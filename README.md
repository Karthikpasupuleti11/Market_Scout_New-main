# Market Intelligence Scout

> AI-powered competitive intelligence platform that discovers, verifies, and scores technical signals from public sources in real time.

Enter a company name → the system runs an agentic LangGraph pipeline (async via Celery) → delivers a structured intelligence report with verified features, confidence scores, source citations, and an executive summary.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Service Endpoints](#service-endpoints)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Useful Commands](#useful-commands)

---

## Prerequisites

| Tool              | Version | Download                                                 |
|-------------------|---------|----------------------------------------------------------|
| Python            | 3.10+   | [python.org](https://www.python.org/downloads/)          |
| Node.js           | 18+     | [nodejs.org](https://nodejs.org/)                        |
| Docker Desktop    | Latest  | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git               | Latest  | [git-scm.com](https://git-scm.com/)                     |

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Market_Scout
```

### 2. Create the `.env` File

Copy the template and add your API keys:

```bash
cp .env.example .env
```

Minimum required in `.env`:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

> **API Key Sources:**
> - **NVIDIA NIM** → [build.nvidia.com](https://build.nvidia.com/) (Free credits available)
> - **Tavily** → [tavily.com](https://tavily.com/) (Free tier available)

### 3. Start Docker Services

```bash
docker compose up -d
```

This launches **7 services**:

| Service        | Container                | Port  | Purpose                         |
|----------------|--------------------------|-------|---------------------------------|
| PostgreSQL 15  | `market_postgres`        | 5433  | Relational database             |
| Redis 7        | `market_redis`           | 6379  | Cache, rate limiting, broker    |
| FastAPI App    | `market_scout_app`       | 8000  | Backend API server              |
| Celery Worker  | `market_celery_worker`   | —     | Async pipeline task execution   |
| Flower         | `market_flower`          | 5555  | Celery task monitoring UI       |
| Prometheus     | `market_prometheus`      | 9090  | Metrics collection              |
| Grafana        | `market_grafana`         | 3000  | Monitoring dashboards           |

Verify all services are running:

```bash
docker compose ps
```

### 4. Set Up Python Backend (Local Development)

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

> Verify: Open [http://localhost:8000/docs](http://localhost:8000/docs) — you should see the Swagger API documentation.

### 5. Set Up & Start the Frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

### 6. Open the App

Navigate to **[http://localhost:5173](http://localhost:5173)** — you're ready to go!

---

## Service Endpoints

| Service            | URL                             | Credentials    |
|--------------------|---------------------------------|----------------|
| **Frontend**       | http://localhost:5173            | —              |
| **Backend API**    | http://localhost:8000            | —              |
| **Swagger Docs**   | http://localhost:8000/docs       | —              |
| **Flower**         | http://localhost:5555            | —              |
| **Prometheus**     | http://localhost:9090            | —              |
| **Grafana**        | http://localhost:3000            | admin / admin  |

---

## Project Structure

```
Market_Scout/
│
├── app/                    # FastAPI application (main.py, config.py)
├── agents/                 # Autonomous AI agents
│   ├── scraper_agent/      #   Multi-tool web scraper (BS4, Newspaper3k, Playwright)
│   └── search_agent/       #   LLM-driven query planner + Tavily search executor
│
├── nodes/                  # Deterministic pipeline nodes
│   ├── guardrails.py       #   Input validation + rate limiting (OWASP)
│   ├── date_validation.py  #   Recency filter (≤7 days)
│   ├── content_filter.py   #   Technical relevance filter
│   ├── authority_check.py  #   Source credibility scoring
│   ├── feature_extraction.py # LLM-powered structured feature extraction
│   ├── verification.py     #   SBERT cross-source verification
│   ├── scoring.py          #   Confidence score calculation
│   └── synthesis.py        #   Executive report generation
│
├── graph/                  # LangGraph pipeline (builder.py, state.py)
├── llm/                    # NVIDIA NIM client (Llama 3.1 8B Instruct)
├── celery_app/             # Celery async task worker configuration
├── scheduler/              # Automated scheduled analysis jobs
├── services/               # Business logic services
├── database/               # PostgreSQL models, CRUD, schemas (SQLAlchemy)
├── cache/                  # Redis client (caching, rate limiting, audit logs)
├── observability/          # Prometheus metrics + OpenTelemetry tracing
├── monitoring/             # Prometheus & Grafana configuration files
│
├── frontend/               # React 19 SPA (Vite)
│   └── src/
│       ├── components/     #   Sidebar, TopBar, Settings, Notifications, GuidedTour
│       └── pages/          #   Dashboard, RunPipeline, Reports, Analysis,
│                           #   Competitors, Schedule, About (+ Report Assistant on Intelligence)
│
├── docker-compose.yaml     # 7-service container orchestration
├── Dockerfile              # Multi-stage Python container
├── requirements.txt        # Python dependencies
└── .env                    # API keys (create manually)
```

---

## Architecture Overview

```
┌─────────────┐     POST /run-agent      ┌──────────────┐
│   React UI  │ ──────────────────────── │   FastAPI     │
│  (Vite SPA) │ ◄── Poll /task/{id} ──── │   Backend     │
└─────────────┘                          └──────┬───────┘
                                                │ Celery Task
                                         ┌──────▼───────┐
                                         │ Celery Worker │
                                         └──────┬───────┘
                                                │
                    ┌───────────────────────────────────────────────┐
                    │          LangGraph Pipeline (11 Nodes)        │
                    │                                               │
                    │  Guardrails → Search Agent → Scraper Agent    │
                    │  → Date Filter → Content Filter → Authority  │
                    │  → Feature Extraction → Verification (SBERT) │
                    │  → Confidence Scoring → Synthesis (LLM)      │
                    └───────────────────────────────────────────────┘
                           │           │            │
                    ┌──────┘     ┌─────┘      ┌─────┘
                    ▼            ▼             ▼
               PostgreSQL     Redis       NVIDIA NIM
               (Storage)     (Cache)    (NVIDIA NIM LLM)
```

---

## Tech Stack

| Layer             | Technologies                                                              |
|-------------------|---------------------------------------------------------------------------|
| **Backend**       | Python, FastAPI, LangGraph, Celery, NVIDIA NIM (Llama 3.1 8B), Tavily |
| **AI / ML**       | NVIDIA NIM (Llama 3.1 8B Instruct), Sentence-BERT, LLM extraction & synthesis |
| **Frontend**      | React 19, Vite, React Router, React Icons                                |
| **Database**      | PostgreSQL 15, SQLAlchemy ORM, Redis 7                                   |
| **Monitoring**    | Prometheus (14 custom metrics), Grafana (16-panel dashboard), Flower      |
| **Infrastructure**| Docker, Docker Compose, GitHub Actions CI/CD                             |
| **Deployment**    | Azure VM (Backend), Azure Static Web Apps (Frontend)                     |

---

## 3-minute demo script (presentations)

1. `docker compose up -d` — show `docker compose ps` (all services healthy).
2. Open **http://localhost:5173** → **Intelligence** → run **OpenAI** (first run ~1–3 min; watch pipeline stages).
3. Run **OpenAI** again — cached result returns in seconds (mention Redis + PostgreSQL cache).
4. **Settings** → enable **Force fresh analysis** → re-run to show full pipeline reset.
5. **Reports** / **Watchlist** — historical data and competitors.
6. **http://localhost:3000** (Grafana) + **http://localhost:9090** (Prometheus) — observability story.
7. Optional: **Report Assistant** on the intelligence results page (index report → ask a question).

Backend pipeline path: `POST /run-agent` → Celery worker → poll `GET /task/{id}`.

## Useful Commands

```bash
# Run API smoke tests (from repo root, venv active)
pip install -r requirements-dev.txt
pytest tests/ -q

# ── Docker ─────────────────────────────────────────
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose ps                 # Check service status
docker compose logs -f app        # Stream backend logs
docker compose restart grafana    # Restart a single service
docker compose up -d --build app  # Rebuild and restart app

# ── Database Access ────────────────────────────────
docker exec -it market_postgres psql -U admin -d market_db

# ── Redis Access ───────────────────────────────────
docker exec -it market_redis redis-cli

# ── Celery ─────────────────────────────────────────
docker logs -f market_celery_worker   # Monitor worker logs
docker logs -f market_flower          # Monitor Flower logs
```

---

## License

This project is for educational and research purposes.
