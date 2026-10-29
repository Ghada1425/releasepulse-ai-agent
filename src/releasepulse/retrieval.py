import re
from pathlib import Path

POLICY = Path(__file__).resolve().parents[2] / "context" / "qa-policy.md"
SOURCE = "context/qa-policy.md"


def load_rules(path: Path = POLICY) -> dict[str, str]:
    """Parse the maintained policy table so MCP serves exactly what reviewers read."""
    rules = dict(
        re.findall(r"^\|\s*(QA-\d{2})\s*\|\s*(.+?)\s*\|\s*$", path.read_text("utf-8"), re.M)
    )
    if set(rules) != {"QA-01", "QA-02", "QA-03", "QA-04"}:
        raise RuntimeError(f"{SOURCE} must define exactly QA-01 to QA-04")
    return rules


RULES = load_rules()


def retrieve(query: str, limit: int = 3) -> list[dict]:
    terms = set(re.findall(r"\w+", query.lower()))
    ranked = sorted(
        RULES.items(),
        key=lambda item: (-len(terms & set(re.findall(r"\w+", item[1].lower()))), item[0]),
    )
    return [
        {"document_id": k, "excerpt": v, "source": f"{SOURCE}#{k.lower()}"}
        for k, v in ranked[: max(1, min(limit, 4))]
    ]
