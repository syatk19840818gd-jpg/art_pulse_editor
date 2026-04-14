03_状態スナップショット_次タスク
プロジェクトスラッグ: ART_PULSE_EDITOR
最終更新: 2026-04-14 JST（current scope 10館 block docs同期完了）

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
- `current_required_rag_full` による full parity audit / full sync / post-check を完了し、app 必須 current RAG family の local / R2 完全一致を確認済み。
- `run_block_closeout verify-first` は current Artist作品画像 duplicate audit を含む正式 gate とし、duplicate cluster 残存時は `blocking_errors` で停止する契約へ更新済み。
- current scope 10館 block は `run_block_closeout apply（R2なし）`、workbook 人間確認、`current_required_rag_full plan/apply/post-check` まで完了済み。
- `current_required_rag_full` 完了値: plan `would_upload=7 / would_prune=20`、apply `uploaded=7 / deleted=20 / failure=0`、post-check `would_upload=0 / would_prune=0`。
- duplicate gate cleanup 済みで、closeout verify-first の再検証は `duplicate_cluster_count=0`、`blocking_errors=[]`。
- `Goodman Gallery` は対象0/非追加で整合、`Lucas Hirsch` は `exhibition_text_count=0 / exhibition_image_count=0` 維持。
- `Matthew Brown` は duplicate cleanup 後の `1071` 現状を人間受理済み（current fix 採用）。

確定した運用契約
- source of truth は `data/current` の current formal artifacts。
- runtime current enrichment は `APPLIED` のみ、history は audit 用に分離。
- stale request は current raw 基準で自動再同期。
- `openai_output_not_json` failure class は tolerant parse で汎用救済。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルトとして維持し、今後の更新で消さない。
- block必須工程は 01/02 に固定した正式順序（1〜23）で運用し、順序変更・省略を行わない。
- Exhibition enrichment（preflight / submit / check / apply）を飛ばさない。
- 未完了工程が1つでもある場合は closeout apply へ進まない。
- workbook 人間確認後の正式 R2 手順は narrow hotfix sync ではなく `current_required_rag_full` の `plan -> apply -> post-check` とする。
- `current_required_rag_full` は `missing local->R2 = 0`、`remote_only = 0`、`size_mismatch = 0` を満たさない限り block 完了扱いにしない。

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
- [x] block必須工程 `21/23`（docs同期）を完了した。
- [ ] 直近の現在段階を block必須工程 `22/23`（次 block 再開判定）に固定する。
- [ ] まず `次 block 再開判定` を行う。
- [ ] 再開判定では、直前 block の `current_required_rag_full` canonical log と duplicate gate 固定済み導線を確認する。
- [ ] 再開判定が終わるまで次 block を開始しない。

Codex task 作成運用（固定）
- [ ] 毎回「この block の必須工程一覧」を task 本文に明記する。
- [ ] 毎回「今回がどの段階か（n/23）」を task 本文に明記する。
- [ ] 毎回「未完了工程が残るなら次へ進まない」を task 本文に明記する。
- [ ] closeout 後の R2 手順として `current_required_rag_full` の `plan / apply / post-check` を task 本文に明記する。
- [ ] `run_block_closeout verify-first` task には「Artist作品画像 duplicate audit gate を含む」を明記する。

引き継ぎメモ
- 仕様判断は常に 01 を正本とする。
- 02 は実装参照索引、04 は時系列ログ、03 は現在地と次タスクの正本とする。
