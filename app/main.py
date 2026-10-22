import asyncio
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import store
from .config import ROOT, settings
from .prompts import TEMPLATES
from .service import Service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")
service = Service()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(service.start)
    task = asyncio.create_task(service.auto_refresh_loop())
    yield
    task.cancel()


app = FastAPI(title="PlacidWay Knowledge Chatbot", lifespan=lifespan)

# simple in-memory rate limit to protect the free LLM quota
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request, limit: int = 20, window: int = 60, scope: str = "chat"):
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "?").split(",")[0].strip()
    q, now = _hits[f"{scope}:{ip}"], time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests - please wait a moment.")
    q.append(now)


def admin(x_admin_token: str = Header(default="")):
    if not settings.admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Admin token required.")


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[Turn] = Field(default_factory=list, max_length=12)
    disclaimer_shown: bool = False


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=200)
    interest: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=1000)
    consent: bool = False
    website: str = ""          # hidden field, only bots fill it


@app.post("/api/chat", dependencies=[Depends(rate_limit)])
async def chat(body: ChatIn):
    if not service.bot:
        raise HTTPException(503, "Knowledge base is not loaded yet. Please try again shortly.")
    history = [t.model_dump() for t in body.history][-8:]
    try:
        return await asyncio.to_thread(service.bot.answer, body.message.strip(), history, body.disclaimer_shown)
    except Exception:  # noqa: BLE001
        log.exception("chat failed")
        return JSONResponse({"answer": TEMPLATES["error"], "sources": [], "answerable": False, "cta": None,
                             "show_lead_form": False, "disclaimer": None, "intent": "error"}, status_code=200)


@app.post("/api/lead")
async def lead(body: LeadIn, request: Request):
    rate_limit(request, limit=5, window=300, scope="lead")
    if body.website:                                   # bot detected, ignore quietly
        return {"ok": True}
    if not body.consent:
        raise HTTPException(400, "Please tick the consent box so we can contact you.")
    if not store.EMAIL_RE.match(body.email):
        raise HTTPException(400, "That email address doesn't look right.")
    store.add_lead(body.name, body.email, body.interest, body.note)
    if settings.lead_webhook:
        try:
            await asyncio.to_thread(requests.post, settings.lead_webhook, timeout=8,
                                    json={"name": body.name, "email": body.email, "interest": body.interest, "note": body.note})
        except requests.RequestException:
            log.warning("lead webhook failed (lead is still saved locally)")
    return {"ok": True}


@app.get("/api/status")
async def status():
    return service.status()


@app.get("/health")
async def health():
    return {"ok": True, "ready": service.bot is not None}


@app.post("/api/admin/refresh", dependencies=[Depends(admin)])
async def refresh():
    return await asyncio.to_thread(service.refresh)


@app.get("/api/admin/gaps", dependencies=[Depends(admin)])
async def gaps():
    return {"summary": store.gap_summary(), "recent": store.list_rows("gaps", 100)}


@app.get("/api/admin/leads", dependencies=[Depends(admin)])
async def leads():
    return store.list_rows("leads")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(ROOT / "static" / "index.html")
