"""Strict upload validation and versioned synthetic release policy."""

import io
import zipfile
from collections import Counter

import pandas as pd

from releasepulse.models import CHANNELS, CRITICAL, FEATURES, TestCase

MAX_BYTES = 5 * 1024 * 1024


def read_report(data: bytes, filename: str) -> list[TestCase]:
    if len(data) > MAX_BYTES:
        raise ValueError("File exceeds 5 MB limit")
    if filename.lower().endswith(".csv"):
        frame = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    elif filename.lower().endswith(".xlsx"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 25 * 1024 * 1024:
                raise ValueError("Expanded workbook exceeds 25 MB limit")
        frame = pd.read_excel(io.BytesIO(data), dtype=str, keep_default_na=False)
    else:
        raise ValueError("Only CSV and XLSX are accepted")
    required = set(TestCase.model_fields)
    if set(frame.columns) != required:
        raise ValueError("Required columns: " + ", ".join(sorted(required)))
    if len(frame) > 10000:
        raise ValueError("Maximum 10,000 rows")
    rows = [TestCase.model_validate(row) for row in frame.to_dict("records")]
    if any(r.feature not in FEATURES for r in rows):
        raise ValueError("Unknown feature; use the documented feature names")
    if len({r.test_id for r in rows}) != len(rows):
        raise ValueError("Duplicate test_id; every execution must have a unique ID")
    return rows


def analyze_testing_report(rows: list[TestCase]) -> dict:
    return {
        "total": len(rows),
        "statuses": dict(Counter(r.status for r in rows)),
        "by_feature": dict(Counter(r.feature for r in rows)),
        "by_channel": dict(Counter(r.channel for r in rows)),
    }


def calculate_quality_metrics(rows: list[TestCase]) -> dict:
    total = len(rows)
    counts = Counter(r.status for r in rows)
    executed = {(r.feature, r.channel) for r in rows if r.status in {"passed", "failed"}}
    gaps = [f"{f}/{c}" for f in FEATURES for c in CHANNELS if (f, c) not in executed]
    critical_gaps = [g for g in gaps if g.split("/")[0] in CRITICAL]
    open_issues = [r for r in rows if r.status in {"failed", "blocked"}]
    duplicates = Counter((r.feature, r.issue.strip().lower()) for r in open_issues if r.issue)
    critical_ids = [r.test_id for r in open_issues if r.severity == "critical"]
    pass_rate = counts["passed"] / total if total else 0
    decision = (
        "INSUFFICIENT_EVIDENCE"
        if not total
        else "HOLD"
        if critical_ids or critical_gaps
        else "REVIEW"
        if open_issues or gaps or pass_rate < 0.95
        else "READY"
    )
    return {
        "policy_version": "1.0",
        "total": total,
        "pass_rate": pass_rate,
        "failure_rate": counts["failed"] / total if total else 0,
        "severity_distribution": dict(Counter(r.severity for r in open_issues)),
        "coverage_rate": len(executed) / (len(FEATURES) * len(CHANNELS)),
        "coverage_gaps": gaps,
        "critical_gaps": critical_gaps,
        "critical_test_ids": critical_ids,
        "decision": decision,
        "duplicate_issue_groups": sum(n > 1 for n in duplicates.values()),
        "issues": [
            {
                "test_id": r.test_id,
                "feature": r.feature,
                "channel": r.channel,
                "status": r.status,
                "severity": r.severity,
                "rule_id": "QA-01" if r.severity == "critical" else "QA-02",
            }
            for r in open_issues
        ],
    }
