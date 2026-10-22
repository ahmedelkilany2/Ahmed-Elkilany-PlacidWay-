"""Answering pipeline.

1. analyze the message (language, intent, English search query)
2. greetings, booking requests, out-of-scope and quote requests get a fixed reply
3. real questions: search -> relevance check -> answer from sources -> price check
"""
import logging
import threading

from . import guard, store
from .config import settings
from .index import KnowledgeIndex
from .llm import LLM, LLMError
from .prompts import ANALYZE_SYSTEM, GENERATE_SYSTEM, TEMPLATES
from .sources import ALLOWED_URLS, QUOTE_URL

log = logging.getLogger("chat")
CTA = {"label": "Get a free quote", "url": QUOTE_URL}


class Bot:
    def __init__(self, index: KnowledgeIndex, llm: LLM | None = None):
        self.index, self.llm = index, llm or LLM()
        self._i18n, self._lock = {}, threading.Lock()

    # ------------------------------------------------------------------ helpers
    def localize(self, key: str, language: str) -> str:
        en = TEMPLATES[key]
        if not language or language.lower().startswith("english"):
            return en
        ck = (key, language.lower())
        with self._lock:
            if ck in self._i18n:
                return self._i18n[ck]
        try:
            out = self.llm.text(f"Translate into {language}. Keep the meaning and tone exactly. Output only the translation.", en)
        except LLMError:
            return en
        with self._lock:
            self._i18n[ck] = out or en
        return out or en

    @staticmethod
    def _history_text(history: list[dict]) -> str:
        return "\n".join(f"{t['role']}: {t['content'][:400]}" for t in history[-6:]) or "(none)"

    def analyze(self, message: str, history: list[dict]) -> dict:
        try:
            a = self.llm.json(ANALYZE_SYSTEM, f"CHAT HISTORY:\n{self._history_text(history)}\n\nLATEST MESSAGE:\n{message}", 300)
        except LLMError:
            a = {}
        if a.get("intent") not in {"kb_question", "medical_advice", "booking_or_action", "quote_or_contact", "out_of_scope", "greeting"}:
            a["intent"] = "kb_question"
        a["language"] = a.get("language") or "English"
        a["standalone_query"] = a.get("standalone_query") or message
        a["user_stated_amounts"] = a.get("user_stated_amounts") or []
        return a

    def _result(self, text, a, **kw):
        base = {"answer": text, "sources": [], "answerable": True, "intent": a["intent"], "language": a["language"],
                "disclaimer": None, "cta": None, "show_lead_form": False}
        base.update(kw)
        return base

    def _not_found(self, a, message, reason, hits):
        store.add_gap(message, a["standalone_query"], reason, hits[0]["url"] if hits else "")
        return self._result(self.localize("not_found", a["language"]), a, answerable=False, cta=CTA)

    # ------------------------------------------------------------------ main entry
    def answer(self, message: str, history: list[dict], disclaimer_shown: bool = False) -> dict:
        a = self.analyze(message, history)
        intent, lang = a["intent"], a["language"]

        if intent in ("greeting", "booking_or_action", "out_of_scope", "quote_or_contact"):
            if intent == "booking_or_action":
                store.add_gap(message, a["standalone_query"], "action_request")
            elif intent == "out_of_scope":
                store.add_gap(message, a["standalone_query"], "out_of_scope")
            wants_cta = intent in ("booking_or_action", "quote_or_contact")
            return self._result(self.localize(intent, lang), a, cta=CTA if wants_cta else None, show_lead_form=wants_cta)

        hits = self.index.search(a["standalone_query"])
        if not self.index.is_relevant(hits):
            return self._not_found(a, message, "weak_retrieval", hits)

        sources = {f"S{i+1}": h for i, h in enumerate(hits)}
        context = "\n\n".join(f"[{sid}] {h['title']} - {h['section']}\nURL: {h['url']}\n{h['text']}" for sid, h in sources.items())
        context_plain = "\n".join(h["index_text"] for h in hits)
        user_amts = guard.amounts(" ".join(a["user_stated_amounts"]) + " " + message)
        system = GENERATE_SYSTEM.format(language=lang)
        user = (f"CHAT HISTORY:\n{self._history_text(history)}\n\nUSER QUESTION: {message}\n"
                f"(search query used: {a['standalone_query']})\n\nSOURCES:\n{context}")

        gen, problems = None, []
        for attempt in range(2):
            try:
                gen = self.llm.json(system, user + (f"\n\nYour previous answer was rejected: {problems}. "
                                                    "Use only amounts that appear verbatim in the SOURCES." if problems else ""), 800)
            except LLMError:
                return self._result(self.localize("error", lang), a, answerable=False, cta=CTA)
            problems = guard.check_prices(gen.get("answer", ""), context_plain, user_amts, gen.get("user_claim_verdict", "none"))
            if not problems:
                break
            log.warning("price guard rejected answer: %s", problems)
        if problems:
            return self._not_found(a, message, "guard_rejected", hits)

        if not gen.get("answerable", True) or not gen.get("answer"):
            return self._not_found(a, message, "not_in_content", hits)

        used = [sources[s] for s in gen.get("source_ids", []) if s in sources and sources[s]["url"] in ALLOWED_URLS]
        used = used or [hits[0]]
        seen, srcs = set(), []
        for h in used:
            if h["url"] not in seen:
                seen.add(h["url"])
                srcs.append({"title": h["title"], "url": h["url"], "section": h["section"]})

        medical = intent == "medical_advice" or gen.get("needs_medical_disclaimer")
        offer = bool(gen.get("offer_quote"))
        return self._result(gen["answer"], a, sources=srcs, cta=CTA if offer else None, show_lead_form=False,
                            disclaimer=self.localize("disclaimer", lang) if medical and not disclaimer_shown else None)
