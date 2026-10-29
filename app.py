import asyncio
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from releasepulse.agent import run_agent
from releasepulse.analytics import analyze_testing_report, calculate_quality_metrics, read_report
from releasepulse.llm import OpenRouter
from releasepulse.security import ReportStore

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="ReleasePulse · Quality intelligence", page_icon="◈", layout="wide")
st.markdown(
    """<style>
.stApp {background:#f4f7fa;color:#102b43}
[data-testid=stSidebar] {background:#102b43}
[data-testid=stSidebar] * {color:#e2edf3}
[data-testid=stSidebar] [role=combobox], [data-testid=stSidebar] input {color:#102b43}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid=stMetric] {background:white;border:1px solid #dce7ed;border-radius:12px;padding:18px}
.stButton>button[kind=primary] {background:#087f80;border:0}
.block-container {padding-top:4rem;max-width:1440px}
</style>""",
    unsafe_allow_html=True,
)
with st.sidebar:
    st.title("◈ ReleasePulse")
    st.caption("QUALITY & RELEASE INTELLIGENCE")
    page = st.radio(
        "Workspace",
        [
            "Overview",
            "Upload & Analysis",
            "Issues & Findings",
            "Agent Activity",
            "Evaluation",
            "Reports",
        ],
    )
    st.divider()
    st.caption("FICTIONAL PRODUCT · NOVA TRADE")
    config = st.selectbox("Agent configuration", ["B", "A"])
    st.caption("B · Enhanced harness\n\nA · Baseline instructions")
    st.divider()
    st.caption("Developed by Ghada Alaidi\n\nSDAIA Academy capstone")

st.caption("RELEASE WORKSPACE / NOVA TRADE / SYNTHETIC DATA")
st.title(page)
st.write("Make your next release decision with evidence.")

if "store" not in st.session_state:
    st.session_state.store = ReportStore(ROOT / "runtime" / "reports")
if page in {"Upload & Analysis", "Overview"}:
    col1, col2 = st.columns([2, 1])
    with col1:
        upload = st.file_uploader(
            "Upload a testing report",
            type=["csv", "xlsx"],
            help="Synthetic data only · 5 MB · exact sample column names",
        )
    with col2:
        sample = st.selectbox(
            "Synthetic sample",
            ["release_candidate.csv", "healthy.csv", "injection.csv", "release_candidate.xlsx"],
        )
        use_sample = st.button("Load sample", use_container_width=True)
    if upload is not None or use_sample:
        data = (
            upload.getvalue()
            if upload is not None
            else (ROOT / "data" / "samples" / sample).read_bytes()
        )
        name = upload.name if upload is not None else sample
        fingerprint = hashlib.sha256(data).hexdigest()
        if fingerprint != st.session_state.get("fingerprint"):
            try:
                rows = read_report(data, name)
                st.session_state.rows = rows
                st.session_state.fingerprint = fingerprint
                st.session_state.source = name
                for key in ["run", "proposal", "download"]:
                    st.session_state.pop(key, None)
                st.success(f"Validated {len(rows)} test executions")
            except Exception as exc:
                st.error(
                    f"Upload rejected: {type(exc).__name__}. Check columns, values, size and unique test IDs."
                )

rows = st.session_state.get("rows")
if rows is None and page != "Evaluation":
    st.info("Start with a synthetic sample or upload a QA report in Overview or Upload & Analysis.")
    st.stop()

if rows is not None:
    metrics = calculate_quality_metrics(rows)
    stats = analyze_testing_report(rows)
    st.caption(f"Source: {st.session_state.source} · Policy v1.0 · Calculated locally")

if page in {"Overview", "Upload & Analysis"}:
    columns = st.columns(4)
    for col, label, value in zip(
        columns,
        ["Test executions", "Pass rate", "Feature coverage", "Open issues"],
        [
            metrics["total"],
            f"{metrics['pass_rate']:.1%}",
            f"{metrics['coverage_rate']:.1%}",
            len(metrics["issues"]),
        ],
    ):
        col.metric(label, value)
    st.subheader("Explainable release decision")
    st.warning(metrics["decision"] + " · Deterministic policy assessment")
    st.write(
        f"{len(metrics['critical_test_ids'])} critical open tests and {len(metrics['critical_gaps'])} critical coverage gaps."
    )
    st.caption(
        "QA-01: Critical failures block release · QA-03: Critical coverage is mandatory · QA-04: All release gates must pass"
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Execution status")
        st.bar_chart(pd.Series(stats["statuses"], name="Tests"), color="#087f80")
    with right:
        st.subheader("Coverage gaps")
        st.dataframe(
            pd.DataFrame({"Missing executed feature / channel": metrics["coverage_gaps"]}),
            hide_index=True,
            use_container_width=True,
        )
    st.subheader("AI investigation")
    st.caption(
        "Sends bounded aggregates and test IDs to OpenRouter. Raw issue text stays local. No paid fallback."
    )
    if st.button("Run agent analysis", type="primary"):
        try:
            if "llm" not in st.session_state:
                st.session_state.llm = OpenRouter(max_requests=40, token_budget=200000)
            with st.spinner("Investigating evidence and retrieving QA policies over MCP…"):
                st.session_state.run = asyncio.run(run_agent(rows, st.session_state.llm, config))
            st.session_state.pop("proposal", None)
            st.session_state.pop("download", None)
        except ValueError as exc:
            st.error(str(exc))
    if "run" in st.session_state:
        run = st.session_state.run
        if run["status"] == "complete":
            st.success(run["assessment"]["summary"])
        else:
            st.error(run["error"])
    with st.expander("Validated source rows · untrusted descriptions"):
        st.dataframe(pd.DataFrame([r.model_dump() for r in rows]), hide_index=True)

elif page == "Issues & Findings":
    st.subheader("Prioritize remediation")
    issues = pd.DataFrame(metrics["issues"])
    if issues.empty:
        st.success("No failed or blocked tests in the supplied data.")
    else:
        issues["priority"] = issues.severity.map({"critical": 0, "high": 1, "medium": 2, "low": 3})
        st.dataframe(
            issues.sort_values("priority").drop(columns="priority"),
            hide_index=True,
            use_container_width=True,
        )
    st.metric("Repeated issue descriptions", metrics["duplicate_issue_groups"])
    findings = st.session_state.get("run", {}).get("assessment", {}).get("findings", [])
    for finding in findings:
        with st.expander(f"{finding['test_id']} · {finding['rule_id']}"):
            st.write(finding["explanation"])
            st.write("Recommended action: " + finding["action"])

elif page == "Agent Activity":
    run = st.session_state.get("run")
    if not run:
        st.info("Run an AI investigation to see actual tool activity.")
    else:
        for event in run["trace"]:
            with st.expander(f"Step {event['step'] + 1} · {event['tool']} · {event['status']}"):
                st.json(event)
        llm = st.session_state.get("llm")
        if llm:
            st.write(
                {
                    "requests": llm.requests,
                    "reported_tokens": llm.tokens,
                    "retries": llm.retries,
                    "estimated_cost_usd": llm.estimated_cost_usd,
                }
            )
    st.subheader("Approval audit · current session")
    st.json(st.session_state.store.audit)

elif page == "Evaluation":
    st.info(
        "Deterministic harness tests use a scripted model test double. They do not measure live LLM quality."
    )
    frames = []
    for label in ["A", "B"]:
        path = ROOT / "evals" / f"results_{label}.csv"
        if path.exists():
            frame = pd.read_csv(path)
            frames.append(frame)
    if frames:
        results = pd.concat(frames)
        st.bar_chart(results.groupby("config")["passed"].mean(), color="#087f80")
        st.dataframe(results, hide_index=True)
    else:
        st.info("Run the evaluation command in README to generate measured results.")
    st.caption(
        "Live A/B results are separate: evals/live_results_A.csv and live_results_B.csv. Not run without an API key."
    )
    for path in sorted((ROOT / "evals").glob("live_results_*.csv")):
        st.dataframe(pd.read_csv(path), hide_index=True)

elif page == "Reports":
    st.subheader("Review before export")
    report = {
        "source_sha256": st.session_state.fingerprint,
        "metrics": metrics,
        "agent": st.session_state.get("run", {"status": "not_run"}),
    }
    st.json(report)
    if st.button("Prepare this report for approval"):
        st.session_state.proposal = st.session_state.store.propose(report)
        st.session_state.pop("download", None)
    if "proposal" in st.session_state:
        st.info(
            "Approval saves the exact preview as JSON under runtime/reports. Rejection writes nothing."
        )
        approve, reject = st.columns(2)
        if approve.button("Approve & save", type="primary"):
            path = st.session_state.store.decide(st.session_state.pop("proposal"), True)
            st.session_state.download = path.read_bytes()
            st.success("Report saved. Approval recorded.")
        if reject.button("Reject"):
            st.session_state.store.decide(st.session_state.pop("proposal"), False)
            st.warning("Rejected. No report was written.")
    if "download" in st.session_state:
        st.download_button(
            "Download approved JSON",
            st.session_state.download,
            "releasepulse-report.json",
            "application/json",
        )
