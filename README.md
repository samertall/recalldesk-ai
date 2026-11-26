# RecallDesk AI
ContextCon 2026 · Challenge 02, Agentic Support: Never Solve It Twice.

A deterministic proof of concept for shared, validated support resolutions. Three ticket-handling agent identities use one Meko datapack; a specialist-review role records a fixture-approved solution. A subsequent agent searches and reuses the verified result. The prototype uses synthetic tickets and does not take real support actions.

## Run locally (Python 3.10+)

```
python app.py baseline
python app.py local
python app.py serve
```
Open http://127.0.0.1:8080. No packages or credentials required for local simulation. Local mode is an in-memory stand-in, not Meko.

## Run with Meko Cloud
1. Sign up at https://cloud.mekodata.ai/signup, create a dedicated datapack (RecallDesk), and copy its ID. In Settings > API Keys generate a key.
2. Upload `data/runbook.json` to the datapack knowledge base in the portal and wait until indexed.
3. Install the MCP client in a virtual environment: `python -m pip install -r requirements.txt`.
4. Set credentials in your shell (never commit them). PowerShell example:

```powershell
$env:MEKO_API_KEY = 'your-key'
$env:MEKO_DATAPACK_ID = 'your-datapack-id'
python app.py meko
python app.py serve
```

In Bash, use `export MEKO_API_KEY=...` and `export MEKO_DATAPACK_ID=...`. Select Live Meko results in the dashboard. The adapter uses the documented streamable HTTP endpoint, bearer authorization and user-agent header. It discovers available tools and uses context_search when exposed, otherwise documented memory_search; it calls memory_add, conversation_create, conversation_add_message and artifact_put. It intentionally fails on service errors rather than silently substituting local data. Use a dedicated test datapack. Same-account agent namespaces are used; cross-user permissions and memory promotion are not implemented. The fixture marker scopes each experiment, so old experiments cannot inflate reuse results. Inspect raw Meko portal traces for verification. Live adapter is untested against an authenticated server; tool response schemas may require adjustment. The optional Gemini model workflow is also included, but not tested against a live model API.

## Architecture
Ticket fixture → agent identity → Meko context search → verified memory match OR runbook lookup → fixture oracle → memory write → response → conversation / artifact logging. The local canonical runbook is an explicit validation oracle, not learned model behavior. Only synthetic approved solutions are persisted. The app does not execute retrieved instructions.

## Evaluation
36 tickets: 12 issue codes repeated in three cycles. Ticket labels are preassigned. Baseline uses four logical actions per ticket. Local simulation uses six on first occurrence and three for repeats; 24 repeated tickets reuse memory. Both match all 36 canonical fixtures by construction, not a real accuracy measure. Overall action count is equal at 144; repeats use 25% fewer actions than baseline (3 versus 4). Local latency is implementation overhead only, not a meaningful service benchmark. No token or cost claims. Live results must be generated separately. To meet the competition's stronger expectations, run the included optional model-backed workflow, add independent human review, and verify portal retrievals and artifacts.

## Submission
- Public GitHub repository with setup instructions.
- Recorded demo under five minutes, using live Meko (not the simulation alone).
- Optional documentation and measured results.
- Deadline Jan 17, 2027, 11:59 PM Pacific Time.

Docs: https://docs.mekodata.ai/reference/mcp-server/ and https://docs.mekodata.ai/use-meko/api-keys/.

## Optional model-backed experiment
Set `USE_GEMINI=1`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL` (choose an available Gemini model). For both baseline and Meko modes, the model receives only the ticket text and category catalog for classification. On a memory miss, it extracts the exact runbook resolution. The fixture oracle blocks incorrect proposals from memory and counts them as failures. A memory hit avoids the resolution model call. Token counts come from Gemini response usage metadata. This is a constrained retrieval/extraction experiment, not open-ended troubleshooting. Free quota and model availability depend on your account. Both live integrations still require validation.

```powershell
$env:USE_GEMINI = '1'
$env:GEMINI_API_KEY = 'your-key'
python app.py baseline
python app.py meko
```
