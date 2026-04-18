# 04_作業進捗ログ

最終更新: 2026-04-18 JST
プロジェクト: ART_PULSE_EDITOR

## 0. 文書の役割
- 01 は正本。
- 02 は派生運用契約。
- 03 は現在地と次タスク。
- 04 は実装・進捗ログ。

## 1. 現行ベースライン
- 機能1 Art Pulse: 完了。
- 機能2 Exhibition Search: 完了。
- 機能3 Artist Search: 安定。
- 機能4 Advisor: 受け入れベースライン。
- 機能6 Gallery list: read-only 機能として稼働中。
- 機能7 ArtWork Search: 稼働中。

## 2. 2026-03-30 ベースラインのクリーンアップ/削除同期
- retired 済み advisor レーンの UI / route / import / session state を app から削除。
- retired 済み advisor readonly / draft / type2 ファイルを削除。
- retired 済み text corpus / vector / config / sync-log / import / enrichment / vectorize 成果物を削除。
- docs 01 / 02 / 03 / 04 を現行ベースラインへ同期。

## 3. 維持対象
- 機能4 Advisor の受け入れベースライン。
- 機能2 / 3 / 7 の read path。
- current-first の保存契約。
- shared/common の汎用構造。

## 4. 次タスク方針
- retired レーンはベースライン対象外を維持する。
- タスクログは機能1 / 2 / 3 / 4 / 6 / 7 のベースラインにのみ整合させる。
- 主ロードマップは explicit user task で進行する。

## 5. 2026-03-30 クローズアウト同期（本チャット）
- R2 remote residue prune を狭い legacy scope のみで完了。
- post-check 完了: 狭いscopeと広いcurrent scope の双方で `would_prune=0` を確認。
- 機能6 Gallery list の verify-first を完了: read-only 品質はOK、修正不要。
- 機能3 / 4 / 7 の current-only runtime verify-first を完了: 回帰なし。
- 機能7の独立機能契約は維持（Advisor へ吸収しない）。
- 追加の tiny-fix タスクは現時点で不要。

## 6. 2026-03-31 R2 current-only mirror 最終化
- `config/r2_sync_targets.json` を簡素化し、既定R2 mainline を `current_root_mirror`（`data/current` -> `data/current`）のみにした。
- `data/history` を R2 sync targets から除外し、GitHub側保持のみへ変更。
- `run_r2_sync.py` は remote mutation を `sync --apply` の背後に維持し、1回のsyncで upload + delete を同時反映できるようにした。
- live plan で `current_root_mirror` は `would_upload=0` / `would_prune=0`、`tarutani_data_retired_mirror` は `would_prune=93` を確認。
- live apply で R2 上 `data/Tarutani_data` の93件を削除し、失敗0。
- live post-check で `current_root_mirror` と Tarutani cleanup scopes の全てが `would_prune=0` を確認。

## 7. 2026-03-31 remote residue cleanup 最終
- verify-first で current R2 mainline が `data/current` のみであること、`phase1_seed10` が active R2 sync targets から外れていることを確認。
- verify-first で remote `phase1_seed10` への active runtime / default sync 依存がないことを確認。残存参照は default R2 mirror 契約外の local legacy helper / logs のみ。
- live plan の `history_remote_residue_cleanup` は `would_prune=20`。
- live plan の `phase1_seed10_remote_residue_cleanup` は `would_prune=601`。
- live apply で R2 上 `data/history` 20件と `phase1_seed10` 601件を削除、失敗0。
- live post-check で `current_root_mirror` / `history_remote_residue_cleanup` / `phase1_seed10_remote_residue_cleanup` の全てが `would_prune=0`。

## 8. 2026-03-31 phase1_seed10 最終retire-and-cleanup
- `phase1_seed10` の正本確認は、前回post-check要約ではなく実R2 listing を採用。
- その listing で残存実オブジェクト1件を確認: `phase1_seed10/logs/failed_fetches_artists_seed10_2025.json.bak_20260301_134210`。
- `phase1_seed10` / `phase1_seed10/` の placeholder key はどちらも存在せず、表示フォルダは marker ではなく残存実オブジェクト由来。
- 原因は cleanup scope が global exclude `**/*.bak*` を継承しており、前回 plan/post-check が残存 `.bak` を検知できなかったこと。
- `run_r2_sync.py` と `config/r2_sync_targets.json` を更新し、明示retired/cleanup scope が global excludes を無視して remote prefix を空まで収束できるようにした。
- live re-plan で `phase1_seed10_remote_residue_cleanup` の `would_prune=1` を確認。
- live apply で最終1件を削除し、失敗0。
- 最終実R2 listing は `object_count=0`、`phase1_seed10` / `phase1_seed10/` の `head_object` はともに404。
- 最終保存方針: `phase1_seed10` は R2 保持しない・GitHub retention にも昇格しない。必要時のみ local-only。

## 9. 2026-03-31 local phase1_seed10 path 廃止
- `data/phase1_seed10/...` 参照を config / preview scripts / enrichment helpers / collect scripts / formalize/recovery helpers で確認。
- 正規RAG出力は既に shared-helper 基盤で `data/current/...` に留まっており、`data/phase1_seed10/...` への active 正規出力書き込みは禁止状態。
- `phase2_art_pulse_config.py` で deprecated local legacy root alias を `data/runtime/legacy_phase1` に向け、残存 helper import による `data/phase1_seed10/...` 再生成を防止。
- preview 出力を `data/runtime/enrichment_requests/_reports/previews/...` へ移動。
- `run_enrichment_seed10.py` の runtime request / request-summary 成果物を `data/runtime/enrichment_requests/...` と `_reports/...` へ移動し、旧自動R2 sync hook を削除。
- legacy 専用 logs / trial / trash helper は `data/phase1_seed10/...` ではなく中立 runtime path へ解決。
- 変更後の repo-wide code search で `data/phase1_seed10/...` への Python 書き込み path は残存なし。唯一の直接参照は旧remote key 向け `app.py` read fallback のみ。

## 10. 2026-03-31 R2 log レーン統一
- verify-first で active `run_r2_sync.py` が既に plan / apply / listing / run logs を `logs/r2_sync/` に出力していることを確認。
- `data/r2_auto_sync/` には retired auto-sync 残骸のみが存在（履歴summary logs と旧 `phase1_*` auto-sync flow 用の未使用 `auto_sync_state.json`）。
- `run_r2_sync.py` は `logs/r2_sync/` を canonical R2 sync log directory として明示。
- retired の `data/r2_auto_sync/` を削除し、R2 logs/state の並行レーンを解消。

## 11. 2026-03-31 フェーズ遷移判断（Phase 2 closeout -> Phase 3）
- ユーザー判断を本サイクルの最終決定として記録: Phase 2 は closed/completed。
- 次ロードマップ段階を Phase 3: gallery expansion に固定。
- 拡張運用では current-only runtime / family separation / guarded sync / fetch-enrichment separation の現行契約を維持。
- cleanup レーンはクローズ維持。ロードマップ進行は explicit-user-task mode を継続。
- 後続検証メモ: live enrichment batch smoke は任意フォローアップとして実施可能だが、Phase 2 -> Phase 3 遷移判断の阻害要因ではない。

## 12. 2026-03-31 Phase 3 固定運用方針の明確化
- Phase 3 では未確認の multi-wave 実行を行わない。
- 正式 review チェックポイントは 10 galleries ごとを維持。
- 各選定ブロックは `Frieze 5 + Liste 5` の 10 galleries 固定。
- 選定順は提供CSVの上から順（ABC順）に従う。
- 各10-galleryブロック後に `rag_gellery_breakdown_master.xlsx` 更新と抽出率の人間 review を必須とする。
- 標準速度目標は1サイクル最大20 galleries。
- 現時点で30 galleries は標準運用目標にしない。
- サイクル目標は review 済み10-galleryブロックの積み上げで達成する。2つ目の10は1つ目の review 後に開始する。
- 本方針は速度と運用安全性の両立、および explicit-user-task 実行維持を目的とする。

## 13. 2026-04-02 fixed10 rerun クローズアウト同期
- fixed10 rerun block は docs 同期クローズアウト後、条件付きGOでクローズ済み。
- rerun 実行前に verify-first 改善（year gate / 2-digit date extraction）を確認。
- fixed10 Exhibitions Text delta-only rerun は Exhibition cap=25 で完了。
- fixed10 Exhibition Image delta-only rerun は完了。
- fixed10 enrichment/xlsx 再更新は完了（exhibitions apply=27、artists apply=no-op、xlsx overwrite=10 / append=0）。
- artists/exhibitions の enrichment model 契約は `artist_name_kana` / `headline_ja` / `summary_ja` をすべて `gpt-5-mini` で統一。
- residual はクローズせず明示維持（Bombon 403 residual、Callirrhoë image 0 residual）。
- Chris Sharp Gallery の改善は rerun 出力へ反映済み。
- 次実行順序は docs 更新 -> Artist 側タスク -> initial10 Exhibitions delta-only backfill に固定。

## 14. 2026-04-05 RAG抽出 block 完了条件の正式化
- `current` 反映は単独で完了扱いにしない。同一 scope の `rag_gellery_breakdown_master.xlsx` 更新までを必須セットとする。
- RAG抽出 block の正式な完了条件は、Artist / Exhibition の抽出結果の current 反映、同一 scope の `rag_gellery_breakdown_master.xlsx` 更新、Artist Works Images の OpenCLIP embedding の current 反映の3点をすべて満たすこととする。
- Artist Works Images の OpenCLIP embedding は任意の後処理ではなく、RAG抽出 block の正式な完了条件の一部とする。
- 上記のいずれかが未完了の状態では、初期10件 / 新10件 / 今後の全 gallery block を問わず、次 block に進まない。
- 以後の closeout / gallery expansion / RAG抽出運用はこの条件で判定する。

## 15. 2026-04-06 block scope 一括 closeout 主導線の正式化
- 今後の通常運用では、block closeout の人間向け主導線を `run_block_closeout.py` に統一し、`1 block = 1 scope = 1 command` を基本とする。
- 10件単位 block 運用は Phase 3 の汎用コード安定化フェーズにおける検証運用であり、恒久ルールにはしない。安定化後の通常運用は差分 scope 一括または対象 scope 一括で行う。
- block closeout の正式完了条件は、current 反映、同一 scope の `rag_gellery_breakdown_master.xlsx` 更新、Artist Works Images の OpenCLIP current 反映確認、R2 sync、closeout report の5点をすべて満たすこととした。
- `current -> xlsx -> R2` は block closeout の正式契約とし、Exhibition / Artist / Artist Works Images の current formal artifacts を block scope 一括で bundle 化する運用に統一した。
- xlsx 更新と R2 bundle は current formal artifacts を source of truth とし、docs / `rag_gellery_breakdown_master.xlsx` / `_trial` は R2 bundle に含めない。xlsx 自体は GitHub バックアップ前提であり、R2 sync 必須対象には含めない。
- 既存のカテゴリ別 runner は残してよいが、手動のカテゴリ別 closeout / narrow sync は主導線にしない。
- `phase3_fixed_block_next10_targets.csv` の verify-first は安定化フェーズ残タスクとして例外的に実施し、`run_block_closeout.py --r2-live-plan` で planned を確認した。これは通常運用ルールへ昇格させない。

## 16. 2026-04-07 Phase 3 最終安全化（汎用性監査 + approval guard + baseline固定）
- offline-only で、Phase 3 の主 runner / closeout / enrichment / vectorize / repair / promote を棚卸しし、gallery個別・host個別・initial10/new10 固定の残存有無を監査した。
- `run_block_closeout.py` は `next10` 既定CSVに依存しないよう修正し、scope CSV の明示指定を必須化した。live R2 plan / apply は `--approval-token` 必須にした。
- `run_enrichment_artists_seed10_apply.py` は live OpenAI Batch 実行を `--approval-token` 必須にし、request-id 固定の localized repair whitelist を空に戻した。以後の repair は hidden fallback ではなく offline diagnosis + approved promote に寄せる。
- `run_vectorize_artists_seed10.py`、`run_repair_artist_works_images_vectors.py`、`run_text_enrichment_delta_promote.py`、`run_closeout_new10_artists_from_trial.py` は live vectorize / repair / promote / current closeout を `--approval-token` 必須にした。
- `run_phase1_seed10.py` と `run_phase1_seed10_artist_image_collect.py` は `--mode rebuild` を approval 必須にし、承認前は fill-missing / dry-run による offline-only diagnosis へ寄せた。
- `run_enrichment_artists_preview.py` の sample 選定は `frieze_london` / `liste` 固定分岐を外し、fair 一般化のロジックへ置き換えた。preview 層に残っていた軽微な母集団依存を削った。
- 次 block の標準運用を正式固定: baseline code をそのまま1回だけ使う -> verify-first -> 70%以上なら apply -> 70%未満なら offline-only で failure class 分析 -> generic patch を1回だけ検討 -> 再実行は承認後のみ。
- gallery個別対応 / host個別対応 / block母集団別専用コードは通常運用の本番ロジックに追加しない。特殊館は skip を許容するが、block 全体70%以上は必須ラインとして維持する。
- ①②で行った trial-and-error の教訓を今後の全 block に適用することを、01 / 03 / 04 に同期した。

## 17. 2026-04-10 docs同期（本チャット確定分）
- true next 進行中に Exhibition image 密度不足が顕在化した。理由は、gallery個別救済では再発しやすく、通常運用の汎用性を阻害するため。
- HTML fetch / route guard / year/provenance / listing quota を含む generic patch を複数回重ね、Exhibition image を verify-first で十分な密度まで改善した。理由は、母集団依存ではなく汎用ロジック側で再利用可能な改善に寄せるため。
- true next block は最終的に closeout apply 完了、workbook 人間確認 OK まで到達した。理由は、block 完了判定を人間確認付きで確定するため。
- true next の最終整理として `City Galerie Wien` を `all_rag_zero` で skip registry 化し、active gallery list から除外した。理由は、以後の通常運用で無駄な下流処理を回避するため。
- skip 契約を `all_rag_zero` から `exhibition_text_only` まで拡張した。`exhibition_text_only`（理由コード互換名）は `artist_count == 0`、`artist_image_rows == 0`、`artist_image_count == 0`、かつ exhibition 側が片側モダリティのみ（textのみ または imageのみ）を満たす場合に generic skip として扱う。理由は、gallery/host 固定分岐を増やさず shared helper 契約で運用するため。
- active list / skip registry 反映後の次 real scope 10館 block を実施し、raw verify-first、artists image collect verify-first、exhibitions image collect verify-first、artists enrichment submit/resume、artists text vector verify-first、artist works images vector verify-first、closeout apply、workbook OK まで完了した。理由は、skip 拡張後の主導線が end-to-end で成立することを確認するため。
- block 完了後に `Copperfield` / `Coulisse Gallery` を `exhibition_text_only` として retroactive に skip registry へ移管し、Liste active list から除外、`data/current/raw/exhibitions_liste_2025.jsonl` から Copperfield 3行・Coulisse Gallery 1行を purge した。理由は、active RAG に不要行を残さないため。
- `run_block_closeout` 主導線へ `skip_registry_gallery_list_cleanup` を接続し、`current_write -> xlsx_update -> skip_registry_gallery_list_cleanup -> r2_sync` の契約へ拡張した。dry-run report は `all_rag_zero_detected_rows` / `skip_registry_plan` / `gallery_list_removal_plan` を必須化した。理由は、将来の `all_rag_zero` / `exhibition_text_only` を closeout 主導線で自動除外しつつ、最終合格判定を workbook 人間確認で維持するため。
- 上記 skip/purge 契約追加は offline-only タスクとして実施した（API実行0 / rerun0 / closeout apply0 / R2 apply0 / docs更新0）。理由は、無駄な API lane への流入を pre-enrichment で停止する方針を固定するため。

## 18. 2026-04-10 exhibition_text_only 契約境界の固定（本チャット実装）
- `gallery_skip_registry.py` の shared helper を最小差分で更新し、`exhibition_text_only` 判定を「artist側が空」かつ「exhibition側が片側モダリティのみ（textのみ / imageのみ）」へ統一した。
- exhibition 側で text と image が両方ある館は、この理由では skip しない境界を明示した。
- 既存 reason code 名 `exhibition_text_only` は後方互換のため維持し、gallery名分岐は追加していない。
- 実例確認: Emalin は generic 条件で auto skip 側、Gauli Zitter は exhibition text + exhibition image が両方あるためこの理由では non-skip 側。
- 最終 accept 判定は従来どおり `rag_gellery_breakdown_master.xlsx` の人間確認で確定する。

## 19. 2026-04-11 Exhibition Text narrow apply 完了 + R2 narrow apply/post-check 完了
- Exhibition Text の fair差分監査を実施し、`if fair == ...` の固定分岐ではなく、汎用ヒューリスティクス差（候補投入量・year signal・date candidateノイズ）が主因であることを確認した。
- generic 改善は段階的に実施した。候補投入改善（same_domain -> same_site と root listing fallback）で Liste 候補投入を改善し、続いて year-signal の最小修正を適用した。
- `_collect_date_candidates` / ISO系の追加改善は複数案を verify-first 比較し、`v7` の source-aware weighting は no-gain（指標同値）としてロールバックした。
- 最終的な Exhibition Text コード状態は `v3安定版`（候補投入改善 + year-signal 順序修正 + month/two-digit 文脈絞り）で凍結した。
- `run_block_closeout.py` に `--exhibitions-raw-trial-root` 導線を追加し、既存の bounded merge 契約に沿って Exhibition raw も same scope で narrow 反映できるようにした（gallery/host 固定分岐なし）。
- same scope narrow apply（`TASK_PHASE3_EXHIB_TEXT_NARROW_APPLY_20260411T2215JST`）を実行し、`current exhibitions raw` を `59 -> 69` へ更新、workbook 更新を完了した。
- post-apply dry-run（`TASK_PHASE3_EXHIB_TEXT_NARROW_APPLY_POSTCHECK_20260411T2217JST`）で scope 汚染なし、block status planned を確認した。
- skip 契約は維持された。Emalin は `exhibition_text_only_auto_detected_in_block_closeout` で skip 維持、Stephen Friedman Gallery は既存 `all_rag_zero` skip 維持、Gauli Zitter は non-skip 維持。
- workbook 人間確認 OK 後、same scope narrow config のみで R2 live apply を実行した（`TASK_PHASE3_EXHIB_TEXT_NARROW_SCOPE_R2_APPLY_20260411T2258JST`）。pre-plan は upload 2 / prune 0、apply は uploaded 2 / deleted 0 / failure 0。
- R2 post-check（`TASK_PHASE3_EXHIB_TEXT_NARROW_SCOPE_R2_POSTCHECK_20260411T2300JST`）で `would_upload=0 / would_prune=0` を確認し、same scope 反映をクローズした。
- exhibitions image vector は今回も optional 契約のまま扱い、必須段への昇格はしていない。
- 次タスク入口は `active list -> 次scope 10館定義 -> raw verify-first` とする。

## 20. 2026-04-11 Phase 3 修正1〜修正5 + skip契約 + workbook表示契約 docs同期
- タスク種別は docs-only とし、実装変更・currentデータ変更・R2 apply・next block開始は行わなかった。
- 修正1の確定事項として、workbook は current formal artifacts から導出する契約を維持し、closeout/current-write 契約の順序を文書へ同期した。
- 修正2の確定事項として、current enrichment の source-of-truth は current formal artifacts、runtime current は APPLIED のみ、history は audit 用分離で固定した。
- 修正3-A〜3-Dの確定事項として、Exhibition Text は 446/446 到達、stale request 自動再同期、openai_output_not_json failure class の tolerant parse 汎用救済を文書へ同期した。
- 修正4の確定事項として、artists text vector（fair_slug + normalize_url(source_url) + text_hash）、artist works images vector（image_id）、Artist loader dedup（fair_slug + normalized source_url + text_hash）の canonical key 契約を同期した。
- 修正5の確定事項として、workbook の Artist 一致数・一致率列は shared artist match key で再計算し、テキスト抽出Artist数は text canonical row key 件数として分離維持する契約を同期した。
- verify-first 結果として、Artist cross-gallery same-name skip は収集段で実装済み（global first-write-wins）であることを記録した。
- verify-first 結果として、Exhibition は同姓同名アーティスト名・同名展覧会名を理由に skip しない契約（名前ベース非skip）を記録した。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルトとして固定し、今後の更新でも消さないことを運用契約へ明記した。
- row/slot count と canonical key count を混同しない運用メモを 02/03 に同期した。
- docs同期後の次タスク入口は `next real scope 10館 block 再開（raw verify-first開始）` として更新した。

## 21. 2026-04-12 block必須工程と順序ゲートの docs固定（再発防止）
- 本件は docs-only で実施し、実装変更・API実行・rerun/rebuild/promote・R2実行・workbook更新・next block開始は行っていない。
- 01を正本として、Phase 3 block の必須工程を `1〜20` の正式順序で固定した。
- 固定順序には `exhibitions enrichment preflight / submit / check / apply` を明示し、closeout 前の必須工程として契約化した。
- 固定ゲートとして「未完了工程が1つでもある場合は `run_block_closeout apply（R2なし）` に進まない」を明記した。
- 固定ゲートとして「Exhibition enrichment を飛ばさない（省略・後回し・置換禁止）」を明記した。
- closeout 前後の順序を `run_block_closeout verify-first -> run_block_closeout apply（R2なし）-> workbook 人間確認 -> R2 narrow sync -> post-check -> 次 block` に固定した。
- 02へ圧縮版チェックリスト索引を追加し、03の現在地を `9/20: Exhibition enrichment preflight` に更新した。
- 今後の Codex task 作成ルールとして、毎回「必須工程一覧」「今回段階」「未完了なら次へ進まない」を明記する運用を 01/02/03 に固定した。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）を標準デフォルトとして維持し、今後も消さないルールを継続明記した。

## 22. 2026-04-14 R2 full required scope 正式運用固定 + Artist作品画像 duplicate gate 固定
- 本件は再発防止の固定のみを実施し、API実行・R2実行・workbook更新・next block開始は行っていない。
- `run_r2_sync.py` に target 単位 inventory を plan log として残す拡張を入れ、family ごとの `local_count / remote_count / local_only / remote_only / size_mismatch` を canonical log で追えるようにした。
- `config/r2_sync_targets.json` に `current_required_rag_full` を正式運用 scope として固定し、app/runtime が実際に参照する current RAG family のみを explicit target 化した。
- 正式運用の R2 手順は narrow hotfix sync ではなく `current_required_rag_full` の `plan -> apply -> post-check` とし、成功条件を `missing local->R2 = 0`、`remote_only = 0`、`size_mismatch = 0` に固定した。
- `run_block_closeout verify-first` に current Artist作品画像 duplicate audit を組み込み、duplicate cluster が残っている場合は `blocking_errors` に載せて closeout apply へ進めない構造にした。
- duplicate gate は gallery/host 固定ではなく class-based とし、`exact_payload_duplicate`、`same_visual_signature_duplicate`、`contextual_near_duplicate` を cluster 理由として扱う。
- `run_block_closeout` の contract/report には `formal_post_workbook_r2_scope=current_required_rag_full`、required sequence、success criteria を出力するようにし、closeout apply 後の正式導線を code 上でも明示した。
- 01/02/03 を同期し、block 完了順序を `run_block_closeout verify-first（duplicate gate含む） -> run_block_closeout apply（R2なし） -> workbook 人間確認 -> current_required_rag_full plan/apply/post-check -> docs同期 -> 次 block 再開判定 -> 次 block 開始` に更新した。

## 23. 2026-04-14 current scope 10館 block 完了（remote完了条件到達 + docs同期）
- scope: `_trial/phase3_next_real_scope_20260412.csv`（Frith Street Gallery / Gagosian / Alexander Gray Associates / Garth Greenan Gallery / Laveronica / Livie Gallery / Lodos / Lodovico Corsini / Lucas Hirsch）。
- duplicate gate cleanup を実施し、closeout verify-first 再検証で `duplicate_cluster_count=0`、`blocking_errors=[]` を確認した。
- `run_block_closeout apply（R2なし）` を完了し、`block_completion_status=applied_pending_workbook_and_current_required_rag_full` を確認した。
- workbook 人間確認は OK。
- 正式 remote 導線 `current_required_rag_full` を実行した。
- plan: `would_upload=7`、`would_prune=20`。
- apply: `uploaded=7`、`deleted=20`、`upload_failed=0`、`delete_failed=0`。
- post-check: `would_upload=0`、`would_prune=0`。
- family parity: `images_metadata_artist_works` / `vector_artist_works_images` の size mismatch を解消し、`images_cache_artist_works` の remote_only 20 を解消した。
- workbook / docs / history / runtime / `_trial` は R2 mirror 対象外のまま維持した。
- `Goodman Gallery` は対象0/非追加で整合、`Lucas Hirsch` は `exhibition_text_count=0 / exhibition_image_count=0` のまま反映。
- `Matthew Brown` は duplicate cleanup 後の `1071` 現状を人間受理とし、current fix として採用した（補助修正履歴として記録）。
- `rag_gellery_breakdown_master` の合計数表示（フェア別合計 + 全体合計）は標準デフォルト維持を継続。
- 本節は docs 同期のみ。実装変更・API実行・R2再実行・workbook更新・next block開始は行っていない。

## 24. 2026-04-18 アプリ機能調整ラウンド完了同期（本チャット）
- 新ブロック再開前に、アプリ機能確認を優先する運用へ切り替えて実施した。
- 機能2 / 機能3は、30件ページングを前提に、案内文・件数表示・検索結果表示を通常黒字へ統一した。
- 機能7は、案内文・件数表示・検索結果表示の黒字化、upload 文字重複解消、30件ページング前提の表示整理を実施した。
- 機能7は、画像未取得・不整合画像が不自然に上位へ出る挙動を抑える方向で調整した。
- 機能4は、upload 重複表示を解消し、broad / 抽象質問で参照が初期10館・同一参照へ偏りすぎる問題を緩和した。
- 機能4は、固定テンプレ禁止を維持したまま参照多様性を改善した。
- 機能1（Art Pulse）は旧方針（3見出し固定 / 1800〜2000字 / 第3節条件 / 多段 expand-salvage-rescue）を打ち切った。
- 機能1（Art Pulse）は単一記事1本（目安1000字、実運用許容800〜1200字）へ再設計し、表示仕様を本文下サムネイル（最大4枚）・根拠URLへ整理した。
- 機能1（Art Pulse）は本文構成を「指定年・指定フェアのトレンド」から「おすすめ Artist / Exhibition」へつなぐ2構成へ整理した。
- 機能1（Art Pulse）は本文中の Artist / Exhibition リンク付与、本文文字数表示 `/1000`、根拠表示 `根拠URL` を現行仕様として維持した。
- 本ラウンド中に Art Pulse 調整時の API コスト増大が顕在化したため、運用を「実テストはユーザー本人、Codex は静的確認と原因分析のみ」へ切り替えた。
- 最終的に、アプリ機能調整ラウンドは完了とし、docs 同期後に既存ロードマップへ復帰可能な状態へ整理した。
