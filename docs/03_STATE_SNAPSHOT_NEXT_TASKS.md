03_STATE_SNAPSHOT＋NEXT_TASKS（統合）
PROJECT_SLUG: ART_PULSE_EDITOR

DOC_PATHS（固定：Codexはここを参照）
- SSOT_01: ./docs/01_PROJECT_SPEC_CURRENT_FULL.docx
- DERIVED_02: ./docs/02_RAG_SPEC_DERIVED.md
- STATE_03: ./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- GALLERY_CSV_FRIEZE: ./data/gallery_lists/gallery_list_frieze_london.csv
- GALLERY_CSV_LISTE: ./data/gallery_lists/gallery_list_liste.csv

STREAMLIT_ENTRYPOINT（固定）
- Streamlit Cloud main file path: app.py
- Local run: streamlit run app.py

SOURCE_SSOT: 01_PROJECT_SPEC_CURRENT_FULL.docx
LAST_UPDATED: 2026-03-11 16:32 JST


========================
03_EDIT_POLICY（03の更新方針：ここが崩れると詰むので固定）
========================
■ロック（Codexが絶対に変更しない）
- PROJECT_SLUG / SOURCE_SSOT
- 「重要な運用ルール（迷子防止）」の本文（方針は固定）
- CODEX_SNIPPETS（A0/A/B/C）の骨格（※文言の微調整はOKだが、意味を変えない）

■更新対象（Codexが更新してよい／更新すべき）
- LAST_UPDATED：03を更新したときだけ更新する（日時はJST）
- STATE_SNAPSHOT（現在地）：
  - 小Taskごとに毎回更新は不要
  - 「いまの最優先フェーズが変わった時」「直近の到達目標が変わった時」「実行フェーズが一区切りついた時」「handoff前」に更新する
- NEXT_TASKS：
  - 小Taskの完了だけなら、都度更新は必須ではない
  - 数Taskぶんの完了をまとめて [x] 化してよい
  - 新しい作業が確定したら、節目の同期時に追記し、優先順位に並べ替える
- CODEX_TASK_PROMPTS：
  - NEXT_TASKS に新しい番号（8,9…）を正式追加した時だけ、同じ番号のプロンプトを作る
- CHANGELOG：
  - 毎Taskではなく、作業の節目ごとにまとめて追記してよい（「何をした／どこまで到達した／次は何」）

■SSOT（01）と索引（02）の扱い（事故防止：重要）
- Codexは SSOT（01）/索引（02）の内容変更が必要だと判断した場合でも、
  “勝手に編集しない”。
  必ず「変更理由／変更案（置換文）／影響範囲」を提示し、
  ユーザー合意を取ってから反映する。
- 02/03は、01に矛盾したら必ず01が正。

■中断の定義（迷わないように固定）
- 次のいずれかに当てはまれば「中断」扱いとし、CODEX_SNIPPETS B（中断・締め）を必ず実行する：
  1) 作業が未完で止まる（実装途中／テスト未実行／エラー未解決／コミット前など）
  2) 次に戻るとき、どこまでやったか思い出す必要がある
  3) 作業の流れが切れる（別の用事に移る／しばらくCodex会話を止める）

■Codexが毎回やるべきこと（小Taskの標準）
- ① 計画（短く：変更ファイル／変更点／動作確認コマンド）
- ② 実装
- ③ 動作確認
- ④ 短い結果報告（変更ファイル / 実行コマンド / 生成物パス / exit code / 次の最優先タスク）
- ⑤ 03/04更新は、節目に当たる場合だけ実施する
   - 節目の例：2-4Task進んだ時 / 実行フェーズ完了時 / 長めの中断前 / handoff前 / 重要な判断が固まった時
   - 更新時の確認順は 02 -> 01 -> 03/04 とする
   - SSOTに書かれていない「抽出/保存仕様（RAGルール）」は03/04に足さない（必要なら「SSOT追記案」として提案し合意を取る）。※運用固定（DOC_PATHS/実行コマンド/現在地の記録）は03に書いてOK
- ⑥ 次に進むタスク番号を1つ選び、必要なら対応する「TASK n プロンプト全文」を提示
  → ユーザーが “そのままコピペで次依頼” できる状態にする

■SSOT整合チェック（再発防止：必須）
- 実装前に必ず「01章ID」「02 CARD_ID」「変更対象関数」を1対1対応で明示する。
- Artists抽出は「一覧URL→詳細URL抽出→詳細ページ抽出」を必須とし、一覧URL直抽出は禁止。
- パラメータはカテゴリ別正本を使用し、Exhibitions用上限のArtists流用を禁止する。
- Artist Works Images のローカル作業キャッシュは FAIR_SLUG 単位で一本化し、gallery単位のディレクトリ分割は行わない（識別はファイル名/メタデータで保持）。
- 暫定運用: artists抽出上限は各gallery 1件（安定化まで）。安定確認後、段階的に引き上げて最終80へ戻す。
- 実装後に `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` へ内訳追記し、03/04へ失敗理由上位を記録する。
- `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` の内訳は日本語で記述する（英語のみの追記は禁止）。
- このルールは **全RAGカテゴリ（Artists/Exhibitions/Tarutani、画像/テキスト/ベクター、同期含む）** に常時適用する。


========================
STATE_SNAPSHOT（現在地）
========================
■いまの最優先フェーズ（Codexが随時更新する）
- Phase 2 app run-state (current baseline):
  - Feature 1 Art Pulse: completed
  - Feature 2 Exhibition Search: completed
  - Feature 3 Artist Search: almost completed (current-first read-only smoke passed)
  - Feature 4 Advisor: kickoff completed (type1 minimal grounded draft connected in app)
  - type2 status: gate-only confirmation, not implementation-complete
  - current/history rebaseline phase: completed (A2-A9)
  - Immediate priority: A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01
- NOTE: keep this current-goal line updated whenever phase priority changes.
- Fixed master roadmap alignment (from SSOT 01):
  - 5 RAG categories (Tarutani_Text / Artist Works Images / Artist Text / Exhibitions Image / Exhibitions Text) are established at 10-gallery operational scope
  - App features status: 1/2 completed, 3 almost completed, 4 kickoff completed (type1 minimal)
  - Mandatory pre-Advisor phase (current/history canonical rebaseline) is completed and fixed in roadmap
  - Role split: current=day-to-day canonical / history=audit archive / R2=primary persistent sync target for current / local=current fallback
  - app/read-only must read current first
  - After 4-6 are available, validate operations using 10-gallery RAG only
  - Then expand to initial 2025 scale (~150 galleries)
  - Then extend yearly toward long-term 200+ galleries

■いま出来ていること（事前準備・現状）
- Git（PC側）＋GitHub接続：開発の土台 完了
- Python環境（venv）＋requirements＋Playwright導入：実行できる状態 完了
- OpenAI API準備（課金/キー）：LLM側が動く状態 完了
- Gemini API準備（キー）：Text Embeddingが動く状態 完了
- Cloudflare R2準備（バケット/キー/接続）：正本ストレージ 完了
- Streamlit Cloud（GitHub連携＋Secrets）：デプロイできる状態 完了
- 最小スモークテスト：ローカル→クラウドまで通す 完了
- VSCode→Codex拡張インストール＋サインイン済み 完了
- ギャラリーリスト（全件）作成済み：
  - Frieze 95件 / Liste 52件
- ギャラリーリストCSV（repo配置＆コミット済み）
  - data/gallery_lists/gallery_list_frieze_london.csv
  - data/gallery_lists/gallery_list_liste.csv
- Phase1 seed10 最小実行入口（4-1 Exhibitions Textのみ）を作成
  - run_phase1_seed10.py
  - 取得ループ内LLM加工なし（headline_ja / summary_ja は空で保存）
  - 生成物：data/phase1_seed10/raw/*.jsonl, data/phase1_seed10/logs/*.json
- TASK 4 完了（4-1 Exhibitions Text）
  - 同じコマンド2回実行で自動スキップが動作（KNOWN_FAILED_URL 系）
  - 台帳を再利用して 2回目以降の再取得を抑制
- TASK 5 完了（台帳/失敗ログ運用）
  - failed_fetches に reason_code / attempt_count / last_attempt_at を保持
  - 再実行時はクールダウン・上限判定で打ち切り/スキップ（無限再試行を防止）
  - 補足：saved=0 は異常ではない。既存raw 64件があるrunでは new_saved=0 / skipped_known_saved_page=64 / skipped_out_of_year=14 が正常
- TASK 6 完了（Enrichment事後バッチ入口）
  - run_enrichment_seed10.py を追加（raw読込→未Enrichment抽出→requests/summary出力）
  - 生成物：data/phase1_seed10/enrichment/enrichment_requests_seed10_2025.jsonl
  - 生成物：data/phase1_seed10/enrichment/enrichment_summary_seed10_2025.json
- TASK 7 完了（Tarutani_Text 取り込み）
  - run_tarutani_text_import.py を追加（docx/pdf読込→tarutani_text.jsonl追記）
  - 生成物：data/Tarutani_data/tarutani_text.jsonl（16件）
  - 生成物：data/Tarutani_data/tarutani_text_import_summary.json
  - 初回取り込み時は PDF由来レコードに text="" を含む状態（OCRなし）
- TASK 8 完了（Tarutani_Text Enrichment入口）
  - run_enrichment_tarutani_text.py を追加（tarutani_text.jsonl読込→未付与headline_ja候補を抽出）
  - 生成物：data/Tarutani_data/enrichment/enrichment_requests_tarutani_text.jsonl（7件）
  - 生成物：data/Tarutani_data/enrichment/enrichment_summary_tarutani_text.json
- TASK 9 完了（Tarutani_Text headline_ja 反映）
  - run_enrichment_tarutani_text_apply.py を追加（requests読込→headline生成→tarutani_text.jsonl更新）
  - 生成物：data/Tarutani_data/enrichment/enrichment_output_tarutani_text_*.jsonl
  - 生成物：data/Tarutani_data/enrichment/enrichment_apply_summary_tarutani_text_*.json
  - 実行結果：updated=7 / failed=0（再実行は updated=0 / failed=0）
- TASK 9.5 完了（TarutaniRAG向けPDF抽出＋バックフィル）
  - run_tarutani_text_pdf_backfill.py を追加（TarutaniRAGのPDFのみ本文抽出。OCRなし）
  - 実行結果：pdf_records_updated_with_text=9 / pdf_records_still_empty_after=0
  - 再Enrichment結果：requests candidates=9 → apply updated=9 / failed=0
  - 現在値：tarutani_text.jsonl は 16件すべて text非空・headline_ja非空
- TASK 10 完了（Tarutani_Text Embedding/Index入口）
  - run_vectorize_tarutani_text.py を追加（Post-fetchバッチ。fetchループ非依存）
  - 実行結果：records_total=16 / chunk_size=1000 / overlap=200 / embedding_input_count=76 / embedded=76 / failed=0
  - 生成物：data/Tarutani_data/vector/tarutani_text_index.npy
  - 生成物：data/Tarutani_data/vector/tarutani_text_meta.jsonl
  - 生成物：data/Tarutani_data/vector/tarutani_text_vectorize_summary.json
  - 生成物：data/Tarutani_data/vector/artifact_manifest.json
- TASK 11 完了（Tarutani_Text 検索スモークCLI）
  - run_search_tarutani_text.py を追加（RETRIEVAL_QUERY / 1536次元 / L2正規化）
  - 実行結果：query=「曲線と直線」, top-k=5 を出力（source_path / chunk_index / score）
  - 生成物：data/Tarutani_data/vector/search/tarutani_text_search_results_*.jsonl
  - 生成物：data/Tarutani_data/vector/search/tarutani_text_search_summary_*.json
- TASK 12 完了（Tarutani_Text コンテキストJSON整形）
  - run_build_tarutani_context.py を追加（TASK11検索を呼び出して context JSON を生成）
  - 実行結果：query=「曲線と直線」, k_returned=5, empty_excerpt=0
  - 生成物：data/Tarutani_data/context/tarutani_text_context_*.json
  - 生成物：data/Tarutani_data/context/tarutani_text_context_summary_*.json
- TASK 13 完了（機能⑤向け回答スモークCLI）
  - run_answer_tarutani_advisor.py を追加（TASK12 context を利用して回答生成）
  - 実行結果：question=「曲線と直線の要点を教えて」, k_used=5, answer_chars=396
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_*.json
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_summary_*.json
- TASK 14 完了（機能⑤回答CLIのcontext固定再現モード）
  - run_answer_tarutani_advisor.py に `--context-path` を追加（query再生成と排他）
  - 実行結果：context_input_mode=fixed_context を summary に保存し、query再生成モードと区別可能化
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_*.json
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_summary_*.json
- TASK 15 完了（機能⑤回答の比較レポートCLI）
  - run_compare_tarutani_answers.py を追加（query再生成 vs context固定を1回で比較）
  - 実行結果：query_chars=585 / fixed_chars=482、evidence_count は双方5、主要数値比較で 700 は双方True・180 は双方False
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_compare_*.json
- TASK 16 完了（差分ガード）
  - run_compare_tarutani_answers.py に `--fail-on-mismatch` と `watch_numbers`（既定: 700,180）を追加
  - 実行結果：一致ケースは `guard_passed=true` で exit 0、不一致ケースは `mismatch_fields` を保存して exit 2
  - 生成物：data/Tarutani_data/answers/tarutani_advisor_answer_compare_*.json（`guard_passed` / `mismatch_fields` 含む）
- TASK X-2 完了（共通ストレージ方針の明文化＋Tarutani派生/ログR2バックアップ導線）
  - SSOT 5-7/5-8 に「source/derived/vectorはR2正本」「local dataはキャッシュ」「重要ログのR2 logsバックアップ推奨」を追記
  - SSOT 5-5 に Tarutani派生データ/重要ログのR2バックアップ対象を追記
  - run_tarutani_r2_sync.py を `--scope source|derived|logs|all` 対応へ拡張し、`tarutani/{source,derived,logs,vectors}/...` へ同期可能化
  - 実行結果：derived 初回 uploaded=20 / 再実行 skipped=20、logs 初回 uploaded=8 / 再実行 skipped=8（+新規2）
- X-3 反映（Exhibition/Artist章への最小追記）
  - SSOT 5-1（Exhibitions Text）/5-3（Artist Text）に、5-7/5-8参照・保存分類（source/derived/logs/vectors）・カテゴリ分離キー・manifest準拠を追記
  - 02の該当カード（04/05/15）も01準拠で索引更新（新仕様の追加なし）
- SSOT更新（TarutaniRAG PDF抽出ルール）
  - 01 の 4-5 に「TarutaniRAGはPDF本文抽出を標準実装とする（未実装理由の一律text空を禁止）」を追記
  - 抽出失敗PDFのみ text="" とし、extract_status に理由を残す方針へ明確化
- SSOT更新（TarutaniRAG Embeddingチャンク方針）
  - 01 の 5-9 に「TarutaniRAGは先頭2000字1本ではなく、1000字チャンク＋200字オーバーラップで複数埋め込み」を追記
- Tarutani_data のR2正本運用を整理（最小差分）
  - SSOT 5-5 に「R2正本 / source_pathメタ保持 / Git非コミット方針」を追記
  - run_tarutani_r2_sync.py を追加（dry-run/apply, logs出力）
  - 実行結果：apply 1回目 uploaded=16 / failed=0、2回目 skipped=16 / failed=0（冪等）
- C対応（saved=0 切り分け）
  - DNS切り分け後に実ネット再実行で saved=64 を確認（原因はネット経路と既存失敗台帳クールダウンの複合）

■作業環境メモ（固定しておく）
- OS：Windows 11 + WSL2 Ubuntu
- Repo：art_pulse_editor
- venv：.venv_art_pulse_editor
- 実行ディレクトリ：repo 直下

■重要な運用ルール（迷子防止：本文ロック）
- 仕様や判断に変更が出たら：SSOT（01）を更新してから実装を変える（口頭だけで変えない）
- 02は索引（カード集）。数値は転載しない。衝突したら01を正とする
- 日々の作業ログ・次タスクはこのファイル（03）に集約する（01/02に散らさない）
- 機能削除・無効化・置換で機能が消える可能性がある場合は、必ず事前に合意を取る
- 4章は「4-0共通→4-1〜」を分けて実装・検証（混ぜない）
- LLM加工（headline_ja / かな等）は取得ループ内で逐次実行しない（FetchとEnrichmentを分離）
- ドメイン専用ハードコード増殖は禁止（頻出ドメイン×汎用ロジックのみ改善／取れない分はログ化して割り切る）
- 共通化できる判定・抽出ロジックは必ず共通モジュールへ寄せる。個別スクリプトへの重複実装を禁止し、修正点を1箇所に集約する（シンプル運用固定）。

■リスク台帳（短く：必要に応じて更新OK）
- 429/403/Timeout：同一ドメインで連続したら打ち切り、失敗一覧に残す
- R2 env の名前ゆれ：ローカル .env と Streamlit Secrets を揃える（値は書かない）


========================
NEXT_TASKS（次回やること）
========================
優先度順（上から実行）。終わったら [x] にする。
※各タスクは「計画→実装→動作確認→短い結果報告」を1セットで回す。03/04更新は数Taskごと・実行フェーズの節目・長めの中断前・handoff前にまとめて行う。
※R2運用テンプレは `TASK PREP-R2-GUARD-20260227` を参照（dry-run -> apply固定）。
※重要: RAG生成（画像/ベクター/派生JSON）だけではR2へ自動反映されない。生成タスクの完了条件に「R2同期（dry-run -> guarded apply）」を必須で含める。
  - 例（Phase1 derived plan）: `python run_r2_sync.py plan --scope phase1_seed10_formal --run-id <RUN_ID>`
  - 例（Phase1 derived apply-upload）: `python run_r2_sync.py apply-upload --scope phase1_seed10_formal --apply --run-id <RUN_ID>`
※同期運用（現行）: R2同期入口は `run_r2_sync.py` のみ。`plan -> apply-upload -> apply-prune` を明示実行する。
※追加ルール: prune は `--confirm-prune` + `--max-prune` + stability確認（2回一致）を必須とする。
※scope運用（固定）: defaultは `phase1_seed10_formal` / `tarutani_source`。`gallery_lists` は opt-in（GitHub正本扱い）かつ prune禁止。
※旧入口注記: `run_phase1_seed10_r2_sync.py` / `run_tarutani_r2_sync.py` / `run_r2_auto_sync.py` / `r2_auto_sync.py` は廃止済み（03内の旧名称は当時ログ参照のみ）。
※2026-03-06 同期完了事実: apply-upload成功（phase1_seed10_formal uploaded=88 / tarutani_source uploaded=77）、apply-prune成功（phase1_seed10_formal extra_remote 72->0 / deleted_count=72）、旧入口4本削除済み（詳細は04参照）。
※共通スキップ（固定）: `data/gallery_lists/skipped_galleries_registry.csv` に登録されたgalleryは Artists/Exhibitions の text/image 抽出すべてで自動スキップする。
※共通同期（固定）: Artists/Exhibitions の text/image/vector/derived すべてに同一の guarded R2同期ルール（dry-run -> guarded apply）を適用する。

[x] 190) hundreds of galleries 向け標準フロー具体化（完了）
    - 目的：④ Exhibitions Image を、10ギャラリー成功で終わらせず、何百ギャラリーへ横展開できる標準実行フローとして固定する
    - 位置づけ：これは 5種類RAGのうち「④ Exhibitions Image を先に仕上げる」ための最優先タスク
    - 前提：現在の10ギャラリー正式状態を壊さない。コード変更・rerunは設計確定まで行わない
    - 成立条件：分類条件（Keep-Current / Safe-But-Provenance-Gated / Guard-First）と、各レーンの入出力・QA・adoption条件を1本化する
    - 次段条件：④ Exhibitions Image が 10ギャラリーで汎用的に70%以上を安定達成したら、次に ⑤ Exhibitions Text へ進む

[x] 228) Exhibitions Image completion closure memo（完了）
    - 目的：TASK215〜227の remediation / guard hardening / final isolated rerun retry を確定履歴として closure し、④ Exhibitions Image を completion として正式記録する
    - 完了根拠：`PASS_FOR_CLOSURE` / `READY_FOR_COMPLETION_CLOSURE` / `CURRENT_FORMAL_STILL_VALID` / Baton再発0 / Athr再出現0 / duplicate 0 / `SUSPICIOUS_*=0` / `REJECT_FOR_COMPLETION=0`
    - 補足：final isolated rerun retry の新規1件は `SAFE_BUT_NOT_NEEDED` として formal 採用不要（closure blocker ではない）

[x] 229) Exhibitions Text kickoff / spec start（方針変更でクローズ）
    - 備考：現行ロードマップでは、④ Advisor 前に current/history 正本再編を先行するため、本タスクは優先度を引き継がずクローズ

[x] 189) 03/04 FINAL SYNC EXECUTION（完了）
    - 10ギャラリー正式状態を03/04へ最終同期（01/02更新なし）
[x] 286) Artists Text enrichment full apply (done)
    - scope: approved fields headline_ja / summary_ja / artist_name_kana to 2025 formal raw
    - result: full apply completed (see 04 log entry)

[x] 287) Artists enrichment target hygiene guard (done)
    - scope: replace target-row-miss with generic target hygiene guard
    - result: SKIPPED_TARGET_GUARD_NON_ARTIST_UTILITY_URL=3 / TARGET_ROW_NOT_FOUND=0

[x] 288) Artist Search re-baseline (done)
    - scope: confirm current implementation and apply only minimal fix
    - result: status = almost completed, read-only route usable

[x] 289) docs 01-04 sync (done)
    - scope: integrate pre-Advisor current/history roadmap into official docs

[x] 290) PRE_ADVISOR_STORAGE_CONTRACT_01 (done)
    - scope: fixed storage contract only (no code migration / no data move / no R2 sync execution)
    - result: writer/readers, R2/local fallback, anti-mixing, migration policy fixed in 01/02
    - note: root rebaseline was identified as an additional required fix after TASK290

[x] 290B) STORAGE_ROOT_REBASELINE_01 (done)
    - scope: changed canonical roots only (contract idea unchanged)
    - result: current=`data/current/enrichment/`, history=`data/history/enrichment/{artists,exhibitions}/`
    - role fix: `data/phase1_seed10/` is explicitly treated as seed10 working/validation lane

[x] 291) A2_STORAGE_LAYOUT_SCAFFOLD_01 (done)
    - scope: create current/history directory scaffold and manifest-ready placeholders only
    - constraints: no payload move, no writer switch, no read-path switch, no R2 sync execution

[x] 292) A3_WRITER_HISTORY_PROMOTION_01 (done)
    - scope: artists/exhibitions apply writer switched to history timestamp save -> current fixed-name promotion

[x] 293) A4_MIGRATION_PLAN_AND_DRYRUN_01 (done)
    - scope: legacy enrichment artifacts inventory + migration dry-run manifest for current/history

[x] 294) A5_MIGRATION_EXECUTE_COPY_01 (done)
    - scope: non-destructive copy from legacy seed10 artifacts to new current/history lanes

[x] 295) A6_READER_CURRENT_FIRST_SWITCH_01 (done)
    - scope: app/read-only switched to current-first with migration-period legacy fallback only

[x] 296) A7_R2_TARGETS_CURRENT_FIRST_UPDATE_01 (done)
    - scope: r2 targets updated to current-primary / history-audit / legacy-lane-off-by-default

[x] 297) A8_GUARDED_R2_SYNC_EXECUTION_01 (done)
    - scope: guarded upload run for current+history lanes only (no prune/delete)

[x] 298) A9_PHASE2_CURRENT_CANONICAL_SMOKE_01 (done)
    - scope: feature 1/2/3 smoke on current canonical structure passed

[x] 299) LEGACY_ENRICHMENT_ARTIFACT_CLEANUP_01 (done)
    - scope: duplicate legacy enrichment apply outputs/summaries cleanup under seed10 lane

[x] 300) A10_PHASE4_ADVISOR_KICKOFF_01 (done)
    - scope: advisor type1 current-canonical grounded context connection + minimal UI smoke

[x] 301) DOC_SYNC_POST_ADVISOR_KICKOFF_01 (this task)
    - scope: docs 01/02/03/04 synchronized to post-kickoff baseline

[ ] 302) A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01 (highest priority)
    - scope: advisor type1 answer quality/evidence quality tuning under current canonical constraints

[x] 1) ギャラリーリストCSVを repo に配置してコミットする（完了）
    - 置き場所：data/gallery_lists/
    - ファイル：
      - gallery_list_frieze_london.csv（95件）
      - gallery_list_liste.csv（52件）
    - 形式：CSV / ヘッダーなし / UTF-8 / 1行=1ギャラリー

[x] 2) 02_RAG_SPEC_DERIVED.md（カテゴリ別カード集）を生成して固定する（3本立ての土台）
    - 01（SSOT）を読み、RAG抽出・保存に必要なルールを「カテゴリ別カード」で整理する
    - 02は “参照しやすさのための索引”。衝突したら必ず01が正。
    - まずは Phase1 に必要な範囲（4-0共通 / 4-1 Exhibitions Text）だけでOK

[x] 3) Phase 1 用の「最小実行入口スクリプト」を作る（seed10）
    - 例：python run_phase1_seed10.py
    - seed10の定義：
      - frieze = gallery_list_frieze_london.csv の先頭5件
      - liste  = gallery_list_liste.csv の先頭5件
    - 目的：UIより先に、取得→保存が通ることを確認

[x] 4) 4-1 Exhibitions Text だけで「取得→保存→再実行でスキップ」を成立させる
    - まずはこの1カテゴリだけでOK（他カテゴリへは後で拡張）
    - 成立条件：
      - 1回目：取得→保存→完走
      - 2回目：同じコマンドで “自動スキップ” が効く（台帳が働く）

[x] 5) 台帳（visited_pages / failed_fetches など）を保存し、失敗をログ化して割り切れる状態にする
    - 目的：取れない分はログに残して前進（頻出ドメイン×汎用ロジックのみ改善）
    - 成立条件：失敗URLが一覧で追える／再実行しても同じ失敗を無限に繰り返さない

[x] 6) （余力があれば）Enrichment（見出し/かな等）を「事後バッチ」で回す導線を作る
    - FetchとEnrichmentは分離（取得ループ内で逐次実行しない）
    - UIはPhase 2でOK。まずはバッチ/CLIで成立させる

[x] 7) Tarutani_Text 取り込み（条件付き：忘れ防止ゲート）
    - 条件：「Phase1 seed10 が2回連続で完走」したら着手する
      - ここでいう完走：
        - スクリプトが例外で落ちずに終了（exit code 0）
        - failed_fetches が “残る” のはOK（ログ化されていればOK）
    - 着手の最初に必ずやること：
      - Codex は作業開始前に、ユーザーへ「TarutaniRAGの配置場所/形式」を質問してから開始する
    - 目的：機能⑤用の文章RAG（作品画像は扱わない）

[x] 8) Tarutani_Text のPost-fetch Enrichment入口を作る
    - 目的：Tarutani_Text（tarutani_text.jsonl）の headline_ja 付与を事後バッチで回す導線を作る
    - 制約：取り込みループ内でLLMを呼ばない（Fetch/Enrichment分離）
    - 成立条件：
      - python run_enrichment_tarutani_text.py（例）が実行できる
      - tarutani_text.jsonl を読み、未付与headline_ja候補の requests/summary を出力できる

[x] 9) Tarutani_Text のheadline_jaを事後バッチで実生成し、jsonlへ反映する
    - 目的：TASK 8で作成した requests を使って headline_ja を生成し、tarutani_text.jsonl を更新する
    - 制約：取り込み（fetch）ループでは実行しない。Post-fetchのバッチとして実行する
    - 成立条件：
      - headline_ja の生成結果（output）が保存される
      - tarutani_text.jsonl で headline_ja が一部以上更新される
    - 更新件数/未更新件数の summary が保存される
    - メモ：Tarutani_data のR2同期は本実行まで完了（uploaded=16, failed=0）。再実行で skipped=16 を確認（冪等）。

[x] 9.5) TarutaniRAG向けPDF抽出を実装し、既存PDFをバックフィルする
    - 目的：Tarutani_Textに限り、PDF本文を抽出して text を埋め、再Enrichment/検索に載せる
    - 制約：TarutaniRAGのみ対象（他カテゴリのPDF処理は変えない）
    - 成立条件：
      - PDF抽出実装後に tarutani_text.jsonl の text 空件数が減る
      - 抽出失敗分は text="" のまま + extract_status に理由が残る
      - headline_ja 再生成で更新件数が summary に出る
    - 実行メモ：backfill updated=9 / still_empty=0、再Enrichment apply updated=9 / failed=0

[x] 10) Tarutani_Text のEmbedding/Index入口を作る
    - 目的：headline_ja 付与済み tarutani_text.jsonl を対象に、ベクトル化と検索用index生成の入口を作る
    - 制約：fetchループには組み込まない（Post-fetchバッチとして分離）
    - 成立条件：
      - python run_vectorize_tarutani_text.py（例）が実行できる
      - embedding入力件数 / skip件数（text空など） / 生成物パスが summary に出る
      - 生成物（index + meta）が保存される
    - 実行メモ：chunk_size=1000 / overlap=200 / embedding_input_count=76 / embedded=76 / failed=0

[x] X) SSOT追記：埋め込み入力メタ3項目（text_len / embed_input_len / is_truncated）の明文化と実装反映
    - 目的：後で取りこぼし分析できるよう、埋め込み時メタ3項目をSSOTと実装で統一する
    - 反映：01の5-9へ追記済み、run_vectorize_tarutani_text.py のmeta出力へ3項目を追加済み
    - 確認：meta 76件すべてで text_len / embed_input_len / is_truncated を確認

[x] X-2) ストレージ方針をSSOTで明文化し、Tarutani派生データ/ログのR2バックアップ導線を追加
    - 目的：共通ストレージ方針の運用ぶれを防ぎ、Tarutani派生/ログ/将来vectorのR2退避導線を最小差分で追加する
    - 反映：01の5-5/5-7/5-8追記、run_tarutani_r2_sync.py の scope拡張（source/derived/logs/all）
    - 実行メモ：derived 初回 uploaded=20 / 再実行 skipped=20、logs 初回 uploaded=8 / 再実行 skipped=8（+新規2）

[x] X-3) Exhibition / Artist 章へ保存方針の最小追記（SSOT明確化）
    - 目的：Exhibition/Artist章でも、共通方針（5-7/5-8）参照と保存分類（source/derived/logs/vectors）を明確化する
    - 反映：01の5-1/5-3へ最小追記、02のCARD 04/05/15を01準拠で索引更新
    - メモ：R2キーはカテゴリ分離、manifestは5-8最低項目準拠

[x] 11) Tarutani_Text の検索スモークCLIを作る（chunk index検証）
    - 目的：TASK10の index+meta を使って、Tarutani_Text の top-k 検索結果をCLIで確認できるようにする
    - 制約：RETRIEVAL_QUERY（Gemini, 1536次元, L2正規化）でクエリ埋め込みし、TASK10の index 空間と混在させない
    - メモ：Tarutani vectors生成時は R2 `tarutani/vectors/` へ保存し、`artifact_manifest.json` を同梱する
    - メモ：Exhibition/Artist も Tarutani と同じ保存分類（source/derived/logs/vectors）で統一し、manifestは5-8準拠で運用する
    - 成立条件：
      - python run_search_tarutani_text.py --query \"...\" が実行できる
      - top-k の source_path / chunk_index / score を出力できる
      - 検索summary（入力クエリ、k、出力先）を保存できる
    - 実行メモ：query=「曲線と直線」で top-k=5 を確認、results/summary 保存済み
    - 実行メモ：検索優先度プロファイル（`config/tarutani_text_search_profile.json`）を反映。`曲線と直線_概要.docx` と `垂谷_ステートメント.docx` を優先しつつ、同一source偏り抑制（max_per_source=1）を適用。

[x] 12) Tarutani_Text 検索結果を機能⑤向けコンテキストJSONに整形する
    - 目的：検索top-k結果を、機能⑤でそのままLLM投入できるコンテキスト形式（根拠付き）に変換する
    - 制約：取得ループには組み込まない（Post-fetchバッチのまま）
    - 成立条件：
      - python run_build_tarutani_context.py --query \"...\" が実行できる
      - source_path / chunk_index / score / excerpt を含む context JSON が保存される
      - 03のCHANGELOGに反映される
    - 実行メモ：query=「曲線と直線」で context JSON/summary を保存（k_returned=5, empty_excerpt=0）

[x] 13) 機能⑤向け回答スモークCLIを作る（Tarutani context利用）
    - 目的：TASK12の context JSON を入力に、機能⑤の回答（根拠付き）をCLIで再現できる入口を作る
    - 制約：Tarutani_Text は検索結果一覧に混ぜず、回答の根拠セクションとしてのみ使用する
    - 成立条件：
      - python run_answer_tarutani_advisor.py --question \"...\" --query \"...\" が実行できる
      - 回答本文 + 根拠（source_path / chunk_index / score / excerpt）を保存できる
      - 03のCHANGELOGに反映される
    - 実行メモ：query=「曲線と直線」+ question=「曲線と直線の要点を教えて」で回答JSON/summaryを保存（k_used=5）
    - 実行メモ：数値競合時は最新要約+rank上位を優先するよう調整し、再実行で「約700名」を採用（「180名」は不採用）を確認

[x] 14) 機能⑤回答CLIに再現モード（context固定入力）を追加する
    - 目的：API再検索を省き、既存context JSONを指定して回答再生成できるようにする（検証/比較を容易化）
    - 制約：Post-fetch分離を維持し、Tarutani_Text は回答根拠セクションとしてのみ使用する
    - 成立条件：
      - python run_answer_tarutani_advisor.py --question \"...\" --context-path \"...\" が実行できる
      - query経由（context再生成）と context固定入力の両モードが summary で識別できる
      - 03のCHANGELOGに反映される
    - 実行メモ：`--context-path data/Tarutani_data/context/tarutani_text_context_20260223T123040Z.json` で `context_input_mode=fixed_context`、`--query "曲線と直線"` で `context_input_mode=query_rebuild` を確認（summaryで両モード識別）

[x] 15) 機能⑤回答の比較レポートCLIを作る（query再生成 vs context固定）
    - 目的：query再生成モードと context固定モードの回答差分を可視化し、再現性確認を短時間で回せるようにする
    - 制約：Tarutani_Text は回答根拠セクションとしてのみ使用し、検索結果一覧へは出さない
    - 成立条件：
      - python run_compare_tarutani_answers.py --question \"...\" --query \"...\" --context-path \"...\" が実行できる
      - 回答本文長・根拠件数・主要数値（例：700/180）の差分サマリを保存できる
      - 03のCHANGELOGに反映される
    - 実行メモ：`--question "曲線と直線の要点を教えて" --query "曲線と直線" --context-path "...123040Z.json"` で比較実行し、`contains_700=True/True`・`contains_180=False/False` を確認

[x] 16) 機能⑤回答に差分ガードを追加する（数値競合アラート）
    - 目的：比較結果を使って、主要数値（例：700/180）に差分が出た時に警告を出すガードをCLIに追加する
    - 制約：Tarutani_Text は回答根拠セクションとしてのみ使用し、検索結果一覧へは出さない
    - 成立条件：
      - python run_compare_tarutani_answers.py ... --fail-on-mismatch で差分検知時に非0終了できる
      - 差分がなければ0終了し、summary に guard 判定結果を保存できる
      - 03のCHANGELOGに反映される
    - 実行メモ：最新context指定では `guard_passed=true`（exit 0）を確認。旧context指定では `mismatch_fields=['contains_700','contains_180']`（exit 2）を確認

[x] 17) Phase1本体へ復帰：Tarutaniで作った比較ガードの“型”をExhibitions/Artistへ横展開する準備をする
    - 目的：
      - Tarutani_Text で作った比較CLI/差分ガード（再現モード・比較・guard）の実績を、Phase1本体（Exhibitions/Artist）へ転用できるように“共通の見張り項目”を整理する。
      - Tarutani側の追加深掘りではなく、本体優先で前進する。
    - 参照ファイル：
      - 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists（共通方針・保存・ログ）
      - 02（索引）共通保存方針・manifest・ログ関連カード
      - run_phase1_seed10.py
      - （あれば）run_summary_seed10_2025.json / manifest / visited_pages / failed_fetches
      - run_compare_tarutani_answers.py（比較ガードの“型”の参照用）
    - 制約：
      - 取り込みループ内でLLM加工しない（Post-fetch分離を維持）
      - ドメイン専用ハードコードを増やさない
      - Tarutani_Text は今回は“参照実装”として扱い、Tarutani側の新機能追加はしない（保守のみ）
    - 完了条件：
      - Exhibitions/Artists に横展開するための「共通ガード項目」を明文化できる（例：必須キー存在、内部整合、件数サマリ整合、manifest/台帳整合）
      - 次タスクで実装する対象CLI（または新規CLI名）と、最小実装範囲（どのJSON/manifestを比較するか）を決められる
      - 03 の NEXT_TASKS の 17) を [x]、CHANGELOG追記
      - 次の最優先タスク（TASK 18）のプロンプト全文を提示する
        ※ TASK 18 は「Exhibitions/Artists向け比較CLI + guard最小版の実装」にする
    - 整理結果（Exhibitions/Artists向け共通ガード項目）：
      - G1 必須キー存在チェック：`run_summary_seed10_2025.json` の必須キー（`target_year / records_saved_total / existing_records_total / new_records_saved_total / records_total_after_run / records_saved_by_fair / failed_fetches_new_in_run / failed_fetches_total_ledger / visited_pages_total_ledger / skipped_total / skipped_by_reason / output_files / failed_fetches_path / visited_pages_path`）を検査する。
      - G2 内部整合チェック：`records_total_after_run == existing_records_total + new_records_saved_total`、`records_saved_total == new_records_saved_total`、`sum(records_saved_by_fair) == new_records_saved_total`、`skipped_total == sum(skipped_by_reason)` を検査する。
      - G3 summary と ledger/manifest の整合チェック：`run_summary` が指す `visited_pages_path / failed_fetches_path / output_files` の実在確認、`visited_pages_total_ledger == len(visited_pages)`、`failed_fetches_total_ledger == len(failed_fetches)` を検査する。manifest は任意入力（存在すれば最低キーのみ検査）として扱う。
      - G4 失敗しても前進する運用を壊さないチェック：`failed_fetches` 件数が非0でも、それ自体では失敗判定しない。失敗は schema整合（最低フィールド）と件数整合のみ確認し、運用方針（ログ化して前進）を維持する。
    - TASK18で実装する比較CLIの最小範囲（決定）：
      - CLI名：`run_compare_phase1_guard.py`（新規）
      - 入力：`run_summary_seed10_2025.json`、`visited_pages_seed10_2025.json`、`failed_fetches_seed10_2025.json`、`raw/exhibitions_frieze_london_2025.jsonl`、`raw/exhibitions_liste_2025.jsonl`、（任意）`artifact_manifest.json`
      - 比較/検査：G1〜G4 + `target_year` 整合 + ledgerキー（dictキーと `page_url_hash`/`fail_hash` の一致）を実装する。
      - 非0終了ガード（最小）：必須入力欠落、必須キー欠落、内部整合不一致、summary↔ledger件数不一致のいずれかで非0終了。`--fail-on-mismatch` 指定時のみ厳格失敗、それ以外はsummary出力を優先する。
    - 実行メモ：文面整理タスクとして `01/02/run_phase1_seed10.py` を確認し、実装はTASK18へ分離した。
    - 動作確認コマンド：
      - （今回は文面整理のみのため実行コマンド不要）

[x] 18) Exhibitions/Artists向け比較CLI + guard最小版を実装する
    - 目的：TASK17で確定した共通ガード項目（G1〜G4）をCLI化し、Phase1本体データの整合確認を再実行可能にする
    - 制約：取得ループには入れずPost-fetch検証CLIとして分離、failed_fetchesを「存在しただけで失敗」扱いにしない
    - 成立条件：
      - `python run_compare_phase1_guard.py --target-year 2025` が実行できる
      - 必須キー/内部整合/summary↔ledger整合/失敗前進運用チェックの結果を summary JSON に保存できる
      - `--fail-on-mismatch` で非0終了ガードが機能する
      - 03のCHANGELOGに反映される
    - 実行メモ：`python run_compare_phase1_guard.py --target-year 2025` 実行で `guard_passed=true` / `mismatches=0` を確認し、`data/phase1_seed10/logs/phase1_guard_summary_2025_20260223T132951Z.json` を保存。
    - 実行メモ：`python run_compare_phase1_guard.py --target-year 2025 --fail-on-mismatch` 実行でも差分なしのため exit 0 を確認（`phase1_guard_summary_2025_20260223T132959Z.json`）。
    - 実行メモ：不一致確認として `python run_compare_phase1_guard.py --target-year 2024 --fail-on-mismatch` を実行し、`guard_passed=false` / `mismatches=7` / exit 2 を確認（`phase1_guard_summary_2024_20260223T133211Z.json`）。

[x] 19) Phase1 guardの回帰比較CLIを追加する（前回runとの比較）
    - 目的：TASK18の単発整合チェックに加え、前回runと比較して悪化（回帰）を検知できるようにする
    - 制約：取得ループには組み込まず、Post-fetchの検証CLIとして分離する
    - 成立条件：
      - `python run_compare_phase1_guard_history.py --current-summary \"...\" --baseline-summary \"...\"` が実行できる
      - `records_saved_total / skipped_total / failed_fetches_total_ledger / visited_pages_total_ledger / mismatch_fields` の差分を summary JSON に保存できる
      - `--fail-on-regression` 指定時のみ回帰で非0終了、差分なしは0終了
      - 03のCHANGELOGに反映される
    - 実行メモ：`run_compare_phase1_guard_history.py` を追加し、比較前提一致チェック（`target_year` / 生成元CLI / 任意 `guard_schema_version`）を実装。`comparison_compatible` と `compatibility_errors` を summary 保存。
    - 実行メモ：差分（`records_saved_total / skipped_total / failed_fetches_total_ledger / visited_pages_total_ledger / mismatches / mismatch_fields(added/removed/common)`）と回帰（`guard_passed true→false` / `mismatches増加` / `new_mismatch_fields`）を分離して判定する実装を確認。
    - 実行メモ：正常系 `--fail-on-regression` で exit 0（`phase1_guard_history_compare_20260223T134004Z.json`）、回帰系（fixture）で exit 2（`...134020Z.json`）、比較不成立（target_year不一致）で exit 3（`...134028Z.json`）を確認。

[x] 20) Phase1 guard比較の運用化（baseline自動解決 + CI向け終了コード整理）
    - 目的：TASK19の比較CLIを日常運用に乗せるため、baseline指定の手間と誤指定を減らす
    - 制約：取得ループには組み込まず、Post-fetch検証CLIとして分離する
    - 成立条件：
      - baseline未指定時に「最新の比較可能summary」を自動選択できる
      - `--strict-compatibility`（比較不成立を常に非0）を追加できる
      - CI向けに exit code の意味を README/summary に明記できる（0=pass,2=regression,3=incompatible）
      - 03のCHANGELOGに反映される
    - 実行メモ：`run_compare_phase1_guard_history.py` に baseline自動解決を実装。`--baseline-summary` 未指定時は current除外・`target_year`一致・生成元CLI一致を満たす候補から、過去summary優先で最新を選択し、`guard_passed=true` / schema一致を優先する。
    - 実行メモ：`--strict-compatibility` を追加し、比較不成立を exit 3 で明示化。`--fail-on-regression` は既存どおり回帰時 exit 2（比較不成立も非0）を維持。
    - 実行メモ：summaryに `baseline_resolution_mode / baseline_candidates_checked / baseline_selected_reason / strict_compatibility / exit_code_meaning` を追加し、CI向け終了コード（0/2/3）の意味を保存。
    - 実行メモ：正常系（auto baseline）exit 0、回帰系（fixture）exit 2、比較不成立（strict）exit 3 を確認。

[x] 21) Phase1 guardをseed10以外へ拡張する準備（入力パス/年/カテゴリの汎化点整理）
    - 目的：seed10固定の比較運用から脱却し、対象年・入力パス・カテゴリ追加に耐える設計へ事前整理する
    - 制約：このタスクでは実装を急がず、汎化ポイントの明文化を優先する（既存挙動は壊さない）
    - 成立条件：
      - `run_compare_phase1_guard.py / run_compare_phase1_guard_history.py` のseed10固定箇所を棚卸しできる
      - 受け入れる入力（year / summary path / logs dir / category）の最小CLI仕様案を決められる
      - 互換維持方針（既定値は現行seed10）を明文化できる
      - 03のCHANGELOGに反映される
    - 棚卸し結果（seed10固定箇所）：
      - A) ファイル名固定：
        - `run_compare_phase1_guard.py` が `run_summary_seed10_{target_year}.json` を既定参照（`DEFAULT_SUMMARY_TEMPLATE`）。
        - `run_phase1_seed10.py` が `visited_pages_seed10_{TARGET_YEAR}.json` / `failed_fetches_seed10_{TARGET_YEAR}.json` / `run_summary_seed10_{TARGET_YEAR}.json` を生成。
        - history側は `phase1_guard_summary_*.json` / `phase1_guard_history_compare_*.json` 命名に依存（候補探索・出力）。
      - B) ディレクトリ固定：
        - `run_compare_phase1_guard.py` / `run_compare_phase1_guard_history.py` とも `LOG_DIR = data/phase1_seed10/logs` 固定。
        - 入出力既定が seed10 logs に寄っており、非seed10 runでは引数指定が必須。
      - C) target_year固定：
        - `run_phase1_seed10.py` は `TARGET_YEAR = 2025` 固定。
        - guard系CLIは `--target-year`（本体）と summary内 `target_year`（history）で扱っており、年比較ロジック自体は共通化可能。
      - D) カテゴリ固定（Exhibitions/Artists拡張余地）：
        - G1〜G4はカテゴリ非依存の共通チェック（必須キー/内部整合/summary↔ledger/failed前進運用）として維持可能。
        - ただし `output_files` の実体は現状 Exhibitions raw 前提。Artists を含める場合は「カテゴリ別必須ファイル集合」を引数/設定で受ける必要がある。
      - E) baseline探索固定：
        - history CLI の auto探索は `phase1_guard_summary_*.json` と `target_year` / 生成元CLI一致で候補を選別。
        - `--baseline-search-dir` は導入済みで seed10以外へ拡張可能だが、候補命名は phase1_guard_summary 依存。
    - 汎化方針（互換維持）：
      - 既定値は現行seed10挙動を維持（引数未指定で現状どおり動作）。
      - 新引数は追加のみ（既存引数/summary項目は破壊しない）。
      - summaryは後方互換を保ち、項目追加で拡張する。
      - 取得ループには組み込まず、Post-fetch検証CLIとして分離を維持する。
    - 最小CLI仕様案（TASK22実装対象）：
      - `run_compare_phase1_guard.py`：
        - 既存：`--target-year` / `--summary-path` / `--fail-on-mismatch`
        - 追加案：`--logs-dir`（既定：`data/phase1_seed10/logs`）、`--category`（既定：`exhibitions_text`、現時点はメタ保存中心）
      - `run_compare_phase1_guard_history.py`：
        - 既存：`--current-summary` / `--baseline-summary` / `--baseline-search-dir` / `--strict-compatibility` / `--fail-on-regression`
        - 追加案（必要なら）：`--summary-glob`（既定 `phase1_guard_summary_*.json`、命名拡張時の保険）
    - TASK22の実装優先順（最小）：
      - 先行：`run_compare_phase1_guard.py` のパス/年汎化（`--logs-dir` + 既定テンプレートの動的解決）を先に実装。
      - 後続：history CLI は既存 `--baseline-search-dir` を活かし、必要最小限（glob可変化の要否確認）のみ実装。
      - カテゴリは同時に厳格判定へ入れず、まずは summary メタに `category` を保存して互換維持で進める。

[x] 22) Phase1 guard本体のパス/年汎化を実装する（seed10互換維持）
    - 目的：`run_compare_phase1_guard.py` の seed10 固定依存を最小差分で外し、logs-dir/target-year 指定で再利用可能にする
    - 制約：既定値は現行seed10挙動を維持し、既存コマンドの互換を壊さない
    - 成立条件：
      - `--logs-dir` を追加し、summary/ledger入出力の既定解決を切り替えられる
      - 未指定時は現行どおり `data/phase1_seed10/logs` を使う
      - summaryに `category`（既定 `exhibitions_text`）と `logs_dir` を追加保存できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `python run_compare_phase1_guard.py --target-year 2025` で `guard_passed=true` / exit 0 を確認（`phase1_guard_summary_2025_20260224T010743Z.json`）。
      - `python run_compare_phase1_guard.py --target-year 2025 --logs-dir "data/phase1_seed10/logs"` で `guard_passed=true` / exit 0 を確認（`phase1_guard_summary_2025_20260224T010751Z.json`）。
      - `python run_compare_phase1_guard.py --target-year 2025 --logs-dir "data/phase1_seed10/logs" --fail-on-mismatch` で差分なし exit 0 を確認（`phase1_guard_summary_2025_20260224T010758Z.json`）。

[x] 23) Phase1 guard history比較のパス/探索汎化を実装する（seed10互換維持）
    - 目的：`run_compare_phase1_guard_history.py` の baseline探索を seed10 固定前提から外し、current summary 起点で他runにも使えるようにする
    - 制約：既定値は現行互換を維持し、`--fail-on-regression` / `--strict-compatibility` の終了コード規約（0/2/3）を壊さない
    - 成立条件：
      - `--baseline-search-dir` 未指定時に `--current-summary` の親ディレクトリを既定探索先として使える
      - 候補探索のglobをCLIから指定できる（例：`--summary-glob`、既定は現行互換）
      - summary に `baseline_auto_search_dir` / `baseline_candidates_checked` / `baseline_resolution_mode` が保存される
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - auto baseline: `python run_compare_phase1_guard_history.py --current-summary data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T010758Z.json --output-path data/phase1_seed10/logs/phase1_guard_history_compare_task23_auto.json` で exit 0。`baseline_auto_search_dir` / `summary_glob_effective` / `baseline_candidates_checked` を確認。
      - regression: `--fail-on-regression` 付き（fixture利用）で exit 2（`phase1_guard_history_compare_task23_regression.json`）。
      - incompatible: `--strict-compatibility` 付き（target_year不一致）で exit 3（`phase1_guard_history_compare_task23_incompatible.json`）。
      - manual優先: `--baseline-summary` 明示時は `--baseline-search-dir` / `--summary-glob` を探索に使わず、`baseline_resolution_mode=manual` / `baseline_selected_reason=manual_baseline_argument:auto_search_skipped` を確認（`phase1_guard_history_compare_task23_manual.json`）。

[x] 24) Phase1 guard CLIの共通関数化（path解決/summary保存）を最小実装する
    - 目的：`run_compare_phase1_guard.py` と `run_compare_phase1_guard_history.py` の重複処理（パス解決・summary書き出し・終了コード説明）を共通化し、保守性を上げる
    - 制約：挙動変更を最小化し、既存CLIオプションと終了コード規約（0/2/3）を壊さない
    - 成立条件：
      - 共通ユーティリティ（例: `phase1_guard_common.py`）へ最小切り出しができる
      - 両CLIの既存コマンドが従来どおり成功する
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `phase1_guard_common.py` を追加し、`resolve_logs_dir` / `paths_equal` / `write_summary_json` / `utc_now_iso` / `utc_timestamp_compact` / `EXIT_CODE_MEANING` を共通化。
      - `run_compare_phase1_guard.py` は path解決・summary保存・時刻生成のみ共通関数へ差し替え（判定ロジックは維持）。
      - `run_compare_phase1_guard_history.py` は path比較・path解決・summary保存・終了コード説明の参照を共通化（regression/compatibility判定ロジックは維持）。
      - 動作確認：guard本体 2コマンドは exit 0、history比較は auto=0 / regression=2 / incompatible=3 を確認。

[x] 25) Phase1 guard系CLIの共通fixture/テストデータ整理（回帰/非互換の再現性向上）
    - 目的：機能追加より安全性を優先し、guard本体/history比較の回帰ケース・非互換ケースを毎回同じ入力で再現できるようにする
    - 制約：CLIロジック本体は変更しない（テストデータと実行手順の整備のみ）
    - 成立条件：
      - 最低限3ケース（pass/regression/incompatible）のfixtureセットを整理できる
      - 実行コマンドと期待exit code（0/2/3）を明文化できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `tests/fixtures/phase1_guard/{pass,regression,incompatible}` を追加し、各ケースの `current_*.json / baseline_*.json` を固定配置。
      - `tests/fixtures/phase1_guard/fixture_manifest.json` に case定義（description/current/baseline/expected_exit_code/recommended_command）を記載。
      - `tests/fixtures/phase1_guard/README.md` と `run_guard_fixture_matrix.sh` を追加し、再現手順を固定化。
      - 動作確認：pass（exit 0）/ regression（exit 2）/ incompatible（exit 3）を固定fixtureで確認。CLIロジック本体は未変更。

[x] 26) Phase1 guard本体のsummary/ledger見張り項目を最小強化する（安全側）
    - 目的：カテゴリ分岐追加より先に、既存guard本体の整合チェックを1段だけ強化して回帰検知の抜け漏れを減らす
    - 制約：`run_compare_phase1_guard.py` の既存判定を壊さず、追加チェックは最小（項目追加のみ）に限定する
    - 成立条件：
      - summary/ledgerキー整合の追加見張り項目を2〜3個実装できる
      - `--fail-on-mismatch` の終了コード挙動（不一致時のみ exit 2）を維持できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加見張り項目を実装：`GX_SKIP_BREAKDOWN_SUM_MATCH`、`GX_FAILED_REASON_COUNTS_SUM_MATCH`、`GX_RECORDS_RELATIONS_MATCH`。
      - 後方互換方針：キー不足は mismatch にせず `missing_keys` / `skipped_checks` へ記録（`skipped_backward_compatible`）。
      - summary拡張：`additional_guard_checks` / `additional_guard_check_results` / `missing_keys` / `skipped_checks` を保存。
      - 動作確認：2025 pass は exit 0、`skip内訳` を崩したコピーsummaryで `--fail-on-mismatch` exit 2 を確認。
      - 既存判定ロジック（internal_consistency / summary_vs_ledger / manifest / failed schema）は変更せず維持。

[x] 27) Phase1 guard history比較の追加見張り項目差分を見える化する（安全側）
    - 目的：TASK26で増えた追加見張り項目を history比較 summary で読み取りやすくし、回帰理由の把握時間を短縮する
    - 制約：historyの回帰判定ロジックは変更しない（表示/summary項目追加のみ）
    - 成立条件：
      - `additional_guard_check_results` の差分（pass→fail / fail→pass / skipped）を summary に保存できる
      - `--fail-on-regression` / `--strict-compatibility` の終了コード規約（0/2/3）を維持できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - history summary に `additional_guard_checks_diff` / `additional_guard_checks_changed_fields` / `additional_guard_check_transitions` を追加。
      - 後方互換の可視化として `additional_guard_checks_comparison_mode` / `additional_guard_checks_missing_in` を追加（old summaryに項目が無くても比較継続）。
      - 動作確認：pass=exit 0（both_present, changedなし）、regression=exit 2（`GX_SKIP_BREAKDOWN_SUM_MATCH` が changed_to_fail）、incompatible=exit 3（current_only）。後方互換ケース（old baseline）でも比較不成立にせず exit 0 を確認。
      - 既存の回帰判定ロジック/終了コード規約（0/2/3）は変更なし。

[x] 28) guard本体/history比較のsummary schemaを軽く文書化して運用読み方を固定化する
    - 目的：CLI出力JSONの主要キーと読み方を文書化し、CI/運用での解釈ずれを防ぐ
    - 制約：CLIロジックは変更しない（README/docs追加のみ）
    - 成立条件：
      - guard本体summaryとhistory summaryの主要キー一覧を作成できる
      - exit code（0/2/3）と判定手順の読み方を明記できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` を追加し、guard本体/history比較の主要キー・読み方・exit code・fixture再現手順を文書化。
      - TASK26/27で追加した `additional_guard_check_results` と `additional_guard_checks_diff` 系の読み方を明記。
      - 後方互換（old summaryで追加項目欠落時）の扱いを明記（比較不成立にしない）。
      - CLIロジック本体は未変更。

[x] 29) guard fixture matrix 実行を1コマンド化して手元/CIの入口を揃える（安全側）
    - 目的：既存fixture実行を1コマンドで回せるようにし、運用ミスを減らす（CLI本体は触らない）
    - 制約：新規ラッパー/ドキュメント追加のみで、guard CLIロジックは変更しない
    - 成立条件：
      - pass/regression/incompatible を一括実行する入口コマンドを固定化できる
      - 期待exit code（0/2/3）と失敗時の停止条件を明確化できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `run_phase1_guard_fixture_matrix.py` を追加し、`fixture_manifest.json` 駆動で pass/regression/incompatible を一括実行可能化。
      - matrix summary を `data/phase1_seed10/logs/phase1_guard_fixture_matrix_*.json` に保存（`all_cases_passed` / `cases[].expected_exit_code` / `cases[].actual_exit_code` を保持）。
      - 終了コードを分離：内側CLIは期待値として `0/2/3`、ラッパー自身は `0=matrix pass / 1=matrix fail`。
      - 動作確認：通常実行で exit 0、`--fail-fast` + テスト用manifest（/tmp）で最初の不一致停止と exit 1 を確認（fixture本体は未改変）。
      - guard CLI本体ロジックは未変更。

[x] 30) guard schema version の安定付与/文書化を整えて互換判定を固定化する（安全側）
    - 目的：summary schema の将来拡張時に history比較の互換判定がぶれないよう、`guard_schema_version` の運用ルールを固定化する
    - 制約：まずは運用整理を優先し、CLI本体ロジック変更は最小に留める
    - 成立条件：
      - guard本体/history比較の schema version の扱い（必須/任意/未設定互換）を明文化できる
      - 既存fixtureと実行結果に照らして、互換判定ルールの確認手順を固定化できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `guard_schema_version` を共通定数化（`phase1_guard_common.py`）し、guard本体summaryへの安定付与を維持。
      - history summary に `current_guard_schema_version` / `baseline_guard_schema_version` / `guard_schema_version_comparison_mode` / `guard_schema_version_compatible` / `guard_schema_version_policy` を追加。
      - 互換判定ルールを固定：
        - both_present一致: 互換OK
        - both_present不一致: schema互換NG（compatibility_errorsへ記録）
        - current_only/baseline_only/both_missing: 後方互換モード（warningのみ、比較継続）
      - strict/non-strict:
        - non-strict: 不一致でもsummary保存して比較結果を出力（exitはフラグ条件依存）
        - strict: schema不一致は incompatible（exit 3）
      - 動作確認：
        - fixture matrix: exit 0（既存0/2/3運用を維持）
        - pass/regression/incompatible: exit 0/2/3
        - `/tmp` 一時コピーで schema mismatch を作成し、non-strict exit 0、strict exit 3 を確認（fixture本体は未改変）。
      - 既存回帰判定ロジック（mismatch/additional checks）と終了コード規約（0/2/3）は維持。

[x] 31) `--category` の最小実体化：カテゴリ別必須ファイル集合の入口を追加する（安全側）
    - 目的：`run_compare_phase1_guard.py` の category メタを最小限実体化し、将来のExhibitions/Artists拡張に備える
    - 制約：判定ロジックの大改造は避け、まずは「必須ファイル集合の切替入口」だけを追加する
    - 成立条件：
      - categoryごとの必須入力集合（最小）を定義し、未指定時は現行互換を維持できる
      - 既存 seed10 コマンドの結果を壊さない（exit/summary互換）
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `phase1_guard_common.py` にカテゴリプロファイル定義を追加（`exhibitions_text`=active、`artists_text`=reserved_minimal）。
      - `run_compare_phase1_guard.py` にカテゴリ入口を追加し、必須入力集合と必須summaryキー集合をプロファイルで切替。
      - 既定互換を維持（`--category` 未指定は `exhibitions_text`）。
      - summary追加キー：
        - `category_required_files_profile`
        - `required_input_files_effective`
        - `category_support_mode`
        - `category_warnings`
      - 追加メタは `check_results.category_profile` にも保存し、未対応カテゴリは fallback warning で継続。
      - 動作確認：
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text --fail-on-mismatch` → exit 0
        - 参考確認（任意）：`artists_text` でも reserved_minimal warning 付きで実行継続（exit 0）。
      - 既存判定ロジック（G1〜G4 + TASK26追加見張り）と終了コード規約（0/2/3）は維持。

[x] 32) history比較に category 文脈を追加し、カテゴリ互換情報をsummary化する（安全側）
    - 目的：`run_compare_phase1_guard_history.py` に current/baseline の category 情報を載せ、比較時の文脈ずれを可視化する
    - 制約：回帰判定ロジックは変更せず、表示/summary項目追加を中心に最小差分で進める
    - 成立条件：
      - history summary に category 比較情報（current/baseline/effective/compatibility）を保存できる
      - strict/non-strict での扱いを既存互換の範囲で明記できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - history summary に category 比較キーを追加：
        - `current_category`
        - `baseline_category`
        - `category_comparison_mode`
        - `category_effective_for_comparison`
        - `category_compatible`
        - `category_compatibility_policy`
        - `category_warnings`
      - category互換ルールを実装（可視化優先）：
        - both_present一致: 互換OK
        - both_present不一致: `category_compatible=false`
        - current_only/baseline_only/both_missing: 後方互換（warningで比較継続）
      - strict/non-strict：
        - non-strict: category不一致は warning-only（比較継続）
        - strict: category不一致を `compatibility_errors` に昇格し incompatibility（exit 3）
      - 動作確認：
        - 通常比較（同カテゴリ）: exit 0
        - regression fixture + `--fail-on-regression`: exit 2
        - incompatible fixture + `--strict-compatibility`: exit 3
        - 後方互換（baselineのcategory欠落を/tmpコピーで再現）: non-strict/strict とも比較継続（exit 0）、`category_comparison_mode=current_only` と warning を確認
      - 既存回帰判定ロジックと終了コード規約（0/2/3）は維持。

[x] 33) category mismatch の固定再現fixtureを追加し、history比較の運用再現性を固める（安全側）
    - 目的：TASK32で追加した category 互換可視化を、fixtureで毎回同じ入力で再現できるようにする
    - 制約：history回帰判定ロジックは変更しない。fixture/manifest/README整備を中心に最小差分で進める
    - 成立条件：
      - category mismatch ケースを fixture manifest に追加し、期待結果（non-strict=0 / strict=3）を固定化できる
      - matrixまたは同等の1コマンドで再現確認できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - fixture追加：`tests/fixtures/phase1_guard/category_mismatch/{current_category_mismatch_2025.json,baseline_category_mismatch_2025.json}`（category以外の互換条件は一致させ、category mismatch単独原因で再現）。
      - manifest追加：`category_mismatch_non_strict`（expected 0）/ `category_mismatch_strict`（expected 3）を2ケース登録（方式：manifest分離で strict/non-strict を固定）。
      - README更新：category mismatch の目的、non-strict/strict の期待exit code、確認キー（`current_category`/`baseline_category`/`category_comparison_mode`/`category_effective_for_comparison`/`category_compatible`/`category_warnings`）を追記。
      - 動作確認：
        - non-strict: exit 0（`comparison_compatible=true`, `category_compatible=false`, `category_comparison_mode=both_present`）
        - strict: exit 3（`compatibility_errors` に `category_mismatch:*` を確認）
        - matrix: `python run_phase1_guard_fixture_matrix.py` で 5ケース pass（wrapper exit 0）

[x] 34) artists_text の最小guard運用を reserved_minimal から一段進める（必須集合の具体化）
    - 目的：`--category artists_text` を実運用に近づけるため、最小の必須入力集合と必須summaryキーを具体化し、将来のExhibitions/Artists横展開の準備を進める
    - 制約：既存の `exhibitions_text` 既定挙動・終了コード規約を壊さない（後方互換優先）
    - 成立条件：
      - artists_text 向けの最小必須ファイル集合と必須summaryキー集合が明文化/実装される
      - category profile の support mode が `reserved_minimal` から安全に更新される（または更新条件が明確化される）
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `phase1_guard_common.py` の category profile を具体化し、artists_text に activation条件（3項目）と reserved理由を定義。
      - `run_compare_phase1_guard.py` に以下を追加：
        - `required_summary_keys_effective`
        - `category_profile_version`（v1.1）
        - `category_support_mode_configured`
        - `category_activation_conditions`
        - `category_data_presence`（`artists_*_<year>.jsonl` 探索結果）
      - support_mode判断：
        - artistsデータ検出時のみ `provisional_minimal` へ昇格
        - 未検出時は `reserved_minimal` 維持 + warning（理由/activation条件）を明示
      - 動作確認：
        - default（exhibitions）: exit 0
        - `--category exhibitions_text`: exit 0（既定互換維持）
        - `--category artists_text`: exit 0（クラッシュなし、reserved理由をsummaryに保存）
        - `--category artists_text --fail-on-mismatch`: exit 0（差分なし）

[x] 35) artists_text 用の最小fixture（pass/欠落warning）を追加して再現性を固定する（安全側）
    - 目的：TASK34で追加した artists category profile 挙動（reserved/provisional判定・warning）を fixture で毎回同じ入力で再現できるようにする
    - 制約：guard本体/ history本体ロジックは変更しない。fixture/manifest/README/matrix整備のみで対応する
    - 成立条件：
      - artists_text の pass ケース（互換継続）と warning ケース（reserved維持）を fixture として固定化できる
      - matrix 1コマンド実行で期待exit codeと確認キーを検証できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加fixture（guard本体向け）：
        - `tests/fixtures/phase1_guard/category_profile/artists_reserved_warning/...`
        - `tests/fixtures/phase1_guard/category_profile/artists_provisional_pass/...`
      - 追加manifest：`tests/fixtures/phase1_guard/category_fixture_manifest.json`
        - `artists_reserved_warning`（expected exit=0）
        - `artists_provisional_pass`（expected exit=0）
        - `expected_summary_checks` で category profile キー検証を固定化
      - 追加1コマンド入口：`run_phase1_guard_category_fixture_matrix.py`
        - wrapper exit: `0=matrix pass / 1=matrix fail`
        - matrix summary: `phase1_guard_category_fixture_matrix_*.json`
        - case summary結果: `cases[].summary_checks_passed` / `cases[].summary_check_failures`
      - 動作確認：
        - reserved個別: exit 0（`category_support_mode=reserved_minimal`）
        - provisional個別: exit 0（`category_support_mode=provisional_minimal`）
        - category matrix: 2ケースとも expected一致で exit 0
        - 既存history matrix（`run_phase1_guard_fixture_matrix.py`）: 5ケース pass、exit 0（影響なし）

[x] 36) artists_text 用の history比較fixture（category同一/不一致）を追加し、history再現性を固定する
    - 目的：artists文脈でも history比較（compatible / incompatible）を固定再現し、Exhibitions→Artists横展開時の検証導線を揃える
    - 制約：history/guard 本体ロジックは変更しない（fixture/manifest/README/matrix整備のみ）
    - 成立条件：
      - artists同一カテゴリ比較（compatible）と artists↔exhibitions 比較（strict incompatible）の最低2ケースを固定化できる
      - matrix 1コマンドで expected exit と category互換キーを確認できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加fixture：`tests/fixtures/phase1_guard/artists_history/{current_artists_compatible_2025.json,baseline_artists_compatible_2025.json,baseline_exhibitions_2025.json}`。
      - `tests/fixtures/phase1_guard/fixture_manifest.json` に3ケース追加：
        - `artists_history_compatible`（expected 0）
        - `artists_vs_exhibitions_category_mismatch_non_strict`（expected 0）
        - `artists_vs_exhibitions_category_mismatch_strict`（expected 3）
      - `run_phase1_guard_fixture_matrix.py` を最小拡張し、`expected_summary_checks` を機械検証（`summary_checks_passed` / `summary_check_failures` を matrix summary に保存）。
      - `tests/fixtures/phase1_guard/README.md` と `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に artists history fixture の確認手順・確認キーを追記。
      - 動作確認：
        - compatible（artists↔artists, non-strict）: exit 0
        - mismatch（artists↔exhibitions, strict）: exit 3
        - mismatch（artists↔exhibitions, non-strict）: exit 0
        - history matrix: `python run_phase1_guard_fixture_matrix.py` で 8ケース pass、wrapper exit 0
        - 既存 category profile matrix: `python run_phase1_guard_category_fixture_matrix.py` で 2ケース pass、wrapper exit 0（既存影響なし）

[x] 37) category profile（必須集合/activation条件）の設定ファイル化準備を行い、コード直書きを減らす（土台整備）
    - 目的：`phase1_guard_common.py` の category profile 直書きを外部設定へ寄せるための最小土台を作り、Exhibitions/Artists拡張時の保守性を上げる
    - 制約：guard/history判定ロジックは変更せず、挙動互換（既定 `exhibitions_text`）を維持する
    - 成立条件：
      - category profile を外部JSON（または同等）で読み込む入口を追加できる
      - 設定未指定/壊れた設定時の安全フォールバック（現行内蔵profile）がある
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加設定ファイル：`config/phase1_guard_category_profiles.json`（`exhibitions_text` / `artists_text` を現行内蔵profileと同値で定義）。
      - `phase1_guard_common.py` に外部設定読み込み入口を追加：
        - `DEFAULT_CATEGORY_PROFILE_CONFIG_PATH`
        - `DEFAULT_CATEGORY_PROFILES`（内蔵fallback）
        - `load_category_profiles(...)`
        - `get_effective_category_profiles(...)`
      - fallback方針：config不在/JSON壊れ/スキーマ不正は `builtin_fallback` で継続（例外で落とさない）。
      - `run_compare_phase1_guard.py` に `--category-profile-config` を追加し、summaryへ以下メタを追加：
        - `category_profile_source`
        - `category_profile_config_path`
        - `category_profile_config_loaded`
        - `category_profile_config_error`
        - `category_profile_config_version_effective`
      - fallback検証：
        - missing path（`/tmp/phase1_guard_missing_config.json`）で `category_profile_source=builtin_fallback` を確認
        - broken JSON（`/tmp/phase1_guard_bad_config.json`）で `category_profile_config_error=config_json_decode_error:*` を確認
        - schema不正（`/tmp/phase1_guard_bad_schema_config.json`）で `category_profile_config_error=config_schema_error:*` を確認
      - 動作確認：
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（external_config）
        - `python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category artists_text` → exit 0
        - `python run_phase1_guard_fixture_matrix.py` → wrapper exit 0（8ケース）
        - `python run_phase1_guard_category_fixture_matrix.py` → wrapper exit 0（2ケース）

[x] 38) category profile 設定ファイルのスキーマ検証を最小追加し、設定ミス検知を安定化する（安全側）
    - 目的：外部設定導入後の運用事故を減らすため、configの型/必須キー不足を summary warning として可視化し、fallback理由を一貫化する
    - 制約：guard/history 判定ロジック・終了コード規約は変更しない（設定検証はロード段だけ）
    - 成立条件：
      - profile config の最小スキーマ検証が関数化される
      - 検証失敗時の error code 体系（config_schema_error:*）が統一される
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `phase1_guard_common.py` に `validate_category_profiles_config(config_obj)` を追加し、最小スキーマを検証：
        - root dict
        - `categories` dict
        - 必須カテゴリ（`exhibitions_text` / `artists_text`）
        - category profile dict
        - 最低限キーと型（`required_input_files`, `support_mode`系, required_summary_keys系, `activation_conditions`, `reserved_reason`）
      - error codeを統一：
        - `config_missing:*`
        - `config_json_decode_error:*`
        - `config_schema_error:*`
      - `run_compare_phase1_guard.py` は判定ロジック不変で、設定エラー詳細メタのみ追加：
        - `category_profile_config_error_detail`
      - fallback確認：
        - missing: `config_missing:file_not_found`
        - bad json: `config_json_decode_error:invalid_json`
        - bad schema（missing key）: `config_schema_error:missing_category:artists_text`
        - bad schema（type error）: `config_schema_error:type_error:exhibitions_text.required_input_files`
      - 動作確認：
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_missing_config.json` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_bad_config.json` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_bad_schema_missing.json` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_bad_schema_type.json` → exit 0
        - `python run_phase1_guard_fixture_matrix.py` → wrapper exit 0（8ケース）
        - `python run_phase1_guard_category_fixture_matrix.py` → wrapper exit 0（2ケース）

[x] 39) history比較summaryにも category_profile_config 文脈を載せ、運用可視化を揃える（安全側）
    - 目的：current/baseline の guard summary がどの profile config ソースで生成されたかを history summary に写し、比較時の前提差を早く把握できるようにする
    - 制約：history回帰判定・互換判定ロジックは変更しない（可視化キー追加のみ）
    - 成立条件：
      - history summary に `current_category_profile_config_*` / `baseline_category_profile_config_*` 系キーが追加される
      - strict/non-strict の終了コード規約（0/2/3）は不変
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `run_compare_phase1_guard_history.py` に、history summary へ current/baseline の config 文脈を追加：
        - `current_category_profile_config_source/path/loaded/error/error_detail/version_effective`
        - `baseline_category_profile_config_source/path/loaded/error/error_detail/version_effective`
      - 可視化専用比較キーを追加（判定ロジックには未使用）：
        - `category_profile_config_comparison_mode`
        - `category_profile_config_same_source`
        - `category_profile_config_same_version`
        - `category_profile_config_effective_for_comparison`
        - `category_profile_config_warnings`
      - 後方互換：
        - 旧summaryで category_profile_config 系キー欠落でも比較は継続（warning-only）
        - strict/non-strict ともにこの文脈は終了コードに影響させない
      - 動作確認：
        - 通常比較（実summary）  
          `python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T063506Z.json" --baseline-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T063050Z.json"`  
          → exit 0、`category_profile_config_comparison_mode=both_present`
        - regression fixture  
          `python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/regression/current_regression_2025.json" --baseline-summary "tests/fixtures/phase1_guard/regression/baseline_regression_2025.json" --fail-on-regression`  
          → exit 2（維持）
        - incompatible fixture  
          `python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json" --baseline-summary "tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json" --strict-compatibility`  
          → exit 3（維持）
        - 後方互換（/tmp 一時コピーで baseline の config 文脈キーを削除）  
          `python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T063506Z.json" --baseline-summary "/tmp/phase1_guard_summary_2025_baseline_no_profile_ctx.json"`  
          → exit 0、`category_profile_config_comparison_mode=current_only` と warning を確認
        - matrix影響確認  
          `python run_phase1_guard_fixture_matrix.py` → wrapper exit 0（8ケース）

[x] 40) category profile config の簡易lint CLIを追加し、guard実行前に設定だけ検査できる入口を作る（安全側）
    - 目的：`config/phase1_guard_category_profiles.json` の編集ミスを guard実行前に検知し、fallback起動前に問題を早期把握できるようにする
    - 制約：guard/history 判定ロジックは変更しない（設定検査CLIの追加のみ）
    - 成立条件：
      - `python run_phase1_guard_category_profile_lint.py --config-path ...` が実行できる
      - exit code を明確化（0=lint pass / 1=lint fail）
      - 検査結果JSON（`config_path` / `config_exists` / `config_valid` / `config_error_code` / `config_error_detail` / `checked_at` / `source_cli`）を保存できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 新規CLI `run_phase1_guard_category_profile_lint.py` を追加（設定検査専用）
      - `phase1_guard_common.load_category_profiles(...)` を利用して、Task38の検証/エラーコード体系をそのまま再利用
      - lint summary（`data/phase1_seed10/logs/phase1_guard_category_profile_lint_*.json`）に以下を保存：
        - `config_path`
        - `config_exists`
        - `config_valid`
        - `config_error_code`
        - `config_error_detail`
        - `checked_at`
        - `source_cli`
      - exit code 規約：
        - `0 = lint_pass`
        - `1 = lint_fail`
      - 動作確認：
        - `python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"` → exit 0
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_missing_config.json"` → exit 1
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_config.json"` → exit 1
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_schema_config.json"` → exit 1

[x] 41) artists_text activation条件の監視キーを category fixture matrix に追加し、昇格判定の再現性を強化する（安全側）
    - 目的：`reserved_minimal` / `provisional_minimal` の切替条件（activation_conditions）を fixture summary チェックとして固定化し、運用確認を1コマンド化する
    - 制約：guard/history 判定ロジックは変更しない（fixture/manifest/matrixの検証項目追加のみ）
    - 成立条件：
      - category fixture matrix で activation系キー（`category_activation_conditions`, `category_data_presence`, `category_support_mode`）を機械検証できる
      - reserved/provisional 両ケースで expected summary checks が通る
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - `tests/fixtures/phase1_guard/category_fixture_manifest.json` を更新：
        - reserved/provisional 両ケースに `category_activation_conditions` 非空チェックを追加
        - 両ケースに `category_data_presence` 存在チェックを追加
        - logs_dir を `tests/fixtures/phase1_guard/category/...` に統一
      - fixture再現パスを追加：
        - `tests/fixtures/phase1_guard/category/artists_reserved_warning/{logs,raw}`
        - `tests/fixtures/phase1_guard/category/artists_provisional_pass/{logs,raw}`
      - README更新（category fixture の実行パス統一 + activation監視キーの確認ポイント追記）
      - schema文書更新（category fixture matrix で activation系チェックを読むポイント追記）
      - 動作確認：
        - `python run_phase1_guard_category_fixture_matrix.py` → wrapper exit 0（2ケース）
        - `python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir "tests/fixtures/phase1_guard/category/artists_reserved_warning/logs"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir "tests/fixtures/phase1_guard/category/artists_provisional_pass/logs"` → exit 0
      - matrix summary確認：
        - `cases[].summary_checks_passed=true`（reserved/provisional 両方）

[x] 42) category profile lint を fixture matrix に統合し、設定検証の再現性を1コマンド化する（安全側）
    - 目的：Task40で追加した lint CLI を matrix 化し、valid/missing/bad_json/bad_schema の期待結果（exit 0/1）を固定再現できるようにする
    - 制約：guard/history 判定ロジックは変更しない（lint実行ラッパー/manifest/READMEの整備のみ）
    - 成立条件：
      - lint fixture manifest（ケース定義）を追加できる
      - `python run_phase1_guard_lint_fixture_matrix.py`（例）が 1コマンドで全ケース実行できる
      - matrix summary に expected/actual exit と `config_error_code` チェック結果が保存される
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加ファイル：
        - `tests/fixtures/phase1_guard/lint_fixture_manifest.json`
        - `run_phase1_guard_lint_fixture_matrix.py`
        - `tests/fixtures/phase1_guard/lint/valid/phase1_guard_category_profiles_valid.json`
        - `tests/fixtures/phase1_guard/lint/bad_json/phase1_guard_bad_config.json`
        - `tests/fixtures/phase1_guard/lint/bad_schema/phase1_guard_bad_schema_config.json`
      - 4ケース固定再現：
        - valid（exit 0）
        - missing（exit 1, `config_missing:*`）
        - bad json（exit 1, `config_json_decode_error:*`）
        - bad schema（exit 1, `config_schema_error:*`）
      - matrix summary（`phase1_guard_lint_fixture_matrix_*.json`）に以下を保存：
        - `all_cases_passed`
        - `cases[].expected_exit_code`
        - `cases[].actual_exit_code`
        - `cases[].summary_checks_passed`
        - `cases[].summary_check_failures`
        - `cases[].output_summary_path`
      - ドキュメント更新：
        - `tests/fixtures/phase1_guard/README.md` に lint matrix 入口と lint fixture ケースを追記
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に lint fixture matrix summary 読み方を追記
      - 動作確認：
        - `python run_phase1_guard_lint_fixture_matrix.py` → wrapper exit 0（4ケース）
        - `python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"` → exit 0
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_missing_config.json"` → exit 1
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_config.json"` → exit 1
        - `python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_schema_config.json"` → exit 1
      - 既存matrix影響確認：
        - `python run_phase1_guard_category_fixture_matrix.py` → wrapper exit 0
        - `python run_phase1_guard_fixture_matrix.py` → wrapper exit 0

[x] 43) guard検証（history/category/lint）の統合matrix入口を追加し、手元/CIの実行導線を一本化する（安全側）
    - 目的：history/category/lint の3系統matrixを1コマンドで順次実行し、総合pass/failを返す統合ラッパーを作る
    - 制約：各CLI/各matrix本体の判定ロジックは変更しない（統合実行ラッパーのみ追加）
    - 成立条件：
      - `python run_phase1_guard_all_matrices.py`（例）で3系統を順次実行できる
      - 総合summaryに各matrixの exit / summary_path / pass_fail が保存される
      - wrapper exit code を `0=all_pass / 1=any_fail` で固定
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加ファイル：
        - `run_phase1_guard_all_matrices.py`
      - 主要実装：
        - 実行順 `lint -> category -> history` で各matrix wrapperを順次実行
        - 各wrapperへ `--output-path` を渡して summary_path を確定取得
        - 統合summary `phase1_guard_all_matrices_*.json` に `all_passed / wrapper_exit_code / execution_order / matrices[] / warnings` を保存
        - fail-fast無し（1件失敗でも残りを継続）で総合判定
      - ドキュメント更新：
        - `tests/fixtures/phase1_guard/README.md` に統合matrix入口を追記
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に統合matrix summaryキー（7.5）を追記
      - 動作確認：
        - `python run_phase1_guard_all_matrices.py` → exit 0
        - `python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json" --pretty` → exit 0
        - `python run_phase1_guard_lint_fixture_matrix.py` → exit 0
        - `python run_phase1_guard_category_fixture_matrix.py` → exit 0
        - `python run_phase1_guard_fixture_matrix.py` → exit 0

[x] 44) 統合matrix summaryの軽量レポートCLIを追加し、CIの失敗原因把握を高速化する（安全側）
    - 目的：`run_phase1_guard_all_matrices.py` の summary JSON から、失敗matrix名・exit code・summary_path を一目で読めるレポートを生成する
    - 制約：matrix本体/guard/history/lint 本体ロジックは変更しない（summary読取CLIのみ追加）
    - 成立条件：
      - `python run_phase1_guard_all_matrices_report.py --summary-path "<path>"` が実行できる
      - `--latest` で最新の `phase1_guard_all_matrices_*.json` を自動解決できる
      - レポートに `all_passed` / 失敗matrix一覧 / 各matrixの `actual_exit_code` / `summary_path` が出る
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加ファイル：
        - `run_phase1_guard_all_matrices_report.py`
      - 主要実装：
        - `--summary-path` / `--latest` の両経路で統合summaryを読取
        - 標準出力で `all_passed` / `wrapper_exit_code` / `execution_order` / `failed_matrices` / `child_summary_paths` を短く表示
        - 任意 `--output-json` で軽量レポートJSONを保存可能
        - report CLI exit code を `0=report_generated / 1=summary_not_found_or_invalid` で固定
      - ドキュメント更新：
        - `tests/fixtures/phase1_guard/README.md` に report CLI 入口を追記
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に report CLI（7.6）の読み方を追記
      - 動作確認：
        - `python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --latest` → exit 0

[x] 45) report CLIの固定再現fixtureを追加し、summary欠落/破損時の挙動を1コマンドで検証できるようにする（安全側）
    - 目的：`run_phase1_guard_all_matrices_report.py` の入出力を fixture 化し、valid/missing/bad_json の挙動を常に同じ条件で再現する
    - 制約：guard/history/lint/matrix本体ロジックは変更しない（report CLI向け fixture/matrix 追加のみ）
    - 成立条件：
      - report fixture manifest と 1コマンドmatrix wrapperを追加
      - valid（exit 0）/ missing（exit 1）/ bad_json（exit 1）を固定再現
      - matrix summaryに expected/actual exit と summary_checks 結果を保存
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加ファイル：
        - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
        - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
        - `tests/fixtures/phase1_guard/report/valid/phase1_guard_all_matrices_valid.json`
        - `tests/fixtures/phase1_guard/report/bad_json/phase1_guard_all_matrices_bad.json`
      - 主要実装：
        - report CLI向け3ケース（valid/missing/bad_json）を固定fixture化
        - 1コマンドmatrixで `expected_exit_code` と report出力の `expected_summary_checks` を機械判定
        - matrix summaryに `all_cases_passed` / `cases[].expected_exit_code` / `cases[].actual_exit_code` / `cases[].summary_checks_passed` / `cases[].summary_check_failures` / `cases[].report_output_path` を保存
      - ドキュメント更新：
        - `tests/fixtures/phase1_guard/README.md` に report fixture matrix 入口を追記
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に report fixture matrix summary（7.7）を追記
      - 動作確認：
        - `python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（3ケース）

[x] 46) report CLIに`--fail-on-failed-matrix`を追加し、統合summaryが失敗状態なら非0終了を選べるようにする（安全側）
    - 目的：report生成は成功していても `all_passed=false` のときCIを落としたい運用に対応する
    - 制約：guard/history/lint/各matrix本体ロジックは変更しない（report CLIの終了ポリシー追加のみ）
    - 成立条件：
      - `--fail-on-failed-matrix` 指定時のみ、`all_passed=false` で exit 1
      - 未指定時は従来どおり `0=report_generated` を維持
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 変更ファイル：
        - `run_phase1_guard_all_matrices_report.py`
        - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
        - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
        - `tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json`
      - 主要実装：
        - report CLI に `--fail-on-failed-matrix` を追加（既定挙動は後方互換）
        - 出力メタ `fail_on_failed_matrix` / `exit_policy` / `exit_reason` / `report_exit_code` を追加
        - fixture matrix に strict policy ケースを追加し、`all_passed=false` のフラグ有無差を固定再現
      - 動作確認：
        - `python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --latest --fail-on-failed-matrix` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json" --fail-on-failed-matrix` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "/tmp/not_found.json" --fail-on-failed-matrix` → exit 1
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json" --fail-on-failed-matrix` → exit 1
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（5ケース）

[x] 47) report CLIの終了ポリシー差（default/strict）をfixture matrixで明示出力し、CIログ読解を固定化する（安全側）
    - 目的：report fixture matrix の各ケースで「どの終了ポリシーで判定したか」をsummaryに固定保存し、CI読解をブレさせない
    - 制約：guard/history/lint/matrix本体ロジックは変更しない（report fixture matrixの可視化のみ）
    - 成立条件：
      - matrix summary の `cases[]` に `fail_on_failed_matrix` / `policy_expected` / `policy_actual`（相当）を保存
      - README と schema文書に policy別の見方を追記
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 変更ファイル：
        - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
        - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
        - `tests/fixtures/phase1_guard/README.md`
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
      - 主要実装：
        - report fixture matrix の `cases[]` に `policy_expected`（manifest由来）、`policy_actual`（report出力 `exit_policy` 由来）、`policy_match` を追加
        - `policy_expected` 未指定時は `fail_on_failed_matrix` から `default_report_only` / `fail_on_failed_matrix` を導出
        - manifestへ `policy_expected` を明示追加（valid/missing/bad_json/default/strict）
      - 動作確認：
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（5ケース）
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json"` → exit 0（`policy_actual=default_report_only`）
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json" --fail-on-failed-matrix` → exit 1（`policy_actual=fail_on_failed_matrix`）

[x] 48) report fixture matrixに`policy_match`ガードを追加し、終了ポリシー齟齬をwrapper失敗として検知できるようにする（安全側）
    - 目的：TASK47で可視化した `policy_expected` / `policy_actual` をそのまま判定に使い、ポリシー齟齬を機械的に fail 化する
    - 制約：report CLI本体の終了規約は変更しない（fixture matrix判定の追加のみ）
    - 成立条件：
      - `policy_actual` が取れるケースで `policy_match=false` を matrix fail 判定に含められる
      - missing/bad_json など `policy_actual=null` ケースは互換維持で warning 扱いにできる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 変更ファイル：
        - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
        - `tests/fixtures/phase1_guard/README.md`
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
      - 主要実装：
        - matrix判定に policy guard を追加（`policy_check_mode=enforce_when_available`）
        - `policy_actual` が取得できるケースで `policy_match=false` を fail 条件へ反映
        - `policy_actual` 未取得（missing/bad_json）は `policy_guard_reason=policy_actual_unavailable_warning_only` で後方互換継続
        - summaryに `policy_check_mode` / `policy_guard_applied` / `policy_guard_passed` / `policy_guard_reason` を保存
      - 動作確認：
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（5ケース）
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json"` → exit 0
        - `python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json" --fail-on-failed-matrix` → exit 1
        - 追加確認（/tmp一時manifestで strictケースの `policy_expected` を意図的に不一致化）：
          - `python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path /tmp/report_fixture_manifest_policy_mismatch.json` → exit 1

[x] 49) report fixture matrixにpolicy mismatch専用negative fixtureを追加し、policy_guardの失敗経路を固定再現する（安全側）
    - 目的：TASK48で追加した `policy_match` ガードの失敗経路を常設fixtureで再現し、CIでの見逃しを防ぐ
    - 制約：report CLI本体ロジックと終了規約は変更しない（fixture/manifest/matrix整備のみ）
    - 成立条件：
      - 通常manifest（green）とは別に policy mismatch 再現manifest（negative）を固定化できる
      - negative実行で wrapper exit 1 を期待値どおり確認できる
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 追加ファイル：
        - `tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json`
      - 変更ファイル：
        - `tests/fixtures/phase1_guard/README.md`
        - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
      - 主要実装：
        - green manifestとは分離した negative manifest を常設化
        - strictケースで `policy_expected` を意図的に不一致化し、`policy_match=false` の失敗経路を固定再現
      - 動作確認：
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（green）
        - `python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path "tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json"` → exit 1（negative）
        - negative summary（`...20260224T085257Z.json`）で `policy_match=false` / `policy_guard_passed=false` / `policy_guard_reason=policy_mismatch_enforced` を確認

[x] 50) Phase1本体へ復帰：`run_phase1_seed10.py` に artists_text の最小取得入口を追加し、Exhibitionsと並走できる状態にする（安全側）
    - 目的：検証層（TASK49）を締めたので、本体前進として artists_text の最小取得入口を seed10 実行へ追加する
    - 制約：取得ループ内LLM加工は禁止（Post-fetch分離を維持）、既存Exhibitions挙動/台帳/終了コード規約を壊さない
    - 成立条件：
      - `run_phase1_seed10.py` で artists_text の最小 raw 保存と summary反映が実行できる
      - 既存 `exhibitions_text` 実行結果（saved/skipped/failedログ）は後方互換を維持する
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 変更ファイル：
        - `run_phase1_seed10.py`
      - 主要実装：
        - `--include-artists-text` を追加（既定は exhibitions_text のみで後方互換維持）
        - artists_text 専用の raw出力・台帳を追加
          - `data/phase1_seed10/raw/artists_{fair}_{year}.jsonl`
          - `data/phase1_seed10/logs/visited_pages_artists_seed10_{year}.json`
          - `data/phase1_seed10/logs/failed_fetches_artists_seed10_{year}.json`
        - run summary に artists系メタ（saved/skipped/failed/path）を追加（既存キーの意味は維持）
      - 動作確認：
        - `python run_phase1_seed10.py` → exit 0（既存互換）
        - `python run_phase1_seed10.py --include-artists-text` → exit 0（並走）
        - `python run_phase1_seed10.py --include-artists-text`（再実行）→ exit 0（artists側も台帳スキップ確認）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（既存guard互換）

[x] 51) artists_text の入力ソースをCSV拡張で分離し、seed10取得率の改善余地を作る（本体前進・最小）
    - 目的：artists_text が exhibitions_url に依存しすぎる状態を避けるため、CSVに artists用URL（任意）を追加できる入口を作る
    - 制約：既存CSV（2列）との後方互換を維持し、未指定時は従来どおり exhibitions_url をフォールバック利用する
    - 成立条件：
      - `run_phase1_seed10.py` が CSV 3列目（artists_url 任意）を読める
      - `--include-artists-text` 実行時に artists_url 優先、未指定時は exhibitions_url fallback で動作
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 変更ファイル：
        - `run_phase1_seed10.py`
      - 主要実装：
        - `GallerySeed` に `artists_url`（任意）を追加し、CSV 3列目を読込（2列CSVは後方互換維持）
        - `resolve_artists_list_url(...)` を追加し、artists入口URLを `artists_url` 優先 / `exhibitions_url` fallback で解決
        - artists取得ループの list fetch/台帳更新を `artists_list_url` 基準へ切替
        - run summary に artists入口URL解決メタを追加：
          - `artists_list_source_counts`
          - `artists_list_source_counts_by_fair`
          - `artists_list_url_artists_url_used`
          - `artists_list_url_exhibitions_fallback_used`
      - 動作確認：
        - `python run_phase1_seed10.py` → exit 0（既存互換）
        - `python run_phase1_seed10.py --include-artists-text` → exit 0（並走）
        - `python run_phase1_seed10.py --include-artists-text`（再実行）→ exit 0（台帳スキップ）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（既存guard互換）
        - summary確認：
          - `artists_list_source_counts={'artists_url': 10}`
          - `artists_list_url_artists_url_used=10`
          - `artists_list_url_exhibitions_fallback_used=0`

[x] 52) artists_text のCSV入力（artists_url列）を実データ拡充し、seed10で new_saved 発生を確認する（本体前進）
    - 目的：TASK51で作った artists_url 優先導線を実データで活かし、seed10で artists_text の新規保存を実際に発生させる
    - 制約：既存Exhibitions挙動・2列CSV後方互換を壊さない、取得ループ内LLM加工は入れない
    - 成立条件：
      - gallery CSV の対象行で `artists_url` を補完できる（空欄許容）
      - `--include-artists-text` 実行で artists の `new_saved>0` を1件以上確認
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - seed10対象10行は既に `artists_url` 補完済み（CSV 3列目あり）
      - 実行結果（通信回復後・cooldown影響除外）：
        - `python run_phase1_seed10.py --include-artists-text` 1回目: artists `saved=81 failed_new=1 skipped=0`
        - `python run_phase1_seed10.py --include-artists-text` 2回目: artists `saved=0 failed_new=0 skipped=82`
      - summary確認：
        - `data/phase1_seed10/logs/run_summary_seed10_2025_task53_first_pass.json`
        - `artists_records_saved_total=81`（`new_saved>0` 達成）
        - `artists_list_url_artists_url_used=10`
        - `artists_list_url_exhibitions_fallback_used=0`

[x] 53) ブロッカー解消：外向き通信回復後に artists_text の `new_saved>0` を再検証し、TASK52を完了させる
    - 目的：TASK52未達要因（DNS/外向き通信不可）を解消した状態で、artists_text の `new_saved>0` を確認して本体前進を再開する
    - 制約：取得ループ内LLM加工なし、既存Exhibitions処理を壊さない、ドメイン専用ハードコードを増やさない
    - 成立条件：
      - 外向き通信確認（curl/socket）が通る
      - artists台帳のcooldown影響を除外した再実行ができる
      - run summary で `artists_records_saved_total > 0` を1回確認し、03のTASK52を [x] に更新できる
    - 実行メモ：
      - 通信確認（sandbox外実行）：
        - `curl -I https://example.com` → HTTP/2 200
        - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → 104.18.26.120
      - cooldown影響除外：
        - `failed_fetches_artists_seed10_2025.json` をバックアップ後に空dictへ初期化
      - guard互換：
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0

[x] 54) artists_text のPost-fetch Enrichment入口をseed10本体へ追加する（本体前進・最小）
    - 目的：TASK52/53で取得できた artists_text raw を、取得ループ外の事後バッチへ接続し、Phase2連携の土台を作る
    - 制約：取得ループ内LLM加工は追加しない、既存Exhibitions Enrichment挙動を壊さない
    - 実装メモ：
      - `run_phase1_seed10.py` に artists Post-fetch requests 生成を追加（取得ループ外）
      - 生成物：`data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl`（上書き生成）
      - run summary 追加キー：
        - `artists_enrichment_mode=post_fetch_requests_only`
        - `artists_enrichment_candidates_total=81`
        - `artists_enrichment_requests_created=81`
        - `artists_enrichment_requests_output_path`
        - `artists_enrichment_raw_records_total` / `artists_enrichment_raw_records_by_fair`
        - `artists_enrichment_counters` / `artists_enrichment_warnings`
      - 動作確認：
        - `python run_phase1_seed10.py` → exit 0（既存互換）
        - `python run_phase1_seed10.py --include-artists-text` → exit 0（artists+requests生成）
        - `python run_phase1_seed10.py --include-artists-text` → exit 0（再実行、requests上書きで冪等）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（guard互換）

[x] 55) artists_text のEnrichment apply バッチを追加し、requests から `headline_ja` 反映までを成立させる（本体前進）
    - 目的：TASK54の requests を使って、artists_text raw に `headline_ja`（必要なら `summary_ja`）を反映する
    - 制約：取得ループ内LLM加工なし（Post-fetch分離維持）、既存Exhibitions導線を壊さない
    - 実装メモ：
      - `run_enrichment_artists_seed10_apply.py` を追加（requests読込→artists raw更新→apply output/summary保存）
      - 生成物：
        - `data/phase1_seed10/derived/artists_enrichment_apply_output_2025_20260224T100342Z.jsonl`
        - `data/phase1_seed10/derived/artists_enrichment_apply_summary_2025_20260224T100342Z.json`
        - `data/phase1_seed10/derived/artists_enrichment_apply_output_2025_20260224T100355Z.jsonl`
        - `data/phase1_seed10/derived/artists_enrichment_apply_summary_2025_20260224T100355Z.json`
      - 動作確認：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0
        - `python run_enrichment_artists_seed10_apply.py` → exit 0（updated=81）
        - `python run_enrichment_artists_seed10_apply.py` → exit 0（updated=0, 冪等）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 補足：
        - 実行環境の外向き制約でOpenAI応答が取れない場合に備え、applyはフォールバック見出し生成で前進可能化（Post-fetch範囲内）

[x] 56) artists_text のEmbedding/Index入口を追加し、検索用生成物をseed10派生データとして保存する（本体前進）
    - 目的：headline_ja 反映済み artists raw を対象に、埋め込み入力と検索用 index/meta 生成を最小で成立させる
    - 制約：取得ループ内LLM加工は追加しない、既存Exhibitions/Tarutaniのベクトル処理を壊さない
    - 実装メモ：
      - `run_vectorize_artists_seed10.py` を追加（Post-fetch CLI）
      - 生成物：
        - `data/phase1_seed10/derived/vector/artists_text_index_2025.npy`
        - `data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl`
        - `data/phase1_seed10/derived/vector/artists_text_vectorize_failed_2025.jsonl`
        - `data/phase1_seed10/derived/vector/artists_text_vectorize_summary_2025.json`
        - `data/phase1_seed10/derived/vector/artists_text_artifact_manifest_2025.json`
      - 動作確認：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0
        - `python run_enrichment_artists_seed10_apply.py` → exit 0
        - `python run_vectorize_artists_seed10.py` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 実行結果：
        - `input_total=81`
        - `embedded_total=0`
        - `skipped_total=0`
        - `failed_total=81`（接続失敗）

[x] 57) ブロッカー解消：artists_text vectorize の外向き接続を回復し、`embedded_total>0` を再確認する（本体前進）
    - 目的：TASK56で成立した入口を使い、接続回復後に実埋め込みを生成して検索基盤を前進させる
    - 制約：取得ループ内LLM加工なし、既存Exhibitions/Tarutani処理を壊さない
    - 成立条件：
      - 外向き接続確認（curl/socket）が通る
      - `python run_vectorize_artists_seed10.py` で `embedded_total > 0` を確認
      - 03のCHANGELOGに反映される
    - 実行メモ：
      - 接続確認（sandbox外）:
        - `curl -I https://example.com` → HTTP/2 200
        - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → `104.18.27.120`
      - 実行結果：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0（artists: `saved=0 skipped=10`, cooldownスキップ）
        - `python run_enrichment_artists_seed10_apply.py` → exit 0（updated=0）
        - `python run_vectorize_artists_seed10.py` → exit 0（`input_total=81 embedded_total=81 skipped_total=0 failed_total=0`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（guard互換維持）
      - 生成物確認：
        - `data/phase1_seed10/derived/vector/artists_text_index_2025.npy`
        - `data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl`
        - `data/phase1_seed10/derived/vector/artists_text_vectorize_summary_2025.json`

[x] 58) artists_text の検索スモークCLIを追加し、vector生成物から top-k を確認する（本体前進）
    - 目的：TASK57で再生成した artists index/meta を使い、artists_text の最小検索入口を作って Phase2接続前の確認導線を作る
    - 制約：取得ループ内で実行しない（Post-fetchバッチ分離）、既存Exhibitions/Tarutani処理を壊さない
    - 成立条件：
      - `python run_search_artists_seed10.py --query "..."`（例）が実行できる
      - top-k の `source_url` / `record_id` / `score`（または同等）を出力できる
      - search summary（query, k, output_paths）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK59）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_search_artists_seed10.py` を追加（artists index/meta を入力に RETRIEVAL_QUERY で top-k 検索）
        - 検索結果に `source_url` / `record_id` / `score` / `vector_index` / `fair_slug` を保存
        - summaryに `query` / `k_requested` / `k_returned` / `output_paths` を保存
      - 動作確認：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0
        - `python run_enrichment_artists_seed10_apply.py` → exit 0
        - `python run_vectorize_artists_seed10.py` → exit 0（`embedded_total=81`）
        - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/vector/search/artists_text_search_results_20260224T102557Z.jsonl`
        - `data/phase1_seed10/derived/vector/search/artists_text_search_summary_20260224T102557Z.json`

[x] 59) artists_text の検索結果を context JSON に整形し、Phase2接続入力を固定する（本体前進）
    - 目的：TASK58の top-k 検索結果を、後続回答層にそのまま渡せる context JSON として保存する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani処理を壊さない
    - 成立条件：
      - `python run_build_artists_context_seed10.py --query "..."`（例）が実行できる
      - context JSON に `source_url` / `record_id` / `score` / `excerpt`（または同等）を含めて保存できる
      - context summary（query, k, input_paths, output_paths）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK60）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_build_artists_context_seed10.py` を追加（`run_search_artists_seed10.py` 実行→top-k結果を context JSON へ整形）
        - context item に `source_url` / `record_id` / `score` / `excerpt` / `headline_ja` / `vector_index` を保存
        - context summary に `query` / `k_requested` / `k_returned` / `input_paths` / `output_paths` を保存
      - 動作確認：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0
        - `python run_enrichment_artists_seed10_apply.py` → exit 0
        - `python run_vectorize_artists_seed10.py` → exit 0（`embedded_total=81`）
        - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/context/artists_text_context_20260224T103230Z.json`
        - `data/phase1_seed10/derived/context/artists_text_context_summary_20260224T103230Z.json`

[x] 60) artists_text の回答スモークCLIを追加し、context JSON から根拠付き回答を出力する（本体前進）
    - 目的：TASK59で整形した context JSON を入力に、Phase2接続前の最小回答導線（質問→回答+根拠）を成立させる
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani処理を壊さない
    - 成立条件：
      - `python run_answer_artists_seed10.py --question "..." --query "..."`（例）が実行できる
      - 出力JSONに `answer` と根拠（`source_url` / `record_id` / `score` / `excerpt`）を保存できる
      - answer summary（question, query, context_path, output_paths）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK61）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_answer_artists_seed10.py` を追加（`--question`/`--query` で context再生成→回答生成→根拠同梱保存）
        - LLM失敗時の最小フォールバックを実装（`answer_status=fallback` + evidence保存）
      - 動作確認：
        - `python run_phase1_seed10.py --include-artists-text` → exit 0
        - `python run_enrichment_artists_seed10_apply.py` → exit 0
        - `python run_vectorize_artists_seed10.py` → exit 0（`embedded_total=81`）
        - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0（`answer_status=ok`, `k_returned=5`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_20260224T104404Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T104404Z.json`

[x] 61) artists_text の回答比較CLIを追加し、query再生成 / context固定の差分可視化入口を作る（本体前進）
    - 目的：artists回答導線の再現性を高めるため、query再生成とcontext固定の差分を1コマンドで比較できる入口を作る
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_compare_artists_answers.py --question "..." --query "..." --context-path "..."`（例）が実行できる
      - 比較summaryに `answer_chars` / `evidence_count` / `mismatch_fields`（または同等）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK62）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_compare_artists_answers.py` を追加（`run_answer_artists_seed10.py` の query再生成 / context固定を両実行して比較）
        - 比較summaryに `answer_chars` / `evidence_count` / `mismatch_fields` / `differences` を保存
      - 動作確認：
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T105015Z.json"` → exit 0（`mismatch_fields=['answer_chars','numeric_tokens']`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T105153Z.json`

[x] 62) artists_text 回答CLIの最小ガードを追加し、空回答/根拠欠落を非0終了で検知できるようにする（本体前進）
    - 目的：回答導線の最低品質を守るため、空回答や根拠欠落をCI/手元で検知できる最小ガードを導入する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `run_answer_artists_seed10.py` に `--fail-on-invalid-output`（例）を追加し、条件不成立時に非0終了できる
      - 最低限のガード条件（`answer` 非空、`evidence` 1件以上、必須根拠キー存在）をsummaryへ記録できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK63）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_answer_artists_seed10.py` に `--fail-on-invalid-output` を追加
        - 出力ガード（`answer` 非空 / `evidence` 非空 / `source_url,record_id,score,excerpt` の必須キー存在）を実装
        - answer JSON / summary JSON に `output_valid` / `invalid_reasons` / `fail_on_invalid_output` を追加
      - 動作確認（外向き接続あり）：
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0（`artists_text_context_20260224T110028Z.json`）
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0（`output_valid=true`）
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T110028Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 失敗系確認（無効出力）：
        - `/tmp/artists_invalid_context_task62.json` を使って `python run_answer_artists_seed10.py --question "ガード動作確認" --context-path /tmp/artists_invalid_context_task62.json --fail-on-invalid-output` を実行
        - `output_valid=false` / `invalid_reasons=['empty_evidence_value:0.source_url','empty_evidence_value:0.record_id','empty_evidence_value:0.excerpt']` / exit 2 を確認
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T110049Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T110214Z.json`

[x] 63) artists_text 回答比較CLIに最小回帰ガードを追加し、差分悪化時のみ非0終了にする（本体前進）
    - 目的：TASK61の単純差分比較を運用しやすくするため、「差分」と「回帰」を分離し、悪化方向だけを非0で検知できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `run_compare_artists_answers.py` に `--fail-on-regression` を追加し、回帰条件時のみ非0終了できる
      - 最低限 `guard_passed` / `regression_reasons` / `mismatch_fields` をsummaryへ保存できる
      - 回帰条件（例：`answer_status` 悪化、`output_valid` true→false、`evidence_count` 減少）を明示できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK64）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_compare_artists_answers.py` に `--fail-on-regression` を追加（既定は後方互換で `False`）
        - 回帰判定を追加（baseline=`query_rebuild`, current=`fixed_context`）：
          - `answer_status` 悪化（`ok < fallback < error`）
          - `output_valid` 悪化（`true -> false`）
          - `evidence_count` 減少
        - 比較summaryへ `fail_on_regression` / `guard_passed` / `regression_detected` / `regression_reasons` / `regression_warnings` / `compare_exit_code` / `exit_reason` を追加
      - 動作確認（通常系）：
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T111221Z.json"` → exit 0（`guard_passed=true`）
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T111221Z.json" --fail-on-regression` → exit 0（`regression_reasons=[]`）
      - 動作確認（回帰系）：
        - `/tmp/artists_invalid_context_task63.json` を使って `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "/tmp/artists_invalid_context_task63.json" --fail-on-regression` を実行
        - `guard_passed=false` / `regression_reasons=['output_valid_regressed:true->false','evidence_count_decreased:5->1']` / exit 2 を確認
      - 互換確認：
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111318Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111347Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111430Z.json`

[x] 64) artists回答導線のQA統合スモークCLIを追加し、context生成→回答→比較を1コマンドで実行できるようにする（本体前進）
    - 目的：artists回答系の手動コマンド列を1本化し、日次確認とCI前の手元確認を短時間で回せるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_smoke.py --question "..." --query "..."`（例）が実行できる
      - 内部で context build / answer / compare（`--fail-on-regression` 任意）を順次実行できる
      - QA summary に各ステップの `exit_code` / `output_paths` / `all_passed` を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK65）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_smoke.py` を追加（context build → answer(`--fail-on-invalid-output`) → compare(`--fail-on-regression` 任意) を順次実行）
        - QA summary に `all_passed` / `wrapper_exit_code` / `steps[].name` / `steps[].command` / `steps[].exit_code` / `steps[].output_paths` を保存
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-regression` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T112405Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T112518Z.json`

[x] 65) artists回答の根拠整形を最小強化し、excerpt/headline欠落時フォールバックを安定化する（本体前進）
    - 目的：answers出力の根拠を常に読みやすくするため、evidence整形の欠落フォールバックを最小追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `run_answer_artists_seed10.py` で `excerpt` 欠落時のフォールバック整形（`headline_ja` / `text` 断片）を実装できる
      - summary にフォールバック件数（例: `evidence_fallback_excerpt_count`）を保存できる
      - `--fail-on-invalid-output` の既存ガードを壊さない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK66）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_answer_artists_seed10.py` に raw参照インデックス（record_id/source_url）を追加し、evidence整形時の欠落フォールバックを実装
          - `excerpt` 欠落時：`headline_ja` → raw `text` 断片（260字）
          - `headline_ja` 欠落時：raw `headline_ja` → `excerpt` 先頭（80字）
        - summary / answer payload に以下メタを追加：
          - `evidence_fallback_excerpt_count`
          - `evidence_fallback_headline_count`
          - `evidence_source_row_missing_count`
      - 動作確認：
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T120544Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - フォールバック再現確認（/tmp 一時context）：
        - `excerpt/headline_ja` を空にした `/tmp/artists_context_task65_missing_excerpt_headline.json` を使用
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --context-path /tmp/artists_context_task65_missing_excerpt_headline.json --fail-on-invalid-output` → exit 0
        - `evidence_fallback_excerpt_count=2` / `evidence_fallback_headline_count=2` / `output_valid=true` を確認
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T120624Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T120844Z.json`

[x] 66) artists回答QA統合CLIにcontext固定再現モードを追加し、日次runと再現runの入口を一本化する（本体前進）
    - 目的：`run_artists_answer_qa_smoke.py` に `--context-path` を追加し、query再生成モードとcontext固定モードを1CLIで運用できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `--query` モード（既存）と `--context-path` モード（新規）を排他で実行できる
      - QA summary に `qa_input_mode` / `context_path_effective` / `steps[].exit_code` を保存できる
      - `--fail-on-regression` の既存挙動を壊さない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK67）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_smoke.py` に `--context-path` を追加し、`--query` と排他制御を実装（両方指定/両方未指定は非0）
        - モード分岐を追加：
          - `qa_input_mode=query_rebuild`：既存どおり context build -> answer -> compare
          - `qa_input_mode=fixed_context`：context build は `skipped`、answer実行、compareは `skipped`
        - summary を拡張：
          - `qa_input_mode`
          - `context_path_effective`
          - `query_effective`
          - `steps[].status`（`ok/failed/skipped`）
          - 引数エラー時は `errors` を保存
        - fixed_context + `--fail-on-regression` は warning-only（`fail_on_regression_ignored_without_query`）に統一
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-regression` → exit 0
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 0
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --fail-on-regression` → exit 0
        - `python run_artists_answer_qa_smoke.py --question "test" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 1（排他違反）
        - `python run_artists_answer_qa_smoke.py --question "test"` → exit 1（query/context未指定）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131612Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131713Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131835Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132100Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132130Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132137Z.json`

[x] 67) artists回答QA統合CLIに複数query一括実行モードを追加し、日次確認を1コマンド化する（本体前進）
    - 目的：`run_artists_answer_qa_smoke.py` に manifest/JSONL 入力を追加し、複数queryの context->answer->compare を一括実行できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `--batch-manifest`（例）で複数ケースを順次実行できる
      - batch summary に `total_cases` / `passed_cases` / `failed_cases` / `cases[].summary_path` を保存できる
      - 単発モード（現行 `--query` / `--context-path`）の後方互換を壊さない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK68）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_smoke.py` に `--batch-manifest` を追加（`.json` / `.jsonl` 読込対応）
        - batchケースは同CLIの単発モードをsubprocessで再利用し、ロジック重複を回避
        - batch summaryへ `total_cases` / `passed_cases` / `failed_cases` / `cases[].summary_path` / `cases[].exit_code` を保存
        - 単発モード（`--query` / `--context-path`）の既存挙動は維持
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 1（DNS: `Temporary failure in name resolution`）
        - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"` → exit 1（queryケースのDNS失敗）
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_fixed_context.json"` → exit 0
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_fixed.json"` → exit 0（`all_passed=true`, `total_cases=2`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_fixed_context.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_fixed.json`

[x] 68) artists回答の根拠整形を最小強化し、重複source統合と表示順の安定化を行う（本体前進）
    - 目的：`run_answer_artists_seed10.py` の evidence を読みやすく保つため、重複根拠の統合と順序安定化を最小差分で追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `source_url + record_id` 重複の根拠を1件に統合できる
      - evidenceの表示順を安定化できる（score降順 + tie-break）
      - summaryに `evidence_dedup_removed_count` / `evidence_sorted`（同等）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK69）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_answer_artists_seed10.py` に evidence安定化処理を追加
          - 安定ソート：`score` 降順 + tie-break（`rank`, `source_url`, `record_id`, `vector_index`）
          - 重複統合：`source_url + record_id` が同一の evidence を1件に集約（先頭採用）
        - summary/payload へ以下を追加
          - `evidence_dedup_removed_count`
          - `evidence_sorted`
      - 動作確認：
        - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 1（DNS: `Temporary failure in name resolution`）
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 1（同上）
        - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 1（query再生成側がDNS失敗）
        - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --fail-on-invalid-output` → exit 0（`evidence_sorted=true`, `evidence_dedup_removed_count=0`）
        - `/tmp/artists_context_task68_dedup.json`（重複1件を意図注入）で再実行 → exit 0（`evidence_dedup_removed_count=1`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T134716Z.json`
        - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T134739Z.json`

[x] 69) artists回答QA統合CLIのbatch caseごとに回帰ガード適用を追加し、失敗検知をケース単位で固定化する（本体前進）
    - 目的：`run_artists_answer_qa_smoke.py --batch-manifest` で、case単位に `fail_on_regression` を適用し、差分悪化ケースのみを明確にfail化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - manifestごとに `fail_on_regression` を指定できる（default + case override）
      - batch summary に `cases[].fail_on_regression_effective` / `cases[].guard_passed`（同等）を保存できる
      - 既存単発モードと既存batch互換を壊さない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK70）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_smoke.py` のbatch caseに以下を追加保存
          - `fail_on_regression_effective`
          - `guard_passed`（compare summaryがある場合）
          - `compare_summary_path` / `compare_exit_code` / `regression_reasons`
          - `case_failure_kind`（`regression_guard_failed` / `query_rebuild_failed` / `fixed_context_failed` / `invalid_case_config`）
        - manifest defaults の反映を明示化
          - `fail_on_regression_default` は manifest defaults 優先で保存
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"` → exit 1（DNS制約でqueryケース失敗）
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task69_regression.json"` → exit 1（fixed_context case=exit 0 / query case=exit 1）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T140420Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T140432Z.json`

[x] 70) artists回答QA統合CLIのbatch実行結果を集約JSONL化し、日次確認対象を1ファイルで追えるようにする（本体前進）
    - 目的：batch summaryだけでなく、case単位の主要結果（question/query/context/exit/summary_path）をJSONLに集約し、日次確認の差分追跡を軽くする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - batch実行時に `artists_answer_qa_batch_cases_*.jsonl`（例）を出力できる
      - 1行1caseで `case_id` / `question` / `query` / `context_path` / `exit_code` / `guard_passed` / `summary_path` を保存できる
      - 既存のbatch summary JSONと単発モード互換を壊さない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK71）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_smoke.py` の batch モードに集約JSONL出力を追加
          - `summary_path.parent / f"{summary_path.stem}_cases.jsonl"` に保存
          - 1行1caseで `case_id/question/query/context_path/exit_code/guard_passed/summary_path` を出力
          - 追加項目：`qa_input_mode` / `fail_on_regression_effective` / `case_failure_kind` / `compare_exit_code` / `compare_summary_path` / `regression_reasons`
        - batch summary JSONに以下を追加
          - `batch_cases_jsonl_path`
          - `batch_cases_jsonl_written`
          - `batch_cases_jsonl_count`
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_fixed_context.json"` → exit 0（単発モードでJSONL未生成を確認）
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed.json"` → exit 0（`total_cases=2`, `batch_cases_jsonl_written=true`, `batch_cases_jsonl_count=2`）
        - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"` → exit 1（DNS制約でqueryケース失敗だが JSONL 出力は維持）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed_cases.jsonl`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T142921Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T142921Z_cases.jsonl`

[x] 71) artists回答QA batch集約JSONLの軽量レポートCLIを追加し、失敗case一覧と子summary参照を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK70で出力した `*_cases.jsonl` を読み、失敗caseだけを短く表示/保存できる入口を作って日次確認を高速化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_batch_report.py --cases-jsonl "..."`（例）が実行できる
      - `failed_cases` / `failed_case_ids` / `summary_paths_to_check`（同等）を出力・保存できる
      - `--latest` で最新 `*_cases.jsonl` を自動解決できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK72）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_batch_report.py` を追加
          - `--cases-jsonl` 指定読み込み
          - `--latest` で `artists_answer_qa_smoke_summary_*_cases.jsonl` 最新を自動解決
          - レポートへ `total_cases` / `failed_cases` / `failed_case_ids` / `summary_paths_to_check` を保存
          - 既定で `*_cases_report.json` を出力
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed.json"` → exit 0
        - `python run_artists_answer_qa_batch_report.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases.jsonl"` → exit 0
        - `python run_artists_answer_qa_batch_report.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases.jsonl`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases_report.json`

[x] 72) artists回答QA batch集約JSONLから失敗case再実行manifestを生成するCLIを追加し、日次復旧導線を短縮する（本体前進）
    - 目的：`*_cases.jsonl` から失敗caseだけを抽出して再実行用manifestを自動生成し、手動切り分けを減らす
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "..."`（例）が実行できる
      - 失敗caseだけを含む manifest JSON（`question/query/context_path/fail_on_regression`）を保存できる
      - `--latest` で最新 `*_cases.jsonl` を解決できる
      - 失敗0件時は空manifestまたは明示メッセージを保存し、非0にはしない
      - 03のCHANGELOGに反映される
      - 次タスク（TASK73）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_retry_manifest.py` を追加
          - `--cases-jsonl` / `--latest` で入力 `*_cases.jsonl` を解決
          - 失敗case（`exit_code != 0`）のみ抽出して再実行manifest JSONを出力
          - caseごとに `case_id/question/query/context_path/fail_on_regression` を保存
          - 失敗0件でも `cases=[]` + `notes=['no_failed_cases_found']` で成功終了
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed.json"` → exit 0
        - `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases.jsonl"` → exit 0
        - `python run_artists_answer_qa_retry_manifest.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases.jsonl`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases_retry_manifest.json`

[x] 73) artists回答QA retry manifest をそのまま実行するワンショットCLIを追加し、失敗case復旧を1コマンド化する（本体前進）
    - 目的：TASK72の retry manifest を直接実行して復旧runまでを1コマンド化し、日次運用の手戻りを減らす
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_retry_run.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `*_retry_manifest.json` を解決できる
      - 失敗0件manifestでは no-op/skip を明示して成功終了できる
      - summaryに `retry_manifest_path` / `executed_cases` / `wrapper_exit_code`（同等）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK74）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_retry_run.py` を新規追加
          - 入力モード：`--retry-manifest` / `--latest`（排他、両方指定/未指定は exit 1）
          - `--latest` は `data/phase1_seed10/derived/answer` 配下の最新 `artists_answer_qa_smoke_summary_*_retry_manifest.json` を解決
          - retry manifest を検証し、`cases=[]` は no-op 成功（exit 0）として処理
          - validケースは `run_artists_answer_qa_smoke.py --batch-manifest ...` を subprocess 再利用して実行（ロジック重複なし）
          - 親summaryに `retry_manifest_path` / `retry_manifest_path_requested` / `retry_manifest_latest_resolved` / `retry_manifest_case_count` / `executed_cases` / `child_batch_exit_code` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `invalid_case_count` / `invalid_case_ids` / `wrapper_exit_code` を保存
          - 親CLI exit code は `0=success(no-op含む)` / `1=failure` に正規化
      - 動作確認：
        - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed.json"` → exit 0
        - `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases.jsonl"` → exit 0
        - `python run_artists_answer_qa_retry_run.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases_retry_manifest.json"` → exit 0（no-op, `executed_cases=0`）
        - `python run_artists_answer_qa_retry_run.py --latest` → exit 0（no-op）
        - `python run_artists_answer_qa_retry_run.py --retry-manifest "/tmp/artists_answer_qa_retry_manifest_task73_invalid.json"` → exit 1（`child_batch_exit_code=1`）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162427Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162436Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162445Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162445Z_child_batch_summary.json`

[x] 74) artists回答QA retry run summary の軽量レポートCLIを追加し、failed/recovered を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK73で出力した `artists_answer_qa_retry_run_summary_*.json` を短く集計し、失敗/復旧の切り分けを高速化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_retry_run_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 retry run summary を自動解決できる
      - レポートに `retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `all_passed` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `notes`（同等）を保存できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK75）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_retry_run_report.py` を新規追加
          - 入力：`--summary-path` / `--latest`（排他）
          - `--latest` は `artists_answer_qa_retry_run_summary_*.json` から `_child_batch_summary` / `_report` を除外して最新本体summaryを解決
          - レポートJSONへ `retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `all_passed` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `notes` を保存
          - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可能）
          - 終了コードは `0=report_generated` / `1=summary_not_found_or_invalid`
      - 動作確認：
        - `python run_artists_answer_qa_retry_run.py --latest` → exit 0
        - `python run_artists_answer_qa_retry_run_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T163348Z.json"` → exit 0
        - `python run_artists_answer_qa_retry_run_report.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T163348Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T163434Z.json`

[x] 75) artists回答QAの日次復旧ワンショットCLIを追加し、batch実行→report→retry manifest→retry run→retry report を1コマンド化する（本体前進）
    - 目的：TASK70〜74の個別CLIを順次実行する運用手順を1コマンド化し、日次復旧の手戻りを減らす
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "..."`（例）が実行できる
      - 内部で `qa_smoke(batch)` / `batch_report` / `retry_manifest` / `retry_run` / `retry_run_report` を順次再利用できる（重複実装しない）
      - daily summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` を保存できる
      - retry対象0件でも no-op を明示して成功終了（exit 0）できる
      - 03のCHANGELOGに反映される
      - 次タスク（TASK76）プロンプト全文を提示できる
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery.py` を追加
        - 子CLIを順次再利用して実行（`batch_smoke -> batch_report -> retry_manifest -> retry_run -> retry_run_report`）
        - daily summary に `steps[].name/command/exit_code/status/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存
        - `retry_run` が `noop_empty_retry_manifest` の場合は no-op 成功として扱い、`notes` に理由を残す
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260224T164617Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest.json`

[x] 76) artists回答QA日次復旧ワンショットの軽量レポートCLIを追加し、daily summary から failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
    - 目的：TASK75の `artists_answer_qa_daily_recovery_summary_*.json` を短く集約し、日次で「どのstepが失敗したか」「どの子summaryを開くべきか」を即確認できる導線を追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_summary_*.json` を自動解決できる
      - レポートに最低限 `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes`（同等）を保存できる
      - 03 の NEXT_TASKS の 76) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_report.py` を追加
        - 入力モード：`--summary-path` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_summary_*.json` から `_report.json` / `_batch_smoke_summary` / `_batch_report` / `_retry_manifest` / `_retry_run_summary` / `_retry_run_report` を除外して本体summaryを解決
        - レポートJSONへ `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes` / `report_exit_code` / `exit_reason` を保存
        - 終了コードは `0=report_generated` / `1=summary_not_found_or_invalid` で固定
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T075527Z.json`

[x] 77) artists回答QA日次復旧レポートから failed step あり run を抽出する要約CLIを追加し、要再対応runを1コマンドで一覧化する（本体前進）
    - 目的：TASK76のレポートJSONを複数本まとめて読み、`failed_steps>0` の run だけを抽出して日次フォロー対象を固定化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20`（例）が実行できる
      - 失敗run一覧（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
      - 03 の NEXT_TASKS の 77) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_report_rollup.py` を追加
        - `artists_answer_qa_daily_recovery_summary_*_report.json` を最新N件（`--latest-n`）読み込み、`failed_steps` を基準に失敗runのみ抽出
        - rollup JSONへ `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存
        - `_batch_report.json` / `_retry_run_report.json` は候補から除外し、daily report本体のみを集計対象にする
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T080328Z.json`

[x] 78) artists回答QA日次復旧レポートrollupから failed run 向け retry manifest を生成するCLIを追加し、要再対応runだけを即再実行できるようにする（本体前進）
    - 目的：TASK77の rollup JSON から `failed_runs[]` を抽出し、daily recovery再実行用の最小manifestを自動生成する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_report_rollup_*.json` を自動解決できる
      - 生成manifestに最低限 `source_summary_path` / `retry_manifest_path` / `failed_step_names` を保存できる
      - 03 の NEXT_TASKS の 78) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py` を追加
        - 入力モード：`--rollup-json` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_report_rollup_*.json` から最新を解決
        - `failed_runs[]` から `cases[]` を生成し、`source_summary_path` / `failed_step_names` / `child_summary_paths_to_check` / `batch_manifest_path` を保存
        - manifest top-level に `retry_manifest_path` / `rollup_failed_run_count` / `retry_case_count` / `notes` を保存
        - failed run 0件でも `cases=[]` で manifest を保存し exit 0
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 1
        - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z.json"` → exit 0（failed run 0件）
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T081259Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z_retry_manifest.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T081303Z.json`

[x] 79) artists回答QA日次復旧retry manifest（rollup起点）をそのまま実行するワンショットCLIを追加し、failed run再実行を1コマンド化する（本体前進）
    - 目的：TASK78の `*_report_rollup_*_retry_manifest.json` を直接実行し、要再対応runだけを再実行する導線を固定する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json` を自動解決できる
      - failed run 0件manifestでは no-op成功（exit 0）し、summaryで判別できる
      - 03 の NEXT_TASKS の 79) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を追加
        - 入力モード：`--retry-manifest` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json` から最新を解決
        - retry manifest `cases[]` を順次実行し、`run_artists_answer_qa_daily_recovery.py --batch-manifest ... --output-json ...` をsubprocess再利用
        - summaryへ `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries` / `cases[]`（`case_id` / `exit_code` / `daily_summary_path`）を保存
        - 0件manifestは no-op成功（`executed_runs=0` / `retry_run_mode=noop_empty_retry_manifest` / exit 0）
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085050Z.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085050Z_retry_manifest.json"` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z_retry_manifest.json"` → exit 0（no-op）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085111Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085123Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085135Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T085123Z.json`

[x] 80) artists回答QA日次復旧retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK79で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
      - レポートに最低限 `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check`（同等）を保存できる
      - 03 の NEXT_TASKS の 80) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py` を追加
        - 入力モード：`--summary-path` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` から `_report.json` と `_failed_run_` を除外して本体summaryのみ解決
        - レポートへ `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存
        - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可）
        - exit code を `0=report_generated / 1=summary_not_found_or_invalid` で固定
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085951Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085951Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T085954Z.json`

[x] 81) artists回答QA日次復旧retry run reportのrollup CLIを追加し、failed/recovered runの推移を1コマンドで抽出できるようにする（本体前進）
    - 目的：TASK80で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json` を複数本集約し、要再対応runを即把握できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20`（例）が実行できる
      - rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存できる
      - `--latest-n` / `--search-dir` で対象範囲を調整できる
      - 03 の NEXT_TASKS の 81) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py` を追加
        - 対象：`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json`
        - `--latest-n` / `--search-dir` / `--glob` / `--output-json` を実装
        - rollup JSONへ `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存
        - `failed_run` は `failed_case_ids` / `failed_runs` / `all_passed` / `wrapper_exit_code` から判定
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T091123Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T091123Z_report.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T091126Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T091126Z.json`

[x] 82) artists回答QA日次復旧retry run report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
    - 目的：TASK81の rollup JSON から failed run だけを抽出し、`run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` に渡せるmanifestを自動生成する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存Exhibitions/Tarutani/guard/history/lint/matrixの処理を壊さない
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` を自動解決できる
      - 生成manifestに `source_summary_path` / `failed_case_ids` / `retry_manifest_path`（同等）を保存できる
      - failed run 0件でも空manifestを保存し、exit 0 を維持できる
      - 03 の NEXT_TASKS の 82) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` を追加
        - 入力：`--rollup-json` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` から `*_retry_manifest.json` を除外して解決
        - 出力manifestへ `source_summary_path` / `source_summary_paths` / `failed_case_ids` / `retry_manifest_path` / `cases[].batch_manifest_path` を保存
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json /tmp/artists_retry_run_report_rollup_empty_task82.json` → exit 0（failed_runs=0 / retry_cases=0）
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z_retry_manifest.json"` → exit 1
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z_retry_manifest.json`
        - `/tmp/artists_retry_run_report_rollup_empty_task82_retry_manifest.json`

[x] 83) artists回答QA日次復旧retry run report rollup起点manifestをそのまま実行するワンショットCLIを追加し、要再対応run再実行を1コマンド化する（本体前進）
    - 目的：TASK82で生成した `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を直接実行して、failed run の再実行を1コマンド化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily recovery/retry run/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を自動解決できる
      - failed run 0件manifestでは no-op 成功（exit 0）し、summary に `executed_runs=0` / `notes` を保存できる
      - summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
      - 03 の NEXT_TASKS の 83) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py` を追加
        - 既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を subprocess で再利用する薄い実行ラッパーとして実装
        - `--latest` は `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を既定globで解決
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094043Z_retry_manifest.json"` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "/tmp/artists_retry_run_report_rollup_empty_task82_retry_manifest.json"` → exit 0（no-op）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094051Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094111Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T094051Z.json`

[x] 84) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK83で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily recovery/retry run/report/rollup/retry-manifest本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
      - レポートに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
      - 03 の NEXT_TASKS の 84) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py` を追加
        - 入力：`--summary-path` / `--latest`（排他）
        - `--latest` は `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` から `_report.json` と `_failed_run_` を除外して本体summaryのみ解決
        - レポートへ `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094707Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094707Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T094725Z.json`

[x] 85) artists回答QA日次復旧retry run summary report のrollup CLIを追加し、failed/recovered run推移を1コマンドで抽出できるようにする（本体前進）
    - 目的：TASK84で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json` を複数本まとめて読み、失敗runを即時抽出する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存retry run本体/報告CLIのロジックは変更しない（rollup CLI追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20`（例）が実行できる
      - rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存できる
      - `--latest-n` と `--search-dir` を使って対象範囲を調整できる
      - 03 の NEXT_TASKS の 85) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py` を追加
        - top-levelへ `schema_name` / `schema_version` / `artifact_kind` / `generated_at` / `generated_by` を追加
        - 対象探索を `is_target_report(...)` / `list_candidate_reports(...)` に寄せ、include/exclude/sortを1か所に集約
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T100815Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T100815Z_report.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T100830Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T100835Z.json`

[x] 86) artists回答QA日次復旧retry run summary report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
    - 目的：TASK85で生成した rollup JSON から failed run のみを抽出し、再実行用 manifest を自動生成して復旧導線を短縮する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily recovery/retry run/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` を解決できる
      - generated manifest に最低限 `source_summary_path` / `failed_case_ids` / `retry_manifest_path`（同等）を保存できる
      - failed run 0件でも空manifestを保存して exit 0 を維持できる
      - 03 の NEXT_TASKS の 86) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：
        - 既存 `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` をTASK85出力に対して適用
        - `--latest` で `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` を解決し、`*_retry_manifest.json` を除外する探索ロジックを確認
        - 生成manifestに `source_summary_path` / `failed_case_ids` / `retry_manifest_path` / `cases[]` を保存
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102015Z.json"` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102015Z_retry_manifest.json"` → exit 1
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102015Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102015Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T102033Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T102015Z.json`

[x] 87) artists回答QA日次復旧retry run report rollup起点retry manifestのワンショット実行ラッパーを追加し、`--latest` だけで再実行できるようにする（本体前進）
    - 目的：TASK86で生成する `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を直接実行し、要再対応run再実行を1コマンド化する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily recovery/retry run/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest`（例）が実行できる
      - `--retry-manifest` 明示指定でも実行できる
      - failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
      - 03 の NEXT_TASKS の 87) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py` を追加
        - 既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を subprocess で再利用する薄いラッパーとして実装
        - `--latest` は `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を既定globで解決
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102710Z_retry_manifest.json"` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --retry-manifest "/tmp/artists_retry_run_report_rollup_empty_task87_retry_manifest.json"` → exit 0（no-op）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102710Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T102710Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T102717Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T102805Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T103131Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T102859Z.json`

[x] 88) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK87で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存retry run本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
      - レポートに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
      - 03 の NEXT_TASKS の 88) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：
        - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py` を追加
        - `qa_artifact_utils.py` を追加し、TASK85〜88系の `--latest` 解決とスキーマ識別メタを最小共通化
        - TASK85/86/87系へ共通ユーティリティ適用（`list/resolve latest`・`artifact header`）
        - 短い入口を追加（後方互換のため長いCLI名は維持）:
          - `run_aqa_retry_run_report_rollup.py`
          - `run_aqa_retry_run_report_rollup_manifest.py`
          - `run_aqa_retry_run_report_rollup_retry_run.py`
          - `run_aqa_retry_run_report_rollup_retry_run_report.py`
      - 動作確認：
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest` → exit 1
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --latest` → exit 0
        - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z.json"` → exit 0
        - `python run_aqa_retry_run_report_rollup_retry_run_report.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T105421Z.json`

[x] 89) artists回答QA retry-run導線（TASK85〜88）を短い入口でワンショット実行するCLIを追加し、日次復旧の運用手順を固定する（本体前進）
    - 目的：TASK85〜88を都度手打ちせず、`rollup -> retry manifest -> retry run -> retry run report` を1コマンドで実行して daily summary に集約する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存本体CLIは再利用（subprocess）しロジック重複を作らない
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain.py --latest`（例）が実行できる
      - summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存できる
      - retry対象0件（no-op）でも exit 0 で完了できる
      - 03 の NEXT_TASKS の 89) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記

[x] 90) artists回答QA retry-run daily chain summary の軽量レポートCLIを追加し、failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
    - 目的：TASK89で生成される `artists_answer_qa_retry_run_daily_chain_summary_*.json` から failed step を即時抽出し、次に開くべき子summaryを短く提示する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_report.py --summary-path "..."` / `--latest` が実行できる
      - report JSONに `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes` を保存できる
      - 03 の NEXT_TASKS の 90) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_report.py` を追加（`--summary-path` / `--latest` 排他）
      - 共通化：`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用
      - スキーマ識別メタ：`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by` を report JSON に付与
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z_report.json`

[x] 91) artists回答QA retry-run daily chain report のrollup CLIを追加し、failed run推移を1コマンドで抽出できるようにする（本体前進）
    - 目的：TASK90で生成される `artists_answer_qa_retry_run_daily_chain_summary_*_report.json` を複数本集約し、要再対応runの一覧と参照先summaryを短時間で確認できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/report本体ロジックは変更しない（rollup CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（例）が実行できる
      - rollup JSONに `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
      - `--latest-n` / `--search-dir` で対象範囲を調整できる
      - 03 の NEXT_TASKS の 91) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_report_rollup.py` を追加
      - 共通化：`qa_artifact_utils.py` の `list_candidate_artifacts` / `build_artifact_header` を再利用
      - 出力：rollup JSONに `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T120703Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T120703Z_report.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T120723Z.json`

[x] 92) artists回答QA retry-run daily chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
    - 目的：TASK91で生成される `artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` を自動解決できる
      - 生成manifestに最低限 `source_summary_path` / `failed_step_names` / `retry_manifest_path`（同等）を保存できる
      - failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
      - 03 の NEXT_TASKS の 92) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` を追加
      - 共通化：`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用
      - 出力：manifest JSONに `source_summary_path` / `failed_step_names` / `retry_manifest_path`（+ `cases[]` / `notes`）を保存
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T121322Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T121322Z_retry_manifest.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T121331Z.json`

[x] 93) artists回答QA retry-run daily chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
    - 目的：TASK92で生成される `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を直接実行し、要再対応runのみを1コマンドで再実行する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を自動解決できる
      - failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
      - summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
      - 03 の NEXT_TASKS の 93) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 運用メモ：
      - 削除候補は `docs/04_TASK_PROGRESS_LOG.md` の `CLEANUP_CANDIDATES_MASTER` に集約管理する
      - 実削除前は手動で `_trash` へ退避する（2026-02-25から候補退避運用を開始）
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py` を追加（薄い実行ラッパー）
      - 共通化：`qa_artifact_utils.py` の `resolve_latest_artifact(...)` を使い、`--latest` で `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を解決
      - 再利用：`run_aqa_retry_run_report_rollup_retry_run.py` を subprocess 委譲し、retry-run本体ロジックは既存実装を再利用
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --latest` → exit 0（no-op, `executed_runs=0`）
        - `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z_retry_manifest.json"` → exit 0（no-op）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T143206Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T143053Z.json`

[x] 94) artists回答QA retry-run daily chain report rollup起点の復旧導線をワンショット化し、rollup→manifest→retry-runを1コマンドで順次実行できるようにする（本体前進）
    - 目的：TASK91〜93の短い入口CLI（rollup / retry-manifest / retry-run）を一つのチェーンCLIで順次実行し、日次復旧の手順漏れを減らす
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存rollup/retry-manifest/retry-run本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（例）が実行できる
      - 内部で少なくとも以下を順次実行できる：
        - `run_aqa_retry_run_daily_chain_report_rollup.py`
        - `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py`
        - `run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py`
      - chain summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存できる
      - no-op（retry対象0件）でも chain は正常終了（exit 0）できる
      - 03 の NEXT_TASKS の 94) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_recovery_chain.py` を追加
      - 再利用：既存3本（`run_aqa_retry_run_daily_chain_report_rollup.py` / `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` / `run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py`）を subprocess で順次実行
      - 共通化：`qa_artifact_utils.py` の `build_artifact_header(...)` を再利用し、chain summaryへ schema識別メタを付与
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T155516Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T155522Z.json`

[x] 95) artists回答QA retry-run daily chain recovery chain summary の軽量レポートCLIを追加し、failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
    - 目的：TASK94で生成する `artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json` から failed step を即時抽出し、次に開くべき子summaryを短く提示する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain recovery chain本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "..."` / `--latest` が実行できる
      - report JSONに最低限 `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes` を保存できる
      - 03 の NEXT_TASKS の 95) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/レポートパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_recovery_chain_report.py` を追加
      - 共通化：`qa_artifact_utils.py` の `resolve_latest_artifact(...)` / `build_artifact_header(...)` を再利用
      - 追記：`qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_report` artifact定義を追加し、`retry_run_daily_chain_recovery_chain_summary` に `_report.json` 除外を追加
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T160126Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T160126Z_report.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T155516Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T160138Z.json`

[x] 96) artists回答QA retry-run daily chain recovery chain report のrollup CLIを追加し、failed step推移を1コマンドで抽出できるようにする（本体前進）
    - 目的：TASK95で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*_report.json` を最新N件で集約し、failed runの推移を即確認できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/report本体ロジックは変更しない（rollup CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（例）が実行できる
      - rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
      - `--latest-n` と `--search-dir` で対象範囲を調整できる
      - 03 の NEXT_TASKS の 96) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py` を追加
      - 共通化：`qa_artifact_utils.py` の `list_candidate_artifacts(...)` / `build_artifact_header(...)` を再利用
      - 追記：`qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_report_rollup` artifact定義を追加
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T161147Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T161147Z_report.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T161201Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T161204Z.json`

[x] 97) artists回答QA retry-run daily chain recovery chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
    - 目的：TASK96で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` を自動解決できる
      - 生成manifestに最低限 `source_summary_path` / `failed_step_names` / `retry_manifest_path`（同等）を保存できる
      - failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
      - 03 の NEXT_TASKS の 97) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py` を追加
      - 共通化：`qa_artifact_utils.py` の `resolve_latest_artifact(...)` / `build_artifact_header(...)` を再利用
      - 追記：`qa_artifact_utils.py` に以下を追加
        - `retry_run_daily_chain_recovery_chain_report_rollup`（`exclude_substrings=[\"_retry_manifest.json\"]`）
        - `retry_run_daily_chain_recovery_chain_report_rollup_retry_manifest`
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest` → exit 0（no-op, `notes=[\"no_failed_runs_in_rollup\"]`）
        - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --rollup-json \"data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z.json\"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T163112Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T163112Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T163137Z.json`

[x] 98) artists回答QA retry-run daily chain recovery chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
    - 目的：TASK97で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` を直接実行し、要再対応runのみを1コマンドで再実行する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存daily chain/recovery chain report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` を自動解決できる
      - failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
      - summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
      - summaryに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
      - 03 の NEXT_TASKS の 98) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：`run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py` を追加
      - 共通化：`qa_artifact_utils.resolve_latest_artifact(...)` で `--latest` の retry manifest を解決
      - 追記：`qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_retry_run_summary_from_report_rollup_manifest` artifact定義を追加（TASK99の `--latest` 解決を安定化）
      - 再利用：`run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲し、retry-run本体ロジックの重複を回避
      - 動作確認：
        - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
        - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest` → exit 0（no-op）
        - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z_retry_manifest.json"` → exit 0（no-op）
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 生成物：
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z_retry_manifest.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T164211Z.json`
        - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T164217Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T164228Z.json`

[x] 99) artists回答QA retry-run daily chain recovery chain report rollup起点retry-run summary の軽量レポートCLIを追加し、failed/recovered run を `--latest` で即確認できるようにする（本体前進）
    - 目的：TASK98で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存retry-run本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
      - report JSONに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
      - report JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
      - 03 の NEXT_TASKS の 99) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/reportパス）を追記

[x] 100) Phase1 seed10 の artists画像収集（実測）CLIを追加し、5枚/人・70%超えの達成状況を summary で可視化する（本体前進）
    - 目的：seed10（artists対象）で画像収集を実行し、まずは現状の取得率（目標: 1人あたり5枚 / 取得率70%超）を実測で把握する
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存画像取得ロジックを壊さない、ドメイン専用ハードコードを増やさない
    - 成立条件：
      - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` が実行できる
      - summary JSONに `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `failed_cases` を保存できる
      - summary JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
      - 03 の NEXT_TASKS の 100) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記
    - 実行メモ：
      - 実装：`run_phase1_seed10_artist_image_collect.py` を追加（seed10 artists rawから画像候補抽出・保存・実測summary出力）
      - 動作確認：
        - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 実測結果：
        - `seed_artist_count=81`
        - `artists_with_ge_target_images=0`
        - `success_rate_ge_target=0.0`
        - `threshold_passed=false`
      - 生成物：
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T232825Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T232825Z.json`

[x] 101) artists画像収集実測summaryの軽量レポートCLIを追加し、5枚達成率/失敗理由上位/ドメイン別失敗を1コマンドで確認できるようにする（本体前進）
    - 目的：TASK100のsummaryを短く集約し、改善優先順位（どこで失敗しているか）を日次で即判断できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、画像収集本体ロジックは変更しない（report CLI追加のみ）
    - 成立条件：
      - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "..."`（例）が実行できる
      - `--latest` で最新 `phase1_seed10_artist_image_collect_summary_*.json` を自動解決できる
      - report JSONに `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `top_failed_reasons` / `top_failed_domains`（同等）を保存できる
      - 03 の NEXT_TASKS の 101) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/reportパス）を追記
    - 実行メモ：
      - 実装：`run_phase1_seed10_artist_image_collect_report.py` を追加（`--summary-path` / `--latest`）
      - 共通化：`qa_artifact_utils.resolve_latest_artifact(...)` を再利用して最新summaryを解決
      - 追記：`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_summary` / `phase1_seed10_artist_image_collect_report` artifact定義を追加
      - 動作確認：
        - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T233537Z.json"` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 実測レポート要点：
        - `seed_artist_count=81`
        - `artists_with_ge_target_images=0`
        - `success_rate_ge_target=0.0`
        - `threshold_passed=false`
        - `top_failed_reasons=[{\"reason\":\"html_fetch_failed\",\"count\":81}]`
      - 生成物：
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T233537Z.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T233537Z_report.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T233602Z.json`

[x] 102) artists画像収集実測reportのrollup CLIを追加し、直近N回の達成率推移と失敗理由変化を1コマンドで抽出できるようにする（本体前進）
    - 目的：TASK101のreportを複数回集約し、改善施策の効き目を時系列で確認できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、画像収集本体ロジックは変更しない（rollup CLI追加のみ）
    - 成立条件：
      - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（例）が実行できる
      - rollup JSONに `total_reports` / `threshold_passed_count` / `success_rate_trend` / `top_failed_reasons_trend`（同等）を保存できる
      - `--latest-n` と `--search-dir` で対象範囲を調整できる
      - 03 の NEXT_TASKS の 102) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/rollupパス）を追記
    - 実行メモ：
      - 実装：`run_phase1_seed10_artist_image_collect_report_rollup.py` を追加（`--latest-n` / `--search-dir` / `--glob` / `--output-json`）
      - 共通化：`qa_artifact_utils.list_candidate_artifacts(...)` で report候補の最新N件解決を共通化
      - 追記：`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_report_rollup` artifact定義を追加
      - 動作確認：
        - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 実測rollup要点：
        - `total_reports=2`
        - `threshold_passed_count=0`
        - `threshold_passed_rate=0.0`
        - `success_rate_trend` / `top_failed_reasons_trend` / `top_failed_domains_trend` を保存
      - 生成物：
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T234412Z.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T234412Z_report.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260225T234417Z.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T234417Z.json`

[x] 103) artists画像収集実測rollupから優先再収集manifestを生成し、失敗理由/ドメイン上位への再試行入口を短縮する（本体前進）
    - 目的：TASK102のrollupを起点に、次に再収集すべきartistケースを手作業なしで抽出できるようにする
    - 制約：取得ループ内で実行しない（Post-fetch分離）、画像収集本体ロジックは変更しない（manifest生成CLI追加のみ）
    - 成立条件：
      - `python run_phase1_seed10_artist_image_collect_retry_manifest.py --rollup-json "..."`（例）が実行できる
      - `--latest` で最新 `phase1_seed10_artist_image_collect_report_rollup_*.json` を自動解決できる
      - manifestに `source_rollup_path` / `failed_reason_filter` / `failed_domain_filter` / `cases[]`（artist_id/source_url/reason/domain）を保存できる
      - failedケース0件でも空manifestを保存して exit 0 を維持できる
      - 03 の NEXT_TASKS の 103) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/manifestパス）を追記
    - 実行メモ：
      - 実装：`run_phase1_seed10_artist_image_collect_retry_manifest.py` を追加（`--rollup-json` / `--latest` / `--max-cases` / `--min-failed-count`）
      - 共通化：`qa_artifact_utils.resolve_latest_artifact(...)` で rollupの `--latest` 解決を再利用
      - 追記：`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_retry_manifest` artifact定義を追加
      - 動作確認：
        - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
        - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
        - `python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest` → exit 0
        - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
      - 実測manifest要点：
        - `source_rollup_path=.../phase1_seed10_artist_image_collect_report_rollup_20260225T234417Z.json`
        - `failed_reason_filter=[\"html_fetch_failed\"]`
        - `failed_domain_filter` は上位10ドメインを自動採用
        - `selected_case_count=50`
      - 生成物：
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T235137Z.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T235137Z_report.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260225T235146Z.json`
        - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260225T234417Z_retry_manifest.json`
        - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T235146Z.json`

[x] 104) artists画像収集retry manifestをワンショット実行するCLIを追加し、再収集導線を1コマンド化する（本体前進）
    - 目的：TASK103で生成した retry manifest を直接実行し、優先再収集の手順漏れを防ぐ
    - 制約：取得ループ内で実行しない（Post-fetch分離）、既存画像収集本体ロジックは変更しない（実行ラッパー追加のみ）
    - 成立条件：
      - `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest "..."`（例）が実行できる
      - `--latest` で最新 `phase1_seed10_artist_image_collect_report_rollup_*_retry_manifest.json` を自動解決できる
      - no-op manifest（cases=0）でも exit 0 で完了し、summaryに `executed_cases=0` / `notes` を残せる
      - summaryに `retry_manifest_path` / `executed_cases` / `wrapper_exit_code` / `child_collect_summaries`（同等）を保存できる
      - 03 の NEXT_TASKS の 104) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summaryパス）を追記

[x] 105) ブロッカー解消確認：DNS/外向き通信回復後の artists画像収集再実測を実施し、改善ループ再開可否を判定する（本体前進）
    - 目的：DNS/外向き通信が復旧したかを実測し、`run_phase1_seed10_artist_image_collect.py` の再検証を行う
    - 制約：取得ループ内でLLM加工しない（Post-fetch分離）、既存画像収集本体ロジックは原則変更しない
    - 成立条件：
      - `curl` / `socket.gethostbyname` の通信確認を実施
      - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` を再実行
      - report / rollup / guard を再実行し、summaryに DNS状態と失敗理由を残す
      - 03 の NEXT_TASKS の 105) を [x]、CHANGELOG追記
      - 04 に実行結果（コマンド/exit/summary/report/rollupパス）を追記
[x] 106) 環境ブロッカー継続対応：DNS/外向き通信回復後の artists画像収集再実測を再開し、5枚達成率の改善ループへ戻す（本体前進）
    - 結果：通信確認は成功（`curl`/`socket` ともOK）、再実測で `network_dns_probe_ok=true`
    - 実測値：`seed_artist_count=81`, `artists_with_ge_1_image=70`, `artists_with_ge_target_images=66`, `success_rate_ge_target=0.814815`, `threshold_passed=true`
[x] 107) 10ギャラリーのArtistsテキスト抽出を実行し、共通スキップ適用 + 共通R2同期適用を確認してExhibitions抽出フェーズへ進む（本体前進）
    - 結果：初回は最小スコープ（`--max-artists-per-gallery 1`）で実行。`skip_registry applied: before=10 after=8 skipped=2` を確認。
    - 実測値（初回）：`artists_records_saved_total=0` / `artists_existing_records_total=225` / `artists_skipped_total=8`
    - 原因修正：capを候補抽出段階ではなく「保存成功件数段階」で適用するよう `run_phase1_seed10.py` を修正。
    - 再実測（修正後）：`--max-artists-per-gallery 80` で `artists_records_saved_total=4`（The Approach 3件 + Gallery Baton 1件）を追加保存。
    - guard：`guard_passed=true`（mismatches=0）
    - R2：`phase1_all` 自動同期 `status=ok`、手動 `raw dry-run -> guarded apply` も実行（uploaded=0 / skipped=6 / pruned=0）
[x] 108) 10ギャラリーのArtistsテキスト抽出を完了ゲートまで詰める（Exhibitions画像へ進む前に未達要因を確定）（本体前進）
    - 実行完了：`run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` / `run_compare_phase1_guard.py --target-year 2025`（いずれもexit 0）
    - 実測：`artists_records_saved_total=42` を確認（Arcadia/Adamsの再開可否判定まで実施）
    - 運用更新：TASKプロンプト末尾を「【タスク終了時に行うこと】」へ統一し、03更新手順（02→01→03）を固定化
[x] 109) Artists/Exhibitions 共通テンプレ運用で次カテゴリへ進む前の実行ゲートを確定する（本体前進）
    - 実行：`run_phase1_network_preflight.py` 2回PASS後、`run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` を実施。
    - 判定：artist単位coverageは `7/10 gallery` が `>=0.70`（70.00%）。未達は `Athr(0.4359)`、`A+ Works of Art(0.6364)`、`Addis Fine Art(0.6757)`。
    - 未達理由：`DUPLICATE_TEXT_HASH_EXISTING` が支配的（重複除外ルールによる保存抑制）。`reextract_targets_artists_text_task_t109.csv` に最小対象3件を確定。
    - R2：`run_phase1_seed10_r2_sync.py --scope raw --dry-run --prune` 実行後、guarded apply（uploaded=0 / skipped=6 / pruned=0）確認。
[x] 110) 未達3ギャラリー（Athr / A+ Works / Addis）のartist_text重複原因を共通モジュール範囲で切り分け、6-2準拠で追加改修 or 理由付き確定を行う（本体前進）
    - 根因分類：3件すべて `DUPLICATE_TEXT_HASH_DOMINANT`（Athr=26件, A+ Works=28件, Addis=25件）
    - 上位理由（共通）：`DUPLICATE_TEXT_HASH_EXISTING` > `DUPLICATE_ARTIST_GLOBAL_IN_RUN/EXISTING`
    - 判定：個別if禁止・重複ロジック追加禁止（6-2）を優先し、今回は追加改修なしで理由付き確定
    - 再開条件：SSOTで「artist_text重複除外ポリシー（text_hash粒度）」の変更合意が出た場合のみ再開
[x] 111) ArtistsテキストのURL canonical重複整理を汎用改良し、最小回帰テストで達成率低下なしを確認する（本体前進）
    - 実装: `phase1_artist_link_utils.py` に artist detail canonical化/URL品質スコアを追加。
    - 実装: `run_phase1_seed10.py` で Artists候補重複判定を canonical基準へ変更。known/saved判定を「従来hash + canonical hash」互換に変更。
    - 事前基準: Athr=17/39(43.59%)、A+ Works=28/44(63.64%)、Addis=25/37(67.57%)。
    - 判定: 事後coverageは3件とも同値維持（低下なし）。改善は限定的だが、URL表記ゆれ吸収の汎用ガードを実装完了。
    - guard: `phase1_guard_summary_2025_20260301T122227Z.json`（`guard_passed=true`）。
[x] 112) Exhibitions画像抽出フェーズへ移行し、最小スコープで共通スキップ/R2同期の適用を再確認する（本体前進）
    - 実装: `run_phase1_seed10_exhibition_image_collect.py` / `run_phase1_seed10_exhibition_image_collect_report.py` を新規追加（汎用のみ、個別ifなし）。
    - 最小実測: `liste / A+ Works of Art / 110-after-all-we-carry...` で `saved_images=5/5`、`hero/profile/logo` 混入0。
    - 同期: `run_phase1_seed10_r2_sync.py --scope derived` の dry-run / guarded apply を実行し、新規6件反映を確認。
    - guard: `phase1_guard_summary_2025_20260301T125846Z.json`（`guard_passed=true`）。
[x] 113) Exhibitions画像抽出を段階拡張し、10ギャラリーへ安全展開する前提（回帰なし・重複なし・R2同期）を確定する（本体前進）
    - 対象固定: `data/gallery_lists/reextract_targets_exhibitions_image_task_t113.csv`（10ギャラリー×各1exhibition）を機械生成。
    - 実測結果: `seed=10`, `ge_1=10`, `ge_target=8`, `saved_images_total=42`。
    - 判定値: 抽出0件ギャラリー=0、hero/profile/logo混入=0、重複保存（URL/payload）=0、`ge_1率=1.0`。
    - guard/R2: `guard_passed=true`、derived同期 `uploaded=44 / pruned=0 / failed=0`。
[x] 114) Exhibitions画像抽出を10ギャラリー全体へ拡張し、未達のみ再抽出で達成率と安定性を確定する（本体前進）
    - 対象CSV: `reextract_targets_exhibitions_image_task_t114.csv` を 36件で生成（10ギャラリー×最大5exhibition、5/5済み除外）。
    - 実測結果: `seed=36`, `ge_1=28`, `ge_target=16`, `saved_images_total=103`。
    - 判定値: `ge_1率=0.7778`（通過）, 抽出0件ギャラリー=1, hero/profile/logo混入=0, 重複(URL/payload)=0/0。
    - 運用整形: 実行後CSVを「未達のみ20件」に縮約して再抽出対象を最小化。
    - guard/R2: `guard_passed=true`、derived同期 `uploaded=146 / pruned=0 / failed=0`。
[x] 115) Exhibitions Text RAG の SSOT逸脱を一括是正し、監査7項目＋現状症状を回帰なしで再確定する（T-115完了）
    - 監査Before/Afterで `対象年外混入=0`、`source_url重複=0`、`date/headline/summary` の充足改善を確認。
    - `run_phase1_seed10.py` に Exhibitions Text 共通ユーティリティ適用（URL正規化、対象年判定、日付抽出、participating artists、sources永続化、manifest最小同期）。
    - `run_enrichment_seed10_apply.py` と `run_phase1_exhibitions_text_raw_cleanup.py` を導入し、既存raw症状（重複/年外混入）を補正。
    - guard/R2: `guard_passed=true`、raw/derived とも `dry-run -> guarded apply` を実施。
[x] 116) Exhibitions画像の未達20件のみ再抽出し、0件ギャラリーの解消と ge_target率の改善可否を確定する（本体前進）
    - 実測結果（T-116 MAX7）: `seed_exhibition_count=49` / `ge_1=37` / `ge_target=37` / `saved_images_total=37`
    - 成功率: `success_rate_ge_1=0.755102` / `success_rate_ge_target=0.755102`
    - 失敗内訳: `insufficient_image_candidates_after_download=11`, `target_year_signal_missing=1`（計12件）
    - 補足: `MAX7` は「各ギャラリーの上限」であり、全ギャラリーで7展示が必ず取得できる意味ではない

[x] 117) T-118D YEAR_BUCKET_WIRING を反映し、Exhibitions detail year bucket の target_year 判定停滞を解消する（本体前進）
    - 根因: `int(page.get("year_bucket") or 2)` で `0(target_year)` が falsy 扱いされ non-target に潰れていた
    - 実測: Adams `2025 0 -> 12` / Arcadia `2025 0 -> 8` / Anca `2025 0 -> 4`
    - triage: `data/phase1_seed10/logs/debug_exhibitions_listing_triage_20260302T093256Z.json`
[x] 118) T-118E TRIAGE_NORMALIZE を反映し、debug-gallery-triage の表記ゆれ耐性を安定化する（本体前進）
    - 実装: `NFKC + strip + 連続空白正規化`（比較処理のみ）
    - 方針: `gallery_name_en` の保存値自体は変更しない
    - triage: `data/phase1_seed10/logs/debug_exhibitions_listing_triage_20260302T094558Z.json`
[x] 119) T-120 TWO_DIGIT_YEAR_SIGNAL を反映し、2桁年日付の target-year 取りこぼしを是正する（本体前進）
    - 実装: `phase1_exhibitions_text_utils.py` に2桁年 helper を追加し、日付文脈末尾の `25` のみ signal 化
    - 実測: The Approach `target_year 0 / non-target 32 -> target_year 32 / non-target 0`
    - triage: `data/phase1_seed10/logs/debug_exhibitions_listing_triage_20260302T102354Z.json`
[x] 120) 10ギャラリー Exhibitions画像の under-target CSV を再評価し、A/B/C/D（再抽出不要/改善余地/重点監視/自然収束）で再分類する（最優先）
[x] 121) （最優先） under-target 再抽出対象を再確定し、不要な再抽出（A群/D群）を除外した targets CSV を再生成する
[x] 122) （最優先） 必要最小限で under-target のみ再実行し、ge_1/ge_target/new_saved を再判定する（full rerun 禁止）
[HOLD] 123) （低優先 / housekeeping） gallery_name_en 文字化けの保存値修正方針を整理し、実施条件を明記する
[x] 124) （最優先） Exhibitions画像 under-target フェーズの close判定を確定し、次フェーズ（Exhibitions Text再開可否）へ移行条件を決める
[HOLD] 125) （最優先） Exhibitions Text 再開の最小スコープ（1フェア×1ギャラリー×最小件数）を確定し、画像フェーズとの非干渉ゲートを定義する

========================
BACKLOG（後回し/保留）
========================
[HOLD] 旧TASK 17) 数値ウォッチ項目を設定ファイル化する（compare guardの運用固定）
    - 目的：`700/180` などのウォッチ数値をコード直書きから外し、運用で更新可能にする
    - 参照：run_compare_tarutani_answers.py
    - 保留理由：優先順位見直しにより、Tarutani側は一旦保守モードとして後回し。Phase1本体（Exhibitions/Artist）を先行する。
    - 再開条件：Phase1本体の共通ガード最小版（Exhibitions/Artist向け）が成立した後
    - メモ：価値があるため削除せず保留


========================
CODEX_TASK_PROMPTS（コピペでCodexに渡す指示文）
========================
使い方：
- NEXT_TASKS の番号に対応するプロンプトを、そのままCodexに貼るだけ。
- Codexはタスク完了時に「次のTASK n のプロンプト全文」を必ず提示する（Bスニペットで強制）。
- 大きな変更の前は「まず計画だけ。実装はその後。」を追加してOK。
- 以後のTASKプロンプトは、下記テンプレ（`運用ルールは前回と同じ...` / `RECOMMENDED_MODE` / 章ID明示 / 固定出力5項目）に必ず準拠する。

------------------------------------------------------------
TASK 190) HUNDREDS-OF-GALLERIES-STANDARD-FLOW-CONCRETIZATION（最優先）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
今回は TASK190 のみを行ってください。
目的は、10ギャラリーで確立した anti-mixing 運用を hundreds of galleries 向けに標準化すること。
Keep-Current / Safe-But-Provenance-Gated / Guard-First の3分類条件、各レーンの入出力、trial->QA->adoption基準を固定する。
03/04/01/02更新・コード変更・rerunは行わない（設計のみ）。

------------------------------------------------------------
TASK 189) 03/04 FINAL SYNC EXECUTION（実施済み）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
03を「現在地/次アクション中心」、04を「milestone block方式」で最終同期し、10ギャラリー正式状態を文書に反映済み。

------------------------------------------------------------
TASK 182) 03/04 DOC SYNC EXECUTION（実施済み）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
TASK181設計を反映し、03/04の現在地同期を完了（01/02更新なし、コード変更なし、rerunなし）。

------------------------------------------------------------
TASK 117) T-118D YEAR_BUCKET_WIRING（実施済み）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
T-118D の year_bucket wiring 修正結果（Adams/Arcadia/Anca の 2025 件数改善）を 03/04/RAG に反映し、再発防止メモを追記する。

------------------------------------------------------------
TASK 118) T-118E TRIAGE_NORMALIZE（実施済み）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
debug-gallery-triage の NFKC/strip/空白正規化適用結果を 03/04/RAG に反映し、gallery_name_en 保存値は未変更であることを明記する。

------------------------------------------------------------
TASK 119) T-120 TWO_DIGIT_YEAR_SIGNAL（実施済み）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
2桁年日付シグナル追加の結果（The Approach の改善、既存3ギャラリー悪化なし）を 03/04/RAG に反映する。

------------------------------------------------------------
TASK 120) EXHIBITIONS-UNDER-TARGET-REEVAL
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
10ギャラリーの Exhibitions画像現状を A/B/C/D に再分類し、under-target の再評価表を作成する（実行なし）。

------------------------------------------------------------
TASK 121) EXHIBITIONS-TARGETS-RECERT
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
A群/D群を除外し、B群/C群のみを再抽出対象にした targets CSV を再生成する（実行なし）。

------------------------------------------------------------
TASK 122) EXHIBITIONS-UNDER-TARGET-RERUN
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
under-target 対象のみ再実行し、ge_1/ge_target/new_saved/existing_hit_only を再判定する（full rerun 禁止）。

------------------------------------------------------------
TASK 123) HOUSEKEEPING-GALLERY-NAME-ENCODING
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
gallery_name_en 文字化けの保存値修正方針を低優先 housekeeping として整理し、実施条件を定義する。

------------------------------------------------------------
TASK 124) EXHIBITIONS-IMAGE-UNDER-TARGET-CLOSE-GATE
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
T120/T121/T122 の結果を確定値として、under-target フェーズを close するか継続監視にするかを判定し、次フェーズ（Exhibitions Text）へ移行可能条件を明文化する。
------------------------------------------------------------
TASK 125) EXHIBITIONS-TEXT-RESTART-BOOTSTRAP
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
Exhibitions画像フェーズ（T124 close）を前提に、Exhibitions Text を最小スコープで再開する実行条件を確定し、非干渉ゲートを確認する。
------------------------------------------------------------
TASK 107) 10ギャラリー Artistsテキスト抽出（共通スキップ + 共通R2同期）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。 

RECOMMENDED_MODE: high

TASK T-107-ARTISTS-TEXT) 10ギャラリーのArtistsテキスト抽出を実行し、共通スキップ運用と共通R2同期運用を確認する

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-0-A) 既知URL/既知画像の“記憶”と自動スキップ（必須）
  - 4-2) Artist：Text（抽出ルール）
  - 5-3) Artist Text（4-2の成果物）
  - 5-8) 同期方式（R2正本 + local cache）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
- 02（DERIVED）
  - CARD_ID: 05_MANIFEST_SYNC
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT（運用比較参照）
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- run_phase1_seed10.py
- run_r2_sync.py
- run_compare_phase1_guard.py
- data/gallery_lists/skipped_galleries_registry.csv
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実行手順（固定）】
1) 実装前存在確認（本体実行はまだしない）
- docs/01_PROJECT_SPEC_CURRENT_FULL.docx
- docs/02_RAG_SPEC_DERIVED.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

2) preflight 2回（PASS必須）
- python run_phase1_network_preflight.py
- python run_phase1_network_preflight.py

3) 共通スキップ運用の事前確認（分析のみ）
- skipped_galleries_registry.csv の登録galleryが、Artistsテキスト抽出対象から除外される前提を確認する

4) seed10 Artistsテキスト抽出を実行（初回最小スコープ。成功済み画像は触らない）
- python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 1

5) guard確認
- python run_compare_phase1_guard.py --target-year 2025

6) R2同期確認（共通ルール）
- 自動同期ログを確認し、必要時のみ手動で dry-run -> guarded apply を実行
- 例:
  - python run_r2_sync.py plan --scope phase1_seed10_formal --run-id <RUN_ID>
  - python run_r2_sync.py apply-upload --scope phase1_seed10_formal --apply --run-id <RUN_ID>
  - python run_r2_sync.py apply-prune --scope phase1_seed10_formal --apply --run-id <RUN_ID> --confirm-prune --max-prune 600

7) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- 10ギャラリー対象で Artistsテキスト抽出が完了（skip登録galleryは除外）
- summary/guard/R2同期ログで共通運用（skip + R2）が確認できる
- 03/04/RAG の記録が整合して更新済み

【タスク終了時に行うこと】
①03の更新
- 03更新は必ず 02→01→03 の順で行う
- 03 の STATE_SNAPSHOT / NEXT_TASKS（終わったら [x]）/ CHANGELOG / LAST_UPDATED を更新する
②報告フォーマットの出力
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 「次のタスクのプロンプト全文」を1つのコードブロックで添付する

TASK 108) 10ギャラリー Artistsテキスト完了ゲート（Exhibitions着手前）
------------------------------------------------------------
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。 

RECOMMENDED_MODE: high

TASK T-108-ARTISTS-TEXT-CLOSE-1) 10ギャラリーのArtistsテキスト抽出を完了ゲートまで実施し、未達要因を確定してから次カテゴリへ進む

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①～④共通ルール
  - 4-0-A) 既知URL/既知画像の“記憶”と自動スキップ（必須）
  - 4-2) Artist：Text（抽出ルール）
  - 5-3) Artist Text（4-2の成果物）
  - 5-8) 同期方式（R2正本 + local cache）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
- 02（DERIVED）
  - CARD_ID: 05_MANIFEST_SYNC
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT（運用比較参照）
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- run_phase1_seed10.py
- run_r2_sync.py
- run_compare_phase1_guard.py
- data/gallery_lists/skipped_galleries_registry.csv
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実行手順（固定）】
1) 実装前存在確認（本体実行はまだしない）
- docs/01_PROJECT_SPEC_CURRENT_FULL.docx
- docs/02_RAG_SPEC_DERIVED.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

2) preflight 2回（PASS必須）
- python run_phase1_network_preflight.py
- python run_phase1_network_preflight.py

3) 段階実行（Artistsテキスト）
- Step-A: `--max-artists-per-gallery 1` で実行し、保存/スキップ内訳を確認
- Step-B: `--max-artists-per-gallery 3` で実行し、新規追加の有無を確認
- Step-C: `--max-artists-per-gallery 80` で実行し、完了ゲート判定する
- 既存成功データは削除しない

4) guard確認
- python run_compare_phase1_guard.py --target-year 2025

5) R2同期確認（共通ルール）
- 自動同期ログを確認し、必要時のみ手動で dry-run -> guarded apply を実行

6) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- Artistsテキストを段階実行し、最終（max=80）で追加有無の判定が完了
- 未達が残る場合は理由コードを確定して 03/04/RAG に明記
- summary/guard/R2同期ログで共通運用（skip + R2）が確認できる
- 03/04/RAG の記録が整合して更新済み

【タスク終了時に行うこと】
①03の更新
- 03更新は必ず 02→01→03 の順で行う
- 03 の STATE_SNAPSHOT / NEXT_TASKS（終わったら [x]）/ CHANGELOG / LAST_UPDATED を更新する
②報告フォーマットの出力
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 「次のタスクのプロンプト全文」を1つのコードブロックで添付する

------------------------------------------------------------
TASK 1) ギャラリーCSVを配置してコミット（完了済み・参照用）
------------------------------------------------------------
目的：
- ギャラリーリスト（全件）を repo に配置し、Phase1の入力として確定させる。

参照ファイル：
- data/gallery_lists/gallery_list_frieze_london.csv（95件）
- data/gallery_lists/gallery_list_liste.csv（52件）
- 03_STATE_SNAPSHOT_NEXT_TASKS.md（NEXT_TASKS）

完了条件：
- data/gallery_lists/ に2ファイルが存在し、git status がクリーン（コミット済み）
- 03 の NEXT_TASKS の 1) を [x] にして、CHANGELOGに1行追記

動作確認コマンド：
- （WSL）git log -1 --oneline -- data/gallery_lists/
- （WSL）ls -l data/gallery_lists/

------------------------------------------------------------
TASK 2) 02_RAG_SPEC_DERIVED.md（カード集）を生成する
------------------------------------------------------------
目的：
- 01（SSOT）を元に、RAG抽出・保存ルールを “カテゴリ別カード” に整理し、Codex/LLMが参照しやすくする。

参照ファイル：
- 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）
- 03_STATE_SNAPSHOT_NEXT_TASKS.md（この03）

制約：
- 02は索引。衝突したら必ず01が正。
- まずは Phase1 に必要な範囲（4-0共通 / 4-1 Exhibitions Text）だけでOK。
- 01の内容を勝手に変えない（変更が必要ならユーザー合意）。

完了条件：
- 02_RAG_SPEC_DERIVED.md が repo に存在し、最低限「4-0共通」「4-1 Exhibitions Text」のカードがある
- 03 の NEXT_TASKS の 2) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 3）のプロンプト全文を提示する

動作確認（確認方法）：
- （WSL）ls -l 02_RAG_SPEC_DERIVED.md
- （目視）4-0 / 4-1 のカードがあること

------------------------------------------------------------
TASK 3) Phase1 seed10 の最小実行入口 run_phase1_seed10.py を作る
------------------------------------------------------------
目的：
- seed10（Frieze先頭5 + Liste先頭5）で「取得→保存」が走る入口を作る。

参照ファイル：
- 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）
- 02_RAG_SPEC_DERIVED.md（索引）
- data/gallery_lists/*.csv
- 03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- まずは 4-1 Exhibitions Text だけでOK（他カテゴリは後回し）。
- 取得ループ内で LLM加工（headline_ja 等）を逐次実行しない（Fetch/Enrichment分離）。
- ドメイン専用ハードコード増殖禁止。取れない分はログ化して割り切る。

完了条件：
- python run_phase1_seed10.py が実行でき、ログに「開始→完了」が出る
- 何らかの成果物（保存ファイル）が生成される
- 03 の NEXT_TASKS の 3) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 4）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py

------------------------------------------------------------
TASK 4) 4-1 Exhibitions Text で「取得→保存→再実行でスキップ」を成立させる
------------------------------------------------------------
目的：
- 同じコマンドを2回実行したときに、2回目は“自動スキップ”が効く状態を作る。

参照ファイル：
- run_phase1_seed10.py（入口）
- 01（SSOT）4-0 / 4-1
- 02（索引）該当カード
- 生成物と台帳

制約：
- 重複で「新規レコード量産」事故を起こさない
- 失敗は握りつぶさずログに残す
- 機能削除/無効化はしない

完了条件：
- 1回目：取得→保存→完走（失敗があってもログ化され、止まらずに前進できる）
- 2回目：同じコマンドで、多くがスキップされるログが出る
- 03 の NEXT_TASKS の 4) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 5）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py
- （WSL）python run_phase1_seed10.py

------------------------------------------------------------
TASK 5) 台帳とログを整備して「失敗を割り切って前進」できる状態にする
------------------------------------------------------------
目的：
- 429/403/タイムアウト等が出ても、無限ループせず、失敗一覧が残り、再実行で前進できるようにする。

参照ファイル：
- 01（SSOT）4-0
- 02（索引）4-0カード
- 現状の台帳/ログ出力

制約：
- 頻出ドメイン×汎用ロジックのみ改善。個別ドメイン専用の分岐は増やさない
- 取れない分はログ化して割り切る

完了条件：
- failed_fetches 的な一覧が保存される（URL、理由、カテゴリ、時刻など最低限）
- 再実行で同じ失敗を無限に繰り返さない（打ち切り/スキップが効く）
- 03 の NEXT_TASKS の 5) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py

------------------------------------------------------------
TASK 6) Enrichment を「事後バッチ」で回す導線を作る（余力があれば）
------------------------------------------------------------
目的：
- Fetchと分離した“後処理バッチ”として、見出し/かな等のEnrichmentを回す入口を用意する。

参照ファイル：
- 01（SSOT）Post-fetch/Enrichment 方針
- 02（索引）該当カード
- 生成済みの raw 保存ファイル

制約：
- 取得ループ内で逐次Enrichmentしない
- まずは「入口だけ」でもOK（実処理は後で拡張可）

完了条件：
- python run_enrichment_seed10.py（例）が実行でき、対象ファイルを読み込める
- 03 の NEXT_TASKS の 6) を [x]（やった場合のみ）、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_enrichment_seed10.py

------------------------------------------------------------
TASK 7) Tarutani_Text（条件付き：Phase1が安定してから）
------------------------------------------------------------
目的：
- 機能⑤用の Tarutani_Text を取り込む（作品画像は扱わない）

参照ファイル：
- 01（SSOT）4-5 Tarutani_Text / 保存
- data_private/tarutani_text/（想定：Git管理外）

制約：
- 着手条件：Phase1 seed10 が「2回連続で完走」してから
  - 完走＝例外で落ちずに終了（exit 0）。failed_fetches が残るのはOK（ログ化されていればOK）
- 着手の最初に必ずユーザーへ質問する：
  「TarutaniRAG（文章データ）はどこに置いた？（パス）形式は？（ファイル種類/構成）」
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- 質問→ユーザー回答→取り込みの最小実行が通る
- 03 の NEXT_TASKS の 7) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_tarutani_text_import.py（例：作った場合）

------------------------------------------------------------
TASK 8) Tarutani_Text のPost-fetch Enrichment入口を作る
------------------------------------------------------------
目的：
- Tarutani_Text（tarutani_text.jsonl）に対する headline_ja 付与を、Fetch後の事後バッチで回す入口を作る。

参照ファイル：
- 01（SSOT）Post-fetch/Enrichment / 4-5 / 5-5
- 02（索引）CARD_ID: 08_POST_FETCH_ENRICHMENT / CARD_ID: 16_TARUTANI_TEXT_SCOPE
- data/Tarutani_data/tarutani_text.jsonl

制約：
- 取り込みループ内でLLM加工をしない（Fetch/Enrichment分離）
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_enrichment_tarutani_text.py（例）が実行できる
- 未付与headline_ja候補の requests/summary を生成できる
- 03 の NEXT_TASKS の 8) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_enrichment_tarutani_text.py

------------------------------------------------------------
TASK 9) Tarutani_Text のheadline_jaを事後バッチで実生成し、jsonlへ反映する
------------------------------------------------------------
目的：
- TASK 8 で生成した requests を使い、Tarutani_Text の headline_ja を Post-fetch バッチで付与する。

参照ファイル：
- 01（SSOT）Post-fetch/Enrichment / 4-5 / 5-5
- 02（索引）CARD_ID: 08_POST_FETCH_ENRICHMENT / CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_enrichment_tarutani_text.py
- data/Tarutani_data/enrichment/enrichment_requests_tarutani_text.jsonl
- data/Tarutani_data/tarutani_text.jsonl

制約：
- 取り込みループ内でLLM加工をしない（Fetch/Enrichment分離）
- 作品画像（Tarutani_Works）は扱わない
- text が空文字のレコードは headline_ja を空文字のまま維持する

完了条件：
- python run_enrichment_tarutani_text_apply.py（例）が実行できる
- headline_ja の生成結果（output jsonl等）を保存できる
- tarutani_text.jsonl の headline_ja を更新できる（更新件数が summary に出る）
- 03 の NEXT_TASKS の 9) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_enrichment_tarutani_text_apply.py

------------------------------------------------------------
TASK 9.5) TarutaniRAG向けPDF抽出を実装し、既存PDFをバックフィルする
------------------------------------------------------------
目的：
- TarutaniRAG（⑤）に限りPDF本文抽出を実装し、既存の text="" レコードをバックフィルして検索可能データを増やす。

参照ファイル：
- 01（SSOT）4-5 / 5-5 / Post-fetch
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE / CARD_ID: 08_POST_FETCH_ENRICHMENT
- run_tarutani_text_import.py
- data/Tarutani_data/tarutani_text.jsonl
- data/Tarutani_data/*/Text/*.pdf

制約：
- TarutaniRAGのみ対象（Exhibitions/Artist側のPDF処理は変えない）
- 取り込みループ内でLLM加工はしない（headline_jaはPost-fetch）
- OCRはしない（抽出不能PDFは text="" 維持 + extract_status に理由記録）

完了条件：
- python run_tarutani_text_pdf_backfill.py（例）が実行できる
- tarutani_text.jsonl の PDF由来レコードで text 非空件数が増える（増加件数をsummaryで確認）
- 抽出失敗レコードは text="" のまま、extract_status が更新される
- その後 python run_enrichment_tarutani_text.py / python run_enrichment_tarutani_text_apply.py を再実行し、headline_ja 更新件数を確認
- 03 の NEXT_TASKS の 9.5) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_tarutani_text_pdf_backfill.py
- （WSL）python run_enrichment_tarutani_text.py
- （WSL）python run_enrichment_tarutani_text_apply.py

------------------------------------------------------------
TASK 10) Tarutani_Text のEmbedding/Index入口を作る
------------------------------------------------------------
目的：
- headline_ja 付与済み tarutani_text.jsonl を対象に、Embeddingと検索用Indexの生成入口を作る。

参照ファイル：
- 01（SSOT）5-5 / 5-8 / 5-9 / Post-fetch/Enrichment
- 02（索引）CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 16_TARUTANI_TEXT_SCOPE
- data/Tarutani_data/tarutani_text.jsonl

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- text が空文字のレコードは埋め込み対象外としてスキップし、件数をログ化する
- 作品画像（Tarutani_Works）は扱わない
- TarutaniRAGは「先頭2000字1本」ではなく、1000字チャンク（200字オーバーラップ）で複数埋め込みする

完了条件：
- python run_vectorize_tarutani_text.py（例）が実行できる
- embedding入力件数 / skip件数 / 出力先が summary に保存される
- index + meta の生成物が保存される
- 03 の NEXT_TASKS の 10) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_vectorize_tarutani_text.py

------------------------------------------------------------
TASK X) SSOT追記：埋め込み入力メタ3項目の明文化（完了済み・参照用）
------------------------------------------------------------
目的：
- 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）に、埋め込み時の保存メタ text_len / embed_input_len / is_truncated を明記する。

参照ファイル：
- 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）
- 02_RAG_SPEC_DERIVED.md（索引）
- 03_STATE_SNAPSHOT_NEXT_TASKS.md

完了条件：
- 01の5-9近傍に、上記3項目の保存メタが明記される
- 必要に応じて02の該当カードを01準拠で更新する
- 03の該当タスクを [x] にし、CHANGELOGに1行追記する

動作確認コマンド（実装反映時）：
- （WSL）python run_vectorize_tarutani_text.py

------------------------------------------------------------
TASK 11) Tarutani_Text の検索スモークCLIを作る（chunk index検証）
------------------------------------------------------------
目的：
- TASK10で生成した Tarutani_Text の index+meta を使って、クエリ検索（top-k）の最小CLIを成立させる。

参照ファイル：
- 01（SSOT）5-8 / 5-9 / 機能⑤（Tarutani_Textの扱い）
- 02（索引）CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_vectorize_tarutani_text.py
- data/Tarutani_data/vector/tarutani_text_index.npy
- data/Tarutani_data/vector/tarutani_text_meta.jsonl

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- クエリ埋め込みは RETRIEVAL_QUERY（Gemini, 1536次元, L2正規化）で統一する
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_search_tarutani_text.py --query "..." が実行できる
- top-k の source_path / chunk_index / score を出力できる
- 検索summary（query, k, output paths）が保存される
- 03 の NEXT_TASKS の 11) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_search_tarutani_text.py --query "曲線と直線"

------------------------------------------------------------
TASK 12) Tarutani_Text 検索結果を機能⑤向けコンテキストJSONに整形する
------------------------------------------------------------
目的：
- TASK11の検索結果（top-k）を、機能⑤でそのまま投入できるコンテキストJSONへ整形する。

参照ファイル：
- 01（SSOT）機能⑤（Tarutani_Textの使い方） / 5-8 / 5-9
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE / CARD_ID: 05_MANIFEST_SYNC
- run_search_tarutani_text.py
- data/Tarutani_data/vector/tarutani_text_meta.jsonl
- data/Tarutani_data/tarutani_text.jsonl

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- 作品画像（Tarutani_Works）は扱わない
- 既存の検索スコア計算（TASK11）を壊さない

完了条件：
- python run_build_tarutani_context.py --query "..." が実行できる
- source_path / chunk_index / score / excerpt を含む context JSON が保存される
- 03 の NEXT_TASKS の 12) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_build_tarutani_context.py --query "曲線と直線"

------------------------------------------------------------
TASK 13) 機能⑤向け回答スモークCLIを作る（Tarutani context利用）
------------------------------------------------------------
目的：
- TASK12で生成した context JSON を使って、機能⑤の回答（根拠付き）をCLIで出力する。

参照ファイル：
- 01（SSOT）機能⑤（Tarutani_Textの使い方） / 5-8 / 5-9
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_build_tarutani_context.py
- data/Tarutani_data/context/tarutani_text_context_*.json

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- Tarutani_Text は検索結果一覧に混ぜない（回答の根拠セクションとしてのみ使う）
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_answer_tarutani_advisor.py --question "..." --query "..." が実行できる
- 回答本文 + 根拠（source_path / chunk_index / score / excerpt）を output JSON に保存できる
- 03 の NEXT_TASKS の 13) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_answer_tarutani_advisor.py --question "曲線と直線の要点を教えて" --query "曲線と直線"

------------------------------------------------------------
TASK 14) 機能⑤回答CLIに再現モード（context固定入力）を追加する
------------------------------------------------------------
目的：
- 既存の context JSON を直接指定し、検索/再生成を省いた回答再現モードを追加する。

参照ファイル：
- 01（SSOT）機能⑤（Tarutani_Textの使い方）
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_answer_tarutani_advisor.py
- data/Tarutani_data/context/tarutani_text_context_*.json

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- Tarutani_Text は検索結果一覧に混ぜない（回答の根拠セクションとしてのみ使う）
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_answer_tarutani_advisor.py --question "..." --context-path "..." が実行できる
- query指定モードと context固定モードの実行区別が summary に保存される
- 03 の NEXT_TASKS の 14) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_answer_tarutani_advisor.py --question "曲線と直線の要点を教えて" --context-path "data/Tarutani_data/context/tarutani_text_context_YYYYMMDDTHHMMSSZ.json"

------------------------------------------------------------
TASK 15) 機能⑤回答の比較レポートCLIを作る（query再生成 vs context固定）
------------------------------------------------------------
目的：
- query再生成モードと context固定モードの回答差分を1回で確認できる比較CLIを追加する。

参照ファイル：
- 01（SSOT）機能⑤（Tarutani_Textの使い方）
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_answer_tarutani_advisor.py
- data/Tarutani_data/context/tarutani_text_context_*.json
- data/Tarutani_data/answers/tarutani_advisor_answer_*.json

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- Tarutani_Text は検索結果一覧に混ぜない（回答の根拠セクションとしてのみ使う）
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_compare_tarutani_answers.py --question "..." --query "..." --context-path "..." が実行できる
- 回答本文長・根拠件数・主要数値（例：700/180）の比較サマリJSONを保存できる
- 03 の NEXT_TASKS の 15) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_tarutani_answers.py --question "曲線と直線の要点を教えて" --query "曲線と直線" --context-path "data/Tarutani_data/context/tarutani_text_context_YYYYMMDDTHHMMSSZ.json"

------------------------------------------------------------
TASK 16) 機能⑤回答に差分ガードを追加する（数値競合アラート）
------------------------------------------------------------
目的：
- 比較CLIにガード機能を追加し、主要数値の不一致をCI/手元で自動検知できるようにする。

参照ファイル：
- 01（SSOT）機能⑤（Tarutani_Textの使い方）
- 02（索引）CARD_ID: 16_TARUTANI_TEXT_SCOPE
- run_compare_tarutani_answers.py
- data/Tarutani_data/answers/tarutani_advisor_answer_compare_*.json

制約：
- 取り込みループ内で実行しない（Post-fetchバッチとして分離）
- Tarutani_Text は検索結果一覧に混ぜない（回答の根拠セクションとしてのみ使う）
- 作品画像（Tarutani_Works）は扱わない

完了条件：
- python run_compare_tarutani_answers.py ... --fail-on-mismatch が実行できる
- 主要数値差分がある場合は非0終了、差分なしなら0終了になる
- summary に `guard_passed` / `mismatch_fields` が保存される
- 03 の NEXT_TASKS の 16) を [x]、CHANGELOG追記
- 次の最優先タスクのプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_tarutani_answers.py --question "曲線と直線の要点を教えて" --query "曲線と直線" --context-path "data/Tarutani_data/context/tarutani_text_context_YYYYMMDDTHHMMSSZ.json" --fail-on-mismatch

------------------------------------------------------------
TASK 17) Phase1本体へ復帰：Tarutaniで作った比較ガードの“型”をExhibitions/Artistへ横展開する準備をする
------------------------------------------------------------
目的：
- Tarutani_Text で作った比較CLI/差分ガード（再現モード・比較・guard）の実績を、Phase1本体（Exhibitions/Artist）へ転用できるように“共通の見張り項目”を整理する。
- Tarutani側の追加深掘りではなく、本体優先で前進する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists（共通方針・保存・ログ）
- 02（索引）共通保存方針・manifest・ログ関連カード
- run_phase1_seed10.py
- （あれば）run_summary_seed10_2025.json / manifest / visited_pages / failed_fetches
- run_compare_tarutani_answers.py（比較ガードの“型”の参照用）

制約：
- 取り込みループ内でLLM加工しない（Post-fetch分離を維持）
- ドメイン専用ハードコードを増やさない
- Tarutani_Text は今回は“参照実装”として扱い、Tarutani側の新機能追加はしない（保守のみ）

完了条件：
- Exhibitions/Artists に横展開するための「共通ガード項目」を明文化できる（例：必須キー存在、内部整合、件数サマリ整合、manifest/台帳整合）
- 次タスクで実装する対象CLI（または新規CLI名）と、最小実装範囲（どのJSON/manifestを比較するか）を決められる
- 03 の NEXT_TASKS の 17) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 18）のプロンプト全文を提示する
  ※ TASK 18 は「Exhibitions/Artists向け比較CLI + guard最小版の実装」にする

動作確認コマンド：
- （今回は文面整理のみのため実行コマンド不要）

------------------------------------------------------------
TASK 18) Exhibitions/Artists向け比較CLI + guard最小版を実装する
------------------------------------------------------------
目的：
- TASK17で確定した共通ガード項目（G1〜G4）を、Phase1本体（Exhibitions/Artists）で再利用できる検証CLIとして実装する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-1 / 5-3 / 5-8
- 02（索引）CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT
- run_phase1_seed10.py
- data/phase1_seed10/logs/run_summary_seed10_2025.json
- data/phase1_seed10/logs/visited_pages_seed10_2025.json
- data/phase1_seed10/logs/failed_fetches_seed10_2025.json
- data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl
- data/phase1_seed10/raw/exhibitions_liste_2025.jsonl
- （任意）artifact_manifest.json

制約：
- 取り込みループ内で実行しない（Post-fetchの検証CLIとして分離）
- ドメイン専用ハードコードを増やさない
- failed_fetches が存在するだけでは失敗扱いにしない（ログ化して前進の方針を維持）
- Tarutani側の新機能追加はしない（参照のみ）

完了条件：
- `python run_compare_phase1_guard.py --target-year 2025` が実行できる
- summary に `guard_passed` / `mismatch_fields` / `check_results` / `input_paths` が保存される
- 最低限の検査を実装する
  - 必須キー存在チェック（run_summary）
  - 内部整合チェック（合計一致）
  - summary と ledger/manifest の整合チェック
  - failed_fetches の「失敗しても前進する運用」を壊さないチェック
- `--fail-on-mismatch` 指定時のみ非0終了、差分なしは0終了
- 03 の NEXT_TASKS の 18) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 19）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --fail-on-mismatch

------------------------------------------------------------
TASK 19) Phase1 guardの回帰比較CLIを追加する（前回runとの比較）
------------------------------------------------------------
目的：
- TASK18で生成した guard summary を2本比較し、Phase1本体（Exhibitions/Artists）の悪化を自動検知できるようにする。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-1 / 5-3 / 5-8
- 02（索引）CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT
- run_compare_phase1_guard.py
- data/phase1_seed10/logs/phase1_guard_summary_*.json
- data/phase1_seed10/logs/run_summary_seed10_2025.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- ドメイン専用ハードコードを増やさない
- failed_fetches が増減した事実は比較に含めるが、「存在するだけ」で失敗扱いにはしない
- Tarutani側の新機能追加はしない（参照のみ）

完了条件：
- `python run_compare_phase1_guard_history.py --current-summary \"...\" --baseline-summary \"...\"` が実行できる
- 回帰比較summaryに以下を保存できる
  - `guard_passed_current / guard_passed_baseline`
  - `delta_records_saved_total / delta_skipped_total / delta_failed_fetches_total_ledger / delta_visited_pages_total_ledger`
  - `new_mismatch_fields / resolved_mismatch_fields`
- `--fail-on-regression` 指定時のみ回帰で非0終了、回帰なしは0終了
- 03 の NEXT_TASKS の 19) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 20）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --baseline-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --baseline-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --fail-on-regression

------------------------------------------------------------
TASK 20) Phase1 guard比較の運用化（baseline自動解決 + CI向け終了コード整理）
------------------------------------------------------------
目的：
- TASK19で実装した回帰比較CLIの運用負荷を下げ、baseline指定ミスを減らしてCIで安定運用できる状態にする。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 14_CATEGORY_4_0_COMMON
- run_compare_phase1_guard_history.py
- data/phase1_seed10/logs/phase1_guard_history_compare_*.json
- data/phase1_seed10/logs/phase1_guard_summary_*.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- ドメイン専用ハードコードを増やさない
- failed_fetches の存在のみで失敗扱いにしない（TASK18/19方針を維持）
- Tarutani側の新機能追加はしない

完了条件：
- baseline未指定時、`target_year` と互換条件（生成元CLI等）を満たす最新summaryを自動選択できる
- `--strict-compatibility` を追加し、比較不成立を常に非0終了にできる
- summary に `baseline_resolution_mode` / `baseline_selected_reason` / `baseline_candidates_checked` を保存できる
- exit code の意味（0=pass,2=regression,3=incompatible）をCLI出力とsummaryで明示できる
- 03 の NEXT_TASKS の 20) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 21）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --strict-compatibility

------------------------------------------------------------
TASK 21) Phase1 guardをseed10以外へ拡張する準備（入力パス/年/カテゴリの汎化点整理）
------------------------------------------------------------
目的：
- Phase1 guard系CLIを seed10 固定運用から段階的に汎化するため、入力パス・対象年・カテゴリの設計ポイントを先に整理する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-1 / 5-3 / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- run_phase1_seed10.py
- data/phase1_seed10/logs/run_summary_seed10_2025.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- ドメイン専用ハードコードを増やさない
- 既存のseed10運用をデフォルト互換として維持する（破壊的変更をしない）
- Tarutani側の新機能追加はしない

完了条件：
- seed10固定箇所（パス文字列、ファイル命名、年固定、カテゴリ前提）を棚卸しし、汎化対象を一覧化できる
- 最小CLI仕様案（例：`--logs-dir` / `--target-year` / `--summary-path` / `--category`）を定義できる
- 互換維持方針（引数未指定時は現行seed10挙動）を明記できる
- 実装に進む場合の最小差分計画（どのファイルをどう変えるか）を提示できる
- 03 の NEXT_TASKS の 21) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 22）のプロンプト全文を提示する

動作確認コマンド：
- （今回は設計整理中心のため実行コマンドは任意）

------------------------------------------------------------
TASK 22) Phase1 guard本体のパス/年汎化を実装する（seed10互換維持）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py` の seed10 固定依存（logs-dir / 既定ファイル名）を最小差分で汎化し、非seed10 runにも流用できる状態にする。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- run_phase1_seed10.py
- data/phase1_seed10/logs/run_summary_seed10_2025.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- 既存の seed10 既定挙動を壊さない（引数未指定時は現行互換）
- failed_fetches は「存在しただけ」で失敗扱いにしない方針を維持
- Tarutani側の新機能追加はしない

完了条件：
- `run_compare_phase1_guard.py` に `--logs-dir` を追加できる（既定：`data/phase1_seed10/logs`）
- `--summary-path` 未指定時の既定解決が `--logs-dir` 基準になる
- `visited_pages_path` / `failed_fetches_path` / `output_files` の既定解決も `--logs-dir` 基準で破綻しない
- summary に `logs_dir` / `category`（既定 `exhibitions_text`）を保存できる
- 既存コマンド（`--target-year 2025`）は従来どおり成功する
- 03 の NEXT_TASKS の 22) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 23）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --logs-dir "data/phase1_seed10/logs"
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --logs-dir "data/phase1_seed10/logs" --fail-on-mismatch

------------------------------------------------------------
TASK 23) Phase1 guard history比較のパス/探索汎化を実装する（seed10互換維持）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard_history.py` の baseline探索を seed10 固定前提から外し、`current-summary` の場所に追従して他runにも流用できるようにする。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING
- run_compare_phase1_guard_history.py
- run_compare_phase1_guard.py
- data/phase1_seed10/logs/phase1_guard_summary_*.json
- data/phase1_seed10/logs/phase1_guard_history_compare_*.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- 既存の seed10 既定挙動を壊さない（引数未指定時は現行互換）
- `--fail-on-regression` / `--strict-compatibility` の終了コード規約（0=pass, 2=regression, 3=incompatible）を維持する
- failed_fetches は「存在しただけ」で失敗扱いにしない方針を維持
- Tarutani側の新機能追加はしない

完了条件：
- `--baseline-search-dir` 未指定時、`--current-summary` の親ディレクトリを既定探索先として使える
- 候補探索globをCLIで指定できる（例：`--summary-glob`、既定は `phase1_guard_summary_*.json`）
- auto baseline解決時の情報（`baseline_auto_search_dir` / `baseline_candidates_checked` / `baseline_resolution_mode` / `baseline_selected_reason`）を summary に保存できる
- 既存の手動指定モード（`--baseline-summary`）は従来どおり動作する
- 03 の NEXT_TASKS の 23) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 24）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --baseline-search-dir "data/phase1_seed10/logs" --summary-glob "phase1_guard_summary_*.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --strict-compatibility

------------------------------------------------------------
TASK 24) Phase1 guard CLIの共通関数化（path解決/summary保存）を最小実装する
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py` と `run_compare_phase1_guard_history.py` で重複している処理（パス正規化・タイムスタンプ付きsummary出力・終了コード説明）を最小差分で共通化し、今後の汎化タスクでの変更点を減らす。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- （新規）phase1_guard_common.py（必要なら）
- data/phase1_seed10/logs/phase1_guard_summary_*.json
- data/phase1_seed10/logs/phase1_guard_history_compare_*.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- 機能追加より保守性優先（挙動変更は最小）
- 既存CLI引数・既存summary項目・終了コード規約（0=pass, 2=regression, 3=incompatible）を壊さない
- failed_fetches は「存在しただけ」で失敗扱いにしない方針を維持
- Tarutani側の新機能追加はしない

完了条件：
- 共通化対象を最小2点以上切り出せる（例：`write_json`/`utc_now_iso`/output path helper）
- 両CLIの既存コマンド（TASK22/TASK23で使ったコマンド）が従来どおり成功する
- summaryの主要キー互換（既存キーが消えていない）を確認できる
- 03 の NEXT_TASKS の 24) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 25）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_regression_fixture.json" --baseline-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --fail-on-regression

------------------------------------------------------------
TASK 25) Phase1 guard系CLIの共通fixture/テストデータ整理（回帰/非互換の再現性向上）
------------------------------------------------------------
目的：
- 安全側（機能追加なし）を優先し、`run_compare_phase1_guard.py` / `run_compare_phase1_guard_history.py` の回帰判定・比較不成立判定を、毎回同じ入力で再現できるfixture運用を整備する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- data/phase1_seed10/logs/phase1_guard_summary_*.json
- （新規候補）tests/fixtures/phase1_guard/ または data/phase1_seed10/logs/fixtures/

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- CLI本体ロジックは変更しない（fixture整理・実行手順・確認スクリプト中心）
- 既存終了コード規約（0=pass,2=regression,3=incompatible）を維持
- Tarutani側の新機能追加はしない

完了条件：
- 最低3ケースのfixtureを明示できる（pass / regression / incompatible）
- 各ケースで「入力ファイル」「実行コマンド」「期待exit code」を一覧化できる
- 可能なら `run_guard_smoke_matrix.sh`（または同等）で一括実行できる
- 03 の NEXT_TASKS の 25) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 26）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard_history.py --current-summary "<pass_case_current_summary>"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "<regression_case_current>" --baseline-summary "<regression_case_baseline>" --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary "<incompatible_case_current>" --baseline-summary "<incompatible_case_baseline>" --strict-compatibility

------------------------------------------------------------
TASK 26) Phase1 guard本体のsummary/ledger見張り項目を最小強化する（安全側）
------------------------------------------------------------
目的：
- 新しいカテゴリ分岐を増やす前に、`run_compare_phase1_guard.py` の既存整合チェックを1段だけ強化し、回帰検知の抜け漏れを減らす。
- 機能追加より保守性優先で、既存挙動（seed10互換・終了コード）を維持する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_phase1_seed10.py
- data/phase1_seed10/logs/run_summary_seed10_2025.json
- data/phase1_seed10/logs/visited_pages_seed10_2025.json
- data/phase1_seed10/logs/failed_fetches_seed10_2025.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- 既存の判定ロジックを壊さない（チェック項目の追加のみ）
- `--fail-on-mismatch` の終了コード規約を維持（不一致時のみ exit 2）
- ドメイン専用ハードコードを増やさない
- Tarutani側の新機能追加はしない

完了条件：
- summary/ledger 見張り項目を最小2〜3個追加できる（例：必須キー型チェック、ledger entry最小キー率、output_files実在率）
- 追加項目の結果が `check_results` と `mismatch_fields` に保存される
- 既存コマンドで passケースは exit 0 を維持できる
- 不一致fixture（target_year違い等）で `--fail-on-mismatch` が従来どおり exit 2 になる
- 03 の NEXT_TASKS の 26) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 27）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --fail-on-mismatch
- （WSL）python run_compare_phase1_guard.py --target-year 2024 --fail-on-mismatch

------------------------------------------------------------
TASK 27) Phase1 guard history比較の追加見張り項目差分を見える化する（安全側）
------------------------------------------------------------
目的：
- TASK26で追加した `additional_guard_check_results` を history比較 summary に見える形で載せ、どの見張りが悪化/改善したかを即読できるようにする。
- 判定ロジックや終了コードは変えず、表示・summary項目の追加に限定して安全に進める。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/pass/*.json
- tests/fixtures/phase1_guard/regression/*.json
- tests/fixtures/phase1_guard/incompatible/*.json

制約：
- 取り込みループ内で実行しない（Post-fetch検証CLIとして分離）
- regression判定・compatibility判定のロジックは変更しない（見える化のみ）
- 既存終了コード規約（0=pass,2=regression,3=incompatible）を維持
- ドメイン専用ロジックは追加しない
- Tarutani側の新機能追加はしない

完了条件：
- history比較 summary に、追加見張り項目の差分一覧（例：`additional_check_diffs`）を保存できる
  - 最低限 `new_failures` / `resolved_failures` / `state_changes`（skipped含む）を持つ
- fixtureの pass/regression/incompatible で実行し、exit code が従来どおり 0/2/3 であることを確認できる
- 03 の NEXT_TASKS の 27) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 28）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/pass/current_pass_2025.json --baseline-summary tests/fixtures/phase1_guard/pass/baseline_pass_2025.json --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/regression/current_regression_2025.json --baseline-summary tests/fixtures/phase1_guard/regression/baseline_regression_2025.json --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json --strict-compatibility

------------------------------------------------------------
TASK 28) guard本体/history比較のsummary schemaを軽く文書化して運用読み方を固定化する
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py` / `run_compare_phase1_guard_history.py` の summary JSON 主要キーを最小ドキュメント化し、CI/運用で「どこを見ればよいか」を固定化する。
- ロジック変更ではなく、読み方の標準化で運用ミスを減らす。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/results/task27_*.json

制約：
- CLIロジックは変更しない（README/docs追加のみ）
- 既存終了コード規約（0=pass,2=regression,3=incompatible）を文書上でも維持
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- ドメイン専用ロジックは追加しない
- Tarutani側の新機能追加はしない

完了条件：
- guard本体summary / history summary の主要キー一覧を文書化できる（必須・任意・後方互換キーの区分）
- 判定フロー（どのキーを見て pass/regression/incompatible を判断するか）を短く明記できる
- fixtureコマンド（pass/regression/incompatible）と期待exit code（0/2/3）を文書へ紐づけできる
- 03 の NEXT_TASKS の 28) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 29）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/regression/current_regression_with_additional_2025.json --baseline-summary tests/fixtures/phase1_guard/regression/baseline_regression_with_additional_2025.json --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_with_additional_2025.json --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json --strict-compatibility

------------------------------------------------------------
TASK 29) guard fixture matrix 実行を1コマンド化して手元/CIの入口を揃える（安全側）
------------------------------------------------------------
目的：
- `tests/fixtures/phase1_guard/` の pass/regression/incompatible 実行を1コマンド入口に統一し、手元・CIの運用差を減らす。
- CLIロジックは変更せず、ラッパー/実行手順の整備だけで再現性を上げる。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/run_guard_fixture_matrix.sh
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md

制約：
- CLI本体（`run_compare_phase1_guard.py` / `run_compare_phase1_guard_history.py`）は変更しない
- 実行入口の整理（スクリプト/README/コマンド）に限定する
- 既存終了コード規約（0/2/3）を維持
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- Tarutani側の新機能追加はしない

完了条件：
- 1コマンドで fixture matrix を回せる入口が明確化される（例：`python run_phase1_guard_fixture_matrix.py`）
- 実行結果の保存先と失敗時停止ルールを README に明記できる
- CIで使う最小コマンド例（1〜2行）を文書に追加できる
- 03 の NEXT_TASKS の 29) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 30）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_fixture_matrix.py
- （WSL）echo $?  # 期待: 0（全ケース期待通り）

------------------------------------------------------------
TASK 30) guard schema version の安定付与/文書化を整えて互換判定を固定化する（安全側）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py` / `run_compare_phase1_guard_history.py` で使う `guard_schema_version` の運用ルールを固定化し、将来の項目追加時にも比較互換判定がぶれない状態にする。
- まずは文書/運用手順の整備を優先し、実装変更は必要最小限に留める。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- phase1_guard_common.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- tests/fixtures/phase1_guard/fixture_manifest.json

制約：
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- guard CLI本体ロジックを大きく変えない（互換維持を最優先）
- ドメイン専用ロジックを追加しない
- Tarutani側の新機能追加はしない

完了条件：
- `guard_schema_version` の運用方針（必須/任意/未設定互換）を文書化できる
- history比較で schema 不一致時の扱い（warning/strict時fail）の確認手順を固定化できる
- fixture/既存summaryで正常系・非互換系の確認コマンドを明記できる
- 03 の NEXT_TASKS の 30) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 31）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json --strict-compatibility
- （WSL）python run_phase1_guard_fixture_matrix.py

------------------------------------------------------------
TASK 31) `--category` の最小実体化：カテゴリ別必須ファイル集合の入口を追加する（安全側）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py` の `--category` を summaryメタだけでなく、最小の検証入口として機能させる。
- まずはカテゴリ別の必須ファイル集合（最小）だけを切り替え可能にし、将来のExhibitions/Artists拡張の土台を作る。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-1 / 5-3 / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- phase1_guard_common.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- data/phase1_seed10/logs/run_summary_seed10_2025.json

制約：
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- 既存 seed10 既定挙動（`--category` 未指定時）を壊さない
- 既存終了コード規約（0/2/3）を壊さない
- ドメイン専用ロジックを追加しない
- Tarutani側の新機能追加はしない

完了条件：
- `run_compare_phase1_guard.py` でカテゴリ別の最小必須ファイル集合を定義し、`--category` に応じて検証入口を切り替えられる
- 未対応カテゴリや不足入力時のエラー/summary表記を明確にできる（後方互換を壊さない）
- 既存の `--target-year 2025`（既定 category）で従来どおり成功する
- 03 の NEXT_TASKS の 31) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 32）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text --fail-on-mismatch

------------------------------------------------------------
TASK 32) history比較に category 文脈を追加し、カテゴリ互換情報をsummary化する（安全側）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard_history.py` の summary に current/baseline の category 文脈を追加し、比較結果の解釈を安定化する。
- 回帰判定ロジックは変えず、カテゴリ互換の見える化を最小差分で追加する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- phase1_guard_common.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- tests/fixtures/phase1_guard/fixture_manifest.json

制約：
- 既存の回帰判定ロジック（guard_passed/mismatches/mismatch_fields）は変更しない
- 既存終了コード規約（0/2/3）を壊さない
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- 既存summaryキーは削除しない（追加のみ）
- ドメイン専用ロジックを追加しない

完了条件：
- history summary に category 比較メタを追加できる（例：`current_category` / `baseline_category` / `category_comparison_mode` / `category_compatible`）
- `--strict-compatibility` 時の扱いを明記し、既存fixture（pass/regression/incompatible）の exit code 0/2/3 を維持できる
- docs に category 比較キーの読み方を追記できる
- 03 の NEXT_TASKS の 32) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 33）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_fixture_matrix.py
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/pass/current_pass_2025.json --baseline-summary tests/fixtures/phase1_guard/pass/baseline_pass_2025.json --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json --strict-compatibility

------------------------------------------------------------
TASK 33) category mismatch の固定再現fixtureを追加し、history比較の運用再現性を固める（安全側）
------------------------------------------------------------
目的：
- TASK32で追加した category 互換可視化を、毎回同じ入力/同じ期待値で再現できる fixture ケースとして固定化する。
- まずは運用再現性を優先し、history CLI本体ロジックは変更しない。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC / CARD_ID: 09_FAILURE_LOGGING
- run_compare_phase1_guard_history.py
- run_phase1_guard_fixture_matrix.py
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md

制約：
- history回帰判定ロジックは変更しない（表示/fixture追加のみ）
- 既存終了コード規約（0/2/3）を壊さない
- fixture本体を直接壊す編集は避け、必要なら新規fixtureファイルを追加する
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- 既存summaryキーは削除しない

完了条件：
- category mismatch ケース（both_present不一致）を fixture に追加できる
- 期待結果を固定化できる：
  - non-strict: exit 0（category不一致は warning-only）
  - strict: exit 3（category不一致を incompatibility 扱い）
- fixture manifest / README / matrix実行手順を更新できる
- 03 の NEXT_TASKS の 33) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 34）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json" --baseline-summary "tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json" --baseline-summary "tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json" --strict-compatibility
- （WSL）python run_phase1_guard_fixture_matrix.py

------------------------------------------------------------
TASK 34) artists_text の最小guard運用を reserved_minimal から一段進める（必須集合の具体化）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard.py --category artists_text` を「入口のみ」から一段進め、最小の必須入力集合/必須summaryキー集合を具体化する。
- 既存の `exhibitions_text` 既定挙動を壊さず、Artists横展開の実運用準備を進める。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- phase1_guard_common.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- （必要なら）run_compare_phase1_guard_history.py
- data/phase1_seed10/logs/run_summary_seed10_2025.json

制約：
- 既存の `exhibitions_text` 未指定時挙動（seed10互換）を壊さない
- 既存判定ロジック（G1〜G4 + TASK26追加見張り）を壊さない
- 既存終了コード規約を壊さない（本体CLI: pass=0, mismatch+`--fail-on-mismatch`=2）
- 取得ループには組み込まない（Post-fetch検証CLIのまま）
- ドメイン専用ロジックを追加しない

完了条件：
- artists_text の最小必須ファイル集合（required input files）と必須summaryキー集合を定義できる
- `category_required_files_profile` / `required_input_files_effective` / `category_support_mode` の内容が artists_text で意味を持つ形に更新される
- artists_text 実行時に「何が足りないか」を warning/mismatch として判別できる（ただし過剰に失敗させない）
- docs に artists_text のサポート範囲を追記できる
- 03 の NEXT_TASKS の 34) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 35）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category exhibitions_text
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text --fail-on-mismatch

------------------------------------------------------------
TASK 35) artists_text 用の最小fixture（pass/欠落warning）を追加して再現性を固定する（安全側）
------------------------------------------------------------
目的：
- TASK34で具体化した artists category profile（`required_summary_keys_effective` / `category_support_mode` / `category_activation_conditions` / `category_data_presence`）を、fixtureで毎回同じ入力・同じ期待結果で再現できるようにする。
- まずは「運用再現性」を優先し、guard CLI本体ロジックは変更しない。

参照ファイル：
- 01（SSOT）4-0共通 / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- run_phase1_guard_fixture_matrix.py
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md

制約：
- guard本体/history比較の判定ロジックは変更しない（fixture/manifest/README/matrix整備のみ）
- 既存終了コード規約（0/2/3）と matrix wrapper 規約（0/1）を壊さない
- 既存fixture（pass/regression/incompatible/category_mismatch）を壊さない
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- artists_text 用の固定fixtureケースを最低2本追加できる
  - `artists_reserved_warning_non_strict`（期待: exit 0）
  - `artists_reserved_warning_strict`（期待: exit 0 もしくは既存互換の範囲で明示）
- fixture summaryで以下キーを確認できる
  - `category`
  - `category_support_mode`
  - `required_summary_keys_effective`
  - `category_activation_conditions`
  - `category_data_presence`
  - `category_warnings`
- fixture manifest / README / matrix実行入口を更新できる
- 03 の NEXT_TASKS の 35) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 36）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text --summary-path "tests/fixtures/phase1_guard/artists/current_artists_reserved_2025.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text --summary-path "tests/fixtures/phase1_guard/artists/baseline_artists_reserved_2025.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/artists/current_artists_reserved_2025.json" --baseline-summary "tests/fixtures/phase1_guard/artists/baseline_artists_reserved_2025.json" --fail-on-regression
- （WSL）python run_phase1_guard_fixture_matrix.py

------------------------------------------------------------
TASK 36) artists_text 用の history比較fixture（category同一/不一致）を追加し、history再現性を固定する
------------------------------------------------------------
目的：
- artists文脈でも history比較（compatible / incompatible）を固定再現し、Exhibitions→Artists横展開時の検証導線を揃える。
- 既存 history比較ロジック（0/2/3）を変更せず、fixture/manifest/README/matrix運用を整える。

参照ファイル：
- 01（SSOT）4-0共通 / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING / CARD_ID: 05_MANIFEST_SYNC
- run_compare_phase1_guard_history.py
- run_phase1_guard_fixture_matrix.py
- tests/fixtures/phase1_guard/fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md

制約：
- history/guard CLI本体の判定ロジックは変更しない（fixture/manifest/README更新のみ）
- 既存終了コード規約を維持（history: 0/2/3、matrix wrapper: 0/1）
- 既存fixture（pass/regression/incompatible/category_mismatch + category_profile）を壊さない
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- artists用 history fixture を最低2ケース追加できる
  - artists_same_category_compatible（expected 0）
  - artists_vs_exhibitions_category_mismatch_strict（expected 3）
- summaryで category互換キーの確認を固定化できる
  - `current_category`
  - `baseline_category`
  - `category_comparison_mode`
  - `category_effective_for_comparison`
  - `category_compatible`
  - `compatibility_errors`（strict mismatch時）
- fixture manifest / README / matrix手順を更新できる
- 03 の NEXT_TASKS の 36) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 37）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/artists_history/current_artists_compatible_2025.json" --baseline-summary "tests/fixtures/phase1_guard/artists_history/baseline_artists_compatible_2025.json" --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/artists_history/current_artists_compatible_2025.json" --baseline-summary "tests/fixtures/phase1_guard/artists_history/baseline_exhibitions_2025.json" --strict-compatibility
- （WSL）python run_phase1_guard_fixture_matrix.py

------------------------------------------------------------
TASK 37) category profile（必須集合/activation条件）の設定ファイル化準備を行い、コード直書きを減らす（土台整備）
------------------------------------------------------------
目的：
- `phase1_guard_common.py` 内の category profile 直書きを、将来のExhibitions/Artists拡張に備えて外部設定へ寄せる。
- 判定ロジックは変えず、profile定義だけを差し替え可能にして運用保守性を上げる。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC
- phase1_guard_common.py
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py（参照のみ）
- tests/fixtures/phase1_guard/category_fixture_manifest.json
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md

制約：
- guard/history CLI本体の判定ロジックは変更しない（profile読込導線の最小追加のみ）
- 既定挙動（`--category` 未指定は `exhibitions_text`）を壊さない
- 設定読込失敗時は安全フォールバックで現行内蔵profileを使う
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- category profile 定義を外部JSON（例：`config/phase1_guard_category_profiles.json`）へ切り出せる
- `phase1_guard_common.py` が外部設定を読める（失敗時は内蔵profileへフォールバック）
- summaryに profileソース情報（例：`category_profile_source`）を保存できる
- 既存fixture（history matrix / category matrix）が従来どおり通る
- 03 の NEXT_TASKS の 37) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 38）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text
- （WSL）python run_phase1_guard_fixture_matrix.py
- （WSL）python run_phase1_guard_category_fixture_matrix.py

------------------------------------------------------------
TASK 38) category profile 設定ファイルのスキーマ検証を最小追加する（設定ミス検知の安定化）
------------------------------------------------------------
目的：
- TASK37で導入した外部設定（`config/phase1_guard_category_profiles.json`）の読み込みを、運用で壊れにくくする。
- 設定ミス（型違い/必須キー欠落）を summary で一目判別できるようにし、fallback理由を統一する。
- guard/history 判定ロジックは変更しない（設定ロード段のみ強化）。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC
- phase1_guard_common.py
- run_compare_phase1_guard.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- tests/fixtures/phase1_guard/category_fixture_manifest.json

制約：
- guard/history 判定ロジック（G1〜G4、TASK26追加見張り、history回帰/互換判定）は変更しない
- 終了コード規約は維持（guard=0/2, history=0/2/3, matrix=0/1）
- 外部設定が壊れていてもクラッシュさせず、必ず `builtin_fallback` で実行継続する
- 既定挙動（`--category` 未指定は `exhibitions_text`）を維持する

完了条件：
- `phase1_guard_common.py` に最小スキーマ検証が追加される
  - root dict / `categories` dict / default category存在 / category profile dict
  - 必須配列/文字列項目の型検証（最小）
- fallbackエラーコードが `config_schema_error:*` 系で統一される
- `run_compare_phase1_guard.py` summary で schema error理由を確認できる
- 既存fixture matrix（history/category）が従来どおり通る
- 03 の NEXT_TASKS の 38) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK39）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard.py --target-year 2025
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_missing_config.json
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category-profile-config /tmp/phase1_guard_bad_schema_config.json
- （WSL）python run_phase1_guard_fixture_matrix.py
- （WSL）python run_phase1_guard_category_fixture_matrix.py

------------------------------------------------------------
TASK 39) history比較summaryにも category_profile_config 文脈を載せて、運用可視化を揃える（安全側）
------------------------------------------------------------
目的：
- `run_compare_phase1_guard_history.py` の summary に、current/baseline の category profile config 文脈（source/path/error/version）を追加し、比較前提差を読み取りやすくする。
- 回帰判定/互換判定ロジックは変更せず、可視化キー追加のみで運用診断を強化する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists / 5-8
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC
- phase1_guard_common.py
- run_compare_phase1_guard.py
- run_compare_phase1_guard_history.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- tests/fixtures/phase1_guard/fixture_manifest.json

制約：
- history回帰判定ロジック（`guard_passed`/`mismatches`/`mismatch_fields`）は変更しない
- compatibility判定ロジック（target_year/schema/category）は変更しない
- 終了コード規約を維持（history: 0/2/3、matrix wrapper: 0/1）
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- history summary に最低限以下が保存される
  - `current_category_profile_source`
  - `baseline_category_profile_source`
  - `current_category_profile_config_path`
  - `baseline_category_profile_config_path`
  - `current_category_profile_config_loaded`
  - `baseline_category_profile_config_loaded`
  - `current_category_profile_config_error`
  - `baseline_category_profile_config_error`
  - `current_category_profile_config_version_effective`
  - `baseline_category_profile_config_version_effective`
- old summary（キー欠落）でも比較継続できる（後方互換）
- `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` に history側キーを最小追記
- 03 の NEXT_TASKS の 39) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK40）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/pass/current_pass_2025.json" --baseline-summary "tests/fixtures/phase1_guard/pass/baseline_pass_2025.json" --fail-on-regression
- （WSL）python run_compare_phase1_guard_history.py --current-summary "tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json" --baseline-summary "tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json" --strict-compatibility
- （WSL）python run_phase1_guard_fixture_matrix.py

------------------------------------------------------------
TASK 40) category profile config の簡易lint CLIを追加し、guard実行前に設定だけ検査できる入口を作る（安全側）
------------------------------------------------------------
目的：
- `config/phase1_guard_category_profiles.json` の更新時に、guard本体を走らせる前に設定ミス（missing key / type error / json broken）を検知できるようにする。
- Task38で整えた `validate_category_profiles_config(config_obj)` と error code体系（`config_missing:*` / `config_json_decode_error:*` / `config_schema_error:*`）を単体で検査可能にする。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ・manifest系運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC
- phase1_guard_common.py
- run_compare_phase1_guard.py
- config/phase1_guard_category_profiles.json
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history 判定ロジックは変更しない
- 終了コード規約（guard=0/2, history=0/2/3, matrix=0/1）を壊さない
- lint CLI は設定検査専用（取得ループには組み込まない）
- 既存の fallback 挙動は維持（lint導入で guard 実行を強制失敗にしない）

完了条件：
- `python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"` が実行できる
- lint結果 summary JSON を保存できる（例：`data/phase1_seed10/logs/phase1_guard_category_profile_lint_*.json`）
- lint summary に最低限以下が入る：
  - `config_path`
  - `config_exists`
  - `config_valid`
  - `config_error_code`
  - `config_error_detail`
  - `checked_at`
  - `source_cli`
- exit code 規約：
  - `0 = lint pass`
  - `1 = lint fail`（missing/json/schema）
- 03 の NEXT_TASKS の 40) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK41）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_missing_config.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_config.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_schema_config.json"

------------------------------------------------------------
TASK 41) artists_text activation条件の監視キーを category fixture matrix に追加し、昇格判定の再現性を強化する（安全側）
------------------------------------------------------------
目的：
- `run_phase1_guard_category_fixture_matrix.py` の summary checks で、artists category profile の activation条件まわり（`category_activation_conditions` / `category_data_presence` / `category_support_mode`）を固定検証できるようにする。
- reserved/provisional の昇格判定を、毎回同じ入力で再現し、手元/CIで運用差をなくす。

参照ファイル：
- 01（SSOT）4-0共通 / 4-3 Artists / 5-8（ログ・manifest系）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 09_FAILURE_LOGGING
- run_phase1_guard_category_fixture_matrix.py
- tests/fixtures/phase1_guard/category_fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- run_compare_phase1_guard.py（確認のみ）

制約：
- guard/history 判定ロジックは変更しない（fixture/manifest/matrix検証項目の追加のみ）
- 終了コード規約を維持（guard 0/2, history 0/2/3, matrix wrapper 0/1）
- 既存 fixture ケースの意味を変えない（追加/追記のみ）
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- category fixture manifest に activation監視の expected_summary_checks が追加される
- 最低限以下の確認が matrix で機械判定できる
  - reserved ケース：`category_support_mode=reserved_minimal`
  - provisional ケース：`category_support_mode=provisional_minimal`
  - 両ケース：`category_activation_conditions` 非空、`category_data_presence` 存在
- `python run_phase1_guard_category_fixture_matrix.py` 実行で wrapper exit 0
- matrix summary に `cases[].summary_checks_passed=true` が残る
- 03 の NEXT_TASKS の 41) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK42）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_category_fixture_matrix.py
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir "tests/fixtures/phase1_guard/category/artists_reserved_warning/logs"
- （WSL）python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir "tests/fixtures/phase1_guard/category/artists_provisional_pass/logs"

------------------------------------------------------------
TASK 42) category profile lint を fixture matrix に統合し、設定検証の再現性を1コマンド化する（安全側）
------------------------------------------------------------
目的：
- Task40で追加した `run_phase1_guard_category_profile_lint.py` を fixture matrix 化し、valid/missing/bad_json/bad_schema を毎回同じ期待結果（exit 0/1）で再現できるようにする。
- guard本体を実行しなくても、設定ファイル品質をCI/手元で固定検証できる入口を作る。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ・manifest運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_category_profile_lint.py
- phase1_guard_common.py
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history 判定ロジックは変更しない（lint matrix追加のみ）
- 終了コード規約を維持：
  - lint CLI: 0/1
  - guard: 0/2
  - history: 0/2/3
  - matrix wrapper: 0/1
- 既存fixture（history/category）は壊さない
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- lint fixture manifest（例：`tests/fixtures/phase1_guard/lint_fixture_manifest.json`）を追加
- 1コマンドラッパー（例：`python run_phase1_guard_lint_fixture_matrix.py`）を追加
- minimum 4ケースを固定再現：
  - valid config（expected exit 0）
  - missing config（expected exit 1, `config_missing:*`）
  - bad json（expected exit 1, `config_json_decode_error:*`）
  - bad schema（expected exit 1, `config_schema_error:*`）
- matrix summary に以下を保存：
  - `all_cases_passed`
  - `cases[].expected_exit_code`
  - `cases[].actual_exit_code`
  - `cases[].summary_checks_passed`
  - `cases[].summary_check_failures`
  - `cases[].output_summary_path`
- 03 の NEXT_TASKS の 42) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK43）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_lint_fixture_matrix.py
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_missing_config.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_config.json"
- （WSL）python run_phase1_guard_category_profile_lint.py --config-path "/tmp/phase1_guard_bad_schema_config.json"

------------------------------------------------------------
TASK 43) guard検証（history/category/lint）の統合matrix入口を追加し、手元/CIの実行導線を一本化する（安全側）
------------------------------------------------------------
目的：
- 既存の3系統matrix（history/category/lint）を1コマンドで順次実行し、総合pass/failを判定できる統合ラッパーを追加する。
- 実行漏れ（「lintだけ忘れた」「categoryだけ未実行」）を防ぎ、手元/CIの運用導線を固定化する。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ・manifest運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_fixture_matrix.py
- run_phase1_guard_category_fixture_matrix.py
- run_phase1_guard_lint_fixture_matrix.py
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- history/category/lint の各CLIおよび各matrix本体ロジックは変更しない（統合ラッパー追加のみ）
- 終了コード規約を維持：
  - history matrix: wrapper 0/1
  - category matrix: wrapper 0/1
  - lint matrix: wrapper 0/1
  - 統合matrix wrapper: 0/1
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- 統合ラッパー（例：`run_phase1_guard_all_matrices.py`）を追加
- 1コマンドで以下を順次実行できる：
  - `run_phase1_guard_fixture_matrix.py`
  - `run_phase1_guard_category_fixture_matrix.py`
  - `run_phase1_guard_lint_fixture_matrix.py`
- 総合summaryに最低限以下を保存：
  - `all_passed`
  - `executed_matrices`
  - `matrices[].name`
  - `matrices[].expected_exit_code`
  - `matrices[].actual_exit_code`
  - `matrices[].pass_fail`
  - `matrices[].summary_path`（取れる範囲）
- 統合wrapper exit:
  - `0 = all_passed`
  - `1 = any_failed`
- 03 の NEXT_TASKS の 43) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK44）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices.py
- （WSL）python run_phase1_guard_fixture_matrix.py
- （WSL）python run_phase1_guard_category_fixture_matrix.py
- （WSL）python run_phase1_guard_lint_fixture_matrix.py

------------------------------------------------------------
TASK 44) 統合matrix summaryの軽量レポートCLIを追加し、CI失敗時の切り分けを高速化する（安全側）
------------------------------------------------------------
目的：
- `run_phase1_guard_all_matrices.py` が出力する統合summary JSONを読み、失敗matrix・exit code・子summaryパスを短く表示/保存するレポートCLIを追加する。
- CIログで「どこが落ちたか」を1画面で把握できる入口を作る（matrix本体ロジックは変更しない）。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices.py
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- tests/fixtures/phase1_guard/README.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history/lint 各CLIの判定ロジックは変更しない
- 既存終了コード規約は維持（新規report CLIは `0=report_generated` / `1=summary_not_found_or_invalid` で可）
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- `python run_phase1_guard_all_matrices_report.py --summary-path "<path>"` が実行できる
- `--latest` で最新 `phase1_guard_all_matrices_*.json` を自動解決できる
- レポートに最低限以下を出力できる：
  - `all_passed`
  - `wrapper_exit_code`
  - `execution_order`
  - 失敗matrix一覧（name / actual_exit_code / summary_path）
  - 参照すべき子summaryパス一覧
- 任意でレポートJSONまたはMarkdown保存（どちらか1つ）を実装
- 03 の NEXT_TASKS の 44) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK45）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --latest

------------------------------------------------------------
TASK 45) report CLIの固定再現fixtureを追加し、summary欠落/破損時の挙動を1コマンドで検証できるようにする（安全側）
------------------------------------------------------------
目的：
- `run_phase1_guard_all_matrices_report.py` の入出力を fixture 化し、valid/missing/bad_json の期待exitを毎回同じ条件で再現できるようにする。
- CIで report CLI の安定性（summary読取の壊れやすさ）を guard本体ロジック非依存で検証できる入口を作る。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices_report.py
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history/lint 各CLIおよび各matrix本体ロジックは変更しない
- report CLIのexit規約（0/1）を維持
- fixture/matrix追加のみ（取得ループには組み込まない）

完了条件：
- report fixture manifest（例：`tests/fixtures/phase1_guard/report_fixture_manifest.json`）を追加
- report fixture matrix wrapper（例：`run_phase1_guard_all_matrices_report_fixture_matrix.py`）を追加
- 最低3ケースを固定再現：
  - valid summary（expected exit 0）
  - missing summary（expected exit 1）
  - bad json summary（expected exit 1）
- matrix summaryに最低限以下を保存：
  - `all_cases_passed`
  - `cases[].expected_exit_code`
  - `cases[].actual_exit_code`
  - `cases[].summary_checks_passed`
  - `cases[].summary_check_failures`
  - `cases[].report_output_path`（任意）
- 03 の NEXT_TASKS の 45) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK46）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py

------------------------------------------------------------
TASK 46) report CLIに`--fail-on-failed-matrix`を追加し、CIの終了条件を選べるようにする（安全側）
------------------------------------------------------------
目的：
- `run_phase1_guard_all_matrices_report.py` で、レポート生成成功とは別に「統合summaryが失敗状態（all_passed=false）ならCIを落とす」運用を選べるようにする。
- 既存の report CLI 規約（デフォルトは `0=report_generated / 1=summary_not_found_or_invalid`）は維持し、オプション指定時のみ厳格化する。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices_report.py
- run_phase1_guard_all_matrices_report_fixture_matrix.py
- tests/fixtures/phase1_guard/report_fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history/lint 各CLIおよび各matrix本体ロジックは変更しない
- 既定挙動（オプション未指定）は後方互換を維持
- 取得ループには組み込まない（Post-fetch検証CLIのまま）

完了条件：
- `run_phase1_guard_all_matrices_report.py` に `--fail-on-failed-matrix` を追加
- 挙動：
  - 未指定：従来どおり（summary読取成功なら exit 0）
  - 指定時：`all_passed=false` なら exit 1、`all_passed=true` なら exit 0
- report出力（stdout/JSON）に `fail_on_failed_matrix` と `policy_result`（相当）を保存/表示
- report fixture matrix にケースを追加して期待exitを固定再現（strict policy）
- 03 の NEXT_TASKS の 46) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK47）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json" --fail-on-failed-matrix
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py

------------------------------------------------------------
TASK 47) report fixture matrixに終了ポリシー可視化キーを追加し、CIログ読解を固定化する（安全側）
------------------------------------------------------------
目的：
- `run_phase1_guard_all_matrices_report_fixture_matrix.py` の `cases[]` へ、終了ポリシーの実効値を明示保存し、default/strict の違いを機械的に追えるようにする。
- 実行結果は同じでも「どのポリシーで判定したか」が曖昧にならないようにする。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices_report.py
- run_phase1_guard_all_matrices_report_fixture_matrix.py
- tests/fixtures/phase1_guard/report_fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history/lint 各CLIと各matrix本体ロジックは変更しない
- report CLI の終了規約（default/strict）は変更しない（可視化強化のみ）
- 取得ループには組み込まない

完了条件：
- report fixture matrix summary の `cases[]` に最低限以下を追加：
  - `fail_on_failed_matrix`
  - `policy_expected`（manifest由来）
  - `policy_actual`（report出力由来）
  - `policy_match`（bool）
- strictケースで `policy_actual=fail_on_failed_matrix` が取れる
- defaultケースで `policy_actual=default_report_only` が取れる
- `python run_phase1_guard_all_matrices_report_fixture_matrix.py` で wrapper exit 0
- 03 の NEXT_TASKS の 47) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK48）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json" --fail-on-failed-matrix

------------------------------------------------------------
TASK 48) report fixture matrixにpolicy_matchガードを追加し、終了ポリシー齟齬をwrapper failとして検知する（安全側）
------------------------------------------------------------
目的：
- TASK47で可視化した `policy_expected` / `policy_actual` を matrix判定へ最小反映し、ポリシー齟齬を見逃さない運用にする。
- 既存の report CLI 本体ロジックは変更せず、fixture matrix 側の判定だけを強化する。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices_report.py
- run_phase1_guard_all_matrices_report_fixture_matrix.py
- tests/fixtures/phase1_guard/report_fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- guard/history/lint 各CLIと各matrix本体ロジックは変更しない
- report CLI の終了規約（default/strict）は変更しない
- 取得ループには組み込まない

完了条件：
- report fixture matrix で `policy_match=false` を機械判定できる
- `policy_actual` が取得できるケースでは、`policy_match=false` を matrix fail 条件に追加できる
- `policy_actual` が取得不能（missing/bad_json）ケースは後方互換で warning 扱いにできる
- matrix summary に `policy_check_mode`（または同等）を保存できる
- `python run_phase1_guard_all_matrices_report_fixture_matrix.py` で期待どおり判定できる
- 03 の NEXT_TASKS の 48) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK49）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json"
- （WSL）python run_phase1_guard_all_matrices_report.py --summary-path "tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json" --fail-on-failed-matrix

------------------------------------------------------------
TASK 49) report fixture matrixにpolicy mismatch専用negative fixtureを追加し、policy_guard失敗経路を常設再現する（安全側）
------------------------------------------------------------
目的：
- TASK48で導入した `policy_match` ガードの失敗経路を、常設のnegative fixtureとして再現可能にする。
- 通常のgreen matrixとは分離し、CIで「失敗すべき時に失敗する」を固定検証できるようにする。

参照ファイル：
- 01（SSOT）4-0共通 / 5-8（ログ運用）
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_guard_all_matrices_report_fixture_matrix.py
- tests/fixtures/phase1_guard/report_fixture_manifest.json
- tests/fixtures/phase1_guard/README.md
- docs/PHASE1_GUARD_SUMMARY_SCHEMA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- report CLI本体（`run_phase1_guard_all_matrices_report.py`）のロジック/終了規約は変更しない
- 既存のgreen manifest（通常実行でexit 0）は壊さない
- 取得ループには組み込まない

完了条件：
- policy mismatch専用manifest（例：`tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json`）を追加
- negative manifest実行で strictケースが `policy_match=false` になり wrapper exit 1 になる
- 通常manifest実行は従来どおり wrapper exit 0 を維持
- README と schema文書に「green/negative 2系統実行」の読み方を追記
- 03 の NEXT_TASKS の 49) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK50）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py
- （WSL）python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path "tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json"

------------------------------------------------------------
TASK 50) Phase1本体へ復帰：run_phase1_seed10.py に artists_text の最小取得入口を追加する（安全側）
------------------------------------------------------------
目的：
- 検証層タスク（TASK49）を締めたので、本体前進として seed10 実行に artists_text の最小取得導線を追加する。
- Exhibitionsとの並走入口を作り、今後のExhibitions/Artists拡張を本体側で進めやすくする。

参照ファイル：
- 01（SSOT）4-0共通 / 4-3 Artists / 5-1 / 5-3
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT
- run_phase1_seed10.py
- run_compare_phase1_guard.py（summary/ledgerキー整合の参照）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内でLLM加工しない（Post-fetch分離）
- 既存Exhibitions処理を壊さない（デフォルト挙動の後方互換）
- ドメイン専用ハードコードを増やさない
- 既存台帳（visited/failed）運用は維持する

完了条件：
- `run_phase1_seed10.py` で artists_text の最小取得入口が実行できる（データ0件でもクラッシュしない）
- summary/logsに artists_text 文脈の件数（saved/skipped/failed）が残る
- 既存Exhibitionsの saved/skipped/failed 表示と台帳再利用が維持される
- 03 の NEXT_TASKS の 50) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK51）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py
- （WSL）python run_phase1_seed10.py
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 51) artists_text の入力ソースをCSV拡張で分離し、seed10取得率の改善余地を作る（本体前進・最小）
------------------------------------------------------------
目的：
- `run_phase1_seed10.py --include-artists-text` で、artists取得元を `exhibitions_url` 依存から緩和し、CSVの任意3列目 `artists_url` を優先利用できるようにする。
- 既存CSV（2列）の後方互換を維持しつつ、Artists入口の取得率改善導線を最小差分で作る。

参照ファイル：
- 01（SSOT）4-0共通 / 4-1 Exhibitions / 4-3 Artists
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT
- run_phase1_seed10.py
- data/gallery_lists/gallery_list_frieze_london.csv
- data/gallery_lists/gallery_list_liste.csv
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内でLLM加工をしない（Post-fetch分離）
- 既存Exhibitions挙動・既存CSV（2列）を壊さない
- artists_url未指定時は `exhibitions_url` をフォールバック利用する
- ドメイン専用ハードコードを増やさない

完了条件：
- CSV読込で `artists_url`（任意）を扱える（列が無い/空でもクラッシュしない）
- `--include-artists-text` 実行時、artists入口URLは `artists_url` 優先、未指定時は `exhibitions_url` fallback で動作する
- run summary に artists入口URLの解決結果サマリ（例: artists_url_used / fallback_used）を追加できる
- 既存コマンド `python run_phase1_seed10.py` は後方互換で成功する
- 03 の NEXT_TASKS の 51) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK52）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 52) artists_text のCSV入力（artists_url列）を実データ拡充し、seed10で new_saved 発生を確認する（本体前進）
------------------------------------------------------------
目的：
- TASK51で追加した `artists_url` 優先導線を実データで活かし、seed10で artists_text の `new_saved>0` を1件以上発生させる。
- 取得率改善のための最小データ整備（CSV 3列目補完）を行い、並走実行で効果を確認する。

参照ファイル：
- 01（SSOT）4-0共通 / 4-3 Artists
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_seed10.py
- data/gallery_lists/gallery_list_frieze_london.csv
- data/gallery_lists/gallery_list_liste.csv
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 既存CSV（2列）互換を壊さない（3列目は任意）
- 取得ループ内でLLM加工しない（Post-fetch分離）
- ドメイン専用ハードコードを増やさない
- 既存Exhibitions処理は変更しない

完了条件：
- seed10対象（frieze/liste 各先頭5行）のうち、可能な行に `artists_url` を補完できる
- `python run_phase1_seed10.py --include-artists-text` で artists側 `new_saved>0` を確認できる
- run summary で `artists_list_url_artists_url_used` / `artists_list_url_exhibitions_fallback_used` を確認できる
- 03 の NEXT_TASKS の 52) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK53）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 53) ブロッカー解消：外向き通信回復後に artists_text の new_saved>0 を再検証し、TASK52を完了させる
------------------------------------------------------------------------------------------------
目的：
- TASK52の未達要因（DNS/外向き通信不可）を解消した状態で、artists_text の `new_saved>0` を確認して本体前進を再開する。

参照ファイル：
- run_phase1_seed10.py
- data/phase1_seed10/logs/failed_fetches_artists_seed10_2025.json
- data/phase1_seed10/logs/visited_pages_artists_seed10_2025.json
- data/phase1_seed10/logs/run_summary_seed10_2025.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内でLLM加工しない
- 既存Exhibitions処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- 外向き通信確認が通る（curl/socket）
- artists台帳のcooldown影響を除外したうえで `python run_phase1_seed10.py --include-artists-text` を再実行できる
- run summary で `artists_records_saved_total > 0` を1回確認できる
- 03 の TASK52 を [x] に更新し、CHANGELOG追記
- 次の最優先タスク（TASK54）のプロンプト全文を提示

動作確認コマンド：
- （WSL）curl -I https://example.com
- （WSL）python -c "import socket; print(socket.gethostbyname('example.com'))"
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 54) artists_text のPost-fetch Enrichment入口をseed10本体へ追加する（本体前進・最小）
------------------------------------------------------------------------------------------------
目的：
- TASK52/53で保存できた artists_text raw を対象に、取得ループ外の事後バッチ（Enrichment requests生成）へ接続する。
- Phase2接続に向け、artists_text の headline候補生成導線を最小差分で成立させる。

参照ファイル：
- 01（SSOT）Post-fetch / 4-3 Artists
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_enrichment_seed10.py
- run_phase1_seed10.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/raw/artists_liste_2025.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内でLLM加工しない（Post-fetch分離を維持）
- 既存Exhibitions Enrichment出力を壊さない
- artists向け追加は「入力対象追加＋summary拡張」に留める（大規模改修しない）

完了条件：
- artists raw を読み込み、未付与候補の enrichment requests を生成できる
- summary に `artists_enrichment_candidates` / `artists_enrichment_output_paths`（同等キー）を保存できる
- `python run_enrichment_seed10.py` で既存Exhibitionsと併存して実行できる
- 03 の NEXT_TASKS の 54) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK55）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_enrichment_seed10.py
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_seed10.py

------------------------------------------------------------
TASK 55) artists_text のEnrichment applyバッチを追加し、requestsから `headline_ja` をrawへ反映する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK54で生成した artists enrichment requests を使い、`artists_*.jsonl` の `headline_ja` を Post-fetch バッチで更新する。
- 取得ループ外で完結する apply 導線を追加し、Phase2接続前の最小品質改善を進める。

参照ファイル：
- 01（SSOT）Post-fetch / 4-3 Artists
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON
- run_phase1_seed10.py
- data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/raw/artists_liste_2025.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内でLLM加工しない（Post-fetch分離維持）
- 既存Exhibitions取得/summary/台帳の挙動を壊さない
- artists_text 以外のカテゴリへ影響を広げない（最小差分）

完了条件：
- `python run_enrichment_artists_seed10_apply.py`（例）が実行できる
- `artists_enrichment_requests_2025.jsonl` から更新対象を読み、`artists_*.jsonl` の `headline_ja` を更新できる
- apply結果 summary（updated/skipped/failed/output_paths）を保存できる
- 03 の NEXT_TASKS の 55) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK56）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 56) artists_text のEmbedding/Index入口を追加し、検索用生成物をseed10派生データとして保存する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK55で `headline_ja` を反映した artists raw を対象に、Embeddingと検索用Indexの生成入口を作る。
- Phase2接続に向けて、artists_text の検索基盤（index/meta）を最小で成立させる。

参照ファイル：
- 01（SSOT）Post-fetch / 4-3 Artists / 5-8 / 5-9
- 02（索引）CARD_ID: 14_CATEGORY_4_0_COMMON / CARD_ID: 05_MANIFEST_SYNC
- run_enrichment_artists_seed10_apply.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/raw/artists_liste_2025.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md

制約：
- 取得ループ内で実行しない（Post-fetchバッチとして分離）
- 空textレコードは埋め込み対象外としてスキップし、件数をsummaryに残す
- 既存Exhibitions/Tarutaniのvector処理を壊さない（最小差分）

完了条件：
- `python run_vectorize_artists_seed10.py`（例）が実行できる
- artists向け index + meta + summary を保存できる
- summaryに `input_total` / `embedded_total` / `skipped_total` / `output_paths` を保存できる
- 03 の NEXT_TASKS の 56) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/件数）を追記
- 次の最優先タスク（TASK57）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_vectorize_artists_seed10.py
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 57) ブロッカー解消：artists_text vectorize の外向き接続を回復し、`embedded_total>0` を再確認する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK56で追加した `run_vectorize_artists_seed10.py` の接続ブロッカーを解消し、実埋め込みを生成して検索基盤を前進させる。
- `embedded_total=0` の原因を「接続要因」か「コード要因」か最短で切り分ける。

参照ファイル：
- run_vectorize_artists_seed10.py
- data/phase1_seed10/derived/vector/artists_text_vectorize_failed_2025.jsonl
- data/phase1_seed10/derived/vector/artists_text_vectorize_summary_2025.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内でLLM加工しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutaniの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- 外向き接続確認（curl/socket）が通る
- `python run_vectorize_artists_seed10.py` で `embedded_total > 0` を1回確認できる
- summaryに `input_total / embedded_total / skipped_total / output_paths` が保存される
- 03 の NEXT_TASKS の 57) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/embedded件数）を追記
- 次の最優先タスク（TASK58）のプロンプト全文を提示

動作確認コマンド：
- （WSL）curl -I https://example.com
- （WSL）python -c "import socket; print(socket.gethostbyname('example.com'))"
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_vectorize_artists_seed10.py
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 58) artists_text の検索スモークCLIを追加し、vector生成物から top-k を確認する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK57で再生成した artists index/meta を使い、artists_text の検索導線（最小CLI）を成立させる。
- Phase2接続前に「質問→top-k根拠表示」が動く状態を先に作る。

参照ファイル：
- run_vectorize_artists_seed10.py
- data/phase1_seed10/derived/vector/artists_text_index_2025.npy
- data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutaniの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_search_artists_seed10.py --query "..."`（例）が実行できる
- top-k の `source_url` / `record_id` / `score`（または同等）を出力できる
- search summary（`query` / `k` / `output_paths`）を保存できる
- 03 の NEXT_TASKS の 58) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/top-k件数）を追記
- 次の最優先タスク（TASK59）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_vectorize_artists_seed10.py
- （WSL）python run_search_artists_seed10.py --query "contemporary painting"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 59) artists_text の検索結果を context JSON に整形し、Phase2接続入力を固定する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK58の top-k 検索結果を、後続回答層へそのまま渡せる context JSON として保存する。
- Phase2接続前に「検索結果→根拠コンテキスト」の受け渡し形式を固定する。

参照ファイル：
- run_search_artists_seed10.py
- data/phase1_seed10/derived/vector/search/artists_text_search_results_*.jsonl
- data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/raw/artists_liste_2025.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutaniの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_build_artists_context_seed10.py --query "..."`（例）が実行できる
- context JSON に `source_url` / `record_id` / `score` / `excerpt`（または同等）を含めて保存できる
- context summary（`query` / `k` / `input_paths` / `output_paths`）を保存できる
- 03 の NEXT_TASKS の 59) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/context件数）を追記
- 次の最優先タスク（TASK60）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_vectorize_artists_seed10.py
- （WSL）python run_search_artists_seed10.py --query "contemporary painting"
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 60) artists_text の回答スモークCLIを追加し、context JSON から根拠付き回答を出力する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK59で整形した artists context JSON を入力に、回答本文と根拠を1コマンドで出力できる最小CLIを成立させる。
- Phase2接続前に「質問→回答→根拠保存」の往復を固定する。

参照ファイル：
- run_build_artists_context_seed10.py
- data/phase1_seed10/derived/context/artists_text_context_*.json
- data/phase1_seed10/derived/context/artists_text_context_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutaniの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_answer_artists_seed10.py --question "..." --query "..."`（例）が実行できる
- 出力JSONに `answer` と根拠（`source_url` / `record_id` / `score` / `excerpt`）を保存できる
- answer summary（`question` / `query` / `context_path` / `output_paths`）を保存できる
- 03 の NEXT_TASKS の 60) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/answer長）を追記
- 次の最優先タスク（TASK61）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_phase1_seed10.py --include-artists-text
- （WSL）python run_enrichment_artists_seed10_apply.py
- （WSL）python run_vectorize_artists_seed10.py
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_answer_artists_seed10.py --question "contemporary paintingの要点を教えて" --query "contemporary painting"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 61) artists_text の回答比較CLIを追加し、query再生成 / context固定の差分可視化入口を作る（本体前進）
------------------------------------------------------------------------------------------------
目的：
- artists回答導線の再現性を高めるため、query再生成モードとcontext固定モードの差分を1コマンドで比較できるようにする。
- 回答品質調整前に、まずは「差分を見える化できる状態」を先に作る。

参照ファイル：
- run_answer_artists_seed10.py
- run_build_artists_context_seed10.py
- data/phase1_seed10/derived/context/artists_text_context_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_compare_artists_answers.py --question "..." --query "..." --context-path "..."`（例）が実行できる
- 比較summaryに最低限 `answer_chars` / `evidence_count` / `mismatch_fields`（または同等）を保存できる
- 03 の NEXT_TASKS の 61) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/差分要約）を追記
- 次の最優先タスク（TASK62）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"
- （WSL）python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 62) artists_text 回答CLIの最小ガードを追加し、空回答/根拠欠落を非0終了で検知できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- artists回答導線の最低品質を守るため、空回答や根拠欠落を手元/CIで早期検知できる最小ガードを追加する。
- 回答品質改善の前に、まずは「壊れている回答を自動検知できる状態」を固定する。

参照ファイル：
- run_answer_artists_seed10.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/answer/artists_text_answer_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_answer_artists_seed10.py --question "..." --query "..." --fail-on-invalid-output`（例）が実行できる
- 最低限の検知条件（`answer` 非空 / `evidence` 1件以上 / 根拠必須キー存在）を実装できる
- summaryに `output_valid` / `invalid_reasons`（または同等）を保存できる
- 無効出力時は `--fail-on-invalid-output` 指定で非0終了できる
- 03 の NEXT_TASKS の 62) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/ガード判定）を追記
- 次の最優先タスク（TASK63）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output
- （WSL）python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 63) artists_text 回答比較CLIに最小回帰ガードを追加し、差分悪化時のみ非0終了にする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK61の比較CLIで出ている差分を「単なる差分」と「回帰（悪化）」に分離し、運用でノイズfailを減らす。
- 回答品質改善前に、最低限の回帰検知（status/evidence/output_valid）だけを固定する。

参照ファイル：
- run_compare_artists_answers.py
- run_answer_artists_seed10.py
- data/phase1_seed10/derived/answer/artists_text_answer_compare_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_compare_artists_answers.py --question "..." --query "..." --context-path "..." --fail-on-regression`（例）が実行できる
- 比較summaryに `guard_passed` / `regression_reasons` / `mismatch_fields` を保存できる
- 回帰条件（最低限）を実装できる：
  - `answer_status` が `ok -> fallback` に悪化
  - `output_valid` が `true -> false` に悪化
  - `evidence_count` が減少
- `--fail-on-regression` 指定時のみ回帰で非0終了、差分のみ（回帰なし）は0終了できる
- 03 の NEXT_TASKS の 63) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/回帰判定）を追記
- 次の最優先タスク（TASK64）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json" --fail-on-regression
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 64) artists回答導線のQA統合スモークCLIを追加し、context生成→回答→比較を1コマンドで実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- artists回答系の手動コマンド列（context build / answer / compare）を1コマンド化し、手元運用とCI前確認を簡素化する。
- 既存CLIを再利用し、判定ロジックの重複実装を避ける。

参照ファイル：
- run_build_artists_context_seed10.py
- run_answer_artists_seed10.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/context/artists_text_context_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存CLI本体の終了コード規約は変更しない（統合側で集約のみ）

完了条件：
- `python run_artists_answer_qa_smoke.py --question "..." --query "..."`（例）が実行できる
- 内部で以下を順次実行できる：
  - context build
  - answer（`--fail-on-invalid-output`）
  - compare（`--fail-on-regression` 任意）
- QA summaryに最低限以下を保存できる：
  - `all_passed`
  - `steps[].name`
  - `steps[].command`
  - `steps[].exit_code`
  - `steps[].output_paths`（取得できる範囲）
- 03 の NEXT_TASKS の 64) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK65）のプロンプト全文を提示

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-regression
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 65) artists回答の根拠整形を最小強化し、excerpt/headline欠落時フォールバックを安定化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- artists回答JSONの evidence を運用で読みやすく保つため、excerpt/headline欠落時のフォールバック整形を最小追加する。
- 回答品質の高度化前に、根拠欠落で読みづらくなるケースを減らす。

参照ファイル：
- run_answer_artists_seed10.py
- run_build_artists_context_seed10.py
- data/phase1_seed10/derived/answer/artists_text_answer_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- `--fail-on-invalid-output` の既存終了規約を変えない

完了条件：
- `run_answer_artists_seed10.py` で `excerpt` 欠落時フォールバック（`headline_ja` / `text` 断片）を実装できる
- summary に `evidence_fallback_excerpt_count` / `evidence_fallback_headline_count`（同等）を保存できる
- `python run_answer_artists_seed10.py --question "..." --query "..." --fail-on-invalid-output` が従来どおり実行できる
- 03 の NEXT_TASKS の 65) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/フォールバック件数）を追記
- 次の最優先タスク（TASK66）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output
- （WSL）python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 66) artists回答QA統合CLIにcontext固定再現モードを追加し、日次runと再現runの入口を一本化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- `run_artists_answer_qa_smoke.py` に `--context-path` を追加し、query再生成とcontext固定再現を同一CLIで運用できるようにする。
- 日次確認（query再生成）と再現確認（固定context）を分離せず、1コマンド系で扱える状態を作る。

参照ファイル：
- run_artists_answer_qa_smoke.py
- run_build_artists_context_seed10.py
- run_answer_artists_seed10.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/context/artists_text_context_*.json
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存CLI本体の終了コード規約は変更しない（統合側で集約のみ）

完了条件：
- `run_artists_answer_qa_smoke.py` で `--query`（既存）と `--context-path`（新規）を排他で扱える
- `--context-path` 指定時は context build をスキップし、answer/compare を固定contextで実行できる
- QA summary に `qa_input_mode` / `context_path_effective` / `steps[].exit_code` / `all_passed` を保存できる
- `--fail-on-regression` の既存挙動を維持できる
- 03 の NEXT_TASKS の 66) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK67）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json" --fail-on-regression
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 67) artists回答QA統合CLIに複数query一括実行モードを追加し、日次確認を1コマンド化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- `run_artists_answer_qa_smoke.py` に batch 実行入口（manifest/JSONL）を追加し、複数queryケースを1コマンドで回せるようにする。
- 日次運用の手動反復を減らし、summary収集を固定化する。

参照ファイル：
- run_artists_answer_qa_smoke.py
- run_build_artists_context_seed10.py
- run_answer_artists_seed10.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存単発モード（`--query` / `--context-path`）の後方互換を壊さない

完了条件：
- `run_artists_answer_qa_smoke.py --batch-manifest "..."`（例）が実行できる
- batch summary に `total_cases` / `passed_cases` / `failed_cases` / `cases[].summary_path` / `cases[].exit_code` を保存できる
- 単発モードの既存挙動（終了コード・summaryキー）を維持できる
- 03 の NEXT_TASKS の 67) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK68）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 68) artists回答の根拠整形を最小強化し、重複source統合と表示順の安定化を行う（本体前進）
------------------------------------------------------------------------------------------------
目的：
- `run_answer_artists_seed10.py` の evidence を運用で読みやすく保つため、重複根拠の統合と表示順安定化を最小差分で追加する。
- 回答品質の高度化前に、表示揺れ（同一source重複・順序不安定）を減らす。

参照ファイル：
- run_answer_artists_seed10.py
- run_build_artists_context_seed10.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/answer/artists_text_answer_*.json
- data/phase1_seed10/derived/answer/artists_text_answer_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- `--fail-on-invalid-output` の既存終了規約を変えない

完了条件：
- `run_answer_artists_seed10.py` で evidence の重複統合（`source_url + record_id`）を実装できる
- evidence の表示順を安定化できる（`score` 降順 + tie-break）
- summary に `evidence_dedup_removed_count` / `evidence_sorted`（同等）を保存できる
- `python run_answer_artists_seed10.py --question "..." --query "..." --fail-on-invalid-output` が従来どおり実行できる
- 03 の NEXT_TASKS の 68) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/統合件数）を追記
- 次の最優先タスク（TASK69）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_build_artists_context_seed10.py --query "contemporary painting"
- （WSL）python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output
- （WSL）python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 69) artists回答QA統合CLIのbatch caseごとに回帰ガード適用を追加し、失敗検知をケース単位で固定化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- `run_artists_answer_qa_smoke.py --batch-manifest` で、case単位に `fail_on_regression` を適用し、差分悪化ケースのみを明確にfail化する。
- 日次batch実行時に「どのケースが回帰で落ちたか」をsummaryだけで追える状態にする。

参照ファイル：
- run_artists_answer_qa_smoke.py
- run_compare_artists_answers.py
- data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存単発モード（`--query` / `--context-path`）とbatch互換を壊さない

完了条件：
- batch manifest で `fail_on_regression` を default指定 + case上書きできる
- batch summary に `cases[].fail_on_regression_effective` / `cases[].guard_passed`（同等）を保存できる
- 回帰ケースのみ `case exit != 0` になり、非回帰ケースは `exit 0` を維持できる
- 03 の NEXT_TASKS の 69) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/失敗ケース）を追記
- 次の最優先タスク（TASK70）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task69_regression.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 70) artists回答QA統合CLIのbatch実行結果を集約JSONL化し、日次確認対象を1ファイルで追えるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- `run_artists_answer_qa_smoke.py --batch-manifest` の結果を、case単位JSONLとしても保存し、日次確認の差分追跡を簡素化する。
- batch summary JSONは維持しつつ、1行1caseの軽量導線を追加する。

参照ファイル：
- run_artists_answer_qa_smoke.py
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存単発モード（`--query` / `--context-path`）とbatch summary互換を壊さない

完了条件：
- batch実行時に集約JSONL（例: `artists_answer_qa_batch_cases_*.jsonl`）を保存できる
- 1行1caseで最低限 `case_id` / `question` / `query` / `context_path` / `exit_code` / `guard_passed` / `summary_path` を出力できる
- batch summary JSONに `batch_cases_jsonl_path`（同等）を保存できる
- 03 の NEXT_TASKS の 70) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/JSONLパス）を追記
- 次の最優先タスク（TASK71）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task69_regression.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 71) artists回答QA batch集約JSONLの軽量レポートCLIを追加し、失敗case一覧と子summary参照を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK70で追加した `artists_answer_qa_smoke_summary_*_cases.jsonl` を読み、失敗caseの切り分けを短時間で行える入口を作る。
- 日次運用で「どのcaseが落ちたか」「どのsummaryを開けばよいか」を1コマンドで把握できるようにする。

参照ファイル：
- run_artists_answer_qa_smoke.py
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*_cases.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存のbatch summary/JSONLスキーマ互換を壊さない（追加のみ）

完了条件：
- `python run_artists_answer_qa_batch_report.py --cases-jsonl "..."`（例）が実行できる
- `--latest` で最新 `*_cases.jsonl` を自動解決できる
- レポートに最低限 `total_cases` / `failed_cases` / `failed_case_ids` / `summary_paths_to_check`（同等）を保存できる
- 03 の NEXT_TASKS の 71) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK72）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed.json"
- （WSL）python run_artists_answer_qa_batch_report.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases.jsonl"
- （WSL）python run_artists_answer_qa_batch_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 72) artists回答QA batch集約JSONLから失敗case再実行manifestを生成するCLIを追加し、日次復旧導線を短縮する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK70/71で整備した `*_cases.jsonl` から失敗caseのみを抽出し、再実行用manifestを自動生成して運用復旧を短くする。
- 手動で失敗caseを拾い直す作業を減らし、再実行導線を1コマンドで固定する。

参照ファイル：
- run_artists_answer_qa_smoke.py
- run_artists_answer_qa_batch_report.py
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*_cases.jsonl
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存のbatch summary/JSONLスキーマ互換を壊さない（追加のみ）

完了条件：
- `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "..."`（例）が実行できる
- 失敗caseだけを含む再実行manifestを保存できる（最低限 `case_id/question/query/context_path/fail_on_regression`）
- `--latest` で最新 `*_cases.jsonl` を自動解決できる
- 失敗0件でもクラッシュせず、空manifest（または0件明示付きmanifest）を保存できる
- 03 の NEXT_TASKS の 72) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK73）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed.json"
- （WSL）python run_artists_answer_qa_retry_manifest.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases.jsonl"
- （WSL）python run_artists_answer_qa_retry_manifest.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 73) artists回答QA retry manifest をそのまま実行するワンショットCLIを追加し、失敗case復旧を1コマンド化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK72で生成した `*_retry_manifest.json` を直接実行し、失敗caseの復旧runまでを1コマンドで回せるようにする。
- 日次運用で「抽出→再実行」の手順分断をなくし、復旧導線を短縮する。

参照ファイル：
- run_artists_answer_qa_retry_manifest.py
- run_artists_answer_qa_smoke.py
- data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_*_cases_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存batch manifest/summary互換を壊さない（追加のみ）

完了条件：
- `python run_artists_answer_qa_retry_run.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `*_retry_manifest.json` を自動解決できる
- 失敗0件manifestでは no-op/skip を明示し、非0にしない
- retry run summary に `retry_manifest_path` / `executed_cases` / `wrapper_exit_code`（同等）を保存できる
- 03 の NEXT_TASKS の 73) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK74）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_retry_manifest.py --latest
- （WSL）python run_artists_answer_qa_retry_run.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases_retry_manifest.json"
- （WSL）python run_artists_answer_qa_retry_run.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 74) artists回答QA retry run summary の軽量レポートCLIを追加し、failed/recovered を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK73で生成される `artists_answer_qa_retry_run_summary_*.json` を読み、日次運用で「どのretry runが失敗/復旧したか」を短時間で把握できる入口を追加する。
- 子summary参照（child batch summary/cases jsonl）を1画面で辿れるようにする。

参照ファイル：
- run_artists_answer_qa_retry_run.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- retry run本体ロジックは変更しない（レポートCLIの追加のみ）

完了条件：
- `python run_artists_answer_qa_retry_run_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_summary_*.json` を自動解決できる
- レポートに最低限 `retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `all_passed` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 74) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK75）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_retry_run.py --latest
- （WSL）python run_artists_answer_qa_retry_run_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_artists_answer_qa_retry_run_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 75) artists回答QAの日次復旧ワンショットCLIを追加し、batch実行→report→retry manifest→retry run→retry report を1コマンド化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK70〜74で分離された運用CLIを1コマンド導線に統合し、日次の復旧手順を固定化する。
- 手動でのコマンド打ち間違い/実行漏れを減らし、summary確認を一箇所に集約する。

参照ファイル：
- run_artists_answer_qa_smoke.py
- run_artists_answer_qa_batch_report.py
- run_artists_answer_qa_retry_manifest.py
- run_artists_answer_qa_retry_run.py
- run_artists_answer_qa_retry_run_report.py
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存CLI本体ロジックは再利用し、重複実装しない

完了条件：
- `python run_artists_answer_qa_daily_recovery.py --batch-manifest "..."`（例）が実行できる
- 内部で以下を順次実行できる：
  - `run_artists_answer_qa_smoke.py --batch-manifest ...`
  - `run_artists_answer_qa_batch_report.py --cases-jsonl ...`
  - `run_artists_answer_qa_retry_manifest.py --cases-jsonl ...`
  - `run_artists_answer_qa_retry_run.py --retry-manifest ...`
  - `run_artists_answer_qa_retry_run_report.py --summary-path ...`
- daily summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存できる
- retry対象0件（no-op）でも正常終了（exit 0）し、summaryで判別できる
- 03 の NEXT_TASKS の 75) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/daily summaryパス）を追記
- 次の最優先タスク（TASK76）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"
- （WSL）python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 76) artists回答QA日次復旧ワンショットの軽量レポートCLIを追加し、daily summary から failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK75で生成される `artists_answer_qa_daily_recovery_summary_*.json` を読み、日次運用で「どこが失敗したか」「どの子summaryを開くべきか」を短時間で把握できる入口を追加する。
- daily復旧runの結果確認を1画面で固定化し、手動トレース時間を削減する。

参照ファイル：
- run_artists_answer_qa_daily_recovery.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- daily recovery本体ロジックは変更しない（レポートCLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_summary_*.json` を自動解決できる
- レポートに最低限 `all_passed` / `wrapper_exit_code` / `execution_order` / `failed_steps` / `child_summary_paths_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 76) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK77）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_task76_input.json"
- （WSL）python run_artists_answer_qa_daily_recovery_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_task76_input.json"
- （WSL）python run_artists_answer_qa_daily_recovery_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 77) artists回答QA日次復旧レポートのrollup CLIを追加し、failed step あり run を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK76で生成される `artists_answer_qa_daily_recovery_summary_*_report.json` を複数本まとめて読み、失敗stepを含むrunのみを抽出する。
- 日次運用で「要再対応runの一覧」と「参照先子summary」を1ファイルで確認できるようにする。

参照ファイル：
- run_artists_answer_qa_daily_recovery_report.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_*_report.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery / report CLI本体ロジックは変更しない（rollup CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20`（例）が実行できる
- rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
- `--latest-n` と `--search-dir` を使って対象範囲を調整できる
- 03 の NEXT_TASKS の 77) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK78）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"
- （WSL）python run_artists_answer_qa_daily_recovery_report.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 78) artists回答QA日次復旧レポートrollupから failed run 向け retry manifest を生成するCLIを追加し、要再対応runだけを即再実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK77で生成される `artists_answer_qa_daily_recovery_report_rollup_*.json` から `failed_runs[]` を抽出し、要再対応runの再実行manifestを自動生成する。
- 日次運用で「失敗run抽出→再実行対象作成」の手作業を減らし、復旧導線を短縮する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_report_rollup.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery/report/rollup CLI本体ロジックは変更しない（manifest生成CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_report_rollup_*.json` を自動解決できる
- manifestに最低限 `source_summary_path` / `retry_manifest_path` / `failed_step_names`（同等）を保存できる
- failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
- 03 の NEXT_TASKS の 78) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK79）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"
- （WSL）python run_artists_answer_qa_daily_recovery_report.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 79) artists回答QA日次復旧retry manifest（rollup起点）をそのまま実行するワンショットCLIを追加し、failed run再実行を1コマンド化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK78で生成される `artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json` を直接実行し、要再対応runのみを再実行する。
- 日次運用で「rollup抽出→retry manifest生成→再実行」の最終手順を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py
- run_artists_answer_qa_daily_recovery.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery / report / rollup / retry-manifest CLI本体ロジックは変更しない（実行ラッパー追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json` を自動解決できる
- 失敗0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
- 03 の NEXT_TASKS の 79) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK80）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 80) artists回答QA日次復旧retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK79で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する。
- 日次運用で「retry run実行後の確認」を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry run本体ロジックは変更しない（report CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
- レポートに最低限 `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 80) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK81）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 81) artists回答QA日次復旧retry run reportのrollup CLIを追加し、failed/recovered runの推移を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK80で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json` を複数本まとめて読み、失敗runを即時抽出する。
- 日次運用で「要再対応run一覧」と「参照先子summary」を1ファイルで確認できるようにする。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry run本体/報告CLIのロジックは変更しない（rollup CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20`（例）が実行できる
- rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存できる
- `--latest-n` と `--search-dir` を使って対象範囲を調整できる
- 03 の NEXT_TASKS の 81) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK82）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 82) artists回答QA日次復旧retry run report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK81で生成される `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する。
- 日次運用で「rollup確認→再実行manifest生成」を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py
- run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery/retry run/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` を自動解決できる
- 生成manifestに最低限 `source_summary_path` / `failed_case_ids` / `retry_manifest_path`（同等）を保存できる
- failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
- 03 の NEXT_TASKS の 82) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK83）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 83) artists回答QA日次復旧retry run report rollup起点manifestをそのまま実行するワンショットCLIを追加し、要再対応run再実行を1コマンド化する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK82で生成される `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を直接実行し、failed runのみを再実行する。
- 日次運用で「rollup確認→retry manifest生成→再実行」の最終手順を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py
- run_artists_answer_qa_daily_recovery.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery/retry run/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を自動解決できる
- failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
- 03 の NEXT_TASKS の 83) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK84）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 84) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK83で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する。
- 日次運用で「retry run実行後の確認」を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry run本体ロジックは変更しない（report CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
- レポートに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 84) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK85）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 85) artists回答QA日次復旧retry run summary report のrollup CLIを追加し、failed/recovered run推移を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK84で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json` を複数本まとめて読み、失敗runを即時抽出する。
- 日次運用で「要再対応run一覧」と「参照先子summary」を1ファイルで確認できるようにする。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry run本体/報告CLIのロジックは変更しない（rollup CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20`（例）が実行できる
- rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存できる
- `--latest-n` と `--search-dir` を使って対象範囲を調整できる
- 03 の NEXT_TASKS の 85) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK86）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 86) artists回答QA日次復旧retry run summary report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK85で生成される `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する。
- 日次運用で「rollup確認→retry manifest生成」の手作業を減らし、復旧導線を短縮する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery/retry run/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` を自動解決できる
- 生成manifestに最低限 `source_summary_path` / `failed_case_ids` / `retry_manifest_path`（同等）を保存できる
- failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
- 03 の NEXT_TASKS の 86) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK87）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 87) artists回答QA日次復旧retry run report rollup起点retry manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK86で生成される `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を直接実行し、failed runの再実行を1コマンド化する。
- 日次運用で「rollup確認→manifest生成→再実行」の最終手順を短縮する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py
- run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily recovery/retry run/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を自動解決できる
- failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
- 03 の NEXT_TASKS の 87) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK88）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 88) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK87で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する。
- 日次運用で「retry run実行後の確認」を1コマンド化する。

参照ファイル：
- run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry run本体ロジックは変更しない（report CLI追加のみ）

完了条件：
- `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
- レポートに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 88) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK89）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20
- （WSL）python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest
- （WSL）python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 89) artists回答QA retry-run導線（TASK85〜88）を短い入口でワンショット実行するCLIを追加し、日次復旧の運用手順を固定する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK85〜88 の個別CLI（rollup / retry manifest / retry run / retry run report）を短い入口で順次実行し、日次復旧を1コマンド化する。
- 手動実行漏れを減らし、stepごとのexitと生成物参照先をdaily chain summaryへ集約する。

参照ファイル：
- run_aqa_retry_run_report_rollup.py
- run_aqa_retry_run_report_rollup_manifest.py
- run_aqa_retry_run_report_rollup_retry_run.py
- run_aqa_retry_run_report_rollup_retry_run_report.py
- qa_artifact_utils.py
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- 既存長いCLI名は後方互換のため残し、短い入口はラッパーとして追加のみ
- 既存本体ロジックは再利用（subprocess）し、重複実装しない

完了条件：
- `python run_aqa_retry_run_daily_chain.py --latest`（例）が実行できる
- 内部で少なくとも以下を順次実行できる：
  - `run_aqa_retry_run_report_rollup.py`
  - `run_aqa_retry_run_report_rollup_manifest.py`
  - `run_aqa_retry_run_report_rollup_retry_run.py`
  - `run_aqa_retry_run_report_rollup_retry_run_report.py`
- chain summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存できる
- retry対象0件（no-op）でも chain は正常終了（exit 0）できる
- 03 の NEXT_TASKS の 89) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK90）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_latest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 90) artists回答QA retry-run daily chain summary の軽量レポートCLIを追加し、failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK89で生成される `artists_answer_qa_retry_run_daily_chain_summary_*.json` を短く集約し、失敗stepと参照先summaryを即確認できる導線を追加する。
- 日次運用で「daily chain 実行後の確認」を1コマンド化する。

参照ファイル：
- run_aqa_retry_run_daily_chain.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain本体ロジックは変更しない（report CLI追加のみ）

完了条件：
- `python run_aqa_retry_run_daily_chain_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_summary_*.json` を自動解決できる（`*_report.json` は除外）
- レポートに最低限 `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 90) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK91）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 91) artists回答QA retry-run daily chain report のrollup CLIを追加し、failed run推移を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK90で生成される `artists_answer_qa_retry_run_daily_chain_summary_*_report.json` を複数本まとめて読み、failed runを即時抽出する。
- 日次運用で「要再対応run一覧」と「参照先子summary」を1ファイルで確認できるようにする。

参照ファイル：
- run_aqa_retry_run_daily_chain_report.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_*_report.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/report本体ロジックは変更しない（rollup CLI追加のみ）
- `--latest` / `latest-n` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（例）が実行できる
- rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
- `--latest-n` と `--search-dir` を使って対象範囲を調整できる
- 03 の NEXT_TASKS の 91) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK92）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 92) artists回答QA retry-run daily chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK91で生成される `artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する。
- 日次運用で「rollup確認→retry manifest生成」の手作業を減らし、復旧導線を短縮する。

参照ファイル：
- run_aqa_retry_run_daily_chain_report_rollup.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` を自動解決できる
- 生成manifestに最低限 `source_summary_path` / `failed_step_names` / `retry_manifest_path`（同等）を保存できる
- failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
- 03 の NEXT_TASKS の 92) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK93）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20
- （WSL）python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 93) artists回答QA retry-run daily chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK92で生成される `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を直接実行し、failed runの再実行を1コマンド化する。
- 日次運用で「rollup確認→retry manifest生成→再実行」の最終手順を短縮する。

参照ファイル：
- run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py
- run_aqa_retry_run_daily_chain.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を自動解決できる
- failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
- 03 の NEXT_TASKS の 93) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK94）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20
- （WSL）python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 94) artists回答QA retry-run daily chain report rollup起点の復旧導線をワンショット化し、rollup→manifest→retry-run を1コマンドで順次実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK91〜93 の短い入口CLI（rollup / retry-manifest / retry-run）を一つのチェーンCLIで順次実行し、日次復旧の手順漏れを減らす。
- 実行結果を1つの chain summary に集約し、失敗stepと参照先を即追えるようにする。

参照ファイル：
- run_aqa_retry_run_daily_chain_report_rollup.py
- run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py
- run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py
- qa_artifact_utils.py
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存rollup/retry-manifest/retry-run本体ロジックは変更しない（実行ラッパー追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（例）が実行できる
- 内部で少なくとも以下を順次実行できる：
  - `run_aqa_retry_run_daily_chain_report_rollup.py`
  - `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py`
  - `run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py`
- chain summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存できる
- no-op（retry対象0件）でも chain は正常終了（exit 0）できる
- 03 の NEXT_TASKS の 94) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK95）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 95) artists回答QA retry-run daily chain recovery chain summary の軽量レポートCLIを追加し、failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK94で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json` を短く集約し、失敗stepと参照先summaryを即確認できる導線を追加する。
- 日次運用で「chain実行後の確認」を1コマンド化する。

参照ファイル：
- run_aqa_retry_run_daily_chain_recovery_chain.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存chain本体ロジックは変更しない（report CLI追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json` を自動解決できる
- report JSONに最低限 `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes`（同等）を保存できる
- 03 の NEXT_TASKS の 95) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/レポートパス）を追記
- 次の最優先タスク（TASK96）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 96) artists回答QA retry-run daily chain recovery chain report のrollup CLIを追加し、failed step推移を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK95で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*_report.json` を最新N件で集約し、failed runの推移を即確認できるようにする。
- 日次運用で「要再対応run一覧」と「参照先子summary」を1ファイルで確認できるようにする。

参照ファイル：
- run_aqa_retry_run_daily_chain_recovery_chain_report.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*_report.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/report本体ロジックは変更しない（rollup CLI追加のみ）
- `--latest-n` / `--search-dir` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（例）が実行できる
- rollup JSONに最低限 `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存できる
- `--latest-n` と `--search-dir` を使って対象範囲を調整できる
- 03 の NEXT_TASKS の 96) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK97）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 97) artists回答QA retry-run daily chain recovery chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK96で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する。
- 日次運用で「rollup確認→retry manifest生成」の手作業を減らし、復旧導線を短縮する。

参照ファイル：
- run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/recovery chain report/rollup本体ロジックは変更しない（manifest生成CLI追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` を自動解決できる
- 生成manifestに最低限 `source_summary_path` / `failed_step_names` / `retry_manifest_path`（同等）を保存できる
- failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる
- 03 の NEXT_TASKS の 97) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK98）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 98) artists回答QA retry-run daily chain recovery chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
------------------------------------------------------------------------------------------------
目的：
- TASK97で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` を直接実行し、failed runの再実行を1コマンド化する。
- 日次運用で「rollup確認→retry manifest生成→再実行」の最終手順を短縮する。

参照ファイル：
- run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py
- run_aqa_retry_run_report_rollup_retry_run.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存daily chain/recovery chain report/rollup/retry-manifest本体ロジックは変更しない（実行ラッパー追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する
- 既存の長いCLI名/短いCLI名の後方互換は壊さない（既存名は維持）

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` を自動解決できる
- failed run 0件manifestでは no-op成功（exit 0）し、summaryに `executed_runs=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`（同等）を保存できる
- 03 の NEXT_TASKS の 98) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK99）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025


========================
CODEX_SNIPPETS（頻出コピペ：ここだけ使えば回る）
========================

■ A0/A/B/Cの使い方）
私（人間）は、 A0（初回だけ）→A（毎回）→B（止める時）→C（エラー時） を貼るだけで回せる。

■A0）初回ブート（最初の1回だけ貼る：存在確認→開始）

あなたは実装AI（Codex）です。次の運用ルールに厳密に従ってください。
(1) 01_PROJECT_SPEC_CURRENT_FULL.docx がSSOT（唯一の正本）です。仕様の衝突が起きたら、まずSSOTを更新してから実装を変えてください（口頭だけで変えない）。
(2) 02_RAG_SPEC_DERIVED.md は索引（カード集）です。数値は転載せず、参照先として扱ってください。更新が必要なら提案して合意を取ってから。
(3) 03_STATE_SNAPSHOT_NEXT_TASKS.md が「今日やること」です。毎回これを起点に動いてください。
(4) 禁止：完成した機能を勝手に削除/無効化しない。削除/置換/挙動変更で機能が消える可能性がある場合は、削除対象・影響範囲・代替案を示し、合意を取ってから。
(5) 禁止：ドメイン専用ハードコードの増殖。改善は「頻出ドメイン×汎用ロジック」のみ。取れない分はログに残して割り切る。
(6) 重要：4章は「4-0共通→4-1〜」を分けて実装・検証。LLM加工（headline_ja等）は取得ループ内で逐次実行しない。

初回の最初に、次の存在確認をしてください（無ければ “最優先で作る/配置する計画” を出す）：
- 01_PROJECT_SPEC_CURRENT_FULL.docx
- 02_RAG_SPEC_DERIVED.md
- 03_STATE_SNAPSHOT_NEXT_TASKS.md
- data/gallery_lists/gallery_list_frieze_london.csv
- data/gallery_lists/gallery_list_liste.csv

確認後、03のNEXT_TASKSから最優先の [ ] を1つ選び、
(1)変更ファイル (2)変更点 (3)動作確認コマンド を短く計画として出してから実装してください。


■A）セッション開始（毎回冒頭に貼る）

参照優先順位・禁止事項 :  
参照優先順位は 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT） > 02_RAG_SPEC_DERIVED.md（索引） > 03_STATE_SNAPSHOT_NEXT_TASKS.md（進捗/次タスク）です。
仕様や判断を変える場合は、必ず先に01（SSOT）を更新してから実装を変えてください。
02は索引なので新仕様を追加しない。日々の作業ログと次タスクは03だけを更新してください。
既存機能の削除・無効化・置換で機能が消える可能性がある変更は、必ず事前に「削除対象/影響範囲/代替案」を提示して合意を取ってから行ってください。

運用ルール : 
あなたは実装AI（Codex）です。次の運用ルールに厳密に従ってください。
(1) 01_PROJECT_SPEC_CURRENT_FULL.docx がSSOT（唯一の正本）です。仕様の衝突が起きたら、まずSSOTを更新してから実装を変えてください（口頭だけで変えない）。
(2) 02_RAG_SPEC_DERIVED.md は索引（カード集）です。数値は転載せず、参照先として扱ってください。
(3) 03_STATE_SNAPSHOT_NEXT_TASKS.md が「今日やること」です。毎回これを起点に動いてください。
(4) 禁止：完成した機能を勝手に削除/無効化しない。削除/置換/挙動変更で機能が消える可能性がある場合は、削除対象・影響範囲・代替案を示し、合意を取ってから。
(5) 禁止：ドメイン専用ハードコードの増殖。改善は「頻出ドメイン×汎用ロジック」のみ。取れない分はログに残して割り切る。
(6) 重要：4章は「4-0共通→4-1〜」を分けて実装・検証。LLM加工（headline_ja等）は取得ループ内で逐次実行しない。

最初の作業：
この03の NEXT_TASKS から最優先の [ ] を1つ選び、(1)変更ファイル (2)変更点 (3)動作確認コマンド を短く計画として出してから実装してください。


■A-1）毎タスク（冒頭コピペ）
・設定されたタスクごとに毎回、以下を冒頭に貼る

運用ルールは前回と同じ（SSOT=01、索引=02、今日=03、機能削除禁止、ドメイン専用ハードコード禁止、LLM加工はPost-fetchのみ）。


■B）中断・締め（長めの中断 / handoff前 / 実行フェーズの区切りで貼る：03/04まとめ更新）

作業をここで区切ります。以下を実施してください。
(1) まず判定
  - 今回が「長めの中断」「handoff前」「実行フェーズの区切り」「2-4Task消化後」のいずれかなら、03/04を更新する
  - それ以外の小Task区切りなら、03/04更新は省略してよい

(2) 03を更新する場合
  - 02で該当CARD_IDを検索 → そのカードのSSOT参照に従って01の該当箇所を確認 → 01に根拠がある内容だけで03を更新（推測で更新しない）
  - LAST_UPDATED：更新
  - STATE_SNAPSHOT：最優先フェーズ / 直近目標 / 現在地を必要な範囲だけ更新
  - NEXT_TASKS：数Taskぶんをまとめて [x] 化してよい。新規タスクが確定したら追加し、優先度順に並べ替える
  - CHANGELOG：節目の作業内容をまとめて追記

(3) 04を更新する場合
  - 実行結果（コマンド / exit / summary / 生成物パス / 判断）を数Taskぶんまとめて追記する

(4) 変更ファイル一覧を出す（ファイル名だけでOK）
(5) 次にやる1手（コマンド含む）を1行で書く
(6) 次に取り組む NEXT_TASKS の番号を1つ選び、必要なら対応する「TASK n プロンプト全文」をこのチャットに貼って提示する
    - ユーザーはそれをそのまま次の依頼としてコピペする


■C）エラー相談（あなたが貼るテンプレ：省略せず全文コピペ）

いまの目的：
やった操作（コマンド）：
期待した結果：
実際の結果：
エラー全文（省略せずコピペ）：
環境：
- OS: Windows11 + WSL2 Ubuntu
- venv: .venv_art_pulse_editor
- 実行場所（pwd）:
直前に変えたファイル（あれば）：
依頼：
- 原因候補を3つに絞って優先順位を付けて
- 最小変更で修正して
- 同じコマンド再実行で直ったことを確認して

■T）TASK_REQUEST_TEMPLATE（任意：依頼文のブレ防止テンプレ）

今回やること：
- 目的：
- 触っていいファイル：
- 触ってはいけない/注意（SSOTの制約）：
- Done条件（これが満たされたら完了）：
- 最低スモークテスト（コマンド）：


========================
CHANGELOG（このファイルの更新履歴）
- 2026-03-05 JST: TASK228 実施。④ Exhibitions Image の completion closure memo を確定し、STATE_SNAPSHOT を `completion closure 完了` へ更新。TASK227結果（`PASS_FOR_CLOSURE` / `CURRENT_FORMAL_STILL_VALID` / Baton再発0 / Athr再出現0 / duplicate 0）を反映。final isolated rerun retry の新規1件は `SAFE_BUT_NOT_NEEDED` として formal 不採用を明記。次タスクを `TASK229（⑤ Exhibitions Text kickoff / spec start）` に更新。
- 2026-03-04 JST: TASK182 実施。TASK181設計を反映して03/04同期方針を更新（現在地を「3ギャラリー + Unit-F + Unit-L 正式採用済み」へ更新、anti-mixing短縮文言を固定、次の最優先をTASK183 Safe群レーン開始準備に一本化）。
- 2026-03-02 JST: TASK125 文書同期を実施。TASK124 close（verdict=close / remaining_rerun_targets_count=0）を 03/04 に反映し、T123は低優先維持のまま次の最優先を TASK125（Exhibitions Text再開ブートストラップ）へ更新。
- 2026-03-02 JST: TASK123A 文書同期を実施。TASK122完了（under-target最小rerun）を 03/04 に反映し、T123は低優先維持のまま、次の最優先を TASK124（under-target close判定）へ更新。
- 2026-03-02 JST: TASK121を実施。T120再分類を正としてA/Dを除外し、B/Cのみの under-target 再抽出CSVを再確定（The Approach 3URLを維持）。次の最優先をTASK122に更新。
- 2026-03-02 JST: TASK120を実施（Exhibitions under-target再評価）。A/B/C/Dを再分類し、A=3/B=3/C=0/D=0で確定。次の最優先をTASK121（targets再確定）に固定。
========================
- 2026-03-02 JST: T-118D/T-118E/T-120 の改善結果を反映し、Exhibitions画像RAGの現在地を under-target 再棚卸しフェーズへ更新（次タスクは under-target CSV再評価→対象再確定→必要最小限再実行）
- 2026-03-02：TASK116 実行結果の記録を補正。`NEXT_TASKS 116) を [x]` に更新し、`seed=49 / ge1=37 / ge_target=37 / saved=37 / failed=12` を確定値として追記。あわせて STATE_SNAPSHOT に「MAX7は上限であり全ギャラリー7件保証ではない」前提を明記し、LAST_UPDATED を更新。
- 2026-03-02：TASK115 実施完了（Exhibitions Text SSOT Recovery）。preflight 2連続PASS後、監査7項目＋現状症状を一括是正。Before/After は `rows 118→59`、`非2025 source_url 15→0`、`source_url重複 52→0`、`date充足 0→57`、`headline 0→59`、`summary 0→59`、`participating artists行 0→22`、`sources保持 0→59`。実装は `phase1_exhibitions_text_utils.py` 追加、`run_phase1_seed10.py` 連携、`run_enrichment_seed10_apply.py` 追加、`run_phase1_exhibitions_text_raw_cleanup.py` 追加。guardは `phase1_guard_summary_2025_20260301T164759Z.json`（pass）、R2同期は raw/derived とも `dry-run -> guarded apply` 実施。NEXT_TASKSは 115) を [x]、次を 116) に更新。
- 2026-03-01：重大修正。SSOT（4-2/5-2）の `EXHIBITION_IMAGE_PER_EXHIBITION_MAX=1` に合わせ、Exhibitions画像収集を「1展示=1画像」に強制。collector既定値を1へ変更し、既存メタ/画像も source_url単位1件へ補正（余剰は `_trash/task_exhibition_one_image_enforce_20260301_232524/` へ退避）。R2 derived同期で削除反映（pruned=147）。
- 2026-03-01：運用強化。`docs/RAG_EXTRACTION_BREAKDOWN_JA.md` への日本語内訳記録ルールを「全RAGカテゴリ（Artists/Exhibitions/Tarutani、画像/テキスト/ベクター、同期）へ常時適用」に明文化（02/03/04整合）。
- 2026-03-01：TASK114 実施完了。Exhibitions画像を10ギャラリー拡張（各ギャラリー最大5 exhibition、5/5済み除外）で実行し、`seed=36 / ge1=28 / ge_target=16 / saved=103`。判定値は `ge_1率=0.7778`（>=0.70）、hero/profile/logo混入0、重複(URL/payload)0で通過。`reextract_targets_exhibitions_image_task_t114.csv` は未達のみ20件へ縮約。guardは `phase1_guard_summary_2025_20260301T134852Z.json`（pass）、R2 derived同期は `uploaded=146 / pruned=0 / failed=0`。NEXT_TASKSは 114) を [x]、次を 115) に更新。
- 2026-03-01：TASK113 実施完了。`reextract_targets_exhibitions_image_task_t113.csv` を生成し、10ギャラリー×各1exhibitionで Exhibitions画像を最小拡張実測。結果は `seed=10 / ge1=10 / ge_target=8 / saved=42`、判定値は「抽出0件=0 / hero-profile-logo混入=0 / 重複(URL/payload)=0」で通過。guardは `phase1_guard_summary_2025_20260301T131452Z.json`（pass）、R2 derived同期は `uploaded=44 / pruned=0 / failed=0`。NEXT_TASKSは 113) を [x]、次を 114) に更新。
- 2026-03-01：TASK112 実施完了。Exhibitions画像の汎用collector/reportを新規追加（`run_phase1_seed10_exhibition_image_collect.py` / `run_phase1_seed10_exhibition_image_collect_report.py`）。最小実測（liste / A+ Works of Art / 1exhibition）で `5/5`、`hero/profile/logo` 混入0を確認。拡張子命名不整合（`..jpg`）を同タスク内で修正し再抽出。R2は `derived dry-run -> guarded apply` で新規反映（uploaded=7 / pruned=5）、guardは `guard_passed=true`（`phase1_guard_summary_2025_20260301T125846Z.json`）。NEXT_TASKS は 112) を [x]、次を 113) へ更新。
- 2026-03-01：TASK110 実施完了。未達3ギャラリー（Athr / A+ Works / Addis）の根因を `DUPLICATE_TEXT_HASH_DOMINANT` で確定。上位reason件数（26/28/25）を記録し、6-2準拠で追加改修は見送り（理由付き確定）。`reextract_targets_artists_text_task_t109.csv` は `closed_duplicate_text_hash_dominant` に更新。guardは `guard_passed=true`（`phase1_guard_summary_2025_20260301T073600Z.json`）。次タスク 111) を追加。
- 2026-03-01：TASK109 実施完了。preflight 2連続PASS後に Artists text を max=80 再実行。artist単位coverageは 7/10 gallery が 0.70以上（70.00%）で、未達は Athr / A+ Works of Art / Addis Fine Art の3件を `data/gallery_lists/reextract_targets_artists_text_task_t109.csv` へ最小化して確定。guardは `guard_passed=true`、R2は `raw dry-run -> guarded apply`（uploaded=0 / skipped=6 / pruned=0）を記録。次タスク 110) を追加。
- 2026-03-01：TASK108 を完了反映。NEXT_TASKS の 108) を [x] に更新し、実行結果（`artists_records_saved_total=42` / guard exit 0）を記録。TASK末尾テンプレを「【タスク終了時に行うこと】」へ置換し、03更新の順序（02→01→03）を固定化。次タスク 109) を追加。
- 2026-03-01：TASK107フォローアップ。`max-artists-per-gallery` の上限適用位置を修正（候補抽出段階→保存成功件数段階）。再実測 `python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` で artists_text 新規+4（The Approach 3, Gallery Baton 1）を確認。`guard_passed=true`。
- 2026-03-01：TASK107 実施完了。`run_phase1_seed10.py` に `--max-artists-per-gallery` と skip registry 共通適用（Artists/Exhibitions text）を追加し、初回最小スコープ `--include-artists-text --max-artists-per-gallery 1` で実行。`skip_registry applied: before=10 after=8 skipped=2`、`guard_passed=true`、R2は auto-sync `status=ok` + 手動 `raw dry-run -> guarded apply`（uploaded=0 / skipped=6 / pruned=0）を確認。NEXT_TASKSは 107 を [x]、次を 108（Exhibitions画像の最小開始）へ更新。
- 2026-03-01：03の本タスク復帰に合わせて TASK107 を再定義。内容を「rollup補正」から「10ギャラリー Artistsテキスト抽出（共通スキップ適用 + 共通R2同期適用確認）」へ軌道修正し、`CODEX_TASK_PROMPTS` に新テンプレ（`RECOMMENDED_MODE` / 章ID明示 / 固定5項目出力）準拠のTASK107全文を追加。あわせて `skipped_galleries_registry` の共通適用（Artists/Exhibitions text/image）とR2 guarded同期の全カテゴリ共通適用をNEXT_TASKSへ明記。
- 2026-02-26：artists抽出ルールを固定化。`run_phase1_seed10.py` の artistsリンク抽出で一覧ページURLフォールバックを禁止し、詳細ページURLのみ巡回するよう修正（候補0件時は `NO_ARTIST_DETAIL_LINKS` を記録）。`run_phase1_seed10_artist_image_collect.py` も一覧ページを直接画像抽出対象にせず、一覧URL入力時は詳細URL抽出→詳細ページ巡回へ変更。既存実行確認: `python run_phase1_seed10.py --include-artists-text` / `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` / `python run_compare_phase1_guard.py --target-year 2025` すべて exit 0。
- 2026-02-26：環境フォールバック対応。`run_phase1_seed10.py` は `bs4` 未導入環境でも動作するよう標準ライブラリHTMLパーサへフォールバック可能化。あわせて exhibitions_text / artists_text の内訳を summary/console に追加（fair/gallery単位の対象gallery数・成功gallery数・抽出件数・成功率%）。`python run_phase1_seed10.py --include-artists-text` 実行で `[BREAKDOWN][exhibitions_text]` / `[BREAKDOWN][artists_text]` 出力を確認（exit 0）。
- 2026-02-26：運用ルール追補（exhibitions/text適用）。「RAG抽出時の内訳」に `取得件数` と `成功率%` を必須化し、画像/テキストの両方へ適用する文言へ更新（SSOT `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` 6-3、索引 `docs/02_RAG_SPEC_DERIVED.md` CARD_ID:14）。実装は `run_phase1_seed10.py` に exhibitions_text / artists_text の fair/gallery内訳（対象gallery数・成功gallery数・抽出件数・成功率%）を追加、`run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` は取得画像枚数 + 成功率% 表示へ更新。
- 2026-02-26：運用ルール追補。RAG抽出の「対象内訳」に `取得画像枚数` と `取得率%` を必須追加。SSOT（`docs/01_PROJECT_SPEC_CURRENT_FULL.docx` 6-3）/索引（`docs/02_RAG_SPEC_DERIVED.md` CARD_ID:14）文言を更新し、実装側も `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` で `images_saved_total` と `%` 表示・保存を追加。
- 2026-02-26：運用ルール追加（恒久化）。RAG抽出時は常に対象内訳（最低: fair/gallery単位の対象人数・成功人数・成功率）を summary/report に残す方針を明文化。SSOT（`docs/01_PROJECT_SPEC_CURRENT_FULL.docx` 6-3）と索引（`docs/02_RAG_SPEC_DERIVED.md` CARD_ID:14）へ追記し、実装側も `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` / `run_phase1_seed10_artist_image_collect_report_rollup.py` に `fair_breakdown` / `gallery_breakdown` を追加。`python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` と `python run_phase1_seed10_artist_image_collect_report.py --latest` で gallery内訳表示を確認（いずれも exit 0）。
- 2026-02-26：TASK 106 完了（通信回復後の再実測）。`curl -I https://example.com` は exit 0、`socket.gethostbyname('example.com')` は exit 0 で通信回復を確認。`python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` は exit 0 で summary保存（`network_dns_probe_ok=true` / `seed_artist_count=81` / `artists_with_ge_1_image=70` / `artists_with_ge_target_images=66` / `success_rate_ge_target=0.814815` / `threshold_passed=true`）。`report` / `rollup` / `guard` は各 exit 0。あわせて rollup が最新成功reportを推移へ取り込めない不整合（最新判定）を確認し、次タスクを TASK107（rollup最新判定補正）に設定。
- 2026-02-26：TASK 106 実施（環境ブロッカー継続確認）。必須通信確認 `curl -I https://example.com` は exit 6、`socket.gethostbyname('example.com')` は exit 1 で DNS 未回復を再確認。`python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` は exit 0 で summary保存（`network_dns_probe_ok=false` / `seed_artist_count=81` / `artists_with_ge_1_image=0` / `artists_with_ge_target_images=0` / `success_rate_ge_target=0.0`）。`report` / `rollup` / `guard` は各 exit 0。目標再開条件未達のため TASK106 は継続管理（[ ]）とし、次タスクを TASK107（環境回復直後の汎用改善）に設定。
- 2026-02-26：TASK 105 実施（DNS/外向き通信ブロッカー再確認）。必須通信確認 `curl -I https://example.com` は exit 6、`socket.gethostbyname('example.com')` は exit 1 で DNS 未回復を確認。再実測 `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` は exit 0 で summary保存（`network_dns_probe_ok=false` / `seed_artist_count=81` / `artists_with_ge_1_image=0` / `artists_with_ge_target_images=0` / `success_rate_ge_target=0.0`）。`run_phase1_seed10_artist_image_collect_report.py --latest`（exit 0）、`run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（exit 0）、`run_compare_phase1_guard.py --target-year 2025`（exit 0）を確認。次タスクは環境回復後の再実測再開（TASK106）へ。
- 2026-02-19：03 統合最終版（省略ゼロ）を確定。A0/A/B/C と TASK 1〜7 を同一ファイルに統合。
- 2026-02-19：TASK 3 実施。run_phase1_seed10.py を追加し、seed10（Frieze5+Liste5）実行入口と成果物保存（raw/logs）を作成。次は TASK 4（再実行スキップ成立）。
- 2026-02-19：TASK 4 実施。run_phase1_seed10.py に台帳再利用（visited_pages/failed_fetches）と既存text_hashスキップを実装し、同一コマンド2回実行でスキップログを確認。次は TASK 5（失敗ログ運用の整備）。
- 2026-02-19：TASK 5 実施。失敗理由を reason_code（DNS_ERROR/HTTP_429等）で正規化し、attempt_count/last_attempt_at を failed_fetches に保存。クールダウン＋再試行上限で再実行時の無限ループを防止。次は TASK 6（Enrichment導線）。
- 2026-02-19：C対応（saved=0切り分け）。curl/socket/resolv.confでDNS切り分け後、失敗台帳のクールダウン影響を解除して再実行し saved=64 / skipped=14 を確認。原因は「ネットワーク経路（sandbox制約）＋既存失敗台帳クールダウン」の複合。
- 2026-02-19：TASK6前の認識合わせ。run_summary/コンソールに existing/new/after-run 指標を追加し、saved=0でも既存raw件数が明確に分かるよう修正。visited_pages / failed_fetches の保存形式をSSOT準拠のdict（キー: page_url_hash / fail_hash）へ統一。
- 2026-02-19：TASK 6 実施。run_enrichment_seed10.py を追加し、Post-fetchで raw（64件）を読み込み、headline_ja/summary_ja 未付与の enrichment requests（64件）と summary を生成。次は TASK 7（Tarutani_Text着手前質問）。
- 2026-02-22：TASK 7 実施。ユーザー回答の配置（data/Tarutani_data/{Series_Name}/Text/{Text_File}、docx/pdf）で run_tarutani_text_import.py を作成し、Tarutani_Text を16件取り込み（jsonl/summary生成）。次は TASK 8（Tarutani_Textの事後Enrichment入口）。
- 2026-02-22：TASK 8 実施。run_enrichment_tarutani_text.py を追加し、tarutani_text.jsonl（16件）から headline_ja 未付与かつ text 非空の候補（7件）を抽出して requests/summary を生成。次は TASK 9（headline_ja実生成とjsonl反映）。
- 2026-02-22：整理タスク実施。SSOT 5-5 に Tarutani_data のR2正本運用（source_pathメタ保持 / Git非コミット方針）を追記し、run_tarutani_r2_sync.py を追加。dry-runで 16ファイル / 14.59MB を確認（本実行は未実施）。
- 2026-02-22：Tarutani R2 sync 実行確認。apply 1回目で uploaded=16 / failed=0、2回目で skipped=16 / failed=0 を確認（冪等）。TASK9メモを更新。
- 2026-02-22：TASK 9 実施。run_enrichment_tarutani_text_apply.py を追加し、headline_ja を7件生成して tarutani_text.jsonl に反映（failed=0）。再実行で updated=0 を確認。次は TASK 10（Tarutani_TextのEmbedding/Index入口）。
- 2026-02-22：SSOT改定。TarutaniRAGに限りPDF本文抽出を標準実装化（未実装理由の一律text空を禁止）し、TASK 9.5（PDF抽出実装＋バックフィル）をNEXT_TASKS/CODEX_TASK_PROMPTSへ追加。
- 2026-02-24：TASK 50 実施。`run_phase1_seed10.py` に `--include-artists-text` を追加し、artists_text の最小取得入口（raw保存/専用visited・failed台帳/summary反映）を実装。既存exhibitions既定挙動は維持し、`python run_phase1_seed10.py` / `python run_phase1_seed10.py --include-artists-text` / 再実行のすべてで exit 0 を確認。
- 2026-02-24：TASK 51 実施。`run_phase1_seed10.py` のCSV読込を任意3列目 `artists_url` 対応へ拡張し、artists取得は `artists_url` 優先 / `exhibitions_url` fallback で解決するよう変更。summaryに `artists_list_source_counts` / `artists_list_url_artists_url_used` / `artists_list_url_exhibitions_fallback_used` を追加し、既存exhibitions既定挙動と guard互換（exit 0）を維持。
- 2026-02-24：TASK 52 着手。seed10対象行の `artists_url` 補完状況は確認済み（10/10）。ただし実行環境のDNS/外向き接続制約で artists取得は `failed_new`→`cooldown skip` となり、`new_saved>0` 検証は未達（継続中）。
- 2026-02-24：03整備。`TASK 53` が NEXT_TASKS / CODEX_TASK_PROMPTS に未反映だったため追記し、再開時の実行手順（通信確認→artists再実行→summary確認）を固定化。
- 2026-02-24：TASK 61 実施。`run_compare_artists_answers.py` を追加し、query再生成 / context固定の差分比較（`answer_chars` / `evidence_count` / `mismatch_fields`）を1コマンド化。実行結果は `artists_text_answer_compare_20260224T105153Z.json`（`mismatch_fields=['answer_chars','numeric_tokens']`）として保存し、次タスク（TASK62: 最小出力ガード）を追加。
- 2026-02-24：TASK 62 実施。`run_answer_artists_seed10.py` に `--fail-on-invalid-output` を追加し、`answer` 非空 / `evidence` 非空 / 必須根拠キー存在の最小ガードを実装。summaryへ `output_valid` / `invalid_reasons` を保存し、正常ケース（exit 0）と無効コンテキストケース（exit 2）を確認。次タスク（TASK63: 回答比較の最小回帰ガード）を追加。
- 2026-02-24：TASK 63 実施。`run_compare_artists_answers.py` に `--fail-on-regression` を追加し、差分と回帰を分離。`answer_status` 悪化 / `output_valid` 悪化 / `evidence_count` 減少で `regression_reasons` を記録し、`--fail-on-regression` 指定時のみ回帰で exit 2 にした。通常系は exit 0、無効context再現では `guard_passed=false` / `regression_reasons=['output_valid_regressed:true->false','evidence_count_decreased:5->1']` / exit 2 を確認。次タスク（TASK64: QA統合スモークCLI）を追加。
- 2026-02-24：TASK 64 実施。`run_artists_answer_qa_smoke.py` を追加し、context build→answer（`--fail-on-invalid-output`）→compare（`--fail-on-regression` 任意）を1コマンド化。QA summaryへ `all_passed` / `steps[].name|command|exit_code|output_paths` / `wrapper_exit_code` を保存し、通常実行・回帰ガード付き実行とも exit 0、`run_compare_phase1_guard.py --target-year 2025` も exit 0 を確認。次タスク（TASK65: 根拠整形フォールバック最小強化）を追加。
- 2026-02-24：TASK 65 実施。`run_answer_artists_seed10.py` に evidence整形フォールバック（excerpt欠落時 `headline_ja`→raw `text` 断片、headline欠落時 raw `headline_ja`→excerpt先頭）を追加。summaryへ `evidence_fallback_excerpt_count` / `evidence_fallback_headline_count` / `evidence_source_row_missing_count` を保存し、通常ケース（exit 0）と欠落再現ケース（`/tmp/artists_context_task65_missing_excerpt_headline.json`、fallback件数=2/2、exit 0）を確認。次タスク（TASK66: QA統合CLIのcontext固定再現モード）を追加。
- 2026-02-24：TASK 66 実施。`run_artists_answer_qa_smoke.py` に `--context-path` を追加し、`--query` と排他で `query_rebuild` / `fixed_context` の2モード運用を実装。fixed_contextでは context build/compare を `skipped` とし、`--fail-on-regression` は warning-only（`fail_on_regression_ignored_without_query`）で継続。summaryへ `qa_input_mode` / `context_path_effective` / `query_effective` / `steps[].status` / `errors` を追加し、query/fixed双方の実行（exit 0）と引数エラー（exit 1）、guard互換（exit 0）を確認。次タスク（TASK67: 複数query一括実行モード）を追加。
- 2026-02-24：TASK 67 実施。`run_artists_answer_qa_smoke.py` に `--batch-manifest`（JSON/JSONL）を追加し、複数ケースの一括実行を実装。batch summaryへ `total_cases` / `passed_cases` / `failed_cases` / `cases[].summary_path` / `cases[].exit_code` を保存。query系ケースはDNS制約下で exit 1（context_build失敗）だったが、fixed_context単発とfixed_context batch（2件）は exit 0 を確認し、単発モード後方互換と guard互換（exit 0）を維持。次タスク（TASK68: evidence重複統合と表示順安定化）を追加。
- 2026-02-24：TASK 68 実施。`run_answer_artists_seed10.py` に evidence 安定ソート（score降順+tiebreak）と `source_url+record_id` 重複統合を追加し、summaryへ `evidence_dedup_removed_count` / `evidence_sorted` を保存。query系コマンドはDNS制約で exit 1 だったため、fixed_context実行（exit 0）と重複注入context（`/tmp/artists_context_task68_dedup.json`、`evidence_dedup_removed_count=1`）で機能成立を確認。guard互換（exit 0）を維持し、次タスク（TASK69: batch case単位回帰ガード）を追加。
- 2026-02-24：TASK 69 実施。`run_artists_answer_qa_smoke.py` のbatch case summaryに `fail_on_regression_effective` / `guard_passed`（取得可能時）/ `compare_summary_path` / `compare_exit_code` / `regression_reasons` / `case_failure_kind` を追加し、manifest default + case override の実効値を保存。`sample` と `/tmp/artists_answer_qa_batch_manifest_task69_regression.json` の2本を実行し、case単位で `query_rebuild_failed` と `fixed_context pass` を識別できることを確認（DNS制約でquery系は exit 1、guard互換は exit 0）。次タスク（TASK70: batch結果JSONL集約）を追加。
- 2026-02-24：TASK 70 実施。`run_artists_answer_qa_smoke.py` のbatchモードに case集約JSONL出力（`{summary_stem}_cases.jsonl`）を追加し、1行1caseで `case_id/question/query/context_path/exit_code/guard_passed/summary_path`（+ `qa_input_mode` など補助項目）を保存。batch summaryへ `batch_cases_jsonl_path` / `batch_cases_jsonl_written` / `batch_cases_jsonl_count` を追加し、fixed_context batch（`/tmp/artists_answer_qa_batch_manifest_task67_fixed.json`）で exit 0・JSONL 2行を確認。sample manifest は DNS制約で exit 1 だがJSONL生成は維持し、guard互換（exit 0）を維持。次タスク（TASK71: batch JSONL軽量レポートCLI）を追加。
- 2026-02-24：TASK 71 実施。`run_artists_answer_qa_batch_report.py` を追加し、`*_cases.jsonl` から `total_cases/failed_cases/failed_case_ids/summary_paths_to_check` を抽出する軽量レポート導線を実装。`--cases-jsonl` と `--latest` の両方を確認し、固定batchケースで exit 0・`artists_answer_qa_smoke_summary_task71_batch_fixed_cases_report.json` 生成を確認。guard互換（exit 0）を維持し、次タスク（TASK72: 失敗case再実行manifest生成）を追加。
- 2026-02-24：TASK 72 実施。`run_artists_answer_qa_retry_manifest.py` を追加し、`*_cases.jsonl` から失敗case（`exit_code != 0`）のみを抽出して再実行manifestを生成。caseごとに `case_id/question/query/context_path/fail_on_regression` を保存し、失敗0件でも `cases=[]` + `notes=['no_failed_cases_found']` で exit 0 を維持。`--cases-jsonl` / `--latest` を確認し、guard互換（exit 0）を維持。次タスク（TASK73: retry manifest ワンショット実行CLI）を追加。
- 2026-02-25：TASK 73 実施。`run_artists_answer_qa_retry_run.py` を追加し、retry manifest から QA batch をワンショット再実行できる入口を実装（`--retry-manifest` / `--latest` 排他、親exitは 0/1 正規化）。`cases=[]` manifest は no-op 成功（`executed_cases=0` / `notes=['no_failed_cases_in_manifest']`）で exit 0、無効contextの `/tmp/artists_answer_qa_retry_manifest_task73_invalid.json` では `child_batch_exit_code=1` として exit 1 を確認。summaryへ `retry_manifest_path` / `executed_cases` / `wrapper_exit_code` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` を保存し、guard互換（`python run_compare_phase1_guard.py --target-year 2025` exit 0）を維持。次タスク（TASK74: retry run 軽量レポートCLI）を追加。
- 2026-02-25：TASK 74 実施。`run_artists_answer_qa_retry_run_report.py` を追加し、retry run summaryの軽量レポート導線（`--summary-path` / `--latest`）を実装。`retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `all_passed` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `notes` を `*_report.json` に保存し、`--latest` は `_child_batch_summary` / `_report` を除外して本体summaryのみ解決するよう固定。動作確認は `retry_run --latest` / `retry_run_report --summary-path` / `retry_run_report --latest` / `run_compare_phase1_guard.py --target-year 2025` すべて exit 0。次タスク（TASK75: 日次復旧ワンショットCLI）を追加。
- 2026-02-24：TASK 52/53 完了。外向き通信確認（curl/socket）通過後、artists failed台帳のcooldown影響を除外して再実行し、`run_summary_seed10_2025_task53_first_pass.json` で `artists_records_saved_total=81` を確認。2回目実行で artists `skipped=82` を確認し、guard互換（exit 0）を維持。
- 2026-02-23：TASK 9.5 実施。run_tarutani_text_pdf_backfill.py でTarutaniRAGのPDF 9件を本文抽出してバックフィル（still_empty=0）。続けて Enrichment requests再生成（candidates=9）→ applyで headline_ja を9件更新（failed=0）。次は TASK 10（Embedding/Index入口）。
- 2026-02-23：運用メンテ実施。`私とあなたの物語り ／水谷イズル(アーティスト),2020.pdf` のレコードを削除済みPDFから新規DOCX（`私とあなたの物語り_水谷イズル_2020.docx`）へ差し替え、text再抽出（1477文字）と headline_ja 再生成（updated=1）を反映。
- 2026-02-23：SSOT改定。TarutaniRAGのEmbedding方針を更新し、「先頭2000字1本」ではなく「1000字チャンク＋200字オーバーラップで複数埋め込み」を5-9へ追記。
- 2026-02-23：TASK 10 実施。run_vectorize_tarutani_text.py を追加し、Tarutani_Text 16件をチャンク分割（76チャンク）で埋め込み生成（embedded=76 / failed=0）。index/meta/summary/manifest を data/Tarutani_data/vector/ に保存。次は TASK 11（検索スモークCLI）。
- 2026-02-23：TASK X 実施。SSOT 5-9に埋め込みメタ `text_len` / `embed_input_len` / `is_truncated` を明記し、run_vectorize_tarutani_text.py のmeta出力へ反映（76件すべてで項目確認）。
- 2026-02-23：TASK X-2 実施。SSOT 5-5/5-7/5-8 に共通ストレージ方針（source/derived/vector=R2正本、local=dataキャッシュ、重要ログR2 logs推奨）とmanifest最低項目を追記。run_tarutani_r2_sync.py を `--scope source|derived|logs|all` 対応へ拡張し、`tarutani/{source,derived,logs,vectors}/...` へ同期可能化。検証: derived 初回 uploaded=20→再実行 skipped=20、logs 初回 uploaded=8→再実行 skipped=8（+新規2）。
- 2026-02-23：TASK X-3 実施。SSOT 5-1/5-3（Exhibition/Artist保存章）へ、5-7/5-8参照・保存分類（source/derived/logs/vectors）・カテゴリ分離キー・manifest準拠の最小追記を追加。02のCARD 04/05/15を01準拠で索引更新。03に運用メモを追記。
- 2026-02-23：TASK 11 実施。run_search_tarutani_text.py を追加し、Tarutani_Text index+meta から RETRIEVAL_QUERY で top-k 検索を実行。query=「曲線と直線」で source_path/chunk_index/score を確認し、search results/summary を保存。次は TASK 12（機能⑤向けコンテキストJSON整形）。
- 2026-02-23：検索品質調整（Tarutani_Text）。SSOTへ「source_path優先度プロファイル + max_per_source」方針を追記し、run_search_tarutani_text.py を設定駆動で拡張。`曲線と直線` で `曲線と直線_概要.docx` を1位、`垂谷_ステートメント.docx` を2位で確認。
- 2026-02-23：検索プロファイル再調整。`config/tarutani_text_search_profile.json` から補完資料の減点ルールを除外し、上位2件（概要/ステートメント）優先は維持。3位以下は重みなしのクエリ素点で可変（同一source偏り抑制 `max_per_source=1` は維持）。
- 2026-02-23：検索プロファイル微調整。`垂谷_ステートメント.docx` の `score_boost` を 0.04 に調整し、query=「曲線と直線」で 1位 `曲線と直線_概要.docx` / 2位 `垂谷_ステートメント.docx` を再確認。
- 2026-02-23：TASK 12 実施。run_build_tarutani_context.py を追加し、TASK11検索結果（top-k）を機能⑤向け context JSON に整形。query=「曲線と直線」で `source_path/chunk_index/score/excerpt` を含む context と summary を保存（k_returned=5, empty_excerpt=0）。次は TASK 13（回答スモークCLI）。
- 2026-02-23：TASK 13 実施。run_answer_tarutani_advisor.py を追加し、TASK12 context を使って機能⑤向け回答をCLI生成。question=「曲線と直線の要点を教えて」/ query=「曲線と直線」で回答本文+根拠（source_path/chunk_index/score/excerpt）を output JSON に保存（k_used=5, answer_chars=396）。次は TASK 14（context固定の再現モード）。
- 2026-02-23：回答品質調整（Tarutani機能⑤）。SSOTに「数値競合時は最新要約資料+rank上位優先」を追記し、run_build_tarutani_context.py の excerpt デフォルトを 900 へ拡張、run_answer_tarutani_advisor.py に競合解決プロンプト（rank優先）を追加。再実行で「約700名」を採用し「180名」は採用しないことを確認。
- 2026-02-23：TASK 14 実施。run_answer_tarutani_advisor.py に `--context-path` を追加し、query再生成モードと排他で context固定再現モードを実装。`--context-path data/Tarutani_data/context/tarutani_text_context_20260223T123040Z.json` で `context_input_mode=fixed_context`、`--query "曲線と直線"` で `context_input_mode=query_rebuild` を確認し、summaryで両モード識別できることを確認。次は TASK 15（回答比較レポートCLI）。
- 2026-02-23：TASK 15 実施。run_compare_tarutani_answers.py を追加し、query再生成とcontext固定を1回で比較可能化。`--question "曲線と直線の要点を教えて" --query "曲線と直線" --context-path "...123040Z.json"` で実行し、回答本文長（585/482）・根拠件数（5/5）・主要数値（700=True/True, 180=False/False）をサマリ保存。次は TASK 16（差分ガード）。
- 2026-02-23：TASK 16 実施。run_compare_tarutani_answers.py に `--fail-on-mismatch` を追加し、summary へ `guard_passed` / `mismatch_fields` / `watch_numbers` を保存。最新contextでは `guard_passed=true` で exit 0、旧contextでは `mismatch_fields=['contains_700','contains_180']` で exit 2 を確認。次は TASK 17（数値ウォッチ設定の外出し）。
- 2026-02-23：優先順位見直し。TASK 17 を Tarutani guard profile 設定化から「Phase1本体（Exhibitions/Artist）へ復帰する準備」へ置換。旧TASK 17 は Backlog（後回し/保留）へ退避し、Tarutani側は当面保守モードとした。
- 2026-02-23：TASK 17 実施（設計整理）。01の4-0/4-1/4-3、02カード、run_phase1_seed10.pyを突合し、Exhibitions/Artists向け共通ガード項目（必須キー、内部整合、summary↔ledger/manifest整合、failed_fetches前進運用維持）を03に明文化。次タスクとして TASK 18（`run_compare_phase1_guard.py` の最小実装）プロンプトを追加。
- 2026-02-23：TASK 18 実施。`run_compare_phase1_guard.py` を追加し、run_summary必須キー・内部整合・summary↔ledger整合・failed_fetches前進運用維持（schema確認）を検証可能化。`--target-year 2025` と `--fail-on-mismatch` の両実行で `guard_passed=true` / exit 0 を確認し、不一致ケース（`--target-year 2024 --fail-on-mismatch`）では exit 2 を確認。次は TASK 19（前回runとの回帰比較CLI）。
- 2026-02-23：TASK 19 実施。`run_compare_phase1_guard_history.py` を追加し、比較前提（target_year/生成元CLI/任意schema version）一致チェックと「差分」と「回帰」の分離判定を実装。正常系（exit 0）、回帰系（exit 2）、比較不成立（exit 3）を確認し、summaryへ `comparison_compatible` / `compatibility_errors` / `diffs` / `regression_passed` / `regression_reasons` / `exit_code` を保存。
- 2026-02-23：TASK 20 実施。`run_compare_phase1_guard_history.py` に baseline自動解決（manual/auto、過去summary優先、schema一致/guard_passed優先）と `--strict-compatibility` を追加。summaryへ `baseline_resolution_mode` などの運用メタと `exit_code_meaning` を保存し、終了コード運用（0=pass,2=regression,3=incompatible）を明文化。正常系 exit 0、回帰系 exit 2、比較不成立(strict) exit 3 を確認。
- 2026-02-23：TASK 21 実施（設計整理）。01/02/guard系CLI/run_phase1_seed10.py を突合し、seed10固定箇所を5分類（ファイル名/ディレクトリ/年/カテゴリ/baseline探索）で棚卸し。互換維持方針（未指定時seed10維持）と最小CLI仕様案（logs-dir/summary-path/category/baseline-search-dir）を明文化し、次タスクを TASK 22（guard本体のパス/年汎化実装）に確定。
- 2026-02-24：TASK 22 実施。`run_compare_phase1_guard.py` に `--logs-dir` / `--run-summary-path` / `--category` を追加し、入力解決（run_summary/visited/failed/output_files）と summary出力既定を logs-dir 基準へ汎化（seed10既定互換を維持）。`--target-year 2025` / `--logs-dir` 指定 / `--fail-on-mismatch` の3コマンドでいずれも `guard_passed=true`・exit 0 を確認。次は TASK 23（history比較CLIのパス/探索汎化）。
- 2026-02-24：TASK 23 実施。`run_compare_phase1_guard_history.py` の baseline探索既定を `--current-summary` 親ディレクトリ起点へ汎化し、`--summary-glob`（既定 `phase1_guard_summary_*.json`）を追加。`--baseline-summary` 明示時はauto探索を無効化（manual固定）し、summaryへ `baseline_auto_search_dir` / `summary_glob_effective` などを保存。終了コード規約（0=pass,2=regression,3=incompatible）は維持確認。次は TASK 24（guard CLI共通関数化）。
- 2026-02-24：TASK 24 実施。`phase1_guard_common.py` を追加し、path解決/summary保存/時刻生成/終了コード説明を共通化。`run_compare_phase1_guard.py` と `run_compare_phase1_guard_history.py` は共通関数参照へ最小差し替え（比較ロジック本体は変更最小）を実施し、動作確認で exit code 規約（0/2/3）維持を確認。次は TASK 25（共通fixture/テストデータ整理）。
- 2026-02-24：TASK 25 実施。`tests/fixtures/phase1_guard/` に pass/regression/incompatible の固定fixture、`fixture_manifest.json`、`README.md`、`run_guard_fixture_matrix.sh` を追加し、再現コマンドと期待exit code（0/2/3）を明文化。固定fixture実行で exit 0/2/3 を確認し、CLIロジック本体は変更していない。
- 2026-02-27：TASK A-2R-FIX-2 実施。`run_phase1_seed10_artist_image_collect.py` に「作品近傍テキスト/alt/caption から年抽出→最新年降順（年不明は末尾）」を汎用実装し、summary/report に `year_sort_audit`（候補年配列と降順判定）を追加。Sara Abdu 単独再実測では `selected_image_years_top5=[2024,2024,2024,2022,2022]` / `selected_image_year_desc_ok=true` を確認。退避は `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*` から `_trash/task_a2r_fix2_sara_abdu_reset_20260227_161353` へ 5件移動し、`run_compare_phase1_guard.py --target-year 2025` は exit 0（guard_passed=true）。
- 2026-02-27：TASK A-2R-FIX-3 実施。`run_phase1_seed10_artist_image_collect.py` の年抽出に `evidence_text`（120文字短縮）を追加し、`year_sort_audit/per_artist_counts` へ候補単位で保存。`run_phase1_seed10_artist_image_collect_report.py` は `year_sort_audit` の `evidence_text` をレポートへ転記。Sara Abdu 単独再実測で `selected_image_years_top5=[2024,2024,2024,2022,2022]` / `selected_image_year_desc_ok=true` / `selected_image_year_evidence_top5` ありを確認。退避は `_trash/task_a2r_fix3_sara_abdu_reset_20260227_162659`（5件）、guard は exit 0（`phase1_guard_summary_2025_20260227T072806Z.json`）。
- 2026-02-27：TASK A-2R-FIX-4 実施。`run_phase1_seed10_artist_image_collect.py` に `sanitize_evidence_text` を追加し、`evidence_text` 生成時に HTML属性断片（`key=value` 形式）や壊れたエンティティ断片を除去してから120文字へ短縮するよう更新。Sara Abdu 単独再実測で `selected_image_years_top5=[2024,2024,2024,2022,2022]` / `selected_image_year_desc_ok=true` を維持し、summary/report の `selected_image_year_evidence_top5` で属性ノイズなしを確認。退避は `_trash/task_a2r_fix4_sara_abdu_reset_20260227_163444`（5件）、guard は exit 0（`phase1_guard_summary_2025_20260227T073546Z.json`）。
- 2026-02-27：TASK A-2B-CLOSE-1 実施。Gallery Baton（Liam Gillick）を1ギャラリー=1アーティストで再実測し、`saved_images=5` / `target_met=true` / `failed_cases=0` を確認。年配列は `selected_image_years_top5=[2025,2025,2025,2025,2024]` で降順成立。selected URL/evidence に exhibition/profile/hero 混入なし。`works_urls_tried` は `/artists/35-liam-gillick`（同一URL内に作品群を持つ構成）で `/works` サフィックスURLは未出現だが、取得画像は作品画像のみ。guard は exit 0（`phase1_guard_summary_2025_20260227T080554Z.json`）。
- 2026-02-27：TASK A-2A-CLOSE-1 実施。A+ Works of Art（Ahmad Fuad Osman）を1ギャラリー=1アーティストで再実測し、`saved_images=5` / `target_met=true` / `failed_cases=0` を確認。ただし `works_urls_tried=['https://aplusart.asia/artists/']` となり、selected URL が他作家トークン（例: `thuy-anh`, `kentaro`）を含むため「対象作家作品のみ」の完了条件は未達。混入種別は exhibition/profile/hero ではないが、artist一致性の観点で ①-3 は未解決のまま継続。guard は exit 0（`phase1_guard_summary_2025_20260227T081204Z.json`）。
- 2026-02-27：TASK A-2A-FIX-1 実施。`run_phase1_seed10_artist_image_collect.py` に artist一致性ガード（source_url由来トークン照合）と一覧URL除外（`/artists` 直抽出回避）を追加し、A+ Works of Art（Ahmad Fuad Osman）を再実測。`works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']` へ改善、`selected_image_years_top5=[2024,2023,2022,2021,2019]` で降順成立、他作家名トークン混入は再現せず。いっぽう selected URL は 5/5 が `/exhibitions/main_image_override/` のため、①-3（WORKS優先のみ）は未完のまま継続。guard は exit 0（`phase1_guard_summary_2025_20260227T082116Z.json`）。
- 2026-02-27：TASK A-2A-FIX-2 実施。`run_phase1_seed10_artist_image_collect.py` に works-only選別ガード（`/exhibitions` / `main_image_override` / `profile` / `hero` などの汎用除外）を追加し、A+ Works of Art（Ahmad Fuad Osman）を再実測。`works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']` を維持しつつ selected URL の Exhibitions/Profile/Hero 混入は 0件、`selected_image_years_top5=[1989,1953,None,None,None]` で降順判定も維持。①-3 をクローズ判定。guard は exit 0（`phase1_guard_summary_2025_20260227T083459Z.json`）。
- 2026-02-27：ユーザー確認により、②（Athrの枚数/作品性）は解決済みとして確定。
- 2026-02-27：TASK A-4-CLOSE-1 実施。The Approach（Phillip Allen）を1ギャラリー=1アーティストで再実測し、`saved_images=5` / `target_met=true` を確認。旧 `_trash/artist_works_images_cleanup_20260227T021440Z` のファイルは「payloadシグネチャ=.avif / 保存拡張子=.jpg」の不整合が5/5で、読込不可の主因は拡張子誤保存と特定。`run_phase1_seed10_artist_image_collect.py` に content-type優先拡張子決定 + payloadシグネチャ補正 + HTML payload除外 + 極小payload除外を汎用実装（この時点では `.avif` 保存）し、guard は exit 0（`phase1_guard_summary_2025_20260227T085012Z.json`）。※この判定は後にユーザー確認で再オープン済み。
- 2026-02-27：ユーザー確認により A-4 を再オープン（`.avif` は閲覧環境で読めず、100KB目標も未達）。`run_phase1_seed10_artist_image_collect.py` を再修正し、(1) 画像要求ヘッダから avif/webp 優先を外す、(2) 保存前に Pillow で JPEG 正規化、(3) `IMAGE_TARGET_SIZE_KB=100` 目標で品質/縮小を段階調整、(4) 実画像サイズが小さすぎる画像（120px未満）を除外、を実装。`2025`配下の既存画像を全退避後に再収集し、最終結果は `.jpg` のみ 39枚、`max=102,358B`、`>120KB=0`、`<10KB=0`。guard は exit 0（`phase1_guard_summary_2025_20260227T091928Z.json`）。
- 2026-02-27：運用修正。画像再検証時に「成功済み画像を全退避」しない方針へ変更し、`run_phase1_seed10_artist_image_collect.py` に「既存キャッシュの健全性検証 + 無効画像のみ `_trash/invalid_cached_images_<ts>/` へ隔離」を実装。成功画像は保持して再利用する。あわせてユーザー判断を反映し、Amanita の 4枚取得は「ページ上限による妥当結果」としてブロッカー扱いしない。

========================
臨時課題①〜⑤ロードマップ（本タスク再開前）
========================
前提:
- 03の本タスク（旧番号 106/107 系）は一時停止。
- 臨時課題①〜⑤を優先し、「1ギャラリーずつ」「1ギャラリー=1アーティスト」で進める。
- SSOT整合ゲートを毎回適用（01章ID / 02 CARD_ID / 変更対象関数の1対1紐付けを明示）。

現在地（ユーザー合意ベース）:
- ①-1 `frieze_london / Athr`: 解決済み（ユーザー確認）
- ①-2 `frieze_london / Gallery Baton`: 解決済み（TASK A-2B-CLOSE-1）
- ①-3 `liste / A+ Works of Art`: 解決済み（TASK A-2A-FIX-2）
- ② `Athr 3枚かつ作品でない`: 解決済み（ユーザー確認）
- ③-1 `frieze_london / Adams and Ollman 0件`: 未着手
- ③-2 `frieze_london / Arcadia Missa 0件`: 未着手
- ④ `frieze_london / The Approach 破損画像`: 解決済み（TASK A-4-CLOSE-1）
- ⑤ `liste / Anca Poterașu Gallery ロゴ/アイコン混入`: 未着手

実行順（軽量ロードマップ）:
- R1: ①-1 Athr（works優先の実効確定）+ ② Athr枚数/非作品問題
- R2: ①-2 Gallery Baton（works優先）
- R3: ①-3 A+ Works of Art（works優先）
- R4: ④ The Approach（破損画像の原因切り分けと修正）
- R5: ⑤ Anca Poterașu（ロゴ/アイコン抑制。6-2抵触なら理由付きスキップ）
- R6: ③-1/③-2（0件系を順番に切り分け。6-2抵触なら理由付きスキップ）

完了判定（臨時課題フェーズ）:
- ①〜⑤の各課題で「解決」または「6-2準拠のスキップ理由記録」が完了。
- 完了後に 03 の本タスク（NEXT_TASKS）へ復帰する。
- 2026-02-24：TASK 26 実施。`run_compare_phase1_guard.py` に summary/ledger 数字整合の追加見張り（skip内訳合計・failed理由内訳合計・records関係）を追加。キー不足は後方互換として `missing_keys`/`skipped_checks` へ記録し、mismatchにはしない方針を明記。2025通常実行は exit 0、skip内訳を崩したコピーsummaryで `--fail-on-mismatch` exit 2 を確認。既存判定ロジックは維持。
- 2026-02-24：TASK 27 実施。`run_compare_phase1_guard_history.py` に追加見張り項目の差分見える化（`additional_guard_checks_diff` / `additional_guard_checks_changed_fields` / `additional_guard_check_transitions`）を追加。旧summary互換として `additional_guard_checks_comparison_mode` / `additional_guard_checks_missing_in` を保存し、項目欠落でも比較継続。動作確認は pass=0 / regression=2 / incompatible=3、回帰判定ロジック自体は未変更。
- 2026-02-24：TASK 28 実施。`docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` を追加し、guard本体summary/history summaryの主要キー、exit code（0/2/3）、運用時の読む順番、fixture再現手順、後方互換メモを文書化。CLIロジック本体は未変更。
- 2026-02-24：TASK 29 実施。`run_phase1_guard_fixture_matrix.py` を追加し、`fixture_manifest.json` 駆動で pass/regression/incompatible を1コマンド実行化。matrix summary（`phase1_guard_fixture_matrix_*.json`）に expected/actual exit code とケース結果を保存。ラッパー終了コードは `0=matrix pass / 1=matrix fail` とし、内側CLI期待値（0/2/3）と分離。動作確認は通常実行 exit 0、`--fail-fast` + テスト用manifestで exit 1。guard CLI本体ロジックは未変更。
- 2026-02-24：TASK 30 実施。`guard_schema_version` を共通定数化し、history summary に `current/baseline_guard_schema_version`・`guard_schema_version_comparison_mode`・`guard_schema_version_compatible`・`guard_schema_version_policy` を追加。互換判定は「both_present一致=OK、不一致=NG、片側欠落/両側欠落=後方互換警告」に固定し、strict時のみ schema不一致を incompatible（exit 3）として扱う方針を文書化。確認は fixture matrix exit 0、既存 pass/regression/incompatible exit 0/2/3、`/tmp` 一時コピーの schema mismatch で non-strict exit 0 / strict exit 3。終了コード規約（0/2/3）は維持。
- 2026-02-24：TASK 31 実施。`--category` を最小実体化し、カテゴリ別必須ファイル集合の入口を追加（`phase1_guard_common.py` の `GUARD_CATEGORY_PROFILES`）。既定値は `exhibitions_text` を維持し、`artists_text` は `reserved_minimal` で入口のみ有効化。summaryへ `category_required_files_profile` / `required_input_files_effective` / `category_support_mode` / `category_warnings` を追加。動作確認は既定/明示カテゴリ/`--fail-on-mismatch` の各コマンドで exit 0、既存判定ロジックと終了コード規約は維持。
- 2026-02-24：TASK 32 実施。`run_compare_phase1_guard_history.py` に category 比較メタ（`current_category` / `baseline_category` / `category_comparison_mode` / `category_effective_for_comparison` / `category_compatible` / `category_compatibility_policy` / `category_warnings`）を追加。互換ルールは「both_present一致=OK、不一致=NG、欠落は後方互換warning」とし、non-strictは比較継続、strictは不一致を `compatibility_errors` へ昇格して exit 3。動作確認は通常比較 exit 0、regression exit 2、incompatible exit 3、category欠落後方互換（/tmpコピー）で継続確認。終了コード規約（0/2/3）と回帰判定ロジックは維持。
- 2026-02-24：TASK 33 実施。category mismatch 固定fixture（`tests/fixtures/phase1_guard/category_mismatch/*.json`）を追加し、manifestに non-strict（expected 0）/ strict（expected 3）を2ケース登録（方式：manifest分離）。READMEとschema文書へ確認手順/確認キー（`current_category` / `baseline_category` / `category_comparison_mode` / `category_effective_for_comparison` / `category_compatible` / `category_warnings`）を追記。動作確認は non-strict exit 0、strict exit 3、matrix（5ケース）exit 0。history回帰判定ロジックは未変更。
- 2026-02-24：TASK 34 実施。artists_text profile を最小具体化（必須入力集合/必須summaryキー）し、`category_profile_version=1.1`、`required_summary_keys_effective`、`category_support_mode_configured`、`category_activation_conditions`、`category_data_presence` を summary へ追加。artistsデータ未検出のため `support_mode=reserved_minimal` を維持し、`category_warnings` に reserved理由と activation条件系メッセージを保存。動作確認は default/exhibitions/artists/`--fail-on-mismatch` の各実行で exit 0（既存互換維持）。
- 2026-02-24：TASK 35 実施。artists category profile 再現用 fixture（`artists_reserved_warning` / `artists_provisional_pass`）を追加し、`category_fixture_manifest.json` と `run_phase1_guard_category_fixture_matrix.py` で1コマンド実行化。matrix summary に `cases[].summary_checks_passed` / `summary_check_failures` を保存し、reserved/provisional の categoryキー検証を固定化。動作確認は個別2ケース exit 0、category matrix exit 0、既存history matrix exit 0（既存fixture影響なし）。
- 2026-02-24：TASK 36 実施。artists history fixture（`artists_history_compatible` / `artists_vs_exhibitions_category_mismatch_non_strict` / `artists_vs_exhibitions_category_mismatch_strict`）を追加し、`fixture_manifest.json` に expected_summary_checks を定義。`run_phase1_guard_fixture_matrix.py` を最小拡張して summaryキー検証（`summary_checks_passed` / `summary_check_failures`）を追加。動作確認は artists個別（0/3/0）と history matrix（8ケース）exit 0、category matrix（2ケース）exit 0で既存影響なしを確認。
- 2026-02-24：TASK 37 実施。category profile を `config/phase1_guard_category_profiles.json` へ外部化し、`phase1_guard_common.py` に外部優先/内蔵fallback（missing/JSON壊れ/schema不正）導線を追加。`run_compare_phase1_guard.py` へ `--category-profile-config` と summaryメタ（`category_profile_source` / `category_profile_config_*`）を追加。fallback検証は missing path / broken JSON / schema不正 の3ケースで `builtin_fallback` を確認。動作確認は guard通常/カテゴリ指定 exit 0、history matrix（8ケース）exit 0、category matrix（2ケース）exit 0で既存影響なしを確認。
- 2026-02-24：TASK 38 実施。`phase1_guard_common.py` に `validate_category_profiles_config(config_obj)` を追加し、最小スキーマ（root/categories/必須カテゴリ/必須キー/型）を検証。`category_profile_config_error` のコード体系を `config_missing:*` / `config_json_decode_error:*` / `config_schema_error:*` に統一し、`run_compare_phase1_guard.py` summaryへ `category_profile_config_error_detail` を追加。fallback確認は missing/bad json/bad schema（missing key・type error）で `builtin_fallback` 継続を確認。history matrix（8ケース）/category matrix（2ケース）とも exit 0 で既存影響なし。
- 2026-02-24：TASK 39 実施。`run_compare_phase1_guard_history.py` に current/baseline の `category_profile_config` 文脈（source/path/loaded/error/error_detail/version）を転記し、可視化専用キー（`category_profile_config_comparison_mode` / `category_profile_config_same_source` / `category_profile_config_same_version` / `category_profile_config_effective_for_comparison` / `category_profile_config_warnings`）を追加。後方互換は warning-only（旧summary欠落でも比較継続）とし、strict/non-strict の終了コード規約（0/2/3）は維持。動作確認は通常比較 exit 0、regression fixture exit 2、incompatible fixture exit 3、/tmp 旧summary相当で `current_only` + warning を確認。history matrix（8ケース）exit 0。
- 2026-02-24：TASK 40 実施。`run_phase1_guard_category_profile_lint.py` を追加し、category profile config を guard実行前に単体検査できる入口を実装。`phase1_guard_common.load_category_profiles(...)` を再利用して error code体系（`config_missing:*` / `config_json_decode_error:*` / `config_schema_error:*`）を維持し、lint summary（`config_path/config_exists/config_valid/config_error_code/config_error_detail/checked_at/source_cli`）を保存。動作確認は valid config で exit 0、missing/bad json/bad schema で exit 1 を確認（判定ロジック本体は未変更）。
- 2026-02-24：TASK 41 実施。`tests/fixtures/phase1_guard/category_fixture_manifest.json` に activation監視チェックを追加（reserved/provisional 両ケースで `category_activation_conditions` 非空、`category_data_presence` 存在）。fixtureパスを `tests/fixtures/phase1_guard/category/...` に統一し、README/Schema文書の実行例と確認キーを更新。動作確認は `run_phase1_guard_category_fixture_matrix.py` で wrapper exit 0（2ケース）および指定の artists_text 2コマンドがともに exit 0、matrix summary の `cases[].summary_checks_passed=true` を確認。
- 2026-02-24：TASK 42 実施。lint fixture manifest（`tests/fixtures/phase1_guard/lint_fixture_manifest.json`）と 1コマンドラッパー（`run_phase1_guard_lint_fixture_matrix.py`）を追加し、valid/missing/bad_json/bad_schema の4ケースを固定再現化。matrix summary に `all_cases_passed` / `cases[].expected_exit_code` / `cases[].actual_exit_code` / `cases[].summary_checks_passed` / `cases[].summary_check_failures` / `cases[].output_summary_path` を保存。動作確認は lint matrix wrapper exit 0（4ケース）、個別lintは valid=0 / missing=1 / bad_json=1 / bad_schema=1。既存の category/history matrix も exit 0 を確認。
- 2026-02-24：TASK 43 実施。`run_phase1_guard_all_matrices.py` を追加し、lint/category/history の3系統matrixを1コマンドで順次実行できる統合入口を実装。統合summary（`phase1_guard_all_matrices_*.json`）へ `all_passed` / `wrapper_exit_code` / `execution_order` / `matrices[]` / `warnings` を保存し、終了コードを `0=all_pass / 1=any_fail` で固定。動作確認は統合実行（通常/`--output-json --pretty`）と既存3matrix単体の全てで exit 0 を確認（本体ロジック未変更）。
- 2026-02-24：TASK 44 実施。`run_phase1_guard_all_matrices_report.py` を追加し、統合summaryを読む軽量レポートCLI（`--summary-path` / `--latest`）を実装。標準出力で `all_passed` / `wrapper_exit_code` / `execution_order` / `failed_matrices` / `child_summary_paths` を表示し、任意 `--output-json` でレポート保存を可能化。exit規約は `0=report_generated / 1=summary_not_found_or_invalid` を固定。動作確認は指定3コマンドすべて exit 0（本体ロジック未変更）。
- 2026-02-24：TASK 45 実施。report CLI向け fixture（valid/missing/bad_json）を `tests/fixtures/phase1_guard/report_fixture_manifest.json` で固定化し、`run_phase1_guard_all_matrices_report_fixture_matrix.py` を追加。matrix summary に `all_cases_passed` / `cases[].expected_exit_code` / `cases[].actual_exit_code` / `cases[].summary_checks_passed` / `cases[].summary_check_failures` / `cases[].report_output_path` を保存。動作確認は指定3コマンドで exit 0、report fixture matrix 3ケースも exit 0（本体ロジック未変更）。
- 2026-02-24：TASK 46 実施。`run_phase1_guard_all_matrices_report.py` に `--fail-on-failed-matrix` を追加し、既定挙動（summary読取成功時 exit 0）を維持したまま strict終了ポリシーを選択可能化。`all_passed=false` で flag無指定は exit 0、flag指定は exit 1 を確認。出力メタ `fail_on_failed_matrix` / `exit_policy` / `exit_reason` / `report_exit_code` を追加し、report fixture matrix を5ケース（default/strict含む）へ拡張して wrapper exit 0 を確認（本体ロジック未変更）。
- 2026-02-24：TASK 47 実施。`run_phase1_guard_all_matrices_report_fixture_matrix.py` の `cases[]` に終了ポリシー可視化キー `policy_expected`（manifest由来）/ `policy_actual`（report `exit_policy` 由来）/ `policy_match` を追加。`report_fixture_manifest.json` に `policy_expected` を明示し、README/schema文書へ読み方を追記。動作確認は report fixture matrix exit 0、failed summary の defaultで exit 0（`policy_actual=default_report_only`）、strictで exit 1（`policy_actual=fail_on_failed_matrix`）を確認。
- 2026-02-24：TASK 48 実施。report fixture matrix に `policy_check_mode=enforce_when_available` のpolicy guardを追加し、`policy_actual` 取得時の `policy_match=false` を wrapper fail 条件へ反映。`policy_actual` 未取得（missing/bad_json）は `policy_guard_reason=policy_actual_unavailable_warning_only` で後方互換継続。summaryへ `policy_check_mode` / `policy_guard_applied` / `policy_guard_passed` / `policy_guard_reason` を追加し、通常manifestは exit 0、/tmp一時manifestでpolicy mismatchを作ったnegative確認は exit 1 を確認。
- 2026-02-24：TASK 49 実施。policy mismatch専用negative manifest（`tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json`）を追加し、`policy_guard` の失敗経路を常設fixture化。green実行（通常manifest）は wrapper exit 0 を維持し、negative実行（`--manifest-path ...negative...`）で wrapper exit 1 を固定再現。README/schema文書に green/negative の2系統実行導線を追記。
- 2026-02-24：TASK 54 実施。`run_phase1_seed10.py` に artists_text 向け Post-fetch Enrichment入口を追加し、`data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl` を上書き生成する導線を実装。run summary に `artists_enrichment_*` メタ（candidates/requests/output_path/counters/warnings）を追加し、`python run_phase1_seed10.py`（既存互換）/ `--include-artists-text`（2回）/ `run_compare_phase1_guard.py --target-year 2025` すべて exit 0 を確認。
- 2026-02-24：TASK 55 実施。`run_enrichment_artists_seed10_apply.py` を追加し、`artists_enrichment_requests_2025.jsonl` から `artists_*.jsonl` の `headline_ja` を更新する apply導線を実装。1回目実行で `updated=81`、2回目実行で `updated=0`（冪等）を確認し、apply output/summary を `data/phase1_seed10/derived/` に保存。guard互換（`python run_compare_phase1_guard.py --target-year 2025` exit 0）も維持。
- 2026-02-24：TASK 56 実施。`run_vectorize_artists_seed10.py` を追加し、artists raw から embedding/index/meta/failed/manifest 生成の Post-fetch 入口を実装。`input_total=81` / `embedded_total=0` / `failed_total=81`（接続失敗）を summary へ保存し、guard互換（`python run_compare_phase1_guard.py --target-year 2025` exit 0）を維持。次は TASK57 で外向き接続回復後に `embedded_total>0` を再検証。
- 2026-02-24：TASK 57 実施。外向き接続を再確認（`curl -I https://example.com` / `socket.gethostbyname` とも成功）後、`python run_vectorize_artists_seed10.py` を再実行して `input_total=81` / `embedded_total=81` / `failed_total=0` を確認。生成物（index/meta/manifest）を更新し、`python run_compare_phase1_guard.py --target-year 2025` exit 0 で既存互換を維持。次は TASK58（artists検索スモークCLI）。
- 2026-02-24：TASK 58 実施。`run_search_artists_seed10.py` を追加し、artists vector生成物（index/meta）から RETRIEVAL_QUERY で top-k 検索を実行可能化。`--query "contemporary painting"` で `source_url/record_id/score` を含む上位5件を出力し、`artists_text_search_results_*.jsonl` / `artists_text_search_summary_*.json`（query/k/output_paths）を保存。`python run_compare_phase1_guard.py --target-year 2025` exit 0 で既存互換を維持。次は TASK59（context JSON整形）。
- 2026-02-24：TASK 59 実施。`run_build_artists_context_seed10.py` を追加し、artists検索結果（top-k）を context JSON へ整形する導線を実装。`--query "contemporary painting"` で `source_url/record_id/score/excerpt` を含む context（k=5）と summary（query/k/input_paths/output_paths）を保存。`python run_compare_phase1_guard.py --target-year 2025` exit 0 で既存互換を維持。次は TASK60（回答スモークCLI）。
- 2026-02-24：TASK 60 実施。`run_answer_artists_seed10.py` を追加し、artists context JSON から回答+根拠（`source_url/record_id/score/excerpt`）を出力する回答スモークCLIを実装。`--question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` で `answer_status=ok` / `k_returned=5` を確認し、`artists_text_answer_*.json` と `artists_text_answer_summary_*.json` を保存。`python run_compare_phase1_guard.py --target-year 2025` exit 0 で既存互換を維持。次は TASK61（回答比較CLI）。
- 2026-02-25：TASK 75 実施。`run_artists_answer_qa_daily_recovery.py` を追加し、`batch_smoke -> batch_report -> retry_manifest -> retry_run -> retry_run_report` を1コマンド化。`--batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` と `--output-json ...daily_recovery_summary_latest.json` の2実行で exit 0、`run_compare_phase1_guard.py --target-year 2025` も exit 0 を確認。daily summary に `steps[]/all_passed/wrapper_exit_code/notes` を保存し、retry対象0件no-opも判別可能化。次タスク（TASK76: daily recovery summary 軽量レポートCLI）を追加。
- 2026-02-25：TASK 76 実施。`run_artists_answer_qa_daily_recovery_report.py` を追加し、daily recovery summary から `failed_steps` と `child_summary_paths_to_check` を抽出する軽量レポート導線（`--summary-path` / `--latest`）を実装。`--latest` は `_report.json` と child summary 系（`_batch_smoke_summary` / `_batch_report` / `_retry_manifest` / `_retry_run_summary` / `_retry_run_report`）を除外して本体summaryのみ解決。動作確認は `daily_recovery --batch-manifest ...` / `daily_recovery_report --summary-path ...` / `daily_recovery_report --latest` / `run_compare_phase1_guard.py --target-year 2025` すべて exit 0。次タスク（TASK77: daily recovery report rollup CLI）を追加。
- 2026-02-25：TASK 77 実施。`run_artists_answer_qa_daily_recovery_report_rollup.py` を追加し、`artists_answer_qa_daily_recovery_summary_*_report.json` を最新N件で集約して `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を抽出するrollup導線を実装。`daily_recovery --batch-manifest ...` / `daily_recovery_report --latest` / `daily_recovery_report_rollup --latest-n 20` / `run_compare_phase1_guard.py --target-year 2025` を実行し、すべて exit 0 を確認。次タスク（TASK78: rollup起点のretry manifest生成CLI）を追加。
- 2026-02-25：TASK 78 実施。`run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py` を追加し、`artists_answer_qa_daily_recovery_report_rollup_*.json` から `failed_runs[]` を抽出して retry manifest を生成する導線（`--rollup-json` / `--latest`）を実装。生成manifestに `retry_manifest_path` / `source_summary_path` / `failed_step_names` / `child_summary_paths_to_check` / `batch_manifest_path` を保存し、failed run 0件でも空manifestを保存して exit 0 を維持。動作確認は `daily_recovery --batch-manifest ...`（exit 1）/ `daily_recovery_report --latest`（exit 0）/ `daily_recovery_report_rollup --latest-n 20`（exit 0）/ `daily_recovery_retry_manifest_from_rollup --latest`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK79: rollup起点retry manifestのワンショット実行CLI）を追加。
- 2026-02-25：TASK 79 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を追加し、rollup起点retry manifestのワンショット再実行導線（`--retry-manifest` / `--latest`）を実装。`cases[]` を順次 `run_artists_answer_qa_daily_recovery.py` へ渡して実行し、summaryに `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries` / `cases[]` を保存。failed runありmanifestでは exit 1、failed run 0件manifestでは `retry_run_mode=noop_empty_retry_manifest` で exit 0 を確認。`run_compare_phase1_guard.py --target-year 2025` は exit 0 を維持。次タスク（TASK80: retry run summary軽量レポートCLI）を追加。
- 2026-02-25：TASK 80 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py` を追加し、retry run summaryの軽量レポート導線（`--summary-path` / `--latest`）を実装。`--latest` は `_report.json` と `_failed_run_` を除外して本体summaryのみ解決し、`executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存。動作確認は `daily_recovery_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_rollup --latest`（exit 0）/ `retry_run_from_rollup_manifest --latest`（exit 1）/ `retry_run_from_rollup_report --latest`（exit 0）/ `retry_run_from_rollup_report --summary-path ...`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK81: retry run report rollup CLI）を追加。
- 2026-02-25：TASK 81 実施。`run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py` を追加し、`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json` を最新N件で集約して failed run を抽出するrollup導線を実装。rollupへ `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check`）を保存し、`--latest-n` / `--search-dir` で対象範囲調整を可能化。動作確認は `retry_run_from_rollup_manifest --latest`（exit 1）/ `retry_run_from_rollup_report --latest`（exit 0）/ `retry_run_report_rollup --latest-n 20`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK82: retry run report rollup起点retry manifest生成CLI）を追加。
- 2026-02-25：TASK 82 実施。`run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` を追加し、`artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` から failed run を抽出して retry manifest を生成する導線（`--rollup-json` / `--latest`）を実装。`--latest` は `*_retry_manifest.json` を除外して rollup本体JSONを解決し、生成manifestへ `source_summary_path` / `failed_case_ids` / `retry_manifest_path` / `cases[].batch_manifest_path` を保存。動作確認は `retry_run_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_retry_run_report_rollup --latest`（exit 0）/ 空rollup（`failed_runs=0`）で manifest 生成（exit 0）/ `retry_run_from_rollup_manifest --retry-manifest ...`（exit 1）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK83: retry run report rollup起点manifestワンショット実行CLI）を追加。
- 2026-02-25：TASK 83 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py` を追加し、TASK82の retry manifest を既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` へ委譲実行するワンショット導線（`--retry-manifest` / `--latest`）を実装。`--latest` 既定globを `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` に固定し、failed runありmanifestでは exit 1、空manifestでは no-op 成功（exit 0, `executed_runs=0`）を確認。動作確認は `retry_run_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_retry_run_report_rollup --latest`（exit 0）/ `retry_run_from_retry_run_report_rollup_manifest --latest`（exit 1）/ `--retry-manifest ...094043Z...`（exit 1）/ `--retry-manifest /tmp/...empty...`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK84: retry run summary軽量レポートCLI）を追加。
- 2026-02-25：TASK 84 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py` を追加し、retry run summary（`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json`）の軽量レポート導線（`--summary-path` / `--latest`）を実装。`--latest` は `_report.json` と `_failed_run_` を除外して本体summaryのみ解決し、`retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存。動作確認は `retry_run_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_retry_run_report_rollup --latest`（exit 0）/ `retry_run_from_retry_run_report_rollup_manifest --latest`（exit 1）/ `retry_run_from_retry_run_report_rollup_manifest_report --latest`（exit 0）/ `--summary-path ...094707Z.json`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK85: retry run summary report rollup CLI）を追加。
- 2026-02-25：TASK 85 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py` を追加し、retry run summary report（`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json`）のrollup導線を実装。出力top-levelへ `schema_name` / `schema_version` / `artifact_kind` / `generated_at` / `generated_by` を追加し、対象探索は `is_target_report` / `list_candidate_reports` へ最小共通化。動作確認は `retry_run_from_rollup_manifest --latest`（exit 1）/ `retry_run_from_retry_run_report_rollup_manifest_report --latest`（exit 0）/ `retry_run_from_retry_run_report_rollup_manifest_report_rollup --latest-n 20`（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK86: retry run summary report rollup起点retry manifest生成CLI）を追加。
- 2026-02-25：TASK 86 実施。`run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` をTASK85生成物に適用し、retry run report rollup起点の retry manifest 生成を再確認。`--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json`（`*_retry_manifest.json` 除外）を解決し、`source_summary_path` / `failed_case_ids` / `retry_manifest_path` / `cases[]` を保存。動作確認は `retry_run_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_retry_run_report_rollup --latest`（exit 0）/ `retry_run_from_rollup_manifest --retry-manifest ...102015Z...`（exit 1）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK87: retry run report rollup起点retry manifestワンショット実行CLI）を追加。
- 2026-02-25：TASK 87 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py` を追加し、retry run report rollup起点 retry manifest のワンショット実行導線（`--retry-manifest` / `--latest`）を実装。既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` をsubprocess再利用して重複実装を回避し、`--latest` で `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` を解決。動作確認は `retry_run_report_rollup --latest-n 20`（exit 0）/ `retry_manifest_from_retry_run_report_rollup --latest`（exit 0）/ `retry_run_from_retry_run_report_rollup_retry_manifest --latest`（exit 1）/ `--retry-manifest ...102710Z...`（exit 1）/ `--retry-manifest /tmp/artists_retry_run_report_rollup_empty_task87_retry_manifest.json`（exit 0, no-op）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK88: retry run summary軽量レポートCLI）を追加。
- 2026-02-25：TASK 88 実施。`run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py` を追加し、retry run summary（`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json`）の軽量レポート導線を実装。あわせて `qa_artifact_utils.py` を新設し、TASK85〜88系で `--latest` 解決とスキーマ識別メタ（`artifact_kind/schema_name/schema_version/generated_at/generated_by`）を最小共通化。短い入口として `run_aqa_retry_run_report_rollup*.py` 系4本を追加し、長いCLI名は後方互換で維持。動作確認は `retry_run_from_retry_run_report_rollup_retry_manifest --latest`（exit 1）/ 新report `--latest`（exit 0）/ 新report `--summary-path ...105331Z...`（exit 0）/ 短い入口report（exit 0）/ `run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK89: TASK85〜88ワンショット日次チェーンCLI）を追加。
- 2026-02-25：TASK 89 実施。`run_aqa_retry_run_daily_chain.py` を追加し、短い入口（TASK85〜88）で `rollup -> retry manifest -> retry run -> retry run report` を1コマンド連結できるようにした。`qa_artifact_utils.py` に `retry_run_daily_chain_summary` を追加し、chain summaryへ `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_latest.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK90: daily chain summary 軽量レポートCLI）を追加。
- 2026-02-25：TASK 90 実施。`run_aqa_retry_run_daily_chain_report.py` を追加し、daily chain summary（`artists_answer_qa_retry_run_daily_chain_summary_*.json`）から `failed_steps` と `child_summary_paths_to_check` を抽出する軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、report出力に `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK91: daily chain report rollup CLI）を追加。
- 2026-02-25：TASK 91 実施。`run_aqa_retry_run_daily_chain_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_summary_*_report.json` を最新N件で集約して failed run 推移を抽出するrollup導線を実装。`qa_artifact_utils.py` の `list_candidate_artifacts` / `build_artifact_header` を再利用し、rollup出力へ `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK92: daily chain report rollup起点retry manifest生成CLI）を追加。
- 2026-02-25：TASK 92 実施。`run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` から failed run を抽出して retry manifest を生成する導線（`--rollup-json` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、manifest出力へ `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。failed run 0件でも `notes=["no_failed_runs_in_rollup"]` 付きの空manifestを保存して exit 0 を維持。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK93: daily chain report rollup起点manifestワンショット実行CLI）を追加。
- 2026-02-25：TASK 93 実施。`run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py` を追加し、daily chain report rollup 起点 retry manifest のワンショット実行導線（`--retry-manifest` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` を使って最新manifestを解決し、既存 `run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲して retry-run本体ロジックの重複を回避。no-op manifest（`cases=[]`）では `executed_runs=0` / `notes=["no_failed_runs_in_manifest"]` を子summaryで確認し exit 0 を維持。動作確認は `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "...143017Z_retry_manifest.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK94: daily chain report rollup起点復旧導線のワンショット化）を追加。
- 2026-02-26：TASK 94 実施。`run_aqa_retry_run_daily_chain_recovery_chain.py` を追加し、daily chain report rollup起点の復旧導線（`report_rollup -> retry_manifest -> retry_run`）を1コマンド化。既存3本の短い入口CLIを subprocess で順次再利用し、chain summaryへ `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest --output-json "..._latest.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK95: chain summary軽量レポートCLI）を追加。
- 2026-02-26：TASK 95 実施。`run_aqa_retry_run_daily_chain_recovery_chain_report.py` を追加し、`artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json` から failed step と参照先summaryを抽出する軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、`retry_run_daily_chain_recovery_chain_report` artifact定義を追加。あわせて `retry_run_daily_chain_recovery_chain_summary` に `_report.json` 除外を追加して `--latest` 解決の後方互換を維持。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T160126Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK96: chain report rollup CLI）を追加。
- 2026-02-26：TASK 96 実施。`run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*_report.json` を最新N件で集約して failed run 推移を抽出するrollup導線を実装。`qa_artifact_utils.py` の `list_candidate_artifacts` / `build_artifact_header` を再利用し、`retry_run_daily_chain_recovery_chain_report_rollup` artifact定義を追加。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK97: chain recovery chain report rollup起点retry manifest生成CLI）を追加。
- 2026-02-26：TASK 97 実施。`run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` から failed run を抽出して retry manifest を生成する導線（`--rollup-json` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、`retry_run_daily_chain_recovery_chain_report_rollup` の `_retry_manifest.json` 除外と `retry_run_daily_chain_recovery_chain_report_rollup_retry_manifest` artifact定義を追加。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK98: recovery chain report rollup起点manifestワンショット実行CLI）を追加。

- 2026-02-26：TASK 98 実施。`run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py` を追加し、recovery chain report rollup起点 retry manifest のワンショット実行導線（`--retry-manifest` / `--latest`）を実装。`qa_artifact_utils.resolve_latest_artifact(...)` で最新manifestを解決し、`qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_retry_run_summary_from_report_rollup_manifest` artifact定義を追加（TASK99の `--latest` 解決準備）。既存 `run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲して retry-run本体ロジックの重複を回避。empty retry manifest（`cases=[]`）では no-op成功（`executed_runs=0` / `notes=["no_failed_runs_in_manifest"]`）で exit 0 を確認。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "...164200Z_retry_manifest.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK99: recovery chain report rollup起点retry-run summary軽量レポートCLI）を追加。
- 2026-02-26：TASK 99 実施。`run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py` を追加し、`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` から failed/recovered を抽出する軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.resolve_latest_artifact(...)` で最新summaryを解決し、`qa_artifact_utils.build_artifact_header(...)` で `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。追加要件として `retry_manifest_path` が `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` 系かを検証し、不一致時は `notes` に理由を残して `exit_reason=summary_out_of_scope_for_task99` / exit 1 とした。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T165814Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK100: artists画像収集実測CLI）を追加。
- 2026-02-26：TASK 100 実施。`run_phase1_seed10_artist_image_collect.py` を追加し、seed10 artists raw から画像候補抽出・保存・実測summary出力（`phase1_seed10_artist_image_collect_summary_*.json`）を実装。`python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` で `seed_artist_count=81 / artists_with_ge_target_images=0 / success_rate_ge_target=0.0 / threshold_passed=false` を確認し、失敗理由は `failed_cases` に保存。`python run_compare_phase1_guard.py --target-year 2025` は exit 0 を維持。次タスク（TASK101: artists画像収集実測summaryの軽量レポートCLI）へ進む。
- 2026-02-26：TASK 101 実施。`run_phase1_seed10_artist_image_collect_report.py` を追加し、`phase1_seed10_artist_image_collect_summary_*.json` から達成率と失敗要因を短く集約する軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_summary` / `phase1_seed10_artist_image_collect_report` artifact定義を追加し、`--latest` 解決を共通化。動作確認は `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report.py --latest`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T233537Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK102: images実測reportのrollup CLI）へ進む。
- 2026-02-26：TASK 102 実施。`run_phase1_seed10_artist_image_collect_report_rollup.py` を追加し、`phase1_seed10_artist_image_collect_summary_*_report.json` の最新N件を集約して達成率推移と失敗要因推移を抽出するrollup導線（`--latest-n` / `--search-dir` / `--glob`）を実装。`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_report_rollup` artifact定義を追加し、候補探索は `list_candidate_artifacts(...)` を再利用。動作確認は `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report.py --latest`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK103: images実測rollup起点の優先再収集manifest生成CLI）へ進む。
- 2026-02-26：TASK 103 実施。`run_phase1_seed10_artist_image_collect_retry_manifest.py` を追加し、`phase1_seed10_artist_image_collect_report_rollup_*.json` から再収集優先ケースを抽出するmanifest導線（`--rollup-json` / `--latest` / `--max-cases` / `--min-failed-count`）を実装。`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_retry_manifest` artifact定義を追加し、`--latest` 解決は `resolve_latest_artifact(...)` を再利用。manifestには `source_rollup_path` / `failed_reason_filter` / `failed_domain_filter` / `cases[]`（`artist_id`/`source_url`/`reason`/`domain`）とschema識別メタを保存。動作確認は `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report.py --latest`（exit 0）/ `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（exit 0）/ `python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK104: retry manifestワンショット再収集CLI）へ進む。
- 2026-02-26：TASK 104 実施。`run_phase1_seed10_artist_image_collect_retry_run.py` を追加し、`phase1_seed10_artist_image_collect_report_rollup_*_retry_manifest.json` 起点の再収集ワンショット実行導線（`--retry-manifest` / `--latest`）を実装。`qa_artifact_utils.resolve_latest_artifact(...)` を再利用し、`qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_retry_run_summary` artifact定義を追加。`phase1_seed10_artist_image_collect_report_rollup` は `--latest` 誤判定防止のため `_retry_manifest.json` を除外するよう修正。no-op（`cases=[]`）時は `executed_cases=0` / `notes=[\"no_retry_cases_in_manifest\",\"no_retry_cases_selected\"]` で exit 0 を維持。動作確認は `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（exit 0）/ `python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest`（exit 0）/ `python run_phase1_seed10_artist_image_collect_retry_run.py --latest`（exit 0）/ `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest \"data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T023049Z_retry_manifest.json\"`（exit 0）/ `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest /tmp/phase1_seed10_artist_image_collect_retry_manifest_empty_task104.json`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK105: retry-run summary軽量レポートCLI）へ進む。
- 2026-02-26：HOTFIX（images抽出0件の原因切り分け）。`run_phase1_seed10_artist_image_collect.py` に最小修正を追加し、(a) `www` 有無の汎用URLフォールバック、(b) requests retry adapter、(c) DNS事前診断（`network_dns_probe_ok`）と失敗理由の正規化（`html_fetch_failed:dns_resolution_error:<domain>`）を実装。実行確認は `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5`（exit 0）で、原因がDNS解決不可であることをsummaryに明示。`python run_compare_phase1_guard.py --target-year 2025` は exit 0 を維持。


------------------------------------------------------------
TASK 99) artists回答QA retry-run daily chain recovery chain report rollup起点retry-run summary の軽量レポートCLIを追加し、failed/recovered run を `--latest` で即確認できるようにする（本体前進）
------------------------------------------------------------
目的：
- TASK98で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する。

参照ファイル：
- run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py
- qa_artifact_utils.py
- data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存retry-run本体ロジックは変更しない（report CLI追加のみ）
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
- report JSONに最低限 `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる
- report JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
- 03 の NEXT_TASKS の 99) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/reportパス）を追記
- 次の最優先タスク（TASK100）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest
- （WSL）python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 100) Phase1 seed10 の artists画像収集（実測）CLIを追加し、5枚/人・70%超えの達成状況を summary で可視化する（本体前進）
------------------------------------------------------------
目的：
- ここまで整備した復旧導線づくりから一度区切り、Phase1 の本命である「画像収集の実測」に切り替える。
- seed10（artists対象）で画像収集を実行し、まずは現状の取得率を把握する。
- 目標は「1人あたり画像5枚取得」かつ「取得率70%超え」。
- このTASKでは、まず“実測”を行う（必要最小限の実装）。report/rollup/manifest系の新設はまだやらない。

参照ファイル：
- run_phase1_seed10.py
- run_compare_phase1_guard.py
- data/phase1_seed10/raw/artists_*_2025.jsonl
- data/phase1_seed10/logs/run_summary_seed10_2025.json
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- 既存の画像取得本体ロジックがある場合は再利用（ロジック重複を作らない）
- QA系のreport/rollup/retry CLIは今回増やさない

完了条件：
- `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` が実行できる
- summary JSONが保存される
- summary から少なくとも以下が分かる：
  - seed10対象人数
  - 5枚以上取れた人数
  - 取得率（70%超えかどうか）
  - 失敗ケース（最低限の理由）
- report JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
- 03 の NEXT_TASKS の 100) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK101）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 101) artists画像収集実測summaryの軽量レポートCLIを追加し、5枚達成率/失敗理由上位/ドメイン別失敗を1コマンドで確認できるようにする（本体前進）
------------------------------------------------------------
目的：
- TASK100で生成した `phase1_seed10_artist_image_collect_summary_*.json` を短く集約し、改善優先順位（失敗理由/失敗ドメイン）を即判断できる導線を追加する。
- 実測結果が目標未達（5枚/人・70%超）だった場合でも、次アクションをログだけで決められる状態にする。

参照ファイル：
- `run_phase1_seed10_artist_image_collect.py`
- `qa_artifact_utils.py`（`--latest` 解決を再利用可能なら再利用）
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_*.json`
- `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- `docs/04_TASK_PROGRESS_LOG.md`

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存画像収集本体ロジックは変更しない（report CLI追加のみ）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_phase1_seed10_artist_image_collect_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `phase1_seed10_artist_image_collect_summary_*.json` を自動解決できる
- report JSONに最低限以下を保存できる：
  - `seed_artist_count`
  - `artists_with_ge_target_images`
  - `success_rate_ge_target`
  - `threshold_passed`
  - `top_failed_reasons`（理由別件数の上位）
  - `top_failed_domains`（ドメイン別失敗件数の上位）
  - `notes`
- report JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与できる
- 03 の NEXT_TASKS の 101) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/reportパス）を追記
- 次の最優先タスク（TASK102）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5
- （WSL）python run_phase1_seed10_artist_image_collect_report.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 102) artists画像収集実測reportのrollup CLIを追加し、直近N回の達成率推移と失敗理由変化を1コマンドで抽出できるようにする（本体前進）
------------------------------------------------------------
目的：
- TASK101で生成される `phase1_seed10_artist_image_collect_summary_*_report.json` を複数本まとめて読み、達成率推移と失敗理由の変化を即確認できる導線を追加する。
- 改善施策の効果（5枚達成率・70%閾値通過率）を時系列で追える状態にする。

参照ファイル：
- `run_phase1_seed10_artist_image_collect_report.py`
- `qa_artifact_utils.py`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_*_report.json`
- `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- `docs/04_TASK_PROGRESS_LOG.md`

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存画像収集本体/報告CLIロジックは変更しない（rollup CLI追加のみ）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない

完了条件：
- `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（例）が実行できる
- `--latest-n` と `--search-dir` で対象範囲を調整できる
- rollup JSONに最低限以下を保存できる：
  - `total_reports`
  - `threshold_passed_count`
  - `threshold_passed_rate`
  - `success_rate_trend`（時系列で summary_path と success_rate を追える形）
  - `top_failed_reasons_trend`（理由別件数の推移）
  - `top_failed_domains_trend`（ドメイン別件数の推移）
- rollup JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与できる
- 03 の NEXT_TASKS の 102) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/rollupパス）を追記
- 次の最優先タスク（TASK103）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5
- （WSL）python run_phase1_seed10_artist_image_collect_report.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 103) artists画像収集実測rollupから優先再収集manifestを生成し、失敗理由/ドメイン上位への再試行入口を短縮する（本体前進）
------------------------------------------------------------
目的：
- TASK102で生成される `phase1_seed10_artist_image_collect_report_rollup_*.json` から再収集優先ケースを抽出し、再実行manifestを自動生成する。
- 日次運用で「rollup確認→対象抽出→再収集」の手作業を減らし、改善ループを短縮する。

参照ファイル：
- `run_phase1_seed10_artist_image_collect_report_rollup.py`
- `qa_artifact_utils.py`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_*.json`
- `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- `docs/04_TASK_PROGRESS_LOG.md`

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存画像収集本体/報告/rollupロジックは変更しない（manifest生成CLI追加のみ）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_phase1_seed10_artist_image_collect_retry_manifest.py --rollup-json "..."`（例）が実行できる
- `--latest` で最新 `phase1_seed10_artist_image_collect_report_rollup_*.json` を自動解決できる
- manifestに最低限 `source_rollup_path` / `failed_reason_filter` / `failed_domain_filter` / `cases[]`（`artist_id` / `source_url` / `reason` / `domain`）を保存できる
- `--max-cases` と `--min-failed-count`（同等）で対象数を調整できる
- failedケース0件でも空manifestを保存して exit 0 を維持できる（`notes=["no_retry_cases_selected"]` など）
- manifest JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与できる
- 03 の NEXT_TASKS の 103) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/manifestパス）を追記
- 次の最優先タスク（TASK104）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5
- （WSL）python run_phase1_seed10_artist_image_collect_report.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20
- （WSL）python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 104) artists画像収集retry manifestをワンショット実行するCLIを追加し、再収集導線を1コマンド化する（本体前進）
------------------------------------------------------------
目的：
- TASK103で生成される `phase1_seed10_artist_image_collect_report_rollup_*_retry_manifest.json` を直接実行し、優先再収集を1コマンドで回せるようにする。
- 日次運用で「rollup確認→manifest生成→再収集」の最終手順を短縮する。

参照ファイル：
- `run_phase1_seed10_artist_image_collect_retry_manifest.py`
- `run_phase1_seed10_artist_image_collect.py`
- `qa_artifact_utils.py`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_*_retry_manifest.json`
- `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- `docs/04_TASK_PROGRESS_LOG.md`

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存画像収集本体ロジックは変更しない（実行ラッパー追加のみ）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest "..."`（例）が実行できる
- `--latest` で最新 `phase1_seed10_artist_image_collect_report_rollup_*_retry_manifest.json` を自動解決できる
- no-op manifest（cases=0）では成功終了（exit 0）し、summaryに `executed_cases=0` / `notes` を保存できる
- summaryに最低限 `retry_manifest_path` / `executed_cases` / `wrapper_exit_code` / `child_collect_summaries`（同等）を保存できる
- summary JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与できる
- 03 の NEXT_TASKS の 104) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/summaryパス）を追記
- 次の最優先タスク（TASK105）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20
- （WSL）python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_retry_run.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_YYYYMMDDTHHMMSSZ_retry_manifest.json"
- （WSL）python run_compare_phase1_guard.py --target-year 2025

------------------------------------------------------------
TASK 105) artists画像収集retry-run summaryの軽量レポートCLIを追加し、failed/recovered と参照先summaryを `--latest` で即確認できるようにする（本体前進）
------------------------------------------------------------
目的：
- TASK104で生成される `phase1_seed10_artist_image_collect_retry_run_summary_*.json` を短く集約し、失敗ケースと参照先collect summaryを即確認できる導線を追加する。

参照ファイル：
- `run_phase1_seed10_artist_image_collect_retry_run.py`
- `qa_artifact_utils.py`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_retry_run_summary_*.json`
- `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- `docs/04_TASK_PROGRESS_LOG.md`

制約：
- 取得ループ内で実行しない（Post-fetch分離維持）
- 既存画像収集本体/ retry-run 本体ロジックは変更しない（report CLI追加のみ）
- 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
- ドメイン専用ハードコードを増やさない
- `--latest` 解決は `qa_artifact_utils.py` の共通ヘルパーを再利用する

完了条件：
- `python run_phase1_seed10_artist_image_collect_retry_run_report.py --summary-path "..."`（例）が実行できる
- `--latest` で最新 `phase1_seed10_artist_image_collect_retry_run_summary_*.json` を自動解決できる
- report JSONに最低限 `retry_manifest_path` / `executed_cases` / `wrapper_exit_code` / `child_collect_summaries_to_check` / `notes`（同等）を保存できる
- report JSONに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与できる
- 03 の NEXT_TASKS の 105) を [x]、CHANGELOG追記
- 04 に実行結果（コマンド/exit/reportパス）を追記
- 次の最優先タスク（TASK106）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20
- （WSL）python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_retry_run.py --latest
- （WSL）python run_phase1_seed10_artist_image_collect_retry_run_report.py --latest
- （WSL）python run_compare_phase1_guard.py --target-year 2025

---
運用メモ（2026-02-26 追加）
- RAG抽出内訳の人間確認は `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` に集約する。
- タスクごとに同ファイルへ追記し、内訳（fair/gallery単位の対象人数・成功人数・取得件数・成功率%）を日本語で記録する。

---
運用メモ（Codex Efficiency Protocol / 2026-02-26）
- 以後はタスク束（3〜6小タスク）で投入し、次タスクには MODEL_HINT（VERY_HIGH/HIGH/MEDIUM/LOW）+ 理由1行を必須化する。
- 本体劣化ゲート（html_fetch_failed>20% / saved系0連続）時は、観測導線増設を停止して原因分解・最小修正へ強制遷移する。


---
旧TASK107 実施結果（ゲート発動・ブロッカー継続）
- 判定: `artists_failed_fetches_new_in_run=10 / artists_text_seed_gallery_count=10 = 100%`（20%超）かつ `saved=0` 継続のためゲート発動。
- 原因上位: `DNS_ERROR`（artists/exhibitionsともに10件）。
- 最小修正: `run_phase1_seed10.py` で `DNS_ERROR` は max-retry/cooldown で恒久スキップしないよう修正（回復後即再試行可能化）。
- 結果: 環境DNS未回復のため抽出再開は未達。TASK107はブロッカー継続として記録。


---
TASK108 実施結果（ゲート継続）
- 通信確認: `example.com` DNS解決失敗（curl/socketともNG）。
- 再実測: `records_saved_total=0` / `artists_records_saved_total=0` 継続。
- ゲート判定: `artists_failed_fetches_new_in_run / artists_text_seed_gallery_count = 10/10 = 100%`（20%超）で継続発動。
- 失敗理由上位: artists/exhibitionsともに `DNS_ERROR` のみ。
- 判定: TASK108は [x] ではなく「環境ブロッカー継続（再実測待ち）」。

---
DNS運用固定メモ（2026-02-26）
- 本体実行前に `python run_phase1_network_preflight.py` を必須化し、失敗時は fetch/collect を実行しない（fail-fast）。
- preflight失敗時は「コード改修を増やさず」環境復旧（DNS/curl確認）を先に行い、復旧後に同コマンドから再開する。

---
TASK109 実施結果（DNS preflightゲート継続）
- `python run_phase1_network_preflight.py` が exit 1（dns_ok_rate=0.000, http_probe_ok=false）。
- ゲート規約どおり、本体（seed10 fetch / image collect）は未実行で停止。
- 判定: TASK109は [x] ではなく「環境ブロッカー継続（preflight pass待ち）」。

---
TASK A-1 実施結果（内訳可視化固定）
- `run_phase1_seed10_artist_image_collect_report.py` で seed10対象CSV（frieze/liste各先頭5）を基準に `gallery_breakdown` を補完し、0件ギャラリーを必ず出力するよう修正。
- 0件の `frieze_london/Adams and Ollman` と `frieze_london/Arcadia Missa` を内訳に表示できることを確認。

---
TASK A-2 実施結果（Athr 1ギャラリー1アーティスト / works優先実装）
- `run_phase1_seed10_artist_image_collect.py` に works優先抽出を追加（worksリンク探索 → `.../works` 試行 → 0件時のみ詳細ページfallback）。
- 失敗可視化として `failed_cases[].notes` に `works_page_tried` / `works_page_found` / `works_candidates_count` / `works_not_found_fallback_used` を記録する実装を追加。
- Athr限定実行は実施できたが、この実行環境では `athrart.com` がDNS失敗となり `artist_detail_fetch_failed` で停止（works段まで未到達）。
- 判定: ロジック実装は完了、実ドメインでの効果確認はネットワーク到達環境で再確認が必要。

---
TASK D0 実施結果（DNS恒久化＋preflight強制運用）
- 恒久化設定確認:
  - `/etc/wsl.conf`: `generateResolvConf=false`
  - `/etc/resolv.conf`: `nameserver 1.1.1.1`, `8.8.8.8`, `options timeout:2 attempts:2`
  - `~/.bashrc`: `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` を固定済み
  - `.venv_art_pulse_editor/bin/activate` に同環境変数を追記（venv有効化時の固定化）
- 安定性検証:
  - `python run_phase1_network_preflight.py` を連続2回実行したが、`dns_ok_rate=0.000 (0/21)` で連続fail。
  - preflight fail-fast規約により、本体抽出は未実行で停止。
- 判定:
  - TASK D0は [x] ではなく「環境ブロッカー継続（preflight連続PASS待ち）」。
  - 次タスクは A-2再検証ではなく、D0継続（DNS復旧確認）を最優先とする。

---
TASK D0-2 実施結果（DNS復旧確認・preflight連続PASS判定）
- DNS/TLS確認:
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` は `socket.gaierror` で失敗。
  - `curl -I --max-time 15 https://example.com` は `Could not resolve host` で失敗（exit 6）。
- preflight連続実行:
  - `python run_phase1_network_preflight.py` を2回実行し、いずれも `dns_ok_rate=0.000 (0/21)` / exit 1。
  - 同秒実行のため summary は同一ファイルへ上書き保存。
- ゲート判定:
  - preflight 2連続PASS条件を満たさないため、本体抽出（seed10 fetch/image collect）は未実行で停止。
  - TASK D0-2 は [x] ではなく「環境ブロッカー継続（DNS復旧待ち）」。

---
TASK D0-3 実施結果（DNS実機切り分け・preflight連続PASS判定）
- 実機切り分け結果:
  - `/etc/wsl.conf` は `generateResolvConf=false`。
  - `/etc/resolv.conf` は `1.1.1.1 / 8.8.8.8` 固定。
  - `socket.gethostbyname('example.com')` は `gaierror` で失敗。
  - `curl -I https://example.com` は `Could not resolve host` で失敗。
  - `requests.get('https://example.com')` も `NameResolutionError` で失敗。
- preflight連続実行:
  - `python run_phase1_network_preflight.py` を2回実行し、いずれも exit 1（`dns_ok_rate=0.000 (0/21)`）。
- ゲート判定:
  - preflight 2連続PASS未達のため、seed10本体再開は未実施（fail-fast運用を維持）。
  - TASK D0-3は [x] ではなく「環境ブロッカー継続（DNS層復旧待ち）」。

---
TASK D0-4 実施結果（Windows側ネットワーク要因切り分け）
- Windows側確認:
  - `ProxyEnable=0`（明示Proxy無効）
  - `Resolve-DnsName example.com` は応答あり（Windowsホスト側のDNS解決は成功）
  - Wi-Fi DNSは `192.168.188.1`（ルーター）
- WSL側確認:
  - `/etc/wsl.conf` は `generateResolvConf=false`
  - `/etc/resolv.conf` は `1.1.1.1 / 8.8.8.8` 固定
  - `socket/curl/requests` は全て名前解決失敗
- preflight判定:
  - `python run_phase1_network_preflight.py` 2回とも exit 1（`dns_ok_rate=0.000`）
  - fail-fast規約により本体抽出は未実行
- 結論:
  - ゲート未解除。D0継続（DNS層の復旧待ち）。

---
TASK D0-5 実施結果（Windows側DNS干渉一時停止の切り分け）
- Windows側確認（読み取り）:
  - Internet Settings: `ProxyEnable=0`（明示Proxy無効）
  - WinHTTP proxy: 直接アクセス
  - DNSサーバー: Wi-Fi は `192.168.188.1`（ルーター）
  - `Resolve-DnsName example.com` はWindows側で成功
- WSL側確認:
  - `socket.gethostbyname('example.com')` / `curl` / `requests` はすべて名前解決失敗
  - `python run_phase1_network_preflight.py` 2回とも exit 1（`dns_ok_rate=0.000`）
- 判定:
  - preflight連続PASS未達のためゲート解除不可。
  - 本体抽出は未実行（fail-fast規約維持）。
  - D0-5は [x] ではなく、Windows側のDNS干渉要因（VPN/セキュリティDNS保護/DoH）の手動一時停止確認が未了。

---
TASK D0-6 実施結果（Windows側干渉停止 + WSL再起動前切り分け）
- 切り分け結果:
  - Internet Proxy: 無効（`ProxyEnable=0`）
  - WinHTTP proxy: 直接アクセス
  - Windows DNS確認: `Resolve-DnsName example.com` は成功
  - WSL側は `socket/curl/requests` が継続して名前解決失敗
  - VPN/セキュリティ系サービス/プロセスは明示ヒットなし（停止対象を自動特定できず）
- preflight判定:
  - 直近2回の preflight（`20260226T111235Z`, `20260226T111236Z`）はいずれも fail。
  - fail-fast規約により本体抽出は未実行。
- 結論:
  - D0-6は継続（手動で Windows側の VPN/DNS保護停止 + `wsl --shutdown` 後の再検証が必要）。

---
TASK D0-6.1 実施結果（ユーザー端末PASSログを正本化）
- ユーザー端末実測（正本）:
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` 成功
  - `curl -I --max-time 15 https://example.com` 成功（HTTP/2 200）
  - `python run_phase1_network_preflight.py` 2連続成功（`dns_ok_rate=1.000 (21/21)`）
  - summary:
    - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T112859Z.json`
    - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T112908Z.json`
- 恒久化対策:
  - Windows側 `C:\Users\syatk\.wslconfig` を新規作成し、`dnsTunneling=true` / `autoProxy=true` を設定済み。
- 判定:
  - D0ゲート解除（preflight連続PASS達成）。
  - 次タスクから A-2（Athr works優先の実ドメイン再検証）へ再開可能。

---
TASK A-2R 実施結果（Athr works優先 再検証）
- DNSゲート確認:
  - `python run_phase1_network_preflight.py` → exit 1（`data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115105Z.json`）
  - `sleep 1; python run_phase1_network_preflight.py` → exit 1（`data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115106Z.json`）
- ゲート判定:
  - 2連続PASS未達のため、fail-fast規約により Athr本体抽出は未実行。
- 互換確認:
  - 本体未実行のため今回は guard 比較は省略（既存最新は pass 維持）。
- 結論:
  - A-2Rは [x] ではなく「DNSブロッカー再発で継続」。
  - 次は D0系（preflight安定化）を優先し、PASS後にA-2Rを再開する。

---
TASK D0-7 実施結果（preflight再取得 + A-2R即再開判定）
- preflight確認:
  - `python run_phase1_network_preflight.py` → exit 1（`data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115331Z.json`）
  - `sleep 1; python run_phase1_network_preflight.py` → exit 1（`data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115342Z.json`）
- 判定:
  - 2連続PASS未達（`dns_ok_rate=0.000`）
  - fail-fast規約により A-2R（Athr本体実行）は未着手
- 結論:
  - D0-7は [x] ではなく「DNSブロッカー継続」。

---
TASK PREP-20260227 result (before issue 1-5 rerun)
- Problem:
  - Mixed images existed because a prior run captured multiple galleries at once.
- Actions:
  - Moved 34 image files from `data/phase1_seed10/derived/images/artist_works_images/2025/*` to `_trash/artist_works_images_cleanup_20260227T021440Z`.
  - Confirmed source folder image count is now 0.
  - Added `.gitignore` rule: `data/phase1_seed10/`.
  - Untracked existing RAG files from git index via `git rm -r --cached data/phase1_seed10` (local files kept).
- SSOT alignment:
  - Aligned with 01 section 5-7/5-8 (R2 as source of truth + local cache) and git policy for logs/data body.
- Fixed execution rule for issue 1-5:
  - one task = one gallery = one artist
  - do not run multiple galleries in one extraction run
  - update `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`, 03, and 04 after each task
- Next highest priority:
  - TASK A-2R (issue 1-1 recheck: frieze_london / Athr)

---
TASK PREP-R2-SYNC（Phase1成果物のR2同期準備）
- 内容:
  - `run_phase1_seed10_r2_sync.py` を新規追加（scope: raw/derived/enrichment/logs/all、dry-run/apply 対応）
  - apply時に `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json` を更新し、R2へ同期
- 実行:
  - `python run_phase1_seed10_r2_sync.py --scope all --dry-run` → exit 0
  - `python run_phase1_seed10_r2_sync.py --scope all` → exit 0
  - summary: `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181020Z.json`
  - uploaded=360 / skipped=134 / failed=0 / manifest_upload=true
- 判定:
  - R2同期CLIは実運用可能
- 次タスク:
  - TASK A-2R（①-1再検証: frieze_london / Athr）

- 再実行メモ:
  - `python run_phase1_seed10_r2_sync.py --scope all` 実行で `uploaded=1 / skipped=494 / failed=0`
  - summary: `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181511Z.json`
  - manifest: `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json`（`failed_count=0`）


---
TASK A-2R 実施結果（2026-02-27 / Athr works優先 再検証）
- preflight:
  - `python run_phase1_network_preflight.py` ? exit 1
  - `python run_phase1_network_preflight.py` ? exit 1
- 出力:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020117Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020135Z.json`
- 判定:
  - 2回とも `passed=False`（`dns_ok_rate=1.000` だが `http_probe_ok=False`）
  - fail-fast により Athr collect/report/guard は未実行
- 次アクション:
  - HTTP probe failure を先に解消し、A-2R は環境復旧後に再開


---
TASK D0-A2R-BLOCKER-ROOTCAUSE 実施結果（2026-02-27 / preflight失敗の根因切り分け）
- 事象:
  - preflight の `https://example.com` probe で、DNSは通るがTLS検証失敗が発生し fail-fast
- 根拠:
  - `phase1_network_preflight_summary_20260227T020117Z.json` / `...020135Z.json`
  - `dns_ok_rate=1.000` だが `http_probe_ok=False`（CERTIFICATE_VERIFY_FAILED）
- 修正対応:
  - `run_phase1_network_preflight.py` に probe URL差し替え対応を追加
  - `config/phase1_network_preflight_profile.json` に probe URL / threshold / timeout を追加
  - summary に失敗種別（tls/dns/timeout/proxy）を記録
  - 連続実行時のファイル衝突を避ける連番出力に修正
- 再実行:
  - `python run_phase1_network_preflight.py` ? exit 0
    - `phase1_network_preflight_summary_20260227T021906Z.json`
  - `python run_phase1_network_preflight.py` ? exit 0
    - `phase1_network_preflight_summary_20260227T021937Z.json`
- 判定:
  - preflight 2連続PASSを確認し、A-2R 再開可能


---
TASK A-2R-RESTART 実施結果（2026-02-27 / Athr works優先 再開）
- preflight:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
- collect:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json"` ? exit 0
- report:
  - 初回は cp932 文字化けで exit 1
  - `PYTHONUTF8=1` で再実行し exit 0
- guard:
  - `python run_compare_phase1_guard.py --target-year 2025` ? exit 0
- 判定:
  - Athr: 対象1 / 成功0 / 画像0 / 成功率0.0%
  - `failed_cases[].notes` に `works_page_tried:3`, `works_page_found:3`, `works_candidates_count:0`
  - 失敗理由は `no_image_candidates_found_on_artist_detail`（domain=`athrart.com`）


---
TASK A-2R-FIX 実施結果（2026-02-27 / Athr works candidates=0 修正）
- preflight:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
- 原因:
  - Athr works画像URLが `data-lazy` 属性にあり、既存抽出では拾えていなかった
- 修正:
  - `run_phase1_seed10_artist_image_collect.py` に `data-lazy` 抽出対応を追加
  - `run_phase1_seed10_artist_image_collect_report.py` に stdoutエンコード安全化を追加（Windows cp932対策）
- 結果:
  - collect: exit 0?Athr: 1/1 artists >=5 images, images_saved=5?
  - report: exit 0
  - guard: exit 0?guard_passed=true?
- 判定:
  - Athr の works candidates=0 問題は解消


---
TASK A-2R-FIX-1 実施結果（2026-02-27 / Athr絞り込み + Sara Abdu検証）
- preflight:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
- 退避:
  - `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__*` → `_trash/task_a2r_fix1_athr_reset_20260227T120334Z`
  - before=5 / after=0
- 修正:
  - works画像URLの `data-lazy` 取得を維持
  - URL由来の artist slug 判定と `works_urls_tried` 記録を追加
- 結果（Sara Abdu）:
  - collect exit 0 / report exit 0 / guard exit 0
  - Athr: 対象1 / 成功1 / 画像5 / 成功率100%
  - 取得ファイルは `athr__sara-abdu__...` 命名で artist検索可能

---
TASK RAG-IMAGE-SSOT-REFIT-20260227 (temporary override before TASK-107)
- scope:
  - reimplemented Artist Works image rules to close SSOT gaps (5-4 / 4-4 update logic / hash dedupe / hero strong-signal handling)
  - added metadata jsonl outputs:
    - `data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl`
    - `data/phase1_seed10/derived/artist_works_images_liste.jsonl`
- run:
  - preflight x2 PASS
  - moved active images to `_trash/task_rag_image_full_reextract_20260227_100225/` (39 files)
  - full collect rerun completed (processed=8, ge_target=7, rate=87.5%)
  - report + guard completed (guard_passed=true)
- generated:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T100759Z.json`


---
TASK TARUTANI-SSOT-REFIT-20260227
- scope:
  - TarutaniRAG の SSOT差分修正（import / r2 sync / vector manifest）
  - Tarutani vector を再生成
- done:
  - backup to _trash/task_tarutani_refit_20260227_102918/ and _trash/task_tarutani_refit_reimport_20260227_103139/
  - un_tarutani_text_import.py rerun (16 records)
  - headline_ja restored from backup (16 records)
  - un_vectorize_tarutani_text.py rerun (chunks=74, embedded=74, failed=0)
  - un_tarutani_r2_sync.py --scope source --dry-run verified source key as data/Tarutani_data/...
- outputs:
  - data/Tarutani_data/tarutani_text.jsonl
  - data/Tarutani_data/vector/tarutani_text_index.npy
  - data/Tarutani_data/vector/tarutani_text_meta.jsonl
  - data/Tarutani_data/vector/artifact_manifest.json


---
TASK PREP-R2-GUARD-20260227（R2同期の安全ガード固定）
- 目的:
  - 01/02 準拠で、R2同期を運用依存ではなく CLI ガードで強制する。
- 実装:
  - 現行入口: `run_r2_sync.py`（scope別 `plan` / `apply-upload` / `apply-prune`）
  - 設定集約: `config/r2_sync_targets.json`（scope / prefix / include / exclude）
  - 安全装置: default plan、applyは `--apply --run-id` 必須、pruneは `--confirm-prune --max-prune` + stability（2回一致）必須
- 運用テンプレ（固定）:
  - Phase1:
    - `python run_r2_sync.py plan --scope phase1_seed10_formal --run-id <RUN_ID>`
    - `python run_r2_sync.py apply-upload --scope phase1_seed10_formal --apply --run-id <RUN_ID>`
    - `python run_r2_sync.py apply-prune --scope phase1_seed10_formal --apply --run-id <RUN_ID> --confirm-prune --max-prune 600`
  - Tarutani:
    - `python run_r2_sync.py plan --scope tarutani_source --run-id <RUN_ID>`
    - `python run_r2_sync.py apply-upload --scope tarutani_source --apply --run-id <RUN_ID>`
  - gallery_lists（opt-in）:
    - `python run_r2_sync.py plan --scope gallery_lists --run-id <RUN_ID>`
    - `python run_r2_sync.py apply-upload --scope gallery_lists --apply --run-id <RUN_ID>`（prune禁止）
- 基準スナップショット（現行正）:
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260227T121330Z.json`（apply）
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_logs_20260227T121741Z.json`（限定prune apply）
  - `data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121540Z.json`（apply）
  - `data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121748Z.json`（限定prune apply）


---
TASK A-3A-CLOSE-1 実施結果（2026-02-27 / Adams and Ollman）
- SSOT整合ゲート（章ID/CARD）確認:
  - 01: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- preflight:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - outputs:
    - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T125944Z.json`
    - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T125944Z_01.json`
- Step2特定結果:
  - `artists_frieze_london_2025.jsonl` に `Adams and Ollman` 行が 0 件（`artists_file_hit=0`）
  - 本タスクでは代替として `exhibitions_frieze_london_2025.jsonl` の `source_url=https://adamsandollman.com/Past-Exhibitions` を参照
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close1_adams_ollman_reset_20260227_220415/`
  - result: moved=0, src_remaining=0
- 再実測:
  - collect: `phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman.json` -> exit 0（`no targets`）
  - report: `phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman_report.json` -> exit 0
  - guard: `phase1_guard_summary_2025_20260227T130507Z.json` -> exit 0（guard_passed=false）
- 判定:
  - 今回は「理由付きスキップ（前提データ不足）」とする
  - 理由:
    - 1ギャラリー=1アーティスト実測の入力源である `artists_frieze_london_2025.jsonl` に対象ギャラリーのartistレコードが未生成
    - そのため collector が `seed_artist_count=0` となり works優先判定まで進行不可
  - 再開条件:
    - `artists_frieze_london_2025.jsonl` に `gallery_name_en=Adams and Ollman` のartistレコードを少なくとも1件生成してから再実測


---
## TASK A-3A-FIX-1 (2026-02-27)
- Done:
  - Added 1 artist seed for `Adams and Ollman` to `artists_frieze_london_2025.jsonl`.
  - source_url: `https://adamsandollman.com/Jonathan-Berger-1`
  - Re-ran `A-3A-CLOSE-1` style measurement with 1 gallery = 1 artist.
- Result:
  - `seed_artist_count=1` (previous `0` issue resolved)
  - `works_urls_tried` includes `/works`
  - `works_candidates_count=0`, `saved_images=0`, `selected_image_years_top5=[]`
  - fail reason: `no_image_candidates_found_on_artist_detail`
- Current status:
  - 3-1 `frieze_london / Adams and Ollman`: seed-missing issue resolved, works-image extraction still unresolved.
  - Next step is quick generic-logic verification; if still no improvement, move to reasoned skip under 01 section 6-2.

---
## TASK A-3A-CLOSE-2 (2026-02-27)
- Scope:
  - 3-1 `frieze_london / Adams and Ollman` (1 gallery = 1 artist)
  - source_url fixed: `https://adamsandollman.com/Jonathan-Berger-1`
- Result:
  - preflight x2 PASS
  - generic non-`img` candidate extraction was added and verified
  - rerun still `works_candidates_count=0`, `saved_images=0`
  - failed reason: `no_image_candidates_found_on_artist_detail`
- Decision:
  - 01 section 6-2 compliant **reasoned skip** is fixed for 3-1.
  - reason: no extractable works image references in current public HTML/DOM without domain-specific hack.
  - skip registry: `data/gallery_lists/skipped_galleries_registry.csv` に1行追記運用を固定。
  - auto behavior: listed galleries are now skipped automatically by `run_phase1_seed10_artist_image_collect.py`.
- Next priority:
  - move to 3-2 `frieze_london / Arcadia Missa` with the same 1-gallery/1-artist rule.

---
## TASK A-3B-CLOSE-1 (2026-02-27)
- Scope:
  - 3-2 `frieze_london / Arcadia Missa` (1 gallery = 1 artist)
- Result:
  - preflight x2 PASS
  - Arcadia Missa artist seed was missing in `artists_frieze_london_2025.jsonl`; one seed was added for `https://arcadiamissa.com/brad-kronz/`
  - rerun result: `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `works_urls_tried=['https://arcadiamissa.com/brad-kronz/works']`
  - `selected_image_years_top5=[2026, 2026, 2026, 2026, 2026]`, `selected_image_year_desc_ok=true`
- Decision:
  - ③-2 Arcadia Missa の「0件課題」は解消（skip化なし）。
- Next priority:
  - ⑤ `liste / anca-potera-u-gallery` のロゴ/アイコン混入判定（6-2準拠で成功 or 理由付きスキップ確定）。


---
## TASK A-3B-DUP-FIX-1 (2026-02-27)
- Scope:
  - Arcadia Missa duplicate-photo fix after A-3B-CLOSE-1.
- Findings:
  - duplicate root cause was URL-hash dedupe by raw URL (scaled variants treated as different).
  - old metadata hash fallback also allowed duplicate reinjection.
- Fix:
  - image dedupe normalized by removing `-WxH` suffix.
  - metadata merge now also dedupes by normalized URL identity.
- Rerun result:
  - duplicate eliminated (`unique selected URLs=4/4`).
  - current saved count is 4 (target 5 unmet) due unique candidates shortage.
- Next priority:
  - TASK A-5-CLOSE-1 (`liste / anca-potera-u-gallery` logo/icon????) ????

---
## TASK A-3B-FIX-2 (2026-02-28)
- Scope:
  - Arcadia Missa / Brad Kronz の「4枚止まり」原因調査と5枚化（1ギャラリー=1アーティスト）
- Root cause:
  - 既存メタの全ハッシュを既知扱いしていたため、ローカル実ファイルが無い候補まで再取得対象から除外されていた。
  - `max_year_seen` / `topN hash prev` による候補除外が、不足補充時にも効いてしまい、5枚目候補を落としていた。
  - artist一致性判定で「artist URL配下ページなら無条件許可」していたため、他作家画像が混入し得た。
- Fix:
  - `run_phase1_seed10_artist_image_collect.py`
    - `seen_image_url_hashes` を「実在かつ有効なローカルキャッシュ由来ハッシュ」のみに変更
    - 不足補充時の候補除外（`max_year_seen` / `topN hash prev`）を撤廃
    - artist一致性の無条件許可を削除し、URL/evidence のトークン一致で判定
- Re-measure result:
  - preflight x2 PASS
  - `saved_images=5`, `target_met=true`
  - `selected_image_years_top5=[2026, 2026, 2026, 2026, 2025]`（降順OK）
  - 5件すべて Brad Kronz 由来URL（他作家混入なし）
- Next priority:
  - ④ The Approach（壊れ画像）または ⑤ Anca Poterașu（ロゴ混入）の未解決タスクへ復帰

---
## TASK A-5-CLOSE-1 (2026-02-28)
- Scope:
  - ⑤ `liste / Anca Poterașu Gallery` を `anetta-mona-chisa` 以外で再検証（`aurora-kiraly` 固定）
- Result:
  - preflight x2 PASS
  - source_url: `https://www.ancapoterasu.com/artists/aurora-kiraly/`
  - works URL試行: `.../aurora-kiraly/works`（404）-> detail fallbackで取得
  - `saved_images=4`, `target_met=false`, `selected_image_years_top5=[2022, 2022, 2022, 2021]`
  - selected画像URL/evidenceで `logo/icon/sprite/favicon/hero/profile/exhibition` 混入は確認されず
- Note:
  - `only-source-url` 指定時に gallery上限(1件)より前に候補絞り込みできるよう collector を修正済み。
- Next priority:
  - ④ `frieze_london / The Approach` の壊れ画像課題に復帰

---
## TASK A-5-CLOSE-1-UPDATE (2026-02-28)
- Scope:
  - `liste / Anca Poterașu Gallery` を non-anetta (`aurora-kiraly`) で再修正・再実測
- Fix:
  - `run_phase1_seed10_artist_image_collect.py`
    - `only-source-url` 指定時、gallery上限適用前に source を優先してターゲット化
    - artist一致性を汎用緩和（artist詳細URL + 姓一致 + 作品情報シグナルで許可）
- Result:
  - `saved_images=5`, `target_met=true`
  - `selected_image_years_top5=[2025, 2022, 2022, 2022, 2021]`（降順OK）
  - selected URL/evidence で logo/icon/sprite/favicon/hero/profile/exhibition 混入なし
  - 退避していた `anetta-mona-chisa` 5枚はローカルへ復元済み
- Next priority:
  - ④ `frieze_london / The Approach` の壊れ画像課題を再開
### TASK A-3A-CLOSE-3 完了（Adams and Ollman skip最終確定）
- 日付: 2026-02-27
- 判定: 「汎用ロジック範囲で未達のため理由付きスキップ」を正式確定
- 根拠:
  - skip registry 登録済み: `data/gallery_lists/skipped_galleries_registry.csv`
  - 再実測 summary で `auto_skipped_by_registry:1` を確認
  - 新規画像保存 0件（対象は抽出せず自動スキップ）
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T185732Z.json`
- 再開条件:
  - 公開DOMで works 画像URLが取得可能になること
  - またはドメイン依存なしで他ギャラリーにも効く汎用抽出要件が成立すること
- 2026-02-28：POLICY-UPDATE-ARTIST-GLOBAL-DEDUPE 実施。01 4-0-A の方針を更新し、Artist系抽出（artists_text / artist works images）の重複抽出を「同一フェア内のみ」から「全フェア・全ギャラリー横断で禁止」へ変更。`run_phase1_seed10.py` と `run_phase1_seed10_artist_image_collect.py` に `artist_master_global.json`（`data/phase1_seed10/logs/artist_master_global.json`）を用いた自動スキップを実装。summary へ global dedupe メタを記録。※ExhibitionsRAG にはこのスキップを適用しない。
- 2026-02-28：4-0-A 失敗リトライ運用を image collect 側へ実装。`run_phase1_seed10_artist_image_collect.py` に `failed_fetches_artist_image_collect_2025.json` を追加し、failed URL を cooldown + retry上限で自動スキップ。テスト時のみ `--force-retry-failed` / `--clear-failed-ledger target|all` を使用可能。
- 2026-02-28：MAX_ARTISTS_PER_GALLERY を 3 に引き上げ（`run_phase1_seed10.py` / `run_phase1_seed10_artist_image_collect.py`）。10ギャラリー対象で再実行し、skip運用の Adams and Ollman を除く実質9ギャラリーに適用。既存成功画像は削除せず保持したまま不足分のみ追加抽出。
- 2026-02-28：max=3 再実測結果。`seed_artist_count=25` / `max_artists_per_gallery_for_collect=3` / `auto_skipped_by_registry=1`。Arcadia Missa は raw artist 母数が1件（`artists_frieze_london_2025.jsonl`）のため 1名処理のまま。
- 2026-02-28：TASK A-REPRO-FIX-1 実施。`run_phase1_seed10_artist_image_collect.py` に (1) payload hash 最終重複ガード、(2) token空 artist seed 除外、(3) `--force-retry-failed` 時の works URL 再評価を追加。再実測で `athr__30__*` 非再生成を確認。
- 2026-02-28：A-REPRO-FIX-1 再実測メモ。Song Burnsoo は 5件ユニーク化、Chong Kim Chiew は同一実体5連続を解消し3件ユニーク、Gan Chin Lee は再抽出0件（重複再生成なし）。次段で The Approach / Afriart / Anca の未達（枚数不足）を個別に詰める。
- 2026-02-28：TASK A-REPRO-FIX-2 実施。artist一致性のartist配下緩和、works URL抽出のartist配下優先、tiny->large/medium 画像取得を追加。再実測で `ge_target=21/24 (87.5%)` に改善。
- 2026-02-28：A-REPRO-FIX-2 結果。The Approach / Afriart / Anca は 3名×5枚を達成。残課題は A+ Works of Art のみ（`Chong Kim Chiew=3/5`）。A+ Works の最終2件補完を次タスク最優先とする。
- 2026-02-28：TASK A-REPRO-FIX-3 実施。`Gan Chin Lee` は seed（`artists_liste_2025.jsonl`）に実在することを確認しつつ、A+ Works で他作家混入の既存5枚を `_trash/task_a_repro_fix3_gan_reset_manual/` へ退避。再実測で `Gan=0/5`（誤混入停止）、`Chong=3/5`（未達継続）、`Ahmad=5/5`。全体は `ge_target=17/24 (70.83%)`。
- 次の最優先：A+ Works of Art の `Chong Kim Chiew 3/5` を 5/5 に補完（works候補は取得済みのため、候補採択/ダウンロード段の汎用改善を優先）。
- 2026-02-28：TASK A-REPRO-FIX-4 実施。`Chong Kim Chiew` 単独再実測は継続して `3/5`。`extract_image_candidates` + works-only + artist一致性を直接検証した結果、`pass_both` の正規化ユニーク画像は3件のみ（同一作品のサイズ違いを除くと増えない）を確認。
- 2026-02-28：`the-approach__tom-allen__...__img_03.jpg` は前回の invalid cache quarantine で `_trash/invalid_cached_images_20260228T051411Z/...` へ移動されていたため、元パスへ復元済み（4枚→5枚に回復）。
- 次の最優先：A+ Works of Art / Chong の 5枚化可否を「works-onlyの範囲で追加画像ソースが実在するか」再確認し、不可なら 6-2準拠で理由付き確定（または仕様更新提案）。
- 2026-02-28：TASK A-REPRO-FIX-5 実施。Chong を再実測しても `3/5` 維持。works URL 5件を再監査し、works-only + artist一致性を満たす正規化ユニーク画像は 3件のみを再確認。
- 2026-02-28：A-REPRO-FIX-5 最終判定（6-2準拠）。`A+ Works / Chong` は works-only範囲で追加ソース確認不可のため、現時点で `3/5` を上限として理由付き確定。再開条件は「works配下に新規ユニーク作品画像が追加される」または「01仕様変更で works-only 条件が緩和される」こと。
- 2026-02-28：TASK A-2A-CLOSE-2 最終確定。`A+ Works of Art` を2名固定で再実測し、`Chong=3/5`（works_only_artist_match_unique_count=3）、`Gan=0/5`（works_only_artist_match_unique_count=0）を確認。
- 2026-02-28：A-2A-CLOSE-2 判定（01 6-2準拠）。works-only範囲で追加ユニークソース無しのため、5枚化は現時点で不可として理由付き確定。再開条件は「サイト側でworks画像が増える」または「01仕様変更で抽出許容範囲を変更する」こと。
- 2026-02-28：TASK A-REPRO-CHECK-ALL-1 実施。max=3 の全体再計測を再実行し、`processed=24` / `ge_target=17` / `success_rate=70.83%` を確認。`Adams and Ollman` は skip registry により自動スキップ（`auto_skipped_by_registry:1`）。
- 2026-02-28：A-REPRO-CHECK-ALL-1 補足。`run_phase1_seed10.py` と image collect を並列実行した競合で The Approach 判定値が崩れたため、この結果は採用しない。`tom-allen__img_05` を `_trash/invalid_cached_images_20260228T061552Z/...` から復元済み。
- 2026-02-28：TASK A-REPRO-TRIAGE-2 実施（固定入力: `...summary_task_a_repro_check_all_1.json`）。原因分類を5件で確定。
- 2026-02-28：分類結果。Arcadia追加2枠= `SEED_INVALID`（fixed summaryの `gallery_breakdown.artist_count=1` により追加seed不在）、Athr 1枠= `SEED_INVALID`（`invalid_artist_seed_token_empty`）、A+ Works `Gan=ARTIST_CONSISTENCY_FILTERED_ALL`、`Chong=NO_NEW_IMAGES_GE_MAX_YEAR_SEEN`（上限確定）。
- 2026-02-28：未達再抽出CSVを最小化。`data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv` は 1件（`A+ Works / Gan Chin Lee`）のみを正とする。
- 次の最優先FIX: `TASK A-REPRO-FIX-7（A+ Works / Gan 0/5 の artist一致性全落ち解消）`。
- 2026-02-28：TASK A-REPRO-FIX-7 実施。preflight 2連続PASS後、`A+ Works / Gan Chin Lee` を単独再実測。`works_candidates_count:27` に対し `artist_consistency_filtered:27` / `works_only_artist_match_unique:0` で `saved_images=0/5` のまま。
- 2026-02-28：A-REPRO-FIX-7 判定（01 6-2準拠）。works-only 範囲で Gan 一致候補が現時点で確認できないため未達確定（暫定）。再開条件は「works配下のGan一致情報追加」または「01仕様変更」。
- 次の最優先FIX: `TASK A-REPRO-FIX-8（A+ Works / Gan seed根拠再監査と、works-only整合を崩さない候補解放条件の最小修正検証）`。
- 2026-02-28：TASK A-REPRO-FIX-8 実施。`A+ Works / Gan` の source_url は実アクセス時に `https://aplusart.asia/artists/` へリダイレクトされることを確認。
- 2026-02-28：collectorに「artist詳細URLが汎用一覧へリダイレクトされた場合の検知」を追加。`reason=seed_invalid_redirected_to_listing` として誤候補探索を停止。
- 2026-02-28：A-REPRO-FIX-8 判定（01 6-2準拠）。Gan 0/5 の主因は artist一致判定ではなく seed URL無効（一覧吸収）で確定。再開条件は「Ganの有効source_url再取得」。
- 次の最優先FIX: `TASK A-REPRO-FIX-9（A+ Works の最新artists導線から Gan 有効source_url再解決 → 1アーティスト再実測）`。
- 2026-02-28：TASK A-REPRO-FIX-9 実施。A+ Works artists導線と sitemap を再監査し、Gan候補URLは `https://aplusart.asia/artists/41-gan-chin-lee/` のみ確認（ただし実アクセスで `/artists/` へ302）。
- 2026-02-28：Gan単独再実測結果は `reason=seed_invalid_redirected_to_listing` / `saved_images=0/5`。`seed_invalid` は継続。
- 2026-02-28：A-REPRO-FIX-9 判定（01 6-2準拠）。現時点で有効なGan artist詳細URLを導線上で再解決できないため未達確定。再開は seed再生成（artists raw更新）を先行させる。
- 次の最優先FIX: `TASK A-REPRO-FIX-10（A+ Works artists raw再生成→Gan seed再供給→1アーティスト再実測）`。
- 2026-02-28：TASK A-REPRO-FIX-10 実施。`run_phase1_seed10.py --include-artists-text` で artists raw再生成を再実行したが、Gan seedは有効URLに更新されず。
- 2026-02-28：A+ artists導線と sitemap 監査で Gan候補は `https://aplusart.asia/artists/41-gan-chin-lee/` のみ確認。ただし同URLは実アクセスで `/artists/` 一覧へ302。
- 2026-02-28：Gan単独再実測は `reason=seed_invalid_redirected_to_listing`、`saved_images=0/5` で未達継続。
- 次の最優先FIX: `TASK A-REPRO-FIX-11（A+ Works Gan を seed供給元起点で再取得する代替導線の設計/実装可否判定）`。
- 2026-02-28：TASK A-REPRO-FIX-11 実施。Arcadia/Athr の 0枚枠を seed補正のみで再検証。
- 2026-02-28：Arcadia seedを 1 -> 3 に補正（`hannah-black`, `jesse-darling` 追加）し、両者とも単独再実測 `5/5` 達成。
- 2026-02-28：Athr は token空seedを有効URLへ置換（`30-ahaad...` ほか）し、0枚枠対象 `ahaad` で単独再実測 `5/5` 達成。
- 2026-02-28：判定。Arcadia/Athr の未達は抽出ロジックではなく seed不備が主因で確定。0枚枠は解消。
- 次の最優先FIX: `TASK A-REPRO-FIX-12（A+ Works / Gan のみ未解決として seed供給元起点の再設計）`。


## TASK MAX5-ROLLUP (2026-02-28)
- ??: MAX_ARTISTS_PER_GALLERY ? 5 ????? artist works images ???????
- ??: processed=43, ge_target=32, success_rate=74.42% (threshold_passed=true)
- ????: Arcadia Missa / Athr / Gallery Baton / Addis Fine Art / Afriart Gallery / Anca Potera?u Gallery
- ???????: The Approach (0/5???), Amanita (4/5???)
- ??: Adams and Ollman ? skip registry ??????????
- ???: The Approach ? 5??????????????????2???????


## TASK MAX5-STABILITY-1?2026-02-28?
- ??: `orphan cleanup` + `works404??????` + `seed_supply????`???if???
- ??:
  - The Approach: 5?? ge_target 0 -> 2 ????Sara/Anderson=5???Tom??? orphan cleanup ????
  - Arcadia Missa: 3?=??5????? seed??? 3/5 ? under_cap ?????
  - A+ Works of Art: 5?? ge_target=1 ????????seed/????????????
- ???: The Approach ???3??Tom/Phillip/Helene???????????????????? 6-2 ?????????????

- 2026-02-28: The Approach再現性修正（metadata_refetch_required）適用後、The Approach 5名が全員5枚達成を再確認。
- 次: max=5全体の未達再点検に戻る（Arcadia/Athr/A+ Worksの残課題監査を優先）。

- 2026-02-28：TASK MAX5-UNRESOLVED-1 実施。未達再抽出対象を3件（A+ Worksのみ）へ最小化し再実測。結果は Gan=0/5, Ha Ninh=1/5, Ho Rui An=0/5 で未達継続。
- 2026-02-28：The Approach は回復確認済み、Amanita 4枚は上限許容として除外維持。
- 次の最優先: A+ Works の seed供給/導線再解決タスク（Gan seed_invalidの解消を先行）。

- 2026-02-28：TASK MAX5-CLOSE-GATE-1 実施。Arcadia Missa は seed供給上限（3/5）として確定、A+ Works は Gan=closed_seed_invalid / Ha Ninh・Ho Rui An=closed_candidate_limit で打ち切り確定。
- 2026-02-28：reextract_targets_task_max5_unresolved_1.csv は closed reason_code に凍結済み。gallery skip registry への追加は行わない。
- 次: max=5本流タスクへ復帰（新規ギャラリー/新規artist拡張を優先）。

- 2026-02-28：MAX_ARTISTS_PER_GALLERY=80（01正本値）で10ギャラリー対象のartists画像RAG抽出を実行。processed=180 / ge_target=145 / success_rate=80.56% / threshold_passed=true。
- 2026-02-28：skip運用が反映（Adams and Ollman / Arcadia Missa は自動スキップ）し、他8ギャラリーで抽出実行。
- 2026-02-28：次の主タスクは A+ Works of Art の未達整理（closed対象を除いた残件の方針確定）。
- 2026-03-01：Adams画像の重複再発（01=02, 03=04）に対して、画像URL正規化を汎用修正（Cargo系 `/t/original` と `/w/<size>` の同一元画像を同一視）。
- 2026-03-01：Adams単独再テスト（Jonathan/Jose/Katherine）。Jose・Katherine は5/5で重複解消を確認。
- 2026-03-01：Jonathan Berger は `works_candidates_count:0` 継続で 0/5。現状は供給側候補不足として扱い、追加改修は保留。
- 2026-03-01：Jonathanが手動seed（`Artist page seed for ...`）由来だったため、image collect のtarget読み込みで手動seedを汎用除外するガードを追加。
- 2026-03-01：`artists_frieze_london_2025.jsonl` から手動seed 4件をバックアップ付きで除去。Adamsは自動抽出3名（Jose/Katherine/Mariel）で再実測へ切替。
- 2026-03-01：回帰テスト（全10ギャラリー×各1名退避→単独再抽出）を実施し、10/10で `saved_images=5`・重複再発なしを確認。
- 2026-03-01：上記通過後に `MAX_ARTISTS_PER_GALLERY=80` 全体再実行。processed=225 / ge_target=184 / success_rate=81.78% / threshold_passed=true。
- 2026-03-01：Arcadia Missa=18/18 ge_target(100.0%)、Adams and Ollman=18/20 ge_target(90.0%) で改善確認。A+ Works of Art は ge_target=7/28(25.0%) で横ばい。
- 2026-03-01：運用更新。`data/gallery_lists/skipped_galleries_registry.csv` は 0件（空）に確定。
- 2026-03-01：Artists画像RAG抽出（10ギャラリー、MAX80、現行汎用コード）は本テスト範囲で完成扱いとする。
- 2026-03-01：TASK111 実施。Artistsテキストで URL canonical化 + 候補重複整理を汎用実装。Athr/A+ Works/Addis の coverage は `17/39`,`28/44`,`25/37` を維持（低下なし）。重複除外ポリシー（text_hash）は変更せず、URL表記ゆれ吸収のみ追加。
## 166. TASK T-116-EXHIBITIONS-IMAGE-MAX7
-  - 01/02/03/04 の順でルールを確認し、`MAX_EXHIBITIONS_PER_GALLERY = 7`（1 展示 × 1 画像 × 最大7 件）で200-EXHIBITIONS収集を再実行。Exhibitionsテキスト作業は現在停止中で、画像抽出に専念。  
-  - 実績: 39 件の展示に対し `ge1=37`/`ge_target=37`/`saved_images_total=37`（不足の 2 件は2025 年の展示数が 4 件以下であったため MAX7 に届かず、取得可能な範囲で収束）。  
-  - 補足: MAX7 はあくまで上限であり、全ギャラリーで7件揃うわけではないという状況を明記。

## 追記（2026-03-02 / TASK117 fix2 反映）

### STATE_SNAPSHOT 更新
- Exhibitions画像抽出は T-117 で MAX7 再実測を完了。
- 汎用修正（seed供給改善 / listing→detail展開2段 / 2025優先）適用後、`ge_1=47/51 (92.16%)` まで改善。
- `existing_hit_only` と `new_saved_images` を分離し、見かけ成功を混同しない集計へ更新（fix2結果は `new_saved=0 / existing_hit_only=47`）。
- 現在の主課題は未達4件（Athr中心）の扱い整理。

### NEXT_TASKS 更新
- [x] 117) Exhibitions画像の未達主因（seed不足 / 一覧URL混在 / 年判定弱さ）を汎用ロジックで是正し、MAX7再実測で改善確認。
- [ ] 118) Exhibitions画像の未達4件を最小対象で再評価し、追加改修か6-2準拠の理由付き確定かを決定する。

### CHANGELOG 追記
- 2026-03-02：TASK117 完了。`run_phase1_seed10.py` のExhibitions seed抽出をdetail優先スコア化、`run_phase1_seed10_exhibition_image_collect.py` にlisting→detail展開と2025優先ロジックを実装、`run_phase1_seed10_exhibition_image_collect_report.py` にURL種別/展開数/ギャラリー別内訳を追加。再実測結果は `seed=51 / ge1=46 / ge_target=46 / failed=5`。guard pass、R2 derived同期（dry-run→guarded apply）実施。
- 2026-03-02：TASK117 fix2 追補。`run_phase1_seed10_exhibition_image_collect_report.py` の `new_saved_images_total` 集計を `saved_images` フォールバックなしへ修正し、summary/reportの整合を回復。MAX7再実測の確定値を `seed=51 / ge1=47 / ge_target=47 / failed=4` に更新。R2 derivedは `dry-run -> guarded apply` を再実行し、`uploaded=0 / skipped=1069 / pruned=8 / failed=0` を確認。




## TASK285 CLOSEOUT SNAPSHOT (Exhibitions Text Controlled Operation)
- status: COMPLETED (closeout)
- final_lane_state: READY=58 / ESCALATE=5 / HOLDING=6 / REJECT=0
- weekly_continuation_policy: Week22+ continuation proof runs are discontinued.
- reopen_trigger: blocker fired (ratio_two_consecutive / route_degradation / boundary or integrity breach), spec change, or monitored state corruption.
- next_action: Exhibitions Text controlled operation remains closed; move project focus to the next primary phase unless a reopen trigger occurs.

## TASK286 PHASE1 CLOSEOUT SIGNOFF + PHASE1.5 EXIT REVIEW PROTOCOL FREEZE
- phase1_signoff: COMPLETED for 5 RAG categories at 10-gallery operational scope.
- phase1_5_exit_review: mandatory before Phase 2.
- fixed_order: 1) Tarutani_Text -> 2) Artist Works Images -> 3) Artist Text -> 4) Exhibitions Image -> 5) Exhibitions Text.
- fixed_per_category_flow: final check -> minimal fix (if needed) -> minimal re-validation -> Exit Review completion declaration.
- fixed_review_axes_6: generality / risky implementation / commonization-reuse / quality-line fit (70%) / operational resilience / next-phase connectivity.
- fix_classes: A=local fix, B=common core promotion candidate.
- minimum_artifacts: per-category review report; re-validation evidence only when fixes were applied; one cross-category common-core promotion summary after all five reviews.
- operation_switch: do not add routine weekly proof continuation; use normal-mode minimal checks, and incident-mode detailed runbook only for anomaly triggers.
- phase2_gate: Phase 2 starts only after Phase 1.5 completion.
- next_mainline_tasks:
  - TASK287 = PHASE1_5_EXIT_REVIEW_01_TARUTANI_TEXT
  - TASK288 = PHASE1_5_EXIT_REVIEW_02_ARTIST_WORKS_IMAGES
  - TASK289 = PHASE1_5_EXIT_REVIEW_03_ARTIST_TEXT
  - TASK290 = PHASE1_5_EXIT_REVIEW_04_EXHIBITIONS_IMAGE
  - TASK291 = PHASE1_5_EXIT_REVIEW_05_EXHIBITIONS_TEXT
  - TASK292 = PHASE1_5_COMMON_CORE_PROMOTION_CANDIDATE_SUMMARY
  - TASK293 = PHASE2_KICKOFF_GATE_AFTER_PHASE1_5_EXIT_REVIEW
- deferred_verification (anti-mixing safety):
  - 汎用抽出ロジック（候補URL選別 / URL正規化 / dedupe / listing→detail fallback など）を変更した場合、
    “後から忘れて混線”を防ぐため、10ギャラリーだけで「統合trial/isolated再検証」を1回だけ実施して回帰有無を確認する。
  - ルール: current formal は read-only / trial は run_id 付きで隔離 / 差分（matched coverage・gallery別）を保存 / diff gateなしでadoptionしない。

## TASK292 PHASE1.5 COMMON CORE PROMOTION CANDIDATE SUMMARY
- status: COMPLETED (summary-only; no cross-RAG rollout in this task).
- phase1_5_review_status: TASK287/TASK288/TASK289/TASK290/TASK291 are completed.
- exhibitions_text_fact: baseline matched coverage 51/76=0.671053; isolated trial reached 54/76=0.710526.
- adams_arcadia_fact: generic listing-origin fallback improvement was effective in isolated revalidation (Adams overlap 10/13, Arcadia overlap 4/8); keep as watchlist for further generic tuning only.
- anti_mixing: no current formal write, no weekly proof restart, trial outputs isolated.
- next_mainline_task: TASK293 = PHASE2_KICKOFF_GATE_AFTER_PHASE1_5_EXIT_REVIEW.

## PHASE1.6 FORMALIZE OPERATION FREEZE (Minimal)
- formal_ssot_filesystem: `data/phase1_seed10/raw` + `data/phase1_seed10/derived` + `data/phase1_seed10/derived/images` is the single formal truth.
- adoption_rule: scoped replace only (`_trash` backup -> move/rename replace), append is prohibited.
- images_prune_rule: union required of Exhibitions Image + Artist Works Images is mandatory; `missing_required_count=0` is enforced.
- guard_rule: preflight/postflight gates are mandatory; `0 rows / sudden drop / required-key missing / required-image missing / required-count mismatch` => HOLD.
- next_task: `TASK_FORMALIZE_02 = PHASE1_7_MISSING_ONLY_DEFAULT_ENFORCEMENT`.
- phase2_gate: `TASK293` remains waiting and starts only after explicit user OK.

## PHASE1.7 MISSING-ONLY DEFAULT (Freeze)
- default_mode: `FILL_MISSING` (all 5 categories); existing keys are skipped and only missing records/files are eligible.
- rebuild_mode: `REBUILD` requires explicit flags and must write to run_id-isolated trial only (`trial -> gate -> adopt`).
- image_missing_rule: image key without local file is treated as missing-recovery target (not as already-saved).
- known_unresolvable_ledger: `data/phase1_seed10/logs/artist_works_images_known_unresolvable.json`
- fill_missing_behavior: entries in ledger are skipped (no-op stability); rebuild may retry.
- scope: Artist Works Images only (current).
- phase2_status: `TASK293` remains not started until user OK.


## TASK293_NEXT_14 PHASE2 MILESTONE SNAPSHOT (FEATURES 01-06)
- 現在地: Phase2 は機能①〜⑥の baseline/minimal implementation を一巡完了（read-only中心、保存処理なし）。
- ① Art Pulse: read-only overview + draft generation（根拠URL表示）。
- ② Exhibition Search: read-only listing（fair/keyword絞り込み・詳細表示）。
- ③ Artist Search: read-only listing（fair/keyword絞り込み・詳細表示）。
- ④ Advisor: type1 grounded draft + type2 minimal実装と品質/安全性tuning（gate制御、保存なし）。
- ⑤ Exclusive Advisor: type1 grounded draft + type2 minimal実装と品質/安全性tuning（外部根拠URLとTarutani抜粋を分離表示）。
- ⑥ Gallery list: read-only baseline + quality tuning（CSV 2列/3列互換、fallback表示、件数/警告表示）。
- 重要注記: ⑥は「Gallery list」が正。01は当初から正しく、今回は03/04の現状記録の是正のみ（仕様変更なし、01未変更）。
- 次の最優先タスク: TASK293_NEXT_15 = PHASE2_MILESTONE_REVIEW_AND_GO_NO_GO_FOR_POLISH_ROUND

## TASK293_CLOSEOUT_01 PHASE2 POLISH CLOSEOUT SNAPSHOT
- 現在地: Phase2は機能①〜⑥のbaseline/minimal実装とpolishingを完了し、copy freezeは `COPY_FREEZE_OK`。
- ① Art Pulse: read-only overview + draft generation（根拠URL表示）。
- ② Exhibition Search / ③ Artist Search: read-only listing + detail（fair/keyword絞り込み）。
- ④ Advisor / ⑤ Exclusive Advisor: type1 + type2（minimal+tuned、gate制御、保存なし、⑤は外部根拠URLとTarutani_Text抜粋を分離表示）。
- ⑥ Gallery list: read-only baseline + tuning（CSV 2列/3列互換、fallback/警告表示）。
- 重要注記: ⑥はGallery listが正。今回は03/04へのcloseout syncであり、01仕様変更ではない（01/02は未変更）。
- 次の最優先タスク: TASK293_NEXT_16 = PHASE2_CLOSEOUT_REVIEW_AND_GO_NO_GO_FOR_NEXT_PHASE
