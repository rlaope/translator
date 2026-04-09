from __future__ import annotations

from ..runners.execution_runner import ExecutionResult


def _pass_rate_to_score(pass_rate: float) -> float:
    """Map a pass rate in [0.0, 1.0] to a 1-5 score."""
    if pass_rate >= 1.0:
        return 5.0
    if pass_rate >= 0.75:
        return 4.0
    if pass_rate >= 0.50:
        return 3.0
    if pass_rate >= 0.25:
        return 2.0
    return 1.0


def score_execution(result: ExecutionResult) -> dict[str, float]:
    """Return partial scores for implementation_accuracy and code_bugs.

    Scores are on the 1-5 scale used throughout the benchmark.

    Returns
    -------
    dict with keys ``implementation_accuracy`` and ``code_bugs``.
    """
    # --- implementation_accuracy ---
    if not result.code_extracted:
        implementation_accuracy = 1.0
    elif result.compilation_error is not None:
        # Code was extracted but did not compile
        implementation_accuracy = 1.0
    elif not result.test_results:
        # No validation cases to evaluate — partial credit
        implementation_accuracy = 3.0
    else:
        passed = sum(1 for tr in result.test_results if tr.passed)
        total = len(result.test_results)
        pass_rate = passed / total
        implementation_accuracy = _pass_rate_to_score(pass_rate)

    # --- code_bugs ---
    if not result.code_extracted:
        code_bugs = 1.0
    elif result.compilation_error is not None:
        code_bugs = 1.0
    elif result.runtime_error is not None:
        # Runtime errors that affected at least some test cases
        failed = sum(1 for tr in result.test_results if not tr.passed)
        if failed == 0:
            # Error occurred but all tests still passed (e.g. stderr noise)
            code_bugs = 4.0
        else:
            total = len(result.test_results) or 1
            fail_rate = failed / total
            if fail_rate <= 0.25:
                code_bugs = 3.0
            elif fail_rate <= 0.50:
                code_bugs = 2.0
            else:
                code_bugs = 1.0
    elif not result.test_results:
        code_bugs = 3.0
    else:
        passed = sum(1 for tr in result.test_results if tr.passed)
        total = len(result.test_results)
        pass_rate = passed / total
        # Bugs correlate inversely with pass rate
        code_bugs = _pass_rate_to_score(pass_rate)

    return {
        "implementation_accuracy": implementation_accuracy,
        "code_bugs": code_bugs,
    }
