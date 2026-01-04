"""
Custom entity types for email knowledge graph extraction.

These Pydantic models guide the LLM to extract specific entity types
from email content, improving extraction accuracy for sales/marketing use cases.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class Contact(BaseModel):
    """A person at a target account (prospect, customer, etc.)"""
    name: str = Field(..., description="Full name of the contact")
    email: Optional[str] = Field(None, description="Email address")
    title: Optional[str] = Field(None, description="Job title or role")
    department: Optional[str] = Field(None, description="Department they work in")


class Account(BaseModel):
    """A target company/account (MQA - Marketing Qualified Account)"""
    name: str = Field(..., description="Company or organization name")
    domain: Optional[str] = Field(None, description="Primary email domain")
    industry: Optional[str] = Field(None, description="Industry vertical")


class TeamMember(BaseModel):
    """A member of your internal sales/marketing team"""
    name: str = Field(..., description="Full name of team member")
    email: Optional[str] = Field(None, description="Email address")
    role: Optional[str] = Field(None, description="Role: SDR, AE, CSM, Marketing, etc.")


class PersonalDetail(BaseModel):
    """Personal information mentioned about a contact.

    This captures personal tidbits like family info, hobbies, interests,
    preferences, etc. that can help build rapport.
    """
    category: str = Field(
        ...,
        description="Category of detail: family, hobby, interest, preference, travel, sports, etc."
    )
    detail: str = Field(..., description="The specific personal detail mentioned")


class Topic(BaseModel):
    """A discussion topic or business theme"""
    name: str = Field(..., description="Name of the topic or theme")
    category: Optional[str] = Field(
        None,
        description="Category: pricing, product, support, partnership, contract, demo, etc."
    )


class Communication(BaseModel):
    """A communication event or interaction"""
    channel: str = Field(
        ...,
        description="Channel: email, phone, linkedin, meeting, conference, slack"
    )
    direction: str = Field(
        ...,
        description="Direction: outbound (we initiated) or inbound (they initiated)"
    )
    sentiment: Optional[str] = Field(
        None,
        description="Sentiment: positive, neutral, negative"
    )


class WebPage(BaseModel):
    """A web page visited by a contact"""
    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(None, description="Page title")
    category: Optional[str] = Field(
        None,
        description="Page category: pricing, product, blog, case-study, demo, etc."
    )


class Technology(BaseModel):
    """A technology or tool used by an account"""
    name: str = Field(..., description="Technology name")
    category: Optional[str] = Field(
        None,
        description="Category: CRM, marketing-automation, analytics, infrastructure, etc."
    )
    vendor: Optional[str] = Field(None, description="Technology vendor/provider")


class SocialProfile(BaseModel):
    """A social media profile"""
    platform: str = Field(..., description="Platform: linkedin, twitter, facebook, etc.")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    handle: Optional[str] = Field(None, description="Username/handle")


class ContentAsset(BaseModel):
    """A piece of content (whitepaper, case study, blog post, etc.)"""
    title: str = Field(..., description="Content title")
    content_type: Optional[str] = Field(
        None,
        description="Type: whitepaper, case-study, blog-post, video, webinar, etc."
    )
    topic: Optional[str] = Field(None, description="Main topic or theme")


class Firmographic(BaseModel):
    """Firmographic data about an account"""
    attribute: str = Field(
        ...,
        description="Attribute: employee_count, revenue, funding, growth_rate, etc."
    )
    value: str = Field(..., description="Attribute value")
    source: Optional[str] = Field(None, description="Data source")


class IntentSignal(BaseModel):
    """A buying intent signal"""
    signal_type: str = Field(
        ...,
        description="Signal type: pricing_visit, demo_request, competitor_research, etc."
    )
    strength: Optional[str] = Field(
        None,
        description="Signal strength: high, medium, low"
    )
    context: Optional[str] = Field(None, description="Additional context")


# Entity types dictionary for Graphiti
ENTITY_TYPES = {
    'Contact': Contact,
    'Account': Account,
    'TeamMember': TeamMember,
    'PersonalDetail': PersonalDetail,
    'Topic': Topic,
    'Communication': Communication,
    'WebPage': WebPage,
    'Technology': Technology,
    'SocialProfile': SocialProfile,
    'ContentAsset': ContentAsset,
    'Firmographic': Firmographic,
    'IntentSignal': IntentSignal,
}
