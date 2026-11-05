# Market-Intell-Scout-Feed

Public live feed for the Market Intelligence Tactical Scout. The live
panel on marketinteloutlook.com fetches `scout-latest.json` from this
repo (raw.githubusercontent.com) when the page loads and every 15
minutes after that. No site rebuild is needed when new scout items land.

## What lives here

- `scout-latest.json` — the current feed. Latest scout items only
  (max 5). Rewritten after each hourly scout run.
- Nothing else belongs here. No private content, no internal notes, no
  subscriber or financial data. Scout items only, each with its sources.

## Feed contract — `scout-feed-v1`

```json
{
  "feed_version": "scout-feed-v1",
  "generated_at": "2026-11-04T16:10:00-05:00",
  "as_of_et": "4:10 PM ET",
  "items": [
    {
      "id": "scout-20261104-1610-momentum-rotation",
      "observed_at": "2026-11-04T16:10:00-05:00",
      "title": "Momentum stocks experience historic relative underperformance",
      "summary": "Short plain-English summary, 2–4 sentences, cap ~60 words.",
      "tickers": ["MTUM", "SMH"],
      "sectors": ["Semiconductors", "AI infrastructure"],
      "evidence_grade": "corroborated",
      "observations": [{"label": "S&P 500", "value": "Approximately +1.6%"}],
      "key_finding": "One line: the single most important finding.",
      "sources": [{"title": "Barron's", "url": "https://…"}],
      "status": "new",
      "supersedes": null
    }
  ]
}