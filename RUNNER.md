# Tactical Scout scheduled runner

The public `scout-feed-v1` contract and website URL are unchanged. Only meaningful findings change `scout-latest.json`. Successful no-change research writes `.scout/heartbeat.json` separately.

## Activation

1. Add repository Actions secret `OPENAI_API_KEY` with Responses and live web-search access and funded API billing. A ChatGPT subscription is not an API credential.
2. Run **Tactical Scout → Run workflow → probe**. It must verify a heartbeat write/readback without changing the feed. The default Actions token is repository-scoped; no GitHub personal token is needed.
3. Pause the existing ChatGPT Scout task and verify it is disabled. Keep its instructions for rollback. Do not enable two publishers.
4. Set repository Actions variable `SCOUT_RUNNER_ENABLED` to `true`. This is the cutover gate. Optional `SCOUT_MODEL` overrides the default `gpt-6-astra`; the chosen model must support Responses web search and background execution.
5. Dispatch **research** during a due slot and inspect the verified result and heartbeat. Check two subsequent scheduled slots before closing the incident.

Runs are due every day at 9:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30 and 16:30 America/Detroit, including weekends, as in the original schedule. UTC wakeups cover both daylight and standard time. Frequent wakeups retry the latest due slot; successful slots are skipped. There are at most two research attempts per slot. Workflow concurrency serializes publishers. A delayed job after another hour starts researches the latest slot rather than falsely creating historical observations.

## Monitoring

The watchdog checks for an overdue completed-slot heartbeat after 20 minutes. Failures open one assigned GitHub issue, with a run link; successful research and readback close it with a recovery comment. GitHub notification email/push must be enabled and tested in the account; creating an issue does not prove delivery.

For detection of a complete GitHub Actions outage, configure an independent dead-man monitor (for example Healthchecks) for `30 9-16 * * *`, timezone America/Detroit, grace 20 minutes, and a verified alert recipient. Store its ping URL as Actions secret `SCOUT_HEALTHCHECK_URL`. The runner pings only after successful research and readback, including no-change runs. This external monitor must be configured and its missed-ping alert tested before claiming independent missed-run notification coverage. The repository watchdog shares GitHub's scheduler and cannot detect a total outage of that scheduler.

GitHub scheduled starts are best effort and may be delayed or dropped. Repeated triggers reduce single-trigger failures; this setup is not a promise of exact wall-clock execution. If a hard start-time SLA is required, use an external scheduler to dispatch this workflow and retain the same concurrency and completed-slot checks.

## Recovery and verification

- Missing key, incomplete output, empty text, missing web searches, incomplete sector coverage, malformed JSON, unreachable sources, or a concurrent feed edit fail closed and preserve the feed.
- Publishing atomically commits heartbeat and any new feed together, then reads main and compares every changed object. Non-fast-forward updates are rejected. Only `scout-latest.json` and `.scout/heartbeat.json` are allowed write targets.
- Probe success is marked separately and never represented as completed research.
- Tests: `python3 -m unittest discover -s tests -v`. Tests use fixtures and never publish simulated findings.
- Rollback: set `SCOUT_RUNNER_ENABLED=false`, wait for any active runner to finish, then re-enable the old task. Preserve the last good public feed. Do not run both publishers.
- Never paste API keys or monitoring URLs into issues, feed JSON, commits, or chat.
