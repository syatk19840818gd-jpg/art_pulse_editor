02_RAG仕様_派生索引
版: 2026-04-11 JST（修正1〜修正5 + skip契約同期）
参照正本: `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`

目的
- 本書は 01 正本の運用要点を実装参照向けに圧縮した索引である。
- 仕様の最終判断は常に 01 を優先する。

現行アプリ構成
- 機能1: Art Pulse
- 機能2: Exhibition Search
- 機能3: Artist Search
- 機能4: Advisor
- 機能6: Gallery list
- 機能7: ArtWork Search

正本契約（current / history / workbook）
- source of truth は `data/current` の current formal artifacts とする。
- runtime current enrichment は `status == APPLIED` のみを保持する。
- `SKIPPED_*` / `BATCH_PARSE_FAILED` などの非APPLIED行は history/audit 側に保持し、runtime current へ混在させない。
- summary/path 記録は canonical current path を指す。

修正1〜修正5で確定した契約
- 修正1（closeout / current-write）
  - workbook は current formal artifacts から導出する。
  - closeout 系は `current_write -> skip_registry_gallery_list_cleanup -> xlsx_update -> r2_sync` の順で運用する。
- 修正2（current enrichment source-of-truth）
  - Artist / Exhibition とも current runtime は materialized current builder を通す。
  - raw/current/history の整合を保持し、runtime current と history/audit を分離する。
- 修正3-A〜3-D（Exhibition Text）
  - stale request は current raw 基準で自動再同期する。
  - `openai_output_not_json` は tolerant parse で汎用救済する。
  - Exhibition Text は `workbook 446 / raw 446 / current enrichment 446 / loader enriched 446` へ到達済み。
- 修正4（Artist vector / loader）
  - `artists text vector` は `fair_slug + normalize_url(source_url) + text_hash` を canonical row key とする。
  - `artist works images vector` は `image_id` を row key とする。
  - Artist loader dedup は `fair_slug + normalized source_url + text_hash` 契約で固定する。
- 修正5（workbook Artist一致列）
  - Artist一致列（総抽出Artist数 / 画像テキストArtist一致数 / Artist一致率）は shared artist match key で算出する。
  - `テキスト抽出Artist数` は text canonical row key 件数として維持する。

名前ベース契約（Artist / Exhibition 境界）
- Artist
  - cross-gallery same-name skip は収集段の契約として実装済み。
  - first-write-wins global no-refetch を維持する。
- Exhibition
  - 同姓同名アーティスト名 / 同名展覧会名を理由に skip しない。
  - skip は year判定・source_url既知・text hash重複・gallery skip 契約など別理由でのみ実施する。

dedup と skip の役割分離
- source_url dedup: 同一URL再訪抑止。
- canonical key dedup: vector/loader の重複排除。
- gallery skip: `all_rag_zero` / `exhibition_text_only` の館単位除外。
- Artist cross-gallery same-name skip: 収集段の global artist identity 契約。

workbook 表示契約（標準デフォルト）
- `rag_gellery_breakdown_master` は合計数表示を標準デフォルトとする。
- フェア別合計と全体合計を維持する。
- 今後の workbook 更新でも合計数表示を消さない。
- workbook 値は current formal artifacts から機械導出する。

count の読み方（運用固定）
- row/slot count
  - `Artistテキスト数`: raw row count
  - `Artist画像枚数`: image metadata slot count
- canonical key count
  - `テキスト抽出Artist数`: `normalize_url(source_url) + text_hash`
  - Artist Works vector: `image_id`

次タスク入口（docs同期後）
- next real scope 10館 block を再開する。
- 開始は raw verify-first とする。

固定原則
- app/readonly は current-first を維持する。
- source/derived/vector/logs のファミリー分離を崩さない。
- 取得ループ内でLLM加工をしない（fetch と enrichment を分離）。
