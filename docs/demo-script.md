# Eight-minute presentation and demo

Before starting: `uv sync --frozen`; configure `.env`; launch Streamlit. Run a small live task beforehand
and verify provider quota. If no key/quota is available, explicitly announce a deterministic-only demo.
Never call the scripted evaluation a live AI demonstration.

**0:00–1:00 — Problem and users.** QA leads need release evidence across features and channels. A high
pass rate alone cannot justify release. Introduce fictional Nova Trade and synthetic data.

**1:00–2:00 — Evidence.** Load the release-candidate sample. Point out 18 tests, 88.9% pass rate,
full execution coverage, and HOLD caused by the critical login failure. Show source QA-000.
Click Run agent analysis only with credentials (without a key the UI shows a configuration error). Show MCP retrieval and the observable tool timeline.

**2:00–3:00 — Human control.** Open Reports, prepare the exact JSON, reject it, then prepare again and
approve. Show the download and approval audit. Explain that the model has no save tool or approval token.

**3:00–4:00 — Architecture.** Walk through UI → agent → deterministic tools/MCP → output validation.
Explain why a lightweight loop is sufficient and why numerical calculations are outside the LLM.

**4:00–5:00 — Context and harness.** Show context spec, four retrieved rules, bounded result/history sizes,
eight steps, two output attempts and request/token reservations. Explain partial results on failure.

**5:00–6:00 — Evaluation.** Open Evaluation. State the displayed mode. Explain 17 cases × two prompts,
automatic expectations, real tools and MCP. Offline runs assess controls, not LLM reasoning.
If live results are available later, compare those separately, including failed or unfinished cases.

**6:00–7:00 — Error analysis.** Show tool-failure partial results and malformed-output regression tests.
Discuss the temp-directory environment failure and verified rerun. State that better prompt B is a
hypothesis until paired live trials establish it. Do not claim a model-accuracy percentage from mocks.

**7:00–8:00 — Security.** Load injection.csv and show the malicious description. Explain the lethal
trifecta, exclusion of raw text, tool allowlist, fixed API destination and immutable approval proposal.
Show the attack regression result and the live `14_injection` pass on `cohere/north-mini-code:free`.

Fallback: use the actual dashboard screenshots, policy calculations and recorded local test results.
They are not a substitute for a live run. Record a live backup with `cohere/north-mini-code:free`
before presentation day; the free tier allows 50 requests/day and one agent run uses about 5.
