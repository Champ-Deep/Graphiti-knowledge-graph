# Graphiti Knowledge Graph

A temporal knowledge graph system for building AI-aware relationship maps from email communications. Designed to integrate with the CEO WhatsApp Assistant for intelligent account insights via ElevenLabs.

## 🚀 Quick Links

- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Deploy to Railway, Render, DigitalOcean, or AWS
- **[ElevenLabs Integration](./ELEVENLABS_INTEGRATION.md)** - Connect to WhatsApp for voice + text assistant
- **[Quick Deploy Script](./deploy.sh)** - One-command deployment for Docker/Railway/Render

## Overview

This system ingests emails from Gmail/Outlook and builds a knowledge graph that tracks:
- **Contacts** - People at target accounts
- **Accounts** - Companies/MQAs being tracked
- **Team Members** - Internal sales/marketing team
- **Topics** - Discussion subjects
- **Personal Details** - Family, hobbies, interests
- **Communications** - Interaction events with temporal tracking

## Architecture

```
WhatsApp (Text/Voice)
        ↓
ElevenLabs Agent (Conversational AI)
        ↓
Custom Tools (Real-time API calls)
        ↓
[FastAPI Server] (:8080) ← This Repository
        ↓
[GraphitiService] (Knowledge Graph Layer)
        ↓
[Neo4j Database] (Graph Storage)
        ↓
[Email Sources] (Gmail/Outlook sync)
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker (for Neo4j)
- Gmail OAuth credentials (for email ingestion)

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Graphiti-knowledge-graph.git
cd Graphiti-knowledge-graph

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start Neo4j

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.26.2
```

### 4. Configure Gmail OAuth

```bash
python setup_gmail_oauth.py
```

### 5. Run the API Server

```bash
python api_server.py
```

The API will be available at `http://localhost:8080`

## API Endpoints

### Query Account Knowledge

```http
POST /api/query
Content-Type: application/json

{
  "account": "acme-corp",
  "query": "Who from our team contacted this account?"
}
```

### Pre-built Queries

```http
GET /api/accounts/{account_name}/contacts
GET /api/accounts/{account_name}/topics
GET /api/accounts/{account_name}/communications
GET /api/accounts/{account_name}/personal-details
```

### Ingest Emails

```http
POST /api/sync/{account_name}
```

## WhatsApp Assistant Integration

The CEO WhatsApp Assistant should connect to this API to query account information.

### Example Integration (Python)

```python
import httpx

KNOWLEDGE_GRAPH_URL = "http://localhost:8080"

async def query_account(account: str, question: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{KNOWLEDGE_GRAPH_URL}/api/query",
            json={"account": account, "query": question}
        )
        return response.json()

# Usage
result = await query_account(
    "acme-corp",
    "What personal details do we know about the CEO?"
)
```

### Example Integration (Node.js)

```javascript
const axios = require('axios');

const KNOWLEDGE_GRAPH_URL = 'http://localhost:8080';

async function queryAccount(account, question) {
  const response = await axios.post(`${KNOWLEDGE_GRAPH_URL}/api/query`, {
    account,
    query: question,
  });
  return response.data;
}
```

## Project Structure

```
Graphiti-knowledge-graph/
├── adapters/              # Email provider adapters
│   ├── base_adapter.py    # Abstract base class
│   ├── gmail_adapter.py   # Gmail/Google Workspace
│   └── outlook_adapter.py # Microsoft 365
├── config/                # Configuration
│   ├── settings.py        # Environment settings
│   ├── entity_types.py    # Custom entity definitions
│   └── edge_types.py      # Relationship definitions
├── models/                # Data models
│   └── email.py           # Email data class
├── services/              # Business logic
│   ├── graphiti_service.py # Graphiti wrapper
│   └── sync_service.py    # Email sync orchestration
├── visualization/         # D3.js graph viewer
│   └── index.html
├── api_server.py          # FastAPI server (WhatsApp integration)
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenRouter API key | Yes |
| `OPENAI_BASE_URL` | API base URL | Yes |
| `MODEL_NAME` | LLM model to use | Yes |
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_USER` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `GOOGLE_CLIENT_ID` | Gmail OAuth client ID | For Gmail |
| `GOOGLE_CLIENT_SECRET` | Gmail OAuth secret | For Gmail |
| `TEAM_DOMAINS` | Your company domains | Yes |
| `API_HOST` | API server host | No (default: 0.0.0.0) |
| `API_PORT` | API server port | No (default: 8080) |

## Development

```bash
# Run tests
python test_setup.py

# Format code
black .

# Type check
mypy .
```

## Production Deployment

### Quick Deploy

Use the included deployment script:

```bash
# Interactive menu
./deploy.sh

# Or specify platform directly
./deploy.sh docker      # Local development
./deploy.sh railway     # Cloud deployment (recommended)
./deploy.sh render      # Free tier available
```

### Manual Deployment

See detailed guides:
- **Railway** (easiest): [DEPLOYMENT_GUIDE.md#railway-deployment](./DEPLOYMENT_GUIDE.md#railway-deployment)
- **Render** (free tier): [DEPLOYMENT_GUIDE.md#render-deployment](./DEPLOYMENT_GUIDE.md#render-deployment)
- **DigitalOcean** (cheapest): [DEPLOYMENT_GUIDE.md#digitalocean-vps-deployment](./DEPLOYMENT_GUIDE.md#digitalocean-vps-deployment)
- **AWS** (enterprise): [DEPLOYMENT_GUIDE.md#aws-deployment](./DEPLOYMENT_GUIDE.md#aws-deployment)

## ElevenLabs Integration

After deployment, connect to ElevenLabs for WhatsApp voice + text assistant:

1. **Deploy your API** (see above)
2. **Secure your API** with authentication
3. **Create ElevenLabs Agent** with custom tools
4. **Connect WhatsApp Business** account
5. **Test end-to-end**

Full guide: **[ELEVENLABS_INTEGRATION.md](./ELEVENLABS_INTEGRATION.md)**

### Example Conversations

**Voice Call:**
```
CEO: "Brief me on Acme Corp"
Assistant: "For Acme Corp, your key contacts are Sarah Johnson, CEO,
           and Mike Chen, VP Engineering. You last spoke 3 days ago
           about Q1 integration timelines. Personal note: Sarah's
           daughter just started at Stanford."
```

**Text Message:**
```
CEO: "What did we discuss with Google last week?"
Assistant: [Queries knowledge graph]
          "Last week you discussed:
          - API integration timeline with John Smith
          - Enterprise pricing with Lisa Wang
          - Security compliance requirements
          Follow-up: Send pricing proposal by end of month"
```

## License

MIT
