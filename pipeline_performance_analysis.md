# 🔍 Pipeline Performance Root Cause Analysis

## TL;DR — Sentry Is NOT the Problem

Your `.env` has all Sentry sample rates at `0`:
```
SENTRY_TRACES_SAMPLE_RATE=0
SENTRY_PIPELINE_TRACES_SAMPLE_RATE=0
SENTRY_PROFILES_SAMPLE_RATE=0
```
With these values, Sentry only captures **crash reports** — zero tracing, zero profiling. It adds essentially **zero overhead** to the pipeline. The `sentry_init.py` even explicitly logs `"errors only=True"` when these are 0.

OpenTelemetry is also disabled (`OTEL_ENABLED=false`).

---

## The Real Root Cause: Sequential LLM Calls

Your pipeline makes a **huge number of sequential (one-at-a-time) LLM calls** that stack up. Here's the full breakdown:

### LLM Call Count Per Run (for a query like "openclaw" returning ~15 URLs → ~10 articles passing filters)

| Stage | LLM Calls | Concurrency | Estimated Time |
|---|---|---|---|
| **Guardrails** — semantic intent check | 1 | — | ~2s |
| **Search Planner** — generate 4 queries | 1 (per iteration, max 2) | — | ~2-3s |
| **Scraper Critic** — `batch_is_technical()` | 1 (batched) | — | ~2-3s |
| **Content Filter** — per-article ACCEPT/REJECT | **N** (one per article) | **Sequential** ⚠️ | ~2-3s × N |
| **Authority Check** — per-article PRIMARY/SECONDARY | **N** (one per article) | **Sequential** ⚠️ | ~2-3s × N |
| **Feature Extraction** — per-article extraction | **N** (one per article) | **Sequential** ⚠️ | ~3-5s × N |
| **Synthesis** — generate final report | 1 | — | ~3-5s |

### The Math

If you have **10 articles** passing the scraper stage:

```
Fixed calls:    1 + 1 + 1 + 1 = 4 calls  ≈  10-13s
Content Filter: 10 × ~2s      = 10 calls ≈  20s
Authority Check: 10 × ~2s     = 10 calls ≈  20s
Feature Extract: 10 × ~4s     = 10 calls ≈  40s
─────────────────────────────────────────────────
Total: ~34 LLM calls           ≈  ~90-120s (best case)
```

But factor in:
- **Semaphore of 3** (only 3 concurrent LLM calls allowed) — but Content Filter, Authority Check, and Feature Extraction all run *inside a `for` loop with `await`*, so they're **actually sequential**, not even using the semaphore concurrency
- **API latency variance** — each NVIDIA LLM call can take 1-5s depending on load
- **429 rate limits** — with 5 keys at 40 RPM each, you have ~200 RPM budget, but bursts can trigger cooldowns (60s penalty!)
- **HuggingFace embedding API** in Verification — can add 2-5s if cache is cold

### Why It Was 1-3 Minutes Before

If you had fewer articles passing through (e.g., 3-5 articles), the math works out:
```
4 fixed + 3×3 per-article = ~13 calls ≈ 40-90s → 1-1.5 minutes
```

The pipeline time scales **linearly with the number of articles that pass scraping/date filters**.

---

## The 3 Biggest Bottlenecks

### 1. 🐢 Content Filter — Sequential per-article LLM calls
**File**: [content_filter.py](file:///c:/Users/Sindhu/Desktop/Market_Scout_New-main/nodes/content_filter.py#L37-L91)

```python
for article in articles:           # ← sequential loop
    response = await invoke_llm(...)  # ← waits for each one
```

Each article gets its own LLM call asking "ACCEPT or REJECT". With 10 articles, that's 10 sequential API round-trips.

### 2. 🐢 Authority Check — Sequential per-article LLM calls  
**File**: [authority_check.py](file:///c:/Users/Sindhu/Desktop/Market_Scout_New-main/nodes/authority_check.py#L37-L82)

```python
for article in articles:           # ← sequential loop
    response = await invoke_llm(...)  # ← waits for each one
```

Same pattern — one LLM call per article, sequentially.

### 3. 🐢 Feature Extraction — Sequential per-article LLM calls  
**File**: [feature_extraction.py](file:///c:/Users/Sindhu/Desktop/Market_Scout_New-main/nodes/feature_extraction.py#L74-L170)

```python
for article in filtered:           # ← sequential loop
    response = await invoke_llm(...)  # ← waits for each one
```

This is the **heaviest** per-article call (longer prompts, more tokens).

---

## Why More Articles = Exponentially Slower

Looking at your screenshot, the "openclaw" query produced:
- Guardrails: 4685 items processed (likely the input token count display)
- Searching: 55 
- Scraping: 355
- Validating (date): passed
- Filtering (content): 23 articles
- Authority: 15 articles  
- Extracting: 125 features
- Verifying: 15
- Scoring: 18
- Synthesizing: 145

That filtering count of **23** means the content filter ran ~23 sequential LLM calls, authority check ran ~23 more, and feature extraction ran on whatever passed. That alone is **~46+ sequential LLM calls** just for those two stages.

---

## Secondary Contributors (Minor)

| Factor | Impact | Details |
|---|---|---|
| Prometheus metrics | Negligible | Counter/histogram `.inc()` and `.observe()` are in-memory operations |
| `_instrument_node` wrapper | Negligible | Just `time.time()` and Prometheus labels |
| Sentry `before_send` filter | Negligible | Only runs on actual exceptions, not on every call |
| Sentry `init()` at startup | One-time | ~50ms at module import, never again |
| HF Embedding API | 2-5s (cold cache) | Redis-cached, so only first run is slow |

---

## Proposed Fixes (Need Your Approval)

> [!IMPORTANT]
> The following are **potential optimizations**, ranked by impact. I will NOT implement any until you tell me which ones to proceed with.

### Fix 1: Batch Content Filter + Authority Check into single LLM calls (HIGH IMPACT)
The scraper critic already does this — `batch_is_technical()` sends ALL articles in one prompt. We can do the same for Content Filter and Authority Check, turning **20+ sequential calls into 2 calls**.

**Estimated savings: 40-60 seconds**

### Fix 2: Parallelize Feature Extraction with `asyncio.gather()` (HIGH IMPACT)
Feature extraction calls are independent per article. We can run them concurrently (respecting the semaphore limit of 3):

```python
tasks = [invoke_llm(...) for article in filtered]
results = await asyncio.gather(*tasks)
```

**Estimated savings: 60-70% of feature extraction time**

### Fix 3: Merge Content Filter + Authority Check into one node (MEDIUM IMPACT)
Both nodes iterate over the same articles and ask binary classification questions. Combine them into a single batched call:

```
"For each article, classify: TECHNICAL or REJECT? PRIMARY or SECONDARY?"
```

**Saves one full node + eliminates redundant iteration**

### Fix 4: Cache LLM responses for Content Filter / Authority Check (LOW-MEDIUM)
These classifications are deterministic (temperature=0.0). Cache by URL hash to avoid re-classifying previously seen articles.

---

## Questions for You

1. **Which fixes do you want me to implement?** I'd recommend Fix 1 + Fix 2 as the highest-impact, lowest-risk changes.
2. **Is there a specific time target you want?** (e.g., "always under 2 minutes")
3. **Are you running this locally or on the VM?** The `.env.vm` shows Docker Compose — network latency to NVIDIA API from a non-US VM could add per-call overhead.
