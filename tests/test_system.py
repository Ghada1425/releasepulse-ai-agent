import asyncio
import io
import json

import pandas as pd
import pytest

from releasepulse.agent import run_agent
from releasepulse.analytics import calculate_quality_metrics, read_report
from releasepulse.fixtures import ScriptedLLM, healthy, scenario
from releasepulse.mcp_client import retrieve_mcp
from releasepulse.security import ReportStore


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("healthy", "READY"),
        ("critical_login", "HOLD"),
        ("market_delay", "REVIEW"),
        ("coverage_gap", "REVIEW"),
        ("untested_critical", "HOLD"),
        ("empty", "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_policy(kind, decision):
    assert calculate_quality_metrics(scenario(kind))["decision"] == decision


def test_denominators_and_duplicates():
    rows = scenario("duplicate")
    result = calculate_quality_metrics(rows)
    assert result["duplicate_issue_groups"] == 1
    assert result["pass_rate"] == 16 / 18
    assert result["failure_rate"] == 2 / 18
    assert result["coverage_rate"] == 1


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_roundtrip(extension):
    frame = pd.DataFrame([r.model_dump() for r in healthy()])
    stream = io.BytesIO()
    if extension == "xlsx":
        frame.to_excel(stream, index=False)
        payload = stream.getvalue()
    else:
        payload = frame.to_csv(index=False).encode()
    assert len(read_report(payload, "report." + extension)) == 18


def test_upload_limits():
    with pytest.raises(ValueError):
        read_report(b"x" * (5 * 1024 * 1024 + 1), "report.csv")
    with pytest.raises(ValueError):
        read_report(b"abc", "report.exe")
    with pytest.raises(ValueError):
        read_report(b"foo,bar\n1,2", "report.csv")


def test_approval_rejection_tamper_and_replay(tmp_path):
    store = ReportStore(tmp_path / "reports")
    report = {"decision": "HOLD"}
    token = store.propose(report)
    report["decision"] = "READY"
    assert not store.root.exists()
    path = store.decide(token, True)
    assert json.loads(path.read_text())["decision"] == "HOLD"
    with pytest.raises(KeyError):
        store.decide(token, True)
    before = list(store.root.iterdir())
    assert store.decide(store.propose(report), False) is None
    assert before == list(store.root.iterdir())
    assert store.audit[-1]["approved"] is False


def test_real_mcp():
    docs = asyncio.run(retrieve_mcp("critical login", 4))
    assert {d["document_id"] for d in docs} == {"QA-01", "QA-02", "QA-03", "QA-04"}


@pytest.mark.parametrize("config", ["A", "B"])
def test_multistep_injection_defense(config):
    rows = scenario("injection")
    client = ScriptedLLM(rows)
    run = asyncio.run(run_agent(rows, client, config))
    assert run["status"] == "complete"
    assert run["assessment"]["decision"] == "HOLD"
    assert all("IGNORE ALL RULES" not in msg for msg in client.messages_seen)
    assert len({e["tool"] for e in run["trace"]}) == 4


def test_unauthorized_tool_denied():
    run = asyncio.run(run_agent(healthy(), ScriptedLLM(healthy(), forbidden=True)))
    assert run["trace"][0]["tool"] == "unauthorized_tool"
    assert run["trace"][0]["status"] == "error"


def test_bounded_repair():
    run = asyncio.run(run_agent(healthy(), ScriptedLLM(healthy(), invalid=True)))
    assert run["status"] == "partial"
    assert sum(e["tool"] == "output_validation" for e in run["trace"]) == 2


def test_failed_mcp_is_partial():
    async def failed(**kwargs):
        raise RuntimeError("failure")

    run = asyncio.run(run_agent(healthy(), ScriptedLLM(healthy()), retrieval=failed))
    assert run["status"] == "partial"
    assert run["metrics"]["decision"] == "READY"


def test_free_model_and_budget(monkeypatch):
    from releasepulse.llm import OpenRouter

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "paid/model")
    with pytest.raises(ValueError):
        OpenRouter()
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    client = OpenRouter(max_requests=0)
    with pytest.raises(RuntimeError):
        client.complete([], [])
    assert client.requests == 0


def test_token_reservation_prevents_request(monkeypatch):
    from releasepulse.llm import OpenRouter

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    client = OpenRouter(token_budget=1)
    with pytest.raises(RuntimeError):
        client.complete([], [])
    assert client.requests == 0


def test_rate_limits_count_every_attempt(monkeypatch):
    import httpx
    from openai import RateLimitError

    from releasepulse.llm import OpenRouter

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    client = OpenRouter(max_requests=3)
    response = httpx.Response(429, request=httpx.Request("POST", "https://openrouter.ai/api/v1"))

    def limited(**kwargs):
        raise RateLimitError("quota", response=response, body=None)

    monkeypatch.setattr(client.client.chat.completions, "create", limited)
    monkeypatch.setattr("releasepulse.llm.time.sleep", lambda _: None)
    with pytest.raises(RuntimeError):
        client.complete([], [])
    assert client.requests == 3
    assert client.retries == 2


def test_untrusted_final_decision_cannot_override_policy():
    from openai.types.chat import ChatCompletionMessage

    class WrongDecision(ScriptedLLM):
        def complete(self, messages, tools):
            reply = super().complete(messages, tools)
            if not reply.tool_calls:
                body = json.loads(reply.content)
                body["decision"] = "READY"
                return ChatCompletionMessage(role="assistant", content=json.dumps(body))
            return reply

    rows = scenario("critical_login")
    run = asyncio.run(run_agent(rows, WrongDecision(rows)))
    assert run["status"] == "partial"
    assert run["metrics"]["decision"] == "HOLD"
