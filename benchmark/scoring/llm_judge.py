from __future__ import annotations

from ..runners.judge_runner import JudgeRunner, JudgeScores

_ALL_DIMENSIONS = [
    "implementation_accuracy",
    "intent_comprehension",
    "hallucination",
    "code_bugs",
    "omission_outdated",
]


class LLMJudgeScorer:
    """Wraps JudgeRunner to produce a complete 5-dimension score dict."""

    def __init__(
        self,
        judge_model: str = "claude-sonnet-4-6-20250514",
        evaluations: int = 3,
        variance_threshold: float = 1.0,
    ) -> None:
        self._runner = JudgeRunner(
            judge_model=judge_model,
            evaluations=evaluations,
            variance_threshold=variance_threshold,
        )

    async def score(
        self,
        english_prompt: str,
        response: str,
    ) -> dict[str, float]:
        """Evaluate a response and return scores for all 5 dimensions.

        Returns
        -------
        dict with float values for each of the 5 rubric dimensions plus
        a ``reasoning`` key (str) and ``evaluations`` key (int).
        """
        judge_scores: JudgeScores = await self._runner.evaluate(
            english_prompt=english_prompt,
            response=response,
        )

        return {
            "implementation_accuracy": judge_scores.implementation_accuracy,
            "intent_comprehension": judge_scores.intent_comprehension,
            "hallucination": judge_scores.hallucination,
            "code_bugs": judge_scores.code_bugs,
            "omission_outdated": judge_scores.omission_outdated,
            "reasoning": judge_scores.reasoning,
            "evaluations": float(judge_scores.evaluations),
        }

    async def score_with_override(
        self,
        english_prompt: str,
        response: str,
        overrides: dict[str, float],
    ) -> dict[str, float]:
        """Score response but replace specified dimensions with pre-computed values.

        Useful when automated scoring already produced reliable values for
        ``implementation_accuracy`` and ``code_bugs`` and only the subjective
        dimensions need LLM evaluation.
        """
        scores = await self.score(english_prompt=english_prompt, response=response)
        scores.update(overrides)
        return scores
