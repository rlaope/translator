from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

_DIMENSIONS = [
    "implementation_accuracy",
    "intent_comprehension",
    "hallucination",
    "code_bugs",
    "omission_outdated",
]

# Default weights from settings.yaml
_DEFAULT_WEIGHTS: dict[str, float] = {
    "implementation_accuracy": 0.30,
    "intent_comprehension": 0.25,
    "hallucination": 0.20,
    "code_bugs": 0.15,
    "omission_outdated": 0.10,
}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def _confidence_interval_95(values: list[float]) -> tuple[float, float]:
    """95 % confidence interval using normal approximation (z=1.96)."""
    if len(values) < 2:
        m = _mean(values)
        return (m, m)
    m = _mean(values)
    se = _stddev(values) / math.sqrt(len(values))
    margin = 1.96 * se
    return (m - margin, m + margin)


@dataclass
class DimensionStats:
    mean: float
    stddev: float
    ci_lower: float
    ci_upper: float
    n: int


@dataclass
class TestCaseAggregation:
    test_case_id: str
    language: str
    dimensions: dict[str, DimensionStats]
    composite_score: float


@dataclass
class CategoryAggregation:
    category: str
    language: str
    dimensions: dict[str, DimensionStats]
    composite_score: float
    test_case_count: int


@dataclass
class LanguageAggregation:
    language: str
    dimensions: dict[str, DimensionStats]
    composite_score: float
    composite_ci: tuple[float, float]
    test_case_count: int


@dataclass
class AggregatedResults:
    per_test_case: list[TestCaseAggregation]
    per_category: dict[str, CategoryAggregation]   # key: "{category}:{language}"
    per_language: dict[str, LanguageAggregation]   # key: language code
    weights: dict[str, float]


# ---------------------------------------------------------------------------
# Input type:
#   trial_scores = list of dicts, each dict has dimension keys -> float score
#   for one trial of one test case / language.
# ---------------------------------------------------------------------------


def _aggregate_dimension_stats(
    score_dicts: list[dict[str, Any]],
    dim: str,
) -> DimensionStats:
    values = [float(d[dim]) for d in score_dicts if dim in d]
    if not values:
        return DimensionStats(mean=0.0, stddev=0.0, ci_lower=0.0, ci_upper=0.0, n=0)
    ci = _confidence_interval_95(values)
    return DimensionStats(
        mean=_mean(values),
        stddev=_stddev(values),
        ci_lower=ci[0],
        ci_upper=ci[1],
        n=len(values),
    )


def _composite(dimension_means: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.get(d, 0.0) for d in _DIMENSIONS)
    if total_weight == 0:
        return 0.0
    return sum(
        dimension_means.get(d, 0.0) * weights.get(d, 0.0) for d in _DIMENSIONS
    ) / total_weight


def aggregate(
    trial_records: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> AggregatedResults:
    """Aggregate trial-level score records into per-test-case, per-category, per-language stats.

    Parameters
    ----------
    trial_records:
        List of dicts, each representing one trial result. Required keys:
            ``test_case_id``, ``language``, ``category``
        Plus one key per scoring dimension with a float score.

    weights:
        Optional dimension weights. Falls back to ``_DEFAULT_WEIGHTS``.

    Returns
    -------
    AggregatedResults
    """
    w = weights if weights is not None else _DEFAULT_WEIGHTS

    # ------------------------------------------------------------------ #
    # 1. Group by (test_case_id, language)
    # ------------------------------------------------------------------ #
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in trial_records:
        key = (rec["test_case_id"], rec["language"])
        groups.setdefault(key, []).append(rec)

    per_test_case: list[TestCaseAggregation] = []
    for (tc_id, lang), recs in groups.items():
        dims = {d: _aggregate_dimension_stats(recs, d) for d in _DIMENSIONS}
        dim_means = {d: dims[d].mean for d in _DIMENSIONS}
        per_test_case.append(
            TestCaseAggregation(
                test_case_id=tc_id,
                language=lang,
                dimensions=dims,
                composite_score=_composite(dim_means, w),
            )
        )

    # ------------------------------------------------------------------ #
    # 2. Per-category (grouped by category + language)
    # ------------------------------------------------------------------ #
    cat_groups: dict[str, list[dict]] = {}
    for rec in trial_records:
        key = f"{rec['category']}:{rec['language']}"
        cat_groups.setdefault(key, []).append(rec)

    per_category: dict[str, CategoryAggregation] = {}
    for cat_lang_key, recs in cat_groups.items():
        category, language = cat_lang_key.split(":", 1)
        dims = {d: _aggregate_dimension_stats(recs, d) for d in _DIMENSIONS}
        dim_means = {d: dims[d].mean for d in _DIMENSIONS}
        tc_count = len({rec["test_case_id"] for rec in recs})
        per_category[cat_lang_key] = CategoryAggregation(
            category=category,
            language=language,
            dimensions=dims,
            composite_score=_composite(dim_means, w),
            test_case_count=tc_count,
        )

    # ------------------------------------------------------------------ #
    # 3. Per-language overall
    # ------------------------------------------------------------------ #
    lang_groups: dict[str, list[dict]] = {}
    for rec in trial_records:
        lang_groups.setdefault(rec["language"], []).append(rec)

    per_language: dict[str, LanguageAggregation] = {}
    for lang, recs in lang_groups.items():
        dims = {d: _aggregate_dimension_stats(recs, d) for d in _DIMENSIONS}
        dim_means = {d: dims[d].mean for d in _DIMENSIONS}
        composite = _composite(dim_means, w)

        # Composite CI: compute composite per trial then CI over those
        trial_composites = [
            _composite({d: float(r.get(d, 0)) for d in _DIMENSIONS}, w)
            for r in recs
        ]
        composite_ci = _confidence_interval_95(trial_composites)
        tc_count = len({rec["test_case_id"] for rec in recs})

        per_language[lang] = LanguageAggregation(
            language=lang,
            dimensions=dims,
            composite_score=composite,
            composite_ci=composite_ci,
            test_case_count=tc_count,
        )

    return AggregatedResults(
        per_test_case=per_test_case,
        per_category=per_category,
        per_language=per_language,
        weights=w,
    )
