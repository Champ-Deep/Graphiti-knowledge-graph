# ElevenLabs Integration Guide

Complete guide for integrating your Graphiti Knowledge Graph with ElevenLabs WhatsApp Agents.

## Overview

This integration allows ElevenLabs conversational AI agents to query your knowledge graph in real-time, providing your CEO with intelligent, context-aware responses about accounts, contacts, and relationships via WhatsApp voice and text.

## Architecture

```
WhatsApp User (CEO)
        ↓
ElevenLabs Agent (Conversational AI)
        ↓
Custom Tools (API Calls)
        ↓
Your Graphiti API (this server)
        ↓
Neo4j Knowledge Graph
```

## Prerequisites

1. **Deployed Graphiti API** - Follow [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) first
2. **ElevenLabs Account** - Sign up at https://elevenlabs.io
3. **WhatsApp Business Account** - For production use
4. **Public API URL** - Your API must be accessible from the internet

## Step 1: Secure Your API

Before connecting to ElevenLabs, add API key authentication.

### Add Authentication to api_server.py

Add this to your `api_server.py`:

```python
import os
from fastapi import Header, HTTPException, Depends

# After your imports, add:

async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for ElevenLabs integration"""
    expected_key = os.getenv("API_KEY")

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return x_api_key

# Then add the dependency to protected endpoints:
@app.post("/api/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
async def query_account(request: QueryRequest):
    # existing code...
```

**Set your API key in environment:**
```bash
# Generate secure key
openssl rand -hex 32

# Add to .env
API_KEY=your_generated_key_here
```

## Step 2: Add Voice-Optimized Endpoints

Add these endpoints to `api_server.py` for better voice interactions:

```python
@app.get("/api/accounts/{account_name}/brief", dependencies=[Depends(verify_api_key)])
async def get_account_brief(account_name: str):
    """
    Get a concise voice-friendly summary of an account.
    Optimized for ElevenLabs voice responses.
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Get top contacts
        contacts_result = await graphiti_service.search_account(
            account_name, "Who are the key contacts?", num_results=5
        )

        # Get recent topics
        topics_result = await graphiti_service.search_account(
            account_name, "What were recent discussion topics?", num_results=3
        )

        # Get personal details
        personal_details = await graphiti_service.query_personal_details(account_name)

        # Get last interaction
        recent_comms = await graphiti_service.query_recent_communications(
            account_name, limit=1
        )

        # Format for concise voice response
        brief = {
            "account": account_name,
            "key_contacts": [
                node.get("name", "Unknown")
                for node in contacts_result.get("nodes", [])[:3]
            ],
            "recent_topics": [
                edge.get("fact", "")
                for edge in topics_result.get("edges", [])[:3]
                if edge.get("fact")
            ],
            "personal_notes": [
                edge.get("fact", "")
                for edge in personal_details[:2]
                if edge.get("fact")
            ],
            "last_contact": recent_comms[0] if recent_comms else None
        }

        return {"success": True, "brief": brief}

    except Exception as e:
        logger.error(f"Brief query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context-for-call", dependencies=[Depends(verify_api_key)])
async def get_context_for_call(request: dict):
    """
    Get comprehensive context before a call.

    Request body:
    {
        "account": "acme-corp",
        "attendees": ["John Smith", "Jane Doe"]  // optional
    }
    """
    if not graphiti_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    account = request.get("account")
    attendees = request.get("attendees", [])

    if not account:
        raise HTTPException(status_code=400, detail="account is required")

    context = {
        "account": account,
        "attendees": []
    }

    # Get info about each attendee
    for attendee in attendees:
        person_info = await graphiti_service.search_account(
            account,
            f"What do we know about {attendee}? Their role, interests, family, hobbies?",
            num_results=5
        )

        discussions = await graphiti_service.query_discussions_by_person(
            account, attendee
        )

        context["attendees"].append({
            "name": attendee,
            "details": person_info,
            "recent_discussions": discussions[:3]
        })

    # Get overall account context
    account_brief = await get_account_brief(account)
    context["account_overview"] = account_brief.get("brief", {})

    # Get action items or follow-ups
    follow_ups = await graphiti_service.search_account(
        account,
        "What were the action items, next steps, or things we promised to follow up on?",
        num_results=5
    )
    context["follow_ups"] = follow_ups.get("edges", [])

    return {"success": True, "context": context}
```

Restart your API after adding these endpoints.

## Step 3: Create ElevenLabs Agent

### 3.1 Create Agent

1. Go to https://elevenlabs.io/app/conversational-ai
2. Click **"Create Agent"**
3. Configure:
   - **Name:** CEO WhatsApp Assistant
   - **Voice:** Choose professional voice (e.g., "Rachel", "Christopher")
   - **Language:** English

### 3.2 Configure System Prompt

Set this as your agent's system prompt:

```
You are an executive assistant for a CEO. Your role is to help the CEO stay
informed about their key business relationships, accounts, and contacts.

You have access to a knowledge graph containing:
- Contact information (names, roles, companies)
- Communication history (emails, calls, meetings)
- Discussion topics and key points
- Personal details (family, hobbies, interests)
- Team member interactions

When the CEO asks about an account or contact:
1. Use the available tools to query the knowledge graph
2. Provide concise, actionable information
3. Highlight personal details that can help build rapport
4. Mention recent communications and key discussion topics
5. Be professional but conversational

Guidelines:
- Keep responses brief and to-the-point for voice calls
- For text, you can be slightly more detailed
- Always mention the source of your information (recent email, last meeting, etc.)
- If you don't have information, say so clearly
- Proactively suggest relevant talking points
- Remember context within the conversation

Example response style:
"For Acme Corp, your main contact is Sarah Johnson, their CEO. You last spoke
3 days ago about Q1 integration timelines. Personal note: her daughter just
started at Stanford. Key talking point: their Q2 budget approval is pending."
```

### 3.3 Configure Custom Tools

ElevenLabs agents can call external APIs as "tools". Configure these tools in the agent settings:

#### Tool 1: Query Account Knowledge

**Name:** `query_account_knowledge`

**Description:**
```
Search the knowledge graph for information about a specific company or account.
Use this to answer questions about contacts, communications, topics, or any
account-related information.
```

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "The company/account name (e.g., 'acme-corp', 'Google')"
    },
    "query": {
      "type": "string",
      "description": "Natural language question about the account"
    },
    "num_results": {
      "type": "integer",
      "description": "Maximum number of results (default: 20)",
      "default": 20
    }
  },
  "required": ["account", "query"]
}
```

**API Configuration:**
- **URL:** `https://your-api-domain.com/api/query`
- **Method:** POST
- **Headers:**
  ```json
  {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key-here"
  }
  ```

#### Tool 2: Get Account Brief

**Name:** `get_account_brief`

**Description:**
```
Get a quick comprehensive summary of an account including key contacts,
recent topics, and personal details. Use this when the CEO asks for a
quick briefing on an account.
```

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "The company/account name"
    }
  },
  "required": ["account"]
}
```

**API Configuration:**
- **URL:** `https://your-api-domain.com/api/accounts/{account}/brief`
- **Method:** GET
- **Headers:**
  ```json
  {
    "X-API-Key": "your-api-key-here"
  }
  ```

#### Tool 3: Get Personal Details

**Name:** `get_personal_details`

**Description:**
```
Get personal information about contacts at an account (family, hobbies,
interests). Use this to help the CEO build rapport and personalize interactions.
```

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "The company/account name"
    }
  },
  "required": ["account"]
}
```

**API Configuration:**
- **URL:** `https://your-api-domain.com/api/accounts/{account}/personal-details`
- **Method:** GET
- **Headers:**
  ```json
  {
    "X-API-Key": "your-api-key-here"
  }
  ```

#### Tool 4: Get Context for Call

**Name:** `get_context_for_call`

**Description:**
```
Get comprehensive context before a scheduled call or meeting. Includes
attendee information, recent discussions, and follow-up items.
```

**Parameters:**
```json
{
  "type": "object",
  "properties": {
    "account": {
      "type": "string",
      "description": "The company/account name"
    },
    "attendees": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Names of people attending the call (optional)"
    }
  },
  "required": ["account"]
}
```

**API Configuration:**
- **URL:** `https://your-api-domain.com/api/context-for-call`
- **Method:** POST
- **Headers:**
  ```json
  {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key-here"
  }
  ```

## Step 4: Connect WhatsApp

### 4.1 Setup WhatsApp Business

1. In ElevenLabs dashboard, go to **WhatsApp** section
2. Click **"Import account"**
3. Follow OAuth flow to connect your WhatsApp Business account
4. Grant permissions for ElevenLabs to manage messages

### 4.2 Assign Agent

1. Select your CEO Assistant agent
2. Configure settings:
   - **Greeting Message:** "Hi! I'm your CEO assistant. Ask me about any account or contact."
   - **Max Conversation Duration:** 15 minutes (adjust as needed)
   - **Working Hours:** Set according to CEO's availability

### 4.3 Test Integration

**Text Message Test:**
1. Send a message to your WhatsApp Business number
2. Try: "Tell me about Acme Corp"
3. The agent should use `get_account_brief` tool to fetch data

**Voice Call Test:**
1. Call your WhatsApp Business number
2. Ask: "Who did we last speak with at Google?"
3. The agent should query the knowledge graph and respond verbally

## Step 5: Advanced Configuration

### Rate Limiting

Add rate limiting to protect your API:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/query", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")  # 30 requests per minute
async def query_account(request: Request, query_request: QueryRequest):
    # existing code...
```

### Caching

Add Redis caching for frequent queries:

```python
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_result(ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"

            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))

            return result
        return wrapper
    return decorator

# Use on endpoints:
@app.get("/api/accounts/{account_name}/brief")
@cache_result(ttl=300)  # Cache for 5 minutes
async def get_account_brief(account_name: str):
    # existing code...
```

### Logging & Monitoring

Add structured logging:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

## Testing Your Integration

### Test with curl

```bash
# Test brief endpoint
curl -X GET "https://your-api.com/api/accounts/acme-corp/brief" \
  -H "X-API-Key: your-api-key"

# Test query endpoint
curl -X POST "https://your-api.com/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "account": "acme-corp",
    "query": "Who are the key contacts?",
    "num_results": 10
  }'

# Test call context endpoint
curl -X POST "https://your-api.com/api/context-for-call" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "account": "google",
    "attendees": ["John Smith", "Sarah Johnson"]
  }'
```

### Test with WhatsApp

**Scenario 1: Quick Brief**
```
CEO: "Brief me on Acme Corp"
Agent: [Calls get_account_brief]
Agent: "For Acme Corp, your key contacts are Sarah Johnson (CEO),
       Mike Chen (VP Engineering), and Lisa Wang (Product Manager).
       You last discussed their Q1 integration timeline 3 days ago.
       Personal note: Sarah's daughter just started at Stanford."
```

**Scenario 2: Specific Query**
```
CEO: "What did we discuss with Mike Chen?"
Agent: [Calls query_account_knowledge with specific query]
Agent: "You discussed API integration requirements and pricing for
       the enterprise tier. Mike was concerned about data security
       and compliance with SOC2."
```

**Scenario 3: Pre-Call Prep**
```
CEO: "I have a call with Google in 10 minutes. Who's attending?"
Agent: "Who will be on the call from Google?"
CEO: "John Smith and Lisa Wang"
Agent: [Calls get_context_for_call]
Agent: "Here's what you need to know: John Smith is VP of Engineering,
       interested in golf - his son plays for Stanford. Lisa Wang is
       Product Lead, recently returned from maternity leave. Last
       discussion: implementation timeline for Q2. Follow-up item:
       You promised pricing proposal by end of month."
```

## Best Practices

### 1. Data Quality
- Regularly sync emails to keep knowledge graph current
- Verify account names are consistent (use canonical names)
- Clean up duplicate entities periodically

### 2. Response Optimization
- Keep voice responses under 30 seconds
- Use bullet points for text responses
- Prioritize most recent and relevant information

### 3. Privacy & Security
- Never expose sensitive credentials in logs
- Rotate API keys quarterly
- Monitor API usage for anomalies
- Use HTTPS only
- Implement IP whitelisting if possible

### 4. Monitoring
- Track API response times
- Monitor ElevenLabs tool call success rates
- Set up alerts for API errors
- Review conversation transcripts weekly

### 5. Continuous Improvement
- Collect feedback from CEO on response quality
- Refine system prompts based on usage patterns
- Add new tools as needs emerge
- Update knowledge graph schema as needed

## Troubleshooting

### Agent doesn't call tools
- Verify tool descriptions are clear
- Check system prompt encourages tool usage
- Ensure API URL is accessible from internet
- Verify API key in tool configuration

### API returns 401 Unauthorized
- Check X-API-Key header is set in tool config
- Verify API key matches .env file
- Ensure verify_api_key dependency is on endpoint

### Slow responses
- Enable caching with Redis
- Optimize Neo4j queries with indices
- Reduce num_results parameter
- Scale up API server resources

### Inaccurate information
- Check knowledge graph has been synced recently
- Verify email ingestion is working
- Review Graphiti entity extraction quality
- Adjust entity_types and edge_types configuration

## Cost Optimization

### ElevenLabs
- Text is much cheaper than voice
- Encourage text for complex queries
- Use voice for quick briefs
- Monitor usage in ElevenLabs dashboard

### API Infrastructure
- Use caching to reduce database queries
- Scale down during off-hours
- Use spot instances for cost savings
- Monitor and optimize slow queries

### LLM Costs (OpenRouter/OpenAI)
- Knowledge graph queries use LLM for entity extraction
- Use cheaper models for simple queries
- Batch email ingestion to reduce API calls
- Monitor OpenRouter usage dashboard

## Next Steps

1. ✅ **Deploy your API** (see DEPLOYMENT_GUIDE.md)
2. ✅ **Add authentication endpoints**
3. ✅ **Create ElevenLabs agent**
4. ✅ **Configure tools**
5. ✅ **Connect WhatsApp**
6. ✅ **Sync initial email data**
7. ✅ **Test thoroughly**
8. ✅ **Train CEO on how to use**
9. ✅ **Monitor and iterate**

## Support

- **ElevenLabs Docs:** https://elevenlabs.io/docs
- **Graphiti Docs:** https://github.com/getzep/graphiti
- **Neo4j Docs:** https://neo4j.com/docs

---

**Ready to go live?** Start with testing locally, then deploy to production, and finally connect ElevenLabs!
