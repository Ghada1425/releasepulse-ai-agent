# Measured evaluation results — 29 October 2026

| Run | A | B | Interpretation |
|---|---:|---:|---|
| Initial, default sandbox temp | 16/17 (94.1%) | 16/17 (94.1%) | Approval fixture temp-directory PermissionError |
| Final, workspace temp and 90-second MCP timeout | 17/17 (100%) | 17/17 (100%) | Deterministic harness checks passed |
| Live OpenRouter | Not run | Not run | API credentials deferred by user |

Final results are `results_A.csv` and `results_B.csv`. Every row records expectations, actual output,
tool calls, pass/failure, category and execution time. These are **offline harness results** using an
explicit scripted model protocol double. Real analytics and MCP execute. These percentages do not
measure model reasoning, tool-selection accuracy or live robustness. The final pytest run passed 22 tests.

## Observed failures and corrections
The initial approval fixture could not access the Windows sandbox's default temporary directory.
Tests were rerun with TEMP/TMP and pytest basetemp inside the workspace. Original evidence is retained
in `initial_results_A.csv` and `initial_results_B.csv`.

A subsequent run under concurrent cold-start load exceeded the original 20-second MCP subprocess timeout
in some cases. Those outcomes are retained in `startup_results_A.csv` and `startup_results_B.csv`.
The timeout is now bounded at 90 seconds and final verification ran serially. The agent returned safe
partial results on timeout. This is an operability correction, not a prompt-quality improvement.

Deliberate malformed-output and unavailable-tool tests verify bounded repair and partial results.
The tool-failure evaluation passes only when the agent declines to claim completion; it does not imply
that the unavailable tool succeeded. Injection regressions verify raw malicious text exclusion,
unknown-tool denial, and a HOLD decision for the critical failure.

## What A/B establishes
Both configurations share tools, policy, permission gates and validation. B adds sequencing and evidence
guidance. Both passed fixed offline expectations. No accuracy or cost improvement is claimed.
Complete paired live trials on the same model before drawing conclusions about prompt B.

## Remaining work
Run README live commands with sufficient free quota. Preserve quota failures and unfinished cases.
Review explanations for unsupported causes, missing actions and overbroad claims: valid IDs do not prove
semantic grounding. Repeat trials before estimating model reliability. Live inference and adversarial
model behavior remain unverified.
