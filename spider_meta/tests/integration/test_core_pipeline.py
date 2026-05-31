import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from spider_meta.core.pipeline_orchestrator import PipelineOrchestrator
from spider_meta.core.worker_dispatcher import WorkerDispatcher
from spider_meta.modules.task_decomposer import TaskDecomposer
from spider_meta.core.schemas import TaskTree, SubTask, TaskStatus, TaskResult


class MockSettings:
    redis_host = "localhost"
    redis_port = 6381
    redis_db = 0
    debug = False
    llm_model = "test"
    llm_max_tokens = 1024
    llm_api_url = ""
    llm_api_key = ""
    kg_collection_name = "test"
    kg_top_k = 3
    enable_knowledge_retrieval = False
    kg_cache_size = 10
    kg_retrieval_timeout = 1.0
    worker_heartbeat_timeout = 3600
    worker_max_tasks = 5


@pytest.fixture
def integration_orchestrator():
    settings = MockSettings()
    mock_redis = MagicMock()
    mock_redis.ping.side_effect = Exception("No Redis")
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=settings):
        dispatcher = WorkerDispatcher(redis_client=mock_redis)
        dispatcher._redis_available = False
        dispatcher.register_worker("w1", ["coding", "analysis", "general"], "http://localhost:8001")
        dispatcher.register_worker("w2", ["search", "general"], "http://localhost:8002")
        dispatcher._redis_available = False
    decomposer = TaskDecomposer(llm_service=None, max_depth=1)
    llm_service = None
    with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=settings):
        orch = PipelineOrchestrator(
            decomposer=decomposer,
            dispatcher=dispatcher,
            llm_service=llm_service,
            settings=settings,
        )
        yield orch


@pytest.mark.asyncio
async def test_full_pipeline_executes(integration_orchestrator):
    result = await integration_orchestrator.execute("Develop a user login feature")
    assert isinstance(result, TaskResult)
    assert result.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_generates_subtasks(integration_orchestrator):
    result = await integration_orchestrator.execute("Write an API interface")
    assert len(result.tree.subtasks) > 0


@pytest.mark.asyncio
async def test_pipeline_assigns_workers(integration_orchestrator):
    result = await integration_orchestrator.execute("Research market data")
    assert result.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_status_tracking(integration_orchestrator):
    result = await integration_orchestrator.execute("Test task")
    status = integration_orchestrator.get_pipeline_status(result.pipeline_id)
    assert status is not None
    assert status.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING]


@pytest.mark.asyncio
async def test_research_pipeline(integration_orchestrator):
    result = await integration_orchestrator.execute("Research market competitors")
    assert result.status == TaskStatus.COMPLETED
    assert len(result.tree.subtasks) > 0
