import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATE_CACHE: Dict[str, Any] | None = None


def _default_state_file() -> Path:
    return Path(__file__).resolve().parent / "model_cache" / "daily_quota_state.json"


def _state_file_path() -> Path:
    configured = (os.getenv("OSINT_QUOTA_STATE_PATH") or "").strip()
    return Path(configured) if configured else _default_state_file()


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _seconds_until_end_of_day_utc(now_ts: Optional[float] = None) -> int:
    now = datetime.fromtimestamp(now_ts or time.time(), tz=timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((tomorrow - now).total_seconds()))


def _normalize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    today = _today_key()
    if state.get("date") != today:
        return {"date": today, "providers": {}}

    providers = state.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    return {"date": today, "providers": providers}


def _normalize_provider_record(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        used = int(raw.get("used", 0) or 0)
        last_call_ts = raw.get("last_call_ts")
    else:
        # Backward compatibility: old state format stored only an integer count.
        used = int(raw or 0)
        last_call_ts = None

    if last_call_ts is not None:
        try:
            last_call_ts = float(last_call_ts)
        except Exception:
            last_call_ts = None

    return {
        "used": max(0, used),
        "last_call_ts": last_call_ts,
    }


def _load_state_unlocked() -> Dict[str, Any]:
    global _STATE_CACHE
    if _STATE_CACHE is not None:
        _STATE_CACHE = _normalize_state(_STATE_CACHE)
        return _STATE_CACHE

    path = _state_file_path()
    try:
        if path.exists():
            parsed = json.loads(path.read_text(encoding="utf-8"))
            _STATE_CACHE = _normalize_state(parsed)
        else:
            _STATE_CACHE = {"date": _today_key(), "providers": {}}
    except Exception as exc:
        logger.warning("Failed to load quota state file (%s). Resetting state.", exc)
        _STATE_CACHE = {"date": _today_key(), "providers": {}}
    return _STATE_CACHE


def _save_state_unlocked(state: Dict[str, Any]) -> None:
    path = _state_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def _get_provider_record_unlocked(state: Dict[str, Any], provider: str) -> Dict[str, Any]:
    normalized = _normalize_provider_record(state["providers"].get(provider))
    state["providers"][provider] = normalized
    return normalized


def _ideal_interval_seconds(limit: int, used: int, now_ts: Optional[float] = None) -> int:
    if limit <= 0:
        return _seconds_until_end_of_day_utc(now_ts)
    remaining_calls = max(limit - used, 1)
    remaining_seconds = _seconds_until_end_of_day_utc(now_ts)
    return max(1, int(remaining_seconds / remaining_calls))


def _seconds_since_last_call(last_call_ts: Optional[float], now_ts: Optional[float] = None) -> Optional[int]:
    if last_call_ts is None:
        return None
    return max(0, int((now_ts or time.time()) - last_call_ts))


def try_consume_quota(provider: str, limit: int, units: int = 1) -> Tuple[bool, int, int]:
    """
    Simple hard-limit consumer without pacing.
    Returns tuple: (allowed, used_after_attempt, remaining_after_attempt)
    """
    provider = (provider or "").strip().lower()
    if not provider:
        raise ValueError("provider is required")
    if units <= 0:
        raise ValueError("units must be positive")

    hard_limit = max(0, int(limit))
    now_ts = time.time()
    with _LOCK:
        state = _load_state_unlocked()
        record = _get_provider_record_unlocked(state, provider)
        used = int(record["used"])

        if hard_limit == 0:
            return False, used, 0
        if used + units > hard_limit:
            return False, used, max(hard_limit - used, 0)

        used_after = used + units
        record["used"] = used_after
        record["last_call_ts"] = now_ts
        state["providers"][provider] = record
        _save_state_unlocked(state)
        return True, used_after, max(hard_limit - used_after, 0)


BURST_MAX = 10          # Allow up to 10 rapid calls in a burst window
BURST_WINDOW_SECONDS = 60  # Burst window duration in seconds


def try_consume_quota_evenly(
    provider: str,
    limit: int,
    units: int = 1,
    min_interval_seconds: int = 0,
) -> Tuple[bool, int, int, int, str, int]:
    """
    Consumes quota while pacing calls evenly through the day.
    Includes a burst allowance: the first BURST_MAX calls within
    BURST_WINDOW_SECONDS are always allowed (no pacing wait),
    so the frontend can load all domain feeds on startup.

    Returns:
      (allowed, used_after_attempt, remaining_after_attempt, retry_after_seconds, reason, ideal_interval_seconds)
    """
    provider = (provider or "").strip().lower()
    if not provider:
        raise ValueError("provider is required")
    if units <= 0:
        raise ValueError("units must be positive")

    hard_limit = max(0, int(limit))
    floor_interval = max(0, int(min_interval_seconds))
    now_ts = time.time()

    with _LOCK:
        state = _load_state_unlocked()
        record = _get_provider_record_unlocked(state, provider)
        used = int(record["used"])
        last_call_ts = record.get("last_call_ts")
        burst_start_ts = record.get("burst_start_ts")
        burst_count = int(record.get("burst_count", 0))

        if hard_limit == 0:
            return False, used, 0, _seconds_until_end_of_day_utc(now_ts), "disabled", _seconds_until_end_of_day_utc(now_ts)

        if used + units > hard_limit:
            return False, used, max(hard_limit - used, 0), _seconds_until_end_of_day_utc(now_ts), "daily_limit_reached", _ideal_interval_seconds(hard_limit, used, now_ts)

        ideal_interval = max(floor_interval, _ideal_interval_seconds(hard_limit, used, now_ts))

        # ── Burst allowance ──────────────────────────────────────
        # If we are within a burst window and under the burst cap, skip pacing.
        in_burst_window = (
            burst_start_ts is not None
            and (now_ts - float(burst_start_ts)) < BURST_WINDOW_SECONDS
            and burst_count < BURST_MAX
        )
        # Start a new burst window if there is no active one.
        if burst_start_ts is None or (now_ts - float(burst_start_ts or 0)) >= BURST_WINDOW_SECONDS:
            burst_start_ts = now_ts
            burst_count = 0
            in_burst_window = burst_count < BURST_MAX

        if not in_burst_window:
            # Normal pacing outside burst window
            elapsed = _seconds_since_last_call(last_call_ts, now_ts)
            if elapsed is not None and elapsed < ideal_interval:
                retry_after = ideal_interval - elapsed
                return False, used, max(hard_limit - used, 0), retry_after, "pacing_wait", ideal_interval

        used_after = used + units
        record["used"] = used_after
        record["last_call_ts"] = now_ts
        record["burst_start_ts"] = burst_start_ts
        record["burst_count"] = burst_count + 1
        state["providers"][provider] = record
        _save_state_unlocked(state)
        return True, used_after, max(hard_limit - used_after, 0), 0, "consumed", ideal_interval


def get_quota_usage(provider: str, limit: int) -> Dict[str, Any]:
    provider = (provider or "").strip().lower()
    hard_limit = max(0, int(limit))
    now_ts = time.time()

    with _LOCK:
        state = _load_state_unlocked()
        record = _get_provider_record_unlocked(state, provider)
        used = int(record["used"])
        remaining = max(hard_limit - used, 0)
        ideal_interval = _ideal_interval_seconds(hard_limit, used, now_ts)
        since_last = _seconds_since_last_call(record.get("last_call_ts"), now_ts)

        if hard_limit == 0:
            status = "disabled"
            next_call_in = _seconds_until_end_of_day_utc(now_ts)
        elif used >= hard_limit:
            status = "daily_limit_reached"
            next_call_in = _seconds_until_end_of_day_utc(now_ts)
        elif since_last is None:
            status = "available"
            next_call_in = 0
        else:
            next_call_in = max(ideal_interval - since_last, 0)
            status = "available" if next_call_in == 0 else "pacing_wait"

        return {
            "provider": provider,
            "date_utc": state["date"],
            "limit": hard_limit,
            "used": used,
            "remaining": remaining,
            "status": status,
            "ideal_interval_seconds": ideal_interval,
            "seconds_since_last_call": since_last,
            "next_call_in_seconds": next_call_in,
        }

