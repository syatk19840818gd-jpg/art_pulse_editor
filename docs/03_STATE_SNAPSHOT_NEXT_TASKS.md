03_状態スナップショット_次タスク
プロジェクトスラッグ: ART_PULSE_EDITOR
最終更新: 2026-04-11 JST（docs同期: 修正1〜修正5 + skip契約）

文書パス
- 正本01: `./docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
- 索引02: `./docs/02_RAG_SPEC_DERIVED.md`
- 状態03: `./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- 進捗04: `./docs/04_TASK_PROGRESS_LOG.md`

現在地スナップショット
- 修正1完了: workbook vs current raw divergence 是正済み。
- 修正2完了: Artist/Exhibition current enrichment の source-of-truth を整理済み。
- 修正3-A〜3-D完了: Exhibition Text は `446/446` で整合済み。
- 修正4完了: artists text vector / artist works images vector / Artist loader dedup を canonical key 契約へ是正済み。
- 修正5完了: workbook の Artist 一致数・一致率列を canonical key 契約で再計算済み。
- workbook は人間確認 OK。

確定した運用契約
- source of truth は `data/current` の current formal artifacts。
- runtime current enrichment は `APPLIED` のみ、history は audit 用に分離。
- stale request は current raw 基準で自動再同期。
- `openai_output_not_json` failure class は tolerant parse で汎用救済。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルトとして維持し、今後の更新で消さない。

Artist / Exhibition 名前ベース契約
- Artist: cross-gallery same-name skip は収集段で実装済み（global first-write-wins）。
- Exhibition: 同姓同名アーティスト名 / 同名展覧会名を理由に skip しない。
- dedup と skip は別契約として運用する。

count 契約メモ（引き継ぎ用）
- row/slot count:
  - `Artistテキスト数` = raw row count
  - `Artist画像枚数` = image metadata slot count
- canonical key count:
  - `テキスト抽出Artist数` = `normalize_url(source_url) + text_hash`
  - artist works images vector row key = `image_id`

次タスク
- [ ] next real scope 10館 block を再開する。
- [ ] 開始順は raw verify-first とする。
- [ ] block 完了判定は current/workbook 整合 + workbook 人間確認で実施する。

引き継ぎメモ
- 仕様判断は常に 01 を正本とする。
- 02 は実装参照索引、04 は時系列ログ、03 は現在地と次タスクの正本とする。
