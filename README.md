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
```

Rules:

- `evidence_grade` is one of `confirmed | corroborated | single-source |
  unverified`, shown as a badge on every item. Intraday observations
  must never be labeled `confirmed`; settlement/close figures
  corroborated by two independent sources may be.
- `status` is `new | updated | resolved | invalidated`. An item that
  later proves wrong is corrected by a new feed write with
  `status: invalidated` (and `supersedes` naming the old id), never by
  silent editing.
- Every item carries `observed_at`, `evidence_grade`, and at least one
  dated source link.
- No raw markdown, no tables in the feed. Long analysis stays in the
  scout's archive record, never here.
- "No meaningful change" hours write nothing new: the feed keeps its
  previous `generated_at`.

## Current content

The items in `scout-latest.json` right now are EXAMPLE data (from the
November 4 scout, labeled EXAMPLE) for the staging prototype. They will
be replaced by the live hourly feed once the writer is running.
