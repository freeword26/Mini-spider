import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import redis

from spider_meta.core.schemas import SubTask, WorkerCapability, WorkerStatus, TaskStatus
from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.dispatcher")


class WorkerDispatcher:
    def __init__(self, redis_client=None):
        self.settings = load_settings()
        self.redis = redis_client
        self._local_workers: Dict[str, WorkerCapability] = {}
        self._redis_available = False

    def _get_redis(self):
        if self.redis:
            return self.redis
        if not self._redis_available:
            return None
        try:
            self.redis = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                socket_connect_timeout=2,
                decode_responses=True
            )
            self.redis.ping()
            self._redis_available = True
            return self.redis
        except (redis.ConnectionError, redis.TimeoutError):
            self._redis_available = False
            logger.warning("Redis unavailable, using in-memory worker registry")
            return None

    def register_worker(self, worker_id: str, skills: List[str], endpoint: str) -> WorkerCapability:
        wc = WorkerCapability(
            worker_id=worker_id,
            skills=skills,
            endpoint=endpoint,
            status=WorkerStatus.ONLINE,
            last_heartbeat=datetime.now().isoformat(),
            load=0.0,
            active_tasks=0,
        )
        self._local_workers[worker_id] = wc
        r = self._get_redis()
        if r:
            try:
                r_key = f"worker:{worker_id}:capability"
                r.set(r_key, wc.model_encode() if hasattr(wc, 'model_encode') else json.dumps(wc.model_dump()), ex=self.settings.worker_heartbeat_timeout * 3)
                self.heartbeat(worker_id, 0.0)
            except (redis.ConnectionError, redis.TimeoutError):
                logger.warning(f"Redis failed during register of {worker_id}, using local only")
        logger.info(f"Worker registered: {worker_id} with skills={skills}")
        return wc

    def heartbeat(self, worker_id: str, load: float) -> bool:
        if worker_id not in self._local_workers:
            logger.warning(f"Heartbeat from unregistered worker: {worker_id}")
            return False
        now = datetime.now().isoformat()
        self._local_workers[worker_id].last_heartbeat = now
        self._local_workers[worker_id].load = load
        if load >= 0.9:
            self._local_workers[worker_id].status = WorkerStatus.BUSY
        else:
            self._local_workers[worker_id].status = WorkerStatus.ONLINE
        r = self._get_redis()
        if r:
            try:
                key = f"worker:{worker_id}:heartbeat"
                data = json.dumps({"load": load, "timestamp": now, "worker_id": worker_id})
                r.setex(key, self.settings.worker_heartbeat_timeout, data)
                cap_key = f"worker:{worker_id}:capability"
                r.setex(cap_key, self.settings.worker_heartbeat_timeout * 3, json.dumps(self._local_workers[worker_id].model_dump()))
                self._redis_available = True
            except (redis.ConnectionError, redis.TimeoutError):
                self._redis_available = False
                logger.warning(f"Redis failed during heartbeat for {worker_id}")
        return True

    def dispatch(self, subtask: SubTask) -> Optional[str]:
        available = self.list_available_workers()
        if not available:
            logger.warning(f"No available workers for subtask {subtask.task_id}")
            return None
        candidates = self._match_skill(subtask.required_skill, available)
        if not candidates:
            logger.warning(f"No workers match skill '{subtask.required_skill}' for subtask {subtask.task_id}")
            return None
        best = self._balance_load(candidates)
        if best is None:
            return None
        best.active_tasks += 1
        best.last_heartbeat = datetime.now().isoformat()
        logger.info(f"Dispatched subtask {subtask.task_id} to worker {best.worker_id}")
        return best.worker_id

    def _match_skill(self, required_skill: str, workers: List[WorkerCapability]) -> List[WorkerCapability]:
        if not required_skill or required_skill == "general":
            return workers
        matched = []
        for w in workers:
            if required_skill in w.skills:
                matched.append(w)
        return matched

    def _balance_load(self, candidates: List[WorkerCapability]) -> Optional[WorkerCapability]:
        if not candidates:
            return None
        best = None
        best_score = float("inf")
        for w in candidates:
            score = w.load * (1 + w.active_tasks)
            if score < best_score:
                best_score = score
                best = w
        return best

    def _is_worker_alive(self, worker_id: str) -> bool:
        if worker_id not in self._local_workers:
            return False
        wc = self._local_workers[worker_id]
        if wc.status == WorkerStatus.OFFLINE:
            return False
        r = self._get_redis()
        if r:
            try:
                key = f"worker:{worker_id}:heartbeat"
                data = r.get(key)
                if data is None:
                    wc.status = WorkerStatus.OFFLINE
                    return False
                return True
            except (redis.ConnectionError, redis.TimeoutError):
                self._redis_available = False
        if wc.last_heartbeat is None:
            wc.status = WorkerStatus.OFFLINE
            return False
        try:
            hb_time = datetime.fromisoformat(wc.last_heartbeat)
            elapsed = (datetime.now() - hb_time).total_seconds()
            if elapsed > self.settings.worker_heartbeat_timeout:
                wc.status = WorkerStatus.OFFLINE
                return False
            return True
        except (ValueError, TypeError):
            return False

    def get_worker_status(self, worker_id: str) -> Optional[WorkerCapability]:
        return self._local_workers.get(worker_id)

    def list_available_workers(self, skill: str = None) -> List[WorkerCapability]:
        available = []
        for wid, wc in self._local_workers.items():
            if self._is_worker_alive(wid):
                available.append(wc)
        if skill:
            available = self._match_skill(skill, available)
        return available

    def unregister_worker(self, worker_id: str) -> bool:
        if worker_id in self._local_workers:
            del self._local_workers[worker_id]
        r = self._get_redis()
        if r:
            try:
                r.delete(f"worker:{worker_id}:heartbeat")
                r.delete(f"worker:{worker_id}:capability")
            except (redis.ConnectionError, redis.TimeoutError):
                logger.warning(f"Redis failed during unregister of {worker_id}")
        logger.info(f"Worker unregistered: {worker_id}")
        return True

    def get_all_workers(self) -> Dict[str, WorkerCapability]:
        return dict(self._local_workers)
