# 04_TASK_PROGRESS_LOG

最終更新: 2026-03-30 JST
対象プロジェクト: ART_PULSE_EDITOR

## 0. 位置づけ

- 01 が正本です。
- 02 は索引、03 は current snapshot、04 は実装ログの要約です。

## 1. 現行ベースライン

- Feature 1 Art Pulse: completed
- Feature 2 Exhibition Search: completed
- Feature 3 Artist Search: stable
- Feature 4 Advisor: accepted baseline
- Feature 6 Gallery list: active read-only feature
- Feature 7 ArtWork Search: active feature

## 2. 2026-03-30 の整理

- app から retired advisor lane の UI / route / import / session state を削除
- 専用 readonly / draft / type2 実装ファイルを削除
- 専用 text corpus, vector, config, sync log, import / enrichment / vectorize scripts を削除
- docs 01 / 02 / 03 / 04 を現行構成へ同期

## 3. 維持したもの

- Feature 4 Advisor accepted baseline
- Feature 2 / 3 / 7 の read path
- current-first storage contract
- shared/common の既存責務

## 4. 今後のログ方針

- 廃止済み lane の再開は前提にしない
- 新しい task log は Feature 1 / 2 / 3 / 4 / 6 / 7 の現行構成だけを前提に書く
