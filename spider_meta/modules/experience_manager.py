import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from spider_meta.core.schemas import TaskTree, Experience
from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.experience")


class ExperienceManager:
    def __init__(self, db_path: str = None, settings=None):
        self.settings = settings or load_settings()
        self.db_path = db_path or str(Path(__file__).resolve().parent.parent.parent / "data" / "experiences.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                experience_id TEXT PRIMARY KEY,
                task_summary TEXT NOT NULL,
                task_tree_snapshot TEXT NOT NULL,
                worker_assignments TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON experiences(created_at DESC)")
        conn.commit()
        conn.close()

    def store_experience(
        self,
        task_summary: str,
        task_tree: TaskTree,
        worker_assignments: Dict[str, str],
    ) -> Experience:
        exp = Experience(
            experience_id=f"exp-{uuid.uuid4().hex[:8]}",
            task_summary=task_summary,
            task_tree_snapshot=task_tree.model_dump(),
            worker_assignments=worker_assignments,
            created_at=datetime.now().isoformat(),
        )
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO experiences (experience_id, task_summary, task_tree_snapshot, worker_assignments, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                exp.experience_id,
                exp.task_summary,
                json.dumps(exp.task_tree_snapshot, ensure_ascii=False),
                json.dumps(exp.worker_assignments, ensure_ascii=False),
                exp.created_at,
            ),
        )
        conn.commit()
        conn.close()
        logger.info(f"Experience stored: {exp.experience_id}")
        return exp

    def retrieve_similar(self, task: str, top_k: int = None) -> List[Experience]:
        if not self.settings.enable_experience_reuse:
            return []
        if top_k is None:
            top_k = self.settings.experience_top_k

        keywords = [w for w in task.lower().split() if len(w) > 1]

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if keywords:
            placeholders = " OR ".join(["task_summary LIKE ?"] * len(keywords))
            params = [f"%{kw}%" for kw in keywords]
            rows = conn.execute(
                f"SELECT * FROM experiences WHERE {placeholders} ORDER BY created_at DESC LIMIT ?",
                params + [top_k],
            ).fetchall()

            if not rows:
                rows = conn.execute(
                    "SELECT * FROM experiences ORDER BY created_at DESC LIMIT ?",
                    (top_k,),
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM experiences ORDER BY created_at DESC LIMIT ?",
                (top_k,),
            ).fetchall()

        conn.close()

        experiences = []
        for row in rows:
            experiences.append(Experience(
                experience_id=row["experience_id"],
                task_summary=row["task_summary"],
                task_tree_snapshot=json.loads(row["task_tree_snapshot"]),
                worker_assignments=json.loads(row["worker_assignments"]),
                created_at=row["created_at"],
            ))
        return experiences

    def get_all_experiences(self, limit: int = 50) -> List[Experience]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM experiences ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [Experience(
            experience_id=r["experience_id"],
            task_summary=r["task_summary"],
            task_tree_snapshot=json.loads(r["task_tree_snapshot"]),
            worker_assignments=json.loads(r["worker_assignments"]),
            created_at=r["created_at"],
        ) for r in rows]

    def delete_experience(self, experience_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("DELETE FROM experiences WHERE experience_id = ?", (experience_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def clear_all(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM experiences")
        conn.commit()
        conn.close()

    def stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
        oldest = conn.execute("SELECT MIN(created_at) FROM experiences").fetchone()[0]
        newest = conn.execute("SELECT MAX(created_at) FROM experiences").fetchone()[0]
        conn.close()
        return {
            "total_experiences": count,
            "oldest": oldest,
            "newest": newest,
            "db_path": self.db_path,
        }
