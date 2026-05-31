import asyncio
import logging
import time
from asyncio import TimeoutError as AsyncTimeoutError
from collections import OrderedDict
from typing import Dict, List, Optional

from spider_meta.core.schemas import KnowledgeDoc
from spider_meta.config import load_settings

logger = logging.getLogger("meta-agent.knowledge")


class LRUCache:

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[List[KnowledgeDoc]]:
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: List[KnowledgeDoc]):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def stats(self) -> Dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0,
            "size": len(self.cache),
            "capacity": self.capacity,
        }


class KnowledgeRetriever:

    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        self.cache = LRUCache(capacity=self.settings.kg_cache_size)
        self._chroma_client = None
        self._collection = None
        self._available = False
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            self._chroma_client = chromadb.Client()
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.settings.kg_collection_name
            )
            self._available = True
            logger.info(f"KnowledgeRetriever initialized with collection: {self.settings.kg_collection_name}")
        except ImportError:
            logger.warning("ChromaDB not installed, knowledge retrieval will return empty results")
            self._available = False
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}, knowledge retrieval degraded")
            self._available = False

    async def retrieve(self, query: str, top_k: int = None) -> List[KnowledgeDoc]:
        if not self.settings.enable_knowledge_retrieval:
            return []

        if top_k is None:
            top_k = self.settings.kg_top_k

        cache_key = f"{query}:{top_k}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            results = await asyncio.wait_for(
                self._search_vector(query, top_k),
                timeout=self.settings.kg_retrieval_timeout
            )
            if results:
                self.cache.put(cache_key, results)
                return results
        except (AsyncTimeoutError, asyncio.TimeoutError):
            logger.warning(f"Knowledge retrieval timed out for query: {query[:50]}")
        except Exception as e:
            logger.error(f"Knowledge retrieval error: {e}")

        try:
            results = await self._search_keyword(query, top_k)
            if results:
                self.cache.put(cache_key, results)
                return results
        except Exception as e:
            logger.error(f"Keyword search fallback error: {e}")

        return []

    async def _search_vector(self, query: str, top_k: int) -> List[KnowledgeDoc]:
        if not self._available or self._collection is None:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k
            )
            docs = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    docs.append(KnowledgeDoc(
                        doc_id=results["ids"][0][i] if results.get("ids") else f"vec-{i}",
                        content=doc,
                        source="knowledge_graph",
                        score=1.0 - (results["distances"][0][i] if results.get("distances") else 0.0),
                    ))
            return docs
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _search_keyword(self, query: str, top_k: int) -> List[KnowledgeDoc]:
        if not self._available or self._collection is None:
            return []

        try:
            results = self._collection.get(
                where_document={"$contains": query},
                limit=top_k
            )
            docs = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"]):
                    docs.append(KnowledgeDoc(
                        doc_id=results["ids"][i] if results.get("ids") else f"kw-{i}",
                        content=doc,
                        source="knowledge_graph_keyword",
                        score=0.5,
                    ))
            return docs
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def stats(self) -> Dict:
        return {
            "available": self._available,
            "collection": self.settings.kg_collection_name,
            "cache": self.cache.stats(),
        }

    def clear_cache(self):
        self.cache = LRUCache(capacity=self.settings.kg_cache_size)
