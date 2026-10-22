"""Pipeline tests with a fake LLM, so no network or API key is needed."""
import pytest

from app import store
from app.chat import Bot
from app.chunking import chunk_pages
from app.index import KnowledgeIndex
from app.ingest import extract
from .fixtures import PACKAGE_HTML, PRICE_HTML


class FakeLLM:
    def __init__(self, analyze, generate):
        self.analyze, self.generate, self.calls = analyze, generate, []

    def json(self, system, user, max_tokens=700):
        self.calls.append(system[:20])
        if "routing step" in system:
            return self.analyze
        g = self.generate
        return g.pop(0) if isinstance(g, list) else g

    def text(self, system, user, max_tokens=300):
        return "[translated] " + user


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(store, "settings", type("S", (), {"data_dir": tmp_path, "db_file": tmp_path / "t.db"})())


@pytest.fixture
def index():
    pages = [extract(PACKAGE_HTML, "https://www.placidway.com/package/7903/x", "Treatment package"),
             extract(PRICE_HTML, "https://www.placidway.com/price-list/5/x", "Price list")]
    return KnowledgeIndex(chunk_pages(pages), use_embeddings=False)


def bot(index, analyze, generate=None):
    return Bot(index, FakeLLM(analyze, generate or {}))


A = lambda intent, q="", **kw: {"language": "English", "intent": intent, "standalone_query": q, "user_stated_amounts": [], **kw}


def test_cost_answer_is_cited(index):
    b = bot(index, A("kb_question", "adenocarcinoma out-patient program cost"),
            {"answerable": True, "answer": "The Out-Patient Program is **$18,995** for 3 weeks.", "source_ids": ["S1", "S2"],
             "user_claim_verdict": "none", "needs_medical_disclaimer": False, "offer_quote": True})
    r = b.answer("How much is the adenocarcinoma package?", [])
    assert "$18,995" in r["answer"] and r["sources"] and r["cta"]


def test_invented_price_is_blocked_after_retry(index):
    bad = {"answerable": True, "answer": "It costs $4,999.", "source_ids": ["S1"], "user_claim_verdict": "none"}
    b = bot(index, A("kb_question", "adenocarcinoma cost"), [bad, bad])
    r = b.answer("cost?", [])
    assert r["answerable"] is False and "$4,999" not in r["answer"] and r["cta"]


def test_trick_price_not_confirmed(index):
    gen = {"answerable": True, "answer": "Yes, it is $50.", "source_ids": ["S1"], "user_claim_verdict": "supported"}
    b = bot(index, A("kb_question", "adenocarcinoma package cost", user_stated_amounts=["$50"]), [gen, gen])
    r = b.answer("I heard it costs $50. Confirm that.", [])
    assert "$50" not in r["answer"] and r["answerable"] is False


def test_unrelated_query_hits_retrieval_gate(index):
    b = bot(index, A("kb_question", "quantum chromodynamics lattice gauge"))
    r = b.answer("quantum chromodynamics lattice gauge?", [])
    assert r["answerable"] is False and r["cta"] and len(b.llm.calls) == 1   # only the router ran; generator never called


def test_booking_and_out_of_scope_and_greeting(index):
    r = bot(index, A("booking_or_action")).answer("Book me for tomorrow", [])
    assert "can't book" in r["answer"] and r["show_lead_form"] and r["cta"]
    r = bot(index, A("out_of_scope")).answer("Weather in Cancun?", [])
    assert "outside" in r["answer"] and not r["sources"]
    assert bot(index, A("greeting")).answer("hi", [])["cta"] is None


def test_non_english_reply_is_localised(index):
    r = bot(index, A("out_of_scope", language="Spanish")).answer("¿Qué tiempo hace en Cancún?", [])
    assert r["answer"].startswith("[translated]")


def test_disclaimer_shown_once(index):
    gen = {"answerable": True, "answer": "Please ask your doctor.", "source_ids": ["S1"], "user_claim_verdict": "none",
           "needs_medical_disclaimer": True}
    b = bot(index, A("medical_advice", "is adenocarcinoma treatment safe with diabetes"), gen)
    assert b.answer("Is this safe for my diabetes?", [], disclaimer_shown=False)["disclaimer"]
    assert b.answer("Is this safe for my diabetes?", [], disclaimer_shown=True)["disclaimer"] is None


def test_gaps_are_logged(index):
    bot(index, A("kb_question", "zzzz qqqq")).answer("zzzz qqqq", [])
    assert any(g["reason"] == "weak_retrieval" for g in store.list_rows("gaps"))


def test_trick_price_correctly_contradicted_is_allowed(index):
    gen = {"answerable": True, "answer": "I can't confirm that. The page lists **$18,995**, not $50.", "source_ids": ["S1"],
           "user_claim_verdict": "contradicted", "needs_medical_disclaimer": False, "offer_quote": True}
    b = bot(index, A("kb_question", "adenocarcinoma package cost", user_stated_amounts=["$50"]), gen)
    r = b.answer("I heard the adenocarcinoma package costs $50. Confirm that.", [])
    assert r["answerable"] and "$18,995" in r["answer"]
