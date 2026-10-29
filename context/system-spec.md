# Context and trust specification

The system prompt specifies the output schema, tool boundaries and untrusted-data policy.
Configuration A uses that basic prompt. B additionally guides tool order, retrieval and evidence grounding.
Both use the same configured free model, tools, validation, permission boundary and numerical policy.
Only validated IDs, enum values, feature names and deterministic aggregates enter the model context.
Raw issue descriptions remain local; this intentionally sacrifices nuanced free-text reasoning to remove
the primary report-injection channel. Uploaded descriptions are visible in the source table, never HTML.

Retrieval tokenizes a query and ranks four short local policy excerpts by keyword overlap with deterministic
tie breaking. At most four excerpts are returned over a real MCP stdio subprocess. No remote retrieval.
Tool results are capped at 6,000 characters, with a truncation flag. At 18,000 history characters the loop
replaces completed conversation rounds with bounded verified evidence (up to 14,000 characters).
The latest request remains. Compaction never retains an orphaned tool-result message.

Eight agent steps, at most six calls per step, two invalid-output attempts. API timeout 40 seconds, three
attempts with 1/2-second backoff; every attempt counts against quota. MCP timeout 90 seconds.
UTF-8 serialized request bytes plus output allocation are conservatively reserved before API calls.
Reported API usage is tracked separately. SDK automatic retries are disabled. Only :free model IDs and
zero-price providers are allowed; estimated token cost is $0. No paid fallback exists.
UI session quota: 40 attempts / 200,000 reserved tokens. CLI live eval quota: 40 attempts / 500,000 reserved
tokens shared across A and B by default. Restarting a process resets this local quota; OpenRouter's account
quota is authoritative. Never use process restarts to evade provider limits.


