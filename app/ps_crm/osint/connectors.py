import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

from app.ps_crm.osint.quota import get_quota_usage, try_consume_quota_evenly

try:
    from websockets.sync.client import connect as ws_connect
except Exception:  # pragma: no cover - optional runtime dependency path
    ws_connect = None

logger = logging.getLogger(__name__)

# Ensure .env variables are available even when this module is imported directly.
load_dotenv()


# -----------------------------------------------------------------------------
# Core Output Schema
# -----------------------------------------------------------------------------
class RawIntelObject(BaseModel):
    id: str
    source_api: str
    title: str
    content: str
    timestamp: str
    url: str


# -----------------------------------------------------------------------------
# Environment / Limits
# -----------------------------------------------------------------------------
GNEWS_KEY = os.environ.get("GNEWS_API_KEY", "").strip()
NEWSDATA_KEY = os.environ.get("NEWSDATA_API_KEY", "").strip()

GNEWS_DAILY_LIMIT = max(0, int(os.environ.get("GNEWS_DAILY_LIMIT", "80")))
NEWSDATA_DAILY_LIMIT = max(0, int(os.environ.get("NEWSDATA_DAILY_LIMIT", "80")))
REDDIT_DAILY_LIMIT = max(0, int(os.environ.get("REDDIT_DAILY_LIMIT", "120")))
OPENSKY_DAILY_LIMIT = max(0, int(os.environ.get("OPENSKY_DAILY_LIMIT", "120")))
AISSTREAM_DAILY_LIMIT = max(0, int(os.environ.get("AISSTREAM_DAILY_LIMIT", "120")))

GNEWS_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("GNEWS_MIN_INTERVAL_SECONDS", "0")))
NEWSDATA_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("NEWSDATA_MIN_INTERVAL_SECONDS", "0")))
REDDIT_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("REDDIT_MIN_INTERVAL_SECONDS", "0")))
OPENSKY_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("OPENSKY_MIN_INTERVAL_SECONDS", "0")))
AISSTREAM_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("AISSTREAM_MIN_INTERVAL_SECONDS", "0")))

OSINT_CACHE_TTL_SECONDS = max(60, int(os.environ.get("OSINT_CACHE_TTL_SECONDS", "3600")))

NEWSDATA_URL = os.environ.get("NEWSDATA_API_URL", "https://newsdata.io/api/1/latest").strip()
OPENSKY_TOKEN_URL = os.environ.get("OPENSKY_TOKEN_URL", "https://opensky-network.org/api/oauth/token").strip()
OPENSKY_API_URL = os.environ.get("OPENSKY_API_URL", "https://opensky-network.org/api/states/all").strip()
OPENSKY_CLIENT_ID = os.environ.get("OPENSKY_CLIENT_ID", "").strip()
OPENSKY_CLIENT_SECRET = os.environ.get("OPENSKY_CLIENT_SECRET", "").strip()
OPENSKY_BBOX = os.environ.get("OPENSKY_BBOX", "6.0,68.0,38.0,98.0").strip()
OPENSKY_MAX_STATES = max(1, int(os.environ.get("OPENSKY_MAX_STATES", "12")))

AISSTREAM_API_KEY = os.environ.get("AISSTREAM_API_KEY", "").strip()
AISSTREAM_WS_URL = os.environ.get("AISSTREAM_WS_URL", "wss://stream.aisstream.io/v0/stream").strip()
AISSTREAM_BBOX = os.environ.get("AISSTREAM_BBOX", "5.0,65.0,28.0,96.0").strip()
AISSTREAM_MAX_MESSAGES = max(1, int(os.environ.get("AISSTREAM_MAX_MESSAGES", "2")))
AISSTREAM_TIMEOUT_SECONDS = max(2, int(os.environ.get("AISSTREAM_TIMEOUT_SECONDS", "8")))

_opensky_token_cache: Dict[str, Any] = {"token": "", "expires_at": 0.0}


# Simple In-Memory TTL Cache Strategy
_cache = {
    "last_fetched": 0.0,
    "ttl_seconds": OSINT_CACHE_TTL_SECONDS,
    "data": [],
}


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch_to_iso(epoch_value: Any, fallback: Optional[str] = None) -> str:
    try:
        return datetime.fromtimestamp(float(epoch_value), tz=timezone.utc).isoformat()
    except Exception:
        return fallback or _now_iso()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _consume_provider_quota(provider: str, limit: int, min_interval_seconds: int) -> bool:
    allowed, used, remaining, retry_after, reason, ideal_interval = try_consume_quota_evenly(
        provider,
        limit,
        units=1,
        min_interval_seconds=min_interval_seconds,
    )
    if not allowed:
        usage = get_quota_usage(provider, limit)
        logger.warning(
            "Skipping %s call (%s). used=%s/%s retry_after=%ss next_call_in=%ss",
            provider.upper(),
            reason,
            usage["used"],
            usage["limit"],
            retry_after,
            usage.get("next_call_in_seconds"),
        )
        return False

    logger.info(
        "%s quota usage: %s/%s (remaining %s, ideal_interval=%ss)",
        provider.upper(),
        used,
        limit,
        remaining,
        ideal_interval,
    )
    return True


def _parse_bbox(value: str) -> Optional[Tuple[float, float, float, float]]:
    try:
        parts = [float(piece.strip()) for piece in value.split(",")]
        if len(parts) != 4:
            return None
        return parts[0], parts[1], parts[2], parts[3]
    except Exception:
        return None


def _build_raw_intel(source_api: str, title: str, content: str, timestamp: str, url: str) -> RawIntelObject:
    return RawIntelObject(
        id=str(uuid.uuid4()),
        source_api=source_api,
        title=title,
        content=content,
        timestamp=timestamp or _now_iso(),
        url=url or "#",
    )


def _parse_iso_timestamp(value: Any) -> str:
    if value is None:
        return _now_iso()
    if isinstance(value, (int, float)):
        return _epoch_to_iso(value)
    raw = str(value).strip()
    if not raw:
        return _now_iso()
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc).isoformat()
    except Exception:
        return _now_iso()


# -----------------------------------------------------------------------------
# Connectors
# -----------------------------------------------------------------------------
class NewsConnectors:
    """Connects to GNews + NewsData.io feeds."""

    def fetch_recent(self) -> List[RawIntelObject]:
        results: List[RawIntelObject] = []
        results.extend(self._fetch_gnews_recent())
        results.extend(self._fetch_newsdata_recent())
        return results

    def _fetch_gnews_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from GNEWS API...")
        results: List[RawIntelObject] = []
        if not GNEWS_KEY:
            logger.warning("GNEWS_API_KEY not configured. Skipping GNEWS connector.")
            return results
        if not _consume_provider_quota("gnews", GNEWS_DAILY_LIMIT, GNEWS_MIN_INTERVAL_SECONDS):
            return results

        try:
            url = "https://gnews.io/api/v4/search"
            params = {
                "q": "india government infrastructure OR defense OR trade",
                "lang": "en",
                "max": 8,
                "apikey": GNEWS_KEY,
            }
            resp = httpx.get(url, params=params, timeout=12.0)
            if resp.status_code != 200:
                logger.error("GNEWS API returned status %s", resp.status_code)
                return results

            payload = resp.json()
            for article in payload.get("articles", []):
                results.append(
                    _build_raw_intel(
                        source_api="GNEWS",
                        title=_safe_str(article.get("title"), "GNews item"),
                        content=_safe_str(article.get("description")) or _safe_str(article.get("content")),
                        timestamp=_parse_iso_timestamp(article.get("publishedAt")),
                        url=_safe_str(article.get("url"), "#"),
                    )
                )
        except Exception as exc:
            logger.error("GNEWS request failed: %s", exc)
        return results

    def _fetch_newsdata_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from NewsData.io API...")
        results: List[RawIntelObject] = []
        if not NEWSDATA_KEY:
            logger.warning("NEWSDATA_API_KEY not configured. Skipping NewsData connector.")
            return results
        if not _consume_provider_quota("newsdata", NEWSDATA_DAILY_LIMIT, NEWSDATA_MIN_INTERVAL_SECONDS):
            return results

        try:
            params = {
                "apikey": NEWSDATA_KEY,
                "q": "india OR infrastructure OR defense OR geopolitics OR economy",
                "language": "en",
                "size": 10,
            }
            resp = httpx.get(NEWSDATA_URL, params=params, timeout=12.0)
            if resp.status_code != 200:
                logger.error("NewsData API returned status %s", resp.status_code)
                return results

            payload = resp.json()
            for article in payload.get("results", []):
                source = _safe_str(article.get("source_id"), "newsdata")
                title = _safe_str(article.get("title"), "NewsData item")
                description = _safe_str(article.get("description")) or _safe_str(article.get("content"))
                link = _safe_str(article.get("link"), "#")
                published = _parse_iso_timestamp(article.get("pubDate"))

                results.append(
                    _build_raw_intel(
                        source_api="NewsData.io",
                        title=f"{title} ({source})",
                        content=description,
                        timestamp=published,
                        url=link,
                    )
                )
        except Exception as exc:
            logger.error("NewsData request failed: %s", exc)
        return results


class SocialConnectors:
    """Connects to Reddit public feed."""

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from Reddit API (r/delhi)...")
        results: List[RawIntelObject] = []
        if not _consume_provider_quota("reddit", REDDIT_DAILY_LIMIT, REDDIT_MIN_INTERVAL_SECONDS):
            return results

        try:
            url = "https://www.reddit.com/r/delhi/new.json?limit=5"
            headers = {"User-agent": "civic-osint-bot 0.2"}
            resp = httpx.get(url, headers=headers, timeout=10.0)
            if resp.status_code != 200:
                logger.error("Reddit API returned status %s", resp.status_code)
                return results

            payload = resp.json()
            for post in payload.get("data", {}).get("children", []):
                data = post.get("data", {})
                title = _safe_str(data.get("title"), "Reddit post")
                content = _safe_str(data.get("selftext"))[:600]
                permalink = _safe_str(data.get("permalink"))
                created_utc = data.get("created_utc")
                results.append(
                    _build_raw_intel(
                        source_api="Reddit",
                        title=title,
                        content=content,
                        timestamp=_epoch_to_iso(created_utc),
                        url=f"https://reddit.com{permalink}" if permalink else "#",
                    )
                )
        except Exception as exc:
            logger.error("Reddit request failed: %s", exc)
        return results


class OpenSkyConnectors:
    """Connects to OpenSky OAuth + states API."""

    def _get_access_token(self) -> str:
        now_ts = time.time()
        cached_token = _opensky_token_cache.get("token", "")
        if cached_token and now_ts < float(_opensky_token_cache.get("expires_at", 0.0)) - 30:
            return cached_token

        if not OPENSKY_CLIENT_ID or not OPENSKY_CLIENT_SECRET:
            return ""

        # Primary approach: OAuth2 client credentials with Basic Auth.
        try:
            resp = httpx.post(
                OPENSKY_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET),
                timeout=10.0,
            )
            if resp.status_code != 200:
                logger.error("OpenSky token endpoint returned status %s", resp.status_code)
                return ""
            payload = resp.json()
            token = _safe_str(payload.get("access_token"))
            expires_in = int(payload.get("expires_in", 1800) or 1800)
            if not token:
                logger.error("OpenSky token response missing access_token.")
                return ""
            _opensky_token_cache["token"] = token
            _opensky_token_cache["expires_at"] = now_ts + max(60, expires_in)
            return token
        except Exception as exc:
            logger.error("OpenSky token request failed: %s", exc)
            return ""

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from OpenSky states API...")
        results: List[RawIntelObject] = []
        if not OPENSKY_CLIENT_ID or not OPENSKY_CLIENT_SECRET:
            logger.warning("OpenSky client credentials not configured. Skipping OpenSky connector.")
            return results
        if not _consume_provider_quota("opensky", OPENSKY_DAILY_LIMIT, OPENSKY_MIN_INTERVAL_SECONDS):
            return results

        token = self._get_access_token()
        if not token:
            return results

        headers = {"Authorization": f"Bearer {token}"}
        params: Dict[str, Any] = {}
        bbox = _parse_bbox(OPENSKY_BBOX)
        if bbox:
            params["lamin"], params["lomin"], params["lamax"], params["lomax"] = bbox

        try:
            resp = httpx.get(OPENSKY_API_URL, headers=headers, params=params, timeout=12.0)
            if resp.status_code != 200:
                logger.error("OpenSky states endpoint returned status %s", resp.status_code)
                return results

            payload = resp.json()
            state_time = payload.get("time")
            for state in (payload.get("states") or [])[:OPENSKY_MAX_STATES]:
                icao24 = _safe_str(state[0], "unknown")
                callsign = _safe_str(state[1], icao24)
                origin_country = _safe_str(state[2], "Unknown")
                last_contact = state[4] or state_time
                longitude = _safe_float(state[5])
                latitude = _safe_float(state[6])
                baro_altitude = _safe_float(state[7])
                on_ground = bool(state[8]) if len(state) > 8 else False
                velocity = _safe_float(state[9]) if len(state) > 9 else None

                title = f"OpenSky flight track: {callsign} ({origin_country})"
                content = (
                    f"ICAO24={icao24}; lat={latitude}; lon={longitude}; "
                    f"altitude_m={baro_altitude}; velocity_mps={velocity}; on_ground={on_ground}"
                )
                results.append(
                    _build_raw_intel(
                        source_api="OpenSky",
                        title=title,
                        content=content,
                        timestamp=_epoch_to_iso(last_contact),
                        url=OPENSKY_API_URL,
                    )
                )
        except Exception as exc:
            logger.error("OpenSky states request failed: %s", exc)
        return results


class AISStreamConnectors:
    """Connects to AISStream websocket and ingests vessel position reports."""

    def _subscription_payload(self) -> Dict[str, Any]:
        bbox = _parse_bbox(AISSTREAM_BBOX) or (5.0, 65.0, 28.0, 96.0)
        return {
            "APIKey": AISSTREAM_API_KEY,
            "BoundingBoxes": [[[bbox[0], bbox[1]], [bbox[2], bbox[3]]]],
            "FilterMessageTypes": ["PositionReport"],
        }

    def _message_to_intel(self, payload: Dict[str, Any]) -> Optional[RawIntelObject]:
        meta = payload.get("MetaData") or {}
        message = payload.get("Message") or {}
        position = message.get("PositionReport") or {}

        mmsi = _safe_str(meta.get("MMSI") or meta.get("mmsi"), "unknown")
        ship_name = _safe_str(meta.get("ShipName") or meta.get("shipname"), f"MMSI-{mmsi}")
        latitude = meta.get("latitude", position.get("Latitude"))
        longitude = meta.get("longitude", position.get("Longitude"))
        sog = position.get("Sog")
        cog = position.get("Cog")
        nav_status = position.get("NavigationalStatus")
        ts_value = meta.get("time_utc") or meta.get("Timestamp") or payload.get("time")

        title = f"AIS vessel update: {ship_name} ({mmsi})"
        content = (
            f"lat={latitude}; lon={longitude}; sog={sog}; cog={cog}; "
            f"nav_status={nav_status}; message_type={payload.get('MessageType')}"
        )
        return _build_raw_intel(
            source_api="AISStream",
            title=title,
            content=content,
            timestamp=_parse_iso_timestamp(ts_value),
            url="https://aisstream.io/",
        )

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from AISStream websocket...")
        results: List[RawIntelObject] = []
        if not AISSTREAM_API_KEY:
            logger.warning("AISSTREAM_API_KEY not configured. Skipping AISStream connector.")
            return results
        if ws_connect is None:
            logger.warning("websockets sync client unavailable. Skipping AISStream connector.")
            return results
        if not _consume_provider_quota("aisstream", AISSTREAM_DAILY_LIMIT, AISSTREAM_MIN_INTERVAL_SECONDS):
            return results

        subscription = self._subscription_payload()
        try:
            with ws_connect(AISSTREAM_WS_URL, open_timeout=10, close_timeout=3) as ws:
                ws.send(json.dumps(subscription))
                for _ in range(AISSTREAM_MAX_MESSAGES):
                    try:
                        raw = ws.recv(timeout=AISSTREAM_TIMEOUT_SECONDS)
                    except TimeoutError:
                        break
                    payload = json.loads(raw)
                    item = self._message_to_intel(payload)
                    if item:
                        results.append(item)
        except Exception as exc:
            logger.error("AISStream websocket request failed: %s", exc)
        return results


class GoogleNewsRSSConnector:
    """Fetches news from Google News RSS feeds — free, no API key, unlimited."""

    RSS_QUERIES = [
        "geopolitics diplomacy",
        "defense military weapons",
        "trade economy sanctions",
        "technology AI semiconductor",
        "earthquake climate flood",
        "protest election migration",
        "nuclear missile",
        "India government",
    ]

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from Google News RSS...")
        results: List[RawIntelObject] = []
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed. Skipping Google News RSS.")
            return results

        for query in self.RSS_QUERIES:
            try:
                url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
                feed = feedparser.parse(url)
                for entry in feed.entries[:4]:
                    title = _safe_str(getattr(entry, "title", ""), "RSS item")
                    link = _safe_str(getattr(entry, "link", ""), "#")
                    published = getattr(entry, "published", "")
                    summary = _safe_str(getattr(entry, "summary", ""))
                    source_name = _safe_str(getattr(entry, "source", {}).get("title", "") if hasattr(entry, "source") and isinstance(entry.source, dict) else getattr(getattr(entry, "source", None), "title", "Google News") if hasattr(getattr(entry, "source", None), "title") else "Google News")
                    results.append(
                        _build_raw_intel(
                            source_api=f"Google News ({source_name})",
                            title=title,
                            content=summary or title,
                            timestamp=_parse_iso_timestamp(published),
                            url=link,
                        )
                    )
            except Exception as exc:
                logger.warning("Google News RSS query '%s' failed: %s", query, exc)

        logger.info("Google News RSS: collected %d items.", len(results))
        return results


class IMFConnector:
    """Fetches economic indicators from the IMF SDMX JSON API."""

    BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc"

    # Key indicators: GDP growth, inflation (CPI), current account balance
    DATASETS = [
        {
            "path": "/CompactData/IFS/M.IN.PCPI_IX",
            "label": "India CPI (Consumer Price Index)",
            "domain": "economics",
        },
        {
            "path": "/CompactData/IFS/M.CN.PCPI_IX",
            "label": "China CPI (Consumer Price Index)",
            "domain": "economics",
        },
        {
            "path": "/CompactData/IFS/M.US.PCPI_IX",
            "label": "US CPI (Consumer Price Index)",
            "domain": "economics",
        },
    ]

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from IMF SDMX API...")
        results: List[RawIntelObject] = []

        for dataset in self.DATASETS:
            try:
                url = f"{self.BASE_URL}{dataset['path']}"
                resp = httpx.get(url, timeout=15.0, headers={"Accept": "application/json"})
                if resp.status_code != 200:
                    logger.warning("IMF API returned %s for %s", resp.status_code, dataset["label"])
                    continue

                payload = resp.json()
                # Navigate SDMX structure
                series_data = (
                    payload.get("CompactData", {})
                    .get("DataSet", {})
                    .get("Series", {})
                )
                if not series_data:
                    continue

                obs_list = series_data.get("Obs", [])
                if isinstance(obs_list, dict):
                    obs_list = [obs_list]

                # Take the last 3 observations (most recent months)
                recent = obs_list[-3:] if len(obs_list) > 3 else obs_list
                for obs in recent:
                    period = _safe_str(obs.get("@TIME_PERIOD"), "")
                    value = _safe_str(obs.get("@OBS_VALUE"), "N/A")
                    title = f"IMF: {dataset['label']} — {period}: {value}"
                    content = (
                        f"Period: {period}, Value: {value}. "
                        f"Source: IMF International Financial Statistics (IFS). "
                        f"Indicator: {dataset['label']}."
                    )
                    results.append(
                        _build_raw_intel(
                            source_api="IMF",
                            title=title,
                            content=content,
                            timestamp=_parse_iso_timestamp(f"{period}-01" if period else None),
                            url=f"https://data.imf.org/",
                        )
                    )
            except Exception as exc:
                logger.warning("IMF dataset '%s' failed: %s", dataset["label"], exc)

        logger.info("IMF: collected %d items.", len(results))
        return results


class WorldBankConnector:
    """Fetches development indicators from World Bank API."""

    # Indicator codes
    INDICATORS = [
        ("NY.GDP.MKTP.KD.ZG", "GDP Growth Rate (%)"),
        ("FP.CPI.TOTL.ZG", "Inflation Rate (CPI, %)"),
        ("MS.MIL.XPND.GD.ZS", "Military Expenditure (% of GDP)"),
        ("BX.KLT.DINV.CD.WD", "Foreign Direct Investment (Net Inflows, USD)"),
        ("SL.UEM.TOTL.ZS", "Unemployment Rate (%)"),
    ]

    COUNTRIES = ["IND", "CHN", "USA", "RUS", "PAK", "GBR", "DEU", "JPN"]

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from World Bank API...")
        results: List[RawIntelObject] = []

        for code, label in self.INDICATORS:
            try:
                countries_str = ";".join(self.COUNTRIES)
                url = (
                    f"https://api.worldbank.org/v2/country/{countries_str}"
                    f"/indicator/{code}?format=json&date=2022:2024&per_page=30"
                )
                resp = httpx.get(url, timeout=15.0)
                if resp.status_code != 200:
                    logger.warning("World Bank API returned %s for %s", resp.status_code, label)
                    continue

                payload = resp.json()
                if not isinstance(payload, list) or len(payload) < 2:
                    continue

                data_records = payload[1] or []
                for record in data_records[:10]:
                    country_name = record.get("country", {}).get("value", "Unknown")
                    year = _safe_str(record.get("date"), "")
                    value = record.get("value")
                    if value is None:
                        continue

                    value_str = f"{float(value):.2f}" if isinstance(value, (int, float)) else str(value)
                    title = f"World Bank: {country_name} — {label} ({year}): {value_str}"
                    content = (
                        f"Country: {country_name}, Year: {year}, "
                        f"Indicator: {label} ({code}), Value: {value_str}. "
                        f"Source: World Bank Open Data."
                    )
                    results.append(
                        _build_raw_intel(
                            source_api="World Bank",
                            title=title,
                            content=content,
                            timestamp=_parse_iso_timestamp(f"{year}-07-01" if year else None),
                            url=f"https://data.worldbank.org/indicator/{code}",
                        )
                    )
            except Exception as exc:
                logger.warning("World Bank indicator '%s' failed: %s", label, exc)

        logger.info("World Bank: collected %d items.", len(results))
        return results


class SIPRIConnector:
    """Fetches arms trade and military expenditure data from SIPRI."""

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from SIPRI databases...")
        results: List[RawIntelObject] = []

        # SIPRI Top List page
        try:
            resp = httpx.get(
                "https://www.sipri.org/databases/armstransfers",
                timeout=15.0,
                headers={"User-Agent": "OSINT-Intel-Engine/1.0"},
                follow_redirects=True,
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(resp.text, "lxml")
                # Extract structured content from the page
                paragraphs = soup.find_all("p")
                for i, p in enumerate(paragraphs[:6]):
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        results.append(
                            _build_raw_intel(
                                source_api="SIPRI",
                                title=f"SIPRI Arms Trade Report: {text[:80]}...",
                                content=text[:500],
                                timestamp=_now_iso(),
                                url="https://www.sipri.org/databases/armstransfers",
                            )
                        )
        except Exception as exc:
            logger.warning("SIPRI arms transfers page failed: %s", exc)

        # SIPRI military expenditure page
        try:
            resp = httpx.get(
                "https://www.sipri.org/databases/milex",
                timeout=15.0,
                headers={"User-Agent": "OSINT-Intel-Engine/1.0"},
                follow_redirects=True,
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(resp.text, "lxml")
                paragraphs = soup.find_all("p")
                for i, p in enumerate(paragraphs[:6]):
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        results.append(
                            _build_raw_intel(
                                source_api="SIPRI",
                                title=f"SIPRI Military Expenditure: {text[:80]}...",
                                content=text[:500],
                                timestamp=_now_iso(),
                                url="https://www.sipri.org/databases/milex",
                            )
                        )
        except Exception as exc:
            logger.warning("SIPRI military expenditure page failed: %s", exc)

        logger.info("SIPRI: collected %d items.", len(results))
        return results


YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
YOUTUBE_DAILY_LIMIT = max(0, int(os.environ.get("YOUTUBE_DAILY_LIMIT", "50")))
YOUTUBE_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("YOUTUBE_MIN_INTERVAL_SECONDS", "0")))


class YouTubeConnector:
    """Searches YouTube for intelligence-relevant videos."""

    QUERIES = [
        "geopolitics analysis",
        "military defense latest",
        "world economy news",
        "India foreign policy",
        "nuclear weapons update",
    ]

    def fetch_recent(self) -> List[RawIntelObject]:
        logger.info("Fetching from YouTube Data API...")
        results: List[RawIntelObject] = []
        if not YOUTUBE_API_KEY:
            logger.warning("YOUTUBE_API_KEY not configured. Skipping YouTube connector.")
            return results
        if not _consume_provider_quota("youtube", YOUTUBE_DAILY_LIMIT, YOUTUBE_MIN_INTERVAL_SECONDS):
            return results

        for query in self.QUERIES:
            try:
                url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "date",
                    "maxResults": 3,
                    "key": YOUTUBE_API_KEY,
                    "relevanceLanguage": "en",
                }
                resp = httpx.get(url, params=params, timeout=12.0)
                if resp.status_code != 200:
                    logger.warning("YouTube API returned %s for '%s'", resp.status_code, query)
                    continue

                payload = resp.json()
                for item in payload.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    title = _safe_str(snippet.get("title"), "YouTube video")
                    description = _safe_str(snippet.get("description"))
                    channel = _safe_str(snippet.get("channelTitle"), "Unknown")
                    published = _parse_iso_timestamp(snippet.get("publishedAt"))

                    results.append(
                        _build_raw_intel(
                            source_api=f"YouTube ({channel})",
                            title=title,
                            content=description[:500] if description else title,
                            timestamp=published,
                            url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "#",
                        )
                    )
            except Exception as exc:
                logger.warning("YouTube query '%s' failed: %s", query, exc)

        logger.info("YouTube: collected %d items.", len(results))
        return results


# -----------------------------------------------------------------------------
# Aggregator Orchestration with TTL Cache
# -----------------------------------------------------------------------------
def fetch_all_osint_data() -> List[RawIntelObject]:
    """Hits configured OSINT APIs while utilizing TTL cache to preserve quota."""
    current_time = time.time()

    if _cache["data"] and (current_time - float(_cache["last_fetched"]) < int(_cache["ttl_seconds"])):
        logger.info(
            "OSINT HIT CACHE: Returning %s-minute cached records to preserve API quota.",
            int(_cache["ttl_seconds"]) // 60,
        )
        return _cache["data"]

    logger.info("OSINT CACHE MISS: Triggering live API fetches...")
    all_data: List[RawIntelObject] = []

    connectors = [
        NewsConnectors(),           # NewsData.io (+ legacy GNews if configured)
        SocialConnectors(),         # Reddit
        GoogleNewsRSSConnector(),   # Google News RSS — free, unlimited
        OpenSkyConnectors(),        # OpenSky Network
        AISStreamConnectors(),      # AIS maritime stream
        IMFConnector(),             # IMF economic indicators
        WorldBankConnector(),       # World Bank development data
        SIPRIConnector(),           # SIPRI arms trade + military expenditure
        YouTubeConnector(),         # YouTube intelligence-relevant videos
    ]

    for connector in connectors:
        try:
            all_data.extend(connector.fetch_recent())
        except Exception as exc:
            logger.error("Failed to fetch data from %s: %s", connector.__class__.__name__, exc)

    _cache["last_fetched"] = current_time
    all_data.sort(key=lambda item: item.timestamp, reverse=True)
    _cache["data"] = all_data
    return all_data
