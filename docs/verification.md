# Verification record — 29 October 2026

## Environment
Windows; CPython 3.12.16; locked dependencies in uv.lock. A fresh second virtual environment was
installed with `uv sync --frozen` and passed a deterministic READY-policy smoke check.

## Evidence and scope
- CSV/XLSX parsing, exact schema, size limits and policy arithmetic have regression coverage.
- Actual MCP initialize + call_tool communication was exercised against a Python subprocess.
- Scripted model protocol tests execute multiple real tools; they are not live model inference.
- Approval binding, rejection, token replay and mutation after proposal are regression-tested.
- Unknown write tools are rejected; raw injected descriptions are absent from model messages.
- Streamlit AppTest covers sample loading, computed metrics, navigation and rejection.
- The app launched at localhost:8501 and was visually inspected. Real screenshot: docs/screenshots/overview.png.
- Ruff formatting and lint checks passed. Final pytest: 22 passed. Final offline A/B: 17/17 each.
- Browser verification confirmed rejection wrote nothing, then approval saved the exact JSON and exposed its download.
- Public OpenRouter catalog contained the requested model with zero pricing; no inference request was made.
- GitHub CLI initially reported invalid authentication; the repository was later published at
  https://github.com/Ghada1425/releasepulse-ai-agent (commit 8da80db) and verified against the remote.

## Environment errors and corrections
The default sandbox temporary directory denied file operations. Tests were rerun with TEMP/TMP and
pytest basetemp inside the workspace. The first complete A/B run retained 16/17 passes for each config,
with an approval-fixture PermissionError. See initial_results_A/B.csv.
Concurrent cold-start processes then exceeded the MCP startup timeout in some cases. Those results are
retained in startup_results_A/B.csv. The bounded timeout was raised from 20 to 90 seconds and verification
was repeated serially. Partial results on timeout remained safe; no report writes occurred.

## Presentation validation
All eight slides were rendered and visually inspected. Package, layout/font and first-party import checks
passed before the finalizer's hard-link publication step hit Windows EPERM. The validated candidate was
copied byte-for-byte into slides/ReleasePulse-capstone.pptx and matching SHA-256 hashes were checked.
This is not a claim of testing in Microsoft PowerPoint itself.

## Handover verification — 29 October 2026 (later session)
Environment: Windows 11, CPython 3.14.6, uv 0.13.6, `uv sync --frozen` from the committed lock.
The working folder was a ZIP snapshot without `.git`; the published history (d58112c, 8da80db) was
attached unchanged and work continued on `main`.
- `uv run ruff check .` and `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 38 passed, 1 skipped (`tests/test_live.py`, BLOCKED — Awaiting API Key).
- `uv run python -m releasepulse.evaluation`: A 17/17, B 17/17 (`deterministic_harness`).
- `uv run python -m releasepulse.evaluation --live`: printed BLOCKED, exit 2, no files written.
- Streamlit headless start on 127.0.0.1: `/_stcore/health` returned `ok` in 4 s; `/` returned HTTP 200.
- Defects found and fixed with regression tests: sample button ignored once a file was uploaded; a
  rejected upload left the previous report on screen; upload errors showed only an exception class;
  READY/HOLD shared one warning colour; 5xx/empty OpenRouter responses were not retried; fenced JSON
  final answers always failed validation; the MCP knowledge base duplicated and drifted from
  `context/qa-policy.md`; eval graders did not read the agent's decision or grade injection exclusion;
  the eval runner was not resumable and crashed without a key.
Commit hashes and per-requirement status: [FINAL_AUDIT.md](FINAL_AUDIT.md).

## Still pending
Actual OpenRouter inference; complete live A/B suite; live attack/demo recording. All are BLOCKED on
the project owner's OpenRouter API key, are necessary for full capstone acceptance and are not marked
complete. See README commands. Do not present offline pass rates as live model accuracy.
