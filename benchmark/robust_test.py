"""Robust benchmark with multiple trials and code execution verification."""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path

TESTS = [
    # --- CODING (with code execution) ---
    {
        "id": "code-lru",
        "category": "coding",
        "en": "Write a Python function `lru_cache(capacity)` that returns get/put functions implementing an LRU cache with O(1) operations. The get(key) returns -1 if not found. The put(key, value) evicts least recently used when at capacity. Do NOT use functools. Print nothing. Only define the function.",
        "ko": "O(1) 연산으로 LRU 캐시를 구현하는 Python 함수 `lru_cache(capacity)`를 작성해주세요. get/put 함수를 반환해야 합니다. get(key)는 없으면 -1 반환. put(key, value)는 용량 초과 시 가장 오래된 항목 제거. functools 사용 금지. 출력 없이 함수만 정의.",
        "test_code": """
get, put = lru_cache(2)
put(1, 1)
put(2, 2)
assert get(1) == 1
put(3, 3)
assert get(2) == -1
put(4, 4)
assert get(1) == -1
assert get(3) == 3
assert get(4) == 4
print("PASS")
""",
    },
    {
        "id": "code-merge-intervals",
        "category": "coding",
        "en": "Write a Python function `merge_intervals(intervals)` that takes a list of [start, end] intervals and returns merged overlapping intervals sorted by start. Print nothing. Only define the function.",
        "ko": "겹치는 구간을 병합하는 Python 함수 `merge_intervals(intervals)`를 작성해주세요. [start, end] 리스트를 받아 병합된 구간을 start 기준 정렬하여 반환. 출력 없이 함수만 정의.",
        "test_code": """
assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
assert merge_intervals([[1,4],[4,5]]) == [[1,5]]
assert merge_intervals([]) == []
assert merge_intervals([[1,1]]) == [[1,1]]
print("PASS")
""",
    },
    {
        "id": "code-valid-parens",
        "category": "coding",
        "en": "Write a Python function `is_valid(s)` that checks if a string of brackets '()[]{}' is valid. Return True if valid, False otherwise. Print nothing. Only define the function.",
        "ko": "괄호 문자열 '()[]{}' 이 유효한지 확인하는 Python 함수 `is_valid(s)`를 작성해주세요. 유효하면 True, 아니면 False 반환. 출력 없이 함수만 정의.",
        "test_code": """
assert is_valid("()") == True
assert is_valid("()[]{}") == True
assert is_valid("(]") == False
assert is_valid("([)]") == False
assert is_valid("{[]}") == True
assert is_valid("") == True
assert is_valid("(") == False
print("PASS")
""",
    },
    {
        "id": "code-twosum",
        "category": "coding",
        "en": "Write a Python function `two_sum(nums, target)` that returns indices of two numbers that add up to target. Assume exactly one solution exists. Use O(n) time. Print nothing. Only define the function.",
        "ko": "두 수의 합이 target이 되는 인덱스를 반환하는 Python 함수 `two_sum(nums, target)`을 작성해주세요. 정확히 하나의 해가 존재한다고 가정. O(n) 시간. 출력 없이 함수만 정의.",
        "test_code": """
r = two_sum([2,7,11,15], 9)
assert sorted(r) == [0,1]
r = two_sum([3,2,4], 6)
assert sorted(r) == [1,2]
r = two_sum([3,3], 6)
assert sorted(r) == [0,1]
print("PASS")
""",
    },
    {
        "id": "code-bst",
        "category": "coding",
        "en": "Write a Python class `BST` with methods insert(val), search(val)->bool, and inorder()->list. The tree should not allow duplicates (ignore duplicate inserts). Print nothing. Only define the class.",
        "ko": "Python 클래스 `BST`를 작성해주세요. insert(val), search(val)->bool, inorder()->list 메서드 포함. 중복 삽입은 무시. 출력 없이 클래스만 정의.",
        "test_code": """
t = BST()
for v in [5,3,7,1,4,6,8]:
    t.insert(v)
assert t.search(4) == True
assert t.search(9) == False
assert t.inorder() == [1,3,4,5,6,7,8]
t.insert(5)
assert t.inorder() == [1,3,4,5,6,7,8]
print("PASS")
""",
    },
    # --- LLM-JUDGE ONLY ---
    {
        "id": "api-fastapi",
        "category": "api",
        "en": "Write a FastAPI POST endpoint /users that accepts JSON {name: str, email: str, password: str}, validates with Pydantic v2, hashes password with hashlib, and returns {id: int, name: str, email: str}. Include 422 validation error handling.",
        "ko": "FastAPI POST 엔드포인트 /users를 작성해주세요. JSON {name: str, email: str, password: str}을 받아 Pydantic v2로 검증하고, hashlib으로 비밀번호 해시하고, {id: int, name: str, email: str}을 반환. 422 검증 에러 핸들링 포함.",
    },
    {
        "id": "debug-race",
        "category": "debug",
        "en": "Find and fix the race condition bug:\n```python\nimport asyncio\ncounter = 0\nasync def inc():\n    global counter\n    t = counter\n    await asyncio.sleep(0.01)\n    counter = t + 1\nasync def main():\n    await asyncio.gather(*[inc() for _ in range(100)])\n    print(counter)  # should be 100\nasyncio.run(main())\n```\nExplain the bug and provide fixed code.",
        "ko": "경쟁 조건 버그를 찾아서 수정해주세요:\n```python\nimport asyncio\ncounter = 0\nasync def inc():\n    global counter\n    t = counter\n    await asyncio.sleep(0.01)\n    counter = t + 1\nasync def main():\n    await asyncio.gather(*[inc() for _ in range(100)])\n    print(counter)  # 100이어야 함\nasyncio.run(main())\n```\n버그 설명과 수정된 코드를 제공해주세요.",
    },
    {
        "id": "arch-singleton",
        "category": "arch",
        "en": "Implement a thread-safe Singleton pattern in Python that supports lazy initialization, works with inheritance, and can be reset for testing. Provide working code with usage example.",
        "ko": "Python으로 스레드 안전한 싱글톤 패턴을 구현해주세요. 지연 초기화 지원, 상속과 호환, 테스트용 리셋 가능. 동작하는 코드와 사용 예시를 제공해주세요.",
    },
    {
        "id": "arch-observer",
        "category": "arch",
        "en": "Implement the Observer pattern in Python with an EventEmitter class supporting on(event, callback), off(event, callback), and emit(event, *args). Support multiple listeners per event and wildcard '*' events. Provide working code.",
        "ko": "Python으로 Observer 패턴을 구현해주세요. EventEmitter 클래스에 on(event, callback), off(event, callback), emit(event, *args) 지원. 이벤트당 여러 리스너와 와일드카드 '*' 이벤트 지원. 동작하는 코드 제공.",
    },
    {
        "id": "api-websocket",
        "category": "api",
        "en": "Write a Python asyncio WebSocket echo server using the websockets library. It should: accept connections on port 8765, echo back received messages in uppercase, handle disconnections gracefully, and log connections/disconnections. Provide complete runnable code.",
        "ko": "websockets 라이브러리를 사용하여 Python asyncio WebSocket 에코 서버를 작성해주세요. 포트 8765에서 연결 수락, 받은 메시지를 대문자로 에코, 연결 해제를 graceful하게 처리, 연결/해제 로깅. 완전히 실행 가능한 코드 제공.",
    },
]

JUDGE_PROMPT = """You are a strict code reviewer. Score this response on 5 dimensions (1-5, 5=best).

## Task (English)
{task}

## Response
{response}

## Rules
- implementation_accuracy: Does the code actually work correctly for all cases?
- intent_comprehension: Did it address ALL requirements in the task?
- hallucination: Are ALL imported libraries, functions, parameters real and correct?
- code_bugs: Count actual bugs (off-by-one, missing edge cases, wrong logic)
- omission_outdated: Are any requirements missing? Any deprecated patterns?

Be STRICT. Only give 5 if truly perfect. Return ONLY JSON:
{{"implementation_accuracy": N, "intent_comprehension": N, "hallucination": N, "code_bugs": N, "omission_outdated": N}}"""

WEIGHTS = {
    "implementation_accuracy": 0.30,
    "intent_comprehension": 0.25,
    "hallucination": 0.20,
    "code_bugs": 0.15,
    "omission_outdated": 0.10,
}


def run_claude(prompt):
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120,
    )
    return r.stdout.strip()


def extract_python(text):
    import re
    m = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def run_code_test(response_text, test_code):
    """Execute generated code + test code. Returns pass/fail."""
    code = extract_python(response_text)
    if not code:
        return False, "No code block found"
    full = code + "\n" + test_code
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(full)
        f.flush()
        try:
            r = subprocess.run(
                ["python3", f.name], capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and "PASS" in r.stdout:
                return True, "PASS"
            return False, r.stderr[:200] if r.stderr else r.stdout[:200]
        except subprocess.TimeoutExpired:
            return False, "Timeout"


def judge(task_en, response):
    prompt = JUDGE_PROMPT.format(task=task_en, response=response[:3000])
    raw = run_claude(prompt)
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {k: 3 for k in WEIGHTS}


def composite(s):
    return round(sum(s.get(k, 3) * WEIGHTS[k] for k in WEIGHTS), 2)


def avg_scores(score_list):
    result = {}
    for k in WEIGHTS:
        result[k] = round(sum(s[k] for s in score_list) / len(score_list), 2)
    result["composite"] = composite(result)
    return result


def main():
    TRIALS = 3
    all_results = {"en": [], "ko": [], "ko_translated": []}
    test_details = []

    for i, test in enumerate(TESTS):
        print(f"\n{'='*50}")
        print(f"[{i+1}/{len(TESTS)}] {test['id']} ({test['category']})")
        print(f"{'='*50}")

        has_code_test = "test_code" in test
        test_detail = {"id": test["id"], "category": test["category"]}

        for mode, label in [("en", "EN"), ("ko", "KO"), ("ko_translated", "KO-tr")]:
            trial_scores = []
            code_passes = 0

            for trial in range(1, TRIALS + 1):
                prompt = test["en"] if mode == "en" else test["ko"]

                # For translated mode, translate first
                if mode == "ko_translated":
                    translated = run_claude(f"Translate to English. Output ONLY the translation:\n\n{test['ko']}")
                    prompt = translated

                response = run_claude(prompt)

                # Code execution test
                if has_code_test:
                    passed, msg = run_code_test(response, test["test_code"])
                    if passed:
                        code_passes += 1
                    # Override implementation_accuracy based on execution
                    scores = judge(test["en"], response)
                    if passed:
                        scores["implementation_accuracy"] = max(scores["implementation_accuracy"], 5)
                        scores["code_bugs"] = max(scores["code_bugs"], 4)
                    else:
                        scores["implementation_accuracy"] = min(scores["implementation_accuracy"], 2)
                else:
                    scores = judge(test["en"], response)

                trial_scores.append(scores)
                print(f"  {label} trial {trial}: {composite(scores):.2f}" +
                      (f" [exec:{'PASS' if has_code_test and passed else 'N/A' if not has_code_test else 'FAIL'}]" if True else ""))

            avg = avg_scores(trial_scores)
            all_results[mode].append(avg)
            test_detail[mode] = avg["composite"]
            if has_code_test:
                test_detail[f"{mode}_exec"] = f"{code_passes}/{TRIALS}"

            print(f"  {label} avg: {avg['composite']:.2f}" +
                  (f" (exec: {code_passes}/{TRIALS})" if has_code_test else ""))

        test_details.append(test_detail)

    # Summary
    print(f"\n{'='*60}")
    print("FINAL RESULTS (10 tests × 3 trials)")
    print(f"{'='*60}")

    summary = {}
    for mode, label in [("en", "EN-native"), ("ko", "KO-native"), ("ko_translated", "KO-translated")]:
        s = avg_scores(all_results[mode])
        summary[mode] = s
        print(f"\n{label}:")
        for k in WEIGHTS:
            print(f"  {k:30s} {s[k]:.2f}")
        print(f"  {'COMPOSITE':30s} {s['composite']:.2f}")

    print(f"\n{'='*60}")
    print("PER-TEST COMPOSITE SCORES")
    print(f"{'='*60}")
    print(f"{'Test':<25} {'EN':>8} {'KO':>8} {'KO-tr':>8}")
    print("-" * 52)
    for td in test_details:
        print(f"{td['id']:<25} {td['en']:>8.2f} {td['ko']:>8.2f} {td['ko_translated']:>8.2f}")

    # Save
    out = {"summary": summary, "per_test": test_details}
    out_path = Path("benchmark/results/robust_test_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
