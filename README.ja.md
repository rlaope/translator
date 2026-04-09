# 多言語LLM精度ベンチマーク & プロンプト翻訳プラグイン

> **[English](README.md)** | **[한국어](README.kr.md)** | **[中文](README.zh.md)**

Claudeに韓国語・日本語のプロンプトを入力した場合、英語と比較して精度が低下するという仮説を**定量的に検証**し、これを解決するための**自動翻訳Claude Codeプラグイン**を提供します。

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
python -m benchmark.cli run --category coding --languages en,ja

# 翻訳モード（プラグイン効果検証）
python -m benchmark.cli run --languages ko,ja --mode translated --trials 3

# テストケース一覧
python -m benchmark.cli list-cases
```

### 3. 翻訳プラグインのインストール

```bash
cd plugin
claude plugin install .
```

または `~/.claude/settings.json` に手動追加：

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

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `TRANSLATOR_ENABLED` | `true` | プラグインの有効化/無効化 |
| `TRANSLATOR_MODEL` | `claude-haiku-4-5-20251001` | 翻訳用モデル |
| `TRANSLATOR_TIMEOUT` | `6000` | 翻訳APIタイムアウト（ms） |
| `TRANSLATOR_DEBUG` | - | デバッグログの有効化 |

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

主な特徴：
- **依存関係ゼロの言語検出**：Unicode範囲チェック、外部ライブラリ不要
- **グレースフルデグラデーション**：翻訳失敗時は原文のまま通過（ブロッキングなし）
- **コード保持**：コードブロック、ファイルパス、変数名は翻訳しない

## 3-Way比較

| モード | 説明 |
|--------|------|
| **EN-native** | 英語プロンプト → Claude |
| **JA-native** | 日本語プロンプト → Claude |
| **JA-translated** | 日本語 → Haiku翻訳 → 英語 → Claude |

**JA-translated**が**EN-native**に近づくほど、プラグインの効果が高いことを示します。

## テスト結果

### 言語検出テスト（10/10合格）

```
✓ "파이썬으로 정렬 알고리즘을 구현해주세요..."        → ko (1.00)
✓ "Pythonでソートアルゴリズムを実装してください..."     → ja (1.00)
✓ "Implement a sorting algorithm in Python..."      → en (1.00)
✓ "다음 코드에서 버그를 찾아주세요: ```python..."     → ko (1.00)
✓ "ReactコンポーネントでuseStateフックを..."          → ja (1.00)
✓ "FastAPI로 REST API endpoint를 만들어서..."        → ko (0.73)
✓ "Read the file at /Users/test/src/main.py..."     → en (1.00)
✓ "" (空入力)                                        → en (1.00)
✓ "```python\nprint('hello')\n```" (コードのみ)      → en (1.00)
✓ "请用Python实现一个排序算法..."                      → zh (1.00)

10 passed, 0 failed
```

### ベンチマーク検証

```
合計: 40
  coding:       10 ✓
  api_usage:    10 ✓
  debugging:    10 ✓
  architecture: 10 ✓
全3言語（en/ko/ja）チェック: PASS
```

---

## Before / After：プラグイン適用効果

### Before（未適用）

```
ユーザー: "FastAPIでJWT認証付きのREST APIを作成してください"
    ↓
Claude: 日本語プロンプトを直接処理
    ↓
問題: 意図誤解↑、ハルシネーション↑、deprecated API↑
```

### After（適用後）

```
ユーザー: "FastAPIでJWT認証付きのREST APIを作成してください"
    ↓
[translate-hook] 検出: ja (0.95) → Haiku翻訳（〜2秒）
    ↓
"Create a REST API with JWT authentication using FastAPI"
    ↓
Claude: 英語ベースの推論 → 日本語で応答
    ↓
改善: 意図理解↑、ハルシネーション↓、最新パターン↑
```

### パフォーマンスオーバーヘッド

| 項目 | 値 |
|------|-----|
| 言語検出 | < 1ms |
| Haiku翻訳 | 〜2-3秒 |
| 全体タイムアウト | 8秒（超過時は原文通過） |
| 追加コスト | 〜$0.001/呼び出し |

## ライセンス

MIT
