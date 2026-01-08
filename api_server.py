"""
API Server for Graphiti Knowledge Graph

Provides REST endpoints for:
1. CEO WhatsApp Assistant integration (original)
2. n8n Email Automation workflow integration (new)

Replaces Pinecone as the knowledge storage backend.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import get_settings
from services.graphiti_service import GraphitiService
from middleware.auth import require_api_key
from models.lead import (
    Lead,
    LeadStatus,
    LeadSource,
    LeadLookupRequest,
    LeadLookupResponse,
    LeadCreateRequest,
    LeadEnrichRequest,
    LeadContextResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instance
graphiti_service: Optional[GraphitiService] = None

# In-memory lead cache (in production, consider Redis)
# This provides fast lookups while graph handles relationships
lead_cache: Dict[str, Lead] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global graphiti_service
    settings = get_settings()

    graphiti_service = GraphitiService(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        openai_api_key=settings.openai_api_key,
        openai_base_url=settings.openai_base_url,
        model_name=settings.model_name,
    )

    await graphiti_service.connect()
    logger.info("Knowledge graph service connected")

    yield

    await graphiti_service.disconnect()
    logger.info("Knowledge graph service disconnected")


app = FastAPI(
    title="Graphiti Knowledge Graph API",
    description="""
    Knowledge Graph API for intelligent email automation.

    ## Features
    - Lead lookup and management (replaces Pinecone)
    - Rich context retrieval for personalization
    - Relationship and communication tracking
    - Integration with n8n workflows

    ## Authentication
    Protected endpoints require X-API-Key header.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class QueryRequest(BaseModel):
    account: str
    query: str
    num_results: int = 20


class QueryResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "2.0.0"
    neo4j_connected: bool = True


# === Health & Status Endpoints ===

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (no auth required)"""
    return HealthResponse(
        status="healthy",
        service="graphiti-knowledge-graph",
        version="2.0.0",
        neo4j_connected=graphiti_service is not None and graphiti_service.client is not None,
    )


# === n8n Lead Integration Endpoints ===

@app.post("/api/leads/lookup", response_model=LeadLookupResponse)
async def lookup_lead(
    request: LeadLookupRequest,
    api_key: str = Depends(require_api_key),
):
    """
    Look up a lead by email, phone, or lookup_id.

    This replaces the Pinecone fetch operation in the n8n workflow.
    Returns the lead data and rich context from the knowledge graph.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Determine lookup ID
    lookup_id = request.lookup_id or request.email or request.phone
    if not lookup_id:
        raise HTTPException(
            status_code=400,
            detail="Must provide email, phone, or lookup_id"
        )

    lookup_id = lookup_id.lower().strip()

    # Check cache first
    if lookup_id in lead_cache:
        lead = lead_cache[lookup_id]
        logger.info(f"Lead found in cache: {lookup_id}")

        # Get additional context from graph
        context = await _get_lead_context(lead)

        return LeadLookupResponse(
            found=True,
            lead=lead,
            context=context,
            message="Lead found (existing customer)"
        )

    # Search in knowledge graph
    try:
        # Search for contact by email or phone
        search_query = f"Find contact with email {request.email}" if request.email else f"Find contact with phone {request.phone}"
        results = await graphiti_service.search_account(
            account_name="lakeb2b",  # Default account for leads
            query=search_query,
            num_results=5,
        )

        # Check if we found a matching contact
        matching_nodes = [
            n for n in results.get('nodes', [])
            if _node_matches_lookup(n, lookup_id)
        ]

        if matching_nodes:
            # Reconstruct lead from graph node
            node = matching_nodes[0]
            lead = _lead_from_node(node, lookup_id)
            lead_cache[lookup_id] = lead

            context = await _get_lead_context(lead)

            return LeadLookupResponse(
                found=True,
                lead=lead,
                context=context,
                message="Lead found in knowledge graph"
            )

    except Exception as e:
        logger.error(f"Graph search failed: {e}")

    # Lead not found
    return LeadLookupResponse(
        found=False,
        lead=None,
        context=None,
        message="Lead not found (new customer)"
    )


@app.post("/api/leads", response_model=Lead)
async def create_or_update_lead(
    request: LeadCreateRequest,
    api_key: str = Depends(require_api_key),
):
    """
    Create or update a lead.

    This replaces the Pinecone upsert (Initial) operation.
    Ingests the lead into the knowledge graph for relationship tracking.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Normalize lookup_id
    lookup_id = request.lookup_id or request.email_norm or request.phone_norm
    if not lookup_id:
        raise HTTPException(status_code=400, detail="Must provide email or phone")

    lookup_id = lookup_id.lower().strip()

    # Check if lead exists
    existing_lead = lead_cache.get(lookup_id)

    if existing_lead:
        # Update existing lead
        lead = existing_lead.model_copy(update={
            "full_name": request.full_name or existing_lead.full_name,
            "inquiry_type": request.inquiry_type or existing_lead.inquiry_type,
            "comments": request.comments or existing_lead.comments,
            "company": request.company or existing_lead.company,
            "title": request.title or existing_lead.title,
            "updated_at": datetime.now(timezone.utc),
        })
        lead.status = LeadStatus.EXISTING
    else:
        # Create new lead
        lead = Lead(
            lookup_id=lookup_id,
            full_name=request.full_name,
            email=request.email_norm,
            phone=request.phone_norm,
            inquiry_type=request.inquiry_type,
            comments=request.comments,
            company=request.company,
            title=request.title,
            status=LeadStatus.NEW,
            source=LeadSource.LAKEB2B_FORM,
        )

    # Store in cache
    lead_cache[lookup_id] = lead

    # Ingest into knowledge graph (async, don't block response)
    asyncio.create_task(_ingest_lead_to_graph(lead))

    logger.info(f"Lead created/updated: {lookup_id} (status: {lead.status.value})")
    return lead


@app.post("/api/leads/{lookup_id}/enrich", response_model=Lead)
async def enrich_lead(
    lookup_id: str,
    request: LeadEnrichRequest,
    api_key: str = Depends(require_api_key),
):
    """
    Enrich a lead with research data.

    This replaces the Pinecone upsert (Enriched) operation.
    Stores research findings and email tracking in the knowledge graph.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    lookup_id = lookup_id.lower().strip()

    # Get existing lead
    lead = lead_cache.get(lookup_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead not found: {lookup_id}")

    # Update with enrichment data
    lead.research_summary = request.research_summary
    lead.enrichment_sources = request.sources
    lead.email_sent = request.email_sent
    lead.email_subject = request.email_subject
    lead.status = LeadStatus.EMAIL_SENT if request.email_sent else LeadStatus.ENRICHED
    lead.updated_at = datetime.now(timezone.utc)

    if request.email_sent:
        lead.email_sent_at = datetime.now(timezone.utc)

    # Update cache
    lead_cache[lookup_id] = lead

    # Ingest enrichment to graph
    asyncio.create_task(_ingest_enrichment_to_graph(lead))

    logger.info(f"Lead enriched: {lookup_id} (email_sent: {lead.email_sent})")
    return lead


@app.get("/api/leads/{lookup_id}/context", response_model=LeadContextResponse)
async def get_lead_context(
    lookup_id: str,
    api_key: str = Depends(require_api_key),
):
    """
    Get rich context about a lead for personalization.

    Returns previous communications, personal details, discussed topics,
    and related contacts from the knowledge graph.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    lookup_id = lookup_id.lower().strip()

    lead = lead_cache.get(lookup_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead not found: {lookup_id}")

    context = await _get_lead_context(lead)

    return LeadContextResponse(
        lead=lead,
        previous_communications=context.get('communications', []),
        personal_details=context.get('personal_details', []),
        discussed_topics=context.get('topics', []),
        team_contacts=context.get('team_contacts', []),
        related_contacts=context.get('related_contacts', []),
        context_summary=context.get('summary'),
    )


# === Original Knowledge Graph Endpoints (for WhatsApp Assistant) ===

@app.post("/api/query", response_model=QueryResponse)
async def query_account(
    request: QueryRequest,
    api_key: str = Depends(require_api_key),
):
    """
    Query the knowledge graph for an account.

    This is the main endpoint for the CEO WhatsApp Assistant.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        results = await graphiti_service.search_account(
            account_name=request.account,
            query=request.query,
            num_results=request.num_results,
        )

        return QueryResponse(
            success=True,
            data=results,
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/{account_name}/contacts")
async def get_account_contacts(
    account_name: str,
    api_key: str = Depends(require_api_key),
):
    """Get all contacts for an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.search_account(
        account_name=account_name,
        query="Who are the contacts and people at this account?",
    )
    return {"success": True, "contacts": results.get("nodes", [])}


@app.get("/api/accounts/{account_name}/topics")
async def get_account_topics(
    account_name: str,
    api_key: str = Depends(require_api_key),
):
    """Get all topics discussed with an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.search_account(
        account_name=account_name,
        query="What topics, subjects, and themes were discussed?",
    )
    return {"success": True, "topics": results.get("edges", [])}


@app.get("/api/accounts/{account_name}/communications")
async def get_account_communications(
    account_name: str,
    limit: int = Query(default=10, ge=1, le=100),
    api_key: str = Depends(require_api_key),
):
    """Get recent communications with an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_recent_communications(
        account_name=account_name,
        limit=limit,
    )
    return {"success": True, "communications": results}


@app.get("/api/accounts/{account_name}/personal-details")
async def get_personal_details(
    account_name: str,
    api_key: str = Depends(require_api_key),
):
    """Get personal details about contacts at an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_personal_details(account_name)
    return {"success": True, "personal_details": results}


@app.get("/api/accounts/{account_name}/team-contacts")
async def get_team_contacts(
    account_name: str,
    api_key: str = Depends(require_api_key),
):
    """Get which team members contacted this account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_who_reached_out(account_name)
    return {"success": True, "team_contacts": results}


@app.get("/api/accounts/{account_name}/graph")
async def get_account_graph(
    account_name: str,
    api_key: str = Depends(require_api_key),
):
    """Get full graph data for visualization"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.get_account_graph(account_name)
    return {"success": True, "graph": results}


# === Helper Functions ===

def _node_matches_lookup(node: Dict, lookup_id: str) -> bool:
    """Check if a graph node matches the lookup ID"""
    lookup_lower = lookup_id.lower()

    # Check node attributes
    attrs = node.get('attributes', {})
    if attrs.get('email', '').lower() == lookup_lower:
        return True
    if attrs.get('phone', '') == lookup_lower:
        return True

    # Check node name (might contain email)
    if lookup_lower in node.get('name', '').lower():
        return True

    return False


def _lead_from_node(node: Dict, lookup_id: str) -> Lead:
    """Reconstruct a Lead from a graph node"""
    attrs = node.get('attributes', {})

    return Lead(
        lookup_id=lookup_id,
        full_name=node.get('name', ''),
        email=attrs.get('email', lookup_id),
        phone=attrs.get('phone'),
        company=attrs.get('company'),
        title=attrs.get('title'),
        status=LeadStatus.EXISTING,
        source=LeadSource.LAKEB2B_FORM,
        graph_node_id=node.get('uuid'),
    )


async def _get_lead_context(lead: Lead) -> Dict[str, Any]:
    """Get rich context for a lead from the knowledge graph"""
    if not graphiti_service:
        return {}

    context = {
        'communications': [],
        'personal_details': [],
        'topics': [],
        'team_contacts': [],
        'related_contacts': [],
        'summary': None,
    }

    try:
        account = lead.account_group_id or "lakeb2b"

        # Get various context types in parallel
        results = await asyncio.gather(
            graphiti_service.query_recent_communications(account, limit=5),
            graphiti_service.query_personal_details(account),
            graphiti_service.search_account(
                account,
                f"What topics did {lead.full_name} discuss?",
                num_results=10,
            ),
            graphiti_service.query_who_reached_out(account),
            return_exceptions=True,
        )

        if not isinstance(results[0], Exception):
            context['communications'] = results[0]
        if not isinstance(results[1], Exception):
            context['personal_details'] = results[1]
        if not isinstance(results[2], Exception):
            context['topics'] = results[2].get('edges', [])
        if not isinstance(results[3], Exception):
            context['team_contacts'] = results[3]

        # Generate summary if we have context
        if any(context.values()):
            context['summary'] = _generate_context_summary(lead, context)

    except Exception as e:
        logger.error(f"Failed to get lead context: {e}")

    return context


def _generate_context_summary(lead: Lead, context: Dict) -> str:
    """Generate a brief summary of lead context for prompts"""
    parts = []

    if context.get('communications'):
        parts.append(f"{len(context['communications'])} previous communications")

    if context.get('personal_details'):
        parts.append(f"{len(context['personal_details'])} personal details known")

    if context.get('topics'):
        parts.append(f"{len(context['topics'])} topics discussed")

    if context.get('team_contacts'):
        parts.append(f"contacted by {len(context['team_contacts'])} team members")

    if parts:
        return f"Lead {lead.full_name}: {', '.join(parts)}"

    return f"Lead {lead.full_name}: new contact, no prior history"


async def _ingest_lead_to_graph(lead: Lead) -> None:
    """Ingest lead as an episode to the knowledge graph"""
    if not graphiti_service:
        return

    try:
        from models.email import Email, EmailDirection

        # Create a pseudo-email representing the form submission
        email = Email(
            message_id=f"lead-{lead.lookup_id}-{lead.created_at.timestamp()}",
            from_email=lead.email,
            from_name=lead.full_name,
            to_emails=["leads@lakeb2b.com"],  # Internal receiver
            subject=f"Contact Form: {lead.inquiry_type or 'General Inquiry'}",
            body_text=lead.to_episode_content(),
            timestamp=lead.created_at,
            direction=EmailDirection.INBOUND,
            channel="contact_form",
            account_name="LakeB2B Leads",
            provider="n8n_workflow",
        )

        await graphiti_service.ingest_email(email, account_name="lakeb2b")
        logger.info(f"Lead ingested to graph: {lead.lookup_id}")

    except Exception as e:
        logger.error(f"Failed to ingest lead to graph: {e}")


async def _ingest_enrichment_to_graph(lead: Lead) -> None:
    """Ingest enrichment data as an episode to the knowledge graph"""
    if not graphiti_service:
        return

    try:
        from models.email import Email, EmailDirection

        enrichment_content = lead.to_enrichment_episode()
        if not enrichment_content:
            return

        # Create a pseudo-email for the enrichment
        email = Email(
            message_id=f"enrichment-{lead.lookup_id}-{lead.updated_at.timestamp()}",
            from_email="research@lakeb2b.com",  # Internal
            from_name="Research Agent",
            to_emails=[lead.email],
            subject=f"Lead Enrichment: {lead.full_name}",
            body_text=enrichment_content,
            timestamp=lead.updated_at,
            direction=EmailDirection.OUTBOUND,
            channel="enrichment",
            account_name="LakeB2B Leads",
            provider="n8n_workflow",
        )

        await graphiti_service.ingest_email(email, account_name="lakeb2b")
        logger.info(f"Enrichment ingested to graph: {lead.lookup_id}")

    except Exception as e:
        logger.error(f"Failed to ingest enrichment to graph: {e}")


# === Main ===

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))

    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,
    )
