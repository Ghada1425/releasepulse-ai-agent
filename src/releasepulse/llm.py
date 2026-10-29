import json
import os
import time

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


class BudgetExhausted(RuntimeError):
    """Local request/token quota reached; no request was sent."""


class ProviderUnavailable(RuntimeError):
    """Rate limits, timeouts or provider errors persisted through every budgeted attempt."""


class EmptyResponse(RuntimeError):
    """OpenRouter can return HTTP 200 with an upstream error and no choices."""


RETRYABLE = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    EmptyResponse,
)


class OpenRouter:
    """No automatic paid fallback. SDK retries disabled so every attempt is budgeted."""

    def __init__(self, max_requests: int = 12, token_budget: int = 50000):
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

    def complete(self, messages: list, tools: list):
        for attempt in range(3):
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
            except RETRYABLE:
                if attempt == 2:
                    raise ProviderUnavailable("OpenRouter unavailable after 3 attempts") from None
                self.retries += 1
                time.sleep(2**attempt)
