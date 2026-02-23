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
LAST_UPDATED: 2026-02-23 22:58 JST


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
  - 直近の到達目標：Phase1 guard比較の運用化（TASK 20）を成立させる
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

[ ] 20) Phase1 guard比較の運用化（baseline自動解決 + CI向け終了コード整理）
    - 目的：TASK19の比較CLIを日常運用に乗せるため、baseline指定の手間と誤指定を減らす
    - 制約：取得ループには組み込まず、Post-fetch検証CLIとして分離する
    - 成立条件：
      - baseline未指定時に「最新の比較可能summary」を自動選択できる
      - `--strict-compatibility`（比較不成立を常に非0）を追加できる
      - CI向けに exit code の意味を README/summary に明記できる（0=pass,2=regression,3=incompatible）
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
- summary に `baseline_auto_selected` / `baseline_selection_reason` を保存できる
- exit code の意味（0=pass,2=regression,3=incompatible）をCLI出力とsummaryで明示できる
- 03 の NEXT_TASKS の 20) を [x]、CHANGELOG追記
- 次の最優先タスク（TASK 21）のプロンプト全文を提示する

動作確認コマンド：
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json"
- （WSL）python run_compare_phase1_guard_history.py --current-summary "data/phase1_seed10/logs/phase1_guard_summary_2025_YYYYMMDDTHHMMSSZ.json" --strict-compatibility


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
