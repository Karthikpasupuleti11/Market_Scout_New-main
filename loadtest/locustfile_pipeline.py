"""
Tier 2 — /run-agent. EXPENSIVE — hits Tavily + NVIDIA + HF on every call.
Keep concurrency LOW (1-10 users). Each request runs minutes.
"""
import random
from locust import HttpUser, task, constant, events

# Cache-friendly: reuse same companies so Redis hits accumulate.
COMPANIES = ["OpenAI", "Anthropic", "Mistral"]


class PipelineUser(HttpUser):
    # No wait — fire next request immediately after previous returns.
    wait_time = constant(0)

    @task
    def run_agent(self):
        company = random.choice(COMPANIES)
        with self.client.post(
            "/run-agent",
            json={"company_name": company, "date_window_days": 7},
            name="/run-agent",
            timeout=600,        # 10 min ceiling per request
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"status={resp.status_code} body={resp.text[:200]}")
                return
            data = resp.json()
            if not data.get("features") and not data.get("executive_summary"):
                resp.failure("empty report")


@events.test_start.add_listener
def on_start(environment, **kw):
    print("\n=== Tier 2: /run-agent load test ===")
    print("WARNING: each request hits paid APIs. Watch your quotas.")
    print(f"Target: {environment.host}")
