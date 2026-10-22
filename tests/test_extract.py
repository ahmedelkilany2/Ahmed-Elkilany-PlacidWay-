from app.chunking import chunk_page
from app.ingest import extract
from .fixtures import PACKAGE_HTML, PRICE_HTML


def page():
    return extract(PACKAGE_HTML, "https://x/p", "Treatment package")


def test_boilerplate_and_other_clinics_dropped():
    t = page()["text"]
    assert "Limphocare" not in t and "33,400" not in t       # another clinic's price must not leak in
    assert "Experiences" not in t and "Dental Implants" not in t
    assert "Request your Free Quote" not in t


def test_main_content_and_facts_kept():
    t = page()["text"]
    assert t.startswith("# Alternative Adenocarcinoma")
    assert "Listed price (page metadata): 18995 USD" in t
    assert "Out-Patient Program; Duration: 3 Weeks" in t.replace("Program Type: ", "") or "Program Type: Out-Patient Program" in t
    assert "In-Patient Program" in t and "$30,000" in t
    assert "About Package" in t and "Padre Kino" in t


def test_tables_become_self_describing_rows_and_junk_rows_vanish():
    t = extract(PRICE_HTML, "https://x/price", "Price list")["text"]
    assert "Procedure: Breast Cancer; Price in USD: $18995" in t      # duplicate 'Details' collapsed, 'Actions' dropped
    assert "Chat with Center" not in t
    assert t.count("$18995") == 2                                      # the nameless row was discarded


def test_chunks_carry_context():
    chunks = chunk_page(page(), 0)
    assert chunks and all(c["title"] in c["index_text"] for c in chunks)
    cost = next(c for c in chunks if "In-Patient Program" in c["text"] and "$30,000" in c["text"])
    assert "Out-Patient" in cost["text"]                                # both tiers stay together
