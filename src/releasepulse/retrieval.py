import re

RULES = {
    "QA-01": "Critical failed or blocked tests prohibit release. Fix and retest login, trading, funds and transfers before release.",
    "QA-02": "Any failed or blocked test requires review. High severity issues are prioritized before medium and low. Market data delay requires freshness verification and retesting.",
    "QA-03": "Execute every feature on Web and Mobile. Missing executed critical feature coverage prohibits release; other gaps require review. Skipped or blocked is not executed coverage.",
    "QA-04": "No tests means insufficient evidence. READY requires no open failures or blockers, full feature/channel execution, and at least 95 percent passed out of all rows.",
}


def retrieve(query: str, limit: int = 3) -> list[dict]:
    terms = set(re.findall(r"\w+", query.lower()))
    ranked = sorted(
        RULES.items(),
        key=lambda item: (-len(terms & set(re.findall(r"\w+", item[1].lower()))), item[0]),
    )
    return [
        {"document_id": k, "excerpt": v, "source": "context/qa-policy.md"}
        for k, v in ranked[: max(1, min(limit, 4))]
    ]
