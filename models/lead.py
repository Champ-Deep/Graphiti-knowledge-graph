"""
Lead data model for n8n email automation workflow integration.

This model represents a lead/contact from the LakeB2B contact form,
replacing the Pinecone vector storage with Graphiti knowledge graph.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LeadStatus(str, Enum):
    """Lead processing status"""
    NEW = "new"
    EXISTING = "existing"
    ENRICHED = "enriched"
    EMAIL_SENT = "email_sent"
    REPLIED = "replied"
    CONVERTED = "converted"


class LeadSource(str, Enum):
    """Source of the lead"""
    LAKEB2B_FORM = "lakeb2b_form"
    WEBSITE = "website"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    IMPORT = "import"
    OTHER = "other"


class Lead(BaseModel):
    """
    Lead model for the email automation workflow.

    This replaces Pinecone's flat vector metadata with a structured
    model that integrates with Graphiti's knowledge graph.
    """

    # Identifiers (same as Pinecone lookup_id logic)
    lookup_id: str = Field(..., description="Primary lookup ID (email or phone)")

    # Contact information
    full_name: str = Field(..., description="Full name of the lead")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    email: str = Field(..., description="Normalized email address")
    phone: Optional[str] = Field(None, description="Normalized phone (digits only)")

    # Company information
    company: Optional[str] = Field(None, description="Company/organization name")
    title: Optional[str] = Field(None, description="Job title")
    industry: Optional[str] = Field(None, description="Industry vertical")

    # Form submission data
    inquiry_type: Optional[str] = Field(None, description="Type of inquiry from form")
    comments: Optional[str] = Field(None, description="Comments/message from form")

    # Status tracking
    status: LeadStatus = Field(default=LeadStatus.NEW, description="Lead status")
    source: LeadSource = Field(default=LeadSource.LAKEB2B_FORM, description="Lead source")

    # Enrichment data (from Perplexity/research)
    research_summary: Optional[List[str]] = Field(None, description="Research findings")
    enrichment_sources: Optional[List[str]] = Field(None, description="Source URLs")

    # Email tracking
    email_sent: bool = Field(default=False, description="Has outreach email been sent?")
    email_subject: Optional[str] = Field(None, description="Subject of sent email")
    email_sent_at: Optional[datetime] = Field(None, description="When email was sent")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Graph references (populated after ingestion)
    graph_node_id: Optional[str] = Field(None, description="Graphiti node UUID")
    account_group_id: Optional[str] = Field(None, description="Account group in graph")

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower().strip() if v else ""

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        """Normalize phone to digits only"""
        if not v:
            return None
        import re
        return re.sub(r'\D', '', str(v))

    def to_episode_content(self) -> str:
        """
        Format lead for Graphiti episode ingestion.

        This creates a structured text that the LLM can extract
        entities and relationships from.
        """
        content = f"""New Lead Contact Form Submission
================================
Source: LakeB2B Contact Form
Submitted At: {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Contact Information:
-------------------
Name: {self.full_name}
Email: {self.email}
Phone: {self.phone or 'Not provided'}
Company: {self.company or 'Not provided'}
Title: {self.title or 'Not provided'}
Industry: {self.industry or 'Not provided'}

Inquiry Details:
---------------
Type: {self.inquiry_type or 'General inquiry'}
Comments: {self.comments or 'No comments provided'}

Lead Status: {self.status.value}
Lead Source: {self.source.value}
"""

        # Add research summary if available
        if self.research_summary:
            content += "\nResearch Findings:\n------------------\n"
            for finding in self.research_summary:
                content += f"- {finding}\n"

        return content

    def to_enrichment_episode(self) -> str:
        """
        Format enrichment data as a separate episode.

        This is called after Perplexity research to add
        enriched information to the knowledge graph.
        """
        if not self.research_summary:
            return ""

        content = f"""Lead Enrichment Update
=====================
Contact: {self.full_name} <{self.email}>
Enriched At: {self.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Research Findings:
-----------------
"""
        for finding in self.research_summary:
            content += f"- {finding}\n"

        if self.enrichment_sources:
            content += "\nSources:\n--------\n"
            for source in self.enrichment_sources:
                content += f"- {source}\n"

        return content


class LeadLookupRequest(BaseModel):
    """Request model for looking up a lead"""
    email: Optional[str] = Field(None, description="Email to look up")
    phone: Optional[str] = Field(None, description="Phone to look up")
    lookup_id: Optional[str] = Field(None, description="Direct lookup ID")

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else None


class LeadLookupResponse(BaseModel):
    """Response model for lead lookup"""
    found: bool = Field(..., description="Whether lead was found")
    lead: Optional[Lead] = Field(None, description="Lead data if found")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context from graph")
    message: Optional[str] = Field(None, description="Status message")


class LeadCreateRequest(BaseModel):
    """Request model for creating a new lead (from n8n Format Data Script)"""
    # From n8n workflow
    full_name: str
    email_norm: str = Field(..., alias="email")
    phone_norm: Optional[str] = Field(None, alias="phone")
    lookup_id: Optional[str] = None

    # Optional form fields
    inquiry_type: Optional[str] = Field(None, alias="Inquiry Type")
    comments: Optional[str] = Field(None, alias="Comments")

    # Company info if available
    company: Optional[str] = None
    title: Optional[str] = None

    class Config:
        populate_by_name = True


class LeadEnrichRequest(BaseModel):
    """Request model for enriching a lead with research data"""
    lookup_id: str
    research_summary: List[str] = Field(..., description="Research findings from Perplexity")
    sources: Optional[List[str]] = Field(None, description="Source URLs")
    email_subject: Optional[str] = Field(None, description="Subject of outreach email")
    email_sent: bool = Field(default=False, description="Whether email was sent")


class LeadContextResponse(BaseModel):
    """Rich context about a lead for the Prompt Writer agents"""
    lead: Lead

    # From knowledge graph
    previous_communications: List[Dict[str, Any]] = Field(default_factory=list)
    personal_details: List[Dict[str, Any]] = Field(default_factory=list)
    discussed_topics: List[Dict[str, Any]] = Field(default_factory=list)
    team_contacts: List[Dict[str, Any]] = Field(default_factory=list)
    related_contacts: List[Dict[str, Any]] = Field(default_factory=list)

    # Summary for prompt generation
    context_summary: Optional[str] = Field(None, description="LLM-generated context summary")
