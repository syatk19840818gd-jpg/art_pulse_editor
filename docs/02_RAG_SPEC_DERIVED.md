02_RAG仕様_派生索引
版: 2026-04-18 JST（アプリ機能調整ラウンド同期）
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

block必須工程チェックリスト（圧縮索引）
1. scope 定義
2. raw verify-first
3. artists image collect verify-first
4. exhibitions image collect verify-first
5. artists enrichment preflight
6. artists enrichment submit
7. artists enrichment check
8. artists enrichment apply
9. exhibitions enrichment preflight
10. exhibitions enrichment submit
11. exhibitions enrichment check
12. exhibitions enrichment apply
13. artists text vector verify-first
14. artist works images vector verify-first
15. run_block_closeout verify-first（Artist作品画像 duplicate audit gate 含む）
16. run_block_closeout apply（R2なし）
17. workbook 人間確認
18. `current_required_rag_full` plan
19. `current_required_rag_full` apply
20. `current_required_rag_full` post-check
21. docs同期
22. 次 block 再開判定
23. 次 block 開始

closeout 前の必須ゲート（索引）
- 未完了工程が1つでもある場合は `run_block_closeout apply（R2なし）` へ進まない。
- Exhibition enrichment（preflight / submit / check / apply）を飛ばさない。
- `run_block_closeout verify-first` は current Artist作品画像 duplicate audit を含み、`duplicate_cluster_count > 0` または `blocking_errors` がある場合は closeout apply へ進まない。
- workbook 人間確認完了前に `current_required_rag_full` へ進まない。
- block 完了後の正式 R2 手順は narrow hotfix sync ではなく `current_required_rag_full` を用いる。
- `current_required_rag_full` は `plan -> apply -> post-check` を必ず順に実行し、`missing local->R2 = 0`、`remote_only = 0`、`size_mismatch = 0` を確認する。
- `current_required_rag_full` post-check 完了前に次 block を開始しない。

今後の Codex task 作成固定ルール（索引）
- 毎回「この block の必須工程一覧」を明記する。
- 毎回「今回がどの段階か」を明記する。
- 毎回「未完了工程が残るなら次へ進まない」を明記する。
- closeout 後の R2 手順として毎回 `current_required_rag_full` の `plan / apply / post-check` を task 本文に明記する。
- `run_block_closeout verify-first` task には「Artist作品画像 duplicate audit gate を含む」ことを毎回明記する。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルトとして維持し、今後の更新でも消さない。

次タスク入口（docs同期後）
- まず `次 block 再開判定` に進む。
- 再開判定では、直前 block の `current_required_rag_full` 完了ログと duplicate gate 導線固定済みであることを前提確認する。
- 再開判定完了前に次 block 開始へは進まない。

current scope 10館 block 完了同期（2026-04-14 JST）
- 対象scope: `_trial/phase3_next_real_scope_20260412.csv`（Frith Street Gallery / Gagosian / Alexander Gray Associates / Garth Greenan Gallery / Laveronica / Livie Gallery / Lodos / Lodovico Corsini / Lucas Hirsch）。
- duplicate gate cleanup 後、`run_block_closeout verify-first` は `duplicate_cluster_count=0`、`blocking_errors=[]` で通過済み。
- `run_block_closeout apply（R2なし）` は完了済み。`block_completion_status=applied_pending_workbook_and_current_required_rag_full`。
- workbook 人間確認は OK。
- 正式 R2 導線 `current_required_rag_full` は `plan -> apply -> post-check` を完了済み。
- plan 結果: `would_upload=7`、`would_prune=20`。
- apply 結果: `uploaded=7`、`deleted=20`、`upload_failed=0`、`delete_failed=0`。
- post-check 結果: `would_upload=0`、`would_prune=0`。
- family parity: `images_metadata_artist_works` / `vector_artist_works_images` の size mismatch 解消、`images_cache_artist_works` の remote_only 20 解消。
- `Goodman Gallery` は今回も対象0/非追加で整合。`Lucas Hirsch` は `exhibition_text_count=0 / exhibition_image_count=0` のまま反映。
- 補助履歴: `Matthew Brown` は duplicate cleanup 後の `1071` 現状を人間受理として current fix を採用済み。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルト維持を継続。

固定原則
- app/readonly は current-first を維持する。
- source/derived/vector/logs のファミリー分離を崩さない。
- 取得ループ内でLLM加工をしない（fetch と enrichment を分離）。

2026-04-18 アプリ機能調整ラウンド同期（現行仕様）
- 本節は、前回 docs 同期以降にこのチャットで確定した「現行アプリ仕様」のみを追記する。
- 新ブロック再開前に、アプリ機能確認を優先する運用を採用した。

機能2 / 機能3（Exhibition Search / Artist Search）
- 検索結果は 30件ずつのページング表示を維持する。
- ページ切替 UI を用いる。
- 案内文・件数表示・検索結果表示の文字色は通常の黒字を標準とする。

機能7（Art Work Search）
- 案内文・件数表示・検索結果表示の文字色は通常の黒字を標準とする。
- upload 文字の重複表示を解消した状態を現行とする。
- 30件ページング前提を維持し、過剰表示を抑える。
- 画像未取得・不整合画像が不自然に上位へ出る挙動を抑制した現行実装を維持する。

機能4（Advisor）
- upload 文字重複を解消した現行表示を維持する。
- broad / 抽象質問でも参照多様性を持たせる。
- 固定テンプレは禁止し、broad 質問で同一参照への過度固定を避ける。

機能1（Art Pulse）現行仕様
- 3見出し固定は廃止し、単一記事1本を現行契約とする。
- 文字数目安は 1000字前後、実運用許容は 800〜1200字程度とする。
- 本文構成は、同一記事内で「指定年・指定フェアのトレンド」から「おすすめ Artist / Exhibition」へ自然接続する2構成とする。
- 主要固有名詞（Artist / Exhibition）は RAG 根拠ベースで扱う。内部知識は補完的にのみ利用可。
- 表示は本文 → サムネイル（最大4枚）→ 根拠URL の順とする。
- 根拠表示ラベルは `根拠URL` を用いる。
- 本文文字数表示は `/1000` を用いる。
- Artist 名 / Exhibition 名リンク付与は維持する。

Art Pulse 調整時の運用ルール
- API コスト抑制のため、Art Pulse の実テストはユーザー本人が実施する。
- Codex は静的確認と原因分析を担当し、live API テストを行わない。
