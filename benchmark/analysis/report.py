from __future__ import annotations

"""Report generation for benchmark results."""

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from .statistics import ComparisonResult, LanguageSummary

LANG_LABELS = {"en": "English", "ko": "Korean", "ja": "Japanese", "zh": "Chinese"}

MARKDOWN_TEMPLATE = Template("""# Multilingual LLM Accuracy Benchmark Report

**Generated:** {{ generated_at }}
**Model:** {{ model }}
**Trials per case:** {{ trials }}
**Test cases:** {{ n_cases }}

---

## Executive Summary

{% for s in summaries %}
- **{{ lang_label(s.language) }}**: Composite {{ "%.2f"|format(s.composite_mean) }} ± {{ "%.2f"|format(s.composite_std) }} (n={{ s.n_cases }})
{% endfor %}

{% if winner %}
**Best performing language:** {{ lang_label(winner.language) }} ({{ "%.2f"|format(winner.composite_mean) }})
{% endif %}

---

## Per-Dimension Scores

| Dimension | {% for s in summaries %}{{ lang_label(s.language) }} | {% endfor %}
|-----------|{% for s in summaries %}--------|{% endfor %}
{% for dim in dimensions %}| {{ dim_label(dim) }} | {% for s in summaries %}{{ "%.2f"|format(s.dimension_means[dim]) }} ± {{ "%.2f"|format(s.dimension_stds[dim]) }} | {% endfor %}
{% endfor %}

---

## Statistical Comparisons

{% for comparison in comparisons %}
### {{ lang_label(comparison[0].language_a) }} vs {{ lang_label(comparison[0].language_b) }}

| Dimension | Δ Mean | Cohen's d | p-value | Significant |
|-----------|--------|-----------|---------|-------------|
{% for r in comparison %}| {{ dim_label(r.dimension) }} | {{ "%+.2f"|format(r.mean_diff) }} | {{ "%.2f"|format(r.cohens_d) }} | {{ "%.4f"|format(r.p_value) }} | {{ "✓" if r.statistically_significant else "✗" }} |
{% endfor %}

{% endfor %}

---

## Effect Size Interpretation

| Cohen's d | Interpretation |
|-----------|---------------|
| < 0.2 | Negligible |
| 0.2 - 0.5 | Small |
| 0.5 - 0.8 | Medium |
| > 0.8 | Large |

---

## Charts

{% for chart in chart_paths %}
![{{ chart.stem }}]({{ chart.name }})
{% endfor %}

---

## Methodology

- **Scoring scale:** 1-5 per dimension (5 = best)
- **Composite formula:** impl×0.30 + intent×0.25 + hallucination×0.20 + bugs×0.15 + omission×0.10
- **Statistical tests:** Paired t-test with Bonferroni correction (α=0.05)
- **Judge:** LLM-as-judge evaluating in English to avoid language bias
- **Trials:** {{ trials }} per test case per language (scores averaged)
""")

DIM_LABELS = {
    "implementation_accuracy": "Impl. Accuracy",
    "intent_comprehension": "Intent Comprehension",
    "hallucination": "Hallucination",
    "code_bugs": "Code Bugs",
    "omission_outdated": "Omission/Outdated",
}


def _lang_label(code: str) -> str:
    return LANG_LABELS.get(code, code)


def _dim_label(name: str) -> str:
    return DIM_LABELS.get(name, name)


def generate_markdown_report(
    summaries: list[LanguageSummary],
    comparisons: list[list[ComparisonResult]],
    dimensions: list[str],
    chart_paths: list[Path],
    model: str,
    trials: int,
    n_cases: int,
) -> str:
    """Generate a Markdown benchmark report."""
    winner = max(summaries, key=lambda s: s.composite_mean) if summaries else None

    return MARKDOWN_TEMPLATE.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model=model,
        trials=trials,
        n_cases=n_cases,
        summaries=summaries,
        winner=winner,
        dimensions=dimensions,
        comparisons=comparisons,
        chart_paths=chart_paths,
        lang_label=_lang_label,
        dim_label=_dim_label,
    )


def save_report(
    summaries: list[LanguageSummary],
    comparisons: list[list[ComparisonResult]],
    dimensions: list[str],
    chart_paths: list[Path],
    model: str,
    trials: int,
    n_cases: int,
    output_dir: Path,
) -> Path:
    """Generate and save the benchmark report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    md = generate_markdown_report(
        summaries, comparisons, dimensions, chart_paths, model, trials, n_cases
    )

    report_path = output_dir / "REPORT.md"
    report_path.write_text(md, encoding="utf-8")
    return report_path
