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
LAST_UPDATED: 2026-02-22 22:55 JST


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
  - 直近の到達目標：Tarutani_Text の headline_ja 付与バッチ（実行・反映）を成立させる
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
  - PDF抽出ライブラリ未導入のため、PDFはSSOT準拠で text=""（OCRなし）
- TASK 8 完了（Tarutani_Text Enrichment入口）
  - run_enrichment_tarutani_text.py を追加（tarutani_text.jsonl読込→未付与headline_ja候補を抽出）
  - 生成物：data/Tarutani_data/enrichment/enrichment_requests_tarutani_text.jsonl（7件）
  - 生成物：data/Tarutani_data/enrichment/enrichment_summary_tarutani_text.json
- Tarutani_data のR2正本運用を整理（最小差分）
  - SSOT 5-5 に「R2正本 / source_pathメタ保持 / Git非コミット方針」を追記
  - run_tarutani_r2_sync.py を追加（dry-run/apply, logs出力）
  - dry-run結果：16ファイル / 14.59MB（本実行は未実施）
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

[ ] 9) Tarutani_Text のheadline_jaを事後バッチで実生成し、jsonlへ反映する
    - 目的：TASK 8で作成した requests を使って headline_ja を生成し、tarutani_text.jsonl を更新する
    - 制約：取り込み（fetch）ループでは実行しない。Post-fetchのバッチとして実行する
    - 成立条件：
      - headline_ja の生成結果（output）が保存される
      - tarutani_text.jsonl で headline_ja が一部以上更新される
      - 更新件数/未更新件数の summary が保存される
    - メモ：Tarutani_data のR2同期は本実行まで完了（uploaded=16, failed=0）。再実行で skipped=16 を確認（冪等）。


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
