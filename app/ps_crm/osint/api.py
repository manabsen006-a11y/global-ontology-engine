import logging
import os
import re
import time
from typing import Dict, Any, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

from app.ps_crm.osint.connectors import fetch_all_osint_data, GoogleNewsRSSConnector
from app.ps_crm.osint.ai_filter import process_and_filter_intel
from app.ps_crm.osint.quota import get_quota_usage, try_consume_quota_evenly
from app.ps_crm.osint.correlation_engine import (
    process_articles_to_signals,
    generate_intel_reports,
    run_full_correlation_pipeline,
)

logger = logging.getLogger(__name__)

# Ensure .env variables are loaded for direct module execution.
load_dotenv()

router = APIRouter()
news_proxy_router = APIRouter()

NEWSDATA_BASE = "https://newsdata.io/api/1"
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "").strip()
NEWSDATA_DAILY_LIMIT = max(0, int(os.environ.get("NEWSDATA_DAILY_LIMIT", "80")))
NEWSDATA_MIN_INTERVAL_SECONDS = max(0, int(os.environ.get("NEWSDATA_MIN_INTERVAL_SECONDS", "0")))
NEWSDATA_CACHE_MAX_AGE_SECONDS = max(60, int(os.environ.get("GNEWS_CACHE_MAX_AGE_SECONDS", "21600")))

THREAT_WEIGHT = {"none": 0, "low": 6, "medium": 12, "high": 18, "critical": 24, "unknown": 4}
QUERY_STOPWORDS = {
    "and", "or", "the", "for", "with", "from", "into", "onto", "about", "over",
    "under", "after", "before", "between", "among", "news", "latest", "update",
}
_NEWSDATA_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "search": {},
    "latest": {},
}


def _extract_terms(query: str) -> List[str]:
    raw_tokens = re.findall(r"[a-z0-9]{3,}", query.lower())
    return [token for token in raw_tokens if token not in QUERY_STOPWORDS]


def _query_match_score(article: Dict[str, Any], query: str) -> int:
    query = (query or "").strip().lower()
    if not query:
        return 0

    haystack = " ".join([
        str(article.get("title", "")),
        str(article.get("description", "")),
        str(article.get("content", "")),
        str(article.get("category", "")),
        str(article.get("threatLevel", "")),
        str(article.get("source", {}).get("name", "")),
    ]).lower()

    score = 0
    terms = _extract_terms(query)

    if len(query) > 4 and query in haystack:
        score += 10

    for term in terms:
        if term in haystack:
            score += 4

    return score


def _dedupe_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []

    for article in articles:
        url_key = (article.get("url") or "").strip().lower()
        title_key = re.sub(r"\s+", " ", str(article.get("title", "")).strip().lower())
        key = url_key or title_key
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)

    return deduped


def _rank_articles(articles: List[Dict[str, Any]], query: str, max_items: int) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    ranked: List[Dict[str, Any]] = []

    for article in _dedupe_articles(articles):
        query_score = _query_match_score(article, query)
        if query and query_score == 0:
            continue

        relevance = int(article.get("relevanceScore") or 0)
        threat = str(article.get("threatLevel", "none")).strip().lower()
        threat_score = THREAT_WEIGHT.get(threat, 0)
        article["_rank"] = relevance + threat_score + query_score
        ranked.append(article)

    ranked.sort(
        key=lambda item: (
            item.get("_rank", 0),
            str(item.get("publishedAt", "")),
        ),
        reverse=True,
    )

    final = ranked[:max_items]
    for item in final:
        item.pop("_rank", None)
    return final


def _map_intel_to_article(item: Dict[str, Any]) -> Dict[str, Any]:
    threat_level = str(item.get("threat_level") or "None")
    title = item.get("title") or item.get("extracted_category") or "General"
    threat_prefix = "" if threat_level.lower() in {"none", "unknown"} else f"[{threat_level.upper()}] "

    return {
        "title": f"{threat_prefix}{title}".strip(),
        "description": item.get("rationale", ""),
        "content": item.get("rationale", ""),
        "source": {"name": item.get("source_api", "Central OSINT Command")},
        "publishedAt": item.get("timestamp", ""),
        "url": item.get("url", "#"),
        "image": "https://images.unsplash.com/photo-1541888081628-912f2759e917?auto=format&fit=crop&q=80&w=800",
        "relevanceScore": int(item.get("relevance_score") or 0),
        "threatLevel": threat_level,
        "category": item.get("extracted_category", "Uncategorized"),
    }


def _map_newsdata_article(item: Dict[str, Any], query: str = "") -> Dict[str, Any]:
    title = str(item.get("title", "")).strip()
    description = str(item.get("description") or item.get("content") or "").strip()
    published_at = item.get("pubDate", "")
    source_name = item.get("source_id", "NewsData")
    query_score = 8 if query and _query_match_score({"title": title, "description": description}, query) > 0 else 0

    return {
        "title": title,
        "description": description,
        "content": description,
        "source": {"name": source_name},
        "publishedAt": published_at,
        "url": item.get("link", "#"),
        "image": item.get("image_url", ""),
        "relevanceScore": 62 + query_score,
        "threatLevel": "Unknown",
        "category": "News",
    }


def _cache_key_search(query: str, lang: str) -> str:
    return f"{lang.lower()}::{query.strip().lower()}"


def _cache_key_latest(country: str, lang: str, query: str = "") -> str:
    return f"{country.lower()}::{lang.lower()}::{query.strip().lower()}"


def _get_cached_newsdata(kind: str, key: str, max_items: int) -> List[Dict[str, Any]]:
    entry = _NEWSDATA_CACHE.get(kind, {}).get(key)
    if not entry:
        return []

    age_seconds = int(time.time() - float(entry.get("fetched_at", 0)))
    if age_seconds > NEWSDATA_CACHE_MAX_AGE_SECONDS:
        return []

    articles = entry.get("articles", [])
    return list(articles[:max_items]) if isinstance(articles, list) else []


def _set_cached_newsdata(kind: str, key: str, articles: List[Dict[str, Any]]) -> None:
    _NEWSDATA_CACHE.setdefault(kind, {})[key] = {
        "fetched_at": time.time(),
        "articles": articles,
    }


async def _fetch_newsdata_search(query: str, lang: str, max_items: int) -> List[Dict[str, Any]]:
    if not NEWSDATA_API_KEY or not query.strip():
        return []
    cache_key = _cache_key_search(query, lang)
    allowed, used, remaining, retry_after, reason, ideal_interval = try_consume_quota_evenly(
        "newsdata",
        NEWSDATA_DAILY_LIMIT,
        units=1,
        min_interval_seconds=NEWSDATA_MIN_INTERVAL_SECONDS,
    )
    if not allowed:
        cached = _get_cached_newsdata("search", cache_key, max_items)
        if cached:
            logger.info(
                "Using cached NEWSDATA search due to pacing (%s). retry_after=%ss cache_items=%s",
                reason,
                retry_after,
                len(cached),
            )
            return cached

        usage = get_quota_usage("newsdata", NEWSDATA_DAILY_LIMIT)
        logger.warning(
            "NEWSDATA search blocked (%s). used=%s/%s retry_after=%ss next_call_in=%ss",
            reason,
            usage["used"],
            usage["limit"],
            retry_after,
            usage.get("next_call_in_seconds"),
        )
        return []
    logger.info(
        "NEWSDATA quota usage: %s/%s (remaining %s, ideal_interval=%ss)",
        used,
        NEWSDATA_DAILY_LIMIT,
        remaining,
        ideal_interval,
    )

    params = {
        "q": query.strip(),
        "language": lang,
        "size": 10 if max_items > 10 else max_items,
        "apikey": NEWSDATA_API_KEY,
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(f"{NEWSDATA_BASE}/news", params=params)
        if resp.status_code != 200:
            logger.error("NewsData search failed: %s %s", resp.status_code, resp.text[:200])
            return _get_cached_newsdata("search", cache_key, max_items)
        payload = resp.json()

    mapped = [_map_newsdata_article(article, query=query) for article in payload.get("results", [])]
    if mapped:
        _set_cached_newsdata("search", cache_key, mapped)
    return mapped[:max_items]


async def _fetch_newsdata_latest(
    country: str,
    lang: str,
    max_items: int,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not NEWSDATA_API_KEY:
        return []
    cache_key = _cache_key_latest(country, lang, query or "")
    allowed, used, remaining, retry_after, reason, ideal_interval = try_consume_quota_evenly(
        "newsdata",
        NEWSDATA_DAILY_LIMIT,
        units=1,
        min_interval_seconds=NEWSDATA_MIN_INTERVAL_SECONDS,
    )
    if not allowed:
        cached = _get_cached_newsdata("latest", cache_key, max_items)
        if cached:
            logger.info(
                "Using cached NEWSDATA latest due to pacing (%s). retry_after=%ss cache_items=%s",
                reason,
                retry_after,
                len(cached),
            )
            return cached

        usage = get_quota_usage("newsdata", NEWSDATA_DAILY_LIMIT)
        logger.warning(
            "NEWSDATA latest blocked (%s). used=%s/%s retry_after=%ss next_call_in=%ss",
            reason,
            usage["used"],
            usage["limit"],
            retry_after,
            usage.get("next_call_in_seconds"),
        )
        return []
    logger.info(
        "NEWSDATA quota usage: %s/%s (remaining %s, ideal_interval=%ss)",
        used,
        NEWSDATA_DAILY_LIMIT,
        remaining,
        ideal_interval,
    )

    params = {
        "country": country,
        "language": lang,
        "size": 10 if max_items > 10 else max_items,
        "apikey": NEWSDATA_API_KEY,
    }
    if query:
        params["q"] = query

    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(f"{NEWSDATA_BASE}/latest", params=params)
        if resp.status_code != 200:
            logger.error("NewsData latest failed: %s %s", resp.status_code, resp.text[:200])
            return _get_cached_newsdata("latest", cache_key, max_items)
        payload = resp.json()

    mapped = [_map_newsdata_article(article, query=query or "") for article in payload.get("results", [])]
    if mapped:
        _set_cached_newsdata("latest", cache_key, mapped)
    return mapped[:max_items]


async def _fallback_osint_articles(query: str, max_items: int) -> List[Dict[str, Any]]:
    briefing = await get_filtered_osint_briefing(min_relevance=40)
    actionable_intel = briefing.get("briefing", [])
    mapped = [_map_intel_to_article(item) for item in actionable_intel]
    return _rank_articles(mapped, query, max_items)

@router.get("/api/v1/osint/briefing", tags=["Government OSINT"])
async def get_filtered_osint_briefing(min_relevance: int = 50):
    """
    Triggers the Government Intelligence Aggregator.
    1. Reaches out to 10+ APIs (GNEWS, X, Reddit, ACLED, Maltego, etc.)
    2. Pipes the massive raw data dump through the local ML relevance filter.
    3. Returns only the highly-relevant, actionable intelligence for the frontend dashboard.
    """
    logger.info(f"Generating OSINT briefing with minimum relevance threshold: {min_relevance}")
    
    try:
        # Step 1: Hit all connectors
        raw_firehose = fetch_all_osint_data()
        
        # Step 2: Apply Cognitive Filter
        actionable_intel = process_and_filter_intel(raw_firehose, threshold=min_relevance)
        
        return {
            "status": "success",
            "metrics": {
                "total_raw_scraped": len(raw_firehose),
                "retained_after_filter": len(actionable_intel),
                "noise_reduction_ratio": f"{round((1 - (len(actionable_intel) / len(raw_firehose))) * 100, 1)}%" if raw_firehose else "0%"
            },
            "briefing": actionable_intel
        }
    except Exception as e:
        logger.error(f"Error generating OSINT briefing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error assembling intelligence briefing.")


# -----------------------------------------------------------------------------
# Frontend Proxy Adapters
# -----------------------------------------------------------------------------

@news_proxy_router.get("/api/news/search", tags=["Frontend Adapters"])
async def search_news_adapter(
    q: str = Query(..., min_length=1, max_length=240),
    lang: str = Query(default="en", min_length=2, max_length=5),
    max_items: int = Query(default=20, alias="max", ge=1, le=50),
):
    """
    Search endpoint used by the frontend.
    Priority order:
      1) GNews free tier (if API key exists)
      2) AI-filtered OSINT fallback
    """
    try:
        provider = "newsdata"
        articles = await _fetch_newsdata_search(q, lang, max_items)
        if not articles:
            provider = "osint-fallback"
            articles = await _fallback_osint_articles(q, max_items)
        ranked = _rank_articles(articles, q, max_items)

        return {
            "articles": ranked,
            "totalArticles": len(ranked),
            "provider": provider,
        }
    except Exception as e:
        logger.error("News search adapter error: %s", e, exc_info=True)
        return {"articles": [], "totalArticles": 0, "error": str(e)}


@news_proxy_router.get("/api/news/headlines", tags=["Frontend Adapters"])
async def headlines_news_adapter(
    country: str = Query(default="in", min_length=2, max_length=2),
    lang: str = Query(default="en", min_length=2, max_length=5),
    max_items: int = Query(default=20, alias="max", ge=1, le=50),
    q: str = Query(default="", max_length=240),
):
    """
    Top-headlines endpoint used by the frontend.
    Optional `q` can be supplied to hard-filter by segment/domain.
    """
    try:
        provider = "newsdata"
        articles = await _fetch_newsdata_latest(country, lang, max_items, query=q)
        if not articles:
            provider = "osint-fallback"
            articles = await _fallback_osint_articles(q, max_items)
        ranked = _rank_articles(articles, q, max_items)

        return {
            "articles": ranked,
            "totalArticles": len(ranked),
            "provider": provider,
        }
    except Exception as e:
        logger.error("News headlines adapter error: %s", e, exc_info=True)
        return {"articles": [], "totalArticles": 0, "error": str(e)}


# -----------------------------------------------------------------------------
# Intel Nexus — Cross-Domain Correlation Endpoints
# -----------------------------------------------------------------------------

async def _collect_articles_for_correlation() -> List[Dict[str, Any]]:
    """Gather current articles from search + latest for correlation analysis."""
    all_articles: List[Dict[str, Any]] = []
    
    # Try fetching Google News RSS directly to guarantee some structured news content
    try:
        rss_results = GoogleNewsRSSConnector().fetch_recent()
        # Convert RawIntelObjects from RSS back to the article format our correlator expects
        for rss_item in rss_results:
            all_articles.append({
                "title": rss_item.title,
                "description": rss_item.content,
                "content": rss_item.content,
                "source": {"name": rss_item.source_api},
                "publishedAt": rss_item.timestamp,
                "url": rss_item.url,
                "image": "",
                "relevanceScore": 75,
                "threatLevel": "Unknown",
                "category": "News",
            })
    except Exception as exc:
        logger.warning("Google News RSS directly for correlation failed: %s", exc)

    # Fetch broad latest first
    try:
        headlines = await _fetch_newsdata_latest("in", "en", 10)
        all_articles.extend(headlines)
    except Exception as exc:
        logger.warning("NewsData latest fetch for correlation failed: %s", exc)

    # Fetch per-domain queries
    domain_queries = {
        "geopolitics": "diplomacy OR sanctions OR war",
        "defense": "military OR missile OR nuclear",
        "economics": "trade OR economy OR inflation",
        "technology": "AI OR semiconductor OR cyber",
        "climate": "earthquake OR flood OR climate",
        "society": "protest OR election OR migration",
    }
    for domain, query in domain_queries.items():
        try:
            articles = await _fetch_newsdata_search(query, "en", 10)
            all_articles.extend(articles)
        except Exception as exc:
            logger.warning("Domain search '%s' failed for correlation: %s", domain, exc)

    # Also pull from OSINT briefing if available
    try:
        briefing = await get_filtered_osint_briefing(min_relevance=30)
        osint_articles = [_map_intel_to_article(item) for item in briefing.get("briefing", [])]
        all_articles.extend(osint_articles)
    except Exception as exc:
        logger.warning("OSINT briefing for correlation failed: %s", exc)

    return _dedupe_articles(all_articles)


@router.get("/api/v1/intel/correlations", tags=["Intel Nexus"])
async def get_intel_correlations():
    """
    Run the cross-domain correlation engine on current feed data.
    Returns intelligence reports with hypotheses, evidence chains, and trust scores.
    """
    try:
        articles = await _collect_articles_for_correlation()
        if not articles:
            return {
                "reports": [],
                "signals_analyzed": 0,
                "correlations_found": 0,
                "metadata": {"error": "No articles available for correlation analysis"},
            }

        result = run_full_correlation_pipeline(articles)
        return {
            "reports": result["reports"],
            "signals_analyzed": result["metadata"]["signals_analyzed"],
            "correlations_found": result["metadata"]["correlations_found"],
            "metadata": result["metadata"],
        }
    except Exception as e:
        logger.error("Intel correlation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Correlation engine error")


@router.get("/api/v1/intel/signals", tags=["Intel Nexus"])
async def get_intel_signals():
    """
    Return raw classified signals with extracted entities for the signal timeline view.
    """
    try:
        articles = await _collect_articles_for_correlation()
        if not articles:
            return {"signals": [], "total": 0}

        signals = process_articles_to_signals(articles)
        return {
            "signals": [s.to_dict() for s in signals],
            "total": len(signals),
            "domains_covered": sorted(list({s.domain for s in signals})),
        }
    except Exception as e:
        logger.error("Intel signals error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Signal processing error")
