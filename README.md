# Market Intelligence Scout

AI-powered competitive intelligence platform that discovers, verifies, and scores technical features from public sources. Give it a company name — it returns a structured executive report with confidence-scored, cross-verified technical updates from the past 7 days.

**Live:** [market-scout.me](https://market-scout.me) · **API:** [api.market-scout.me](https://api.market-scout.me)

---

## How It Works

A 10-node **LangGraph** pipeline runs asynchronously via **Celery**, so the API returns a task ID immediately and you poll for results. Every pipeline run follows this path:

```
Input → Guardrails → Search Agent → Scraper Agent → Date Validation
      → Content Filter → Authority Check → Feature Extraction
      → Verification (SBERT) → Confidence Scoring → Synthesis → Report
```

| Node | Type | What it does |
|------|------|--------------|
| **Guardrails** | Deterministic + LLM | OWASP input sanitisation, Redis rate limiting (10 req/60s), LLM semantic intent check |
| **Search Agent** | Agentic | Generates 4 search strategies via LLM, executes against Tavily API, deduplicates URLs, retries weak results (max 2 iterations) |
| **Scraper Agent** | Agentic | Parallel URL scraping with LLM-selected strategy (BeautifulSoup → Newspaper3k → Playwright fallback), Redis article cache |
| **Date Validation** | Deterministic | Enforces 7-day recency window, discards undated articles, creates Redis audit trail |
| **Content Filter** | Deterministic | Keyword density check — removes job postings, earnings reports, marketing fluff |
| **Authority Check** | Deterministic | Domain reputation scoring (github.com = 0.9, unknown = 0.5), sorts by credibility |
| **Feature Extraction** | Agentic | LLM extracts structured features: title, 2–3 sentence description, category, metrics, evidence quotes |
| **Verification** | Deterministic (ML) | SBERT embeddings + cosine similarity (threshold 0.85) clusters duplicate features across sources |
| **Scoring** | Deterministic | `confidence = 0.3×recency + 0.4×verification + 0.3×authority` |
| **Synthesis** | Agentic | LLM generates executive summary, ranks features by confidence, formats final JSON report |

Five early-exit nodes (`no_results`, `no_articles`, `all_expired`, `no_technical`, `no_features`) allow graceful degradation — the API always returns a consistent response shape.

---

## Tech Stack

**Backend:** Python 3.10+, FastAPI, LangGraph, Celery, APScheduler, NVIDIA NIM (`meta/llama-3.1-8b-instruct`), Tavily, Sentence-BERT, SQLAlchemy, Redis, Pydantic, Sentry

**Frontend:** React 19, Vite, Tailwind CSS, React Router

**Infrastructure:** Docker Compose (7 services), PostgreSQL 15, Redis 7, Prometheus, Grafana, OpenTelemetry

**Deployment:** Azure VM (backend), Azure Static Web Apps / Vercel (frontend), GitHub Actions CI/CD

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Docker Desktop**
- **Git**

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd JatayuS5-Housestark
```

### 2. Create the `.env` File

```env
# Required
NVIDIA_API_KEYS=your_nvidia_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional
HF_API_TOKEN=your_huggingface_token      # Raises HF Inference API rate limits
SENTRY_DSN_BACKEND=your_sentry_dsn       # Error tracking
EMAIL_SENDER=your_gmail_address          # For scheduled email reports
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json
GOOGLE_TOKEN_PATH=credentials/token.json
CORS_ORIGINS=                            # Extra allowed origins (comma-separated)
```

> **API Keys:**
> - **NVIDIA NIM:** [build.nvidia.com](https://build.nvidia.com/) → Get API Key
> - **Tavily:** [tavily.com](https://tavily.com/) → Get API Key (free tier available)

### 3. Start Docker Services

```bash
docker compose up -d
```

This starts 7 services:

| Service | Port | Purpose |
|---------|------|---------|
| `app` | 8000 | FastAPI backend |
| `celery_worker` | 9100 | Async pipeline execution |
| `flower` | 5555 | Celery task monitoring |
| `postgres` | 5433 | Persistent storage |
| `redis` | 6379 | Cache, rate limiting, task broker |
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3000 | Monitoring dashboard |

```bash
docker compose ps   # verify all running
```

### 4. Run Locally (without Docker app container)

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Start infrastructure only, then run app + worker locally:

```bash
docker compose up -d postgres redis prometheus grafana

# Terminal 1 — FastAPI
uvicorn app.main:app --reload

# Terminal 2 — Celery worker
celery -A app.celery_app worker --loglevel=info --concurrency=1
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | — |
| **Backend API** | http://localhost:8000 | — |
| **Swagger Docs** | http://localhost:8000/docs | — |
| **Flower** | http://localhost:5555 | — |
| **Prometheus** | http://localhost:9090 | — |
| **Grafana** | http://localhost:3000 | admin / admin |

---

## API Reference

### Pipeline

```
POST /run-agent
  Body: { "company_name": "OpenAI", "date_window_days": 7, "session_id": "...", "force_refresh": false }
  Returns: { "task_id": "...", "status": "queued" }  OR cached report

GET /task-status/{task_id}
  Returns: { "status": "PROGRESS|SUCCESS|FAILURE", "meta": { "current_node": "...", "progress": 0 } }
```

### History

```
GET  /reports/{company_name}?limit=10     # Historical reports from PostgreSQL
GET  /features/{company_name}?limit=50    # All extracted features for a company
DELETE /reports/{report_id}               # Delete a report and its features (204)
```

### Companies

```
GET    /competitors                        # List all tracked companies
POST   /competitors                        # Create company entry
DELETE /competitors/{competitor_id}        # Delete company + all its data (204)
```

### Scheduled Reports

```
POST   /schedules    Body: { "company_name": "...", "email": "...", "scheduled_at": "<ISO UTC>" }
GET    /schedules    # List all scheduled jobs
DELETE /schedules/{job_id}                 # Cancel and delete a job (204)
```

### RAG (Report Q&A)

```
POST /rag/upload     # Upload a PDF → indexes into FAISS/Redis for session_id
POST /rag/ask        # Ask questions against the indexed report or PDF
```

### System

```
GET  /health                  # { status, version, timestamp }
GET  /metrics                 # Prometheus metrics
POST /system/clear-cache      # Flush Redis
POST /system/clear-storage    # Wipe all DB tables
```

---

## Database Schema

Three PostgreSQL tables (SQLAlchemy ORM):

```
competitors:  id, name (unique), industry, created_at
reports:      id, competitor_id→, executive_summary, total_sources, total_features,
              all_sources (JSON), metadata (JSON), created_at
features:     id, competitor_id→, report_id→, feature_title, feature_text,
              description, category, confidence_score, source_count,
              source_url, evidence, metrics (JSON), created_at
```

---

## Observability

14 Prometheus metrics tracked across API, pipeline, LLM, cache, and scraper layers. The Grafana dashboard (auto-provisioned) has 16 panels in 4 rows:

- **Pipeline Overview** — Total runs, success rate, active pipelines, avg duration
- **Pipeline Performance** — Runs over time, per-node latency
- **LLM & Intelligence** — Call counts by agent, token usage, confidence score distribution
- **Scraping & Cache** — Strategy performance, cache hit/miss, features by category

---

## Project Structure

```
JatayuS5-Housestark/
├── app/
│   ├── main.py           # FastAPI app, middleware, all endpoints
│   ├── config.py         # Pydantic BaseSettings (all env vars)
│   ├── api_models.py     # Request/response Pydantic models
│   ├── celery_app.py     # Celery broker config
│   ├── services/
│   │   └── pipeline_enqueue.py   # Cache-or-enqueue logic
│   └── rag/
│       ├── routes.py     # /rag/upload and /rag/ask endpoints
│       ├── service.py    # PDF + report indexing, Q&A via LLM
│       ├── embedding.py  # SBERT embeddings
│       ├── vector_store.py  # FAISS-backed store (Redis-persisted)
│       └── pdf_loader.py
├── agents/
│   ├── search_agent/     # agent.py, planner.py, executor.py, critic.py, memory.py
│   └── scraper_agent/    # agent.py, planner.py, critic.py, memory.py
│       └── tools/        # bs4.py, newspaper.py, playwright.py, cleaners.py, dates.py
├── nodes/                # guardrails, date_validation, content_filter,
│                         # authority_check, feature_extraction, verification,
│                         # scoring, synthesis
├── graph/
│   ├── builder.py        # LangGraph StateGraph wiring
│   └── state.py          # GraphState TypedDict
├── tasks/
│   ├── pipeline_tasks.py # Celery task: run_market_pipeline
│   └── scheduled_tasks.py
├── scheduler/
│   ├── scheduler.py      # APScheduler setup
│   ├── job_runner.py
│   └── email_service.py
├── mcp_server/
│   ├── server.py         # FastMCP server exposing send_email_report tool
│   └── tools/
│       └── gmail_tool.py
├── services/
│   └── gmail_api_service.py
├── llm/
│   └── nvidia_client.py  # OpenAI-SDK client → NVIDIA NIM, retry + metrics
├── database/
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic CRUD schemas
│   ├── crud.py           # Create/read/delete operations
│   └── session.py        # Engine + session factory
├── cache/
│   ├── redis_client.py   # get/set cache, rate limiting, audit log
│   └── report_cache.py
├── observability/
│   ├── metrics.py        # 14 Prometheus metric definitions
│   └── tracing.py        # OpenTelemetry setup
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/          # Auto-provisioned dashboard + datasource
├── utils/
│   └── feature_utils.py
├── frontend/             # React 19 + Vite + Tailwind SPA
├── .github/workflows/
│   └── deploy.yml        # GitHub Actions → SSH → docker compose up --build
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

---

## Configuration Reference

All settings in `app/config.py`, overridable via `.env`:

| Key | Default | Description |
|-----|---------|-------------|
| `NVIDIA_API_KEYS` | — | NVIDIA NIM API key(s) |
| `LLM_MODEL` | `meta/llama-3.1-8b-instruct` | Active LLM model |
| `LLM_MAX_TOKENS` | `4096` | Max generation tokens |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `TAVILY_API_KEY` | — | Web search API key |
| `SEARCH_DEPTH` | `advanced` | Tavily search depth |
| `SEARCH_MAX_RESULTS` | `15` | Results per query |
| `HF_API_TOKEN` | — | HuggingFace token (optional) |
| `DATABASE_URL` | `postgresql://admin:admin@127.0.0.1:5433/market_db` | PostgreSQL connection |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `CACHE_EXPIRY` | `21600` | Redis TTL in seconds (6 h) |
| `MAX_INPUT_LENGTH` | `200` | Max company name characters |
| `RATE_LIMIT_REQUESTS` | `10` | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window in seconds |
| `SCRAPE_TIMEOUT` | `15` | Seconds per HTTP request |
| `MAX_ARTICLE_LENGTH` | `8000` | Characters kept per article |
| `SBERT_MODEL` | `all-MiniLM-L6-v2` | Sentence-BERT model |
| `SIMILARITY_THRESHOLD` | `0.85` | Cosine similarity for clustering |
| `DATE_WINDOW_DAYS` | `7` | Recency filter (days) |
| `MAX_RETRIES` | `3` | LLM retry attempts |

---

## Useful Commands

```bash
# Docker management
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose ps                 # Check status
docker compose logs -f celery_worker  # Stream Celery logs
docker compose restart grafana    # Restart one service
docker compose up -d --build app  # Rebuild and restart app

# Database access
docker exec -it market_postgres psql -U admin -d market_db

# Redis access
docker exec -it market_redis redis-cli

# Celery task monitoring (alternative to Flower UI)
celery -A app.celery_app inspect active
```

---

## Security (OWASP)

| Control | Implementation |
|---------|---------------|
| **A03 Injection** | HTML stripping, regex format validation, blocklist keywords, Pydantic schema validation |
| **A05 Misconfiguration** | All secrets via environment variables, never hardcoded |
| **A07 XSS** | HTML sanitisation + structured JSON responses (no raw HTML output) |
| **A10 SSRF** | Domain allowlist in `config.py`; every scraped URL validated against `ALLOWED_DOMAINS` and `ALLOWED_DOMAIN_PREFIXES` |
| **Rate Limiting** | Redis-backed counter: 10 requests / 60 seconds, enforced before any LLM call |
| **Semantic Guard** | LLM checks company name intent at temperature=0 to catch prompt injection |

---

## Deployment

Backend is containerised and deployed on an **Azure VM** (Ubuntu LTS). Frontend is deployed to **Azure Static Web Apps** (also mirrored on Vercel). CI/CD is via **GitHub Actions** — every push to `main` SSHes into the VM and runs `docker compose up -d --build`.

DNS via Namecheap, HTTPS via Certbot (backend) and Azure (frontend).
