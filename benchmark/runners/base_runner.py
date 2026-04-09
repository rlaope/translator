from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawResult:
    test_case_id: str
    language: str
    trial: int
    model: str
    response_text: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    timestamp: str
    error: str | None = None


@dataclass
class SuiteResult:
    results: list[RawResult]
    category: str
    languages: list[str]
    model: str
    started_at: str
    finished_at: str


class BaseRunner(ABC):
    @abstractmethod
    async def run_single(self, prompt: str, model: str, **kwargs) -> RawResult:
        ...

    async def run_test_case(
        self,
        test_case: dict,
        language: str,
        model: str,
        trials: int = 3,
    ) -> list[RawResult]:
        results = []
        for trial in range(1, trials + 1):
            result = await self.run_single(
                prompt=test_case["prompts"][language],
                model=model,
                test_case_id=test_case["id"],
                language=language,
                trial=trial,
            )
            results.append(result)
        return results
