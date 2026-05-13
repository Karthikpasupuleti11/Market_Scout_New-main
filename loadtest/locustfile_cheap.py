"""
Tier 1 — cheap endpoints. Safe to hammer.
Targets: /health, /, /competitors, /reports/{name}
"""
import random
from locust import HttpUser, task, between, events

COMPANIES = ["OpenAI", "Anthropic", "Google", "Meta", "Microsoft", "NVIDIA"]


class CheapUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def health(self):
        self.client.get("/health", name="/health")

    @task(3)
    def root(self):
        self.client.get("/", name="/")

    @task(2)
    def list_competitors(self):
        self.client.get("/competitors", name="/competitors")

    @task(2)
    def get_reports(self):
        company = random.choice(COMPANIES)
        self.client.get(
            f"/reports/{company}?limit=10",
            name="/reports/{company}",
        )

    @task(1)
    def get_features(self):
        company = random.choice(COMPANIES)
        self.client.get(
            f"/features/{company}?limit=50",
            name="/features/{company}",
        )


@events.test_start.add_listener
def on_start(environment, **kw):
    print("\n=== Tier 1: cheap-endpoint load test ===")
    print(f"Target: {environment.host}")
