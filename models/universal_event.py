"""
Universal event model for any data source (email, web, social, enrichment APIs).

This provides a normalized way to ingest ANY type of customer interaction or signal
into the knowledge graph.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Type of customer interaction or signal"""
    EMAIL = "email"
    WEB_VISIT = "web_visit"
    SOCIAL_ENGAGEMENT = "social_engagement"
    SOCIAL_POST = "social_post"
    ENRICHMENT = "enrichment"
    FORM_SUBMISSION = "form_submission"
    CONTENT_DOWNLOAD = "content_download"
    AD_INTERACTION = "ad_interaction"
    CRM_UPDATE = "crm_update"
    CUSTOM = "custom"


class EventDirection(str, Enum):
    """Direction of the interaction"""
    INBOUND = "inbound"    # They initiated (visited our site, sent email, etc.)
    OUTBOUND = "outbound"  # We initiated (sent email, ad impression, etc.)
    MUTUAL = "mutual"      # Both parties (meeting, call, etc.)


class UniversalEvent(BaseModel):
    """
    Universal event model that represents ANY customer interaction or signal.

    This model can represent:
    - Email communications (already supported)
    - Website visits and page views
    - Social media engagements (likes, comments, shares)
    - Form submissions and content downloads
    - Ad clicks and impressions
    - CRM updates and enrichment data
    - Custom events from any source

    All events are normalized into this structure for consistent
    knowledge graph ingestion.
    """

    # Core identifiers
    event_id: str = Field(..., description="Unique event ID from source system")
    event_type: EventType = Field(..., description="Type of event")
    source_system: str = Field(..., description="Source system: gmail, google-analytics, linkedin, etc.")

    # Timing
    timestamp: datetime = Field(..., description="When the event occurred")

    # Actor (who performed the action)
    actor_email: Optional[str] = Field(None, description="Email of person who performed action")
    actor_name: Optional[str] = Field(None, description="Name of person who performed action")
    actor_id: Optional[str] = Field(None, description="ID in source system (user_id, visitor_id, etc.)")

    # Target (what was acted upon)
    target_type: Optional[str] = Field(None, description="Type of target: page, post, email, content, etc.")
    target_id: Optional[str] = Field(None, description="ID of target in source system")
    target_name: Optional[str] = Field(None, description="Human-readable name of target")
    target_url: Optional[str] = Field(None, description="URL if applicable")

    # Event details
    action: str = Field(..., description="Action performed: visited, clicked, liked, commented, downloaded, etc.")
    direction: EventDirection = Field(..., description="Direction of interaction")

    # Content
    title: Optional[str] = Field(None, description="Title/subject of the event")
    description: Optional[str] = Field(None, description="Description or body content")
    content_text: Optional[str] = Field(None, description="Full text content if available")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata specific to event type"
    )

    # Account mapping (enriched after ingestion)
    account_name: Optional[str] = Field(None, description="Matched account name")
    account_domain: Optional[str] = Field(None, description="Primary account domain")

    # Scoring/analysis
    engagement_score: Optional[float] = Field(None, description="Engagement score 0-100")
    intent_signals: Optional[List[str]] = Field(None, description="Intent signals detected")
    sentiment: Optional[str] = Field(None, description="Sentiment: positive, neutral, negative")

    # Raw data
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw event data for debugging")

    def to_episode_content(self) -> str:
        """
        Format event for Graphiti episode ingestion.

        Returns a structured text representation optimized for
        LLM entity and relationship extraction.
        """
        # Build context based on event type
        context_lines = []

        # Header
        context_lines.append(f"{self.event_type.value.replace('_', ' ').title()} Event")
        context_lines.append("=" * 50)

        # Actor information
        if self.actor_name or self.actor_email:
            actor = self.actor_name or self.actor_email
            context_lines.append(f"Actor: {actor}")
            if self.actor_email and self.actor_name:
                context_lines.append(f"Email: {self.actor_email}")

        # Event details
        context_lines.append(f"Action: {self.action}")
        context_lines.append(f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        context_lines.append(f"Direction: {self.direction.value}")

        # Account context
        if self.account_name:
            context_lines.append(f"Account: {self.account_name}")

        # Target information
        if self.target_name:
            context_lines.append(f"Target: {self.target_name}")
        if self.target_url:
            context_lines.append(f"URL: {self.target_url}")

        # Title/subject
        if self.title:
            context_lines.append(f"Title: {self.title}")

        # Content
        if self.content_text or self.description:
            context_lines.append("")
            context_lines.append("Content:")
            context_lines.append("-" * 50)
            content = self.content_text or self.description or ""
            context_lines.append(content[:5000])  # Limit content length

        # Metadata highlights
        if self.metadata:
            context_lines.append("")
            context_lines.append("Additional Details:")
            for key, value in list(self.metadata.items())[:10]:  # Limit metadata items
                if isinstance(value, (str, int, float, bool)):
                    context_lines.append(f"  {key}: {value}")

        # Intent signals
        if self.intent_signals:
            context_lines.append("")
            context_lines.append("Intent Signals: " + ", ".join(self.intent_signals))

        # Sentiment
        if self.sentiment:
            context_lines.append(f"Sentiment: {self.sentiment}")

        content = "\n".join(context_lines)

        # Truncate if too long
        if len(content) > 10000:
            content = content[:9500] + "\n\n[Content truncated...]"

        return content

    @property
    def actor_domain(self) -> Optional[str]:
        """Extract domain from actor email"""
        if self.actor_email and '@' in self.actor_email:
            return self.actor_email.split('@')[1].lower()
        return None

    @classmethod
    def from_email(cls, email: 'Email') -> 'UniversalEvent':
        """
        Convert an Email object to a UniversalEvent.

        This maintains backward compatibility with existing email adapters.
        """
        from models.email import Email

        return cls(
            event_id=email.message_id,
            event_type=EventType.EMAIL,
            source_system=email.provider,
            timestamp=email.timestamp,
            actor_email=email.from_email,
            actor_name=email.from_name,
            target_type="email_recipients",
            target_name=", ".join(email.to_emails[:3]),
            action="sent_email",
            direction=EventDirection(email.direction.value),
            title=email.subject,
            content_text=email.body_text,
            metadata={
                "thread_id": email.thread_id,
                "to_emails": email.to_emails,
                "cc_emails": email.cc_emails or [],
                "is_reply": email.is_reply,
                "has_attachments": email.has_attachments,
                "labels": email.labels or []
            },
            account_name=email.account_name,
            account_domain=email.account_domain,
            raw_data=email.raw_data
        )


class WebVisitEvent(BaseModel):
    """Specialized model for web analytics events"""
    visitor_id: str
    session_id: Optional[str] = None
    page_url: str
    page_title: Optional[str] = None
    referrer: Optional[str] = None
    duration_seconds: Optional[float] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    country: Optional[str] = None

    def to_universal_event(
        self,
        timestamp: datetime,
        visitor_email: Optional[str] = None,
        visitor_name: Optional[str] = None,
        account_name: Optional[str] = None
    ) -> UniversalEvent:
        """Convert to UniversalEvent"""
        intent_signals = []

        # Detect intent signals from URL patterns
        url_lower = self.page_url.lower()
        if any(x in url_lower for x in ['/pricing', '/price', '/plans']):
            intent_signals.append("pricing_interest")
        if any(x in url_lower for x in ['/demo', '/trial', '/signup']):
            intent_signals.append("high_intent")
        if any(x in url_lower for x in ['/product', '/features', '/solutions']):
            intent_signals.append("product_research")
        if any(x in url_lower for x in ['/case-study', '/customer', '/testimonial']):
            intent_signals.append("validation_seeking")

        # Engagement score based on duration
        engagement_score = None
        if self.duration_seconds:
            # 0-30s = low, 30-120s = medium, 120s+ = high
            engagement_score = min(100, (self.duration_seconds / 120) * 100)

        return UniversalEvent(
            event_id=f"web_{self.visitor_id}_{timestamp.timestamp()}",
            event_type=EventType.WEB_VISIT,
            source_system="web_analytics",
            timestamp=timestamp,
            actor_email=visitor_email,
            actor_name=visitor_name,
            actor_id=self.visitor_id,
            target_type="web_page",
            target_url=self.page_url,
            target_name=self.page_title or self.page_url,
            action="visited_page",
            direction=EventDirection.INBOUND,
            title=f"Visited: {self.page_title or self.page_url}",
            description=f"Page visit from {self.referrer or 'direct'}, duration: {self.duration_seconds or 0}s",
            metadata={
                "session_id": self.session_id,
                "referrer": self.referrer,
                "duration_seconds": self.duration_seconds,
                "utm_source": self.utm_source,
                "utm_medium": self.utm_medium,
                "utm_campaign": self.utm_campaign,
                "device_type": self.device_type,
                "browser": self.browser,
                "country": self.country
            },
            account_name=account_name,
            engagement_score=engagement_score,
            intent_signals=intent_signals
        )


class SocialEngagementEvent(BaseModel):
    """Specialized model for social media engagement events"""
    platform: str  # linkedin, twitter, facebook, etc.
    engagement_type: str  # like, comment, share, follow, view, etc.
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    post_text: Optional[str] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    engagement_text: Optional[str] = None  # For comments

    def to_universal_event(
        self,
        timestamp: datetime,
        actor_email: Optional[str] = None,
        actor_name: Optional[str] = None,
        account_name: Optional[str] = None
    ) -> UniversalEvent:
        """Convert to UniversalEvent"""
        intent_signals = []

        # High-value engagement signals
        if self.engagement_type in ['share', 'repost', 'retweet']:
            intent_signals.append("high_engagement")
        if self.engagement_type == 'comment':
            intent_signals.append("active_discussion")
        if self.engagement_type == 'follow':
            intent_signals.append("ongoing_interest")

        # Engagement scoring
        engagement_score_map = {
            'view': 10,
            'like': 30,
            'comment': 60,
            'share': 80,
            'follow': 90
        }
        engagement_score = engagement_score_map.get(self.engagement_type.lower(), 20)

        return UniversalEvent(
            event_id=f"{self.platform}_{self.engagement_type}_{timestamp.timestamp()}",
            event_type=EventType.SOCIAL_ENGAGEMENT,
            source_system=self.platform,
            timestamp=timestamp,
            actor_email=actor_email,
            actor_name=actor_name,
            target_type="social_post",
            target_id=self.post_id,
            target_url=self.post_url,
            target_name=f"{self.platform} post",
            action=self.engagement_type,
            direction=EventDirection.INBOUND,
            title=f"{self.engagement_type.title()} on {self.platform}",
            description=self.post_text,
            content_text=self.engagement_text,
            metadata={
                "platform": self.platform,
                "post_id": self.post_id,
                "author_id": self.author_id,
                "author_name": self.author_name
            },
            account_name=account_name,
            engagement_score=engagement_score,
            intent_signals=intent_signals
        )
