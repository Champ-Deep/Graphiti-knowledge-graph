# Sales Outreach Integration Guide

Complete guide for integrating the Knowledge Graph with your sales outreach process.

---

## 🎯 Overview

This knowledge graph now provides **comprehensive prospect intelligence** by aggregating data from multiple sources:

- **Email communications** (Gmail, Outlook)
- **Web analytics** (Google Analytics, Segment)
- **Social media** (LinkedIn, Twitter)
- **Enrichment APIs** (Clearbit, BuiltWith, People Data Labs)

All data is unified into **comprehensive profiles** with:
- **Firmographics**: Company data (industry, size, revenue, funding)
- **Technographics**: Technology stack (CRM, tools, infrastructure)
- **Psychographics**: Interests, preferences, personal details
- **Engagement signals**: Email opens, web visits, social interactions
- **Intent scoring**: Buying intent based on multi-channel signals

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SALES OUTREACH AGENT                   │
│           (Your sales automation/CRM system)             │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API
                        ↓
┌─────────────────────────────────────────────────────────┐
│              KNOWLEDGE GRAPH API SERVER                  │
│         (FastAPI - Port 8080)                           │
│                                                          │
│  Endpoints:                                              │
│  • POST /api/profiles/contact                           │
│  • POST /api/profiles/account                           │
│  • POST /api/outreach/generate                          │
│  • GET  /api/accounts/{name}/intent                     │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
┌───────────────┐ ┌──────────┐ ┌──────────────┐
│ Profile       │ │ Intent   │ │ Outreach     │
│ Builder       │ │ Scorer   │ │ Personalizer │
└───────┬───────┘ └────┬─────┘ └──────┬───────┘
        │              │              │
        └──────────────┼──────────────┘
                       ↓
        ┌──────────────────────────┐
        │   GRAPHITI SERVICE       │
        │   (Knowledge Graph Core) │
        │                          │
        │   • Neo4j Database       │
        │   • LLM Entity Extraction│
        │   • Temporal Tracking    │
        └──────────────────────────┘
                       ↓
        ┌──────────────────────────┐
        │      DATA SOURCES        │
        │                          │
        │  Email:                  │
        │  • Gmail API             │
        │  • Microsoft Graph       │
        │                          │
        │  Web Analytics:          │
        │  • Google Analytics 4    │
        │  • Segment CDP           │
        │                          │
        │  Social:                 │
        │  • LinkedIn API          │
        │  • Twitter API           │
        │                          │
        │  Enrichment:             │
        │  • Clearbit              │
        │  • BuiltWith             │
        │  • People Data Labs      │
        └──────────────────────────┘
```

---

## 📦 What's New

### 1. **Universal Data Model**
- `UniversalEvent` - Normalized model for ANY data source
- Supports email, web visits, social engagement, enrichment data, and custom events
- Automatic entity extraction and relationship mapping

### 2. **Universal Adapters**
All adapters implement `BaseUniversalAdapter` for consistent integration:

#### **Web Analytics Adapters**
- `GoogleAnalyticsAdapter` - GA4 page views, sessions, engagement
- `SegmentAdapter` - Segment CDP events (requires data warehouse)

#### **Social Media Adapters**
- `LinkedInAdapter` - Company page engagement, mentions
- `TwitterAdapter` - Mentions, engagement
- `LinkedInEnrichmentAdapter` - Profile enrichment

#### **Enrichment Adapters**
- `ClearbitAdapter` - Firmographics + technographics
- `BuiltWithAdapter` - Technology stack detection
- `PeopleDataLabsAdapter` - Contact enrichment

### 3. **Profile Builder Service**
Aggregates all data sources into comprehensive profiles:
- `build_contact_profile()` - Complete contact intelligence
- `build_account_profile()` - Company-level intelligence

### 4. **Intent Scoring Engine**
- Configurable multi-signal intent scoring
- Time decay for signals
- Firmographic fit multipliers
- Buying stage identification
- Next best action recommendations

### 5. **Outreach Personalization Engine**
LLM-powered outreach generation:
- Personalized emails (subject + body)
- LinkedIn messages
- Call scripts
- Based on comprehensive profile data

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Optional: Web analytics
pip install google-analytics-data

# Optional: Enrichment APIs
# (No additional packages needed - uses REST APIs)
```

### 2. Configure Data Sources

Edit `config/data_sources.yaml` or set environment variables:

```bash
# Required (existing)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export OPENAI_API_KEY="sk-..."

# Optional: Web Analytics
export GA4_PROPERTY_ID="123456789"
export GA4_CREDENTIALS_PATH="credentials/ga4.json"

# Optional: Social Media
export LINKEDIN_ACCESS_TOKEN="your-token"
export LINKEDIN_ORG_ID="12345"
export TWITTER_BEARER_TOKEN="your-token"

# Optional: Enrichment
export CLEARBIT_API_KEY="sk_..."
export BUILTWITH_API_KEY="..."
export PDL_API_KEY="..."
```

### 3. Run the API Server

```bash
python api_server.py
```

Server will start on `http://localhost:8080`

### 4. Test with Example Script

```bash
python examples/sales_outreach_example.py
```

---

## 📡 API Endpoints

### **Build Contact Profile**

Get comprehensive intel on a specific contact.

```bash
POST /api/profiles/contact

{
  "account_name": "acme-corp",
  "contact_email": "john.smith@acme.com",
  "enrich": true
}
```

**Response:**
```json
{
  "success": true,
  "profile": {
    "contact": {
      "name": "John Smith",
      "title": "VP of Engineering",
      "email": "john.smith@acme.com",
      "seniority": "VP",
      "social_profiles": {...}
    },
    "account": {
      "name": "Acme Corp",
      "industry": "SaaS",
      "employee_count": 1200
    },
    "firmographics": {
      "revenue": 50000000,
      "funding": 25000000,
      "founded": 2015
    },
    "technographics": {
      "technologies": [
        {"name": "Salesforce", "category": "CRM"},
        {"name": "AWS", "category": "Infrastructure"}
      ]
    },
    "psychographics": {
      "interests": [
        {"topic": "machine learning", "level": "high"},
        {"topic": "python", "level": "medium"}
      ],
      "personal_details": [
        {"category": "family", "detail": "Has 2 kids"},
        {"category": "hobby", "detail": "Plays golf"}
      ]
    },
    "engagement": {
      "overall_score": 87,
      "email": {"total_emails": 12, "response_rate": 0.75},
      "web": {"total_page_views": 8, "high_intent_pages": ["pricing", "demo"]},
      "social": {"total_engagements": 3}
    },
    "intent": {
      "score": 85,
      "level": "high",
      "signals": ["pricing_interest", "demo_request", "active_communication"]
    },
    "recommended_approach": "High intent - suggest immediate demo. Reference pricing page visits."
  }
}
```

### **Build Account Profile**

Get company-level intelligence.

```bash
POST /api/profiles/account

{
  "account_name": "acme-corp",
  "enrich": true
}
```

### **Generate Personalized Outreach**

Create AI-generated, personalized outreach content.

```bash
POST /api/outreach/generate

{
  "account_name": "acme-corp",
  "contact_email": "john.smith@acme.com",
  "purpose": "intro",           # intro, follow_up, demo_request, value_prop
  "tone": "professional",        # professional, casual, friendly, urgent
  "length": "short",            # short, medium, long
  "channel": "email"            # email, linkedin, call_script
}
```

**Response:**
```json
{
  "success": true,
  "outreach": {
    "subject": "Python ML automation for Acme's engineering team",
    "body": "Hi John,\n\nI noticed you've been researching ML automation solutions...",
    "personalization_notes": [
      "Referenced interest in machine learning",
      "Mentioned pricing page visit",
      "Personalized with Python expertise"
    ],
    "confidence_score": 92
  },
  "profile_summary": {
    "intent_score": 85,
    "intent_level": "high",
    "engagement_score": 87
  }
}
```

### **Get Intent Score**

```bash
GET /api/accounts/acme-corp/intent
```

### **Get Firmographics**

```bash
GET /api/accounts/acme-corp/firmographics?enrich=true
```

---

## 🔌 Integration Examples

### Python (Requests)

```python
import requests

# Build contact profile
response = requests.post("http://localhost:8080/api/profiles/contact", json={
    "account_name": "acme-corp",
    "contact_email": "john.smith@acme.com",
    "enrich": True
})

profile = response.json()['profile']

# Check intent
if profile['intent']['level'] == 'high':
    # Generate personalized email
    email_response = requests.post("http://localhost:8080/api/outreach/generate", json={
        "account_name": "acme-corp",
        "contact_email": "john.smith@acme.com",
        "purpose": "demo_request",
        "channel": "email"
    })

    email = email_response.json()['outreach']
    print(f"Subject: {email['subject']}")
    print(f"Body:\n{email['body']}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function buildProfile(accountName, contactEmail) {
  const response = await axios.post('http://localhost:8080/api/profiles/contact', {
    account_name: accountName,
    contact_email: contactEmail,
    enrich: true
  });

  return response.data.profile;
}

async function generateOutreach(accountName, contactEmail) {
  const response = await axios.post('http://localhost:8080/api/outreach/generate', {
    account_name: accountName,
    contact_email: contactEmail,
    purpose: 'intro',
    channel: 'email'
  });

  return response.data.outreach;
}

// Usage
(async () => {
  const profile = await buildProfile('acme-corp', 'john.smith@acme.com');
  console.log('Intent Score:', profile.intent.score);

  const email = await generateOutreach('acme-corp', 'john.smith@acme.com');
  console.log('Generated Email:', email.subject);
})();
```

### Zapier/Make.com Integration

```json
{
  "url": "http://your-server:8080/api/outreach/generate",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "account_name": "{{account_name}}",
    "contact_email": "{{contact_email}}",
    "purpose": "intro",
    "channel": "email"
  }
}
```

---

## 🔧 Configuration

### Intent Scoring

Customize intent scoring in `config/data_sources.yaml`:

```yaml
intent_scoring:
  high_intent_threshold: 70
  medium_intent_threshold: 40
  recency_boost: true
  icp_fit_multiplier: 1.3

  signals:
    pricing_page_visit: 0.20
    demo_request: 0.30
    email_reply: 0.15
    # ... customize all signal weights
```

### ICP (Ideal Customer Profile)

Define your ideal customer for firmographic fit scoring:

```yaml
icp:
  employee_count:
    min: 500
    max: 5000

  industries:
    - "SaaS"
    - "Technology"
    - "Fintech"

  min_revenue: 10000000
  min_funding: 5000000

  complementary_tech:
    - "Salesforce"
    - "HubSpot"
    - "Segment"
```

### Data Sync

Configure sync intervals:

```yaml
sync:
  intervals:
    email: 1        # hours
    web_analytics: 24
    social_media: 12
    enrichment: 168

  historical_windows:
    email: 90       # days
    web_analytics: 30
    social_media: 14
```

---

## 📊 Data Flow

### 1. Data Ingestion

```python
from adapters.web_analytics_adapter import GoogleAnalyticsAdapter
from services.graphiti_service import GraphitiService

# Initialize adapter
ga_adapter = GoogleAnalyticsAdapter({
    'property_id': 'your-property-id',
    'credentials_path': 'path/to/creds.json'
})

await ga_adapter.connect()

# Fetch events
async for event in ga_adapter.fetch_events(
    since=datetime.now() - timedelta(days=30),
    limit=1000
):
    # Convert to episode and ingest
    episode_content = event.to_episode_content()
    await graphiti_service.ingest_event(event, account_name="acme-corp")
```

### 2. Profile Building

```python
from services.profile_builder import ProfileBuilder

profile_builder = ProfileBuilder(
    graphiti_service=graphiti_service,
    enrichment_configs={
        'clearbit': {'api_key': 'sk_...'},
        'builtwith': {'api_key': '...'}
    }
)

profile = await profile_builder.build_contact_profile(
    account_name="acme-corp",
    contact_email="john.smith@acme.com",
    enrich=True
)
```

### 3. Outreach Generation

```python
from services.outreach_personalizer import OutreachPersonalizer

personalizer = OutreachPersonalizer(
    llm_provider="openai",
    model="gpt-4"
)

email = await personalizer.generate_email(
    profile=profile,
    purpose="intro",
    tone="professional",
    length="short"
)
```

---

## 🎓 Best Practices

### 1. **Data Quality**
- Enable all data sources you have access to
- Keep enrichment APIs updated
- Sync regularly to capture fresh signals

### 2. **Intent Scoring**
- Customize signal weights for your business
- Adjust thresholds based on conversion data
- Monitor and iterate on ICP definition

### 3. **Personalization**
- Don't overdo it - max 2-3 personalization points
- Balance automation with human review
- Test different tones and lengths

### 4. **Privacy & Compliance**
- Only track users who have consented
- Respect GDPR/CCPA requirements
- Provide opt-out mechanisms

---

## 🐛 Troubleshooting

### "No data in knowledge graph"
- Check that email sync has run
- Verify account domains are configured
- Check Neo4j connection

### "Enrichment not working"
- Verify API keys are set
- Check API rate limits
- Ensure domains are valid

### "Low confidence scores"
- Need more data sources
- Wait for more engagement signals
- Check data quality

---

## 🚦 Next Steps

1. **Set up additional data sources**
   - Configure web analytics
   - Connect social media accounts
   - Add enrichment API keys

2. **Customize intent scoring**
   - Define your ICP
   - Adjust signal weights
   - Set appropriate thresholds

3. **Integrate with your sales tools**
   - Connect to CRM (Salesforce, HubSpot)
   - Set up automated workflows
   - Build dashboards

4. **Monitor and optimize**
   - Track conversion rates by intent score
   - A/B test outreach templates
   - Refine personalization strategies

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8080/docs (when server is running)
- **Example Scripts**: `examples/sales_outreach_example.py`
- **Configuration**: `config/data_sources.yaml`
- **Graphiti Docs**: https://github.com/getzep/graphiti

---

## 🤝 Support

For issues or questions:
1. Check this guide
2. Review example scripts
3. Check API docs at `/docs`
4. Open an issue on GitHub

---

## ✅ Checklist

Use this to verify your integration:

- [ ] API server running on port 8080
- [ ] Email sync configured and working
- [ ] At least one enrichment API configured
- [ ] Successfully built a contact profile
- [ ] Successfully generated personalized outreach
- [ ] Intent scoring working correctly
- [ ] Integrated with sales outreach tool
- [ ] Tested end-to-end workflow
- [ ] Monitoring and logging enabled

---

**You're now ready to build comprehensive profiles and personalize outreach at scale! 🎉**
