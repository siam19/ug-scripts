"""
Token Tracking & Accounting Module.

Accumulates prompt and completion token counts from Gemini Vertex AI responses
using a request-scoped ContextVar across sequential and concurrent coroutines.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from schemas import TokenUsage

@dataclass
class TokenAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, input_count: int, output_count: int, total_count: int | None = None) -> None:
        self.input_tokens += max(0, input_count)
        self.output_tokens += max(0, output_count)
        if total_count is not None and total_count > 0:
            self.total_tokens += total_count
        else:
            self.total_tokens += max(0, input_count) + max(0, output_count)

    def to_token_usage(self) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


# Request-scoped accumulator
token_accumulator_var: ContextVar[TokenAccumulator | None] = ContextVar(
    "token_accumulator_var",
    default=None,
)


def start_token_tracking() -> TokenAccumulator:
    """Initializes a new TokenAccumulator for the current request context."""
    acc = TokenAccumulator()
    token_accumulator_var.set(acc)
    return acc


def record_gemini_usage(usage_metadata: Any) -> None:
    """Records token usage from a Google GenAI response object into the active accumulator."""
    if not usage_metadata:
        return

    acc = token_accumulator_var.get()
    if acc is not None:
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
        candidates_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
        acc.add(prompt_tokens, candidates_tokens, total_tokens)


def get_current_token_usage() -> TokenUsage:
    """Returns the accumulated TokenUsage for the current request."""
    acc = token_accumulator_var.get()
    if acc is not None:
        return acc.to_token_usage()
    return TokenUsage()
