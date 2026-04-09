"""Quick before/after benchmark using claude CLI."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

TESTS = [
    {
        "id": "coding-1",
        "en": "Write a Python function that implements an LRU cache with O(1) get and put operations. Include type hints and handle edge cases like capacity=0.",
        "ko": "O(1) get과 put 연산을 가진 LRU 캐시를 Python 함수로 구현해주세요. 타입 힌트를 포함하고 capacity=0 같은 엣지 케이스도 처리해주세요.",
    },
    {
        "id": "coding-2",
        "en": "Write a Python async function that implements a token bucket rate limiter. It should support configurable rate and burst size, and use asyncio.Lock for thread safety.",
        "ko": "토큰 버킷 레이트 리미터를 Python async 함수로 구현해주세요. rate와 burst size를 설정할 수 있어야 하고, asyncio.Lock으로 thread safety를 보장해주세요.",
    },
    {
        "id": "api-1",
        "en": "Write a FastAPI endpoint that accepts a JSON body with user registration data, validates it with Pydantic v2, hashes the password with bcrypt, and returns the created user. Include proper error handling and HTTP status codes.",
        "ko": "사용자 등록 데이터를 JSON body로 받는 FastAPI 엔드포인트를 작성해주세요. Pydantic v2로 검증하고, bcrypt로 비밀번호를 해시하고, 생성된 사용자를 반환해주세요. 적절한 에러 핸들링과 HTTP 상태 코드를 포함해주세요.",
    },
    {
        "id": "debug-1",
        "en": "Find and fix the bug in this Python code that causes a race condition:\n```python\nimport asyncio\n\ncounter = 0\n\nasync def increment():\n    global counter\n    temp = counter\n    await asyncio.sleep(0.01)\n    counter = temp + 1\n\nasync def main():\n    tasks = [increment() for _ in range(100)]\n    await asyncio.gather(*tasks)\n    print(f'Expected 100, got {counter}')\n\nasyncio.run(main())\n```",
        "ko": "다음 Python 코드에서 경쟁 조건을 일으키는 버그를 찾아서 수정해주세요:\n```python\nimport asyncio\n\ncounter = 0\n\nasync def increment():\n    global counter\n    temp = counter\n    await asyncio.sleep(0.01)\n    counter = temp + 1\n\nasync def main():\n    tasks = [increment() for _ in range(100)]\n    await asyncio.gather(*tasks)\n    print(f'Expected 100, got {counter}')\n\nasyncio.run(main())\n```",
    },
    {
        "id": "arch-1",
        "en": "Design a circuit breaker pattern implementation in Python for microservice resilience. Include states (closed, open, half-open), configurable failure threshold, timeout, and recovery. Provide working code.",
        "ko": "마이크로서비스 복원력을 위한 서킷 브레이커 패턴을 Python으로 설계해주세요. 상태(closed, open, half-open), 설정 가능한 실패 임계값, 타임아웃, 복구를 포함해주세요. 동작하는 코드를 제공해주세요.",
    },
]

JUDGE_PROMPT = """You are an expert code reviewer. Score this AI-generated response on 5 dimensions (1-5 scale, 5=best).

## Original Task (English)
{task}

## AI Response
{response}

## Scoring Criteria
1. implementation_accuracy: Does the code work correctly? (5=all correct, 1=broken)
2. intent_comprehension: Did it understand all requirements? (5=perfect, 1=missed everything)
3. hallucination: Are all APIs/functions real? (5=none fabricated, 1=mostly fake)
4. code_bugs: How many bugs? (5=zero, 1=non-functional)
5. omission_outdated: Missing requirements or deprecated patterns? (5=none, 1=most missing)

Return ONLY valid JSON:
{{"implementation_accuracy": N, "intent_comprehension": N, "hallucination": N, "code_bugs": N, "omission_outdated": N}}"""


def run_claude(prompt: str) -> str:
    """Run a prompt through claude CLI."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout.strip()


def judge_response(task_en: str, response: str) -> dict:
    """Score a response using claude as judge."""
    prompt = JUDGE_PROMPT.format(task=task_en, response=response[:3000])
    raw = run_claude(prompt)
    # Extract JSON from response
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    # Try to parse the whole thing
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        print(f"  [warn] Could not parse judge response, using defaults")
        return {
            "implementation_accuracy": 3, "intent_comprehension": 3,
            "hallucination": 3, "code_bugs": 3, "omission_outdated": 3,
        }


WEIGHTS = {
    "implementation_accuracy": 0.30,
    "intent_comprehension": 0.25,
    "hallucination": 0.20,
    "code_bugs": 0.15,
    "omission_outdated": 0.10,
}


def composite(scores: dict) -> float:
    return sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)


def main():
    results = {"en": [], "ko": [], "ko_translated": []}

    for i, test in enumerate(TESTS):
        print(f"\n[{i+1}/{len(TESTS)}] {test['id']}")

        # 1. English native
        print("  EN-native...", end=" ", flush=True)
        t0 = time.time()
        resp_en = run_claude(test["en"])
        t_en = time.time() - t0
        scores_en = judge_response(test["en"], resp_en)
        c_en = composite(scores_en)
        results["en"].append(scores_en)
        print(f"{c_en:.2f} ({t_en:.1f}s)")

        # 2. Korean native (no translation)
        print("  KO-native...", end=" ", flush=True)
        t0 = time.time()
        resp_ko = run_claude(test["ko"])
        t_ko = time.time() - t0
        scores_ko = judge_response(test["en"], resp_ko)
        c_ko = composite(scores_ko)
        results["ko"].append(scores_ko)
        print(f"{c_ko:.2f} ({t_ko:.1f}s)")

        # 3. Korean translated (simulate plugin)
        print("  KO-translated...", end=" ", flush=True)
        t0 = time.time()
        translated = run_claude(f"Translate this Korean text to English. Output ONLY the translation:\n\n{test['ko']}")
        resp_ko_tr = run_claude(translated)
        t_tr = time.time() - t0
        scores_tr = judge_response(test["en"], resp_ko_tr)
        c_tr = composite(scores_tr)
        results["ko_translated"].append(scores_tr)
        print(f"{c_tr:.2f} ({t_tr:.1f}s)")

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    dims = list(WEIGHTS.keys())
    for mode, label in [("en", "EN-native"), ("ko", "KO-native"), ("ko_translated", "KO-translated")]:
        avg_scores = {}
        for d in dims:
            avg_scores[d] = sum(r[d] for r in results[mode]) / len(results[mode])
        avg_composite = composite(avg_scores)
        print(f"\n{label}:")
        for d in dims:
            print(f"  {d:30s} {avg_scores[d]:.2f}")
        print(f"  {'COMPOSITE':30s} {avg_composite:.2f}")

    # Output JSON for README
    summary = {}
    for mode in ["en", "ko", "ko_translated"]:
        avg = {}
        for d in dims:
            avg[d] = round(sum(r[d] for r in results[mode]) / len(results[mode]), 2)
        avg["composite"] = round(composite(avg), 2)
        summary[mode] = avg

    out_path = Path(__file__).parent / "results" / "quick_test_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
