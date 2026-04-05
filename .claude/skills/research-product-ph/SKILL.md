---
name: research-product-ph
description: Shopee PH向けの商品リサーチ。フィリピン市場での競合調査・需要検証・仕入れ候補調査・販売規制チェックを一括実行する。
argument-hint: <商品名（日本語）>
---

# Shopee PH 商品リサーチ

対象商品: **$ARGUMENTS**

以下のステップを順番に実行し、最終的にスプレッドシートへの書き込みと調査レポートを出力する。

---

## Step 1: 英語キーワード生成

対象商品の英語検索キーワードを3〜5個生成する。
- 直訳キーワード
- フィリピンで使われそうな類義語・通称（タガログ語の通称があれば含める）
- ブランド名が分かれば含める

---

## Step 2: Shopee PH 競合調査（Claude in Chrome）

### 2-1: 売上順検索

生成した各キーワードでShopee PHを検索する。

```
https://shopee.ph/search?keyword=<キーワード>&sortBy=sales
```

各検索結果から以下を記録:
- 検索結果件数
- 上位商品の商品名・価格(PHP)・販売数・評価・出品者・出品元（国）
- 直接競合する商品があるか

### 2-2: 価格昇順検索（Shopee PH最低価格の記録）★必須★

**同じキーワードで価格昇順検索を必ず実行する。このステップは絶対にスキップしない。**

```
https://shopee.ph/search?keyword=<キーワード>&sortBy=price&order=asc
```

記録する情報:
- **日本発送品の最低価格** → スプレッドシート16列目「Shopee PH最低価格(PHP)」に記録
- 日本発送品がない場合は「なし (汎用品₱XX〜)」の形式で汎用品最低価格を記録
- 出荷元は商品カードの `location-Japan` / `location-Mainland China` 等で判別

記録形式の例:
- 日本発送あり: `₱245 (日本発送/ブランド名)`
- 日本発送なし: `なし (汎用品₱38〜)`
- ブランド競合なし: `なし (同一ブランド出品ゼロ)`

---

## Step 3: Lazada PH 需要検証（Claude in Chrome）

```
https://www.lazada.com.ph/catalog/?q=<キーワード>
```

記録する情報:
- 検索結果件数
- 上位商品の価格帯・販売数・レビュー数・出荷元
- 中国製の安物が多いか、日本製プレミアム品があるか
- **レビュー数100件以上の商品があれば需要確認済みと判断**

---

## Step 4: Amazon JP 仕入れ候補調査（Claude in Chrome）

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

## Step 5: 販売規制チェック

`research/prohibited_items.md` を読み込み、対象商品がPH（フィリピン）で販売規制に該当するか確認する。

該当する場合は明確に警告する。

---

## Step 6: 価格シミュレーション

各候補商品について以下を計算:
- Amazon JP仕入れ価格（円）
- 推奨PH販売価格（PHP）
- 概算利益: 販売価格 - 仕入れ価格 - 送料 - 手数料
  - Shopee手数料: 約6〜8%
  - 国際送料目安: 商品重量に応じて500〜2000円
  - 為替: 1 PHP = 約2.5円（調査時点で確認）
  - **PH利益目安: 300円/注文が良い方、1,000円で素晴らしいレベル**
  - 購買力が低いため高単価商品は売りにくい

### 価格設定の鉄則（PH市場固有）
- **安すぎると偽物と疑われて売れない**。PHは日本以上に偽物が多い市場で、型番商品が異常に安いと「偽物」と判断される
- **高すぎると購買力の壁に当たる**
- **推奨: 市場相場のちょっと下**に設定する。最安値勝負は逆効果
- 推奨販売価格を決める際は、Step 2-2で取得した既存競合の価格帯を参考に「相場のやや下」を狙う

---

## Step 7: 出力

### 7-1: Google Sheets書き込み

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
ws = sh.worksheet('PH')

# 既存ASINを取得して重複チェック（D列=ASIN）
existing_asins = set(ws.col_values(4)[1:])

# 書き込み日時
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# 追加する行データ（ASIN重複はスキップ）
rows = [
    # [書き込み日時, 商品名, メーカー, ASIN, Amazon JP URL, Amazon JP価格(円), Amazon JPレビュー数, 評価, 日本製, 推奨PH販売価格(PHP), Shopee PH競合状況, Lazada PH参考価格(PHP), 推奨英語タイトル, 推奨キーワード, 優先度, 備考, Shopee PH最低価格(PHP)]
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
- bashで `$` を含む文字列を扱う場合は `<< 'PYEOF'`（シングルクォート）で囲むこと

### 7-2: 調査レポート

以下の構成でサマリーを出力:

1. **結論**: この商品をShopee PHで販売すべきか（Go / No-Go / 要追加検証）
2. **需要の根拠**: Lazada PHの販売数・レビュー数など
3. **競合状況**: Shopee PHの空白度合い
4. **販売規制**: 該当する場合は明記
5. **推奨アクション**:
   - テスト出品する場合の最優先商品（1〜2個）
   - 推奨価格帯
   - 推奨キーワード・カテゴリ
   - PHの役割は注文数確保・Preferred Seller維持・商品テスト場であることを考慮

---

## 注意事項

### 絶対にスキップしないステップ（チェックリスト）
- [ ] **Step 2-2**: Shopee PH価格昇順検索 → 16列目「Shopee PH最低価格(PHP)」を記録
- [ ] **Step 3**: Lazada PH需要検証（レビュー数で需要判断）
- [ ] **Step 5**: 販売規制チェック（prohibited_items.md）
- [ ] **Step 7**: スプレッドシート書き込み時に16列目が空でないことを確認

### 判定ルール
- **Shopee PHで競合ゼロでも即「ブルーオーシャン」判定しない。** Shopee PH・Lazada PHの両プラットフォームを確認してから判定する
- **Shopdora等で同一商品が既に出品されていてlisting timeが3ヶ月以上経過しているのにsoldが0の場合、その商品は需要なし（No-Go）と判断する。** 「ブルーオーシャン」ではなく「需要が証明されていない」という扱いにすること
- **Amazonの売れ筋上位をそのまま出品するのはNG。** 他セドラーと被り価格競争に巻き込まれる。PHに供給が少ないニッチ商品を優先する
- **利益ゼロでも消費税還付（10%）で回収可能**という観点も持つ。ただし還付前提で赤字商品を出すのは推奨しない

### 広告・セール戦略メモ
- Go判定の商品は、テスト出品後に**少額広告（数百円〜）でも効果あり**。セドラーの大半は広告を出さないため、少額でも上位表示されレビュー蓄積が加速する
- **ビッグセール前の小セールで先に仕入れておく**。ビッグセール時はAmazon JP発送が遅延しがちなので、事前仕入れで差別化できる

### ブラウザ検索の効率化（Claude in Chrome）
- Claude in Chromeが使えない場合はWebFetchで代替する
- ブラウザ拡張が切断された場合は `tabs_context_mcp` で再接続を試みる
- **`get_page_text` は Shopee の検索結果ページで不安定**（生HTMLが返る場合がある）。`read_page` のアクセシビリティツリーの方が確実
- `read_page` は `depth=3-4` + `ref_id` で商品リスト要素にフォーカスすると効率的
- 商品カード内の価格: `generic "promotion price"` の次の `generic "X.XX"` に表示される
- 出荷元: `generic "location-Japan"` / `generic "location-Mainland China"` 等で判別
- **`locations=Japan` URLパラメータは信頼性が低い** → 全結果を見て手動フィルタする
- 1カテゴリの検索は最大2-3回のページ読み込みで完了させる
- 販売規制ファイルが存在しない場合はスキップし、手動確認を推奨する
