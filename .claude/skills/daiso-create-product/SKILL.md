---
name: daiso-create-product
description: ダイソーネットストアなど仕入れ先の商品URLから、商品管理システム(pm-8rm)に新規商品を登録する。URL/商品名/説明/仕入れ値/重量/画像/JAN/原産国/材質/Shopeeカテゴリ/バリエーション/販売価格を一括セットアップ。
argument-hint: <仕入れ先商品URL（例: https://jp.daisonet.com/products/4550480218748）>
---

# ダイソー商品 新規登録スキル

対象URL: **$ARGUMENTS**

> **API 参照**: 商品データの送信には pm-8rm API を使用する。詳細は [lib/pm-api.md](../lib/pm-api.md) を参照。

**重要: pm-8rm への登録は全工程 Bash + Python による API 呼び出しで行う。pm-8rm のブラウザタブを開く必要は一切ない。**

---

## 引数の解釈

- 仕入れ先商品URL（ダイソーネットストア・Amazon等）を受け取る
- URLが指定されていない場合は「登録する商品の仕入れ先URLを教えてください」と質問して待つ
- 複数URLがカンマ/改行区切りで渡された場合は1商品ずつ順番に処理する

---

## 前提・ツール

| 操作 | 手段 |
|------|------|
| 仕入れ先ページのスクレイピング | WebFetch または Claude in Chrome（`javascript_tool`）|
| pm-8rm への全操作 | **Python `requests`**（API キー認証）|
| 日→英 翻訳 | **Claude が直接実行** |
| 画像加工 | **API**: `POST /api/products/{id}/process-main-image` |
| カテゴリ推薦 | **API**: `POST /api/shopee/products/category-recommend` |

### 共通プリアンブル（各 Python 実行の冒頭で必ず実行）

```python
import os, requests

api_key = os.environ.get("PM_API_KEY", "")
if not api_key:
    import subprocess
    r = subprocess.run(
        'bash -c "set -a && source /Users/kyosukeishida/Projects/buendia/shopee-marketing/.env && set +a && echo $PM_API_KEY"',
        shell=True, capture_output=True, text=True,
    )
    api_key = r.stdout.strip()

BASE = "https://pm-backend-ts4d.onrender.com"
HEADERS = {"X-Api-Key": api_key} if api_key else {}
```

---

## Step 1: 仕入れ先ページから情報収集

`WebFetch` または Claude in Chrome で商品ページから以下を取得する:

| フィールド | 取得方法 |
|-----------|----------|
| **商品名** | h1 またはページタイトル |
| **税込価格** | `税込○○円` 表記（仕入れ値） |
| **JANコード** | 説明文内または URL のパス末尾数字列 |
| **説明文** | 全文（原産国・材質・サイズ含む） |
| **原産国** | 説明文から抽出 |
| **材質** | 説明文から抽出 |
| **画像URL 1** | `og:image` の値（**必ず `https://` で始まること**。`http://` なら `https://` に置換） |
| **追加画像** | 2〜8枚（あれば） |

### 重量の推定基準

| 商品サイズ感 | 重量 (kg) |
|-------------|-----------|
| 小物・雑貨（コーム・ネット等） | 0.05〜0.1 |
| ヘアケア・プラスチック中型 | 0.1〜0.2 |
| キッチン・ツール類 | 0.2〜0.5 |

---

## Step 2: 日→英 翻訳（Claude が直接実行）

| 日本語 | 英語 |
|--------|------|
| 商品名 | `DAISO Japan [EN Name] \| Directly Shipping from Japan \| Kios Store` |
| 説明文 | 全文英訳（`Country of Origin:`, `Material:` 等） |
| 原産国 | 中国→China / ベトナム→Vietnam / 日本→Japan |
| 材質 | 化学名を英訳（ポリプロピレン→Polypropylene 等） |

### 商品名フォーマット（必須）

```
日本語: DAISO Japan [商品名]  Directly ship from Japan
英語:  DAISO Japan [英語名] | Directly Shipping from Japan | Kios Store
```

---

## Step 3: カテゴリ選定

### A. 既知カテゴリ表（優先）

| 商品ジャンル | カテゴリ ID | パス |
|------------|------------|------|
| ヘアブラシ・コーム | 101664 | Beauty > Beauty Tools > Hair Tools > Brushes & Combs |
| ヘアクリップ・スタイリング | 100873 | Beauty > Hair Care > Hair Styling |
| ヘアトリートメント | 100871 | Beauty > Hair Care > Hair Treatment |
| ヘアケアその他 | 100874 | Beauty > Hair Care > Others |
| アイラッシュカーラー | 101655 | Beauty > Makeup > Eyes > Eyelash Curlers |
| 洗濯・クリーニング布 | 101209 | Home & Living > Home Care Supplies > Cleaning Cloths |
| ドアロック・建具 | 101251 | Home & Living > Home Improvement > Door Hardware & Locks |
| 爪ケアツール | 102034 | Beauty > Hand, Foot & Nail Care > Nail Care > Manicure Tools |
| スナック・乾燥食品 | 100866 | Food & Beverages > Snacks > Dried Snacks > Others |

### B. API によるカテゴリ推薦（A で不明な場合）

```python
rec = requests.post(
    f"{BASE}/api/shopee/products/category-recommend",
    json={"name": name_en, "description": description_en},
    headers=HEADERS,
)
rec.raise_for_status()
print(rec.json())
# → 推薦結果から最適な category_id を選択する
```

---

## Step 4: 商品一括登録（POST /api/products/insert）

翻訳済みテキスト・JAN・原産国・Shopeeカテゴリを **1 回の API で** 登録する。

```python
import time

jan         = "[JANコード]"
cost        = [仕入れ値（int）]
weight      = [重量（float）]
category_id = [選定したカテゴリID]
rakuten_id  = f"daiso-{jan}" if jan else f"daiso-{int(time.time())}"

payload = [{
    "rakuten_product_id":            rakuten_id,
    "name":                          "DAISO Japan [商品名]  Directly ship from Japan",
    "name_ja":                       "DAISO Japan [商品名]  Directly ship from Japan",
    "name_en":                       "DAISO Japan [英語名] | Directly Shipping from Japan | Kios Store",
    "description":                   "[説明文（日本語）]",
    "description_ja":                "[説明文（日本語）]",
    "description_en":                "[説明文（英語）]",
    "product_no":                    jan or rakuten_id,
    "product_url":                   "[仕入れ先URL]",
    "brandName":                     "DAISO",
    "average_price":                 float(cost),
    "used_exclude_sales_min_price":  0.0,
    "used_exclude_sales_max_price":  0.0,
    "used_exclude_sales_item_count": 0,
    "genre_id":                      "",
    "genre_name":                    "",
    "mediumImageUrl":                "[画像URL1（https://）]",
    "image_2":                       [画像URL2 or None],
    "image_3":                       [画像URL3 or None],
    "jan_code":                      jan,
    "country_of_origin_ja":          "[原産国（日本語）]",
    "country_of_origin_en":          "[Country of Origin]",
    "ingredients_ja":                "[材質（日本語）]",
    "ingredients_en":                "[Material（英語）]",
    "shop_category_settings": [
        {"shop_id": 1418317116, "category_id": category_id, "attribute_list": []},
        {"shop_id": 1425845298, "category_id": category_id, "attribute_list": []},
    ],
    "variations": [{
        "option_name_ja": "スタンダード",
        "option_name_en": "Standard",
        "stock":          100,
        "weight":         weight,
        "cost_price":     cost,
        "price_sgd":      2.5,
        "price_php":      109,
    }],
}]

resp = requests.post(f"{BASE}/api/products/insert", json=payload, headers=HEADERS)
resp.raise_for_status()

product    = resp.json()["products"][0]
product_id = product["id"]
print(f"product_id: {product_id}")
print(f"shopee_sku: {product.get('shopee_sku')}")
```

---

## Step 5: 画像加工（POST /api/products/{id}/process-main-image）

加工成功時は `mediumImageUrl` を返却された URL に PUT で更新する。失敗してもそのまま次へ進む。

```python
img_resp = requests.post(
    f"{BASE}/api/products/{product_id}/process-main-image",
    headers=HEADERS,
)

if img_resp.status_code == 200:
    processed_url = img_resp.json().get("mediumImageUrl", "")
    print(f"加工済み画像URL: {processed_url}")

    # 加工済みURLを保存
    requests.put(
        f"{BASE}/api/products/update",
        json={"id": product_id, "mediumImageUrl": processed_url},
        headers=HEADERS,
    ).raise_for_status()
else:
    processed_url = None
    print(f"画像加工失敗（スキップ）: {img_resp.text}")
```

**エラー時の注意:** 失敗した場合は再試行せずそのまま次の Step に進む。完了レポートに失敗理由を記載する。

---

## Step 6: 最終確認・完了レポート

```
商品ID: [product_id]
URL: https://pm-8rm.pages.dev/products/[product_id]
```

| 項目 | 値 |
|------|-----|
| 商品ID | [product_id] |
| 商品名（日本語） | DAISO Japan [名前]  Directly ship from Japan |
| 商品名（英語） | DAISO Japan [英語名] \| ... \| Kios Store |
| 仕入れ値 | ¥[cost_price] |
| 重量 | [weight]kg |
| JAN | [jan_code] |
| 原産国 | [ja] / [en] |
| カテゴリ (PH/SG) | [category_id] ([path]) |
| SG価格 | 2.5 SGD |
| PH価格 | 109 PHP |
| 画像加工 | 完了 / 失敗（理由） |
| 状態 | 保存済み / Shopee未公開 |

---

## 価格ルール（共通）

**ダイソー110円商品のテスト価格（ユーザー指定・変更禁止）:**
- SG: `2.5` SGD
- PH: `109` PHP

ユーザーから別指示がある場合のみ変更する。**220円商品も同じテスト価格**（ユーザー指定）。

---

## Shopee公開（任意・ユーザー確認後）

**必ずユーザーの明示的な指示を待ってから実行する。**（API 未調査のため現時点では対応外）

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| insert が 401 | `.env` の PM_API_KEY が正しいか確認 |
| insert が 422 | name / product_url / rakuten_product_id が空でないか確認 |
| KeyError: 'products'（insert） | 同一 JAN で既登録（rakuten_product_id 重複） |
| process-main-image が 500「ダウンロード失敗」 | 失敗してもそのまま次へ進む |
| カテゴリ推薦が空 | name_en / description_en を渡しているか確認 |
| その他 API エラー | エラー内容をユーザーに報告する |

---

## よく使う値のリファレンス

| 項目 | 典型値 |
|------|--------|
| 仕入れ値 | 110 / 220 / 330 / 550 円 |
| 重量 | 0.05〜0.1 (小物) / 0.1〜0.2 (中型) / 0.2〜0.5 (大型) |
| PH shop_id | `1418317116` |
| SG shop_id | `1425845298` |
| SG価格（110/220円） | `2.5` |
| PH価格（110/220円） | `109` |
