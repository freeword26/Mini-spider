import json
import logging
from pathlib import Path
from typing import Dict, List

from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.kg-export")


class KGExporter:
    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self._chroma_client = None
        self._collection = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb

            self._chroma_client = chromadb.Client()
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.settings.kg_collection_name
            )
            logger.info(f"KGExporter connected to collection: {self.settings.kg_collection_name}")
        except ImportError:
            logger.warning("ChromaDB not installed, export will be no-op")
            self._chroma_client = None
            self._collection = None
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            self._chroma_client = None
            self._collection = None

    def export_from_source(self, source_dir: str, output_collection: str = None) -> int:
        if self._collection is None:
            logger.error("ChromaDB not available, cannot export")
            return 0

        source_path = Path(source_dir)
        if not source_path.exists():
            logger.error(f"Source directory not found: {source_dir}")
            return 0

        total_exported = 0
        batch_size = 100
        batch_docs = []
        batch_ids = []
        batch_metadatas = []

        for jsonl_file in source_path.rglob("*.jsonl"):
            logger.info(f"Processing: {jsonl_file}")
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        triple = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON at {jsonl_file}:{line_num}")
                        continue

                    text = self._triple_to_text(
                        triple.get("subject", ""),
                        triple.get("predicate", ""),
                        triple.get("object", ""),
                    )
                    doc_id = f"{jsonl_file.stem}-{line_num}-{hash(text) % 10000000:07d}"

                    batch_docs.append(text)
                    batch_ids.append(doc_id)
                    batch_metadatas.append({
                        "source_file": str(jsonl_file),
                        "subject": triple.get("subject", ""),
                        "predicate": triple.get("predicate", ""),
                        "object": triple.get("object", ""),
                    })

                    if len(batch_docs) >= batch_size:
                        self._flush_batch(batch_docs, batch_ids, batch_metadatas)
                        total_exported += len(batch_docs)
                        batch_docs = []
                        batch_ids = []
                        batch_metadatas = []

        if batch_docs:
            self._flush_batch(batch_docs, batch_ids, batch_metadatas)
            total_exported += len(batch_docs)

        logger.info(f"Export complete: {total_exported} documents")
        return total_exported

    def _flush_batch(self, docs: List[str], ids: List[str], metadatas: List[Dict]):
        if self._collection is None or not docs:
            return
        try:
            self._collection.add(
                documents=docs,
                ids=ids,
                metadatas=metadatas,
            )
        except Exception as e:
            logger.error(f"Batch write failed: {e}")

    def _triple_to_text(self, subject: str, predicate: str, obj: str) -> str:
        return f"{subject} {predicate} {obj}"

    def export_from_triples(self, triples: List[Dict[str, str]]) -> int:
        if self._collection is None:
            return 0

        docs = []
        ids = []
        metadatas = []

        for i, triple in enumerate(triples):
            text = self._triple_to_text(
                triple.get("subject", ""),
                triple.get("predicate", ""),
                triple.get("object", ""),
            )
            docs.append(text)
            ids.append(f"triple-{i}-{hash(text) % 10000000:07d}")
            metadatas.append({
                "subject": triple.get("subject", ""),
                "predicate": triple.get("predicate", ""),
                "object": triple.get("object", ""),
            })

        if docs:
            self._flush_batch(docs, ids, metadatas)

        return len(docs)

    def get_collection_stats(self) -> Dict:
        if self._collection is None:
            return {"available": False}
        try:
            count = self._collection.count()
            return {
                "available": True,
                "collection": self.settings.kg_collection_name,
                "document_count": count,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
