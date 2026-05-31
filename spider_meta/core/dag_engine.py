import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from spider_meta.core.schemas import SubTask, TaskStatus
from spider_meta.core.worker_dispatcher import WorkerDispatcher
from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.dag")


class DAG:

    def __init__(self):
        self.nodes: Dict[str, SubTask] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def add_node(self, task: SubTask):
        self.nodes[task.task_id] = task
        if task.task_id not in self.in_degree:
            self.in_degree[task.task_id] = 0

    def add_edge(self, from_id: str, to_id: str):
        self.edges[from_id].append(to_id)
        self.in_degree[to_id] += 1

    def get_sources(self) -> List[str]:
        return [nid for nid, deg in self.in_degree.items() if deg == 0]

    def topological_sort(self) -> List[List[str]]:
        in_deg = dict(self.in_degree)
        layers = []
        queue = deque([nid for nid, deg in in_deg.items() if deg == 0])
        while queue:
            layer = list(queue)
            layers.append(layer)
            next_queue = deque()
            for nid in layer:
                for child in self.edges[nid]:
                    in_deg[child] -= 1
                    if in_deg[child] == 0:
                        next_queue.append(child)
            queue = next_queue
        total = sum(len(l) for l in layers)
        if total != len(self.nodes):
            raise ValueError("Cycle detected in DAG")
        return layers


class DAGEngine:

    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self._sop_subgraphs: Set[str] = set()
        self._current_concurrency: int = self.settings.default_parallelism
        self._dag: Optional[DAG] = None

    def build_graph(self, subtasks: List[SubTask]) -> DAG:
        dag = DAG()
        task_ids = {st.task_id for st in subtasks}
        for st in subtasks:
            dag.add_node(st)
        for st in subtasks:
            for dep_id in st.dependency:
                if dep_id in task_ids:
                    dag.add_edge(dep_id, st.task_id)
                else:
                    logger.warning(f"Dependency {dep_id} not found for task {st.task_id}")
        self._dag = dag
        logger.info(f"DAG built: {len(dag.nodes)} nodes, {len(dag.get_sources())} sources")
        return dag

    async def execute(self, dag: DAG, dispatcher: WorkerDispatcher, callback=None) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        layers = dag.topological_sort()
        for layer in layers:
            is_sop_layer = any(tid in self._sop_subgraphs for tid in layer)
            if is_sop_layer:
                for tid in layer:
                    if tid in dag.nodes:
                        result = await self._execute_single(dag.nodes[tid], dispatcher)
                        results[tid] = result
                        if callback:
                            callback(tid, result)
            else:
                semaphore = asyncio.Semaphore(self._current_concurrency)
                async def run_with_limit(st):
                    async with semaphore:
                        result = await self._execute_single(st, dispatcher)
                        results[st.task_id] = result
                        if callback:
                            callback(st.task_id, result)
                        return result
                tasks = [run_with_limit(dag.nodes[tid]) for tid in layer if tid in dag.nodes]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def _execute_single(self, subtask: SubTask, dispatcher: WorkerDispatcher) -> Any:
        subtask.status = TaskStatus.RUNNING
        worker_id = dispatcher.dispatch(subtask)
        if worker_id is None:
            subtask.status = TaskStatus.FAILED
            return None
        subtask.assigned_worker = worker_id
        subtask.status = TaskStatus.COMPLETED
        return {"worker_id": worker_id, "status": "completed"}

    def get_execution_order(self, dag: DAG) -> List[List[str]]:
        return dag.topological_sort()

    def get_graph_status(self, dag: DAG) -> Dict[str, Any]:
        return {
            "total_nodes": len(dag.nodes),
            "sources": dag.get_sources(),
            "layers": self.get_execution_order(dag),
            "sop_nodes": list(self._sop_subgraphs),
            "current_concurrency": self._current_concurrency,
        }

    def mark_subgraph_as_sop(self, task_ids: List[str]):
        for tid in task_ids:
            self._sop_subgraphs.add(tid)
        logger.info(f"SOP subgraph marked: {task_ids}")

    def unmark_subgraph_as_sop(self, task_ids: List[str]):
        for tid in task_ids:
            self._sop_subgraphs.discard(tid)

    def adjust_concurrency(self, worker_loads: Dict[str, float]):
        if not worker_loads:
            return
        avg_load = sum(worker_loads.values()) / len(worker_loads)
        if avg_load > 0.8:
            self._current_concurrency = max(self.settings.min_parallelism, self._current_concurrency - 1)
        elif avg_load < 0.3:
            self._current_concurrency = min(self.settings.max_parallelism, self._current_concurrency + 1)
        logger.info(f"Concurrency adjusted to {self._current_concurrency} (avg_load={avg_load:.2f})")

    @property
    def current_concurrency(self) -> int:
        return self._current_concurrency
