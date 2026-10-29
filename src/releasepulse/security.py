"""Persistence is outside the agent's capability set. Approval binds exact bytes."""

import hashlib
import json
import secrets
from pathlib import Path


class ReportStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.pending: dict[str, bytes] = {}
        self.audit: list[dict] = []

    def propose(self, report: dict) -> str:
        token = secrets.token_hex(16)
        self.pending[token] = json.dumps(report, sort_keys=True, indent=2).encode()
        return token

    def decide(self, token: str, approved: bool) -> Path | None:
        payload = self.pending.pop(token)  # one use, rejection consumes proposal
        digest = hashlib.sha256(payload).hexdigest()
        self.audit.append({"event": "report_decision", "approved": approved, "sha256": digest})
        if not approved:
            return None
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"report-{digest}.json"
        destination.write_bytes(payload)
        (self.root / f"approval-{digest}.json").write_text(json.dumps(self.audit), encoding="utf-8")
        return destination
