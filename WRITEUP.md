# Write-up

## What I would improve with another week

- Build a bigger test set (50 to 100 questions with the expected facts) and run it on every change. I only have 14 questions now, and the relevance thresholds (`MIN_DENSE_SIM`, `MIN_COVERAGE`) should be tuned against a proper set.
- Parse the price tables into records (clinic, procedure, tier, amount, inclusions) and answer cost questions from those. Comparisons would be exact, and I could safely allow totals.
- Add a reranker on the top results, and stream the answer so it appears faster.
- Alert when a page changes, keep leads and the gap log on persistent storage, and add a small admin page to review them.
- Use a multilingual embedding model instead of translating every question to English first.

## Known limitations

- The bot never adds up prices. The price check only confirms a number exists in the retrieved text, so a calculated total can't be verified.
- That same check can't tell whether a number belongs to the right treatment. That depends on the prompt and on chunks carrying their page title and section.
- The source pages have quirks. The price list has a row with a price but no procedure name, so I skip it. The comparison page mixes different clinics and procedures, so any Turkey versus Mexico comparison only applies to the clinics named.
- The pages describe alternative cancer treatments in promotional language. The bot repeats what they say and attributes it to the page, and it does not judge if a treatment is safe or suitable for a person.
- Answers in less common languages may be less polished.
- The LLM free tier has rate limits, and free hosting can sleep when idle.
- If the site blocks the host's IP during a refresh, the bot keeps the last snapshot and shows the failure in `/api/status`.
- Leads are saved in SQLite, which can reset on free hosting. Set `LEAD_WEBHOOK_URL` for anything beyond a demo.
