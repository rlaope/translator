# 다국어 LLM 정확도 벤치마크 & 프롬프트 번역기

> **[English](README.md)** | **[日本語](README.ja.md)** | **[中文](README.zh.md)**

Claude에 한국어/일본어 프롬프트를 입력했을 때 영어 대비 정확도가 떨어진다는 가설을 **정량적으로 검증**하고, 이를 해결하기 위한 **자동 번역 Claude Code 플러그인**을 제공합니다.

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

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `TRANSLATOR_ENABLED` | `true` | 플러그인 활성화/비활성화 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 번역용 모델 |
| `TRANSLATOR_TIMEOUT` | `6000` | 번역 API 타임아웃 (ms) |
| `TRANSLATOR_DEBUG` | - | 디버그 로그 활성화 |

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

| 모드 | 설명 |
|------|------|
| **EN-native** | 영어 프롬프트 → Claude |
| **KO-native** | 한국어 프롬프트 → Claude |
| **KO-translated** | 한국어 → Haiku 번역 → 영어 → Claude |

**KO-translated**가 **EN-native**에 근접할수록 플러그인이 효과적입니다.

## 테스트 결과

### 언어 감지 테스트 (10/10 통과)

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

10 passed, 0 failed
```

### 벤치마크 검증

```
Total: 40
  coding:       10 ✓
  api_usage:    10 ✓
  debugging:    10 ✓
  architecture: 10 ✓
전체 3개 국어 (en/ko/ja) 확인: PASS
```

### 통계 모듈 검증

```
Paired t-test:  t=9.0000, p=0.000844, significant=True
Cohen's d:      4.0249 (대형 효과)
종합 점수:       4.14 ± 0.42
통계 모듈: PASS
```

---

## Before / After: 플러그인 적용 효과

### Before (미적용)

```
사용자: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
Claude: 한국어 프롬프트 직접 처리
    ↓
잠재적 문제: 의도 오해 ↑, 할루시네이션 ↑, deprecated API ↑
```

### After (적용)

```
사용자: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
[translate-hook] 감지: ko (0.85) → Haiku 번역 (~2초)
    ↓
"Create a REST API with JWT authentication using FastAPI"
    ↓
Claude: 영어 기반 추론 → 한국어 응답
    ↓
개선: 의도파악 ↑, 할루시네이션 ↓, 최신 패턴 ↑
```

### 성능 오버헤드

| 항목 | 수치 |
|------|------|
| 언어 감지 | < 1ms |
| Haiku 번역 | ~2-3초 |
| 전체 타임아웃 | 8초 (초과 시 원문 통과) |
| 추가 비용 | ~$0.001/호출 |

## 라이선스

MIT
