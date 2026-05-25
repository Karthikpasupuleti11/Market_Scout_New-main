# Market Intelligence Scout — System Architecture & Documentation

## 1. Executive Summary
The Market Intelligence Scout is an agentic, multi-node enterprise intelligence pipeline designed to automate the discovery, extraction, verification, and synthesis of technical product updates from internet sources. It takes a company name, searches the web for recent announcements (past 7 days), and produces a structured, high-confidence executive report detailing specific technical features.

## 2. Infrastructure & Deployment
The system is built for local development and enterprise deployment readiness using a hybrid architecture:
- **Application Core**: FastAPI (Python), running locally or in Docker.
- **Containerized Services** (via `docker-compose`):
  - **PostgreSQL**: Permanent persistence of historical intelligence.
  - **Redis**: Fast, transient caching layer (TTL: 6 hours) to minimize API calls and rate-limiting.
  - **Prometheus**: Time-series database for application metrics.
  - **Grafana**: Visualization dashboard for observability.

## 3. The LangGraph Pipeline (Agentic Workflow)
The intelligence pipeline is constructed using LangGraph, consisting of 17 distinct functional nodes separated into **Deterministic Nodes** (rule-based) and **Agentic Nodes** (LLM reasoning).

### 3.1. Pre-Flight Security (Guardrails Node)
*Type: Deterministic + Agentic (Safety Net)*
- Ensures OWASP compliance before any external API is hit.
- **Checks applied**:
  1. HTML Sanitization
  2. Length validation (max 200 chars)
  3. Format validation (alphanumeric, spaces, basic punctuation)
  4. Blocklisted keywords (prevents "jailbreak", "ignore previous", etc.)
  5. Redis-backed Rate Limiting (10 requests / 60 seconds)
  6. **LLM Semantic Check**: Evaluates intent to block prompt-injection attacks masking as company names.

### 3.2. Search Generation (Search Planner & Execution)
*Type: Agentic (Planner) + Deterministic (Execution)*
- **Planner Agent**: Generates 4 diverse search strategies (e.g., "Company press releases", "Company GitHub release notes").
- **Execution Node**: Executes queries via the **Tavily API** with a depth of "advanced" and max 15 results per query.
- **Scoring**: Domains are mapped to authority scores (e.g., `github.com` = 0.9, unknown = 0.5).
- **Consolidation**: URLs are deduplicated across queries.

### 3.3. Content Acquisition (Scraper Strategy)
*Type: Deterministic*
- Attempts to fetch content for up to 60 URLs.
- Built-in fallback strategies (Standard HTTP → Headless Browser simulation) to handle anti-bot measures.
- Truncates individual articles to 8000 characters to manage LLM context windows.

### 3.4. Relevancy & Quality Gates
*Type: Agentic*
- **Date Validation**: Explicitly searches the scraped text for date mentions, strictly enforcing a 7-day cutoff window. Prevents reporting on historical features.
- **Content Filter**: Discards articles that do not contain actual technical updates (e.g., rejecting hiring announcements, generic marketing, or earnings reports).

### 3.5. Feature Extraction
*Type: Agentic*
- Instructed to *never* infer or invent. Only extracts explicitly stated facts.
- **Output Schema**: Extracts a short `feature_title` (max 10 words), a detailed 2-3 sentence `description` (what, how, why), the category (API, SDK, Model, etc.), metrics, and a direct quote (`evidence`) for grounding.

### 3.6. Verification (Cross-Source Clustering)
*Type: Deterministic (ML-based)*
- Uses **Hugging Face InferenceClient** (`sentence-transformers/all-MiniLM-L6-v2`) to generate semantic embeddings for all extracted features.
- Clusters semantically similar features using Cosine Similarity (threshold: 0.85).
- Consolidates duplicate features across multiple sources into a single verified feature, incrementing the `source_count` for higher confidence.
- Gracefully falls back to a locally running SentenceTransformer if the HF API is unavailable.

### 3.7. Scoring Node
*Type: Deterministic*
- Calculates a final confidence score (0.0 - 1.0) based on:
  - Base semantic confidence
  - Source authority weight
  - Cross-source verification bonus (mentions across multiple independent domains).

### 3.8. Synthesis Agent
*Type: Agentic*
- Consumes the final, deduplicated, scored feature list.
- Generates a 2-3 sentence executive summary of the company's recent activity.
- Formats the final JSON schema required by downstream consumers or the REST API.

## 4. API & Interface Layer
FastAPI provides the standard REST interface:
- `POST /run-agent`: Primary entry point. Accepts `{"company_name": "..."}` and synchronously returns the synthesis report.
- `GET /reports/{company_name}`: Retrieves historical reports from PostgreSQL.
- `GET /features/{company_name}`: Retrieves individual historical features from PostgreSQL.
- `GET /competitors`: Lists all tracked companies.
- `GET /metrics`: Prometheus metric endpoint.

## 5. Persistence Storage (PostgreSQL)
A robust historical tracking layer using SQLAlchemy ORM.
- **`competitors` Table**: Tracks unique searched entities and their industry.
- **`reports` Table**: Logs every pipeline run, storing the executive summary, total source metrics, and pipeline metadata (model version, configuration).
- **`features` Table**: Deep storage of granular intelligence. Stores:
  - `feature_title` (Short name)
  - `description` (2-3 sentence technical impact)
  - `feature_text` (legacy fallback)
  - `category`, `confidence_score`, `source_count`, `source_url`, `evidence`, and `metrics`.

## 6. Observability & Monitoring
- **OpenTelemetry Tracker**: Injected into the FastAPI application, instrumenting requests and dependency calls.
- **Prometheus Metrics**: Custom metrics tracking:
  - Total pipeline runs (`pipeline_runs_total`)
  - Features extracted per run (`features_extracted_total`)
  - Guardrail blocks (`guardrail_blocks_total`)
  - Cache hit ratios (`redis_cache_hits_total`)
- **Grafana Dashboard**: Visual representation of the Prometheus metrics for live operational monitoring.

## 7. Error Tracking & Analytics

### Sentry — Real-Time Error Monitoring
Integrated into **both frontend and backend** for production error tracking:
- **Frontend** (`main.jsx`): Uses `@sentry/react` with `VITE_SENTRY_DSN` to capture uncaught React errors, promise rejections, and runtime exceptions.
- **Backend** (`app/main.py`): Uses `sentry-sdk[fastapi]` with `FastApiIntegration` to capture API-level crashes and unhandled exceptions.
- **Celery Workers** (`celery_app.py`): Uses `sentry-sdk` with `CeleryIntegration` to capture background task failures during pipeline execution.
- **Smart Filtering**: A custom `before_send` hook silently drops expected, non-critical errors:
  - HTTP 4xx client errors
  - `PermissionDeniedError`, `AuthenticationError`, `RateLimitError` (safely retried API key failures)
  - `ReadOnlyError` (transient Redis cache blips)
  - `ValueError` from guardrails (blocked keywords, rate limits)
  - Expected pipeline outcomes ("no features extracted", "no report")

### Microsoft Clarity — Session Analytics
Integrated via `@microsoft/clarity` in `main.jsx`:
- Session recordings and replays
- Click heatmaps, scroll depth, rage clicks
- User engagement metrics
- Configured via `VITE_CLARITY_PROJECT_ID` in the frontend `.env`.

### Formspree — User Feedback Collection
A floating feedback widget (`FeedbackWidget.jsx`) lets users submit feedback directly from the UI:
- Submissions are sent to Formspree (no backend processing needed).
- Configured via `VITE_FORMSPREE_ENDPOINT` in the frontend `.env`.

## 8. Asynchronous Task Execution (Celery)
The pipeline runs asynchronously via **Celery** with Redis as the broker:
- `POST /run-agent` enqueues a task and immediately returns a `task_id`.
- The frontend polls `GET /task-status/{task_id}` for real-time progress updates (`current_node`, `progress`).
- Task results (success/failure) are stored in Redis and served back to the client.
- Worker metrics are exported on port 9100 for Prometheus scraping.

## 9. Scheduled Reports (APScheduler)
Users can schedule future pipeline runs that automatically generate and email reports:
- **APScheduler** manages scheduled jobs within the FastAPI process.
- When a job fires, it enqueues a Celery task to run the full pipeline.
- After pipeline completion, the report is rendered as a PDF and sent via the **Gmail API** (OAuth2).
- Jobs are persisted in PostgreSQL (`scheduled_jobs` table) and survive server restarts.

## 10. RAG — Report Q&A
A retrieval-augmented generation (RAG) system allows users to ask questions about generated reports:
- **PDF Upload** (`/rag/upload`): Parses uploaded PDFs, chunks the text, generates SBERT embeddings, and indexes them into a FAISS vector store (persisted in Redis).
- **Question Answering** (`/rag/ask`): Retrieves the most relevant chunks via cosine similarity, then sends them as context to the LLM to generate an answer grounded in the report.

## 11. MCP Server
A **FastMCP** server (`mcp_server/server.py`) exposes the `send_email_report` tool, allowing external MCP-compatible clients to trigger email report delivery programmatically.

## 12. Minute Architecture Decisions
- **LLM Selection**: Configured to use NVIDIA NIM endpoints (`meta/llama-3.1-8b-instruct`). Prompts are highly constrained to prevent hallucinations. Max tokens set to 4096 to handle rich summaries.
- **Multi-Key Load Balancing**: Multiple NVIDIA API keys are rotated round-robin with automatic cooldown on 429 rate limit errors.
- **Cache Invalidation**: Redis keys are prefixed logically (`mscout:report:*`, `mscout:search_results:*`). TTL is universally set to 6 hours to balance data freshness with API cost savings.
- **Data Caps Lifted**: Previous limits (e.g., max 10 features in synthesis, max 15 search results) were removed to ensure 100% data capture within the 7-day semantic window.
- **Graceful Degradation**: 
  1. If HF Inference API goes down, it switches to a local model. 
  2. If Redis goes down, rate-limiting fails open but pipeline execution continues.
  3. If DB persistence fails, it logs a warning but still returns the report to the user.

