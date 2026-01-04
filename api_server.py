"""
API Server for CEO WhatsApp Assistant Integration

Provides REST endpoints for querying the knowledge graph.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import get_settings
from services.graphiti_service import GraphitiService
from services.profile_builder import ProfileBuilder
from services.intent_scorer import IntentScorer, IntentScoringConfig
from services.outreach_personalizer import OutreachPersonalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
graphiti_service: Optional[GraphitiService] = None
profile_builder: Optional[ProfileBuilder] = None
intent_scorer: Optional[IntentScorer] = None
outreach_personalizer: Optional[OutreachPersonalizer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global graphiti_service, profile_builder, intent_scorer, outreach_personalizer
    settings = get_settings()

    # Initialize GraphitiService
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

    # Initialize enrichment configs (from environment variables)
    enrichment_configs = {}

    if os.getenv('CLEARBIT_API_KEY'):
        enrichment_configs['clearbit'] = {'api_key': os.getenv('CLEARBIT_API_KEY')}

    if os.getenv('BUILTWITH_API_KEY'):
        enrichment_configs['builtwith'] = {'api_key': os.getenv('BUILTWITH_API_KEY')}

    if os.getenv('PDL_API_KEY'):
        enrichment_configs['people-data-labs'] = {'api_key': os.getenv('PDL_API_KEY')}

    # Initialize ProfileBuilder
    profile_builder = ProfileBuilder(
        graphiti_service=graphiti_service,
        enrichment_configs=enrichment_configs
    )
    logger.info("Profile builder initialized")

    # Initialize IntentScorer
    intent_scorer = IntentScorer(config=IntentScoringConfig())
    logger.info("Intent scorer initialized")

    # Initialize OutreachPersonalizer
    outreach_personalizer = OutreachPersonalizer(
        llm_provider="openai",
        model=os.getenv('OUTREACH_MODEL', 'gpt-4'),
        api_key=settings.openai_api_key
    )
    logger.info("Outreach personalizer initialized")

    yield

    await graphiti_service.disconnect()
    logger.info("All services disconnected")


app = FastAPI(
    title="Graphiti Knowledge Graph API",
    description="API for CEO WhatsApp Assistant to query account knowledge",
    version="1.0.0",
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


class ProfileRequest(BaseModel):
    account_name: str
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    enrich: bool = True


class OutreachRequest(BaseModel):
    account_name: str
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    purpose: str = "intro"  # intro, follow_up, demo_request, value_prop
    tone: str = "professional"  # professional, casual, friendly, urgent
    length: str = "short"  # short, medium, long
    channel: str = "email"  # email, linkedin, call_script


# === Endpoints ===

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="graphiti-knowledge-graph"
    )


@app.post("/api/query", response_model=QueryResponse)
async def query_account(request: QueryRequest):
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
async def get_account_contacts(account_name: str):
    """Get all contacts for an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.search_account(
        account_name=account_name,
        query="Who are the contacts and people at this account?",
    )
    return {"success": True, "contacts": results.get("nodes", [])}


@app.get("/api/accounts/{account_name}/topics")
async def get_account_topics(account_name: str):
    """Get all topics discussed with an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.search_account(
        account_name=account_name,
        query="What topics, subjects, and themes were discussed?",
    )
    return {"success": True, "topics": results.get("edges", [])}


@app.get("/api/accounts/{account_name}/communications")
async def get_account_communications(account_name: str, limit: int = 10):
    """Get recent communications with an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_recent_communications(
        account_name=account_name,
        limit=limit,
    )
    return {"success": True, "communications": results}


@app.get("/api/accounts/{account_name}/personal-details")
async def get_personal_details(account_name: str):
    """Get personal details about contacts at an account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_personal_details(account_name)
    return {"success": True, "personal_details": results}


@app.get("/api/accounts/{account_name}/team-contacts")
async def get_team_contacts(account_name: str):
    """Get which team members contacted this account"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.query_who_reached_out(account_name)
    return {"success": True, "team_contacts": results}


@app.get("/api/accounts/{account_name}/graph")
async def get_account_graph(account_name: str):
    """Get full graph data for visualization"""
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = await graphiti_service.get_account_graph(account_name)
    return {"success": True, "graph": results}


# === NEW: Comprehensive Profile & Sales Intelligence Endpoints ===

@app.post("/api/profiles/contact")
async def build_contact_profile(request: ProfileRequest):
    """
    Build comprehensive contact profile.

    Aggregates data from:
    - Knowledge graph (email, web, social events)
    - Enrichment APIs (firmographics, technographics)
    - Intent scoring
    - Engagement analysis

    Returns complete profile ready for sales outreach.
    """
    if not profile_builder:
        raise HTTPException(status_code=503, detail="Profile builder not initialized")

    try:
        profile = await profile_builder.build_contact_profile(
            account_name=request.account_name,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            enrich=request.enrich
        )

        return {
            "success": True,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Failed to build contact profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profiles/account")
async def build_account_profile(request: ProfileRequest):
    """
    Build comprehensive account profile.

    Returns:
    - All contacts at account
    - Firmographics (industry, size, revenue, etc.)
    - Technographics (tech stack)
    - Engagement summary
    - Intent signals
    """
    if not profile_builder:
        raise HTTPException(status_code=503, detail="Profile builder not initialized")

    try:
        profile = await profile_builder.build_account_profile(
            account_name=request.account_name,
            enrich=request.enrich
        )

        return {
            "success": True,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Failed to build account profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outreach/generate")
async def generate_outreach(request: OutreachRequest):
    """
    Generate personalized outreach content.

    Uses LLM to create:
    - Personalized email (subject + body)
    - LinkedIn message
    - Call script

    Based on comprehensive profile data and intent signals.
    """
    if not profile_builder or not outreach_personalizer:
        raise HTTPException(status_code=503, detail="Services not initialized")

    try:
        # Build profile first
        profile = await profile_builder.build_contact_profile(
            account_name=request.account_name,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            enrich=True
        )

        # Generate outreach based on channel
        if request.channel == "email":
            result = await outreach_personalizer.generate_email(
                profile=profile,
                purpose=request.purpose,
                tone=request.tone,
                length=request.length
            )
        elif request.channel == "linkedin":
            result = await outreach_personalizer.generate_linkedin_message(
                profile=profile,
                purpose=request.purpose
            )
        elif request.channel == "call_script":
            result = await outreach_personalizer.generate_call_script(
                profile=profile,
                call_type=request.purpose
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown channel: {request.channel}")

        return {
            "success": True,
            "outreach": result,
            "profile_summary": {
                "intent_score": profile.get('intent', {}).get('score'),
                "intent_level": profile.get('intent', {}).get('level'),
                "engagement_score": profile.get('engagement', {}).get('overall_score')
            }
        }
    except Exception as e:
        logger.error(f"Failed to generate outreach: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/{account_name}/intent")
async def get_account_intent(account_name: str):
    """
    Calculate intent score for an account.

    Analyzes all signals (email, web, social) to determine buying intent.
    """
    if not profile_builder:
        raise HTTPException(status_code=503, detail="Profile builder not initialized")

    try:
        profile = await profile_builder.build_account_profile(
            account_name=account_name,
            enrich=False  # No need to enrich for intent scoring
        )

        return {
            "success": True,
            "intent": profile.get('intent_signals', []),
            "engagement": profile.get('engagement_summary', {})
        }
    except Exception as e:
        logger.error(f"Failed to get account intent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/{account_name}/firmographics")
async def get_account_firmographics(account_name: str, enrich: bool = True):
    """
    Get firmographic data for an account.

    Optionally enriches with external APIs (Clearbit, etc.)
    """
    if not profile_builder:
        raise HTTPException(status_code=503, detail="Profile builder not initialized")

    try:
        profile = await profile_builder.build_account_profile(
            account_name=account_name,
            enrich=enrich
        )

        return {
            "success": True,
            "firmographics": profile.get('firmographics', {}),
            "technographics": profile.get('technographics', {})
        }
    except Exception as e:
        logger.error(f"Failed to get firmographics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
