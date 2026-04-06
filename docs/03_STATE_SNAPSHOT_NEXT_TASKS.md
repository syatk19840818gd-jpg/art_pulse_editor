03_状態スナップショット_次タスク
プロジェクトスラッグ: ART_PULSE_EDITOR
最終更新: 2026-04-06 JST

文書パス
- 正本01: `./docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
- 索引02: `./docs/02_RAG_SPEC_DERIVED.md`
- 状態03: `./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- 進捗04: `./docs/04_TASK_PROGRESS_LOG.md`

現在地スナップショット
- フェーズ状況: Phase 2 は完了（ユーザー判断済み）、次の主段階は Phase 3 の gallery expansion。
- fixed10 rerun block は条件付きGOでクローズ済み。
- 機能1 Art Pulse: 完了。
- 機能2 Exhibition Search: 完了。
- 機能3 Artist Search: 現行スコープで安定・受け入れ済み。
- 機能4 Advisor: 完了・受け入れベースライン。
- 機能6 Gallery list: read-only 機能として稼働中・verify-first 完了。
- 機能7 ArtWork Search: 現行実装あり・現行スコープで受け入れ済み。
- fixed10 rerun 結果: Exhibitions Text の delta-only 再実行完了（cap=25）。
- fixed10 rerun 結果: Exhibition Image の delta-only 再実行完了。
- fixed10 rerun 結果: exhibitions enrichment apply=27 / artists enrichment apply=no-op。
- fixed10 rerun 結果: xlsx 再更新 overwrite=10 / append=0。
- rerun 前に verify-first 改善（year gate + 2-digit date extraction）を適用。
- residual の明示継続: Bombon 403 residual / Callirrhoë image 0 residual。
- 品質反映: Chris Sharp Gallery の改善を現行出力に反映済み。
- current/history の再ベースライン化レーン: 完了。
- cleanup レーン: クローズ維持。
- 直近優先順: Artist 側タスク -> initial10 Exhibitions delta-only backfill。

稼働中データ / 取得ファミリー
- Artist Works Images 系
- Artist Text 系
- Exhibitions Image 系
- Exhibitions Text 系

現行運用ルール
- app runtime は current-first 挙動を維持する。
- shared/common は機能中立を維持する。
- fetch / enrichment / vectorize / sync はファミリー分離を維持する。
- fixed10 レーンの Exhibition 抽出 cap は 25 とする。
- artists/exhibitions の enrichment model は `artist_name_kana` / `headline_ja` / `summary_ja` をすべて `gpt-5-mini` で統一する。
- 機能7は独立機能として維持し、Advisor へ吸収しない。
- R2 の既定 sync 契約は current-only mirror: `data/current` -> `data/current`。
- R2 log の正本 path は `logs/r2_sync/` とし、retired の `data/r2_auto_sync/` レーンは再作成しない。
- `sync` 1回で current 同一 scope の追加と削除を反映する。
- `data/history` は R2 sync 対象外とし、GitHub 側保持のみとする。
- `phase1_seed10` は R2/GitHub から retired とし、手動 legacy helper が必要な場合のみ local-only とする。
- 新規RAG出力は `data/current/...` のみへ書き込む。
- `current` 反映は単独で完了扱いにしない。同一 scope の `rag_gellery_breakdown_master.xlsx` 更新までを必須セットとする。
- RAG抽出 block の正式完了条件は、Artist / Exhibition の抽出結果の current 反映、同一 scope の `rag_gellery_breakdown_master.xlsx` 更新、Artist Works Images の OpenCLIP current 反映確認、R2 sync、closeout report の5点がすべて完了していることとする。
- `artist_works_images_openclip_current` は任意の後処理ではなく、RAG抽出 block の正式な完了条件に含める。
- R2 sync は任意の後処理ではなく、block closeout の正式必須工程とする。Exhibition / Artist / Artist Works Images に関わる current formal artifacts は、その block closeout 時点で R2 sync 対象とする。
- `rag_gellery_breakdown_master.xlsx` は block 完了条件には含めるが、GitHub バックアップ前提とし、R2 sync 必須対象には含めない。
- xlsx 更新と R2 bundle は current formal artifacts を source of truth とし、docs / `rag_gellery_breakdown_master.xlsx` / `_trial` を R2 bundle に混ぜない。
- preview / request report / legacy logs / trial artifacts は `data/runtime/...` の中立レーンへ置き、`data/phase1_seed10/...` は使わない。
- local の legacy `phase1_seed10` helper は残存しうるが、remote `phase1_seed10` は既定 sync 本流に含めない。新規書き込みで revive しない。
- cleanup レーンは Phase 3 拡張中もクローズ維持。
- 文書表記ルール: 本プロジェクトの docs 更新・運用記録・次タスク記述は原則日本語で統一し、英語の見出し・本文・箇条書きは使わない。

Phase 3 固定運用方針
- 通常運用の主導線は scope 一括 closeout とし、人間の操作は `1 block = 1 scope = 1 command` を基本とする。
- block closeout の人間向け主導線は `run_block_closeout.py` に統一し、既存のカテゴリ別 runner は補助導線としてのみ残す。
- block closeout は current formal artifacts を source of truth とし、差分がある artifact 群だけを更新対象にし、差分がない群は自動 skip とする。
- 10件単位 block 運用は Phase 3 の汎用コード安定化フェーズにおける検証運用であり、恒久ルールにしない。
- 安定化後の通常運用は、差分 scope 一括または対象 scope 一括で closeout を行い、`initial10 / new10 / artists / exhibitions` のような断片コマンド打ち分けを主導線にしない。
- 各 block は、current 反映、同一 scope の `rag_gellery_breakdown_master.xlsx` 更新、Artist Works Images の OpenCLIP current 反映確認、R2 sync、closeout report がすべて完了して初めて closeout 完了とする。
- 上記のいずれかが未完了の状態では、初期10件 / 新10件 / 今後の全 gallery block を問わず、次 block に進まない。
- 安定化フェーズ残タスクとしての `new10` verify-first は例外的に許容するが、通常運用ルールへ昇格しない。

次タスク
- [ ] 安定化フェーズ残タスクとして `phase3_fixed_block_next10_targets.csv` の closeout apply 判断を `run_block_closeout.py` 主導線で行う。verify-first は planned で通過済みだが、恒久運用ルールにはしない。
- [ ] 通常運用の主導線を scope 一括 closeout に統一したまま、差分 scope 一括運用へ移行する。
- [ ] residual の可視化を継続する（fixed10: Bombon 403 / Callirrhoë image 0）。
- [ ] cleanup レーンを閉じたまま、explicit-user-task mode で主ロードマップを継続する。

削除同期メモ（2026-03-30）
- retired 済みの artist-specific advisor レーンと専用 text corpus / config / vector / UI route / docs はベースライン対象外。
- 以後の handoff / task planning は、現行ベースラインを機能1 / 2 / 3 / 4 / 6 / 7 のみとして扱う。

引き継ぎメモ
- まず 01 を正本として参照する。
- 02 を派生運用契約として参照する。
- 進捗と次タスクの同期は本 03 で維持する。
