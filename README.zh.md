# 多语言LLM准确度基准测试 & 提示词翻译插件

> **[English](README.md)** | **[한국어](README.kr.md)** | **[日本語](README.ja.md)**

定量验证以下假设：当向Claude输入韩语、日语或中文提示词时，响应质量低于英语。并提供**自动翻译Claude Code插件**来缩小这一差距。

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

# 分析现有结果
python -m benchmark.cli analyze --results-dir ./results/2026-04-09_120000

# 生成报告
python -m benchmark.cli report --results-dir ./results/2026-04-09_120000 --format html
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

通过环境变量控制：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `TRANSLATOR_ENABLED` | `true` | 启用/禁用插件 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 翻译模型 |
| `TRANSLATOR_TIMEOUT` | `6000` | 翻译API超时（ms） |
| `TRANSLATOR_DEBUG` | - | 启用调试日志 |

## 基准测试用例

4个类别，共40个测试（Easy 3、Medium 4、Hard 3）：

| 类别 | 范围 | 主题 |
|------|------|------|
| **Coding** | TC-CODE-001~010 | 算法、数据结构、异步模式 |
| **API Usage** | TC-API-001~010 | REST、SDK、认证、支付、GraphQL |
| **Debugging** | TC-DEBUG-001~010 | Bug修复、内存泄漏、竞态条件 |
| **Architecture** | TC-ARCH-001~010 | 设计模式、系统设计、分布式系统 |

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

通过三方对比验证插件的实际效果：

| 模式 | 说明 |
|------|------|
| **EN-native** | 英语提示词 → Claude |
| **KO-native** | 韩语提示词 → Claude |
| **KO-translated** | 韩语 → Haiku翻译 → 英语 → Claude |

运行 `--mode translated` 对KO-translated进行基准测试，检验其是否能接近EN-native的质量。

## 测试结果

### 语言检测测试（10/10通过）

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

边缘情况处理：
- 代码较多的中文提示词 → 仍能正确检测为中文
- 混合语言（中文 + 英文技术术语）→ 正确识别为中文
- 纯代码块 → 识别为英语（跳过翻译）
- 空输入 → 无错误通过

---

## 问题：非英语提示词的质量下降

LLM主要以英语数据训练。用韩语、日语或中文输入提示词时，用户会反复遇到以下问题：

| 问题 | 发生的现象 |
|------|-----------|
| **意图误解** | 中文语序和省略主语导致Claude错误理解需求 |
| **API幻觉** | 非英语提示词触发更多虚构的函数名和参数 |
| **使用过时模式** | 更频繁地使用已废弃的库或Python 2风格代码 |
| **遗漏需求** | 中文表达的细微约束被悄然忽略 |
| **代码质量下降** | 更多Bug、边界错误和未处理的异常情况 |

这种准确度差距源于模型的推理针对英语词元序列进行了优化。中文提示词迫使模型走一条训练量更少的路径。

## 解决方案：插件的工作方式

插件拦截每一条非英语提示词，通过Claude Haiku将其翻译成英语，然后将译文作为**主要推理输入**注入——整个过程透明，在3秒内完成。

```
┌─────────────────────────────────────────────────────────┐
│  用中文（或日语、韩语）输入                               │
│                                                         │
│  "FastAPI로 JWT 인증이 포함된 REST API를 만들어줘.       │
│   에러 핸들링하고 Pydantic v2 모델 써줘"                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  [Plugin: translate-hook.mjs]                           │
│                                                         │
│  1. 语言检测: ko（置信度: 0.87）               <1ms     │
│  2. Claude Haiku翻译成英语:                    ~2s      │
│                                                         │
│     "Create a REST API with JWT authentication          │
│      using FastAPI. Include error handling and           │
│      use Pydantic v2 models."                           │
│                                                         │
│  3. 将英语译文注入additionalContext                       │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Claude用英语推理 → 用中文回复                            │
│                                                         │
│  ✓ 意图准确: FastAPI + JWT + 错误处理                    │
│  ✓ 无幻觉: 真实的库、真实的API                           │
│  ✓ 现代代码: Pydantic v2、python-jose、最新语法          │
│  ✓ 回复语言: 仍为中文（保留用户体验）                     │
└─────────────────────────────────────────────────────────┘
```

## 使用示例

### 示例1：复杂编程任务

**不使用插件** — 中文提示词直接发送给Claude：
```
输入: "비동기 레이트 리미터를 토큰 버킷 알고리즘으로 구현해줘. 
      슬라이딩 윈도우도 지원하고 Redis 백엔드 옵션도 넣어줘"

❌ 可能出现的问题:
  - "令牌桶"被误解，实现不完整
  - Redis集成使用已废弃的redis-py模式
  - 滑动窗口逻辑存在off-by-one Bug
  - 缺少async上下文管理器支持
```

**使用插件后** — 先翻译再处理：
```
输入: （相同的提示词）
      ↓
翻译: "Implement an async rate limiter using the token bucket algorithm.
      Support sliding window and include a Redis backend option."
      ↓
✅ 结果:
  - 使用asyncio.Lock正确实现令牌桶
  - Redis后端使用最新的redis.asyncio API
  - 滑动窗口边界处理正确
  - 完整的async上下文管理器协议（__aenter__/__aexit__）
```

### 示例2：调试任务

**不使用插件：**
```
输入: "이 코드에서 메모리 누수 원인 찾아줘. 파일 핸들이 
      제대로 닫히지 않는 것 같은데 asyncio 컨텍스트에서 
      어떻게 해결해야 하는지도 알려줘"

❌ 可能出现的问题:
  - 找错内存泄漏来源
  - 在异步上下文中给出同步修复方案
  - 遗漏asyncio特有的资源清理模式
```

**使用插件后：**
```
输入: （相同的提示词）
      ↓
翻译: "Find the memory leak in this code. File handles don't seem 
      to be closing properly. Also explain how to fix this in 
      an asyncio context."
      ↓
✅ 结果:
  - 准确定位未关闭的aiofiles句柄
  - 建议使用async with进行正确清理
  - 添加asyncio.TaskGroup实现结构化并发
```

### 示例3：架构问题

**不使用插件：**
```
输入: "마이크로서비스 간 이벤트 소싱 패턴을 설계해줘. 
      CQRS도 적용하고 eventual consistency 보장해야 해"

❌ 可能出现的问题:
  - 设计模糊，缺乏具体实现
  - 混淆事件溯源与事件驱动架构
  - 缺少用于保证一致性的补偿/Saga模式
```

**使用插件后：**
```
输入: （相同的提示词）
      ↓
翻译: "Design an event sourcing pattern between microservices. 
      Apply CQRS and ensure eventual consistency."
      ↓
✅ 结果:
  - 命令/查询模型清晰分离
  - 带有适当快照机制的事件存储
  - 分布式事务的Saga模式
  - 包含Kafka/RabbitMQ示例的具体代码
```

## 性能开销

| 项目 | 数值 |
|------|------|
| 语言检测 | < 1ms（Unicode范围检查，零依赖） |
| Haiku翻译 | ~2-3秒（一次API调用） |
| 钩子总超时 | 8秒（超时则静默通过） |
| 每次提示词成本 | ~$0.001（Haiku极其便宜） |
| 英语提示词 | 0ms开销（立即检测并跳过） |

插件为非英语提示词增加约2-3秒延迟。英语提示词无任何额外开销。

## 插件不会做的事

- **不替换**原始提示词——以补充上下文的方式添加译文
- **不阻塞**翻译失败的情况——自然降级到原始提示词
- **不翻译代码**——代码块、文件路径、变量名原样保留
- **不改变回复语言**——Claude仍然用中文回复

## 许可证

MIT
