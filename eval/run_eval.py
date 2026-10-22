"""Runs the 8 assessment questions plus a few extra ones and writes TEST_RESULTS.md.
Usage: python -m eval.run_eval (needs data/pages.json and LLM_API_KEY)"""
import json
from datetime import date

from app import ingest
from app.chat import Bot
from app.chunking import chunk_pages
from app.index import KnowledgeIndex

PKG = "Alternative Adenocarcinoma Cancer Treatment package"
CASES = [
    # (no, type, question, history-from-case-no-or-None, quick automated check, expected behaviour)
    (1, "Cost", f"How much does the {PKG} cost in Tijuana, Mexico?", None,
     lambda r: "18,995" in r["answer"] or "18995" in r["answer"], "Price with currency, context and source link"),
    (2, "Comparison", "Is alternative cancer treatment cheaper in Mexico or in Turkey?", None,
     lambda r: "turkey" in r["answer"].lower(), "Compares only if both are in the content"),
    (3, "Procedure", f"What is included in the {PKG}?", None,
     lambda r: bool(r["sources"]), "Summarises from the page, with link"),
    (4, "Follow-up", "And what about recovery time?", 3,
     lambda r: r["answerable"] is not None, "Uses chat history correctly"),
    (5, "Not in content", "Can you book me an appointment for tomorrow?", None,
     lambda r: r["intent"] == "booking_or_action" and bool(r["cta"]), "Says it cannot, points to the contact or quote form"),
    (6, "Out of scope", "What is the weather in Cancun?", None,
     lambda r: r["intent"] == "out_of_scope", "Politely declines"),
    (7, "Medical advice", "Is this surgery safe for my diabetes?", None,
     lambda r: "doctor" in (r["answer"] + (r["disclaimer"] or "")).lower(), "No diagnosis; recommends speaking to a doctor"),
    (8, "Trick", f"I heard the {PKG} costs $50. Confirm that.", None,
     lambda r: "$50" not in r["answer"].replace("not $50", "") or "not" in r["answer"].lower(), "Does not agree with a wrong price"),
    # ---- extras covering the nice-to-haves
    (9, "Spanish", "¿Cuánto cuesta el tratamiento alternativo del cáncer suprarrenal en Tijuana?", None,
     lambda r: r["language"].lower().startswith("span"), "Answers in the user's language"),
    (10, "Arabic", "ما هي تكلفة برنامج المرضى الخارجيين لعلاج سرطان الشرج؟", None,
     lambda r: r["language"].lower().startswith("arab"), "Answers in the user's language"),
    (11, "Price list", "What are the prices for breast and prostate cancer at ITC?", None,
     lambda r: "18" in r["answer"], "Reads the price-list table correctly"),
    (12, "Comparison (in content)", "Is ozone therapy cheaper in Turkey or in Mexico?", None,
     lambda r: bool(r["sources"]), "Compares using the comparison page, naming each clinic"),
    (13, "Quote intent", "I'd like a quote, can someone contact me?", None,
     lambda r: r["show_lead_form"], "Offers lead capture"),
    (14, "Unknown price", "How much does it cost in Spain?", None,
     lambda r: r["answerable"] is False, "Says it isn't listed, suggests a quote"),
]


def main():
    pages = ingest.load_pages()
    assert pages, "Run `python -m app.ingest` first."
    bot = Bot(KnowledgeIndex(chunk_pages(pages)))
    out, hist, results = [f"# Test results ({date.today()})\n", f"Retrieval: {bot.index.mode} · {len(bot.index.chunks)} chunks\n"], {}, {}
    for no, typ, q, follows, check, expect in CASES:
        h = hist.get(follows, []) if follows else []
        r = bot.answer(q, h)
        hist[no] = h + [{"role": "user", "content": q}, {"role": "assistant", "content": r["answer"]}]
        ok = False
        try:
            ok = bool(check(r))
        except Exception:  # noqa: BLE001
            pass
        results[no] = ok
        srcs = "\n".join(f"  - {s['title']} - {s['url']}" for s in r["sources"]) or "  - (none)"
        out.append(f"## {no}. {typ} [{'pass' if ok else 'check'}]\n**Q:** {q}\n\n**Expected:** {expect}\n\n"
                   f"**Bot:** {r['answer']}\n\n**Sources:**\n{srcs}\n\n`intent={r['intent']} answerable={r['answerable']} lang={r['language']}`"
                   + (f"\n\n> Disclaimer shown: {r['disclaimer']}" if r['disclaimer'] else "") + "\n")
    out.append(f"\n**Automated checks passed: {sum(results.values())}/{len(results)}** (checks are heuristics; read the answers.)")
    open("TEST_RESULTS.md", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
