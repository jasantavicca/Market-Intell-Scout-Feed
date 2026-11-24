# Tactical Scout — Shared Runbook (ChatGPT or Muse)

Purpose: one process, two possible operators. The feed file is the product;
who writes it is interchangeable. Written 2026-11-24 at Joseph's direction.

## Roles (standing)

- **Primary:** ChatGPT's scheduled automation runs the Scout hourly.
- **Automatic fallback (Joseph, 2026-11-24):** Muse does nothing while the
  automation is landing its files. If a slot is missed/unverified past the
  watchdog's 20-minute grace, Muse runs that slot AUTOMATICALLY — no call
  from Joseph needed (cron `scout-fallback`, hourly at ~:55 ET). Joseph is
  notified only when a fallback ran or something is broken. A manual push
  on Joseph's call remains available anytime.
- **Never both for the same slot.** Before writing, the operator reads the
  current feed: if `last_checked_at` already covers the slot being run,
  stand down — the other operator got there first.

## Schedule

- Daily (weekends included), hourly at :30, 09:30–16:30 America/Detroit
  (8 slots/day).
- Each slot: one research sweep, one feed write, one read-back verification.

## The feed contract (do not change without Joseph's approval)

- Repo: `jasantavicca/Market-Intell-Scout-Feed` (public), branch `main`.
- File: `scout-latest.json`, `feed_version: "scout-feed-v1"`.
- Top level: `feed_version`, `generated_at`, `as_of_et`, `items`,
  `last_checked_at`, `last_check_status`.
- Item fields: `id` (`scout-YYYYMMDD-HHMM-<slug>`), `observed_at`, `title`,
  `summary`, `tickers`, `sectors`, `evidence_grade`, `observations`
  (label/value pairs), `key_finding`, `sources`, `status`, `supersedes`.
- The site panel renders this file as-is; a schema change breaks the panel.

## Heartbeat rule (what the watchdog judges)

- EVERY run updates `last_checked_at` (ISO-8601 with ET offset) and
  `last_check_status` — `"new_findings"` or `"no_new_findings"` — and
  commits, even when the sweep found nothing. A quiet run is a completed
  check; the heartbeat fields are how anyone can prove it.
- `generated_at` / `as_of_et` move with the write.
- Items list carries the current findings set; a no-findings run leaves
  the items as they were and only the heartbeat changes.

## Research sweep (per slot)

- Scope: breaking moves in stocks, sectors, and commodities; market-moving
  news since the previous slot — leadership/governance shocks, M&A,
  regulatory/export-control actions, large premarket/intraday moves,
  commodity dislocations.
- Every item checked against at least two independent sources, primary
  source preferred (company announcement, official release, filing).
  Single-source items are graded accordingly, never upgraded silently.
- Evidence grades: use the grades already in the feed (`corroborated` is
  the standard for multi-source items); label premarket figures as
  premarket, never as closes.
- Separate reported fact from inference in the summary; flag what remains
  unresolved (investigations, pending responses, unverified scope).

## Write protocol

1. Read the current `scout-latest.json` on `main` (note its SHA and
   `last_checked_at`). If it already covers this slot, stop.
2. Run the sweep; build the new file content in full (schema above).
3. Commit to `main` with a message naming the slot and outcome, e.g.
   "Scout 2026-11-24 11:30 ET — new_findings (2 items)".
4. Read the file back from GitHub and verify: valid JSON, heartbeat
   fields equal this slot's run, items as intended. A write that cannot
   be read back is not done.
5. Report to Joseph in main chat only when: a manual push was called and
   completed, a write failed, or the read-back disagrees. Routine
   automated slots stay silent (the watchdog reports misses on its own).

## Manual push (Muse, on Joseph's call)

- Joseph's call names the slot(s) to cover — usually the missed slot(s)
  only, not the whole day.
- Muse runs the sweep for the current time (news is weighed as of now,
  not reconstructed for the missed hour), writes per the protocol, and
  confirms completion in main chat with the commit and read-back result.
- The watchdog closes its incident on the next verified check; Muse does
  not edit the watchdog's state or logs as part of a manual push.

## Boundaries

- Observation and publication only: the Scout never trades, never
  recommends, and its items carry evidence grades precisely because they
  are intraday and not the daily edition.
- No AI names in the feed content.
- Governance changes (schema, schedule, grades, this runbook) go through
  Joseph — proposal, his word, then land.
