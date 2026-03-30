# RAG_EXTRACTION_BREAKDOWN_JA

最終更新: 2026-03-30 JST

## 現行対象

- Artist Works Images
- Artist Text
- Exhibitions Image
- Exhibitions Text

## 抽出・保存の共通ルール

- フェア混在を避け、family ごとに保存先を分離する
- fetch と enrichment を分離する
- current-first の参照契約を維持する
- manifest ベースで差分同期する

## アプリ側の参照先

- Feature 2 Exhibition Search: Exhibitions Text / Exhibitions Image
- Feature 3 Artist Search: Artist Text / Artist Works Images
- Feature 4 Advisor: Exhibitions Text / Artist Text / 参考画像
- Feature 7 ArtWork Search: Artist Works Images

## 補足

- 廃止済みの専用 lane はこの内訳から除外済みです。
