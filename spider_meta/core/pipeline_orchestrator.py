import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from spider_meta.core.schemas import (
    PipelineStatus, TaskResult, TaskStatus, TaskTree, TaskIntent, SubTask
)
from spider_meta.core.worker_dispatcher import WorkerDispatcher
from spider_meta.modules.task_decomposer import TaskDecomposer
from spider_meta.services.llm_service import LLMService
from spider_meta.modules.knowledge_retriever import KnowledgeRetriever
from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.orchestrator")


class PipelineOrchestrator:
    def __init__(
        self,
        decomposer: TaskDecomposer = None,
        dispatcher: WorkerDispatcher = None,
        llm_service: LLMService = None,
        knowledge_retriever: KnowledgeRetriever = None,
        settings=None,
    ):
        self.settings = settings or load_settings()
        self.decomposer = decomposer or TaskDecomposer(llm_service=llm_service)
        self.dispatcher = dispatcher or WorkerDispatcher()
        self.llm_service = llm_service or LLMService(settings=self.settings)
        self.knowledge_retriever = knowledge_retriever or KnowledgeRetriever(settings=self.settings)
        self._pipelines: Dict[str, PipelineStatus] = {}
        self._results: Dict[str, TaskResult] = {}

    async def execute(self, task: str) -> TaskResult:
        pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
        status = PipelineStatus(
            pipeline_id=pipeline_id,
            status=TaskStatus.RUNNING,
            current_phase="understanding",
        )
        self._pipelines[pipeline_id] = status

        try:
            intent = await self._understand(task)
            status.current_phase = "decomposing"
            tree = await self._decompose(intent)
            status.total_tasks = len(tree.subtasks)
            status.current_phase = "dispatching"
            results = await self._dispatch(tree)
            status.current_phase = "aggregating"
            task_result = await self._aggregate(pipeline_id, tree, results)
            status.status = TaskStatus.COMPLETED
            status.completed_tasks = len([r for r in results.values() if r is not None])
            status.failed_tasks = len([r for r in results.values() if r is None])
            task_result.status = TaskStatus.COMPLETED
            task_result.completed_at = datetime.now().isoformat()
            status.updated_at = datetime.now().isoformat()
            self._results[pipeline_id] = task_result
            logger.info(f"Pipeline {pipeline_id} completed: {status.completed_tasks}/{status.total_tasks} tasks")
            return task_result
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            status.status = TaskStatus.FAILED
            status.updated_at = datetime.now().isoformat()
            result = TaskResult(
                pipeline_id=pipeline_id,
                tree=TaskTree(title=task[:100]),
                status=TaskStatus.FAILED,
                errors=[str(e)],
                completed_at=datetime.now().isoformat(),
            )
            self._results[pipeline_id] = result
            return result

    async def _understand(self, task: str) -> TaskIntent:
        knowledge = []
        if self.settings.enable_knowledge_retrieval:
            try:
                knowledge = await self.knowledge_retriever.retrieve(task)
            except Exception as e:
                logger.warning(f"Knowledge retrieval failed during understand: {e}")
        return await self.decomposer._analyze_intent(task)

    async def _decompose(self, intent: TaskIntent) -> TaskTree:
        tree = await self.decomposer.decompose(intent.original_task)
        return tree

    async def _dispatch(self, tree: TaskTree) -> Dict[str, Optional[str]]:
        results = {}
        for subtask in tree.subtasks:
            try:
                if subtask.dependency:
                    all_done = all(dep_id in results and results[dep_id] is not None for dep_id in subtask.dependency)
                    if not all_done:
                        logger.warning(f"Dependencies not met for {subtask.task_id}, skipping")
                        results[subtask.task_id] = None
                        continue
                worker_id = self.dispatcher.dispatch(subtask)
                if worker_id:
                    subtask.assigned_worker = worker_id
                    subtask.status = TaskStatus.RUNNING
                results[subtask.task_id] = worker_id
            except Exception as e:
                logger.error(f"Failed to dispatch subtask {subtask.task_id}: {e}")
                results[subtask.task_id] = None
        return results

    async def _aggregate(self, pipeline_id: str, tree: TaskTree, results: Dict[str, Optional[str]]) -> TaskResult:
        return TaskResult(
            pipeline_id=pipeline_id,
            tree=tree,
            status=TaskStatus.COMPLETED,
            results=results,
        )

    def get_pipeline_status(self, pipeline_id: str) -> Optional[PipelineStatus]:
        return self._pipelines.get(pipeline_id)

    def get_result(self, pipeline_id: str) -> Optional[TaskResult]:
        return self._results.get(pipeline_id)

    def list_pipelines(self):
        return {pid: s.model_dump() for pid, s in self._pipelines.items()}
