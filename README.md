# Multilingual LLM Accuracy Benchmark & Prompt Translator

> **[한국어](README.kr.md)** | **[日本語](README.ja.md)** | **[中文](README.zh.md)**

Quantitatively verify the hypothesis that Claude produces lower-quality responses to non-English prompts compared to English, and provide an **automatic translation Claude Code plugin** to close the gap.

## Overview

```
translator/
├── benchmark/     # Python benchmark suite (40 tests, 5 scoring dimensions)
├── plugin/        # Claude Code translation plugin (UserPromptSubmit hook)
└── docs/          # Methodology and scoring rubric documentation
```

## Scoring Dimensions (5-Point Scale)

| # | Dimension | Weight | Method |
|---|-----------|--------|--------|
| 1 | **Implementation Accuracy** | 30% | Code execution tests |
| 2 | **Intent Comprehension** | 25% | LLM-as-Judge |
| 3 | **Hallucination** | 20% | API/function existence verification |
| 4 | **Code Bug Rate** | 15% | Automated + LLM hybrid |
| 5 | **Omission/Outdated** | 10% | LLM-as-Judge |

**Composite Score** = `impl×0.30 + intent×0.25 + hallucination×0.20 + bugs×0.15 + omission×0.10`

## Quick Start

### 1. Installation

```bash
# Python dependencies
cd benchmark
pip install -e .

# Plugin dependencies
cd ../plugin
npm install
```

### 2. Run Benchmark

```bash
# Full benchmark (EN/KO/JA, 3 trials)
python -m benchmark.cli run --languages en,ko,ja --trials 3

# Single category
python -m benchmark.cli run --category coding --languages en,ko

# Translation mode (verify plugin effectiveness)
python -m benchmark.cli run --languages ko,ja --mode translated --trials 3

# List test cases
python -m benchmark.cli list-cases

# Analyze existing results
python -m benchmark.cli analyze --results-dir ./results/2026-04-09_120000

# Generate report
python -m benchmark.cli report --results-dir ./results/2026-04-09_120000 --format html
```

### 3. Install Translation Plugin

```bash
cd plugin
claude plugin install .
```

Or manually add to `~/.claude/settings.json`:

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

### 4. Plugin Configuration

Controlled via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSLATOR_ENABLED` | `true` | Enable/disable plugin |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | Model for translation |
| `TRANSLATOR_TIMEOUT` | `6000` | Translation API timeout (ms) |
| `TRANSLATOR_DEBUG` | - | Enable debug logging |

## Benchmark Test Cases

40 tests across 4 categories (Easy 3, Medium 4, Hard 3 each):

| Category | Range | Topics |
|----------|-------|--------|
| **Coding** | TC-CODE-001~010 | Algorithms, data structures, async patterns |
| **API Usage** | TC-API-001~010 | REST, SDK, auth, payments, GraphQL |
| **Debugging** | TC-DEBUG-001~010 | Bug fixing, memory leaks, race conditions |
| **Architecture** | TC-ARCH-001~010 | Design patterns, system design, distributed systems |

## How the Translation Plugin Works

```
User types Korean prompt
    ↓
UserPromptSubmit hook triggers
    ↓
Unicode-based language detection (<1ms)
    ↓ (non-English detected)
English translation via Claude Haiku (~2-3s)
    ↓
Translation injected as additionalContext
    ↓
Claude reasons from English translation → responds in Korean
```

Key features:
- **Zero-dependency language detection**: Unicode range checks, no external libraries
- **Graceful degradation**: Falls through on translation failure (never blocks)
- **Code preservation**: Code blocks, file paths, and variable names are never translated

## 3-Way Comparison

Verify the plugin's actual effectiveness with a 3-way comparison:

| Mode | Description |
|------|-------------|
| **EN-native** | English prompt → Claude |
| **KO-native** | Korean prompt → Claude |
| **KO-translated** | Korean → Haiku translation → English → Claude |

Run `--mode translated` to benchmark KO-translated and check if it approaches EN-native quality.

## Statistical Analysis

- **Paired t-test**: Compare scores for the same test cases across languages
- **Wilcoxon signed-rank**: Non-parametric alternative
- **Cohen's d**: Effect size (< 0.2: negligible, 0.2-0.5: small, 0.5-0.8: medium, > 0.8: large)
- **Bonferroni correction**: Multiple comparison adjustment
- **95% Confidence Intervals**: CI for mean score differences

## Visualizations

Auto-generated after benchmark runs:

- **Radar chart**: 5-dimension cross-language comparison
- **Box plots**: Score distributions per language
- **Heatmap**: Language × Dimension mean scores
- **Bar chart**: Composite scores with 95% CI
- **Delta chart**: Per-test-case (EN - KO) score differences

## Test Results

### Plugin Language Detection (10/10 PASS)

```
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

### Benchmark Test Case Validation

```
Total: 40
  coding:       10 ✓
  api_usage:    10 ✓
  debugging:    10 ✓
  architecture: 10 ✓
All 3-language (en/ko/ja) check: PASS
```

### Statistics Module Validation

```
Paired t-test:  t=9.0000, p=0.000844, significant=True
Cohen's d:      4.0249 (Large effect)
Composite score: 4.14 ± 0.42
Statistics module: PASS
```

---

## Before / After: Plugin Effect

### Before (Without Plugin)

Korean prompts go directly to Claude.

```
User: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
Claude: Processes Korean prompt directly
    ↓
Response (potential issues):
  - Higher chance of intent misinterpretation
  - Increased hallucination frequency
  - More likely to use deprecated APIs
  - Accuracy gap vs English prompts
```

**Problems:**
- Subtle nuances and technical requirements may be lost in non-English prompts
- Code generation uses suboptimal reasoning paths compared to English-trained data
- Complex technical terminology in Korean increases hallucination risk

### After (With Plugin)

Korean prompts are translated to English before reaching Claude.

```
User: "FastAPI로 JWT 인증이 포함된 REST API를 만들어주세요"
    ↓
[translate-hook.mjs] Language detected: ko (confidence: 0.85)
    ↓
[translator.mjs] Claude Haiku translation (~2s):
  "Create a REST API with JWT authentication using FastAPI"
    ↓
[additionalContext injection]
  <prompt-translation>
  English Translation:
  Create a REST API with JWT authentication using FastAPI

  Instructions: Use English translation as primary input.
  Respond in Korean.
  </prompt-translation>
    ↓
Claude: Reasons from English translation → Responds in Korean
    ↓
Response (improvements):
  - Better intent comprehension
  - Reduced hallucination
  - More modern API patterns
  - Accuracy approaching English-native levels
```

**Improvements:**
- English-based reasoning path improves code generation quality
- Technical terms clearly conveyed in English reduce hallucination
- Prompt intent delivered in model's primary training language improves comprehension
- Response still in Korean (user experience preserved)

### Performance Overhead

| Item | Value |
|------|-------|
| Language detection | < 1ms (Unicode range check) |
| Haiku translation API | ~2-3s |
| Total hook timeout | 8s (falls through on timeout) |
| Additional cost | ~$0.001 per Haiku call |

### Benchmark Comparison

```bash
# 1. Without plugin (native mode)
python -m benchmark.cli run --languages en,ko --mode native --trials 3

# 2. With plugin (translated mode)
python -m benchmark.cli run --languages ko --mode translated --trials 3

# 3. Compare results
python -m benchmark.cli analyze --results-dir ./results/<timestamp>
```

The closer **KO-translated** scores are to **EN-native**, the more effective the plugin.

## License

MIT
