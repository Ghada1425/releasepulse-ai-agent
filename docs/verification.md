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
- GitHub authentication was subsequently renewed and the repository published at https://github.com/Ghada1425/releasepulse-ai-agent. The remote commit was verified against the local commit.

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

## Still pending
Actual OpenRouter inference; complete live A/B suite; live attack/demo recording.
These are necessary for full capstone acceptance and are not marked
complete. See README commands. Do not present offline pass rates as live model accuracy.
