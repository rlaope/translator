# 多语言LLM准确度基准测试 & 提示词翻译插件

> **[English](README.md)** | **[한국어](README.kr.md)** | **[日本語](README.ja.md)**

定量验证以下假设：当向Claude输入韩语/日语/中文提示词时，响应质量低于英语。并提供**自动翻译Claude Code插件**来缩小这一差距。

## 项目结构

```
translator/
├── benchmark/     # Python基准测试套件（40个测试，5个评分维度）
├── plugin/        # Claude Code翻译插件（UserPromptSubmit钩子）
└── docs/          # 方法论和评分标准文档
```

## 评分维度（5分制）

| # | 维度 | 权重 | 测量方法 |
|---|------|------|----------|
| 1 | **实现准确度** | 30% | 代码执行测试 |
| 2 | **意图理解** | 25% | LLM-as-Judge |
| 3 | **幻觉率** | 20% | API/函数真实性验证 |
| 4 | **代码Bug率** | 15% | 自动化 + LLM混合 |
| 5 | **遗漏/过时频率** | 10% | LLM-as-Judge |

**综合评分** = `实现×0.30 + 意图×0.25 + 幻觉×0.20 + Bug×0.15 + 遗漏×0.10`

## 快速开始

### 1. 安装

```bash
# Python依赖
cd benchmark
pip install -e .

# 插件依赖
cd ../plugin
npm install
```

### 2. 运行基准测试

```bash
# 完整基准测试（EN/KO/JA，3次试验）
python -m benchmark.cli run --languages en,ko,ja --trials 3

# 单个类别
python -m benchmark.cli run --category coding --languages en,ko

# 翻译模式（验证插件效果）
python -m benchmark.cli run --languages ko,ja --mode translated --trials 3

# 查看测试用例列表
python -m benchmark.cli list-cases
```

### 3. 安装翻译插件

```bash
cd plugin
claude plugin install .
```

或手动添加到 `~/.claude/settings.json`：

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

### 4. 插件配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `TRANSLATOR_ENABLED` | `true` | 启用/禁用插件 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 翻译模型 |
| `TRANSLATOR_TIMEOUT` | `6000` | 翻译API超时（ms） |
| `TRANSLATOR_DEBUG` | - | 启用调试日志 |

## 翻译插件工作原理

```
用户输入中文提示词
    ↓
UserPromptSubmit钩子触发
    ↓
基于Unicode的语言检测（<1ms）
    ↓（检测到非英语）
通过Claude Haiku翻译成英语（~2-3秒）
    ↓
将翻译注入additionalContext
    ↓
Claude基于英语翻译进行推理 → 用中文回复
```

核心特性：
- **零依赖语言检测**：基于Unicode范围检查，无需外部库
- **优雅降级**：翻译失败时原文直接传递（永不阻塞）
- **代码保留**：代码块、文件路径、变量名不会被翻译

## 三方对比

| 模式 | 说明 |
|------|------|
| **EN-native** | 英语提示词 → Claude |
| **ZH-native** | 中文提示词 → Claude |
| **ZH-translated** | 中文 → Haiku翻译 → 英语 → Claude |

**ZH-translated** 越接近 **EN-native**，说明插件效果越好。

## 测试结果

### 语言检测测试（10/10通过）

```
✓ "파이썬으로 정렬 알고리즘을 구현해주세요..."        → ko (1.00)
✓ "Pythonでソートアルゴリズムを実装してください..."     → ja (1.00)
✓ "Implement a sorting algorithm in Python..."      → en (1.00)
✓ "다음 코드에서 버그를 찾아주세요: ```python..."     → ko (1.00)
✓ "ReactコンポーネントでuseStateフックを..."          → ja (1.00)
✓ "FastAPI로 REST API endpoint를 만들어서..."        → ko (0.73)
✓ "Read the file at /Users/test/src/main.py..."     → en (1.00)
✓ "" (空输入)                                        → en (1.00)
✓ "```python\nprint('hello')\n```" (仅代码)           → en (1.00)
✓ "请用Python实现一个排序算法..."                      → zh (1.00)

10 passed, 0 failed
```

### 基准测试验证

```
总计: 40
  coding:       10 ✓
  api_usage:    10 ✓
  debugging:    10 ✓
  architecture: 10 ✓
全3语言（en/ko/ja）检查: PASS
```

---

## Before / After：插件效果对比

### Before（未应用）

```
用户: "用FastAPI创建一个带JWT认证的REST API"
    ↓
Claude: 直接处理中文提示词
    ↓
潜在问题: 意图误解↑、幻觉↑、deprecated API↑
```

### After（已应用）

```
用户: "用FastAPI创建一个带JWT认证的REST API"
    ↓
[translate-hook] 检测: zh (0.92) → Haiku翻译（~2秒）
    ↓
"Create a REST API with JWT authentication using FastAPI"
    ↓
Claude: 基于英语推理 → 用中文回复
    ↓
改进: 意图理解↑、幻觉↓、最新模式↑
```

### 性能开销

| 项目 | 数值 |
|------|------|
| 语言检测 | < 1ms |
| Haiku翻译 | ~2-3秒 |
| 总超时 | 8秒（超时则原文通过） |
| 额外成本 | ~$0.001/次调用 |

## 许可证

MIT
