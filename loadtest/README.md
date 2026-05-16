# Load Testing

Tool: [Locust](https://locust.io/)

## Install
```powershell
pip install -r loadtest/requirements-loadtest.txt
```

## Tier 1 — cheap endpoints (safe to hammer)

```powershell
# Headless ramp: 0 -> 200 users at 10/s, run 2 min
locust -f loadtest/locustfile_cheap.py `
       --host http://localhost:8000 `
       --headless -u 200 -r 10 -t 2m `
       --csv reports/tier1
```

Outputs `reports/tier1_*.csv` with RPS, p50/p95/p99, failures.

Or open the web UI:
```powershell
locust -f loadtest/locustfile_cheap.py --host http://localhost:8000
# browse http://localhost:8089
```

### Ramp plan (find break point)

| Stage | Users | Spawn rate | Duration |
|-------|-------|------------|----------|
| Warmup | 10 | 5/s | 30s |
| Light | 50 | 10/s | 1m |
| Medium | 200 | 20/s | 2m |
| Heavy | 500 | 50/s | 2m |
| Stress | 1000 | 100/s | 1m |

Watch for: rising p95, error rate > 1%, DB connection-pool errors in app logs.

## Tier 2 — /run-agent (EXPENSIVE)

Each request: minutes long, hits paid APIs.

```powershell
# 5 concurrent pipelines, ramp 1/s, 15 min wall time
locust -f loadtest/locustfile_pipeline.py `
       --host http://localhost:8000 `
       --headless -u 5 -r 1 -t 15m `
       --csv reports/tier2
```

Start with `-u 1`, then `-u 2`, then `-u 5`. Stop when:
- p95 latency doubles vs `u=1` baseline → saturation point reached.
- Errors appear → resource limit hit.

## Metrics to watch (Grafana, port 3000)

Existing Prometheus metrics already cover this:
- `request_latency_seconds` (per endpoint)
- `active_pipelines`
- `pipeline_runs_total{status=...}`
- `llm_call_latency_seconds`
- `cache_operations_total{status=hit|miss}`

Pair Locust output with these to find the real bottleneck.
