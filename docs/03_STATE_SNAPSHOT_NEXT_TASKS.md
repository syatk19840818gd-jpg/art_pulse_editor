03_状態スナップショット_次タスク
プロジェクトスラッグ: ART_PULSE_EDITOR
最終更新: 2026-04-10 JST

文書パス
- 正本01: `./docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
- 索引02: `./docs/02_RAG_SPEC_DERIVED.md`
- 状態03: `./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- 進捗04: `./docs/04_TASK_PROGRESS_LOG.md`

現在地スナップショット
- true next block（`phase3_block_scope_candidate_after_new10.csv`）は完了。
- true next は closeout apply 完了 + workbook 人間確認 OK 済み。
- ただし `City Galerie Wien` は最終的に skip registry へ移管済み（`all_rag_zero`）。
- active list / skip registry 反映後の次 real scope 10館 block も実施完了。
- 当該 block は raw verify-first、artists image collect verify-first、exhibitions image collect verify-first が PASS。
- 当該 block は artists enrichment の preflight clean -> submit_only -> resume_or_check completed（row=1 request collapse 成立）まで完了。
- 当該 block は artists text vector verify-first、artist works images vector verify-first も PASS。
- 当該 block は closeout apply 完了 + workbook 人間確認 OK 済み。
- その後 `Copperfield` / `Coulisse Gallery` は `exhibition_text_only` 契約へ昇格し、skip registry へ移管・active RAG から retroactive purge 済み。
- skip 契約は `all_rag_zero` と `exhibition_text_only` の汎用契約へ更新済み。

現行運用ルール（今回同期分）
- skip 判定は shared helper 契約で扱い、gallery/host 固定分岐は増やさない。
- `run_phase1_seed10_exhibition_image_collect.py` 後の pre-enrichment で自動判定し、skip registry upsert と gallery list 除外を実行する。
- downstream（artists/exhibitions enrichment、artists text vector、artist works images vector）は skip registry を強制尊重する。
- target selection / Gallery list / phase1 runners / closeout 主導線は registry-aware で自動除外する。
- `run_block_closeout` 主導線には `skip_registry_gallery_list_cleanup` が接続済み。
- closeout 実行順は `current_write` -> `xlsx_update` -> `skip_registry_gallery_list_cleanup` -> `r2_sync` を含む。
- dry-run report は `all_rag_zero_detected_rows` / `skip_registry_plan` / `gallery_list_removal_plan` を必須出力とする。
- 最終合格判定は引き続き workbook の人間確認を必須とする。
- API 無駄打ち禁止を維持し、`exhibition_text_only` は pre-enrichment で止める。

次タスク
- [ ] skip registry 反映済み active list から、次の real scope を定義する。
- [ ] 次 block は raw verify-first から開始する。

引き継ぎメモ
- 仕様判断は常に 01 を正本として参照する。
- 02 は 01 の派生索引として運用差分だけを圧縮参照する。
- 進捗履歴は 04、現在地と次タスクは本 03 を正とする。
