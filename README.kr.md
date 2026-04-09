# 다국어 LLM 정확도 벤치마크 & 프롬프트 번역기

> **[English](README.md)** | **[日本語](README.ja.md)** | **[中文](README.zh.md)**

Claude에 한국어/일본어/중국어 프롬프트를 입력했을 때 영어 대비 응답 품질이 낮다는 가설을 정량적으로 검증하고, 이를 해결하기 위한 **자동 번역 Claude Code 플러그인**을 제공합니다.

## 구성

```
translator/
├── benchmark/     # Python 벤치마크 스위트 (40개 테스트, 5개 평가 기준)
├── plugin/        # Claude Code 번역 플러그인 (UserPromptSubmit 훅)
└── docs/          # 방법론 및 채점 기준 문서
```

## 평가 기준 (5점 척도)

| # | 기준 | 가중치 | 측정 방법 |
|---|------|--------|-----------|
| 1 | **구현정확도** | 30% | 코드 실행 테스트 |
| 2 | **의도파악** | 25% | LLM-as-Judge |
| 3 | **할루시네이션** | 20% | API/함수 실재 검증 |
| 4 | **코드버그 발생도** | 15% | 자동 + LLM 혼합 |
| 5 | **누락/아웃데이트** | 10% | LLM-as-Judge |

**종합 점수** = `구현정확도×0.30 + 의도파악×0.25 + 할루시네이션×0.20 + 버그×0.15 + 누락×0.10`

## 빠른 시작

### 1. 설치

```bash
# Python 의존성
cd benchmark
pip install -e .

# 플러그인 의존성
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
cd plugin
claude plugin install .
```

또는 `~/.claude/settings.json`에 수동 추가:

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

환경 변수로 제어합니다:

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `TRANSLATOR_ENABLED` | `true` | 플러그인 활성화/비활성화 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 번역용 모델 |
| `TRANSLATOR_TIMEOUT` | `6000` | 번역 API 타임아웃 (ms) |
| `TRANSLATOR_DEBUG` | - | 디버그 로그 활성화 |

## 벤치마크 테스트 케이스

4개 카테고리, 총 40개 테스트 (Easy 3, Medium 4, Hard 3):

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

플러그인의 실제 효과를 3-way 비교로 검증합니다:

| 모드 | 설명 |
|------|------|
| **EN-native** | 영어 프롬프트 → Claude |
| **KO-native** | 한국어 프롬프트 → Claude |
| **KO-translated** | 한국어 → Haiku 번역 → 영어 → Claude |

`--mode translated`로 KO-translated 벤치마크를 실행하여 EN-native 품질에 얼마나 근접하는지 확인합니다.

## 테스트 결과

### 언어 감지 테스트 (10/10 통과)

```
$ node plugin/tests/translate-hook.test.mjs

✓ "파이썬으로 정렬 알고리즘을 구현해주세요..."        → ko (1.00)
✓ "Pythonでソートアルゴリズムを実装してください..."     → ja (1.00)
✓ "Implement a sorting algorithm in Python..."      → en (1.00)
✓ "다음 코드에서 버그를 찾아주세요: ```python..."     → ko (1.00)
✓ "ReactコンポーネントでuseStateフックを..."          → ja (1.00)
✓ "FastAPI로 REST API endpoint를 만들어서..."        → ko (0.73)
✓ "Read the file at /Users/test/src/main.py..."     → en (1.00)
✓ "" (empty input)                                   → en (1.00)
✓ "```python\nprint('hello')\n```" (code only)       → en (1.00)
✓ "请用Python实现一个排序算法..."                      → zh (1.00)

10 passed, 0 failed — All language detection tests passed!
```

에지 케이스 처리:
- 코드가 많은 한국어 프롬프트 → 한국어 정상 감지
- 혼용 언어 (한국어 + 영어 기술 용어) → 한국어로 정확히 감지
- 순수 코드 블록 → 영어로 식별 (번역 생략)
- 빈 입력 → 오류 없이 통과

---

## 문제: 비영어 프롬프트의 품질 저하

LLM은 대부분 영어 데이터로 학습됩니다. 한국어, 일본어, 중국어로 프롬프트를 입력하면 다음과 같은 문제가 반복적으로 발생합니다:

| 문제 | 발생 현상 |
|------|-----------|
| **의도 오해** | 한국어 문법(SOV 구조)과 생략된 주어로 인해 요구사항을 잘못 파악 |
| **API 할루시네이션** | 비영어 프롬프트에서 존재하지 않는 함수명과 파라미터 생성 증가 |
| **구식 패턴 사용** | deprecated 라이브러리나 Python 2 스타일 코드 빈도 증가 |
| **요구사항 누락** | 한국어로 표현된 세밀한 조건이 조용히 무시됨 |
| **코드 품질 저하** | 버그, off-by-one 오류, 예외 처리 누락 증가 |

이 정확도 격차는 모델의 추론이 영어 토큰 시퀀스에 최적화되어 있기 때문입니다. 한국어 프롬프트는 모델을 덜 학습된 경로로 강제합니다.

## 해결책: 플러그인 동작 방식

플러그인은 비영어 프롬프트를 가로채서 Claude Haiku로 영어로 번역한 뒤, 번역문을 **기본 추론 입력**으로 주입합니다 — 모두 투명하게, 3초 이내에.

```
┌─────────────────────────────────────────────────────────┐
│  한국어(또는 일본어, 중국어)로 입력                        │
│                                                         │
│  "FastAPI로 JWT 인증이 포함된 REST API를 만들어줘.       │
│   에러 핸들링하고 Pydantic v2 모델 써줘"                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  [Plugin: translate-hook.mjs]                           │
│                                                         │
│  1. 언어 감지: ko (신뢰도: 0.87)               <1ms     │
│  2. Claude Haiku가 영어로 번역:                 ~2초     │
│                                                         │
│     "Create a REST API with JWT authentication          │
│      using FastAPI. Include error handling and           │
│      use Pydantic v2 models."                           │
│                                                         │
│  3. 영어 번역을 additionalContext로 주입                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Claude가 영어로 추론 → 한국어로 응답                     │
│                                                         │
│  ✓ 정확한 의도: FastAPI + JWT + 에러 핸들링              │
│  ✓ 할루시네이션 없음: 실제 라이브러리, 실제 API            │
│  ✓ 최신 코드: Pydantic v2, python-jose, 최신 문법        │
│  ✓ 응답 언어: 한국어 유지 (UX 보존)                      │
└─────────────────────────────────────────────────────────┘
```

## 사용 예시

### 예시 1: 복잡한 코딩 작업

**플러그인 없이** — 한국어 프롬프트가 Claude에 직접 전달:
```
입력: "비동기 레이트 리미터를 토큰 버킷 알고리즘으로 구현해줘. 
      슬라이딩 윈도우도 지원하고 Redis 백엔드 옵션도 넣어줘"

❌ 예상 문제:
  - "토큰 버킷" 오해로 불완전한 구현
  - Redis 연동에 deprecated redis-py 패턴 사용
  - 슬라이딩 윈도우 로직에 off-by-one 버그
  - async context manager 지원 누락
```

**플러그인 적용 후** — 먼저 번역 후 처리:
```
입력: (동일한 한국어 프롬프트)
      ↓
번역: "Implement an async rate limiter using the token bucket algorithm.
      Support sliding window and include a Redis backend option."
      ↓
✅ 결과:
  - asyncio.Lock을 활용한 정확한 토큰 버킷 구현
  - 최신 redis.asyncio API 사용
  - 경계 처리가 올바른 슬라이딩 윈도우
  - 완전한 async context manager 프로토콜 (__aenter__/__aexit__)
```

### 예시 2: 디버깅 작업

**플러그인 없이:**
```
입력: "이 코드에서 메모리 누수 원인 찾아줘. 파일 핸들이 
      제대로 닫히지 않는 것 같은데 asyncio 컨텍스트에서 
      어떻게 해결해야 하는지도 알려줘"

❌ 예상 문제:
  - 잘못된 누수 원인 지목
  - 비동기 컨텍스트에 동기식 수정 제안
  - asyncio 전용 리소스 정리 패턴 누락
```

**플러그인 적용 후:**
```
입력: (동일한 한국어 프롬프트)
      ↓
번역: "Find the memory leak in this code. File handles don't seem 
      to be closing properly. Also explain how to fix this in 
      an asyncio context."
      ↓
✅ 결과:
  - 닫히지 않은 aiofiles 핸들 정확히 지목
  - 적절한 정리를 위한 async with 제안
  - 구조화된 동시성을 위한 asyncio.TaskGroup 추가
```

### 예시 3: 아키텍처 질문

**플러그인 없이:**
```
입력: "마이크로서비스 간 이벤트 소싱 패턴을 설계해줘. 
      CQRS도 적용하고 eventual consistency 보장해야 해"

❌ 예상 문제:
  - 구체적 구현 없는 모호하고 일반적인 설계
  - 이벤트 소싱과 이벤트 드리븐 아키텍처 혼동
  - 일관성을 위한 보상/사가 패턴 누락
```

**플러그인 적용 후:**
```
입력: (동일한 한국어 프롬프트)
      ↓
번역: "Design an event sourcing pattern between microservices. 
      Apply CQRS and ensure eventual consistency."
      ↓
✅ 결과:
  - 커맨드/쿼리 모델 명확한 분리
  - 적절한 스냅샷을 갖춘 이벤트 스토어
  - 분산 트랜잭션을 위한 사가 패턴
  - Kafka/RabbitMQ 예제를 포함한 구체적 코드
```

## 성능 오버헤드

| 항목 | 수치 |
|------|------|
| 언어 감지 | < 1ms (Unicode range 확인, 의존성 없음) |
| Haiku 번역 | ~2-3초 (API 호출 1회) |
| 전체 훅 타임아웃 | 8초 (타임아웃 시 조용히 통과) |
| 프롬프트당 비용 | ~$0.001 (Haiku는 매우 저렴) |
| 영어 프롬프트 | 오버헤드 0ms (즉시 감지 후 건너뜀) |

비영어 프롬프트에는 약 2-3초가 추가됩니다. 영어 프롬프트는 오버헤드가 없습니다.

## 플러그인이 하지 않는 것

- **원본 프롬프트를 대체하지 않음** — 번역문을 보조 컨텍스트로 추가하는 방식
- **번역 실패 시 차단하지 않음** — 원본 프롬프트로 자연스럽게 통과
- **코드를 번역하지 않음** — 코드 블록, 파일 경로, 변수명 원본 유지
- **응답 언어를 바꾸지 않음** — Claude는 여전히 한국어로 응답

## 라이선스

MIT
