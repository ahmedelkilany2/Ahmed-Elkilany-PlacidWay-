"""Search: BM25 (exact words) plus embeddings (meaning), combined with reciprocal rank fusion.
If embeddings are turned off or fail to load, it uses BM25 only."""
import logging
import re

import numpy as np
from rank_bm25 import BM25Okapi

from .config import settings

log = logging.getLogger("index")
STOP = set("the a an of in on at for to and or is are was were be do does did how much what which who can i you it this that with from about me my".split())
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks if t not in STOP]


class KnowledgeIndex:
    def __init__(self, chunks: list[dict], use_embeddings: bool | None = None):
        self.chunks = chunks
        self.tokens = [tokenize(c["index_text"]) for c in chunks]
        self._sets = [set(t) for t in self.tokens]
        self.bm25 = BM25Okapi(self.tokens) if chunks else None
        self.emb, self.model = None, None
        if (settings.embeddings if use_embeddings is None else use_embeddings) and chunks:
            try:
                from fastembed import TextEmbedding
                self.model = TextEmbedding(settings.embed_model)
                self.emb = np.array(list(self.model.embed([c["index_text"] for c in chunks])), dtype=np.float32)
                self.emb /= np.linalg.norm(self.emb, axis=1, keepdims=True) + 1e-9
            except Exception as e:  # noqa: BLE001
                log.warning("Embeddings unavailable, falling back to BM25 only: %s", e)
                self.emb = self.model = None

    @property
    def mode(self) -> str:
        return "hybrid (BM25 + embeddings)" if self.emb is not None else "BM25 only"

    def search(self, query: str, k: int | None = None) -> list[dict]:
        k = k or settings.top_k
        if not self.chunks:
            return []
        n = len(self.chunks)
        q = tokenize(query)
        bm = np.array(self.bm25.get_scores(q)) if q else np.zeros(n)
        dense = np.zeros(n)
        if self.emb is not None:
            qv = np.array(list(self.model.embed([QUERY_PREFIX + query]))[0], dtype=np.float32)
            qv /= np.linalg.norm(qv) + 1e-9
            dense = self.emb @ qv
        fused = np.zeros(n)
        for scores in ([bm] + ([dense] if self.emb is not None else [])):
            for rank, i in enumerate(np.argsort(-scores)[:30]):
                fused[i] += 1.0 / (60 + rank)          # rank fusion
        top = np.argsort(-fused)[:k]
        qset = set(q)
        cov = lambda i: (len(qset & self._sets[i]) / len(qset)) if qset else 0.0
        return [{**self.chunks[i], "rrf": float(fused[i]), "dense": float(dense[i]), "bm25": float(bm[i]),
                 "coverage": cov(i)} for i in top]

    @staticmethod
    def is_relevant(hits: list[dict]) -> bool:
        """Reject clearly unrelated questions before calling the LLM. Needs either a decent embedding
        similarity or enough of the question's words in the best chunk. Kept lenient on purpose,
        the answer step does the stricter check."""
        if not hits:
            return False
        lexical = max(h["coverage"] for h in hits) >= settings.min_coverage
        semantic = any(h["dense"] for h in hits) and max(h["dense"] for h in hits) >= settings.min_dense
        return lexical or semantic
