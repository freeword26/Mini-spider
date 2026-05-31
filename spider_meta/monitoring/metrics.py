import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger("meta-agent.metrics")


@dataclass
class MetricSnapshot:
    retrieval_latency_ms: float = 0.0
    retrieval_count: int = 0
    retrieval_hits: int = 0
    retrieval_misses: int = 0
    empty_results: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0


class MetricsCollector:

    def __init__(self):
        self._snapshots: Dict[str, MetricSnapshot] = {}
        self._start_time = time.time()

    def _get_snapshot(self, module: str) -> MetricSnapshot:
        if module not in self._snapshots:
            self._snapshots[module] = MetricSnapshot()
        return self._snapshots[module]

    def record_retrieval_latency(self, module: str, ms: float):
        snap = self._get_snapshot(module)
        snap.retrieval_count += 1
        snap.retrieval_latency_ms = (
            (snap.retrieval_latency_ms * (snap.retrieval_count - 1) + ms) / snap.retrieval_count
        )

    def record_recall_rate(self, module: str, hit: bool):
        snap = self._get_snapshot(module)
        if hit:
            snap.retrieval_hits += 1
        else:
            snap.retrieval_misses += 1

    def record_empty_result(self, module: str, is_empty: bool):
        if is_empty:
            snap = self._get_snapshot(module)
            snap.empty_results += 1

    def record_cache_hit(self, module: str, hit: bool):
        snap = self._get_snapshot(module)
        if hit:
            snap.cache_hits += 1
        else:
            snap.cache_misses += 1

    def record_error(self, module: str):
        snap = self._get_snapshot(module)
        snap.errors += 1

    def report(self) -> Dict:
        uptime = time.time() - self._start_time
        report = {
            "uptime_seconds": round(uptime, 2),
            "modules": {}
        }
        for module, snap in self._snapshots.items():
            total_cache = snap.cache_hits + snap.cache_misses
            total_retrieval = snap.retrieval_hits + snap.retrieval_misses
            report["modules"][module] = {
                "avg_latency_ms": round(snap.retrieval_latency_ms, 2),
                "total_retrievals": snap.retrieval_count,
                "recall_rate": round(snap.retrieval_hits / total_retrieval, 4) if total_retrieval > 0 else 0.0,
                "empty_result_rate": round(snap.empty_results / snap.retrieval_count, 4) if snap.retrieval_count > 0 else 0.0,
                "cache_hit_rate": round(snap.cache_hits / total_cache, 4) if total_cache > 0 else 0.0,
                "errors": snap.errors,
            }
        return report

    def reset(self):
        self._snapshots.clear()
        self._start_time = time.time()


metrics = MetricsCollector()
