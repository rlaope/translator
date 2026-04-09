from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Score(IntEnum):
    TERRIBLE = 1
    POOR = 2
    FAIR = 3
    GOOD = 4
    EXCELLENT = 5


@dataclass
class ScoringDimension:
    name: str
    name_ko: str
    weight: float
    description: str
    rubric: dict[int, str]  # score -> criteria description


@dataclass
class ScoringRubrics:
    dimensions: list[ScoringDimension]

    def composite_score(self, scores: dict[str, int]) -> float:
        total = 0.0
        for dim in self.dimensions:
            total += scores[dim.name] * dim.weight
        return round(total, 2)

    def validate_scores(self, scores: dict[str, int]) -> bool:
        for dim in self.dimensions:
            if dim.name not in scores:
                return False
            if scores[dim.name] not in range(1, 6):
                return False
        return True


DEFAULT_RUBRICS = ScoringRubrics(
    dimensions=[
        ScoringDimension(
            name="implementation_accuracy",
            name_ko="구현정확도",
            weight=0.30,
            description=(
                "Measures how correctly and completely the model implements the requested "
                "functionality. Evaluates whether the output satisfies all stated requirements, "
                "handles edge cases, and produces correct results."
            ),
            rubric={
                1: (
                    "Implementation is fundamentally broken or completely wrong. Does not satisfy "
                    "any of the stated requirements. Output would not run or produces entirely "
                    "incorrect results."
                ),
                2: (
                    "Implementation satisfies fewer than half of the requirements. Major "
                    "functionality is missing or incorrect. Edge cases are ignored and the core "
                    "logic has significant errors."
                ),
                3: (
                    "Implementation satisfies most core requirements but has notable gaps or "
                    "inaccuracies. Key edge cases may be mishandled. Output is partially correct "
                    "but would fail several validation tests."
                ),
                4: (
                    "Implementation satisfies nearly all requirements with only minor omissions "
                    "or inaccuracies. Most edge cases are handled correctly. Output passes the "
                    "majority of validation tests."
                ),
                5: (
                    "Implementation fully and correctly satisfies all stated requirements. All "
                    "edge cases are handled appropriately. Output passes all validation tests "
                    "and demonstrates deep understanding of the problem."
                ),
            },
        ),
        ScoringDimension(
            name="intent_comprehension",
            name_ko="의도파악",
            weight=0.25,
            description=(
                "Measures how well the model understands the underlying intent and context of "
                "the prompt, beyond the literal text. Evaluates whether the response addresses "
                "the actual goal rather than a surface-level reading."
            ),
            rubric={
                1: (
                    "Model completely misunderstands the intent of the prompt. Response addresses "
                    "a different problem or misinterprets the request in a fundamental way. "
                    "No evidence of comprehension of the actual goal."
                ),
                2: (
                    "Model grasps only the most superficial interpretation of the prompt. "
                    "Misses important implicit requirements or context. Response partially "
                    "addresses the request but diverges significantly from the intended goal."
                ),
                3: (
                    "Model understands the primary intent but misses some nuanced requirements "
                    "or secondary goals. Response addresses the main ask but could be more "
                    "aligned with the full context of what was requested."
                ),
                4: (
                    "Model demonstrates good comprehension of both explicit and implicit "
                    "requirements. Response aligns well with the intended goal and considers "
                    "relevant context. Minor aspects of intent may be overlooked."
                ),
                5: (
                    "Model demonstrates excellent comprehension of the full intent including "
                    "implicit requirements and broader context. Response precisely targets the "
                    "actual goal, anticipates unstated needs, and shows deep understanding of "
                    "the problem domain."
                ),
            },
        ),
        ScoringDimension(
            name="hallucination",
            name_ko="할루시네이션",
            weight=0.20,
            description=(
                "Measures the degree to which the model generates false, fabricated, or "
                "ungrounded information. Evaluates the factual accuracy of claims about APIs, "
                "libraries, syntax, behavior, and domain knowledge."
            ),
            rubric={
                1: (
                    "Response contains pervasive hallucinations. Multiple fabricated API calls, "
                    "non-existent functions, incorrect syntax, or false factual claims that would "
                    "critically mislead the user. Core technical assertions are wrong."
                ),
                2: (
                    "Response contains significant hallucinations that would cause material harm "
                    "if followed. Several fabricated or incorrect technical details, wrong API "
                    "signatures, or false claims about library behavior."
                ),
                3: (
                    "Response contains some hallucinations or inaccuracies but they are not "
                    "central to the solution. Minor incorrect details, slightly wrong syntax, or "
                    "marginally outdated information that a careful reader could identify."
                ),
                4: (
                    "Response is largely accurate with only very minor inaccuracies that do not "
                    "materially affect correctness. Occasional imprecise wording but no "
                    "fabricated information. Technical claims are generally trustworthy."
                ),
                5: (
                    "Response is completely accurate with no hallucinations. All API calls, "
                    "library usage, syntax, and factual claims are correct and verifiable. "
                    "Model appropriately expresses uncertainty when knowledge may be limited."
                ),
            },
        ),
        ScoringDimension(
            name="code_bugs",
            name_ko="코드버그 발생도",
            weight=0.15,
            description=(
                "Measures the presence and severity of bugs in generated code. Evaluates "
                "runtime errors, logic errors, security vulnerabilities, and other defects "
                "that would cause the code to fail or behave incorrectly."
            ),
            rubric={
                1: (
                    "Code contains critical bugs that prevent execution or cause immediate "
                    "failure. Multiple severe issues such as syntax errors, undefined variables, "
                    "infinite loops, or security vulnerabilities that make the code unusable."
                ),
                2: (
                    "Code contains significant bugs that cause incorrect behavior in common "
                    "scenarios. Logical errors, off-by-one mistakes, incorrect data handling, "
                    "or resource leaks that would be caught quickly in testing."
                ),
                3: (
                    "Code works for the happy path but has bugs in edge cases or error "
                    "handling. Some missing null checks, unhandled exceptions, or minor logical "
                    "errors that appear under specific conditions."
                ),
                4: (
                    "Code is mostly correct with only trivial bugs or stylistic issues. "
                    "Edge cases are generally handled. Any bugs present are minor and would "
                    "not cause failures in typical usage scenarios."
                ),
                5: (
                    "Code is bug-free or has negligible issues. Handles all cases correctly "
                    "including edge cases. Error handling is robust, resources are managed "
                    "properly, and the code is safe to use in production."
                ),
            },
        ),
        ScoringDimension(
            name="omission_outdated",
            name_ko="누락/아웃데이트 빈번도",
            weight=0.10,
            description=(
                "Measures how often the model omits important information or provides outdated "
                "guidance. Evaluates completeness of the response and currency of the "
                "recommended approaches, APIs, and best practices."
            ),
            rubric={
                1: (
                    "Response has critical omissions that make it nearly unusable without "
                    "significant additional research. Key steps, imports, or configuration are "
                    "missing. Guidance is severely outdated, referencing deprecated APIs or "
                    "obsolete patterns."
                ),
                2: (
                    "Response omits important sections that a user would need to implement the "
                    "solution. Several necessary details are missing. Some guidance references "
                    "outdated approaches that are no longer recommended."
                ),
                3: (
                    "Response covers the main content but omits some useful details. A "
                    "knowledgeable developer could fill the gaps. Mostly current but may include "
                    "a few outdated references or miss recent best practices."
                ),
                4: (
                    "Response is fairly complete with only minor omissions. Guidance is current "
                    "and reflects modern best practices. Any missing details are non-essential "
                    "and the user can proceed without them."
                ),
                5: (
                    "Response is comprehensive with no meaningful omissions. All necessary "
                    "context, imports, configuration, and steps are included. Guidance reflects "
                    "the latest best practices and current API versions."
                ),
            },
        ),
    ]
)
