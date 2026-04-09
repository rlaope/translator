from __future__ import annotations

"""Visualization module for benchmark results."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from .statistics import ComparisonResult, LanguageSummary

# Style
sns.set_theme(style="whitegrid", palette="muted")
LANG_COLORS = {"en": "#2196F3", "ko": "#4CAF50", "ja": "#FF9800", "zh": "#E91E63"}
LANG_LABELS = {"en": "English", "ko": "Korean", "ja": "Japanese", "zh": "Chinese"}
DIM_LABELS = {
    "implementation_accuracy": "Impl.\nAccuracy",
    "intent_comprehension": "Intent\nComprehension",
    "hallucination": "Hallucination",
    "code_bugs": "Code\nBugs",
    "omission_outdated": "Omission/\nOutdated",
}


def radar_chart(
    summaries: list[LanguageSummary],
    dimensions: list[str],
    output_path: Path,
) -> None:
    """Radar chart comparing languages across 5 scoring dimensions."""
    n_dims = len(dimensions)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    for summary in summaries:
        values = [summary.dimension_means[d] for d in dimensions]
        values += values[:1]
        color = LANG_COLORS.get(summary.language, "#999")
        label = LANG_LABELS.get(summary.language, summary.language)
        ax.plot(angles, values, "o-", linewidth=2, label=label, color=color)
        ax.fill(angles, values, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([DIM_LABELS.get(d, d) for d in dimensions], size=10)
    ax.set_ylim(0, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_title("Multilingual Performance Radar", size=14, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def box_plots(
    scores: dict[str, dict[str, list[float]]],
    dimensions: list[str],
    output_path: Path,
) -> None:
    """Box plots showing score distributions per language per dimension."""
    fig, axes = plt.subplots(1, len(dimensions), figsize=(4 * len(dimensions), 6), sharey=True)

    for i, dim in enumerate(dimensions):
        ax = axes[i] if len(dimensions) > 1 else axes
        data = []
        labels = []
        colors = []
        for lang in scores:
            data.append(scores[lang][dim])
            labels.append(LANG_LABELS.get(lang, lang))
            colors.append(LANG_COLORS.get(lang, "#999"))

        bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.6)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_title(DIM_LABELS.get(dim, dim), size=11)
        ax.set_ylim(0.5, 5.5)
        if i == 0:
            ax.set_ylabel("Score (1-5)")

    fig.suptitle("Score Distribution by Language and Dimension", size=14, y=1.02)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def heatmap(
    summaries: list[LanguageSummary],
    dimensions: list[str],
    output_path: Path,
) -> None:
    """Heatmap of Language x Dimension mean scores."""
    languages = [s.language for s in summaries]
    data = np.array([[s.dimension_means[d] for d in dimensions] for s in summaries])

    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(
        data,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        vmin=1,
        vmax=5,
        xticklabels=[DIM_LABELS.get(d, d) for d in dimensions],
        yticklabels=[LANG_LABELS.get(l, l) for l in languages],
        ax=ax,
    )
    ax.set_title("Mean Scores: Language × Dimension", size=14)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def composite_bar_chart(
    summaries: list[LanguageSummary],
    output_path: Path,
) -> None:
    """Bar chart of composite scores with error bars (95% CI)."""
    languages = [s.language for s in summaries]
    means = [s.composite_mean for s in summaries]
    stds = [s.composite_std for s in summaries]
    # 95% CI: mean ± 1.96 * std / sqrt(n)
    cis = [1.96 * s.composite_std / np.sqrt(s.n_cases) if s.n_cases > 0 else 0 for s in summaries]
    colors = [LANG_COLORS.get(l, "#999") for l in languages]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        [LANG_LABELS.get(l, l) for l in languages],
        means,
        yerr=cis,
        capsize=8,
        color=colors,
        alpha=0.8,
        edgecolor="white",
        linewidth=1.5,
    )

    for bar, mean in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{mean:.2f}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    ax.set_ylabel("Composite Score (1-5)")
    ax.set_title("Composite Score by Language (with 95% CI)", size=14)
    ax.set_ylim(0, 5.5)
    ax.axhline(y=3.0, color="gray", linestyle="--", alpha=0.5, label="Baseline (3.0)")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def delta_chart(
    scores_en: list[float],
    scores_other: list[float],
    test_case_ids: list[str],
    other_lang: str,
    output_path: Path,
) -> None:
    """Delta chart: (English - Other) score per test case, sorted."""
    deltas = [e - o for e, o in zip(scores_en, scores_other)]
    sorted_pairs = sorted(zip(deltas, test_case_ids), key=lambda x: x[0])
    sorted_deltas = [p[0] for p in sorted_pairs]
    sorted_ids = [p[1] for p in sorted_pairs]

    colors = ["#4CAF50" if d >= 0 else "#F44336" for d in sorted_deltas]

    fig, ax = plt.subplots(figsize=(12, max(6, len(sorted_ids) * 0.3)))
    ax.barh(range(len(sorted_ids)), sorted_deltas, color=colors, alpha=0.8)
    ax.set_yticks(range(len(sorted_ids)))
    ax.set_yticklabels(sorted_ids, fontsize=8)
    ax.set_xlabel("Score Delta (EN - {})".format(LANG_LABELS.get(other_lang, other_lang)))
    ax.set_title(
        "Per-Test-Case Score Delta: English vs {}".format(LANG_LABELS.get(other_lang, other_lang)),
        size=14,
    )
    ax.axvline(x=0, color="black", linewidth=0.8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_all_charts(
    scores: dict[str, dict[str, list[float]]],
    summaries: list[LanguageSummary],
    dimensions: list[str],
    test_case_ids: list[str],
    output_dir: Path,
) -> list[Path]:
    """Generate all visualization charts and return paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    # 1. Radar chart
    path = output_dir / "radar_chart.png"
    radar_chart(summaries, dimensions, path)
    generated.append(path)

    # 2. Box plots
    path = output_dir / "box_plots.png"
    box_plots(scores, dimensions, path)
    generated.append(path)

    # 3. Heatmap
    path = output_dir / "heatmap.png"
    heatmap(summaries, dimensions, path)
    generated.append(path)

    # 4. Composite bar chart
    path = output_dir / "composite_scores.png"
    composite_bar_chart(summaries, path)
    generated.append(path)

    # 5. Delta charts (EN vs each non-EN language)
    weights = {
        "implementation_accuracy": 0.30,
        "intent_comprehension": 0.25,
        "hallucination": 0.20,
        "code_bugs": 0.15,
        "omission_outdated": 0.10,
    }

    if "en" in scores:
        n = len(test_case_ids)
        en_composites = []
        for i in range(n):
            c = sum(scores["en"][d][i] * weights[d] for d in dimensions)
            en_composites.append(c)

        for lang in scores:
            if lang == "en":
                continue
            other_composites = []
            for i in range(n):
                c = sum(scores[lang][d][i] * weights[d] for d in dimensions)
                other_composites.append(c)

            path = output_dir / f"delta_en_vs_{lang}.png"
            delta_chart(en_composites, other_composites, test_case_ids, lang, path)
            generated.append(path)

    return generated
