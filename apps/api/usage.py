"""
Token Tracking & Accounting Module.

Accumulates prompt and completion token counts from Gemini Vertex AI responses
using a request-scoped ContextVar across sequential and concurrent coroutines.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any
from schemas import StageTokens, TokenUsage

@dataclass
class TokenAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    by_stage: dict[str, dict[str, int]] = field(default_factory=dict)

    def add(
        self,
        input_count: int,
        output_count: int,
        total_count: int | None = None,
        stage: str = "unspecified",
    ) -> None:
        inc_in = max(0, input_count)
        inc_out = max(0, output_count)
        inc_total = total_count if (total_count is not None and total_count > 0) else (inc_in + inc_out)

        self.input_tokens += inc_in
        self.output_tokens += inc_out
        self.total_tokens += inc_total

        if stage:
            if stage not in self.by_stage:
                self.by_stage[stage] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                }
            self.by_stage[stage]["input_tokens"] += inc_in
            self.by_stage[stage]["output_tokens"] += inc_out
            self.by_stage[stage]["total_tokens"] += inc_total

    def to_token_usage(self) -> TokenUsage:
        stage_map = {
            stg: StageTokens(
                input_tokens=data.get("input_tokens", 0),
                output_tokens=data.get("output_tokens", 0),
                total_tokens=data.get("total_tokens", 0),
            )
            for stg, data in self.by_stage.items()
        }
        return TokenUsage(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
            by_stage=stage_map,
        )

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }
        if self.by_stage:
            res["by_stage"] = self.by_stage
        return res


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


def record_gemini_usage(usage_metadata: Any, stage: str = "unspecified") -> None:
    """Records token usage from a Google GenAI response object into the active accumulator."""
    if not usage_metadata:
        return

    acc = token_accumulator_var.get()
    if acc is not None:
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
        candidates_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
        acc.add(prompt_tokens, candidates_tokens, total_tokens, stage=stage)


def get_current_token_usage() -> TokenUsage:
    """Returns the accumulated TokenUsage for the current request."""
    acc = token_accumulator_var.get()
    if acc is not None:
        return acc.to_token_usage()
    return TokenUsage()
