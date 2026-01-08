# Graphiti Knowledge Graph

A temporal knowledge graph system that serves as the intelligent "brain" for email automation workflows. Replaces Pinecone with a rich relationship-aware graph database for personalized outreach.

## Overview

This system builds a knowledge graph that tracks:
- **Contacts/Leads** - People from contact forms and email communications
- **Accounts** - Companies/organizations being tracked
- **Team Members** - Internal sales/marketing team
- **Topics** - Discussion subjects and business themes
- **Personal Details** - Family, hobbies, interests (for personalization)
- **Communications** - Interaction events with temporal tracking
- **Relationships** - Who knows who, who contacted whom, reporting structures

## Use Cases

### 1. n8n Email Automation (Primary)
Replace Pinecone in your email automation workflow with rich context:
- Check if lead exists with full relationship context
- Track communication history across interactions
- Store and retrieve personal details for personalization
- Build relationship maps between contacts

### 2. CEO WhatsApp Assistant
Query account knowledge during conversations:
- "What personal details do we know about John at Acme?"
- "Who from our team has contacted this account?"
- "What topics have we discussed with them?"

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           n8n Workflow                   │
                    │  (Email Automation on Railway)          │
                    └─────────────────┬───────────────────────┘
                                      │ HTTPS + X-API-Key
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Railway Project                               │
│  ┌────────────────────────┐    ┌─────────────────────────────┐  │
│  │   Graphiti API         │    │      Neo4j Database         │  │
│  │   (FastAPI :8080)      │◄──►│      (bolt :7687)           │  │
│  │                        │    │                              │  │
│  │  /api/leads/lookup     │    │  Nodes: Contact, Account,   │  │
│  │  /api/leads            │    │         Topic, PersonalDetail│  │
│  │  /api/leads/{id}/enrich│    │  Edges: SENT_EMAIL_TO,      │  │
│  │  /api/query            │    │         WORKS_AT, etc.      │  │
│  └────────────────────────┘    └─────────────────────────────┘  │
│              │                                                    │
│              ▼                                                    │
│     OpenRouter/OpenAI API                                        │
│     (Entity extraction)                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option A: Local Development with Docker Compose

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Graphiti-knowledge-graph.git
cd Graphiti-knowledge-graph

# Copy environment template
cp .env.example .env
# Edit .env with your OpenRouter API key

# Start all services
docker-compose up -d

# API available at http://localhost:8080
# Neo4j browser at http://localhost:7474
```

### Option B: Railway Deployment

1. **Create Railway Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login and create project
   railway login
   railway init
   ```

2. **Deploy Neo4j** (use Railway's Neo4j template or custom Docker)
   - In Railway dashboard, add a new service
   - Use the Neo4j template or deploy custom Docker image
   - Note the internal URL: `neo4j.railway.internal:7687`

3. **Deploy Graphiti API**
   ```bash
   railway up
   ```

4. **Set Environment Variables** in Railway dashboard:
   ```
   API_KEY=<generate-secure-key>
   NEO4J_URI=bolt://neo4j.railway.internal:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<your-password>
   OPENAI_API_KEY=sk-or-v1-<your-openrouter-key>
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   MODEL_NAME=openai/gpt-4o-mini
   ```

5. **Get your API URL** from Railway (e.g., `https://graphiti-xxx.railway.app`)

## n8n Integration

### Setting Up n8n Credentials

1. **Create HTTP Header Auth Credential** in n8n:
   - Name: `Graphiti API Key`
   - Header Name: `X-API-Key`
   - Header Value: `<your-api-key-from-railway>`

2. **Set Environment Variable** in n8n:
   ```
   GRAPHITI_API_URL=https://your-graphiti.railway.app
   ```

3. **Import the Workflow**:
   - Import `n8n-workflows/email-automation-graphiti.json`
   - Update credential references
   - Test with a sample lead

### Workflow Changes from Pinecone

| Before (Pinecone) | After (Graphiti) |
|-------------------|------------------|
| `GET /vectors/fetch?ids={id}` | `POST /api/leads/lookup` |
| `POST /vectors/upsert` (initial) | `POST /api/leads` |
| `POST /vectors/upsert` (enriched) | `POST /api/leads/{id}/enrich` |
| Flat metadata storage | Rich graph with relationships |
| No relationship tracking | Full communication history |
| No personal details | PersonalDetail entities |

### New Capabilities

With Graphiti, your Prompt Writer agents can access:

```json
{
  "lead": {
    "full_name": "John Smith",
    "email": "john@acme.com",
    "status": "existing"
  },
  "context": {
    "summary": "Lead John Smith: 5 previous communications, 3 personal details known, 2 topics discussed",
    "communications": [...],
    "personal_details": [
      {"category": "hobby", "detail": "Enjoys golf"},
      {"category": "family", "detail": "Has two kids"}
    ],
    "topics": ["data quality", "integration timeline"],
    "team_contacts": ["Sarah from Sales called last month"]
  }
}
```

## API Reference

### Authentication

All endpoints (except `/health`) require an API key:
```
X-API-Key: your-api-key
```

### Lead Endpoints (n8n Integration)

#### Lookup Lead
```http
POST /api/leads/lookup
Content-Type: application/json
X-API-Key: your-api-key

{
  "email": "john@example.com",
  "phone": "1234567890",
  "lookup_id": "john@example.com"
}

Response:
{
  "found": true,
  "lead": {...},
  "context": {
    "communications": [...],
    "personal_details": [...],
    "topics": [...],
    "team_contacts": [...],
    "summary": "..."
  },
  "message": "Lead found (existing customer)"
}
```

#### Create/Update Lead
```http
POST /api/leads
Content-Type: application/json
X-API-Key: your-api-key

{
  "full_name": "John Smith",
  "email": "john@example.com",
  "phone": "1234567890",
  "Inquiry Type": "Data Services",
  "Comments": "Interested in your API"
}
```

#### Enrich Lead
```http
POST /api/leads/{lookup_id}/enrich
Content-Type: application/json
X-API-Key: your-api-key

{
  "lookup_id": "john@example.com",
  "research_summary": ["CTO at Acme Corp", "10+ years in data"],
  "sources": ["https://linkedin.com/..."],
  "email_subject": "Quick question about your data needs",
  "email_sent": true
}
```

#### Get Lead Context
```http
GET /api/leads/{lookup_id}/context
X-API-Key: your-api-key
```

### Knowledge Graph Endpoints (WhatsApp Assistant)

#### Query Account
```http
POST /api/query
Content-Type: application/json
X-API-Key: your-api-key

{
  "account": "acme-corp",
  "query": "Who from our team contacted this account?",
  "num_results": 20
}
```

#### Pre-built Queries
```http
GET /api/accounts/{account_name}/contacts
GET /api/accounts/{account_name}/topics
GET /api/accounts/{account_name}/communications?limit=10
GET /api/accounts/{account_name}/personal-details
GET /api/accounts/{account_name}/team-contacts
GET /api/accounts/{account_name}/graph
```

## Project Structure

```
Graphiti-knowledge-graph/
├── adapters/               # Email provider adapters
│   ├── base_adapter.py     # Abstract base class
│   ├── gmail_adapter.py    # Gmail/Google Workspace
│   └── outlook_adapter.py  # Microsoft 365
├── config/                 # Configuration
│   ├── settings.py         # Environment settings
│   ├── entity_types.py     # Entity definitions (Contact, Account, etc.)
│   ├── edge_types.py       # Relationship definitions
│   └── accounts.py         # Target accounts configuration
├── middleware/             # API middleware
│   └── auth.py             # API key authentication
├── models/                 # Data models
│   ├── email.py            # Email data class
│   └── lead.py             # Lead model (n8n integration)
├── services/               # Business logic
│   ├── graphiti_service.py # Graphiti wrapper
│   └── sync_service.py     # Email sync orchestration
├── n8n-workflows/          # n8n workflow templates
│   └── email-automation-graphiti.json
├── visualization/          # D3.js graph viewer
│   └── index.html
├── api_server.py           # FastAPI server
├── Dockerfile              # Container build
├── docker-compose.yml      # Local development
├── railway.toml            # Railway deployment config
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_KEY` | API key for authentication | Production |
| `API_HOST` | API server host | No (default: 0.0.0.0) |
| `API_PORT` | API server port | No (default: 8080) |
| `OPENAI_API_KEY` | OpenRouter/OpenAI API key | Yes |
| `OPENAI_BASE_URL` | API base URL | Yes |
| `MODEL_NAME` | LLM model to use | Yes |
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `GOOGLE_CLIENT_ID` | Gmail OAuth client ID | For Gmail sync |
| `GOOGLE_CLIENT_SECRET` | Gmail OAuth secret | For Gmail sync |
| `TEAM_DOMAINS` | Your company email domains | Yes |

## Railway Deployment Costs (Estimated)

| Service | RAM | Cost/Month |
|---------|-----|------------|
| Graphiti API | 256-512MB | ~$5-7 |
| Neo4j | 1GB | ~$10-15 |
| **Total** | | **~$15-22** |

Plus LLM API costs (OpenRouter):
- gpt-4o-mini: ~$0.15/1M tokens
- claude-sonnet: ~$3/1M tokens

## Comparison: Graphiti vs Pinecone

| Feature | Pinecone | Graphiti |
|---------|----------|----------|
| Storage type | Vector DB | Knowledge Graph |
| Lookup speed | Fast (ID) | Fast (cache + graph) |
| Relationships | None | Full graph |
| Communication history | Manual | Automatic |
| Personal details | Flat metadata | Structured entities |
| Temporal tracking | None | Built-in |
| Personalization context | Limited | Rich |
| Cost | ~$0-70/mo | ~$15-22/mo + LLM |

## Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_setup.py

# Start locally
docker-compose up -d
python api_server.py
```

## Troubleshooting

### Neo4j Connection Issues
```bash
# Check Neo4j is running
docker logs neo4j

# Verify connection
curl http://localhost:7474
```

### API Key Authentication Errors
- Ensure `X-API-Key` header is set in n8n HTTP Request nodes
- Check the credential ID matches in the workflow JSON
- Verify `API_KEY` env var is set in Railway

### LLM Extraction Failures
- Check OpenRouter API key is valid
- Verify model name exists (e.g., `openai/gpt-4o-mini`)
- Monitor rate limits on OpenRouter dashboard

## License

MIT
