import time
import os
from collections import defaultdict
from typing import Dict, Any

class GrafanaTelemetry:
    """
    Grafana Labs AI Observability Adapter.
    Tracks LLM latency, token counts, tool invocations, and pipeline health.
    Emits standard Prometheus metrics and supports OpenTelemetry/OpenLIT OTLP export.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        self.projects_created = 0
        self.active_jobs = 0
        self.prompt_latencies = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.governance_checks = defaultdict(int) # decision -> count
        self.parallel_queries = 0
        self.parallel_cache_hits = 0
        self.clickhouse_events_logged = 0

        # Attempt to initialize OpenLIT if installed and credentials exist
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("GRAFANA_OTLP_TOKEN"):
            try:
                import openlit
                openlit.init(
                    environment=os.getenv("APP_ENV", "production"),
                    application_name="agentic-cinema-studio"
                )
                print("🔭 [Grafana] OpenLIT AI Observability initialized successfully.")
            except ImportError:
                print("🔭 [Grafana] OpenLIT SDK not installed. Using high-performance native metrics.")
            except Exception as e:
                print(f"⚠️ [Grafana] OpenLIT initialization skipped: {e}")

    def record_project_created(self, topic: str = ""):
        self.projects_created += 1

    def record_prompt_generation(self, duration_seconds: float, input_tokens: int = 0, output_tokens: int = 0):
        self.prompt_latencies.append(duration_seconds)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def record_production_job(self, delta: int = 1):
        self.active_jobs = max(0, self.active_jobs + delta)

    def record_governance_check(self, decision: str):
        self.governance_checks[decision.lower()] += 1

    def record_parallel_search(self, cache_hit: bool = False):
        self.parallel_queries += 1
        if cache_hit:
            self.parallel_cache_hits += 1

    def record_clickhouse_event(self):
        self.clickhouse_events_logged += 1

    def get_summary(self) -> Dict[str, Any]:
        avg_latency = (sum(self.prompt_latencies) / len(self.prompt_latencies)) if self.prompt_latencies else 0.0
        return {
            "partner": "Grafana Labs",
            "status": "connected",
            "projects_created": self.projects_created,
            "active_production_jobs": self.active_jobs,
            "avg_prompt_latency_seconds": round(avg_latency, 3),
            "total_tokens_consumed": self.input_tokens + self.output_tokens,
            "governance_checks": dict(self.governance_checks),
            "parallel_searches": self.parallel_queries,
            "clickhouse_events_logged": self.clickhouse_events_logged,
        }

    def generate_prometheus_metrics(self) -> str:
        lines = [
            "# HELP agent_projects_created_total Total video generation projects started.",
            "# TYPE agent_projects_created_total counter",
            f"agent_projects_created_total {self.projects_created}",
            "",
            "# HELP agent_active_production_jobs Number of active video rendering jobs in pipeline.",
            "# TYPE agent_active_production_jobs gauge",
            f"agent_active_production_jobs {self.active_jobs}",
            "",
            "# HELP agent_tokens_consumed_total Total tokens consumed by AI agents.",
            "# TYPE agent_tokens_consumed_total counter",
            f'agent_tokens_consumed_total{{type="input"}} {self.input_tokens}',
            f'agent_tokens_consumed_total{{type="output"}} {self.output_tokens}',
            "",
            "# HELP parallel_search_queries_total Total research queries sent to Parallel Search.",
            "# TYPE parallel_search_queries_total counter",
            f"parallel_search_queries_total {self.parallel_queries}",
            f"parallel_search_cache_hits_total {self.parallel_cache_hits}",
            "",
            "# HELP ibm_governance_verifications_total Total IBM script compliance checks by decision.",
            "# TYPE ibm_governance_verifications_total counter",
        ]
        for decision, count in self.governance_checks.items():
            lines.append(f'ibm_governance_verifications_total{{decision="{decision}"}} {count}')
        if not self.governance_checks:
            lines.append('ibm_governance_verifications_total{decision="passed"} 0')

        if self.prompt_latencies:
            p95 = sorted(self.prompt_latencies)[int(len(self.prompt_latencies) * 0.95)]
            lines.extend([
                "",
                "# HELP gemini_prompt_latency_seconds Summary of Gemini prompt generation latencies.",
                "# TYPE gemini_prompt_latency_seconds gauge",
                f"gemini_prompt_latency_seconds {p95:.4f}",
            ])
        lines.append("")
        return "\n".join(lines)


telemetry = GrafanaTelemetry()
