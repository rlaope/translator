from __future__ import annotations

"""Statistical analysis for multilingual benchmark results."""

from dataclasses import dataclass
import numpy as np
from scipy import stats


@dataclass
class ComparisonResult:
    language_a: str
    language_b: str
    dimension: str
    mean_a: float
    mean_b: float
    mean_diff: float
    std_a: float
    std_b: float
    t_statistic: float
    p_value: float
    cohens_d: float
    ci_lower: float
    ci_upper: float
    statistically_significant: bool
    n_samples: int


@dataclass
class LanguageSummary:
    language: str
    n_cases: int
    composite_mean: float
    composite_std: float
    dimension_means: dict[str, float]
    dimension_stds: dict[str, float]


def paired_ttest(scores_a: list[float], scores_b: list[float], alpha: float = 0.05) -> dict:
    """Paired t-test for two score arrays on the same test cases."""
    a = np.array(scores_a)
    b = np.array(scores_b)
    diff = a - b

    n = len(diff)
    if n < 2:
        return {
            "t_statistic": 0.0,
            "p_value": 1.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "significant": False,
        }

    t_stat, p_val = stats.ttest_rel(a, b)

    mean_diff = np.mean(diff)
    se = stats.sem(diff)
    ci = stats.t.interval(1 - alpha, df=n - 1, loc=mean_diff, scale=se)

    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_val),
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
        "significant": p_val < alpha,
    }


def wilcoxon_test(scores_a: list[float], scores_b: list[float], alpha: float = 0.05) -> dict:
    """Wilcoxon signed-rank test (non-parametric alternative)."""
    a = np.array(scores_a)
    b = np.array(scores_b)
    diff = a - b

    # Remove zero differences
    nonzero = diff[diff != 0]
    if len(nonzero) < 2:
        return {"statistic": 0.0, "p_value": 1.0, "significant": False}

    stat, p_val = stats.wilcoxon(nonzero)
    return {
        "statistic": float(stat),
        "p_value": float(p_val),
        "significant": p_val < alpha,
    }


def cohens_d(scores_a: list[float], scores_b: list[float]) -> float:
    """Cohen's d effect size for paired samples."""
    a = np.array(scores_a)
    b = np.array(scores_b)
    diff = a - b
    d_std = np.std(diff, ddof=1)
    if d_std == 0:
        return 0.0
    return float(np.mean(diff) / d_std)


def bonferroni_correction(p_values: list[float], alpha: float = 0.05) -> list[dict]:
    """Apply Bonferroni correction for multiple comparisons."""
    m = len(p_values)
    adjusted_alpha = alpha / m if m > 0 else alpha
    return [
        {
            "original_p": p,
            "adjusted_p": min(p * m, 1.0),
            "adjusted_alpha": adjusted_alpha,
            "significant": p < adjusted_alpha,
        }
        for p in p_values
    ]


def compare_languages(
    scores: dict[str, dict[str, list[float]]],
    lang_a: str,
    lang_b: str,
    dimensions: list[str],
    alpha: float = 0.05,
) -> list[ComparisonResult]:
    """
    Compare two languages across all scoring dimensions.

    Args:
        scores: {language: {dimension: [scores_per_test_case]}}
        lang_a: first language code
        lang_b: second language code
        dimensions: list of dimension names
        alpha: significance level

    Returns:
        List of ComparisonResult per dimension
    """
    results = []
    p_values = []

    for dim in dimensions:
        a_scores = scores[lang_a][dim]
        b_scores = scores[lang_b][dim]
        n = min(len(a_scores), len(b_scores))
        a_scores = a_scores[:n]
        b_scores = b_scores[:n]

        ttest = paired_ttest(a_scores, b_scores, alpha)
        d = cohens_d(a_scores, b_scores)
        p_values.append(ttest["p_value"])

        results.append(
            ComparisonResult(
                language_a=lang_a,
                language_b=lang_b,
                dimension=dim,
                mean_a=float(np.mean(a_scores)),
                mean_b=float(np.mean(b_scores)),
                mean_diff=float(np.mean(a_scores) - np.mean(b_scores)),
                std_a=float(np.std(a_scores, ddof=1)) if n > 1 else 0.0,
                std_b=float(np.std(b_scores, ddof=1)) if n > 1 else 0.0,
                t_statistic=ttest["t_statistic"],
                p_value=ttest["p_value"],
                cohens_d=d,
                ci_lower=ttest["ci_lower"],
                ci_upper=ttest["ci_upper"],
                statistically_significant=ttest["significant"],
                n_samples=n,
            )
        )

    # Apply Bonferroni correction
    corrected = bonferroni_correction(p_values, alpha)
    for i, result in enumerate(results):
        result.statistically_significant = corrected[i]["significant"]
        result.p_value = corrected[i]["adjusted_p"]

    return results


def summarize_language(
    scores: dict[str, list[float]],
    language: str,
    weights: dict[str, float],
) -> LanguageSummary:
    """Summarize a single language's performance across all dimensions."""
    dimension_means = {}
    dimension_stds = {}

    for dim, vals in scores.items():
        arr = np.array(vals)
        dimension_means[dim] = float(np.mean(arr))
        dimension_stds[dim] = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0

    # Composite scores per test case
    n = min(len(v) for v in scores.values())
    composites = []
    for i in range(n):
        c = sum(scores[dim][i] * weights[dim] for dim in weights)
        composites.append(c)

    composites_arr = np.array(composites)

    return LanguageSummary(
        language=language,
        n_cases=n,
        composite_mean=float(np.mean(composites_arr)),
        composite_std=float(np.std(composites_arr, ddof=1)) if n > 1 else 0.0,
        dimension_means=dimension_means,
        dimension_stds=dimension_stds,
    )
