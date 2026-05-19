# Market Intelligence Scout — System Architecture

## 1. Executive Summary

Market Intelligence Scout is an **agentic, multi-node enterprise intelligence pipeline** that automates the discovery, extraction, verification, and synthesis of technical product signals from public internet sources.

**Input:** A company name (e.g. "OpenAI")
**Output:** A structured, high-confidence executive report with verified technical features, confidence scores, source citations, and strategic insights — all from the past 7 days.

The system uses an **asynchronous architecture** where FastAPI enqueues analysis tasks to Celery workers, allowing non-blocking execution and real-time progress tracking via frontend polling.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  React 19 SPA (Vite) — 8 pages, responsive, guided tour             │
│  Polls GET /task/{id} every 2s for real-time status                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ HTTP (REST)
┌──────────────────────▼───────────────────────────────────────────────┐
│                       API LAYER (FastAPI)                             │
│  POST /run-agent → enqueue Celery task → return task_id              │
│  GET /task/{id} → poll status/result                                 │
│  GET /reports, /features, /competitors, /scheduled-jobs              │
│  GET /metrics → Prometheus exposition format                         │
└──────────┬─────────────────┬─────────────────┬───────────────────────┘
           │                 │                 │
     ┌─────▼─────┐   ┌──────▼──────┐   ┌──────▼──────┐
     │  Celery    │   │ PostgreSQL  │   │    Redis    │
     │  Worker    │   │   (Data)    │   │  (3 DBs)    │
     │            │   │             │   │  db0: Cache  │
     │ Runs the   │   │ competitors │   │  db1: Broker │
     │ LangGraph  │   │ reports     │   │  db2: Results│
     │ pipeline   │   │ features    │   │             │
     │            │   │ sched_jobs  │   │             │
     └─────┬──────┘   └─────────────┘   └─────────────┘
           │
     ┌─────▼──────────────────────────────────────────────────────────┐
     │              LANGGRAPH PIPELINE (11 Nodes)                     │
     │                                                                │
     │  ┌───────────┐   ┌──────────────┐   ┌──────────────┐          │
     │  │ Guardrails│──▶│ Search Agent │──▶│Scraper Agent │          │
     │  └───────────┘   └──────────────┘   └──────┬───────┘          │
     │                                            │                   │
     │  ┌───────────┐   ┌──────────────┐   ┌──────▼───────┐          │
     │  │ Authority │◀──│Content Filter│◀──│Date Validate │          │
     │  └─────┬─────┘   └──────────────┘   └──────────────┘          │
     │        │                                                       │
     │  ┌─────▼─────┐   ┌──────────────┐   ┌──────────────┐          │
     │  │ Feature   │──▶│ Verification │──▶│   Scoring    │          │
     │  │ Extraction│   │   (SBERT)    │   │              │          │
     │  └───────────┘   └──────────────┘   └──────┬───────┘          │
     │                                            │                   │
     │                                     ┌──────▼───────┐          │
     │                                     │  Synthesis   │          │
     │                                     │   (LLM)      │          │
     │                                     └──────────────┘          │
     └────────────────────────────────────────────────────────────────┘
           │                    │
     ┌─────▼──────┐     ┌──────▼──────┐
     │ NVIDIA NIM │     │  Tavily API │
     │ LLaMA 3.3  │     │ Web Search  │
     │   70B      │     │             │
     └────────────┘     └─────────────┘
```

**Monitoring Layer:**
```
  App (/metrics) ──▶ Prometheus (scrape 15s) ──▶ Grafana (16 panels)
  Celery Worker  ──▶ Flower (real-time task UI on :5555)
```

---

## 3. Infrastructure & Deployment

### 3.1 Docker Services (7 Containers)

| Service         | Container               | Port | Role                           |
|-----------------|-------------------------|------|--------------------------------|
| FastAPI App     | `market_scout_app`      | 8000 | REST API, task dispatch        |
| Celery Worker   | `market_celery_worker`  | —    | Async pipeline execution       |
| Flower          | `market_flower`         | 5555 | Celery monitoring dashboard    |
| PostgreSQL 15   | `market_postgres`       | 5433 | Relational data persistence    |
| Redis 7         | `market_redis`          | 6379 | Cache, broker, result backend  |
| Prometheus      | `market_prometheus`     | 9090 | Metrics time-series database   |
| Grafana         | `market_grafana`        | 3000 | Monitoring visualization       |

### 3.2 Redis Multi-Database Layout

| Database | Purpose                        | Key Examples                          |
|----------|--------------------------------|---------------------------------------|
| `db=0`   | Application cache (TTL: 6hrs) | `mscout:report:{sha256}`, rate limits |
| `db=1`   | Celery message broker          | Task queue messages                   |
| `db=2`   | Celery result backend          | Task results for polling              |

### 3.3 Cloud Deployment (Azure)

| Component | Platform                  | Domain                     |
|-----------|---------------------------|----------------------------|
| Frontend  | Azure Static Web Apps     | `https://market-scout.me`  |
| Backend   | Azure VM (Docker)         | `https://api.market-scout.me` |
| CI/CD     | GitHub Actions            | Auto-deploy on push        |

---

## 4. The LangGraph Pipeline (11 Nodes)

The intelligence pipeline is a **LangGraph StateGraph** with 10 functional nodes and 5 error-exit nodes. Each node reads from and writes to a shared `GraphState` dictionary. The pipeline executes inside a **Celery worker** for non-blocking operation.

### Stage 1 — Guardrails `[Deterministic + Agentic]`

Security firewall enforcing OWASP compliance before any external API is called.

| Check                  | Implementation                                     |
|------------------------|-----------------------------------------------------|
| HTML Sanitization      | Strip tags, unescape entities, collapse whitespace  |
| Length Validation      | 2–200 characters                                    |
| Format Validation      | Regex: letters, numbers, spaces, dots, hyphens      |
| Keyword Blocking       | Rejects "jailbreak", "ignore previous", "exploit"   |
| Rate Limiting          | Redis-backed: 10 requests / 60 seconds              |
| LLM Semantic Check     | Temperature=0 intent validation                     |

**Routes:** → Search Agent **or** → Error Exit

### Stage 2 — Search Agent `[Agentic]`

Autonomous agent with iterative refinement (max 2 loops).

- **Planner:** LLM generates 4+ diverse search queries
- **Executor:** Tavily API (`depth=advanced`, max 15 results per query)
- **Critic:** Evaluates if enough technical content was found
- **Memory:** Redis-cached query history to avoid repetition
- Domain scoring + deduplication across queries

### Stage 3 — Scraper Agent `[Agentic]`

Multi-tool parallel scraper with LLM-driven strategy selection.

| Strategy      | Use Case             | Fallback Order |
|---------------|----------------------|----------------|
| Newspaper3k   | News articles        | 1st            |
| BeautifulSoup | Static HTML pages    | 2nd            |
| Playwright    | Dynamic JS-rendered  | 3rd            |

- Processes URLs in parallel via `ThreadPoolExecutor`
- Concurrency limited by `threading.Semaphore(3)` for Playwright
- LLM critic validates technical relevance per article
- Results cached in Redis to avoid re-scraping
- Articles truncated to 8,000 characters for LLM context

### Stage 4 — Date Validation `[Deterministic]`

- Parses ISO-8601 dates, enforces 7-day recency window
- No date → conservatively discarded
- Audit trail stored in Redis

### Stage 5 — Content Filter `[Deterministic]`

- Keyword density analysis (API, SDK, model, benchmark, etc.)
- Rejects marketing, job postings, investor relations, earnings reports

### Stage 6 — Authority Check `[Deterministic]`

- Domain reputation tiers: official sites > tech publications > .edu/.gov > unknown
- Enriches each article with `authority_score` (0.0–1.0)
- Results sorted by authority (highest first)

### Stage 7 — Feature Extraction `[Agentic]`

LLM extracts structured JSON per article:

```json
{
  "feature_summary": "2-3 sentence description",
  "category": "model_release | api_update | performance | capability",
  "metrics": ["quantitative measurements"],
  "evidence": "direct quote from article"
}
```

Instructed to **never infer or invent** — only explicitly stated facts.

### Stage 8 — Verification `[Deterministic / ML]`

- **Model:** Sentence-BERT (`all-MiniLM-L6-v2`, 384-dim embeddings)
- Cosine similarity threshold: **0.85**
- Clusters semantically identical features from different sources
- Merges into single verified feature with `source_count`
- Falls back to local SentenceTransformer if HF API is unavailable

### Stage 9 — Confidence Scoring `[Deterministic]`

Three scoring signals (each 0.0 → 1.0):

| Signal         | Weight | Logic                                     |
|----------------|--------|-------------------------------------------|
| Recency        | 30%    | Today=1.0, 7d=0.5, >14d=0.3 (floor)     |
| Verification   | 40%    | Logarithmic: 0 sources=0.2, 5+=~1.0      |
| Authority      | 30%    | Direct pass-through of source score       |

**Formula:** `confidence = 0.3×recency + 0.4×verification + 0.3×authority`

### Stage 10 — Synthesis `[Agentic]`

LLM generates the final executive intelligence report:

- **Executive summary:** 3–5 paragraph strategic overview
- **Features:** Ranked list with titles, descriptions, confidence, citations
- **Sources:** Complete URL list
- Deterministic fallback report if LLM fails

### Error / Early-Exit Nodes

| Exit Node       | Trigger Condition                          |
|-----------------|---------------------------------------------|
| `no_results`    | No search results found                    |
| `no_articles`   | All URLs failed to scrape                  |
| `all_expired`   | All articles older than 7 days             |
| `no_technical`  | No technical content after filtering       |
| `no_features`   | No extractable features found              |

All exit nodes return a **consistent response shape** so the API and frontend always receive predictable output.

---

## 5. Data Model (PostgreSQL)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  competitors │──1:N──│   reports    │──1:N──│   features   │
│              │       │              │       │              │
│  id (PK)     │       │  id (PK)     │       │  id (PK)     │
│  name        │       │  competitor_id│       │  report_id   │
│  industry    │       │  exec_summary│       │  feature_title│
│  created_at  │       │  total_sources│      │  confidence   │
│              │       │  all_sources  │       │  category     │
│              │       │  metadata     │       │  evidence     │
│              │       │  created_at   │       │  source_count │
└──────────────┘       └──────┬───────┘       └──────────────┘
                              │
                        ┌─────▼──────┐
                        │ sched_jobs │
                        │            │
                        │ id (PK)    │
                        │ report_id  │
                        │ status     │
                        │ email      │
                        │ scheduled_at│
                        └────────────┘
```

**Deletion order (FK-safe):** ScheduledJob → Feature → Report → Competitor

---

## 6. Observability & Monitoring

### 6.1 Prometheus Metrics (14 Custom)

| Category      | Metrics                                                    |
|---------------|-------------------------------------------------------------|
| API           | `api_requests_total`, `api_request_duration_secs`          |
| Pipeline      | `node_latency_seconds`, `node_executions_total`, `pipeline_runs_total`, `active_pipelines` |
| LLM           | `llm_tokens_total`, `llm_calls_total`, `llm_call_duration_seconds` |
| Intelligence  | `features_extracted_total`, `features_verified_total`, `feature_confidence_score`, `sources_analysed_per_run` |
| Infrastructure| `cache_operations_total`, `scraper_attempts_total`, `urls_discarded_total` |

### 6.2 Grafana Dashboard (16 Panels)

| Row                    | Panels                                              |
|------------------------|------------------------------------------------------|
| Pipeline Overview      | Total runs, success rate, active, avg time, verified |
| Pipeline Performance   | Runs over time (stacked), node latency (lines)      |
| LLM & Intelligence     | Calls by agent, tokens, LLM latency, confidence     |
| Scraping & Cache       | Strategy performance, cache hit/miss, features       |

### 6.3 Flower (Celery Monitoring)

Real-time dashboard at `:5555` showing active/completed/failed tasks, worker status, and task execution history.

---

## 7. Security (OWASP Compliance)

| OWASP        | Threat                    | Mitigation                                  |
|--------------|---------------------------|----------------------------------------------|
| **A03**      | Injection                 | HTML stripping, regex validation, keyword blocking, Pydantic schemas |
| **A05**      | Security Misconfiguration | All secrets in `.env`, never hardcoded       |
| **A07**      | XSS                       | Input sanitisation, structured JSON responses |
| **A10**      | SSRF                      | Domain allowlist, prefix-based URL validation |
| —            | Rate Limiting             | Redis-backed: 10 req / 60s per client        |

---

## 8. Key Architecture Decisions

| Decision                     | Rationale                                                    |
|------------------------------|---------------------------------------------------------------|
| **Celery over sync**         | Pipeline takes 1–3 min; async prevents HTTP timeouts and enables multi-user support |
| **Redis 3-database split**   | Isolates cache, broker, and results to prevent key collision  |
| **Semaphore(3) for Playwright** | Limits concurrent browser instances to prevent memory exhaustion |
| **Polling over SSE/WebSocket** | More reliable behind reverse proxies and load balancers      |
| **NVIDIA NIM (LLaMA 3.3 70B)** | Best cost/performance ratio for structured extraction       |
| **SBERT local fallback**     | Ensures verification works even if HF Inference API is down  |
| **Redis fail-open**          | If Redis is down, rate-limiting fails open but pipeline continues |
| **DB fail-safe**             | If PostgreSQL write fails, report still returns to user       |
| **6-hour cache TTL**         | Balances data freshness with API cost savings                 |
| **8,000 char article cap**   | Manages LLM context window without losing critical content    |
| **FK-ordered deletion**      | ScheduledJob → Feature → Report → Competitor prevents constraint violations |
