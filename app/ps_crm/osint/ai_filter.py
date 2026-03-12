import logging
from typing import Dict, Any, List

from app.ps_crm.osint.connectors import RawIntelObject
from app.ps_crm.osint.local_filter_model import predict_intel_with_local_model

logger = logging.getLogger(__name__)


def process_and_filter_intel(raw_intel: List[RawIntelObject], threshold: int = 50) -> List[Dict[str, Any]]:
    """
    Scores each incoming OSINT item using a locally trained ML model and
    keeps only records at or above `threshold`.
    """
    filtered_results: List[Dict[str, Any]] = []
    logger.info("Filtering %d raw OSINT items through local ML model...", len(raw_intel))

    for item in raw_intel:
        try:
            analysis = predict_intel_with_local_model(
                source_api=item.source_api,
                title=item.title,
                content=item.content,
            )
            score = int(analysis.get("relevance_score", 0))

            if analysis.get("is_relevant") and score >= threshold:
                filtered_results.append({
                    "source_api": item.source_api,
                    "title": item.title,
                    "timestamp": item.timestamp,
                    "url": item.url,
                    "is_relevant": bool(analysis.get("is_relevant", False)),
                    "relevance_score": score,
                    "threat_level": analysis.get("threat_level", "None"),
                    "rationale": analysis.get("rationale", ""),
                    "extracted_category": analysis.get("extracted_category", "Uncategorized"),
                })
            else:
                logger.debug("Dropped OSINT item (%s/100): %s", score, item.title)
        except Exception as exc:
            logger.error("Filtering failed on item %s: %s", item.id, exc, exc_info=True)

    filtered_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    logger.info(
        "Local ML filter complete. Retained %d of %d items.",
        len(filtered_results),
        len(raw_intel),
    )
    return filtered_results
