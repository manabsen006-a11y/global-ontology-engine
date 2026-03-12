"""
app/ps_crm/osint/correlation_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cross-Domain Intelligence Correlation Engine

Connects signals across domains (Geopolitics, Economics, Defense,
Technology, Climate, Society) to produce synthesized intelligence
assessments with trust scores and evidence chains.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.ps_crm.osint.entity_data import (
    CORRELATION_TEMPLATES,
    COUNTRIES,
    DOMAIN_KEYWORDS,
    EVENT_TYPES,
    KEY_PEOPLE,
    ORGANIZATIONS,
    RESOURCES,
    get_source_credibility,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

class Signal:
    """A classified intelligence signal extracted from a news article."""

    def __init__(
        self,
        article_title: str,
        article_url: str,
        domain: str,
        entities: Dict[str, List[str]],
        event_types: List[str],
        sentiment: str,
        timestamp: str,
        source: str,
        trust_base: float,
        raw_text: str = "",
    ):
        self.id = str(uuid.uuid4())[:12]
        self.article_title = article_title
        self.article_url = article_url
        self.domain = domain
        self.entities = entities  # {"countries": [...], "organizations": [...], ...}
        self.event_types = event_types
        self.sentiment = sentiment
        self.timestamp = timestamp
        self.source = source
        self.trust_base = trust_base
        self.raw_text = raw_text

    def all_entity_names(self) -> Set[str]:
        """Flattened set of all entity names across categories."""
        names: Set[str] = set()
        for entity_list in self.entities.values():
            names.update(entity_list)
        return names

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.article_title,
            "url": self.article_url,
            "domain": self.domain,
            "entities": self.entities,
            "event_types": self.event_types,
            "sentiment": self.sentiment,
            "timestamp": self.timestamp,
            "source": self.source,
            "trust_base": round(self.trust_base, 3),
        }


class IntelReport:
    """A synthesized intelligence assessment from correlated signals."""

    def __init__(
        self,
        title: str,
        hypothesis: str,
        evidence_chain: List[Dict[str, Any]],
        trust_score: float,
        entities: List[str],
        domains_spanned: List[str],
        severity: str,
        template_name: str = "",
        key_signals: Optional[List[Signal]] = None,
    ):
        self.id = str(uuid.uuid4())[:12]
        self.title = title
        self.hypothesis = hypothesis
        self.evidence_chain = evidence_chain
        self.trust_score = trust_score
        self.entities = entities
        self.domains_spanned = domains_spanned
        self.severity = severity
        self.template_name = template_name
        self.key_signals = key_signals or []
        self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "hypothesis": self.hypothesis,
            "evidence_chain": self.evidence_chain,
            "trust_score": round(self.trust_score, 3),
            "entities": self.entities,
            "domains_spanned": self.domains_spanned,
            "severity": self.severity,
            "template_name": self.template_name,
            "generated_at": self.generated_at,
            "signal_count": len(self.key_signals),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Entity Extractor
# ─────────────────────────────────────────────────────────────────────────────

class EntityExtractor:
    """Extracts named entities from text using keyword matching."""

    @staticmethod
    def extract(text: str) -> Dict[str, List[str]]:
        """Extract all entity types from text."""
        text_lower = text.lower()
        result: Dict[str, List[str]] = {
            "countries": [],
            "organizations": [],
            "people": [],
            "resources": [],
        }

        # Countries
        for name, aliases in COUNTRIES.items():
            for alias in aliases:
                if len(alias) <= 3:
                    # Short aliases need word-boundary matching
                    if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                        if name not in result["countries"]:
                            result["countries"].append(name)
                        break
                else:
                    if alias in text_lower:
                        if name not in result["countries"]:
                            result["countries"].append(name)
                        break

        # Organizations
        for name, aliases in ORGANIZATIONS.items():
            for alias in aliases:
                if len(alias) <= 3:
                    if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                        if name not in result["organizations"]:
                            result["organizations"].append(name)
                        break
                else:
                    if alias in text_lower:
                        if name not in result["organizations"]:
                            result["organizations"].append(name)
                        break

        # People
        for name, aliases in KEY_PEOPLE.items():
            for alias in aliases:
                if alias in text_lower:
                    if name not in result["people"]:
                        result["people"].append(name)
                    break

        # Resources
        for name, aliases in RESOURCES.items():
            for alias in aliases:
                if len(alias) <= 3:
                    if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                        if name not in result["resources"]:
                            result["resources"].append(name)
                        break
                else:
                    if alias in text_lower:
                        if name not in result["resources"]:
                            result["resources"].append(name)
                        break

        return result


# ─────────────────────────────────────────────────────────────────────────────
# Signal Classifier
# ─────────────────────────────────────────────────────────────────────────────

class SignalClassifier:
    """Classifies articles into domains, extracts events, and builds Signals."""

    @staticmethod
    def classify_domain(text: str) -> Tuple[str, int]:
        """Returns (domain, confidence_score)."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[domain] = score

        if not scores or max(scores.values()) == 0:
            return "unknown", 0

        best_domain = max(scores, key=scores.get)
        return best_domain, scores[best_domain]

    @staticmethod
    def detect_events(text: str) -> List[str]:
        """Detect event types present in the text."""
        text_lower = text.lower()
        detected = []

        for event_type, keywords in EVENT_TYPES.items():
            for kw in keywords:
                if kw in text_lower:
                    if event_type not in detected:
                        detected.append(event_type)
                    break

        return detected

    @staticmethod
    def infer_sentiment(text: str) -> str:
        """Simple sentiment classification."""
        text_lower = text.lower()
        positive = ["growth", "improve", "success", "launch", "boost", "deal",
                     "agreement", "peace", "cooperation", "record", "approved"]
        negative = ["crisis", "attack", "protest", "shortage", "risk", "threat",
                     "war", "conflict", "bomb", "kill", "sanction", "collapse",
                     "scandal", "corruption", "failure"]

        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)

        if neg_count > pos_count:
            return "negative"
        if pos_count > neg_count:
            return "positive"
        return "neutral"

    @classmethod
    def build_signal(cls, article: Dict[str, Any]) -> Signal:
        """Convert a raw article dict into a classified Signal."""
        title = str(article.get("title", "")).strip()
        description = str(article.get("description", "") or article.get("content", "")).strip()
        full_text = f"{title} {description}"
        source = str(
            article.get("source", {}).get("name", "")
            if isinstance(article.get("source"), dict)
            else article.get("source_api", article.get("source", "Unknown"))
        ).strip()

        domain, confidence = cls.classify_domain(full_text)
        entities = EntityExtractor.extract(full_text)
        event_types = cls.detect_events(full_text)
        sentiment = cls.infer_sentiment(full_text)
        trust_base = get_source_credibility(source)

        return Signal(
            article_title=title,
            article_url=str(article.get("url", "#")),
            domain=domain if domain != "unknown" else "geopolitics",
            entities=entities,
            event_types=event_types,
            sentiment=sentiment,
            timestamp=str(article.get("publishedAt", "") or article.get("timestamp", "")),
            source=source,
            trust_base=trust_base,
            raw_text=full_text[:500],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Correlation Engine
# ─────────────────────────────────────────────────────────────────────────────

class CorrelationEngine:
    """
    Finds cross-domain intelligence connections by:
    1. Grouping signals by shared entities
    2. Running correlation templates
    3. Computing open (templateless) correlations
    """

    def __init__(self, signals: List[Signal]):
        self.signals = signals
        self.entity_clusters: Dict[str, List[Signal]] = defaultdict(list)
        self._build_entity_clusters()

    def _build_entity_clusters(self):
        """Group signals by their primary entities."""
        for signal in self.signals:
            # Cluster by countries primarily
            for country in signal.entities.get("countries", []):
                self.entity_clusters[country].append(signal)
            # Also cluster by organizations
            for org in signal.entities.get("organizations", []):
                self.entity_clusters[org].append(signal)
            # Cluster by people
            for person in signal.entities.get("people", []):
                self.entity_clusters[person].append(signal)
            # Cluster by resources
            for resource in signal.entities.get("resources", []):
                self.entity_clusters[resource].append(signal)

    def _cluster_domains(self, cluster: List[Signal]) -> Set[str]:
        """Get the set of domains spanned by a signal cluster."""
        return {s.domain for s in cluster}

    def _cluster_events(self, cluster: List[Signal]) -> Set[str]:
        """Get all event types in a signal cluster."""
        events: Set[str] = set()
        for s in cluster:
            events.update(s.event_types)
        return events

    def _cluster_events_by_domain(self, cluster: List[Signal]) -> Dict[str, Set[str]]:
        """Group events by domain for template matching."""
        result: Dict[str, Set[str]] = defaultdict(set)
        for s in cluster:
            for evt in s.event_types:
                result[s.domain].add(evt)
        return dict(result)

    def run_template_correlations(self) -> List[IntelReport]:
        """Run all correlation templates against entity clusters."""
        reports: List[IntelReport] = []

        for entity_name, cluster in self.entity_clusters.items():
            domains = self._cluster_domains(cluster)

            # Need at least 2 domains for cross-domain correlation
            if len(domains) < 2:
                continue

            domain_events = self._cluster_events_by_domain(cluster)

            for template in CORRELATION_TEMPLATES:
                report = self._try_template(entity_name, cluster, domain_events, template)
                if report:
                    reports.append(report)

        # Deduplicate reports with similar titles
        return self._dedupe_reports(reports)

    def _try_template(
        self,
        entity_name: str,
        cluster: List[Signal],
        domain_events: Dict[str, Set[str]],
        template: Dict[str, Any],
    ) -> Optional[IntelReport]:
        """Try to match a correlation template against a cluster."""
        preconditions = template["preconditions"]
        negative_checks = template.get("negative_checks", [])

        # Check all preconditions
        matched_signals: List[Signal] = []
        evidence_chain: List[Dict[str, Any]] = []

        for precond in preconditions:
            domain = precond["domain"]
            required_events = precond["events"]

            domain_event_set = domain_events.get(domain, set())
            matched_event = None
            for evt in required_events:
                if evt in domain_event_set:
                    matched_event = evt
                    break

            if matched_event is None:
                return None  # Precondition not met

            # Find the signal(s) that provided this evidence
            for signal in cluster:
                if signal.domain == domain and matched_event in signal.event_types:
                    if signal not in matched_signals:
                        matched_signals.append(signal)
                    evidence_chain.append({
                        "domain": domain,
                        "event": matched_event,
                        "signal_title": signal.article_title,
                        "signal_source": signal.source,
                        "signal_url": signal.article_url,
                        "signal_timestamp": signal.timestamp,
                    })
                    break

        # Check negative conditions (absence strengthens hypothesis)
        negative_strength = 0.0
        for neg in negative_checks:
            domain = neg["domain"]
            neg_events = neg["events"]
            domain_event_set = domain_events.get(domain, set())
            # If negative event is ABSENT, that's good
            neg_present = any(evt in domain_event_set for evt in neg_events)
            if not neg_present:
                negative_strength += 0.08
                evidence_chain.append({
                    "domain": domain,
                    "event": f"ABSENT: {', '.join(neg_events)}",
                    "signal_title": f"No {', '.join(neg_events).replace('_', ' ')} detected — strengthens hypothesis",
                    "signal_source": "Absence analysis",
                    "signal_url": "#",
                    "signal_timestamp": "",
                })

        # Compute trust score
        trust_score = self._compute_correlation_trust(
            matched_signals,
            template.get("trust_bonus", 0.0),
            negative_strength,
        )

        # Extract context variables for hypothesis enhancement
        involved_countries = set()
        involved_orgs = set()
        involved_people = set()
        for s in matched_signals:
            involved_countries.update(s.entities.get("countries", []))
            involved_orgs.update(s.entities.get("organizations", []))
            involved_people.update(s.entities.get("people", []))

        all_actors = (involved_orgs | involved_people) - {entity_name}
        all_locations = involved_countries - {entity_name}
        
        actors_str = ", ".join(a.title() for a in sorted(all_actors)) if all_actors else "Unspecified Actors"
        locations_str = ", ".join(l.title() for l in sorted(all_locations)) if all_locations else "Unspecified Regions"

        # Build Title
        title_template = template.get("title_template")
        if title_template:
            title = title_template.format(entity=entity_name.title(), actors=actors_str, locations=locations_str)
        else:
            title = f"{template['name']}: {entity_name.title()}"

        # Build Hypothesis
        base_hypothesis = template["hypothesis_template"].format(entity=entity_name.title(), actors=actors_str, locations=locations_str)
        if "{actors}" not in template["hypothesis_template"]:
            base_hypothesis += f" Other actors involved: {actors_str}."
        hypothesis = base_hypothesis

        domains_spanned = sorted({ec["domain"] for ec in evidence_chain if ec["domain"]})
        all_entities = set()
        for s in matched_signals:
            all_entities.update(s.all_entity_names())
        all_entities.add(entity_name)

        return IntelReport(
            title=title,
            hypothesis=hypothesis,
            evidence_chain=evidence_chain,
            trust_score=trust_score,
            entities=sorted(all_entities),
            domains_spanned=domains_spanned,
            severity=template.get("severity", "MED"),
            template_name=template["name"],
            key_signals=matched_signals,
        )

    def run_open_correlations(self) -> List[IntelReport]:
        """
        Find cross-domain connections without templates.
        Uses entity co-occurrence and multi-domain clustering.
        """
        reports: List[IntelReport] = []

        for entity_name, cluster in self.entity_clusters.items():
            domains = self._cluster_domains(cluster)

            # Need at least 3 different signals across 2+ domains for open correlation
            if len(domains) < 2 or len(cluster) < 3:
                continue

            # Skip if already covered by a template (will be checked in dedup)
            events = self._cluster_events(cluster)

            # Build connections narrative
            evidence_chain = []
            for signal in sorted(cluster, key=lambda s: s.timestamp, reverse=True)[:6]:
                evidence_chain.append({
                    "domain": signal.domain,
                    "event": ", ".join(signal.event_types[:2]) if signal.event_types else "general",
                    "signal_title": signal.article_title,
                    "signal_source": signal.source,
                    "signal_url": signal.article_url,
                    "signal_timestamp": signal.timestamp,
                })

            # Compute open correlation score (generally lower than template matches)
            trust_score = self._compute_open_correlation_trust(cluster)

            # Build hypothesis from the signals
            involved_countries = set()
            involved_orgs = set()
            involved_people = set()
            for s in cluster:
                involved_countries.update(s.entities.get("countries", []))
                involved_orgs.update(s.entities.get("organizations", []))
                involved_people.update(s.entities.get("people", []))

            all_actors = (involved_orgs | involved_people) - {entity_name}
            all_locations = involved_countries - {entity_name}
            actors_str = ", ".join(a.title() for a in sorted(all_actors)) if all_actors else "None specified"
            locations_str = ", ".join(l.title() for l in sorted(all_locations)) if all_locations else "None specified"

            hypothesis = (
                f"Multi-domain intelligence activities ({', '.join(sorted(domains))}) observed involving {entity_name.title()}. "
                f"Economic, geopolitical, or defense maneuvers associated with this entity indicate a coordinated strategic shift. "
                f"Suspected actors responsible: {actors_str}. "
                f"Regions involved: {locations_str}."
            )

            # Determine severity from events
            severity = "MED"
            high_sev_events = {"military_conflict", "nuclear_test", "cyber_attack", "regime_change", "assassination"}
            med_sev_events = {"sanctions", "protest", "arms_deal", "missile_test", "territorial_dispute"}
            if events & high_sev_events:
                severity = "CRIT"
            elif events & med_sev_events:
                severity = "HIGH"

            all_entities = set()
            for s in cluster:
                all_entities.update(s.all_entity_names())

            reports.append(IntelReport(
                title=f"Multi-Domain Activity Detected: {entity_name.title()}",
                hypothesis=hypothesis,
                evidence_chain=evidence_chain,
                trust_score=trust_score,
                entities=sorted(all_entities),
                domains_spanned=sorted(domains),
                severity=severity,
                template_name="Open Correlation",
                key_signals=cluster[:6],
            ))

        return self._dedupe_reports(reports)

    @staticmethod
    def _compute_correlation_trust(
        signals: List[Signal],
        template_bonus: float,
        negative_strength: float,
    ) -> float:
        """Compute trust score for a template-matched correlation."""
        if not signals:
            return 0.0

        # Average source credibility
        avg_credibility = sum(s.trust_base for s in signals) / len(signals)

        # Source diversity bonus (different sources = more trustworthy)
        unique_sources = len({s.source for s in signals})
        diversity_bonus = min(0.15, unique_sources * 0.05)

        # Domain span bonus (more domains = stronger correlation)
        domain_count = len({s.domain for s in signals})
        domain_bonus = min(0.15, domain_count * 0.05)

        # Temporal coherence (signals within 72 hours are more coherent)
        temporal_bonus = 0.05  # Default moderate

        raw = avg_credibility + diversity_bonus + domain_bonus + template_bonus + negative_strength + temporal_bonus
        return max(0.0, min(1.0, raw))

    @staticmethod
    def _compute_open_correlation_trust(cluster: List[Signal]) -> float:
        """Compute trust for templateless open correlations (lower baseline)."""
        if not cluster:
            return 0.0

        avg_credibility = sum(s.trust_base for s in cluster) / len(cluster)
        unique_sources = len({s.source for s in cluster})
        domain_count = len({s.domain for s in cluster})

        raw = (avg_credibility * 0.6) + min(0.12, unique_sources * 0.04) + min(0.12, domain_count * 0.04)
        return max(0.0, min(0.85, raw))

    @staticmethod
    def _dedupe_reports(reports: List[IntelReport]) -> List[IntelReport]:
        """Deduplicate reports with similar content."""
        seen_hashes: Set[str] = set()
        unique: List[IntelReport] = []

        for report in sorted(reports, key=lambda r: r.trust_score, reverse=True):
            # Create a content hash from template + entities
            key = f"{report.template_name}|{'|'.join(sorted(report.entities)[:3])}"
            h = hashlib.md5(key.encode()).hexdigest()[:10]
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique.append(report)

        return unique


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def process_articles_to_signals(articles: List[Dict[str, Any]]) -> List[Signal]:
    """Convert a list of article dicts into classified Signals."""
    signals: List[Signal] = []
    for article in articles:
        try:
            signal = SignalClassifier.build_signal(article)
            # Only keep signals with at least one entity
            if signal.all_entity_names():
                signals.append(signal)
        except Exception as exc:
            logger.warning("Failed to process article: %s", exc)
    return signals


def generate_intel_reports(signals: List[Signal]) -> List[IntelReport]:
    """Run the full correlation engine and return intelligence reports."""
    engine = CorrelationEngine(signals)

    # Template-based correlations (high confidence)
    template_reports = engine.run_template_correlations()

    # Open correlations (moderate confidence)
    open_reports = engine.run_open_correlations()

    # Combine and sort by trust score
    all_reports = template_reports + open_reports
    all_reports.sort(key=lambda r: (
        {"CRIT": 4, "HIGH": 3, "MED": 2, "LOW": 1}.get(r.severity, 0),
        r.trust_score,
    ), reverse=True)

    return all_reports


def run_full_correlation_pipeline(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    End-to-end pipeline:
    1. Process articles into signals
    2. Run correlation engine
    3. Return structured result
    """
    signals = process_articles_to_signals(articles)
    reports = generate_intel_reports(signals)

    return {
        "signals": [s.to_dict() for s in signals],
        "reports": [r.to_dict() for r in reports],
        "metadata": {
            "signals_analyzed": len(signals),
            "correlations_found": len(reports),
            "template_matches": len([r for r in reports if r.template_name != "Open Correlation"]),
            "open_correlations": len([r for r in reports if r.template_name == "Open Correlation"]),
            "domains_covered": sorted(list({s.domain for s in signals})),
            "entities_extracted": len({e for s in signals for e in s.all_entity_names()}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
