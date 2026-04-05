---
name: research-product
description: Shopee越境EC向けの商品リサーチ。競合調査・需要検証・仕入れ候補調査・販売規制チェックを一括実行する。
argument-hint: <商品名（日本語）>
---

# Shopee越境EC 商品リサーチ

対象商品: **$ARGUMENTS**

以下のステップを順番に実行し、最終的にスプレッドシートへの書き込みと調査レポートを出力する。

---

## Step 1: 英語キーワード生成

対象商品の英語検索キーワードを3〜5個生成する。
- 直訳キーワード
- 現地で使われそうな類義語・通称
- ブランド名が分かれば含める

---

## Step 2: Shopee SG 競合調査（Claude in Chrome）

### 2-1: 売上順検索

生成した各キーワードでShopee SGを検索する。

```
https://shopee.sg/search?keyword=<キーワード>&sortBy=sales
```

各検索結果から以下を記録:
- 検索結果件数
- 上位商品の商品名・価格(SGD)・販売数・評価・出品者・出品元（国）
- 直接競合する商品があるか

### 2-2: 価格昇順検索（Shopee SG最低価格の記録）★必須★

**同じキーワードで価格昇順検索を必ず実行する。このステップは絶対にスキップしない。**

```
https://shopee.sg/search?keyword=<キーワード>&sortBy=price&order=asc
```

記録する情報:
- **日本発送品の最低価格** → スプレッドシート16列目「Shopee SG最低価格(SGD)」に記録
- 日本発送品がない場合は「なし (汎用品$X.XX〜)」の形式で汎用品最低価格を記録
- 出荷元は商品カードの `location-Japan` / `location-Mainland China` 等で判別

記録形式の例:
- 日本発送あり: `5.45 (日本発送/白檀)`
- 日本発送なし: `なし (汎用品$0.76〜)`
- ブランド競合なし: `なし (同一ブランド出品ゼロ)`

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

**スプレッドシートに直接書き込む。CSVファイルは作成しない。**

スプレッドシートURL: `https://docs.google.com/spreadsheets/d/1GuLMA2mZN1RXWlakrxYsM8uvvU9BXG83SKjTR89uIk8/`

```bash
# gspreadで直接書き込み
tool/.venv/bin/python3 << 'PYEOF'
import gspread, json
from pathlib import Path
from datetime import datetime
creds = Path('tool/credentials/gcp_service_account.json')
config = json.loads(Path('tool/sheets_config.json').read_text())
client = gspread.service_account(filename=str(creds))
sh = client.open_by_key(config['spreadsheet_id'])
ws = sh.worksheet('SG')

# 既存ASINを取得して重複チェック（D列=ASIN）
existing_asins = set(ws.col_values(4)[1:])

# 書き込み日時
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# 追加する行データ（ASIN重複はスキップ）
rows = [
    # [書き込み日時, 商品名, メーカー, ASIN, Amazon JP URL, Amazon JP価格(円), Amazon JPレビュー数, 評価, 日本製, 推奨SG販売価格(SGD), Shopee SG競合状況, Amazon SG参考価格(SGD), 推奨英語タイトル, 推奨キーワード, 優先度, 備考]
]

added = 0
for row in rows:
    if row[3] not in existing_asins:  # ASIN is now at index 3
        ws.append_row(row, value_input_option='USER_ENTERED')
        added += 1

print(f'Done: {added} added, {len(rows) - added} skipped (duplicate)')
PYEOF
```

**重要:**
- 既存データは絶対に削除しない（追記のみ）
- ASIN重複は自動スキップする
- research/ディレクトリにCSVは保存しない（スプレッドシートが唯一のデータソース）
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

## 注意事項

### 絶対にスキップしないステップ（チェックリスト）
- [ ] **Step 2-2**: Shopee SG価格昇順検索 → 16列目「Shopee SG最低価格(SGD)」を記録
- [ ] **Step 3**: Amazon SG需要検証
- [ ] **Step 4**: Lazada SG競合調査
- [ ] **Step 6**: 販売規制チェック（prohibited_items.md）
- [ ] **Step 8**: スプレッドシート書き込み時に16列目が空でないことを確認

### ブラウザ操作Tips
- Claude in Chromeが使えない場合はWebFetchで代替する
- ブラウザ拡張が切断された場合は `tabs_context_mcp` で再接続を試みる
- **`get_page_text` は Shopee SG の検索結果ページで不安定**（生HTMLソースが返る場合がある）。JavaScriptで `[data-sqe="item"]` の `innerText` を取得する方が確実
- **`locations=Japan` URLパラメータは信頼性が低い**（結果が空になることが多い）。代わりに全結果を見て出荷元をフィルタする

### 判定ルール
- **Shopee SGで競合ゼロでも即「ブルーオーシャン」判定しない。** Lazada SG・Amazon SGの3プラットフォームを確認してから判定する
- **Shopdora等で同一商品が既に出品されていてlisting timeが3ヶ月以上経過しているのにsoldが0の場合、その商品は需要なし（No-Go）と判断する。** 「ブルーオーシャン」ではなく「需要が証明されていない」という扱いにすること

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
