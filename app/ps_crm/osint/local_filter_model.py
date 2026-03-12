import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / "model_cache"
MODEL_PATH = MODEL_DIR / "news_filter_model.joblib"

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Sanitation": ["garbage overflow", "sewage leak", "waste collection delay", "drain blockage"],
    "Traffic": ["traffic congestion", "signal failure", "road accident", "vehicular jam"],
    "Civil Unrest": ["public protest", "road blockade", "violent clash", "demonstration"],
    "Infrastructure": ["bridge collapse", "water pipeline burst", "power outage", "road repair"],
    "Healthcare": ["disease outbreak", "hospital shortage", "vaccination drive", "public health alert"],
    "Education": ["school closure", "teacher shortage", "exam reform", "education policy"],
    "Finance": ["budget deficit", "tax revenue drop", "inflation pressure", "municipal debt"],
    "Security": ["terror alert", "cyber attack", "bomb threat", "security advisory"],
    "Geopolitics": ["border tension", "diplomatic talks", "sanctions", "strategic pact"],
}

NOISE_TOPICS = [
    "celebrity wedding", "film release", "cricket fantasy league", "gaming stream",
    "fashion week", "travel vlog", "restaurant review", "music concert",
]

THREAT_KEYWORDS = {
    "Critical": ["terror", "bomb", "invasion", "missile", "riot", "cyber attack"],
    "High": ["protest", "clash", "outage", "collapse", "security", "threat"],
    "Medium": ["policy", "budget", "review", "advisory", "meeting", "summit"],
}

_BUNDLE_CACHE: Dict[str, Any] | None = None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _build_training_samples() -> List[Tuple[str, int, str]]:
    positives: List[Tuple[str, int, str]] = []
    positive_templates = [
        "City command reports {keyword} affecting multiple wards.",
        "Officials issued a response plan after {keyword} triggered citizen complaints.",
        "Breaking: {keyword} has escalated and requires urgent municipal coordination.",
        "Analysts flagged {keyword} as a high-priority {category} intelligence signal.",
    ]

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            for template in positive_templates:
                positives.append((template.format(keyword=keyword, category=category.lower()), 1, category))

    negatives: List[Tuple[str, int, str]] = []
    negative_templates = [
        "Fans are excited about the latest {topic} this weekend.",
        "Social media discussion trends around {topic} and lifestyle updates.",
        "Influencers posted reactions to {topic} with no civic impact.",
        "Entertainment roundup: {topic} dominates online chatter.",
    ]
    for topic in NOISE_TOPICS:
        for template in negative_templates:
            negatives.append((template.format(topic=topic), 0, "Noise"))

    hard_negatives = [
        ("The weather is pleasant for tourism this week with clear skies.", 0, "Noise"),
        ("Sports fans debate player transfers and team rankings online.", 0, "Noise"),
        ("Movie ticket bookings surged after a trailer release.", 0, "Noise"),
        ("A startup launched a gaming headset for creators.", 0, "Noise"),
    ]
    negatives.extend(hard_negatives)

    return positives + negatives


def _train_model_bundle() -> Dict[str, Any]:
    samples = _build_training_samples()
    texts = [_clean_text(text) for text, _, _ in samples]
    y_relevance = [label for _, label, _ in samples]
    y_category = [category for _, _, category in samples]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=7000)
    X = vectorizer.fit_transform(texts)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_relevance, test_size=0.2, random_state=42, stratify=y_relevance
    )
    relevance_model = LogisticRegression(max_iter=700, class_weight="balanced", solver="liblinear")
    relevance_model.fit(X_train, y_train)
    relevance_acc = accuracy_score(y_test, relevance_model.predict(X_test))

    relevant_indices = [idx for idx, label in enumerate(y_relevance) if label == 1]
    X_rel = X[relevant_indices]
    y_rel_categories = [y_category[idx] for idx in relevant_indices]
    X_cat_train, X_cat_test, y_cat_train, y_cat_test = train_test_split(
        X_rel, y_rel_categories, test_size=0.2, random_state=42, stratify=y_rel_categories
    )
    category_model = LogisticRegression(max_iter=800, solver="lbfgs")
    category_model.fit(X_cat_train, y_cat_train)
    category_acc = accuracy_score(y_cat_test, category_model.predict(X_cat_test))

    return {
        "vectorizer": vectorizer,
        "relevance_model": relevance_model,
        "category_model": category_model,
        "metrics": {
            "relevance_accuracy": float(relevance_acc),
            "category_accuracy": float(category_acc),
            "sample_count": len(samples),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def train_and_save_local_filter_model(force_retrain: bool = False) -> Dict[str, Any]:
    global _BUNDLE_CACHE

    if MODEL_PATH.exists() and not force_retrain:
        bundle = joblib.load(MODEL_PATH)
        _BUNDLE_CACHE = bundle
        return bundle

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = _train_model_bundle()
    joblib.dump(bundle, MODEL_PATH)
    _BUNDLE_CACHE = bundle
    logger.info("Local news filter model trained and saved to %s", MODEL_PATH)
    logger.info("Training metrics: %s", bundle.get("metrics"))
    return bundle


def _load_model_bundle() -> Dict[str, Any]:
    global _BUNDLE_CACHE
    if _BUNDLE_CACHE is not None:
        return _BUNDLE_CACHE

    try:
        if MODEL_PATH.exists():
            _BUNDLE_CACHE = joblib.load(MODEL_PATH)
        else:
            _BUNDLE_CACHE = train_and_save_local_filter_model(force_retrain=True)
    except Exception as exc:
        logger.warning("Failed to load local model from disk (%s). Re-training.", exc)
        _BUNDLE_CACHE = train_and_save_local_filter_model(force_retrain=True)
    return _BUNDLE_CACHE


def _infer_threat_level(text: str, relevance_score: int) -> str:
    if any(token in text for token in THREAT_KEYWORDS["Critical"]):
        return "Critical"
    if any(token in text for token in THREAT_KEYWORDS["High"]):
        return "High"
    if any(token in text for token in THREAT_KEYWORDS["Medium"]):
        return "Medium"
    if relevance_score >= 80:
        return "High"
    if relevance_score >= 60:
        return "Medium"
    return "Low"


def _category_signal(text: str, category: str) -> str:
    for keyword in CATEGORY_KEYWORDS.get(category, []):
        if keyword in text:
            return keyword
    return "contextual policy"


def predict_intel_with_local_model(source_api: str, title: str, content: str) -> Dict[str, Any]:
    bundle = _load_model_bundle()
    vectorizer: TfidfVectorizer = bundle["vectorizer"]
    relevance_model: LogisticRegression = bundle["relevance_model"]
    category_model: LogisticRegression = bundle["category_model"]

    text = _clean_text(f"{source_api} {title} {content}")
    vec = vectorizer.transform([text])
    relevance_prob = float(relevance_model.predict_proba(vec)[0][1])
    relevance_score = int(round(relevance_prob * 100))
    is_relevant = relevance_prob >= 0.5

    if is_relevant:
        extracted_category = str(category_model.predict(vec)[0])
        threat_level = _infer_threat_level(text, relevance_score)
        signal = _category_signal(text, extracted_category)
    else:
        extracted_category = "Uncategorized"
        threat_level = "None"
        signal = "low civic relevance"

    rationale = (
        f"Local ML model scored relevance at {relevance_score}/100 "
        f"using {signal} indicators from the incoming text."
    )

    return {
        "is_relevant": bool(is_relevant),
        "relevance_score": relevance_score,
        "threat_level": threat_level,
        "rationale": rationale,
        "extracted_category": extracted_category,
    }


def get_model_metadata() -> Dict[str, Any]:
    bundle = _load_model_bundle()
    return bundle.get("metrics", {})
