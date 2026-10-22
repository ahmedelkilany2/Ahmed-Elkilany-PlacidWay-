"""Holds the current index. Built at startup and replaced after a refresh."""
import asyncio
import logging
import threading
from datetime import datetime, timezone

from . import ingest
from .chat import Bot
from .chunking import chunk_pages
from .config import settings
from .index import KnowledgeIndex

log = logging.getLogger("service")


class Service:
    def __init__(self):
        self.bot: Bot | None = None
        self.pages: list[dict] = []
        self.built_at = None
        self._refresh_lock = threading.Lock()
        self.last_report: dict = {}

    def _build(self, pages):
        chunks = chunk_pages(pages)
        index = KnowledgeIndex(chunks)
        llm = self.bot.llm if self.bot else None
        self.bot = Bot(index, llm)          # swapping the reference keeps the site up during a rebuild
        self.pages, self.built_at = pages, datetime.now(timezone.utc).isoformat(timespec="seconds")
        log.info("index ready: %d pages, %d chunks, %s", len(pages), len(chunks), index.mode)

    def start(self):
        pages = ingest.load_pages()
        if not pages:
            log.info("no snapshot found - crawling live")
            pages, self.last_report = ingest.crawl()
            if pages:
                ingest.save_pages(pages)
        if pages:
            self._build(pages)
        else:
            log.error("knowledge base is empty (crawl failed and no snapshot). Run `python -m app.ingest`.")

    def refresh(self) -> dict:
        if not self._refresh_lock.acquire(blocking=False):
            return {"status": "already_running"}
        try:
            pages, report = ingest.crawl()
            if not pages:
                return {"status": "failed", **report}
            if report["changed"] or report["new"] or self.bot is None:
                ingest.save_pages(pages)
                self._build(pages)
            self.last_report = report
            return {"status": "ok", "rebuilt": bool(report["changed"] or report["new"]), **report}
        finally:
            self._refresh_lock.release()

    async def auto_refresh_loop(self):
        if settings.refresh_hours <= 0:
            return
        while True:
            await asyncio.sleep(settings.refresh_hours * 3600)
            try:
                await asyncio.to_thread(self.refresh)
            except Exception:  # noqa: BLE001
                log.exception("auto refresh failed")

    def status(self) -> dict:
        return {
            "ready": self.bot is not None,
            "retrieval": self.bot.index.mode if self.bot else None,
            "model": settings.llm_model,
            "pages": [{"url": p["url"], "type": p["type"], "fetched_at": p["fetched_at"], "stale": p.get("stale", False)} for p in self.pages],
            "chunks": len(self.bot.index.chunks) if self.bot else 0,
            "index_built_at": self.built_at,
            "last_refresh": self.last_report,
        }
