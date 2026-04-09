# Multilingual LLM Accuracy Benchmark & Prompt Translator

Claude에 한국어/일본어 프롬프트를 입력했을 때 영어 대비 정확도가 떨어진다는 가설을 **정량적으로 검증**하고, 이를 해결하기 위한 **자동 번역 Claude Code 플러그인**을 제공합니다.

## 구성

```
translator/
├── benchmark/     # Python 벤치마크 스위트 (40개 테스트, 5개 평가 기준)
├── plugin/        # Claude Code 번역 플러그인 (UserPromptSubmit 훅)
└── docs/          # 방법론 및 채점 기준 문서
```

## 평가 기준 (5-Point Scale)

| # | 기준 | 가중치 | 측정 방법 |
|---|------|--------|-----------|
| 1 | **구현정확도** (Implementation Accuracy) | 30% | 코드 실행 테스트 |
| 2 | **의도파악** (Intent Comprehension) | 25% | LLM-as-Judge |
| 3 | **할루시네이션** (Hallucination) | 20% | API/함수 실재 검증 |
| 4 | **코드버그 발생도** (Code Bug Rate) | 15% | 자동 + LLM 혼합 |
| 5 | **누락/아웃데이트** (Omission/Outdated) | 10% | LLM-as-Judge |

**종합 점수** = `impl×0.30 + intent×0.25 + hallucination×0.20 + bugs×0.15 + omission×0.10`

## 빠른 시작

### 1. 설치

```bash
# Python 의존성
cd benchmark
pip install -e .

# Plugin 의존성
cd ../plugin
npm install
```

### 2. 벤치마크 실행

```bash
# 전체 벤치마크 (EN/KO/JA, 3회 시행)
python -m benchmark.cli run --languages en,ko,ja --trials 3

# 특정 카테고리만
python -m benchmark.cli run --category coding --languages en,ko

# 번역 모드 (플러그인 효과 검증)
python -m benchmark.cli run --languages ko,ja --mode translated --trials 3

# 테스트 케이스 목록
python -m benchmark.cli list-cases

# 기존 결과 분석
python -m benchmark.cli analyze --results-dir ./results/2026-04-09_120000

# 리포트 생성
python -m benchmark.cli report --results-dir ./results/2026-04-09_120000 --format html
```

### 3. 번역 플러그인 설치

```bash
# Claude Code에 플러그인 등록
cd plugin
claude plugin install .
```

또는 수동으로 `~/.claude/settings.json`에 훅 추가:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "node /path/to/plugin/scripts/translate-hook.mjs",
            "timeout": 8
          }
        ]
      }
    ]
  }
}
```

### 4. 플러그인 설정

환경 변수로 제어:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRANSLATOR_ENABLED` | `true` | 플러그인 활성화/비활성화 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 번역에 사용할 모델 |
| `TRANSLATOR_TIMEOUT` | `6000` | 번역 API 타임아웃 (ms) |
| `TRANSLATOR_DEBUG` | - | 설정 시 디버그 로그 출력 |

## 벤치마크 테스트 케이스

40개 테스트, 4개 카테고리 (Easy 3, Medium 4, Hard 3):

| 카테고리 | 범위 | 주제 |
|----------|------|------|
| **Coding** | TC-CODE-001~010 | 알고리즘, 자료구조, 비동기 패턴 |
| **API Usage** | TC-API-001~010 | REST, SDK, 인증, 결제, GraphQL |
| **Debugging** | TC-DEBUG-001~010 | 버그 수정, 메모리 누수, 경쟁 조건 |
| **Architecture** | TC-ARCH-001~010 | 디자인 패턴, 시스템 설계, 분산 시스템 |

## 번역 플러그인 동작 원리

```
사용자 한국어 입력
    ↓
UserPromptSubmit 훅 트리거
    ↓
Unicode 기반 언어 감지 (<1ms)
    ↓ (비영어 감지)
Claude Haiku로 영어 번역 (~2-3초)
    ↓
additionalContext로 번역 주입
    ↓
Claude가 영어 번역 기반으로 추론 → 한국어로 응답
```

핵심 특징:
- **Zero-dependency 언어 감지**: Unicode range 기반, 외부 라이브러리 불필요
- **Graceful degradation**: 번역 실패 시 원문 그대로 통과 (절대 blocking 안 함)
- **코드 보존**: 코드 블록, 파일 경로, 변수명은 번역하지 않음

## 3-Way 비교

플러그인의 실제 효과를 검증하는 3-way 비교:

| 모드 | 설명 |
|------|------|
| **EN-native** | 영어 프롬프트 → Claude |
| **KO-native** | 한국어 프롬프트 → Claude |
| **KO-translated** | 한국어 → Haiku 번역 → 영어 → Claude |

`--mode translated` 옵션으로 KO-translated 벤치마크를 실행하면, 번역이 실제로 EN-native 수준에 근접하는지 확인할 수 있습니다.

## 통계 분석

- **Paired t-test**: 동일 테스트에 대한 언어별 점수 비교
- **Wilcoxon signed-rank**: 비모수적 대안
- **Cohen's d**: 효과 크기 (< 0.2: 무시, 0.2-0.5: 소, 0.5-0.8: 중, > 0.8: 대)
- **Bonferroni correction**: 다중 비교 보정
- **95% 신뢰구간**: 평균 차이의 신뢰구간

## 시각화

벤치마크 실행 후 자동 생성되는 차트:

- **레이더 차트**: 5개 차원별 언어 간 성능 비교
- **박스 플롯**: 점수 분포 비교
- **히트맵**: 언어 × 차원 평균 점수
- **바 차트**: 종합 점수 + 95% CI
- **델타 차트**: 테스트별 (EN - KO) 점수 차이

## 테스트 결과

### 플러그인 언어 감지 테스트 (10/10 PASS)

```
✓ "파이썬으로 정렬 알고리즘을 구현해주세요..."        → ko (1.00)
✓ "Pythonでソートアルゴリズムを実装してください..."     → ja (1.00)
✓ "Implement a sorting algorithm in Python..."      → en (1.00)
✓ "다음 코드에서 버그를 찾아주세요: ```python..."     → ko (1.00)
✓ "ReactコンポーネントでuseStateフックを..."          → ja (1.00)
✓ "FastAPI로 REST API endpoint를 만들어서..."        → ko (0.73)
✓ "Read the file at /Users/test/src/main.py..."     → en (1.00)
✓ "" (빈 입력)                                       → en (1.00)
✓ "```python\nprint('hello')\n```" (코드만)           → en (1.00)
✓ "请用Python实现一个排序算法..."                      → zh (1.00)

10 passed, 0 failed — All language detection tests passed!
```

### 벤치마크 테스트 케이스 검증

```
Total: 40
  coding:       10 ✓
  api_usage:    10 ✓
  debugging:    10 ✓
  architecture: 10 ✓
All 3-language (en/ko/ja) check: PASS
```

### 통계 모듈 검증

```
Paired t-test:  t=9.0000, p=0.000844, significant=True
Cohen's d:      4.0249 (Large effect)
Composite score: 4.14 ± 0.42
Statistics module: PASS
```

---

## Before / After: 플러그인 적용 효과

### Before (플러그인 미적용)

한국어 프롬프트가 Claude에 직접 전달됩니다.

```
사용자: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
Claude: 한국어 프롬프트를 직접 처리
    ↓
응답 (잠재적 문제):
  - 의도 파악 오류 가능성 ↑
  - 할루시네이션 빈도 ↑
  - deprecated API 사용 가능성 ↑
  - 영어 대비 정확도 격차 존재
```

**문제점:**
- 비영어 프롬프트에서 미묘한 뉘앙스나 기술적 요구사항이 누락될 수 있음
- 코드 생성 시 영어 기반 학습 데이터 대비 최적화되지 않은 추론 경로
- 복잡한 기술 용어가 포함된 한국어 프롬프트에서 할루시네이션 증가 가능성

### After (플러그인 적용)

한국어 프롬프트가 영어로 번역된 후 Claude에 전달됩니다.

```
사용자: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
[translate-hook.mjs] 언어 감지: ko (confidence: 0.85)
    ↓
[translator.mjs] Claude Haiku 번역 (~2초):
  "Create a REST API with JWT authentication using FastAPI"
    ↓
[additionalContext 주입]
  <prompt-translation>
  English Translation:
  Create a REST API with JWT authentication using FastAPI
  
  Instructions: Use English translation as primary input.
  Respond in Korean.
  </prompt-translation>
    ↓
Claude: 영어 번역 기반으로 추론 → 한국어로 응답
    ↓
응답 (개선 효과):
  - 의도 파악 정확도 ↑
  - 할루시네이션 감소 ↑
  - 최신 API 패턴 사용 ↑
  - 영어 수준에 근접한 정확도
```

**개선 효과:**
- 영어 기반 추론 경로로 코드 생성 품질 향상
- 기술 용어가 영어로 명확히 전달되어 할루시네이션 감소
- 프롬프트 의도가 모델의 주 학습 언어로 전달되어 이해도 향상
- 응답은 여전히 한국어로 제공 (사용자 경험 유지)

### 성능 오버헤드

| 항목 | 수치 |
|------|------|
| 언어 감지 | < 1ms (Unicode range 체크) |
| Haiku 번역 API | ~2-3초 |
| 전체 훅 타임아웃 | 8초 (초과 시 원문 통과) |
| 추가 비용 | Haiku 호출당 ~$0.001 |

### 벤치마크 비교 실행법

```bash
# 1. 플러그인 미적용 (native 모드)
python -m benchmark.cli run --languages en,ko --mode native --trials 3

# 2. 플러그인 적용 (translated 모드)  
python -m benchmark.cli run --languages ko --mode translated --trials 3

# 3. 결과 비교 분석
python -m benchmark.cli analyze --results-dir ./results/<timestamp>
```

3-way 비교 결과에서 **KO-translated**가 **EN-native**에 근접할수록 플러그인이 효과적입니다.

## 라이선스

MIT
