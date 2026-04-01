---
name: research-product
description: Shopee越境EC向けの商品リサーチ。競合調査・需要検証・仕入れ候補調査・販売規制チェックを一括実行する。
argument-hint: <商品名（日本語）>
---

# Shopee越境EC 商品リサーチ

対象商品: **$ARGUMENTS**

以下のステップを順番に実行し、最終的にCSVと調査レポートを出力する。

---

## Step 1: 英語キーワード生成

対象商品の英語検索キーワードを3〜5個生成する。
- 直訳キーワード
- 現地で使われそうな類義語・通称
- ブランド名が分かれば含める

---

## Step 2: Shopee SG 競合調査（Claude in Chrome）

生成した各キーワードでShopee SGを検索する。

```
https://shopee.sg/search?keyword=<キーワード>
```

各検索結果から以下を記録:
- 検索結果件数
- 上位商品の商品名・価格(SGD)・販売数・評価・出品者・出品元（国）
- 直接競合する商品があるか

---

## Step 3: Amazon SG 需要検証（Claude in Chrome）

同じキーワードでAmazon SGを検索する。

```
https://www.amazon.sg/s?k=<キーワード>
```

記録する情報:
- 検索結果件数
- 上位商品の商品名・価格(SGD)・レビュー数・評価
- **レビュー数100件以上の商品があれば需要確認済みと判断**

---

## Step 4: Lazada SG 競合調査（Claude in Chrome）

```
https://www.lazada.sg/catalog/?q=<キーワード>
```

記録する情報:
- 検索結果件数
- 上位商品の価格帯・販売数・出荷元（中国/SG/日本）
- 中国製の安物が多いか、日本製プレミアム品があるか

---

## Step 5: Amazon JP 仕入れ候補調査（Claude in Chrome）

日本語キーワードでAmazon JPを検索する。

```
https://www.amazon.co.jp/s?k=<日本語キーワード>
```

記録する情報:
- 商品名（日本語）
- メーカー/ブランド
- ASIN
- 価格（円）
- レビュー数・評価
- Amazon JPランキング
- 日本製かどうか
- サイズ・重量（送料計算用）

上位5〜7商品を候補としてリストアップする。

---

## Step 6: 販売規制チェック

`research/prohibited_items.md` を読み込み、対象商品が以下の国で販売規制に該当するか確認する:
- SG（シンガポール）
- PH（フィリピン）
- TW（台湾）
- MY（マレーシア）
- TH（タイ）

該当する場合は明確に警告する。

---

## Step 7: 価格シミュレーション

各候補商品について以下を計算:
- Amazon JP仕入れ価格（円）
- 推奨SG販売価格（SGD）: Amazon SG競合価格を参考に設定
- 概算利益率: (販売価格 - 仕入れ価格 - 送料 - 手数料) / 販売価格
  - Shopee手数料: 約6〜8%
  - 国際送料目安: 商品重量に応じて500〜2000円
  - 為替: 1 SGD = 約110円（調査時点で確認）

---

## Step 8: 出力

### 8-1: Google Sheets書き込み

**スプレッドシートに直接書き込む。毎回CSVに書き出す必要はない。**

スプレッドシートID: `1GuLMA2mZN1RXWlakrxYsM8uvvU9BXG83SKjTR89uIk8`（SGシート）

```bash
# 方法1: CSVを一時保存してから書き込み（大量データの場合）
tool/.venv/bin/python3 tool/sheets.py write research/sg_<商品カテゴリ>_candidates.csv --market SG

# 方法2: gspreadで直接書き込み（少量データや価格更新の場合）
tool/.venv/bin/python3 << 'PYEOF'
import gspread, json
from pathlib import Path
creds = Path('tool/credentials/gcp_service_account.json')
config = json.loads(Path('tool/sheets_config.json').read_text())
client = gspread.service_account(filename=str(creds))
sh = client.open_by_key(config['spreadsheet_id'])
ws = sh.worksheet('SG')
# ws.append_row([...]) or ws.update_cell(row, col, value)
PYEOF
```

**重要:**
- 既存データは絶対に削除しない（追記のみ）
- ASIN重複は `sheets.py write` で自動スキップされる
- bashで `$` を含む文字列を扱う場合は `<< 'PYEOF'`（シングルクォート）で囲むこと（`$0.76` 等が変数展開されるのを防ぐ）

### 8-2: 調査レポート

以下の構成でサマリーを出力:

1. **結論**: この商品をShopee SGで販売すべきか（Go / No-Go / 要追加検証）
2. **需要の根拠**: Amazon SGのレビュー数、Lazadaの販売数など
3. **競合状況**: Shopee SGの空白度合い
4. **販売規制**: 該当する場合は明記
5. **推奨アクション**:
   - テスト出品する場合の最優先商品（1〜2個）
   - 推奨価格帯
   - 推奨キーワード・カテゴリ

---

## Step 9: Shopee SG 競合最低価格調査

Step 2 のShopee SG検索結果から、**日本発送の最低価格**を「Shopee SG最低価格(SGD)」カラム（16列目）に記録する。

### 検索手順
1. `https://shopee.sg/search?keyword=<英語キーワード>&sortBy=price&order=asc` で価格昇順検索
2. 各商品カードの `location-` 表示で出荷元を確認（Japan / Mainland China / SG etc.）
3. 日本発送品があれば最低価格を記録
4. 日本発送品がなければ「なし (汎用品$X.XX〜)」の形式で汎用品の最低価格を記録

### ブラウザ検索の効率化
- **`get_page_text` は Shopee SG の検索結果ページで不安定**（生HTMLソースが返る場合がある）。`read_page` のアクセシビリティツリーの方が確実
- `read_page` は `depth=3-4` + `ref_id` で商品リスト要素にフォーカスすると効率的
- 商品カード内の価格は `generic "promotion price"` の次の `generic "X.XX"` に表示される
- 出荷元は `generic "location-Japan"` / `generic "location-Mainland China"` 等で判別
- **`locations=Japan` URLパラメータは信頼性が低い**（結果が空になることが多い）。代わりに全結果を見て手動で出荷元をフィルタする
- 1カテゴリの検索は最大2-3回のページ読み込みで完了させる

### 競合価格の記録形式
- 日本発送あり: `5.45 (日本発送/白檀)` — 数値 + 出荷元 + 商品種別
- 日本発送なし: `なし (汎用品$0.76〜)` — 最安の汎用品価格を参考値として記載
- ブランド競合なし: `なし (SUWADA出品ゼロ)` — 同一ブランドの出品がゼロの場合

---

## 注意事項

- Claude in Chromeが使えない場合はWebFetchで代替する
- ブラウザ拡張が切断された場合は `tabs_context_mcp` で再接続を試みる
- 販売規制ファイルが存在しない場合はスキップし、手動確認を推奨する
- スクリーンショットは必要に応じて取得し、ユーザーに共有する
- **Step 3（Amazon SG）・Step 4（Lazada SG）は絶対にスキップしない。** Shopee SGで競合ゼロでも、Lazada SGやAmazon SGに同一商品が安く出ている場合がある。「ブルーオーシャン」判定はShopee SG・Lazada SG・Amazon SGの3プラットフォームを確認してから下すこと。
- カテゴリ一括調査（複数キーワードスキャン）時も、有望候補が見つかったら必ず3プラットフォームでクロスチェックしてから最終判定する
- **Shopdora等で同一商品が既に出品されていてlisting timeが3ヶ月以上経過しているのにsoldが0の場合、その商品は需要なし（No-Go）と判断する。** 「ブルーオーシャン」ではなく「需要が証明されていない」という扱いにすること。

---

## Shopee SGの競合価格帯（既知データ・2026年4月時点）

以下は調査済みの参考データ。新しいカテゴリを調べる際の目安として使う。

| カテゴリ | 日本発送最安 | 汎用品最安 | 備考 |
|----------|------------|-----------|------|
| 白檀お香 | $5.45 | $3〜 | 日本発送の仏壇の森が最安 |
| 耳かき | $2.07〜$5.19 | $0.50〜 | GB/KAI製品が日本発送で出品あり |
| 鼻毛はさみ/カッター | なし | $0.76 | 中国製が大量出品。日本発送ゼロ |
| フットケア（角質・かかと） | なし | $1.71 | 日本製フットケアは空白 |
| 茶筅 | なし | $1.75 | 中国製レプリカが$1.75〜。日本製なし |
| 若狭塗箸 | なし | $0.65 | 伝統工芸箸は出品ゼロ |
| Pilot Cocoon万年筆 | $21.60 | — | 日本発送の競合多数 |
| SUWADA爪切り | なし | — | 完全ブルーオーシャン |
| GB匠の技ニッパー爪切り | なし（通常型$6.54） | $2.32 | ニッパー型・巻き爪型は空白 |
| KAI巻き爪用 | なし | $2.32 | 巻き爪専用品は空白 |
