from __future__ import annotations

"""CLI entry point for multilingual LLM accuracy benchmark."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
TEST_CASES_DIR = BASE_DIR / "test_cases"
RESULTS_DIR = BASE_DIR / "results"

DIMENSIONS = [
    "implementation_accuracy",
    "intent_comprehension",
    "hallucination",
    "code_bugs",
    "omission_outdated",
]


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_test_cases(category: str | None = None) -> list[dict]:
    """Load test cases from YAML files."""
    cases = []
    categories = [category] if category else ["coding", "api_usage", "debugging", "architecture"]

    for cat in categories:
        cat_dir = TEST_CASES_DIR / cat
        if not cat_dir.exists():
            console.print(f"[yellow]Warning: category dir {cat_dir} not found[/yellow]")
            continue
        for f in sorted(cat_dir.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                cases.append(yaml.safe_load(fh))

    return cases


def save_results(results: list[dict], output_dir: Path) -> Path:
    """Save raw results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "raw_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return path


@click.group()
def main():
    """Multilingual LLM Accuracy Benchmark CLI."""
    pass


@main.command()
@click.option("--languages", default="en,ko,ja", help="Comma-separated language codes")
@click.option("--model", default=None, help="Model to benchmark")
@click.option("--trials", default=3, type=int, help="Trials per test case")
@click.option("--category", default=None, help="Single category to run")
@click.option("--mode", default="native", type=click.Choice(["native", "translated"]))
@click.option("--output-dir", default=None, help="Output directory for results")
def run(languages: str, model: str | None, trials: int, category: str | None, mode: str, output_dir: str | None):
    """Run the benchmark suite."""
    config = load_config()
    lang_list = [l.strip() for l in languages.split(",")]
    model = model or config["benchmark"]["default_model"]

    if output_dir:
        out_dir = Path(output_dir)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_dir = RESULTS_DIR / timestamp

    test_cases = load_test_cases(category)
    if not test_cases:
        console.print("[red]No test cases found![/red]")
        return

    console.print(f"\n[bold]Multilingual LLM Benchmark[/bold]")
    console.print(f"  Model:      {model}")
    console.print(f"  Languages:  {', '.join(lang_list)}")
    console.print(f"  Test cases: {len(test_cases)}")
    console.print(f"  Trials:     {trials}")
    console.print(f"  Mode:       {mode}")
    console.print(f"  Output:     {out_dir}\n")

    total_calls = len(test_cases) * len(lang_list) * trials
    console.print(f"  Total API calls: {total_calls}\n")

    asyncio.run(_run_benchmark(test_cases, lang_list, model, trials, mode, config, out_dir))


async def _run_benchmark(
    test_cases: list[dict],
    languages: list[str],
    model: str,
    trials: int,
    mode: str,
    config: dict,
    output_dir: Path,
):
    from .runners.claude_runner import ClaudeRunner
    from .runners.execution_runner import execute_code
    from .runners.judge_runner import JudgeRunner
    from .scoring.aggregator import aggregate

    runner = ClaudeRunner(model=model, temperature=0.0, max_tokens=config["benchmark"]["max_tokens"])
    exec_timeout = config["execution"]["timeout_seconds"]
    judge = JudgeRunner(
        model=config["judge"]["model"],
        evaluations=config["judge"]["evaluations_per_response"],
        variance_threshold=config["judge"]["variance_threshold"],
    )

    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running benchmark...", total=len(test_cases) * len(languages))

        for tc in test_cases:
            for lang in languages:
                if lang not in tc.get("prompts", {}):
                    progress.advance(task)
                    continue

                progress.update(task, description=f"[cyan]{tc['id']}[/cyan] ({lang})")

                prompt = tc["prompts"][lang]

                # If translated mode, translate non-English prompts first
                if mode == "translated" and lang != "en":
                    from .runners.claude_runner import ClaudeRunner as TR
                    translator = TR(
                        model=config["translation"]["model"],
                        temperature=0.0,
                        max_tokens=4096,
                    )
                    trans_result = await translator.run_single(
                        prompt=f"Translate this to English. Output ONLY the translation:\n\n{prompt}",
                        model=config["translation"]["model"],
                        test_case_id=tc["id"],
                        language=lang,
                        trial=0,
                    )
                    if trans_result.response_text:
                        prompt = trans_result.response_text

                # Run trials
                raw_results = await runner.run_test_case(
                    test_case={"id": tc["id"], "prompts": {lang: prompt}},
                    language=lang,
                    model=model,
                    trials=trials,
                )

                # Score each trial
                for raw in raw_results:
                    scores = {}

                    # Automated scoring for code execution tasks
                    if tc.get("validation", {}).get("type") in ("code_execution", "hybrid"):
                        exec_result = await execute_code(
                            tc["id"], raw.response_text,
                            tc["validation"].get("test_cases", []),
                            exec_timeout,
                        )
                        from .scoring.automated import score_execution
                        auto_scores = score_execution(exec_result)
                        scores.update(auto_scores)

                    # LLM judge scoring
                    en_prompt = tc["prompts"].get("en", prompt)
                    judge_scores = await judge.evaluate(en_prompt, raw.response_text)
                    # Merge: auto scores take priority for dims they cover
                    for dim in DIMENSIONS:
                        if dim not in scores:
                            scores[dim] = judge_scores.get(dim, 3)

                    all_results.append({
                        "test_case_id": tc["id"],
                        "category": tc["category"],
                        "language": lang,
                        "trial": raw.trial,
                        "model": model,
                        "mode": mode,
                        "scores": scores,
                        "response_length": len(raw.response_text),
                        "latency_ms": raw.latency_ms,
                        "tokens_input": raw.tokens_input,
                        "tokens_output": raw.tokens_output,
                    })

                progress.advance(task)

    # Save raw results
    results_path = save_results(all_results, output_dir)
    console.print(f"\n[green]Results saved to {results_path}[/green]")

    # Run analysis
    _analyze_results(all_results, languages, output_dir)


def _analyze_results(results: list[dict], languages: list[str], output_dir: Path):
    """Analyze and visualize results."""
    from .analysis.statistics import compare_languages, summarize_language
    from .analysis.visualization import generate_all_charts
    from .analysis.report import save_report

    config = load_config()
    weights = config["scoring"]["weights"]

    # Organize scores: {lang: {dim: [scores]}}
    scores_by_lang: dict[str, dict[str, list[float]]] = {}
    test_case_ids = []
    seen_ids = set()

    for r in results:
        lang = r["language"]
        if lang not in scores_by_lang:
            scores_by_lang[lang] = {d: [] for d in DIMENSIONS}

        # Average across trials for same test case
        tc_id = r["test_case_id"]
        if tc_id not in seen_ids:
            seen_ids.add(tc_id)
            test_case_ids.append(tc_id)

    # Aggregate per test case (average trials)
    for lang in languages:
        if lang not in scores_by_lang:
            continue
        scores_by_lang[lang] = {d: [] for d in DIMENSIONS}

        for tc_id in test_case_ids:
            trial_results = [r for r in results if r["test_case_id"] == tc_id and r["language"] == lang]
            if not trial_results:
                for d in DIMENSIONS:
                    scores_by_lang[lang][d].append(3.0)  # default
                continue

            for d in DIMENSIONS:
                avg = sum(r["scores"].get(d, 3) for r in trial_results) / len(trial_results)
                scores_by_lang[lang][d].append(avg)

    # Generate summaries
    summaries = []
    for lang in languages:
        if lang in scores_by_lang:
            summaries.append(summarize_language(scores_by_lang[lang], lang, weights))

    # Statistical comparisons (all pairs)
    comparisons = []
    for i, la in enumerate(languages):
        for lb in languages[i + 1:]:
            if la in scores_by_lang and lb in scores_by_lang:
                comp = compare_languages(scores_by_lang, la, lb, DIMENSIONS)
                comparisons.append(comp)

    # Charts
    chart_paths = generate_all_charts(
        scores_by_lang, summaries, DIMENSIONS, test_case_ids, output_dir / "charts"
    )

    # Report
    report_path = save_report(
        summaries, comparisons, DIMENSIONS, chart_paths,
        model=results[0]["model"] if results else "unknown",
        trials=max(r["trial"] for r in results) if results else 0,
        n_cases=len(test_case_ids),
        output_dir=output_dir,
    )

    # Print summary table
    table = Table(title="Benchmark Results Summary")
    table.add_column("Language", style="bold")
    table.add_column("Composite", justify="center")
    for d in DIMENSIONS:
        label = d.replace("_", " ").title()[:15]
        table.add_column(label, justify="center")

    for s in summaries:
        row = [
            s.language.upper(),
            f"{s.composite_mean:.2f}",
        ]
        for d in DIMENSIONS:
            row.append(f"{s.dimension_means[d]:.2f}")
        table.add_row(*row)

    console.print(table)
    console.print(f"\n[green]Report saved to {report_path}[/green]")
    console.print(f"[green]Charts saved to {output_dir / 'charts'}[/green]")


@main.command()
@click.option("--results-dir", required=True, help="Directory with raw_results.json")
def analyze(results_dir: str):
    """Analyze existing results."""
    rdir = Path(results_dir)
    results_file = rdir / "raw_results.json"
    if not results_file.exists():
        console.print(f"[red]{results_file} not found[/red]")
        return

    with open(results_file, encoding="utf-8") as f:
        results = json.load(f)

    languages = sorted(set(r["language"] for r in results))
    _analyze_results(results, languages, rdir)


@main.command()
@click.option("--results-dir", required=True, help="Directory with raw_results.json")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "html"]))
def report(results_dir: str, fmt: str):
    """Generate report from existing results."""
    rdir = Path(results_dir)
    results_file = rdir / "raw_results.json"
    if not results_file.exists():
        console.print(f"[red]{results_file} not found[/red]")
        return

    with open(results_file, encoding="utf-8") as f:
        results = json.load(f)

    languages = sorted(set(r["language"] for r in results))
    _analyze_results(results, languages, rdir)

    if fmt == "html":
        report_path = rdir / "REPORT.md"
        if report_path.exists():
            try:
                import markdown
                md_text = report_path.read_text(encoding="utf-8")
                html = markdown.markdown(md_text, extensions=["tables"])
                html_path = rdir / "REPORT.html"
                html_path.write_text(
                    f"<html><head><style>body{{font-family:sans-serif;max-width:900px;margin:auto;padding:2rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;text-align:center}}th{{background:#f5f5f5}}</style></head><body>{html}</body></html>",
                    encoding="utf-8",
                )
                console.print(f"[green]HTML report saved to {html_path}[/green]")
            except ImportError:
                console.print("[yellow]Install 'markdown' package for HTML output: pip install markdown[/yellow]")


@main.command()
def list_cases():
    """List all available test cases."""
    cases = load_test_cases()
    table = Table(title=f"Test Cases ({len(cases)} total)")
    table.add_column("ID", style="bold")
    table.add_column("Category")
    table.add_column("Difficulty")
    table.add_column("Languages")

    for tc in cases:
        langs = ", ".join(tc.get("prompts", {}).keys())
        table.add_row(tc["id"], tc["category"], tc.get("difficulty", "?"), langs)

    console.print(table)


if __name__ == "__main__":
    main()
