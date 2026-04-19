# pm-8rm API クライアント リファレンス

pm-8rm 商品管理システムのバックエンド API を直接呼び出すためのリファレンス。
**全操作を Python `requests` で行う。ブラウザ操作（pm-8rm タブを開く・JavaScript 実行）は不要。**

---

## 基本情報

| 項目 | 値 |
|------|-----|
| バックエンドURL | `https://pm-backend-ts4d.onrender.com` |
| 認証方式 | `X-Api-Key: <PM_API_KEY>` |
| Content-Type | `application/json` |

---

## 認証: API キー

API キーはプロジェクトルート `.env` に保存している:

```
PM_API_KEY=xxxxxxxxxxxx
```

`.env` は `.gitignore` 済み。

### 共通プリアンブル

**重要**: `subprocess.run` は argv 配列で渡す。`shell=True` + 単一文字列にすると、外側の sh が `$PM_API_KEY` を先に空展開してしまうため API キーが取得できない。

```python
import os, requests, subprocess

api_key = os.environ.get("PM_API_KEY", "")
if not api_key:
    r = subprocess.run(
        ['bash', '-c',
         'set -a && source /Users/kyosukeishida/Projects/buendia/shopee-marketing/.env && set +a && echo "$PM_API_KEY"'],
        capture_output=True, text=True,
    )
    api_key = r.stdout.strip()

BASE = "https://pm-backend-ts4d.onrender.com"
HEADERS = {"X-Api-Key": api_key} if api_key else {}
```

---

## エンドポイント

### POST /api/products/insert — 商品一括登録

**ボディは JSON 配列 `[{...}]` 形式。**翻訳済みテキスト・JAN・原産国・カテゴリ・バリエーションを 1 回で登録する。

**必須フィールド**: `rakuten_product_id`, `name`, `description`, `product_no`, `product_url`, `brandName`, `release_date`, `average_price`, `used_exclude_sales_min_price`, `used_exclude_sales_max_price`, `used_exclude_sales_item_count`, `mediumImageUrl`, `genre_id`, `genre_name`, `variations`。`release_date` は ISO `YYYY-MM-DD`（今日の日付でOK）。

```python
import time
from datetime import date

jan         = "4979909964002"
cost        = 110
weight      = 0.05
category_id = 101664

payload = [{
    "rakuten_product_id":            f"daiso-{jan}" if jan else f"daiso-{int(time.time())}",
    "name":                          "DAISO Japan ブラシケアネット  Directly ship from Japan",
    "name_ja":                       "DAISO Japan ブラシケアネット  Directly ship from Japan",
    "name_en":                       "DAISO Japan Brush Care Net | Directly Shipping from Japan | Kios Store",
    "description":                   "原産国：ベトナム\n材質：ポリエチレン\n...",
    "description_ja":                "原産国：ベトナム\n材質：ポリエチレン\n...",
    "description_en":                "Country of Origin: Vietnam\nMaterial: Polyethylene\n...",
    "product_no":                    jan,
    "product_url":                   "https://jp.daisonet.com/products/4979909964002",
    "brandName":                     "DAISO",
    "release_date":                  date.today().isoformat(),
    "average_price":                 float(cost),
    "used_exclude_sales_min_price":  0.0,
    "used_exclude_sales_max_price":  0.0,
    "used_exclude_sales_item_count": 0,
    "genre_id":                      "",
    "genre_name":                    "",
    "mediumImageUrl":                "https://jp.daisonet.com/cdn/shop/files/4979909964002_1.jpg",
    "image_2":                       None,
    "image_3":                       None,
    "jan_code":                      jan,
    "country_of_origin_ja":          "ベトナム",
    "country_of_origin_en":          "Vietnam",
    "ingredients_ja":                "ポリエチレン",
    "ingredients_en":                "Polyethylene",
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
product = resp.json()["products"][0]
print(product["id"], product.get("shopee_sku"))
```

**レスポンス例:**
```json
{
  "products": [
    {
      "id": 319,
      "shopee_sku": "SKU-XXXXXXXX",
      "variations": [
        { "id": "uuid-xxxx-xxxx-xxxx", "sku": "var-XXXXXXXX" }
      ]
    }
  ]
}
```

---

### PUT /api/products/update — 商品の部分更新

特定フィールドだけ送って更新できる（例: 加工済み画像 URL の上書き）。

```python
requests.put(
    f"{BASE}/api/products/update",
    json={"id": 319, "mediumImageUrl": "https://reboyzvurreclyrodjeg.supabase.co/storage/..."},
    headers=HEADERS,
).raise_for_status()
```

---

### GET /api/products/{id} — 商品取得

```python
resp = requests.get(f"{BASE}/api/products/319", headers=HEADERS)
resp.raise_for_status()
print(resp.json())
```

---

### POST /api/products/{id}/process-main-image — 画像加工（桜背景・ロゴ追加）

```python
img_resp = requests.post(
    f"{BASE}/api/products/319/process-main-image",
    headers=HEADERS,
)
if img_resp.status_code == 200:
    processed_url = img_resp.json().get("mediumImageUrl", "")
    requests.put(
        f"{BASE}/api/products/update",
        json={"id": 319, "mediumImageUrl": processed_url},
        headers=HEADERS,
    ).raise_for_status()
```

成功レスポンス: `{ "success": true, "mediumImageUrl": "https://reboyzvurreclyrodjeg.supabase.co/..." }`

**注意**:
- `mediumImageUrl` が `http://` だと「画像のダウンロードに失敗しました」（500）になる。`https://` で渡すこと
- 失敗しても再試行しない（呼び出し側スキルの方針）

---

### GET /api/shopee/products/category-recommend — カテゴリ推薦

商品名（英語）から Shopee カテゴリ候補を取得する。**クエリパラメータ** `shop_id`・`item_name` は必須。`description` は受け付けない。

```python
rec = requests.get(
    f"{BASE}/api/shopee/products/category-recommend",
    params={"shop_id": 1418317116, "item_name": name_en},  # PH or SG
    headers=HEADERS,
)
rec.raise_for_status()
print(rec.json())
```

レスポンス例: `{ "category_ids": [100898, 102005] }`

**有効な候補が返るのは英語名が設定されているとき。** 国ごとに候補が変わる可能性があるため、必要に応じて PH/SG 両方を呼ぶ。

---

### GET /api/shopee/products/categories?shop_id={shop_id} — カテゴリ一覧

候補 ID からカテゴリ名を引きたいときに使う。

```python
cats = requests.get(
    f"{BASE}/api/shopee/products/categories",
    params={"shop_id": 1418317116},
    headers=HEADERS,
).json()
for c in cats:
    if c["category_id"] in (101655, 101648, 101641):
        print(c["category_id"], c["display_category_name"])
```

---

## 定数リファレンス

### ショップ ID
| 国 | shop_id |
|-----|---------|
| PH (フィリピン) | `1418317116` |
| SG (シンガポール) | `1425845298` |

### ダイソー 110円商品 テスト価格
| 国 | 価格 |
|-----|------|
| SG | `2.5` SGD |
| PH | `109` PHP |
| TW | `null`（参入しない） |
| VN/TH/MY/BR | `null`（初回は未設定可） |

### 英語商品名フォーマット
```
DAISO Japan [English Name] | Directly Shipping from Japan | Kios Store
```

---

## 注意事項

- **API キーは `.env` から読み込む**。チャットや コミットに API キー値を貼らない
- `POST /api/products/insert` は `shop_category_settings` を含めて 1 回で全フィールドを保存できる
- `PUT /api/products/update` は `id` + 更新したいフィールドのみ送る部分更新でも動作する
- `shop_category_settings` の `category_id` は Shopee カテゴリ ID（例: 101664）
- `mediumImageUrl` は画像URL 1（メイン画像）。必ず `https://` で始まること
- 画像加工は `POST /api/products/{id}/process-main-image` で実行可能。失敗時は再試行せず次に進む
- 翻訳（日→英）は Claude が直接実行する
