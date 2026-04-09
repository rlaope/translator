# 多言語LLM精度ベンチマーク & プロンプト翻訳プラグイン

> **[English](README.md)** | **[한국어](README.kr.md)** | **[中文](README.zh.md)**

韓国語・日本語・中国語でClaudeにプロンプトを入力した場合、英語と比較して応答品質が低下するという仮説を定量的に検証し、これを解決するための**自動翻訳Claude Codeプラグイン**を提供します。

## 構成

```
translator/
├── benchmark/     # Pythonベンチマークスイート（40テスト、5評価基準）
├── plugin/        # Claude Code翻訳プラグイン（UserPromptSubmitフック）
└── docs/          # 方法論とスコアリング基準ドキュメント
```

## 評価基準（5段階スケール）

| # | 基準 | 重み | 測定方法 |
|---|------|------|----------|
| 1 | **実装精度** | 30% | コード実行テスト |
| 2 | **意図理解** | 25% | LLM-as-Judge |
| 3 | **ハルシネーション** | 20% | API/関数実在検証 |
| 4 | **コードバグ発生率** | 15% | 自動 + LLMハイブリッド |
| 5 | **欠落/古い情報** | 10% | LLM-as-Judge |

**総合スコア** = `実装×0.30 + 意図×0.25 + ハルシネーション×0.20 + バグ×0.15 + 欠落×0.10`

## クイックスタート

### 1. インストール

```bash
# Python依存関係
cd benchmark
pip install -e .

# プラグイン依存関係
cd ../plugin
npm install
```

### 2. ベンチマーク実行

```bash
# フルベンチマーク（EN/KO/JA、3回試行）
python -m benchmark.cli run --languages en,ko,ja --trials 3

# 特定カテゴリのみ
python -m benchmark.cli run --category coding --languages en,ko

# 翻訳モード（プラグイン効果検証）
python -m benchmark.cli run --languages ko,ja --mode translated --trials 3

# テストケース一覧
python -m benchmark.cli list-cases

# 既存結果の分析
python -m benchmark.cli analyze --results-dir ./results/2026-04-09_120000

# レポート生成
python -m benchmark.cli report --results-dir ./results/2026-04-09_120000 --format html
```

### 3. 翻訳プラグインのインストール

```bash
cd plugin
claude plugin install .
```

または `~/.claude/settings.json` に手動追加:

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

### 4. プラグイン設定

環境変数で制御します:

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `TRANSLATOR_ENABLED` | `true` | プラグインの有効化/無効化 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 翻訳用モデル |
| `TRANSLATOR_TIMEOUT` | `6000` | 翻訳APIタイムアウト（ms） |
| `TRANSLATOR_DEBUG` | - | デバッグログの有効化 |

## ベンチマークテストケース

4カテゴリ、計40テスト（Easy 3、Medium 4、Hard 3）:

| カテゴリ | 範囲 | トピック |
|----------|------|----------|
| **Coding** | TC-CODE-001~010 | アルゴリズム、データ構造、非同期パターン |
| **API Usage** | TC-API-001~010 | REST、SDK、認証、決済、GraphQL |
| **Debugging** | TC-DEBUG-001~010 | バグ修正、メモリリーク、競合状態 |
| **Architecture** | TC-ARCH-001~010 | デザインパターン、システム設計、分散システム |

## 翻訳プラグインの動作原理

```
ユーザーが日本語で入力
    ↓
UserPromptSubmitフックがトリガー
    ↓
Unicode基準の言語検出（<1ms）
    ↓（非英語を検出）
Claude Haikuで英語に翻訳（〜2-3秒）
    ↓
additionalContextとして翻訳を注入
    ↓
Claudeが英語翻訳を基に推論 → 日本語で応答
```

主な特徴:
- **依存関係ゼロの言語検出**: Unicode範囲チェック、外部ライブラリ不要
- **グレースフルデグラデーション**: 翻訳失敗時は原文のまま通過（ブロッキングなし）
- **コード保持**: コードブロック、ファイルパス、変数名は翻訳しない

## 3-Way比較

プラグインの実際の効果を3-way比較で検証します:

| モード | 説明 |
|--------|------|
| **EN-native** | 英語プロンプト → Claude |
| **KO-native** | 韓国語プロンプト → Claude |
| **KO-translated** | 韓国語 → Haiku翻訳 → 英語 → Claude |

`--mode translated` でKO-translatedをベンチマークし、EN-native品質にどれだけ近づくか確認します。

## テスト結果

### 言語検出テスト（10/10合格）

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

エッジケースの処理:
- コードが多い日本語プロンプト → 日本語を正常に検出
- 混在言語（日本語 + 英語の技術用語）→ 日本語として正確に検出
- 純粋なコードブロック → 英語として識別（翻訳をスキップ）
- 空の入力 → エラーなく通過

---

## 問題: 非英語プロンプトの品質低下

LLMは主に英語データで学習されています。韓国語・日本語・中国語でプロンプトを入力すると、次のような問題が繰り返し発生します:

| 問題 | 発生する現象 |
|------|-------------|
| **意図の誤解** | 日本語の文法構造と省略された主語により、要件を誤って理解する |
| **APIのハルシネーション** | 非英語プロンプトでは、架空の関数名やパラメータの生成が増加する |
| **古いパターンの使用** | deprecatedなライブラリやPython 2スタイルのコードが増える |
| **要件の欠落** | 日本語で表現された細かい制約が暗黙のうちに無視される |
| **コード品質の低下** | バグ、off-by-oneエラー、未処理の例外が増加する |

この精度の差は、モデルの推論が英語のトークン列に最適化されているためです。日本語プロンプトは、モデルを学習量が少ないパスに強制します。

## 解決策: プラグインの仕組み

プラグインはすべての非英語プロンプトを傍受し、Claude Haikuで英語に翻訳してから、翻訳文を**主要な推論入力**として注入します — すべて透過的に、3秒以内で完了します。

```
┌─────────────────────────────────────────────────────────┐
│  日本語（または韓国語、中国語）で入力                      │
│                                                         │
│  "FastAPI로 JWT 인증이 포함된 REST API를 만들어줘.       │
│   에러 핸들링하고 Pydantic v2 모델 써줘"                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  [Plugin: translate-hook.mjs]                           │
│                                                         │
│  1. 言語検出: ko (信頼度: 0.87)                  <1ms   │
│  2. Claude Haikuが英語に翻訳:                    ~2s    │
│                                                         │
│     "Create a REST API with JWT authentication          │
│      using FastAPI. Include error handling and           │
│      use Pydantic v2 models."                           │
│                                                         │
│  3. 英語翻訳をadditionalContextとして注入                │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Claudeが英語で推論 → 日本語で応答                       │
│                                                         │
│  ✓ 正確な意図: FastAPI + JWT + エラーハンドリング        │
│  ✓ ハルシネーションなし: 実在ライブラリ、実在API          │
│  ✓ モダンなコード: Pydantic v2、python-jose、最新構文    │
│  ✓ 応答言語: 日本語を維持（UX保持）                      │
└─────────────────────────────────────────────────────────┘
```

## 使用例

### 例1: 複雑なコーディングタスク

**プラグインなし** — 日本語プロンプトがClaudeに直接送信:
```
入力: "비동기 레이트 리미터를 토큰 버킷 알고리즘으로 구현해줘. 
      슬라이딩 윈도우도 지원하고 Redis 백엔드 옵션도 넣어줘"

❌ 想定される問題:
  - 「トークンバケット」の誤解による不完全な実装
  - RedisインテグレーションでdeprecatedなRedis-pyパターンを使用
  - スライディングウィンドウロジックにoff-by-oneバグ
  - asyncコンテキストマネージャのサポートが欠落
```

**プラグイン適用後** — 翻訳してから処理:
```
入力: (同じプロンプト)
      ↓
翻訳: "Implement an async rate limiter using the token bucket algorithm.
      Support sliding window and include a Redis backend option."
      ↓
✅ 結果:
  - asyncio.Lockを使った正確なトークンバケット実装
  - 最新のredis.asyncio APIを使用
  - 境界処理が正確なスライディングウィンドウ
  - 完全なasyncコンテキストマネージャプロトコル（__aenter__/__aexit__）
```

### 例2: デバッグタスク

**プラグインなし:**
```
入力: "이 코드에서 메모리 누수 원인 찾아줘. 파일 핸들이 
      제대로 닫히지 않는 것 같은데 asyncio 컨텍스트에서 
      어떻게 해결해야 하는지도 알려줘"

❌ 想定される問題:
  - 誤ったリーク原因の特定
  - 非同期コンテキストに同期的な修正を提案
  - asyncio特有のリソースクリーンアップパターンを見落とす
```

**プラグイン適用後:**
```
入力: (同じプロンプト)
      ↓
翻訳: "Find the memory leak in this code. File handles don't seem 
      to be closing properly. Also explain how to fix this in 
      an asyncio context."
      ↓
✅ 結果:
  - 未クローズのaiofilesハンドルを正確に特定
  - 適切なクリーンアップのためにasync withを提案
  - 構造化された並行処理のためにasyncio.TaskGroupを追加
```

### 例3: アーキテクチャの質問

**プラグインなし:**
```
入力: "마이크로서비스 간 이벤트 소싱 패턴을 설계해줘. 
      CQRS도 적용하고 eventual consistency 보장해야 해"

❌ 想定される問題:
  - 具体的な実装のない曖昧で一般的な設計
  - イベントソーシングとイベント駆動アーキテクチャの混同
  - 一貫性のための補償/サガパターンが欠落
```

**プラグイン適用後:**
```
入力: (同じプロンプト)
      ↓
翻訳: "Design an event sourcing pattern between microservices. 
      Apply CQRS and ensure eventual consistency."
      ↓
✅ 結果:
  - コマンド/クエリモデルの明確な分離
  - 適切なスナップショットを持つイベントストア
  - 分散トランザクションのためのサガパターン
  - Kafka/RabbitMQの例を含む具体的なコード
```

## パフォーマンスオーバーヘッド

| 項目 | 値 |
|------|-----|
| 言語検出 | < 1ms（Unicode範囲チェック、依存関係なし） |
| Haiku翻訳 | 〜2-3秒（APIコール1回） |
| フック全体のタイムアウト | 8秒（タイムアウト時は無音で通過） |
| プロンプトあたりのコスト | 〜$0.001（Haikuは非常に安価） |
| 英語プロンプト | 0msオーバーヘッド（即座に検出してスキップ） |

プラグインは非英語プロンプトに〜2-3秒を追加します。英語プロンプトはオーバーヘッドなしです。

## プラグインがしないこと

- **元のプロンプトを置き換えない** — 翻訳を補足コンテキストとして追加する方式
- **翻訳失敗時にブロックしない** — 元のプロンプトに自然にフォールスルー
- **コードを翻訳しない** — コードブロック、ファイルパス、変数名はそのまま保持
- **応答言語を変えない** — Claudeは引き続き日本語で応答

## ライセンス

MIT
