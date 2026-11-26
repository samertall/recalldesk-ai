# ContextCon submission — verified live integration
**Project:** RecallDesk AI — Never Solve the Same Ticket Twice
**Track:** Challenge 02 — Agentic Support
**Pitch:** Support teams repeatedly diagnose issues because resolutions are trapped in individual sessions. RecallDesk coordinates triage, billing and technical support roles through one shared context layer, with verified learning and readable decision histories. The prototype contains 36 synthetic tickets, a reusable runbook, fixture-level approval, a baseline and a dashboard. The authenticated live Meko integration retrieves past context, saves fixture-approved fixes, records conversations and publishes evaluation artifacts. GitHub Actions run #4 passed with 24/24 repeated tickets retrieving shared memories. The optional model-backed experiment remains unvalidated.

## Demo outline (4:15)
0:00–0:35 — Problem and architecture.
0:35–1:20 — Show a new support ticket and its review-approved learning.
1:20–2:15 — Show another agent retrieving the same fix from the live datapack.
2:15–3:00 — Open Meko conversation trace and dashboard provenance.
3:00–3:50 — Compare measured baseline and live results; state limitations.
3:50–4:15 — Human approval, privacy, and future work.

No real customer data. Do not claim independent model accuracy, token savings, or production performance.

## Verified live Meko evaluation — 2026-11-26

GitHub Actions [run #4](https://github.com/samertall/recalldesk-ai/actions/runs/45819954272) completed successfully on commit `9a69382bb865ce34b9a1219ec0a7ac5f7686a694`. The authenticated MCP workflow processed all 36 synthetic support tickets, wrote fixture-approved memories, retrieved 24 verified repeat resolutions, logged conversations and stored an evaluation artifact. Both automated unit tests passed.

| Metric | Baseline | Live Meko |
|---|---:|---:|
| Tickets | 36 | 36 |
| Canonical fixture matches | 36 | 36 |
| Verified memory reuses | 0 | 24 of 24 repeat tickets |
| First-occurrence actions | 4 | 6 |
| Repeat-occurrence actions | 4 | 3 |
| Total logical actions | 144 | 144 |
| Mean first-occurrence latency (ms) | Not comparable | 1888.585 |
| Mean repeat-occurrence latency (ms) | Not comparable | 1193.770 |

The repeat-ticket action count is 25% lower than the baseline; total logical actions are unchanged. Mean repeat processing latency is 36.8% lower than first-occurrence latency **within the live Meko run**, excluding conversation logging. The baseline is a local deterministic fixture, not an equivalent network service. Fixture correctness is by construction, not independent model accuracy. No model token or cost savings were measured; the optional Gemini workflow was disabled. This evaluation does not establish production performance or independent cross-user access control.

Evidence: [successful workflow](https://github.com/samertall/recalldesk-ai/actions/runs/45819954272), [synthetic evaluation artifact](https://github.com/samertall/recalldesk-ai/actions/runs/45819954272/artifacts/15118520125) (subject to GitHub artifact retention).
