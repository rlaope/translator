from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import anthropic

from .base_runner import BaseRunner, RawResult


class ClaudeRunner(BaseRunner):
    def __init__(self, max_tokens: int = 4096, temperature: float = 0.0) -> None:
        self._client = anthropic.AsyncAnthropic()
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def run_single(
        self,
        prompt: str,
        model: str,
        *,
        test_case_id: str = "",
        language: str = "",
        trial: int = 1,
        **kwargs,
    ) -> RawResult:
        timestamp = datetime.now(timezone.utc).isoformat()
        max_retries = 2

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            try:
                message = await self._client.messages.create(
                    model=model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                latency_ms = (time.monotonic() - start) * 1000

                response_text = "".join(
                    block.text
                    for block in message.content
                    if hasattr(block, "text")
                )

                return RawResult(
                    test_case_id=test_case_id,
                    language=language,
                    trial=trial,
                    model=model,
                    response_text=response_text,
                    tokens_input=message.usage.input_tokens,
                    tokens_output=message.usage.output_tokens,
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    error=None,
                )

            except anthropic.RateLimitError as exc:
                if attempt < max_retries:
                    wait = 2 ** (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                latency_ms = (time.monotonic() - start) * 1000
                return RawResult(
                    test_case_id=test_case_id,
                    language=language,
                    trial=trial,
                    model=model,
                    response_text="",
                    tokens_input=0,
                    tokens_output=0,
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    error=f"RateLimitError: {exc}",
                )

            except anthropic.APIError as exc:
                latency_ms = (time.monotonic() - start) * 1000
                return RawResult(
                    test_case_id=test_case_id,
                    language=language,
                    trial=trial,
                    model=model,
                    response_text="",
                    tokens_input=0,
                    tokens_output=0,
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    error=f"{type(exc).__name__}: {exc}",
                )

        # Unreachable but satisfies type checker
        raise RuntimeError("run_single exited retry loop unexpectedly")
