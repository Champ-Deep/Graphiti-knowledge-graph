"""
Intent Scoring Engine

Calculates buying intent scores based on configurable signals from multiple channels:
- Email engagement (opens, replies, forward, clicks)
- Web behavior (page visits, time on site, return visits)
- Social engagement (likes, comments, shares)
- Content consumption (downloads, video views)
- Firmographic fit (ICP matching)
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class IntentSignalConfig:
    """Configuration for an intent signal"""
    name: str
    weight: float  # 0.0 to 1.0
    decay_days: Optional[int] = None  # How many days before signal loses value
    threshold: Optional[float] = None  # Minimum value to count


@dataclass
class IntentScoringConfig:
    """Configuration for intent scoring"""
    # Signal weights
    signals: List[IntentSignalConfig] = field(default_factory=lambda: [
        # Email signals (35% total)
        IntentSignalConfig("email_reply", weight=0.15, decay_days=14),
        IntentSignalConfig("email_open", weight=0.05, decay_days=7),
        IntentSignalConfig("email_click", weight=0.10, decay_days=10),
        IntentSignalConfig("email_forward", weight=0.05, decay_days=7),

        # Web signals (40% total)
        IntentSignalConfig("pricing_page_visit", weight=0.20, decay_days=7),
        IntentSignalConfig("product_page_visit", weight=0.10, decay_days=14),
        IntentSignalConfig("demo_request", weight=0.30, decay_days=3),
        IntentSignalConfig("case_study_view", weight=0.05, decay_days=14),
        IntentSignalConfig("return_visitor", weight=0.10, decay_days=7),
        IntentSignalConfig("long_session", weight=0.05, decay_days=7, threshold=120.0),  # 2+ minutes

        # Social signals (15% total)
        IntentSignalConfig("linkedin_engagement", weight=0.08, decay_days=14),
        IntentSignalConfig("twitter_mention", weight=0.05, decay_days=7),
        IntentSignalConfig("social_share", weight=0.10, decay_days=7),

        # Content signals (10% total)
        IntentSignalConfig("whitepaper_download", weight=0.15, decay_days=21),
        IntentSignalConfig("webinar_attendance", weight=0.20, decay_days=14),
        IntentSignalConfig("video_watch", weight=0.05, decay_days=14),
    ])

    # Firmographic fit multiplier (1.0 = no change, 1.5 = 50% boost)
    icp_fit_multiplier: float = 1.3

    # Recency boost (more recent = higher score)
    recency_boost_enabled: bool = True

    # Minimum score to consider "high intent"
    high_intent_threshold: float = 70.0
    medium_intent_threshold: float = 40.0


class IntentScorer:
    """
    Calculate buying intent scores based on multi-channel signals.

    Supports configurable scoring rules, time decay, and ICP fit multipliers.
    """

    def __init__(self, config: Optional[IntentScoringConfig] = None):
        """
        Initialize intent scorer.

        Parameters
        ----------
        config : IntentScoringConfig, optional
            Scoring configuration. Uses defaults if not provided.
        """
        self.config = config or IntentScoringConfig()
        self.signal_weights = {s.name: s for s in self.config.signals}

    def calculate_intent_score(
        self,
        events: List[Dict[str, Any]],
        firmographic_fit: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate intent score based on events and firmographic fit.

        Parameters
        ----------
        events : list of dict
            List of events (email, web, social, etc.)
            Each event should have:
            - signal_type: str
            - timestamp: datetime
            - value: float (optional, defaults to 1.0)
            - metadata: dict (optional)
        firmographic_fit : dict, optional
            Firmographic fit data for ICP matching

        Returns
        -------
        dict
            {
                'score': float (0-100),
                'level': str ('high', 'medium', 'low'),
                'signals_detected': list,
                'signal_breakdown': dict,
                'recency_score': float,
                'firmographic_boost': float
            }
        """
        now = datetime.now(timezone.utc)

        # Group events by signal type
        signal_scores = {}
        signals_detected = []

        for event in events:
            signal_type = event.get('signal_type')
            if signal_type not in self.signal_weights:
                # Unknown signal type, skip
                continue

            signal_config = self.signal_weights[signal_type]
            event_time = event.get('timestamp')
            event_value = event.get('value', 1.0)

            # Apply time decay if configured
            score = signal_config.weight * 100  # Convert to 0-100 scale

            if signal_config.decay_days and event_time:
                days_ago = (now - event_time).days
                if days_ago > signal_config.decay_days:
                    # Exponential decay
                    decay_factor = 0.5 ** (days_ago / signal_config.decay_days)
                    score *= decay_factor

            # Apply threshold if configured
            if signal_config.threshold and event_value < signal_config.threshold:
                continue

            # Apply event value multiplier
            score *= event_value

            # Accumulate
            if signal_type not in signal_scores:
                signal_scores[signal_type] = 0.0
                signals_detected.append(signal_type)

            signal_scores[signal_type] += score

        # Sum all signal scores
        base_score = sum(signal_scores.values())

        # Cap individual signals to prevent over-weighting
        base_score = min(100, base_score)

        # Apply firmographic fit multiplier
        firmographic_boost = 0.0
        if firmographic_fit:
            fit_score = self._calculate_firmographic_fit(firmographic_fit)
            firmographic_boost = fit_score * (self.config.icp_fit_multiplier - 1.0) * 100
            base_score = min(100, base_score * (1 + firmographic_boost / 100))

        # Apply recency boost (recent activity = higher score)
        recency_score = 0.0
        if self.config.recency_boost_enabled and events:
            recency_score = self._calculate_recency_boost(events, now)
            base_score = min(100, base_score + recency_score)

        # Determine intent level
        if base_score >= self.config.high_intent_threshold:
            level = 'high'
        elif base_score >= self.config.medium_intent_threshold:
            level = 'medium'
        else:
            level = 'low'

        return {
            'score': round(base_score, 2),
            'level': level,
            'signals_detected': signals_detected,
            'signal_breakdown': signal_scores,
            'recency_score': round(recency_score, 2),
            'firmographic_boost': round(firmographic_boost, 2)
        }

    def _calculate_firmographic_fit(self, firmographic_data: Dict[str, Any]) -> float:
        """
        Calculate firmographic fit score (0.0 to 1.0).

        This is a simple implementation. You should customize based on your ICP.
        """
        fit_score = 0.0
        checks = 0

        # Example ICP criteria
        # Customize these based on your ideal customer profile

        # Employee count (500-5000 = ideal)
        employee_count = firmographic_data.get('employee_count')
        if employee_count:
            checks += 1
            if 500 <= employee_count <= 5000:
                fit_score += 1.0
            elif 100 <= employee_count < 500 or 5000 < employee_count <= 10000:
                fit_score += 0.5

        # Industry match
        industry = firmographic_data.get('industry', '').lower()
        if industry:
            checks += 1
            ideal_industries = ['saas', 'technology', 'software', 'fintech']
            if any(ind in industry for ind in ideal_industries):
                fit_score += 1.0

        # Funding/revenue (indicates budget)
        revenue = firmographic_data.get('revenue')
        funding = firmographic_data.get('funding')
        if revenue or funding:
            checks += 1
            if revenue and revenue > 10_000_000:  # $10M+
                fit_score += 1.0
            elif funding and funding > 5_000_000:  # $5M+
                fit_score += 0.8

        # Technology stack (uses complementary tech)
        technologies = firmographic_data.get('technologies', [])
        if technologies:
            checks += 1
            complementary_tech = ['salesforce', 'hubspot', 'segment', 'snowflake']
            if any(tech.lower() in str(technologies).lower() for tech in complementary_tech):
                fit_score += 1.0

        return fit_score / checks if checks > 0 else 0.5

    def _calculate_recency_boost(
        self,
        events: List[Dict[str, Any]],
        now: datetime
    ) -> float:
        """
        Calculate recency boost based on recent activity.

        More recent and frequent activity = higher boost (max +10 points)
        """
        if not events:
            return 0.0

        # Get most recent event
        events_with_time = [e for e in events if e.get('timestamp')]
        if not events_with_time:
            return 0.0

        most_recent = max(events_with_time, key=lambda e: e['timestamp'])
        days_since = (now - most_recent['timestamp']).days

        # Recency scoring
        if days_since == 0:  # Today
            recency_boost = 10.0
        elif days_since <= 3:
            recency_boost = 7.0
        elif days_since <= 7:
            recency_boost = 5.0
        elif days_since <= 14:
            recency_boost = 3.0
        elif days_since <= 30:
            recency_boost = 1.0
        else:
            recency_boost = 0.0

        return recency_boost

    def identify_buying_stage(self, intent_data: Dict[str, Any]) -> str:
        """
        Identify buying stage based on intent signals.

        Returns:
            'awareness', 'consideration', 'decision', or 'unknown'
        """
        signals = intent_data.get('signals_detected', [])

        # Decision stage signals
        decision_signals = ['demo_request', 'pricing_page_visit', 'email_reply']
        if any(s in signals for s in decision_signals):
            return 'decision'

        # Consideration stage signals
        consideration_signals = [
            'case_study_view', 'product_page_visit', 'whitepaper_download',
            'webinar_attendance', 'return_visitor'
        ]
        if any(s in signals for s in consideration_signals):
            return 'consideration'

        # Awareness stage signals
        awareness_signals = [
            'email_open', 'social_share', 'video_watch', 'linkedin_engagement'
        ]
        if any(s in signals for s in awareness_signals):
            return 'awareness'

        return 'unknown'

    def get_next_best_action(self, intent_data: Dict[str, Any]) -> str:
        """
        Recommend next best action based on intent score and signals.

        Returns:
            Recommended action string
        """
        score = intent_data.get('score', 0)
        level = intent_data.get('level', 'low')
        signals = intent_data.get('signals_detected', [])
        stage = self.identify_buying_stage(intent_data)

        # High intent + decision stage
        if level == 'high' and stage == 'decision':
            if 'demo_request' in signals:
                return "Schedule demo immediately - they've requested it"
            elif 'pricing_page_visit' in signals:
                return "Sales call to discuss pricing and close deal"
            else:
                return "Direct sales outreach - high intent, ready to buy"

        # High intent + consideration stage
        elif level == 'high' and stage == 'consideration':
            return "Share case study and propose demo to move to decision stage"

        # Medium intent
        elif level == 'medium':
            if 'whitepaper_download' in signals:
                return "Follow up on whitepaper with relevant case study"
            elif 'product_page_visit' in signals:
                return "Share product walkthrough video"
            else:
                return "Nurture with educational content"

        # Low intent
        else:
            return "Continue awareness-building with blog posts and social engagement"
