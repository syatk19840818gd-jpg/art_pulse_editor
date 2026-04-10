# 04_作業進捗ログ

最終更新: 2026-04-10 JST
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
- skip 契約を `all_rag_zero` から `exhibition_text_only` まで拡張した。`exhibition_text_only` は `artist_count == 0`、`artist_image_rows == 0`、`artist_image_count == 0`、`exhibition_count > 0`、`exhibition_image_count == 0` を満たす場合に generic skip として扱う。理由は、gallery/host 固定分岐を増やさず shared helper 契約で運用するため。
- active list / skip registry 反映後の次 real scope 10館 block を実施し、raw verify-first、artists image collect verify-first、exhibitions image collect verify-first、artists enrichment submit/resume、artists text vector verify-first、artist works images vector verify-first、closeout apply、workbook OK まで完了した。理由は、skip 拡張後の主導線が end-to-end で成立することを確認するため。
- block 完了後に `Copperfield` / `Coulisse Gallery` を `exhibition_text_only` として retroactive に skip registry へ移管し、Liste active list から除外、`data/current/raw/exhibitions_liste_2025.jsonl` から Copperfield 3行・Coulisse Gallery 1行を purge した。理由は、active RAG に不要行を残さないため。
- `run_block_closeout` 主導線へ `skip_registry_gallery_list_cleanup` を接続し、`current_write -> xlsx_update -> skip_registry_gallery_list_cleanup -> r2_sync` の契約へ拡張した。dry-run report は `all_rag_zero_detected_rows` / `skip_registry_plan` / `gallery_list_removal_plan` を必須化した。理由は、将来の `all_rag_zero` / `exhibition_text_only` を closeout 主導線で自動除外しつつ、最終合格判定を workbook 人間確認で維持するため。
- 上記 skip/purge 契約追加は offline-only タスクとして実施した（API実行0 / rerun0 / closeout apply0 / R2 apply0 / docs更新0）。理由は、無駄な API lane への流入を pre-enrichment で停止する方針を固定するため。
