# Quick Start Guide

Get started with the Sales Intelligence Platform in **5 minutes**.

---

## 🚀 Quick Setup (3 Steps)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set these REQUIRED variables:
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# - OPENAI_API_KEY
```

**Minimum .env file:**
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here
OPENAI_API_KEY=sk-your-openai-key-here
```

### 3. Run Quick Start

```bash
python quickstart.py
```

This will:
- ✅ Validate your configuration
- ✅ Connect to the knowledge graph
- ✅ Show what's available
- ✅ Display next steps

---

## 🎯 What Works Out of the Box

**With JUST email data** (no enrichment APIs needed):
- ✅ Build contact profiles from email interactions
- ✅ Track engagement (email opens, replies, response times)
- ✅ Extract interests and topics from conversations
- ✅ Map relationships and org charts
- ✅ Calculate basic intent scores

**Example:**
```python
# Profile built from emails alone:
{
  "contact": {
    "name": "John Smith",
    "title": "VP of Engineering",
    "email": "john@acme.com"
  },
  "psychographics": {
    "interests": ["Python", "machine learning"],
    "personal_details": [{"category": "hobby", "detail": "plays golf"}]
  },
  "engagement": {
    "email_count": 12,
    "response_rate": 0.75,
    "avg_response_time": "4.2 hours"
  }
}
```

---

## 🔌 Start the API Server

```bash
python api_server.py
```

**Server starts on:** http://localhost:8080

**Test it:**
```bash
curl http://localhost:8080/health
```

**Interactive docs:** http://localhost:8080/docs

---

## 💡 Test the API

### Build a Profile

```bash
curl -X POST http://localhost:8080/api/profiles/account \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "acme-corp",
    "enrich": false
  }'
```

### Generate Personalized Email

```bash
curl -X POST http://localhost:8080/api/outreach/generate \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "acme-corp",
    "contact_email": "john@acme.com",
    "purpose": "intro",
    "channel": "email"
  }'
```

---

## 🎓 Next Steps

### 1. **Add Enrichment (Optional but Recommended)**

Get richer data by adding enrichment APIs to your `.env`:

```bash
# Clearbit - Firmographics + Technographics
CLEARBIT_API_KEY=sk_...

# BuiltWith - Technology Stack
BUILTWITH_API_KEY=...

# People Data Labs - Contact Data
PDL_API_KEY=...
```

**Restart the server** to enable enrichment:
```bash
python api_server.py
```

Now profiles include:
- Company revenue, funding, employee count
- Technology stack (Salesforce, AWS, etc.)
- Social profiles (LinkedIn, Twitter)
- Job history, skills, education

### 2. **Add Web Analytics (Optional)**

Track website visitors by adding to `.env`:

```bash
# Google Analytics 4
GA4_PROPERTY_ID=123456789
GA4_CREDENTIALS_PATH=credentials/ga4.json
```

Now you'll see:
- Page visits (especially pricing/demo pages!)
- Time on site, return visits
- Campaign tracking (UTM parameters)
- Intent signals from high-value pages

### 3. **Add Social Media (Optional)**

Track social engagement:

```bash
# LinkedIn
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_ORG_ID=...

# Twitter
TWITTER_BEARER_TOKEN=...
```

---

## 🐛 Troubleshooting

### "Configuration Errors" when starting

**Problem:** Missing required environment variables

**Solution:**
```bash
# Make sure .env exists and has these set:
cat .env | grep NEO4J_PASSWORD
cat .env | grep OPENAI_API_KEY

# If missing, edit .env and add them
nano .env
```

### "Connection refused" to Neo4j

**Problem:** Neo4j not running

**Solution:**
```bash
# Start Neo4j (if using Docker)
docker-compose up -d neo4j

# Or start your local Neo4j instance
# Check it's running on bolt://localhost:7687
```

### "No accounts found"

**Problem:** Knowledge graph is empty

**Solution:**
1. Configure Gmail OAuth: `python setup_gmail_oauth.py`
2. The API server automatically syncs emails on startup
3. Wait a few minutes for initial sync
4. Or run the sync service manually

### Import errors

**Problem:** Missing dependencies

**Solution:**
```bash
pip install -r requirements.txt

# If using Google Analytics:
pip install google-analytics-data

# If using web/social features:
pip install aiohttp pyyaml
```

---

## 📚 Learn More

- **Full Integration Guide:** [SALES_INTEGRATION_GUIDE.md](SALES_INTEGRATION_GUIDE.md)
- **What's New:** [WHATS_NEW.md](WHATS_NEW.md)
- **Example Scripts:** [examples/](examples/)
- **API Docs:** http://localhost:8080/docs (when server running)

---

## ✅ Success Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] .env file created with NEO4J and OPENAI settings
- [ ] Neo4j database running
- [ ] `python quickstart.py` runs without errors
- [ ] API server starts (`python api_server.py`)
- [ ] Health check passes (`curl http://localhost:8080/health`)
- [ ] Can build a profile via API
- [ ] (Optional) Enrichment APIs configured
- [ ] (Optional) Web analytics connected
- [ ] (Optional) Social media connected

---

**You're ready to build comprehensive profiles! 🎉**

**Questions?** Check the troubleshooting section above or read [SALES_INTEGRATION_GUIDE.md](SALES_INTEGRATION_GUIDE.md)
