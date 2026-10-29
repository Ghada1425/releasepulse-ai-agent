"""Live OpenRouter checks. Skipped, never faked, until a key is configured locally."""

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from releasepulse.agent import run_agent
from releasepulse.fixtures import scenario
from releasepulse.llm import OpenRouter

load_dotenv(Path(__file__).parents[1] / ".env")
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="BLOCKED — Awaiting API Key (OPENROUTER_API_KEY)"
)


def test_live_model_tool_calling_on_critical_login():
    rows = scenario("critical_login")
    llm = OpenRouter(max_requests=12, token_budget=120000)
    run = asyncio.run(run_agent(rows, llm, "B"))
    tools = [(e["tool"], e["status"]) for e in run["trace"]]
    print(
        {
            "model": llm.model,
            "status": run["status"],
            "requests": llm.requests,
            "tokens": llm.tokens,
        }
    )
    print({"provider_errors": llm.errors, "finish_reasons": llm.finish_reasons})
    print({"trace": tools, "error": run.get("error")})
    print([e.get("reason") for e in run["trace"] if e["tool"] == "output_validation"])
    assert llm.requests >= 1
    assert any(e["tool"] == "retrieve_qa_guidelines" and e["status"] == "ok" for e in run["trace"])
    assert run["status"] == "complete", run.get("error")
    assert run["assessment"]["decision"] == "HOLD"
