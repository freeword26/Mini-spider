import pytest
from unittest.mock import MagicMock
from spider_meta.core.dag_engine import DAGEngine, DAG
from spider_meta.core.schemas import SubTask
from spider_meta.core.worker_dispatcher import WorkerDispatcher


class MockSettings:
    default_parallelism = 3
    min_parallelism = 1
    max_parallelism = 10
    redis_host = "localhost"
    redis_port = 6381
    redis_db = 0
    worker_heartbeat_timeout = 5
    worker_max_tasks = 5


def make_task(task_id, deps=None):
    return SubTask(task_id=task_id, title=f"Task {task_id}", dependency=deps or [])


@pytest.fixture
def engine():
    return DAGEngine(settings=MockSettings())


def test_mark_and_unmark_sop(engine):
    engine.mark_subgraph_as_sop(["a", "b"])
    assert "a" in engine._sop_subgraphs
    engine.unmark_subgraph_as_sop(["a"])
    assert "a" not in engine._sop_subgraphs
    assert "b" in engine._sop_subgraphs


def test_sop_empty_list(engine):
    engine.mark_subgraph_as_sop([])
    assert len(engine._sop_subgraphs) == 0


def test_sop_duplicate_mark(engine):
    engine.mark_subgraph_as_sop(["a"])
    engine.mark_subgraph_as_sop(["a"])
    assert len(engine._sop_subgraphs) == 1


@pytest.mark.asyncio
async def test_sop_execution_is_serial(engine):
    tasks = [make_task(f"t{i}") for i in range(5)]
    dag = engine.build_graph(tasks)
    engine.mark_subgraph_as_sop(["t0", "t1", "t2"])
    mock_dispatcher = MagicMock(spec=WorkerDispatcher)
    mock_dispatcher.dispatch.return_value = "w1"
    results = await engine.execute(dag, mock_dispatcher)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_hotswap_at_runtime(engine):
    tasks = [make_task(f"t{i}") for i in range(3)]
    dag = engine.build_graph(tasks)
    engine.mark_subgraph_as_sop(["t0"])
    assert "t0" in engine._sop_subgraphs
    engine.unmark_subgraph_as_sop(["t0"])
    assert "t0" not in engine._sop_subgraphs
    engine.mark_subgraph_as_sop(["t1", "t2"])
    assert "t1" in engine._sop_subgraphs
    assert "t2" in engine._sop_subgraphs
    mock_dispatcher = MagicMock(spec=WorkerDispatcher)
    mock_dispatcher.dispatch.return_value = "w1"
    results = await engine.execute(dag, mock_dispatcher)
    assert len(results) == 3
