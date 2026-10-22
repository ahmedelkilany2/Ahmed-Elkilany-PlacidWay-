# PlacidWay Website Knowledge Chatbot

A chatbot that answers visitor questions using only the 7 PlacidWay pages from the assessment. Every answer links to the page it came from, and if the answer isn't on those pages the bot says so instead of guessing.

Live link: `<add deployed URL>`
Test answers: `TEST_RESULTS.md`
Limitations and next steps: `WRITEUP.md`

## How it works

1. **Ingestion** (`app/ingest.py`): downloads only the 7 URLs listed in `app/sources.py`. It checks robots.txt, uses a clear User-Agent with a contact email, and waits about a second between requests.
2. **Cleaning**: most of each page is menus, footers and cards for other clinics, so I keep only the main article. This matters because package pages end with other clinics' prices, and I didn't want the bot quoting those for ITC. Table rows are turned into single lines like `Procedure: Breast Cancer; Price in USD: $18995`.
3. **Chunking** (`app/chunking.py`): pages are split by heading, and each chunk starts with the page title and section name.
4. **Search** (`app/index.py`): BM25 for exact words (prices, names) plus embeddings for meaning, merged with reciprocal rank fusion.
5. **Router**: one LLM call works out the language, the intent (question, medical advice, booking, quote, out of scope, greeting) and rewrites the question as a standalone English query. This is what makes follow-ups like "what about Turkey?" and non-English questions work.
6. **Answer** (`app/chat.py`): the model gets the top chunks as numbered sources and must return JSON saying which sources it used. If nothing relevant is found, the LLM isn't called at all and the bot gives the "not found" message with a link to the free quote form.
7. **Price check** (`app/guard.py`): every dollar amount in the answer must appear in the retrieved text. If not, the answer is regenerated once, and then replaced by "not found". If the user quotes a price that isn't in the content, the bot can correct it but can't confirm it.

## Requirements checklist

| Requirement | Where |
|---|---|
| Ingestion from the shared URLs | `app/ingest.py` |
| Knowledge base / retrieval | `app/chunking.py`, `app/index.py` |
| Grounded answers with source links | `app/chat.py`, UI shows sources |
| Honest "I don't know" | relevance check + `answerable` flag |
| Prices with currency and context | answer prompt + `app/guard.py` |
| Chat UI | `static/index.html` |
| Refresh | `python -m app.ingest`, `POST /api/admin/refresh`, daily auto refresh |
| Live deployment | `Dockerfile`, `render.yaml` |
| Answers in the user's language | router detects it, answer written in it |
| Follow-up questions | last few turns are sent with each request |
| Disclaimer (once) | shown when relevant, not repeated in the same chat |
| Lead capture | form with consent box, saved to SQLite, optional webhook |
| Log of unanswered questions | `GET /api/admin/gaps` |

## Tools and why

- Python and FastAPI: small and easy to test.
- Llama 3.3 70B on Groq: free tier, fast, supports JSON output. The client uses the OpenAI-style API, so `LLM_BASE_URL` and `LLM_MODEL` can point to another provider.
- `BAAI/bge-small-en-v1.5` through fastembed: runs on CPU, no API cost. If it can't load, the bot falls back to BM25 only.
- `rank-bm25`, SQLite, plain JavaScript for the UI.
- No LangChain or similar. The pipeline is short and I wanted every step visible.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # (Windows: copy .env.example .env) fill in LLM_API_KEY, CRAWLER_CONTACT, ADMIN_TOKEN

python -m app.ingest            # crawl the pages into data/pages.json
uvicorn app.main:app --reload   # open http://localhost:8000
python -m eval.run_eval         # answers the test questions, writes TEST_RESULTS.md
pytest -q                       # offline tests, no API key needed
```

Commit `data/pages.json`. The app loads it at startup, so it still works if the host gets blocked while crawling.

## Deploy

On Render: push to GitHub, create a Blueprint from the repo (`render.yaml` is included), and set `LLM_API_KEY` and `CRAWLER_CONTACT`. The free plan sleeps when idle, so I point a free uptime monitor at `/health`. The same Dockerfile works on Hugging Face Spaces or Fly.io.

## Refreshing and admin

```bash
curl -X POST $URL/api/admin/refresh -H "X-Admin-Token: $ADMIN_TOKEN"
curl $URL/api/admin/gaps  -H "X-Admin-Token: $ADMIN_TOKEN"
curl $URL/api/admin/leads -H "X-Admin-Token: $ADMIN_TOKEN"
curl $URL/api/status
```

Refresh compares content hashes and reports which pages changed. If a page fails to download, the previous copy is kept.

## Tests

`pytest` covers the page cleaning, the price check, the full answer flow with a fake LLM (invented price, trick price, out-of-scope, booking, disclaimer shown once, gap logging) and the API endpoints.
