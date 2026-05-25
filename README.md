<p align="center">
  <img src="frontend/public/vision.png" alt="Market Scout Logo" width="80" />
</p>

<h1 align="center">Market Intelligence Scout</h1>

<p align="center">
  <strong>AI-Powered Competitive Intelligence Platform</strong><br/>
  Discover, verify, and score technical features from public sources — powered by agentic AI.
</p>

<p align="center">
  <a href="https://market-scout.me"><img src="https://img.shields.io/badge/🌐_Live-market--scout.me-0B1120?style=for-the-badge" alt="Live Site" /></a>
  <a href="https://api.market-scout.me"><img src="https://img.shields.io/badge/⚡_API-api.market--scout.me-6366f1?style=for-the-badge" alt="API" /></a>
  <a href="https://api.market-scout.me/docs"><img src="https://img.shields.io/badge/📄_Docs-Swagger_UI-22c55e?style=for-the-badge" alt="API Docs" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/LangGraph-Agentic-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/NVIDIA_NIM-LLaMA_3.1-76B900?style=flat-square&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Sentry-Error_Tracking-362D59?style=flat-square&logo=sentry&logoColor=white" />
  <img src="https://img.shields.io/badge/Prometheus-Monitoring-E6522C?style=flat-square&logo=prometheus&logoColor=white" />
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Setup Guide](#-setup-guide)
- [Quick Reference](#-quick-reference)
- [API Reference](#-api-reference)
- [Database Schema](#-database-schema)
- [Observability](#-observability)
- [Project Structure](#-project-structure)
- [Configuration Reference](#-configuration-reference)
- [Security (OWASP)](#-security-owasp)
- [Deployment](#-deployment)
- [Useful Commands](#-useful-commands)

---

## 🧠 Overview

Give Market Scout a **company name** (e.g. _"OpenAI"_) and it will:

1. 🔍 Generate smart search queries using an LLM
2. 🌐 Search the web using the Tavily Search API
3. 📰 Scrape the top articles using 3 scraping strategies (BeautifulSoup, Newspaper3k, Playwright)
4. 📅 Filter out anything older than 7 days
5. 🧹 Remove non-technical content (job postings, marketing, earnings)
6. 🏛️ Score each source's authority and credibility
7. 🔬 Extract structured technical features using an LLM
8. ✅ Cross-verify features across sources using SBERT embeddings
9. 📊 Calculate confidence scores for each feature
10. 📝 Generate an executive intelligence report with citations

The result is a **structured briefing document** with verified technical features, confidence scores, source citations, and an executive summary.

---

## ⚙️ How It Works

A 10-node **LangGraph** pipeline runs asynchronously via **Celery**, so the API returns a task ID immediately and you poll for results:

```
Input → Guardrails → Search Agent → Scraper Agent → Date Validation
      → Content Filter → Authority Check → Feature Extraction
      → Verification (SBERT) → Confidence Scoring → Synthesis → Report
```

| # | Node | Type | What It Does |
|---|------|------|-------------|
| 1 | **🛡️ Guardrails** | Deterministic + LLM | OWASP input sanitisation, Redis rate limiting (10 req/60s), LLM semantic intent check |
| 2 | **🔍 Search Agent** | Agentic | Generates 4 search strategies via LLM, executes against Tavily API, deduplicates URLs, retries weak results (max 2 iterations) |
| 3 | **🕷️ Scraper Agent** | Agentic | Parallel URL scraping with LLM-selected strategy (BeautifulSoup → Newspaper3k → Playwright fallback), Redis article cache |
| 4 | **📅 Date Validation** | Deterministic | Enforces 7-day recency window, discards undated articles, creates Redis audit trail |
| 5 | **🧹 Content Filter** | Deterministic | Keyword density check — removes job postings, earnings reports, marketing fluff |
| 6 | **🏛️ Authority Check** | Deterministic | Domain reputation scoring (github.com = 0.9, unknown = 0.5), sorts by credibility |
| 7 | **🔬 Feature Extraction** | Agentic | LLM extracts structured features: title, description, category, metrics, evidence quotes |
| 8 | **✅ Verification** | Deterministic (ML) | SBERT embeddings + cosine similarity (threshold 0.85) clusters duplicate features across sources |
| 9 | **📊 Scoring** | Deterministic | `confidence = 0.3×recency + 0.4×verification + 0.3×authority` |
| 10 | **📝 Synthesis** | Agentic | LLM generates executive summary, ranks features by confidence, formats final JSON report |

> 💡 **Graceful Degradation:** Five early-exit nodes (`no_results`, `no_articles`, `all_expired`, `no_technical`, `no_features`) ensure the API always returns a consistent response shape — even when something goes wrong.

---

## 🏗️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| ![Python](https://img.shields.io/badge/-Python_3.10+-3776AB?style=flat-square&logo=python&logoColor=white) | Core language |
| ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) | REST API framework (async, auto-docs) |
| ![LangGraph](https://img.shields.io/badge/-LangGraph-FF6F00?style=flat-square) | Agentic pipeline orchestrator |
| ![Celery](https://img.shields.io/badge/-Celery-37814A?style=flat-square&logo=celery&logoColor=white) | Async task queue for pipeline execution |
| ![NVIDIA](https://img.shields.io/badge/-NVIDIA_NIM-76B900?style=flat-square&logo=nvidia&logoColor=white) | LLM engine (`meta/llama-3.1-8b-instruct`) |
| ![Tavily](https://img.shields.io/badge/-Tavily_API-5C6BC0?style=flat-square) | Web search engine |
| ![SBERT](https://img.shields.io/badge/-Sentence_BERT-FF9800?style=flat-square) | Semantic similarity for cross-source verification |
| ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL_15-4169E1?style=flat-square&logo=postgresql&logoColor=white) | Persistent relational database |
| ![Redis](https://img.shields.io/badge/-Redis_7-DC382D?style=flat-square&logo=redis&logoColor=white) | Cache, rate limiting, task broker |
| ![SQLAlchemy](https://img.shields.io/badge/-SQLAlchemy-CC2927?style=flat-square) | ORM for database operations |
| ![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white) | Request/response validation & settings |

### Frontend
| Technology | Purpose |
|---|---|
| ![React](https://img.shields.io/badge/-React_19-61DAFB?style=flat-square&logo=react&logoColor=black) | SPA frontend framework |
| ![Vite](https://img.shields.io/badge/-Vite-646CFF?style=flat-square&logo=vite&logoColor=white) | Build tool & dev server |
| ![React Router](https://img.shields.io/badge/-React_Router-CA4245?style=flat-square&logo=reactrouter&logoColor=white) | Client-side routing |
| ![Formspree](https://img.shields.io/badge/-Formspree-EF4444?style=flat-square) | User feedback collection widget |

### Infrastructure & Observability
| Technology | Purpose |
|---|---|
| ![Docker](https://img.shields.io/badge/-Docker_Compose-2496ED?style=flat-square&logo=docker&logoColor=white) | Container orchestration (7 services) |
| ![Prometheus](https://img.shields.io/badge/-Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white) | Metrics collection (14 custom metrics) |
| ![Grafana](https://img.shields.io/badge/-Grafana-F46800?style=flat-square&logo=grafana&logoColor=white) | Monitoring dashboard (16 panels) |
| ![Sentry](https://img.shields.io/badge/-Sentry-362D59?style=flat-square&logo=sentry&logoColor=white) | Error tracking (frontend + backend) |
| ![Clarity](https://img.shields.io/badge/-Microsoft_Clarity-0078D4?style=flat-square&logo=microsoft&logoColor=white) | User session analytics |
| ![OpenTelemetry](https://img.shields.io/badge/-OpenTelemetry-000000?style=flat-square) | Distributed tracing |

### Deployment
| Target | Platform |
|---|---|
| Backend | ![Azure](https://img.shields.io/badge/-Azure_VM-0078D4?style=flat-square&logo=microsoftazure&logoColor=white) (Ubuntu LTS, Docker) |
| Frontend | ![Vercel](https://img.shields.io/badge/-Vercel-000000?style=flat-square&logo=vercel&logoColor=white) / ![Azure](https://img.shields.io/badge/-Azure_Static_Web_Apps-0078D4?style=flat-square&logo=microsoftazure&logoColor=white) |
| CI/CD | ![GitHub Actions](https://img.shields.io/badge/-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) |
| Domain | ![Namecheap](https://img.shields.io/badge/-Namecheap-DE3723?style=flat-square) + Certbot SSL |

---

## 📦 Prerequisites

| Requirement | Version |
|---|---|
| 🐍 Python | 3.10+ |
| 📦 Node.js | 18+ |
| 🐳 Docker Desktop | Latest |
| 🔧 Git | Latest |

---

## 🚀 Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/Karthikpasupuleti11/Market_Scout_New-main.git
cd Market_Scout_New-main
```

### 2. Create the `.env` File

```env
# ── Required ──────────────────────────────────────────
NVIDIA_API_KEYS=your_nvidia_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# ── Optional ──────────────────────────────────────────
HF_API_TOKEN=your_huggingface_token         # Increases HF Inference API rate limits
SENTRY_DSN_BACKEND=your_sentry_dsn          # Backend error tracking
EMAIL_SENDER=your_gmail_address             # For scheduled email reports
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json
GOOGLE_TOKEN_PATH=credentials/token.json
CORS_ORIGINS=                               # Extra allowed origins (comma-separated)
```

> **🔑 Where to get API Keys:**
> | Key | Get it from |
> |-----|-------------|
> | NVIDIA NIM | [build.nvidia.com](https://build.nvidia.com/) → Get API Key |
> | Tavily | [tavily.com](https://tavily.com/) → Get API Key (free tier available) |
> | HuggingFace | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

### 3. Start Docker Services

```bash
docker compose up -d
```

This starts **7 services**:

| Service | Port | Purpose |
|---------|------|---------|
| 🖥️ `app` | `8000` | FastAPI backend |
| ⚙️ `celery_worker` | `9100` | Async pipeline execution |
| 🌸 `flower` | `5555` | Celery task monitoring |
| 🐘 `postgres` | `5433` | Persistent storage |
| 🔴 `redis` | `6379` | Cache, rate limiting, task broker |
| 📈 `prometheus` | `9090` | Metrics collection |
| 📊 `grafana` | `3000` | Monitoring dashboard |

```bash
docker compose ps   # Verify all services are running
```

### 4. Run Locally (without Docker app container)

<details>
<summary><strong>🍎 macOS / 🐧 Linux</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
</details>

<details>
<summary><strong>🪟 Windows</strong></summary>

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
</details>

Start infrastructure only, then run app + worker locally:

```bash
# Start dependencies
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

## 🔗 Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| 🖥️ **Frontend** | http://localhost:5173 | — |
| ⚡ **Backend API** | http://localhost:8000 | — |
| 📄 **Swagger Docs** | http://localhost:8000/docs | — |
| 🌸 **Flower** | http://localhost:5555 | — |
| 📈 **Prometheus** | http://localhost:9090 | — |
| 📊 **Grafana** | http://localhost:3000 | `admin` / `admin` |

---

## 📡 API Reference

### 🔬 Pipeline

```http
POST /run-agent
Content-Type: application/json

{
  "company_name": "OpenAI",
  "date_window_days": 7,
  "session_id": "optional-uuid",
  "force_refresh": false
}

# Returns: { "task_id": "...", "status": "queued" }  OR  cached report
```

```http
GET /task-status/{task_id}

# Returns: { "status": "PROGRESS|SUCCESS|FAILURE", "meta": { "current_node": "...", "progress": 0 } }
```

### 📁 History

```http
GET    /reports/{company_name}?limit=10      # Historical reports from PostgreSQL
GET    /features/{company_name}?limit=50     # All extracted features for a company
DELETE /reports/{report_id}                  # Delete a report and its features (204)
```

### 🏢 Companies

```http
GET    /competitors                           # List all tracked companies
POST   /competitors                           # Create company entry
DELETE /competitors/{competitor_id}           # Delete company + all its data (204)
```

### ⏰ Scheduled Reports

```http
POST   /schedules                             # Schedule a future report
       Body: { "company_name": "...", "email": "...", "scheduled_at": "<ISO UTC>" }
GET    /schedules                             # List all scheduled jobs
DELETE /schedules/{job_id}                    # Cancel and delete a job (204)
```

### 🤖 RAG (Report Q&A)

```http
POST /rag/upload                              # Upload a PDF → indexes into FAISS/Redis
POST /rag/ask                                 # Ask questions against the indexed report
```

### 🔧 System

```http
GET  /health                                  # { status, version, timestamp }
GET  /metrics                                 # Prometheus metrics
POST /system/clear-cache                      # Flush Redis
POST /system/clear-storage                    # Wipe all DB tables
```

---

## 🗄️ Database Schema

Three PostgreSQL tables managed by SQLAlchemy ORM:

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│  competitors │       │     reports      │       │      features        │
├──────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id (PK)      │──1:N──│ id (PK)          │──1:N──│ id (PK)              │
│ name (unique)│       │ competitor_id(FK) │       │ competitor_id (FK)   │
│ industry     │       │ executive_summary│       │ report_id (FK)       │
│ created_at   │       │ total_sources    │       │ feature_title        │
└──────────────┘       │ total_features   │       │ feature_text         │
                       │ all_sources (JSON)│       │ description          │
                       │ metadata (JSON)  │       │ category             │
                       │ created_at       │       │ confidence_score     │
                       └──────────────────┘       │ source_count         │
                                                  │ source_url           │
                                                  │ evidence             │
                                                  │ metrics (JSON)       │
                                                  │ created_at           │
                                                  └──────────────────────┘
```

---

## 📈 Observability & Integrations

### Prometheus Metrics

**14 custom metrics** tracked across API, pipeline, LLM, cache, and scraper layers:

| Layer | Metrics |
|-------|---------|
| 🌐 **API** | `api_requests_total`, `api_request_duration_secs` |
| ⚙️ **Pipeline** | `pipeline_runs_total`, `active_pipelines`, `node_latency_seconds`, `node_executions_total` |
| 🤖 **LLM** | `llm_calls_total`, `llm_call_duration_seconds`, `llm_tokens_total` |
| 🧠 **Intelligence** | `features_extracted_total`, `features_verified_total`, `feature_confidence_score`, `sources_analysed_per_run` |
| 💾 **Cache & Scraper** | `cache_operations_total`, `scraper_attempts_total`, `urls_discarded_total` |

### Grafana Dashboard

Auto-provisioned with **16 panels** across 4 rows:

| Row | Panels |
|-----|--------|
| 📊 Pipeline Overview | Total Runs · Success Rate · Active Pipelines · Avg Duration |
| ⏱️ Pipeline Performance | Runs Over Time · Per-Node Latency |
| 🤖 LLM & Intelligence | Call Counts by Agent · Token Usage · Confidence Distribution |
| 🕷️ Scraping & Cache | Strategy Performance · Cache Hit/Miss · Features by Category |

### 🛡️ Sentry — Error Tracking

Sentry is integrated into **both the frontend and backend** for real-time error monitoring in production:

| Component | Integration | What It Tracks |
|-----------|------------|----------------|
| **Frontend** (`main.jsx`) | `@sentry/react` + `VITE_SENTRY_DSN` | Uncaught React errors, promise rejections, runtime exceptions |
| **Backend** (`app/main.py`) | `sentry-sdk[fastapi]` + `FastApiIntegration` | API crashes, unhandled exceptions in endpoints |
| **Celery Workers** (`celery_app.py`) | `sentry-sdk` + `CeleryIntegration` | Background task failures during pipeline execution |

**Smart Filtering** — The `before_send` hook silently drops expected errors to keep the dashboard clean:
- ✅ `HTTPException` 4xx (normal client errors)
- ✅ `PermissionDeniedError`, `AuthenticationError`, `RateLimitError` (retried API key failures)
- ✅ `ReadOnlyError` (transient Redis blips)
- ✅ `ValueError` from guardrails (blocked keywords, rate limits)
- ✅ Expected pipeline outcomes ("no features extracted", "no report")

> Only **real, unexpected bugs** reach the Sentry dashboard.

### 📊 Microsoft Clarity — Session Analytics

Integrated via `@microsoft/clarity` in `main.jsx`. Tracks:
- 📹 Session recordings and replays
- 🖱️ Click heatmaps, scroll depth, rage clicks
- 📊 User engagement metrics

Configured via `VITE_CLARITY_PROJECT_ID` in the frontend `.env`.

### 💬 Formspree — User Feedback Widget

A floating feedback widget (`FeedbackWidget.jsx`) lets users submit feedback directly from the UI. Submissions are sent to **Formspree** (no backend needed) via `VITE_FORMSPREE_ENDPOINT`.

---

## 📂 Project Structure

```
Market_Scout_New-main/
│
├── 📁 app/                          # FastAPI Application Core
│   ├── main.py                      #   App, middleware, all endpoints
│   ├── config.py                    #   Pydantic BaseSettings (all env vars)
│   ├── api_models.py                #   Request/response Pydantic models
│   ├── celery_app.py                #   Celery broker config + Sentry
│   ├── services/
│   │   └── pipeline_enqueue.py      #   Cache-or-enqueue logic
│   └── rag/
│       ├── routes.py                #   /rag/upload and /rag/ask endpoints
│       ├── service.py               #   PDF + report indexing, Q&A via LLM
│       ├── embedding.py             #   SBERT embeddings
│       ├── vector_store.py          #   FAISS-backed store (Redis-persisted)
│       └── pdf_loader.py            #   PDF parsing
│
├── 📁 agents/                       # Autonomous AI Agents
│   ├── search_agent/                #   agent.py, planner.py, executor.py,
│   │                                #   critic.py, memory.py
│   └── scraper_agent/               #   agent.py, planner.py, critic.py, memory.py
│       └── tools/                   #   bs4.py, newspaper.py, playwright.py,
│                                    #   cleaners.py, dates.py
│
├── 📁 nodes/                        # LangGraph Pipeline Nodes
│   ├── guardrails.py                #   Input validation & security
│   ├── date_validation.py           #   7-day recency enforcement
│   ├── content_filter.py            #   Technical content filtering
│   ├── authority_check.py           #   Domain reputation scoring
│   ├── feature_extraction.py        #   LLM feature extraction
│   ├── verification.py              #   SBERT cross-source verification
│   ├── scoring.py                   #   Confidence score calculation
│   └── synthesis.py                 #   Executive report generation
│
├── 📁 graph/                        # LangGraph Orchestration
│   ├── builder.py                   #   StateGraph wiring
│   └── state.py                     #   GraphState TypedDict
│
├── 📁 llm/
│   └── nvidia_client.py             #   NVIDIA NIM gateway (multi-key, retry, metrics)
│
├── 📁 tasks/                        # Celery Background Tasks
│   ├── pipeline_tasks.py            #   run_market_pipeline task
│   ├── serve_cached.py              #   Serve cached results
│   └── scheduled_tasks.py           #   Scheduled report tasks
│
├── 📁 scheduler/                    # APScheduler
│   ├── scheduler.py                 #   Scheduler setup
│   ├── job_runner.py                #   Job execution logic
│   └── email_service.py             #   Email report delivery
│
├── 📁 services/
│   └── gmail_api_service.py         #   Gmail API OAuth + send
│
├── 📁 database/                     # PostgreSQL Layer
│   ├── models.py                    #   SQLAlchemy ORM models
│   ├── schemas.py                   #   Pydantic CRUD schemas
│   ├── crud.py                      #   Create/read/delete operations
│   └── session.py                   #   Engine + session factory
│
├── 📁 cache/                        # Redis Layer
│   ├── redis_client.py              #   Cache, rate limiting, audit log
│   └── report_cache.py              #   Report-specific caching
│
├── 📁 observability/                # Monitoring
│   ├── metrics.py                   #   14 Prometheus metric definitions
│   └── tracing.py                   #   OpenTelemetry setup
│
├── 📁 monitoring/                   # Infrastructure Config
│   ├── prometheus.yml               #   Prometheus scrape config
│   └── grafana/                     #   Auto-provisioned dashboard + datasource
│
├── 📁 mcp_server/                   # MCP Server
│   ├── server.py                    #   FastMCP server
│   └── tools/gmail_tool.py          #   send_email_report tool
│
├── 📁 frontend/                     # React 19 + Vite SPA
│   └── src/
│       ├── pages/                   #   Dashboard, RunPipeline, Reports,
│       │                            #   Competitors, Schedule, Analysis, About
│       └── components/              #   Sidebar, Header, FeedbackWidget,
│                                    #   ReportAssistant, GuidedTour, etc.
│
├── 📁 .github/workflows/
│   └── deploy.yml                   #   GitHub Actions CI/CD
│
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

---

## ⚙️ Configuration Reference

All settings in `app/config.py`, overridable via `.env`:

| Key | Default | Description |
|-----|---------|-------------|
| `NVIDIA_API_KEYS` | — | 🔑 NVIDIA NIM API key(s), comma-separated |
| `TAVILY_API_KEY` | — | 🔑 Web search API key |
| `HF_API_TOKEN` | — | 🔑 HuggingFace token (optional) |
| `LLM_MODEL` | `meta/llama-3.1-8b-instruct` | Active LLM model |
| `LLM_MAX_TOKENS` | `4096` | Max generation tokens |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_TOP_P` | `0.7` | Nucleus sampling |
| `SEARCH_DEPTH` | `advanced` | Tavily search depth |
| `SEARCH_MAX_RESULTS` | `15` | Results per query |
| `DATABASE_URL` | `postgresql://admin:admin@...` | PostgreSQL connection |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `CACHE_EXPIRY` | `21600` | Redis TTL in seconds (6 hours) |
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

## 🔒 Security (OWASP)

| Control | Implementation |
|---------|---------------|
| 🛡️ **A03 — Injection** | HTML stripping, regex format validation, blocklist keywords, Pydantic schema validation |
| 🔐 **A05 — Misconfiguration** | All secrets via environment variables, never hardcoded |
| 🧹 **A07 — XSS** | HTML sanitisation + structured JSON responses (no raw HTML output) |
| 🌐 **A10 — SSRF** | Domain allowlist in `config.py`; every scraped URL validated against `ALLOWED_DOMAINS` and `ALLOWED_DOMAIN_PREFIXES` |
| ⏱️ **Rate Limiting** | Redis-backed counter: 10 requests / 60 seconds, enforced before any LLM call |
| 🧠 **Semantic Guard** | LLM checks company name intent at temperature=0 to catch prompt injection |

---

## ☁️ Deployment

```
┌─────────────────────────────────────────────────────┐
│                   GitHub Repository                  │
│                        │                             │
│                   push to main                       │
│                        ▼                             │
│              GitHub Actions CI/CD                    │
│              ┌────────┴────────┐                     │
│              ▼                 ▼                     │
│     Azure VM (Backend)    Vercel (Frontend)           │
│     ┌─────────────────┐   ┌──────────────┐           │
│     │ Docker Compose  │   │ React Build  │           │
│     │ • FastAPI       │   │ • Vite SSG   │           │
│     │ • Celery Worker │   └──────┬───────┘           │
│     │ • PostgreSQL    │          │                    │
│     │ • Redis         │          │                    │
│     │ • Prometheus    │          │                    │
│     │ • Grafana       │          │                    │
│     └────────┬────────┘          │                    │
│              │                   │                    │
│    api.market-scout.me    market-scout.me             │
│         (Certbot SSL)       (Azure/Vercel SSL)        │
└─────────────────────────────────────────────────────┘
```

| Component | Platform | Domain |
|-----------|----------|--------|
| 🖥️ Backend | Azure VM (Ubuntu LTS) | `api.market-scout.me` |
| 🌐 Frontend | Vercel / Azure Static Web Apps | `market-scout.me` |
| 🔄 CI/CD | GitHub Actions | Auto-deploy on push to `main` |
| 🌍 DNS | Namecheap | HTTPS via Certbot (backend) + Azure/Vercel (frontend) |

---

## 🛠️ Useful Commands

```bash
# ── Docker Management ──────────────────────────────
docker compose up -d                    # Start all services
docker compose down                     # Stop all services
docker compose ps                       # Check status
docker compose logs -f celery_worker    # Stream Celery logs
docker compose restart grafana          # Restart one service
docker compose up -d --build app        # Rebuild and restart app

# ── Database Access ────────────────────────────────
docker exec -it market_postgres psql -U admin -d market_db

# ── Redis Access ───────────────────────────────────
docker exec -it market_redis redis-cli

# ── Celery Monitoring ──────────────────────────────
celery -A app.celery_app inspect active
```

---

<p align="center">
  <sub>Built with ❤️ using LangGraph, FastAPI, React, and NVIDIA NIM</sub>
</p>
