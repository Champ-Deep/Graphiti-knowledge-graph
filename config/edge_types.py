"""
Custom edge (relationship) types for email knowledge graph.

These define the relationships between entities that can be extracted.
"""
from typing import Optional
from pydantic import BaseModel, Field


class SentEmailTo(BaseModel):
    """Relationship: Someone sent an email to someone else"""
    subject: Optional[str] = Field(None, description="Email subject line")


class WorksAt(BaseModel):
    """Relationship: A contact works at an account/company"""
    title: Optional[str] = Field(None, description="Job title at the company")
    department: Optional[str] = Field(None, description="Department")


class ReportsTo(BaseModel):
    """Relationship: A contact reports to another contact (org structure)"""
    relationship: Optional[str] = Field(None, description="Nature of reporting relationship")


class HasPersonalDetail(BaseModel):
    """Relationship: A contact has a personal detail associated with them"""
    mentioned_date: Optional[str] = Field(None, description="When this was mentioned")


class DiscussedTopic(BaseModel):
    """Relationship: A communication discussed a specific topic"""
    context: Optional[str] = Field(None, description="Context of the discussion")


class RespondedVia(BaseModel):
    """Relationship: A contact responded via a specific channel"""
    response_time_hours: Optional[float] = Field(None, description="Hours until response")


class InterestedIn(BaseModel):
    """Relationship: A contact expressed interest in something"""
    level: Optional[str] = Field(None, description="Interest level: high, medium, low")


class MentionedBy(BaseModel):
    """Relationship: A topic or person was mentioned by someone"""
    sentiment: Optional[str] = Field(None, description="Sentiment when mentioned")


class VisitedPage(BaseModel):
    """Relationship: A contact visited a web page"""
    duration_seconds: Optional[float] = Field(None, description="Time spent on page")
    visit_count: Optional[int] = Field(None, description="Number of visits to this page")


class UsesTechnology(BaseModel):
    """Relationship: An account uses a specific technology"""
    confidence: Optional[str] = Field(None, description="Confidence level: confirmed, likely, possible")
    detected_date: Optional[str] = Field(None, description="When this was detected")


class HasSocialProfile(BaseModel):
    """Relationship: A contact or account has a social media profile"""
    follower_count: Optional[int] = Field(None, description="Number of followers")
    verified: Optional[bool] = Field(None, description="Is the profile verified?")


class DownloadedContent(BaseModel):
    """Relationship: A contact downloaded a content asset"""
    downloaded_date: Optional[str] = Field(None, description="When it was downloaded")


class EngagedWith(BaseModel):
    """Relationship: A contact engaged with content (social post, email, etc.)"""
    engagement_type: Optional[str] = Field(
        None,
        description="Type: like, comment, share, click, open, reply"
    )
    engagement_score: Optional[float] = Field(None, description="Engagement score 0-100")


class HasFirmographic(BaseModel):
    """Relationship: An account has a firmographic attribute"""
    last_updated: Optional[str] = Field(None, description="When this was last updated")
    source: Optional[str] = Field(None, description="Data source")


class ShowsIntent(BaseModel):
    """Relationship: A contact or account shows a buying intent signal"""
    signal_strength: Optional[str] = Field(None, description="Strength: high, medium, low")
    detected_date: Optional[str] = Field(None, description="When signal was detected")


class ResearchedTopic(BaseModel):
    """Relationship: A contact researched a specific topic"""
    page_views: Optional[int] = Field(None, description="Number of related pages viewed")
    total_time_seconds: Optional[float] = Field(None, description="Total time researching")


class CompetesWith(BaseModel):
    """Relationship: An account competes with another account"""
    market_overlap: Optional[str] = Field(None, description="Market overlap description")


# Edge types dictionary for Graphiti
EDGE_TYPES = {
    'SENT_EMAIL_TO': SentEmailTo,
    'WORKS_AT': WorksAt,
    'REPORTS_TO': ReportsTo,
    'HAS_PERSONAL_DETAIL': HasPersonalDetail,
    'DISCUSSED_TOPIC': DiscussedTopic,
    'RESPONDED_VIA': RespondedVia,
    'INTERESTED_IN': InterestedIn,
    'MENTIONED_BY': MentionedBy,
    'VISITED_PAGE': VisitedPage,
    'USES_TECHNOLOGY': UsesTechnology,
    'HAS_SOCIAL_PROFILE': HasSocialProfile,
    'DOWNLOADED_CONTENT': DownloadedContent,
    'ENGAGED_WITH': EngagedWith,
    'HAS_FIRMOGRAPHIC': HasFirmographic,
    'SHOWS_INTENT': ShowsIntent,
    'RESEARCHED_TOPIC': ResearchedTopic,
    'COMPETES_WITH': CompetesWith,
}

# Edge type mapping: defines which edge types can connect which node types
# Format: (source_type, target_type): [list of allowed edge types]
EDGE_TYPE_MAP = {
    # Existing email relationships
    ('TeamMember', 'Contact'): ['SENT_EMAIL_TO'],
    ('Contact', 'TeamMember'): ['SENT_EMAIL_TO'],
    ('Contact', 'Account'): ['WORKS_AT'],
    ('Contact', 'Contact'): ['REPORTS_TO'],
    ('Contact', 'PersonalDetail'): ['HAS_PERSONAL_DETAIL'],
    ('Contact', 'Topic'): ['DISCUSSED_TOPIC', 'INTERESTED_IN', 'RESEARCHED_TOPIC'],
    ('TeamMember', 'Topic'): ['DISCUSSED_TOPIC'],
    ('Communication', 'Topic'): ['DISCUSSED_TOPIC'],
    ('Contact', 'Communication'): ['RESPONDED_VIA'],

    # Web analytics relationships
    ('Contact', 'WebPage'): ['VISITED_PAGE'],
    ('Account', 'WebPage'): ['VISITED_PAGE'],

    # Technology relationships
    ('Account', 'Technology'): ['USES_TECHNOLOGY'],

    # Social media relationships
    ('Contact', 'SocialProfile'): ['HAS_SOCIAL_PROFILE'],
    ('Account', 'SocialProfile'): ['HAS_SOCIAL_PROFILE'],

    # Content relationships
    ('Contact', 'ContentAsset'): ['DOWNLOADED_CONTENT', 'ENGAGED_WITH'],

    # Firmographic relationships
    ('Account', 'Firmographic'): ['HAS_FIRMOGRAPHIC'],

    # Intent signal relationships
    ('Contact', 'IntentSignal'): ['SHOWS_INTENT'],
    ('Account', 'IntentSignal'): ['SHOWS_INTENT'],

    # Competitive relationships
    ('Account', 'Account'): ['COMPETES_WITH'],
}
