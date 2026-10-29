from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FEATURES = [
    "Login",
    "Onboarding",
    "Trading",
    "Market data",
    "Portfolio",
    "Funds",
    "Cash transfers",
    "Settings",
    "Stability",
]
CHANNELS = ["Web", "Mobile"]
CRITICAL = {"Login", "Trading", "Funds", "Cash transfers"}


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    feature: str
    channel: Literal["Web", "Mobile"]
    status: Literal["passed", "failed", "blocked", "skipped"]
    severity: Literal["critical", "high", "medium", "low"]
    issue: str = Field(default="", max_length=1000)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str
    rule_id: Literal["QA-01", "QA-02", "QA-03", "QA-04"]
    explanation: str = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=300)


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["HOLD", "REVIEW", "READY", "INSUFFICIENT_EVIDENCE"]
    summary: str = Field(min_length=1, max_length=1000)
    findings: list[Finding] = Field(max_length=30)
