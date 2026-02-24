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
LAST_UPDATED: 2026-02-24 17:12 JST


========================
03_EDIT_POLICY（03の更新方針：ここが崩れると詰むので固定）
========================
■ロック（Codexが絶対に変更しない）
- PROJECT_SLUG / SOURCE_SSOT
- 「重要な運用ルール（迷子防止）」の本文（方針は固定）
- CODEX_SNIPPETS（A0/A/B/C）の骨格（※文言の微調整はOKだが、意味を変えない）

■更新対象（Codexが更新してよい／更新すべき）
- LAST_UPDATED：03を更新したら必ず更新する（日時はJST）
- STATE_SNAPSHOT（現在地）：
  - 「いまの最優先フェーズ」と「直近の到達目標」を、状況に合わせて必ず更新する
  - 大きな節目（Phase移行、カテゴリ移行、seed10達成など）が起きたら必ず書き換える
- NEXT_TASKS：
  - 完了したら [x] にする
  - 新しい作業が生まれたら追記し、優先順位に並べ替える
- CODEX_TASK_PROMPTS：
  - NEXT_TASKS に新しい番号（8,9…）を追加したら、同じ番号のプロンプトも必ず作る
- CHANGELOG：
  - 作業を区切るたびに1行追記する（「何をした／どこまで到達した／次は何」）

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

■Codexが毎回やるべきこと（中断でも継続でも必須）
- ① 計画（短く：変更ファイル／変更点／動作確認コマンド）
- ② 実装
- ③ 動作確認
- ④ 03更新（必ず 02→01→03 の順で行う）
   - まず 02_RAG_SPEC_DERIVED.md（索引カード）で、今回の変更が該当するカテゴリカードを特定する（例：4-1 Exhibitions Text）
   - 次に 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）で、02が指す該当箇所（ルール/制約/用語）を確認する
   - そのうえで 03 の STATE_SNAPSHOT / NEXT_TASKS / CHANGELOG / LAST_UPDATED を更新する
   - SSOTに書かれていない「抽出/保存仕様（RAGルール）」は03に足さない（必要なら「SSOT追記案」として提案し合意を取る）。※運用固定（DOC_PATHS/実行コマンド/現在地の記録）は03に書いてOK
- ⑤ 次に進むタスク番号を1つ選び、対応する「TASK n プロンプト全文」を提示
  → ユーザーが “そのままコピペで次依頼” できる状態にする


========================
STATE_SNAPSHOT（現在地）
========================
■いまの最優先フェーズ（Codexが随時更新する）
- Phase 1：RAG抽出パイプライン成立（seed10で安定稼働させる）
  - 直近の到達目標：guard検証（history/category/lint）を統合matrixで1コマンド実行できるようにする（TASK 43）
  - 次の到達目標：Phase2（検索/表示）へ接続する
  - その次：検索品質と表示品質の改善サイクルに入る

※この「直近の到達目標」は、達成したら必ず書き換える（意味がなくなるので残さない）

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

■リスク台帳（短く：必要に応じて更新OK）
- 429/403/Timeout：同一ドメインで連続したら打ち切り、失敗一覧に残す
- R2 env の名前ゆれ：ローカル .env と Streamlit Secrets を揃える（値は書かない）


========================
NEXT_TASKS（次回やること）
========================
優先度順（上から実行）。終わったら [x] にする。
※各タスクは「計画→実装→動作確認→03更新」を1セットで回す。

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

[ ] 46) report CLIに`--fail-on-failed-matrix`を追加し、統合summaryが失敗状態なら非0終了を選べるようにする（安全側）
    - 目的：report生成は成功していても `all_passed=false` のときCIを落としたい運用に対応する
    - 制約：guard/history/lint/各matrix本体ロジックは変更しない（report CLIの終了ポリシー追加のみ）
    - 成立条件：
      - `--fail-on-failed-matrix` 指定時のみ、`all_passed=false` で exit 1
      - 未指定時は従来どおり `0=report_generated` を維持
      - 03のCHANGELOGに反映される

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


■B）中断・締め（中断するたびに貼る：03更新＋次プロンプト提示まで強制）

作業をここで区切ります。以下を必ず実施してから終了してください。
(1) 03_STATE_SNAPSHOT_NEXT_TASKS.md を更新
  - 02で該当CARD_IDを検索 → そのカードのSSOT参照に従って01の該当箇所を確認 → 01に根拠がある内容だけで03を更新（推測で更新しない）
  - LAST_UPDATED：更新
  - STATE_SNAPSHOT：現在地（最優先フェーズ／直近目標）を状況に合わせて書き換える
  - NEXT_TASKS：完了は [x]、新規タスクが発生したら追加、優先度順に並べ替え
  - CHANGELOG：今日やったことを1行追記
(2) 重要：NEXT_TASKSに新しい項目（例：8、9…）を追加した場合
  - 同じ番号で CODEX_TASK_PROMPTS に「そのままコピペできる依頼文」を必ず追加してください
  - 依頼文には「目的/参照/制約/完了条件/動作確認コマンド」を含めること
(3) 変更ファイル一覧を出す（ファイル名だけでOK）
(4) 次にやる1手（コマンド含む）を1行で書く
(5) 次に取り組む NEXT_TASKS の番号を1つ選び、対応する「TASK n プロンプト全文」をこのチャットに貼って提示する
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
========================
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
