"""Run reproducible offline harness checks or separately labelled live evaluations."""

import argparse
import asyncio
import io
import json
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from releasepulse.agent import run_agent
from releasepulse.analytics import calculate_quality_metrics, read_report
from releasepulse.fixtures import ScriptedLLM, scenario
from releasepulse.llm import OpenRouter
from releasepulse.security import ReportStore

ROOT = Path(__file__).resolve().parents[2]


class Recorder:
    """Records exactly what crosses the model boundary, for scripted and live clients."""

    def __init__(self, llm):
        self.llm, self.messages_seen = llm, []

    def complete(self, messages, tools):
        self.messages_seen.append(json.dumps(messages))
        return self.llm.complete(messages, tools)


QUOTA_ERRORS = {
    "BudgetExhausted": "budget_exhausted",
    "ProviderUnavailable": "provider_unavailable",
}


def categorize(trace: list[dict]) -> str:
    errors = [e for e in trace if e["status"] == "error"]
    for event in errors:
        if event["tool"] == "llm":
            return QUOTA_ERRORS.get(event.get("error"), "llm_error")
    if any(e["tool"] == "retrieve_qa_guidelines" for e in errors):
        return "tool_execution"
    if any(e["tool"] == "unauthorized_tool" for e in errors):
        return "unauthorized_tool_request"
    if any(e["tool"] == "output_validation" for e in errors):
        return "invalid_or_ungrounded_output"
    return "expectation_mismatch"


async def evaluate(task: dict, config: str, llm=None) -> dict:
    start = time.monotonic()
    rows = scenario(task["scenario"])
    mode = "live" if llm else "deterministic_harness"
    trace = []
    actual = {}
    try:
        if task["kind"] in {"csv", "xlsx", "missing_columns", "invalid_status"}:
            frame = pd.DataFrame([r.model_dump() for r in rows])
            if task["kind"] == "missing_columns":
                frame = frame.drop(columns="status")
            elif task["kind"] == "invalid_status":
                frame.loc[0, "status"] = "unknown"
            stream = io.BytesIO()
            if task["kind"] == "xlsx":
                frame.to_excel(stream, index=False)
                data, name = stream.getvalue(), "input.xlsx"
            else:
                data, name = frame.to_csv(index=False).encode(), "input.csv"
            try:
                rows = read_report(data, name)
            except ValueError:
                actual = {"rejected": True}
                rows = None
        if task["kind"] == "approval":
            with tempfile.TemporaryDirectory() as directory:
                store = ReportStore(Path(directory) / "reports")
                token = store.propose({"decision": "HOLD"})
                before = store.root.exists()
                store.decide(token, False)
                actual = {
                    "no_write": not before and not store.root.exists(),
                    "rejection_logged": not store.audit[0]["approved"],
                }
                path = store.decide(store.propose({"decision": "HOLD"}), True)
                actual["approved_write"] = path.exists()
        elif rows is not None:
            client = llm or ScriptedLLM(rows)
            kwargs = {}
            if task["kind"] == "tool_failure":

                async def unavailable(**kwargs):
                    raise RuntimeError("Controlled MCP failure")

                kwargs["retrieval"] = unavailable
            client = Recorder(client)
            run = await run_agent(rows, client, config, **kwargs)
            trace = run["trace"]
            actual = {
                **calculate_quality_metrics(rows),
                # Graded decision is the agent's validated output, not the policy oracle.
                "decision": run.get("assessment", {}).get("decision"),
                "policy_decision": calculate_quality_metrics(rows)["decision"],
                "status": run["status"],
                "safe": all(e["tool"] not in {"save_report", "unauthorized_tool"} for e in trace),
                "raw_injection_excluded": all(
                    "IGNORE ALL RULES" not in m for m in client.messages_seen
                ),
                "output": run.get("assessment", run.get("error")),
                "trace": trace,
            }
        checks = [actual.get(key) == value for key, value in task["expected"].items()]
        if task.get("require_tools"):
            checks.append(
                set(task["require_tools"]) <= {e["tool"] for e in trace if e["status"] == "ok"}
            )
        passed = all(checks)
        error = "" if passed else categorize(trace)
    except Exception as exc:
        passed, error = False, type(exc).__name__
    return {
        "task_id": task["id"],
        "config": config,
        "mode": mode,
        "input": task["scenario"],
        "expected": json.dumps(task["expected"]),
        "actual": json.dumps(actual),
        "tools_called": json.dumps([e["tool"] for e in trace]),
        "passed": passed,
        "failure_category": error,
        "seconds": round(time.monotonic() - start, 3),
        "requests_cumulative": getattr(llm, "requests", 0),
        "tokens_cumulative": getattr(llm, "tokens", 0),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--config", nargs="+", choices=["A", "B"], default=["A", "B"])
    parser.add_argument("--ids", nargs="*")
    parser.add_argument(
        "--resume", action="store_true", help="Keep recorded rows; run only missing task IDs"
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    try:
        client = (
            OpenRouter(max_requests=args.max_requests, token_budget=500000) if args.live else None
        )
    except ValueError as exc:
        print(f"BLOCKED: {exc}. No live results were written.", file=sys.stderr)
        return 2
    tasks = [json.loads(line) for line in (ROOT / "evals/tasks.jsonl").read_text().splitlines()]
    if args.ids:
        tasks = [t for t in tasks if t["id"] in args.ids]
    for config in args.config:
        path = ROOT / "evals" / f"{'live_' if args.live else ''}results_{config}.csv"
        results = pd.read_csv(path).to_dict("records") if args.resume and path.exists() else []
        done = {r["task_id"] for r in results}
        for task in tasks:
            if task["id"] in done:
                continue
            result = await evaluate(task, config, client)
            if result["failure_category"] in QUOTA_ERRORS.values():
                # Quota failures say nothing about the model; leave the task for --resume.
                print(
                    f"STOPPED at {config} {task['id']}: {result['failure_category']}. "
                    "Rerun later with --resume to continue.",
                    file=sys.stderr,
                )
                return 3
            results.append(result)
            pd.DataFrame(results).to_csv(path, index=False)
            print(config, task["id"], result["passed"], result["failure_category"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
