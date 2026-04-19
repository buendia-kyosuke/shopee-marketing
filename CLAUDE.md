# CLAUDE.md - Shopee越境EC戦略プロジェクト

## プロジェクト概要

日本からShopeeを通じた越境EC事業。月利100万円を1年以内に達成することが目標。
自作のAmazon→Shopee連携ツール（Python/React）を武器とする。

---

## 現状

- 販売先: Shopee PH のみ（SG並走を開始予定）
- 規模: 週3注文（月12注文）
- ツール: Amazon スクレイピング → Shopee API で自動出品。国切り替え可・利益率指定で価格自動計算

---

## 確定している戦略判断（議論不要）

- **PH + SG 並走**: 即実行。技術的障壁なし
- **TW は参入しない**: 最強クラスの日本人セラーが確立済みで赤字しか出ない
- **大衆商品はやらない**: 薬局系・お菓子・定番スキンケアは定価以下で赤字確定
- **グローバルニッチを狙う**: 日本にあるがPH/SGにない専門品が主戦場

---

## 重要な市場インサイト

### PHについて
- 利益は300円/注文が良い方、1,000円で素晴らしいレベル
- 購買力が低く高単価商品が売りにくい
- XでPH投稿が多いのは「稼げる国」だからではなく「初心者全員がPHから始めるから」
- PHの役割: 注文数確保・Preferred Seller維持・商品テスト場

### SGについて
- 高単価で売れることを実体験で確認済み
- 実際の高収益セラーはSGが売上の60〜65%を占める
- 利益の主柱にできる市場

### データ（2024年Shopee Japan調査）
- 「最も売上が良い国」: SG 24.9% > MY 23.6% > VN 21% > TH 18.9% > **PH 6.4%（最下位）**

---

## 参考にすべきXアカウント

- **@makky_shopee**: 最大手・コミュニティ・ツール開発・フルフィルメント
- **@sbcofficial**: 有益情報発信
- **@ShopeeJP**: Shopee Japan公式

---

## ナレッジベース構成

詳細は各ファイルを参照:

- [strategy/overview.md](./strategy/overview.md) - グローバルニッチ戦略・問題の構造分析
- [strategy/roadmap.md](./strategy/roadmap.md) - フェーズ別目標・月次KPI
- [strategy/pricing.md](./strategy/pricing.md) - 国別マージン・手数料
- [strategy/gmv_framework.md](./strategy/gmv_framework.md) - GMV分解(Visit×CVR×AOV)・優先度=Visit>CVR>AOV
- [markets/philippines.md](./markets/philippines.md) - PH市場詳細
- [markets/singapore.md](./markets/singapore.md) - SG市場詳細
- [markets/other_markets.md](./markets/other_markets.md) - TW/MY/TH/VN/BR
- [research/market_comparison.md](./research/market_comparison.md) - 調査データ・比較表
- [research/japanese_sellers.md](./research/japanese_sellers.md) - コミュニティ・競合分析
- [research/listing_optimization.md](./research/listing_optimization.md) - 商品ページ最適化ガイド（国別）
- [tool/overview.md](./tool/overview.md) - ツール仕様・改善ロードマップ
- [skills/](./skills/) - Claude Codeスキル集（追加予定）
