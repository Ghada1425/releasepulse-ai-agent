# ReleasePulse — Final audit

**Project:** ReleasePulse — AI-Powered Product Quality & Release Intelligence Agent
**Author:** Ghada Alaidi · SDAIA Academy — Agentic AI Systems Engineering · Track 2 — Your Harness
**Audit date:** 29 October 2026 · **Repository:** https://github.com/Ghada1425/releasepulse-ai-agent
**Requirements source:** [capstone README](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md)
(minimum requirements 1–5, rubric 25/25/20/20/10, submission checklist), retrieved during this audit.

Status key: **PASS** = executed and observed in this audit · **BLOCKED** = cannot run without an
external dependency (originally the API key; now the upstream free-model rate limit) · **FAIL** = executed and did not meet the requirement.
Nothing marked PASS relies on a previous agent's claim.

## Environment and commits
Windows 11, CPython 3.14.6, uv 0.13.6, locked dependencies (`uv sync --frozen`). CI: GitHub Actions,
Ubuntu, Python 3.12.

| Commit | Content |
|---|---|
| `d58112c`, `8da80db` | Prior agent's published history (preserved unchanged) |
| `900cae7` | Upload-state fixes, live OpenRouter hardening, single-source MCP policy, eval graders/resume, tests |
| `b54da7f` | Regenerated offline A/B evidence; slide 7 test count |
| `67ed574` | README rewrite; error analysis, verification, security and demo-script updates |
| next commit | This audit (hash reported in the handover and visible in `git log`) |

`67ed574` was pushed and verified: local `HEAD` = `origin/main` = `67ed57493b86df59deab5eeb3e9d3addec78facb`.
GitHub Actions run 40837833566 on `67ed574`: **success** (ruff, format, pytest, offline evaluation).

## Executed checks
| Check | Command / procedure | Observed result | Status |
|---|---|---|---|
| Dependency install | `uv sync --frozen` (local and fresh clone) | Installed from lock, no resolution changes | PASS |
| Syntax/imports | `python -m compileall -q src app.py`; full pytest import | No errors | PASS |
| Lint | `uv run ruff check .` | All checks passed | PASS |
| Format | `uv run ruff format --check .` | 24 files already formatted | PASS |
| Test suite | `uv run pytest -q tests/test_system.py tests/test_ui.py` | **40 passed** (offline). Live test excluded to save free-tier quota; its run is under “Live run with key” | PASS |
| Offline A/B eval | `uv run python -m releasepulse.evaluation` | A 17/17, B 17/17 (`deterministic_harness`) | PASS |
| Live A/B eval | `uv run python -m releasepulse.evaluation --live` | `BLOCKED: Set OPENROUTER_API_KEY…`, exit 2, no files | BLOCKED |
| Live smoke | `uv run pytest tests/test_live.py -rs` | Superseded — see “Live run with key” below | BLOCKED |
| Streamlit start | headless on 127.0.0.1:8599, probe `/_stcore/health` and `/` | `ok` after 4 s; HTTP 200 | PASS |
| Clean clone | fresh `git clone` of `67ed574`, README commands only | ruff/format pass; 38 passed, 1 skipped; eval 34/34 | PASS |
| Secret scan | `git grep` + `git log -p --all` for key/token patterns; `.env`/`runtime/` tracking | No matches; neither tracked; `.gitignore` covers both | PASS |

## Minimum requirements
| # | Requirement | Implementation | Verification | Observed | Status |
|---|---|---|---|---|---|
| 1a | Multi-step agent, ≥3 tools | `src/releasepulse/agent.py` (4 tools, 8-step loop) | `test_multistep_injection_defense`, eval tasks 05–17 | Four tools executed in sequence; results returned as `tool` messages | PASS (scripted model) |
| 1b | ≥1 tool over MCP | `mcp_server.py`, `mcp_client.py` (stdio, FastMCP) | `test_real_mcp`, `test_mcp_knowledge_base_matches_maintained_policy` | Real subprocess initialize + call_tool; ranked rule IDs returned | PASS |
| 1c | Genuine model-driven tool calls | `llm.py` → OpenRouter `google/gemma-4-31b-it:free` | `tests/test_live.py`, live eval | Key valid; every request HTTP 429 upstream, 0 tokens | BLOCKED |
| 2a | Context file | `AGENTS.md`, `context/system-spec.md`, `context/qa-policy.md` | Review | Present and consistent with code | PASS |
| 2b | Memory/retrieval | `retrieval.py` parses `qa-policy.md`, served via MCP | Policy/MCP consistency test | Served excerpts equal the maintained table | PASS |
| 2c | Compaction/budget rule | 6,000-char tool cap, 18,000-char history compaction, request/token reservation | `test_free_model_and_budget`, `test_token_reservation_prevents_request` | Budget stops before any request | PASS |
| 3a | Permission policy, human approval for a write | `security.py` `ReportStore`; UI Reports page | `test_approval_rejection_tamper_and_replay`, `test_approve_writes_exact_previewed_report`, `test_dashboard_load_and_reject` | Reject writes nothing; approve writes exact previewed bytes; replay rejected | PASS |
| 3b | Step/cost budgets | 8 steps, 6 calls/step, 1 repair, request/token caps, `:free` + `max_price 0` | `test_bounded_repair`, `test_budget_exhaustion_is_reported_as_partial`, `test_rate_limits_count_every_attempt` | Bounded; typed `BudgetExhausted` | PASS |
| 4a | ≥15 tasks with automatic graders | `evals/tasks.jsonl` (17), `evaluation.py` | `test_eval_grades_agent_decision_not_policy_oracle` | Graders read agent decision, tools used, injection exclusion | PASS |
| 4b | Two configurations | A baseline / B enhanced prompt (`agent.py`) | Offline run | A 17/17, B 17/17 offline | PASS (offline) |
| 4c | Live run of both configurations | `--live`, resumable, quota-aware | — | Awaiting key | BLOCKED |
| 4d | Error analysis | `evals/error_analysis.md` | Review | Historical failures retained; grader defects documented | PASS |
| 5 | Security note: trifecta, attack, defence | `docs/security.md`, `data/samples/injection.csv` | `test_multistep_injection_defense`, `test_unauthorized_tool_denied`, `test_untrusted_final_decision_cannot_override_policy` | Raw payload absent from model messages; `save_report` rejected; HOLD kept | PASS (code-level); live red-team BLOCKED |

## Rubric
| Criterion (weight) | Evidence | Status | Remaining |
|---|---|---|---|
| Working system and live demo (25%) | App starts; upload → metrics → issues → approval verified by AppTest and HTTP probe; agent path verified with scripted model | PASS for deterministic flow · **BLOCKED** for live Gemma demo | Configure key; rehearse live demo; record backup |
| Context and harness engineering (25%) | Spec files, single-source MCP policy, compaction, budgets, allowlist, typed retries, grounding validator | PASS | — |
| Evaluation and error analysis (20%) | 17 tasks × A/B, automatic graders, failure categories, resumable runner, error analysis | PASS offline · **BLOCKED** live | Run live A/B; analyse real failure categories; update error analysis |
| Security, governance and operability (20%) | Trifecta analysis, injection test, tool allowlist, byte-bound approval, validated uploads, no secrets in logs, CI | PASS | Live adversarial check after key |
| Presentation and reproducibility (10%) | README, demo script, 8-slide deck consistent with code (slide 7 count updated), clean-clone run, CI green | PASS | Record demo backup once live |

## UI verification (AppTest, `tests/test_ui.py`)
| Behaviour | Before this audit | Now |
|---|---|---|
| Load sample after uploading a file | Sample ignored; upload kept winning | Sample loads and stays loaded on later reruns |
| Upload rejected after a valid report | Previous report stayed on screen | Previous data, agent run and proposals cleared |
| Rejection message | Exception class only (`ValidationError`) | Row number and field, value not echoed |
| Decision banner | Yellow warning for every decision | READY green, REVIEW amber, HOLD red |
| Run agent without key | Configuration error | Unchanged, now regression-tested |

## Live run with key (29 Oct 2026)
The owner configured `.env`; the key was never printed or committed.

| Probe | Observed |
|---|---|
| `GET /api/v1/key` | 200; free tier, usage 0 |
| `GET /models/google/gemma-4-31b-it:free/endpoints` | One endpoint, Google AI Studio, lists `tools` |
| Owner's run of `tests/test_live.py` (before fix) | `partial`, 3 requests, 0 tokens; no retrieval in trace |
| Single raw request with one tool | HTTP 429 `limit_source: upstream_provider_shared_pool`, provider Google AI Studio |
| `tests/test_live.py` after fix (15 s + 30 s backoff) | FAILED: 3 × `rate_limited_upstream` 429, 0 tokens, trace `[llm: error]` |
| Single raw request about 5 minutes later | HTTP 429, same metadata, no `Retry-After` header |

**Root cause:** Google AI Studio's shared free pool for this model throttled every request upstream. The
old client retried after 1 s and 2 s and kept only `ProviderUnavailable`, so the failure looked like an
agent/tool problem. Failed responses carry no usage, hence 0 tokens: **no inference took place**.
Tool-call parsing, MCP retrieval and output validation were never reached on the live path, so they are
neither confirmed nor refuted live. They still pass with the scripted model.

**Fix:** `diagnose()` classifies each failed attempt (key-free: category, status, provider,
`limit_source`), keeps it in `OpenRouter.errors` and logs it. 429 waits for `Retry-After` or 15 s/30 s
(capped at 60 s). Non-retryable statuses (401/402/404/400) fail at once with their category. The agent
trace and partial-result message include the category. Unit tests:
`test_upstream_rate_limit_is_categorized_and_waits`, `test_non_retryable_status_is_recorded_without_retry`.

**Blocker:** external and not something code can fix. The model was not swapped. Owner options: retry
later; add a free Google AI Studio key under OpenRouter → Settings → Integrations (BYOK, same model);
or approve a different model.

## Live-path hardening (unit-tested, not live-verified)
5xx and empty OpenRouter responses are retried within budget; fenced ```json final answers are
unwrapped; failures surface as `BudgetExhausted` / `ProviderUnavailable` class names only. Whether
`google/gemma-4-31b-it:free` supports function calling reliably on OpenRouter's free tier is **unverified**.
If it does not, the agent returns a partial result; the model must not be swapped without the owner's decision.

## Remaining work (blocked on upstream free-model availability)
1. ~~Add `OPENROUTER_API_KEY` to `.env`~~ — done; key valid.
2. `uv run pytest tests/test_live.py -s -rs` once the 429s clear; it must pass before step 3.
3. `uv run python -m releasepulse.evaluation --live --max-requests 40`, then repeat with `--resume`
   until both `evals/live_results_A.csv` and `evals/live_results_B.csv` hold 17 rows.
4. Update `evals/error_analysis.md` and README results with the real A/B numbers and failure categories.
5. Run the demo once live, record a backup, and refresh `docs/screenshots/overview.png`.
6. Commit the live CSVs and docs (never `.env`) and push.
