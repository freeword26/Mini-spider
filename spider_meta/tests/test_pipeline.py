import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from spider_meta.core.pipeline_orchestrator import PipelineOrchestrator
from spider_meta.core.schemas import TaskTree, TaskIntent, SubTask, TaskStatus, TaskResult


class MockSettings:
    redis_host = "localhost"
    redis_port = 6381
    redis_db = 0
    debug = False
    llm_model = "default"
    llm_max_tokens = 4096
    llm_api_url = ""
    llm_api_key = ""
    kg_collection_name = "test"
    kg_top_k = 5
    enable_knowledge_retrieval = False
    kg_cache_size = 100
    kg_retrieval_timeout = 2.0
    worker_heartbeat_timeout = 3600
    worker_max_tasks = 5


@pytest.fixture
def orchestrator():
    settings = MockSettings()
    with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=settings):
        with patch("spider_meta.core.pipeline_orchestrator.KnowledgeRetriever"):
            with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=settings):
                orch = PipelineOrchestrator(settings=settings)
                yield orch


@pytest.mark.asyncio
async def test_execute_returns_task_result(orchestrator):
    result = await orchestrator.execute("测试任务")
    assert isinstance(result, TaskResult)


@pytest.mark.asyncio
async def test_execute_creates_pipeline_status(orchestrator):
    result = await orchestrator.execute("分析数据")
    status = orchestrator.get_pipeline_status(result.pipeline_id)
    assert status is not None
    assert status.pipeline_id == result.pipeline_id


@pytest.mark.asyncio
async def test_pipeline_failed_status():
    settings = MockSettings()
    with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=settings):
        with patch("spider_meta.core.pipeline_orchestrator.KnowledgeRetriever"):
            with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=settings):
                orch = PipelineOrchestrator(settings=settings)
                orch.decomposer = MagicMock()
                orch.decomposer._analyze_intent = AsyncMock(side_effect=Exception("fail"))
                orch.decomposer.decompose = AsyncMock(side_effect=Exception("fail"))
                result = await orch.execute("task")
                assert result.status == TaskStatus.FAILED
                assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_get_result(orchestrator):
    result = await orchestrator.execute("task")
    fetched = orchestrator.get_result(result.pipeline_id)
    assert fetched is not None
    assert fetched.pipeline_id == result.pipeline_id


@pytest.mark.asyncio
async def test_list_pipelines(orchestrator):
    await orchestrator.execute("task1")
    await orchestrator.execute("task2")
    pipelines = orchestrator.list_pipelines()
    assert len(pipelines) >= 2
