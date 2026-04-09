from __future__ import annotations

import asyncio
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    input_data: str
    expected: str
    actual: str
    passed: bool


@dataclass
class ExecutionResult:
    test_case_id: str
    code_extracted: bool
    code: str
    test_results: list[TestResult]
    compilation_error: str | None
    runtime_error: str | None


_CODE_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.DOTALL)


def _extract_code(response_text: str) -> str | None:
    match = _CODE_BLOCK_RE.search(response_text)
    if match:
        return match.group(1).strip()
    return None


async def execute_code(
    test_case_id: str,
    response_text: str,
    validation_cases: list[dict],
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """Extract Python code from response and run it against validation test cases.

    Each validation case is a dict with keys:
        - ``input_data``: string representation of input (may be empty)
        - ``expected``: expected stdout output (stripped)
        - ``setup``: optional code prepended before the extracted code
    """
    code = _extract_code(response_text)
    if code is None:
        return ExecutionResult(
            test_case_id=test_case_id,
            code_extracted=False,
            code="",
            test_results=[
                TestResult(
                    input_data=vc.get("input_data", ""),
                    expected=vc.get("expected", ""),
                    actual="",
                    passed=False,
                )
                for vc in validation_cases
            ],
            compilation_error="Could not extract Python code block from response",
            runtime_error=None,
        )

    test_results: list[TestResult] = []
    compilation_error: str | None = None
    runtime_error: str | None = None

    # Syntax check first
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as exc:
        compilation_error = f"SyntaxError: {exc}"
        return ExecutionResult(
            test_case_id=test_case_id,
            code_extracted=True,
            code=code,
            test_results=[
                TestResult(
                    input_data=vc.get("input_data", ""),
                    expected=vc.get("expected", ""),
                    actual="",
                    passed=False,
                )
                for vc in validation_cases
            ],
            compilation_error=compilation_error,
            runtime_error=None,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        for vc in validation_cases:
            input_data: str = vc.get("input_data", "")
            expected: str = vc.get("expected", "").strip()
            setup: str = vc.get("setup", "")

            script_content = (setup + "\n" if setup else "") + code
            script_path = Path(tmpdir) / "solution.py"
            script_path.write_text(script_content, encoding="utf-8")

            try:
                proc = await asyncio.create_subprocess_exec(
                    "python3",
                    str(script_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(input=input_data.encode() if input_data else None),
                        timeout=timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.communicate()
                    test_results.append(
                        TestResult(
                            input_data=input_data,
                            expected=expected,
                            actual="",
                            passed=False,
                        )
                    )
                    runtime_error = runtime_error or f"Timeout after {timeout_seconds}s"
                    continue

                actual = stdout_bytes.decode(errors="replace").strip()
                stderr_text = stderr_bytes.decode(errors="replace").strip()

                if proc.returncode != 0 and stderr_text:
                    runtime_error = runtime_error or stderr_text

                test_results.append(
                    TestResult(
                        input_data=input_data,
                        expected=expected,
                        actual=actual,
                        passed=(actual == expected and proc.returncode == 0),
                    )
                )

            except Exception as exc:  # noqa: BLE001
                runtime_error = runtime_error or str(exc)
                test_results.append(
                    TestResult(
                        input_data=input_data,
                        expected=expected,
                        actual="",
                        passed=False,
                    )
                )

    return ExecutionResult(
        test_case_id=test_case_id,
        code_extracted=True,
        code=code,
        test_results=test_results,
        compilation_error=compilation_error,
        runtime_error=runtime_error,
    )
