# Synthetic QA release policy v1.0

These are project-defined demonstration rules, not financial regulatory guidance.
The executable copy lives in `releasepulse.retrieval.RULES`; decision logic is in analytics.py.

| ID | Rule |
|---|---|
| QA-01 | A failed or blocked critical-severity test means HOLD. |
| QA-02 | Any other failed or blocked test means at least REVIEW. Prioritize critical, high, medium, low. Market data delays require freshness verification and retesting. |
| QA-03 | Each of nine features must execute on Web and Mobile. Passed and failed count as executed; blocked and skipped do not. Missing Login, Trading, Funds or Cash transfers coverage means HOLD; any other gap means REVIEW. |
| QA-04 | No rows means INSUFFICIENT_EVIDENCE. READY requires no open issue, complete execution coverage, and pass rate >=95%. |

Precedence: insufficient evidence, HOLD, REVIEW, READY. Percentages are not rounded before decisions.
Pass rate = passed / all rows. Failure rate = failed / all rows. Coverage = executed feature-channel pairs / 18.
Severity distribution counts failed and blocked rows only. Duplicate issue groups share a feature and a
case-insensitive, trimmed nonempty description. They are reported, not removed from the denominator.
This checklist is fixed for fictional Nova Trade; adapt policy and tests together for another product.

