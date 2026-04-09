from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

_JUDGE_SYSTEM = """\
You are an expert evaluator assessing AI model response quality for a multilingual benchmark.
Evaluate objectively and always respond in English regardless of the language of the model's response.
Return ONLY valid JSON — no markdown fences, no extra text.\
"""

_JUDGE_TEMPLATE = """\
You are an expert evaluator assessing an AI model's response quality.

## Original Task (English)
{english_prompt}

## Model's Response
{response}

## Scoring Rubrics
Rate each dimension on a 1-5 scale:

1. **Implementation Accuracy** (1-5)
   5=Fully correct and complete; 4=Minor issues only; 3=Partially correct; 2=Major errors; 1=Incorrect or missing

2. **Intent Comprehension** (1-5)
   5=Perfectly understands task intent and constraints; 4=Good understanding, minor misreads; \
3=Partial understanding; 2=Significant misunderstanding; 1=Fails to understand the task

3. **Hallucination** (1-5, higher=less hallucination)
   5=No hallucination, all claims accurate; 4=Trivial inaccuracies; 3=Some fabricated details; \
2=Significant hallucinations; 1=Pervasive false information

4. **Code Bug Rate** (1-5, higher=fewer bugs)
   5=No bugs, code runs correctly; 4=Minor style issues only; 3=Bugs that may affect output; \
2=Multiple logic errors; 1=Code does not function

5. **Omission / Outdated** (1-5, higher=more complete and current)
   5=Nothing omitted, fully up-to-date; 4=Trivial omissions; 3=Noticeable gaps; \
2=Important sections missing; 1=Critically incomplete or outdated

Return ONLY a JSON object with these exact keys:
{{"implementation_accuracy": N, "intent_comprehension": N, "hallucination": N, \
"code_bugs": N, "omission_outdated": N, "reasoning": "brief explanation"}}\
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_SCORE_KEYS = frozenset(
    ["implementation_accuracy", "intent_comprehension", "hallucination", "code_bugs", "omission_outdated"]
)


@dataclass
class JudgeScores:
    implementation_accuracy: float
    intent_comprehension: float
    hallucination: float
    code_bugs: float
    omission_outdated: float
    reasoning: str
    evaluations: int = 1


def _parse_scores(text: str) -> dict:
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError(f"No JSON found in judge response: {text[:200]}")
    data = json.loads(m.group())
    missing = _SCORE_KEYS - data.keys()
    if missing:
        raise ValueError(f"Judge response missing keys: {missing}")
    return data


def _average_dicts(dicts: list[dict]) -> dict:
    averaged: dict = {}
    for key in _SCORE_KEYS:
        averaged[key] = sum(d[key] for d in dicts) / len(dicts)
    averaged["reasoning"] = dicts[-1].get("reasoning", "")
    return averaged


def _max_variance(dicts: list[dict]) -> float:
    variance = 0.0
    for key in _SCORE_KEYS:
        values = [d[key] for d in dicts]
        mean = sum(values) / len(values)
        v = sum((x - mean) ** 2 for x in values) / len(values)
        variance = max(variance, v)
    return variance


class JudgeRunner:
    def __init__(
        self,
        judge_model: str = "claude-sonnet-4-6-20250514",
        evaluations: int = 3,
        variance_threshold: float = 1.0,
        max_tokens: int = 512,
    ) -> None:
        self._client = anthropic.AsyncAnthropic()
        self.judge_model = judge_model
        self.evaluations = evaluations
        self.variance_threshold = variance_threshold
        self.max_tokens = max_tokens

    async def _call_judge(self, english_prompt: str, response: str) -> dict:
        user_content = _JUDGE_TEMPLATE.format(
            english_prompt=english_prompt,
            response=response,
        )
        message = await self._client.messages.create(
            model=self.judge_model,
            max_tokens=self.max_tokens,
            temperature=0.0,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(
            block.text for block in message.content if hasattr(block, "text")
        )
        return _parse_scores(text)

    async def evaluate(self, english_prompt: str, response: str) -> JudgeScores:
        """Run `self.evaluations` judge calls; re-evaluate once if variance is high."""
        raw_scores: list[dict] = []
        for _ in range(self.evaluations):
            scores = await self._call_judge(english_prompt, response)
            raw_scores.append(scores)

        if _max_variance(raw_scores) > self.variance_threshold:
            # One additional tiebreaker evaluation
            extra = await self._call_judge(english_prompt, response)
            raw_scores.append(extra)

        averaged = _average_dicts(raw_scores)
        return JudgeScores(
            implementation_accuracy=averaged["implementation_accuracy"],
            intent_comprehension=averaged["intent_comprehension"],
            hallucination=averaged["hallucination"],
            code_bugs=averaged["code_bugs"],
            omission_outdated=averaged["omission_outdated"],
            reasoning=averaged["reasoning"],
            evaluations=len(raw_scores),
        )
