# Market-Intell-Scout-Feed

Public live feed for the Market Intelligence Tactical Scout. The live
panel on marketinteloutlook.com fetches `scout-latest.json` from this
repo (raw.githubusercontent.com) when the page loads and every 15
minutes after that. No site rebuild is needed when new scout items land.

## What lives here

- `scout-latest.json` — the current feed. Latest scout items only
  (max 5). A successful completed research run updates check metadata, even when findings are unchanged.
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
- Successful research always updates `last_checked_at` (ISO 8601 with America/Detroit offset) and `last_check_status` (`new_findings` or `no_new_findings`). No-change runs preserve `items`, `generated_at`, and `as_of_et` exactly. These fields record research completion, not browser fetches, connection probes, starts, failures, or the time of a later metadata repair. Verify the GitHub write by readback; failed delivery must fail the heartbeat.
- `generated_at` and `as_of_et` describe the latest published findings; `last_checked_at` describes the last successfully completed research pass. Missing check metadata means unknown, never infer it from findings or a probe.

## Check metadata migration\n\nThe initial `last_checked_at` of `2026-11-08T13:33-05:00` comes from the documented November 8 1:33 PM ET completed Scout pass with no new findings. It does not claim that research was rerun when this metadata was added. Existing findings and publication timestamps are preserved.\n