import json
import logging
import os
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

log = logging.getLogger("releasepulse.llm")


class BudgetExhausted(RuntimeError):
    """Local request/token quota reached; no request was sent."""


class ProviderUnavailable(RuntimeError):
    """Rate limits, timeouts or provider errors persisted through every budgeted attempt."""

    def __init__(self, message: str, category: str = "provider_error"):
        super().__init__(message)
        self.category = category


class EmptyResponse(RuntimeError):
    """OpenRouter can return HTTP 200 with an upstream error and no choices."""


def diagnose(exc: Exception) -> dict:
    """Key-free error summary: category, HTTP status and OpenRouter's routing metadata only."""
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    meta = body.get("metadata", {}) if isinstance(body, dict) else {}
    meta = meta if isinstance(meta, dict) else {}
    if isinstance(exc, EmptyResponse):
        category = "empty_response"
    elif isinstance(exc, APITimeoutError):
        category = "timeout"
    elif isinstance(exc, APIConnectionError):
        category = "connection"
    elif status == 429:
        upstream = meta.get("limit_source", "").startswith("upstream") or bool(
            meta.get("provider_name")
        )
        category = "rate_limited_upstream" if upstream else "rate_limited_account"
    elif status in (401, 403):
        category = "auth"
    elif status == 402:
        category = "insufficient_credits"
    elif status == 404:
        category = "model_unavailable"
    elif status in (400, 422):
        category = "bad_request"
    elif status is not None and status >= 500:
        category = "provider_error"
    else:
        category = "unexpected"
    return {
        "category": category,
        "status": status,
        "provider": meta.get("provider_name"),
        "limit_source": meta.get("limit_source"),
    }


def retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    value = response.headers.get("retry-after") if response is not None else None
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


RETRYABLE = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    EmptyResponse,
)


class OpenRouter:
    """No automatic paid fallback. SDK retries disabled so every attempt is budgeted."""

    def __init__(
        self,
        max_requests: int = 12,
        token_budget: int = 50000,
        attempts: int = 3,
        rate_limit_wait: float = 15.0,
    ):
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("Set OPENROUTER_API_KEY in .env to run live AI analysis")
        self.model = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
        base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        if not self.model.endswith(":free") or base != "https://openrouter.ai/api/v1":
            raise ValueError(
                "Only OpenRouter free models and the official API endpoint are allowed"
            )
        self.client = OpenAI(api_key=key, base_url=base, timeout=40, max_retries=0)
        self.requests = 0
        self.tokens = 0
        self.reserved_tokens = 0
        self.max_requests = max_requests
        self.token_budget = token_budget
        self.retries = 0
        self.estimated_cost_usd = 0.0
        self.attempts = attempts
        # Free shared pools need seconds, not 1-2 s backoff; capped to stay interactive.
        self.rate_limit_wait = rate_limit_wait
        self.errors: list[dict] = []

    def complete(self, messages: list, tools: list):
        for attempt in range(self.attempts):
            # UTF-8 byte count is a conservative upper bound for text token reservation.
            reserve = len(json.dumps([messages, tools]).encode()) + 1500
            if (
                self.requests >= self.max_requests
                or self.reserved_tokens + reserve > self.token_budget
            ):
                raise BudgetExhausted("Request/token budget exhausted; no request sent")
            self.requests += 1
            self.reserved_tokens += reserve
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    temperature=0,
                    max_tokens=1500,
                    extra_body={"provider": {"max_price": {"prompt": 0, "completion": 0}}},
                )
                if response.usage:
                    self.tokens += response.usage.total_tokens
                if not response.choices:
                    raise EmptyResponse()
                return response.choices[0].message
            except (*RETRYABLE, APIStatusError) as exc:
                info = {"attempt": attempt + 1, **diagnose(exc)}
                self.errors.append(info)
                log.warning("OpenRouter attempt failed: %s", info)
                if not isinstance(exc, RETRYABLE):
                    raise
                if attempt == self.attempts - 1:
                    raise ProviderUnavailable(
                        f"OpenRouter unavailable after {self.attempts} attempts "
                        f"({info['category']})",
                        info["category"],
                    ) from None
                self.retries += 1
                wait = 2**attempt
                if isinstance(exc, RateLimitError):
                    wait = min(retry_after(exc) or self.rate_limit_wait * (attempt + 1), 60)
                time.sleep(wait)
