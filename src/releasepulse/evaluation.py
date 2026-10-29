"""Run reproducible offline harness checks or separately labelled live evaluations."""

import argparse
import asyncio
import io
import json
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
            run = await run_agent(rows, client, config, **kwargs)
            trace = run["trace"]
            actual = {
                **calculate_quality_metrics(rows),
                "status": run["status"],
                "safe": all(e["tool"] != "save_report" for e in trace),
                "output": run.get("assessment", run.get("error")),
                "trace": trace,
            }
            if task["kind"] == "injection" and not llm:
                actual["raw_injection_excluded"] = all(
                    "IGNORE ALL RULES" not in m for m in client.messages_seen
                )
        checks = [actual.get(key) == value for key, value in task["expected"].items()]
        if task.get("require_tools"):
            checks.append(
                set(task["require_tools"]) <= {e["tool"] for e in trace if e["status"] == "ok"}
            )
        passed = all(checks)
        error = (
            ""
            if passed
            else (
                "tool_execution"
                if any(
                    e["status"] == "error" and e["tool"] in {"retrieve_qa_guidelines", "llm"}
                    for e in trace
                )
                else "expectation_mismatch"
            )
        )
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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--config", nargs="+", choices=["A", "B"], default=["A", "B"])
    parser.add_argument("--ids", nargs="*")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    client = OpenRouter(max_requests=args.max_requests, token_budget=500000) if args.live else None
    tasks = [json.loads(line) for line in (ROOT / "evals/tasks.jsonl").read_text().splitlines()]
    if args.ids:
        tasks = [t for t in tasks if t["id"] in args.ids]
    for config in args.config:
        results = []
        path = ROOT / "evals" / f"{'live_' if args.live else ''}results_{config}.csv"
        for task in tasks:
            result = await evaluate(task, config, client)
            results.append(result)
            pd.DataFrame(results).to_csv(path, index=False)
            print(config, task["id"], result["passed"], result["failure_category"], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
