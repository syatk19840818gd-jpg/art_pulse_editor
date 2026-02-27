

あなたは実装AI（Codex）です。次の運用ルールに厳密に従ってください。 (1) 01_PROJECT_SPEC_CURRENT_FULL.docx がSSOT（唯一の正本）です。仕様の衝突が起きたら、まずSSOTを更新してから実装を変えてください（口頭だけで変えない）。 (2) 02_RAG_SPEC_DERIVED.md は索引（カード集）です。数値は転載せず、参照先として扱ってください。更新が必要なら提案して合意を取ってから。 (3) 03_STATE_SNAPSHOT_NEXT_TASKS.md が「今日やること」です。毎回これを起点に動いてください。 (4) 禁止：完成した機能を勝手に削除/無効化しない。削除/置換/挙動変更で機能が消える可能性がある場合は、削除対象・影響範囲・代替案を示し、合意を取ってから。 (5) 禁止：ドメイン専用ハードコードの増殖。改善は「頻出ドメイン×汎用ロジック」のみ。取れない分はログに残して割り切る。 (6) 重要：4章は「4-0共通→4-1〜」を分けて実装・検証。LLM加工（headline_ja等）は取得ループ内で逐次実行しない。 初回の最初に、次の存在確認をしてください - 01_PROJECT_SPEC_CURRENT_FULL.docx - 02_RAG_SPEC_DERIVED.md - 03_STATE_SNAPSHOT_NEXT_TASKS.md - 04_TASK_PROGRESS_LOG.md 【現在の前提（引継ぎ）】 - 実行環境: Windows ローカル運用に移行済み（WSL DNS不安定回避） - fail-fast固定: 本体実行前に `python run_phase1_network_preflight.py` を2回実行し、2回PASS時のみ本体を実行 - 1回でもFAILなら本体は実行しない（ブロッカー記録のみ） - 取得ループ内LLM加工は禁止（Post-fetchのみ） - 機能削除禁止、ドメイン専用ハードコード禁止、実削除禁止 - 内訳記録は `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` に集約（タスク見出しごと、失敗0件ギャラリーも必ず記載） 【未完課題（①〜⑤）優先順】 ※03の本タスクの前に、以下の課題を解決してから03の本タスク（NEXT_TASKSのタスク）に戻ること。 1) ①-1: frieze_london / Athr の works優先抽出（Exhibitions/プロフィール混入の停止） 2) ①-2: frieze_london / Gallery Baton の works優先抽出 3) ①-3: liste / A+ Works of Art の works優先抽出 4) ②: Athr の「3枚・作品でない」問題の解消 5) ③-1: frieze_london / Adams and Ollman 0件の切り分け 6) ③-2: frieze_london / Arcadia Missa 0件の切り分け 7) ④: frieze_london / The Approach の破損画像問題 8) ⑤: liste / Anca Poteraşu Gallery のロゴ/アイコン混入抑制 ※ ③/⑤は、SSOT 6-2 に抵触する個別ハック化の恐れが高い場合はスキップ判断可（必ず理由を `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` に記録） 【①～⑤の実行単位（固定）】 - 必ず「1ギャラリーずつ」「1ギャラリー=1アーティスト」で実測・修正・再実測する - 複数ギャラリー同時対応は禁止 - 1タスクで抱えすぎない（必要なら分割） 以上を確認後、以下の ①-1:の最初の着手タスクのプロンプトで開始しますが、まだ開始しないでください。 今回のプロンプトは過去と現在と未来を理解してもらうためです。 理解できれば了解と言ってください。 【最初の着手タスク】 TASK A-2R) ①-1再検証: frieze_london / Athr を1ギャラリー1アーティストで works優先抽出の実効確認 【必須参照（章ID明示）】 - 01（SSOT） - 4-0) ①〜④共通ルール - 4-4) Artist：作品画像（抽出ルール） - 6-2) ドメイン専用ハードコード増殖の禁止 - 6-3) 品質ライン（試作10ギャラリーの運用） - SSOT整合ゲート - 02（DERIVED） - CARD_ID: 10_NO_HERO_IMAGES - CARD_ID: 11_IMAGE_TARGET_LINE - CARD_ID: 14_CATEGORY_4_0_COMMON - CARD_ID: 16_SSOT_COMPLIANCE_GATE 【参照ファイル】 - run_phase1_network_preflight.py - run_phase1_seed10_artist_image_collect.py - run_phase1_seed10_artist_image_collect_report.py - data/phase1_seed10/raw/artists_frieze_london_2025.jsonl - data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_*.json - docs/RAG_EXTRACTION_BREAKDOWN_JA.md - docs/03_STATE_SNAPSHOT_NEXT_TASKS.md - docs/04_TASK_PROGRESS_LOG.md 【実施手順（この順で固定）】 1) preflight 2回（PASS必須） python run_phase1_network_preflight.py python run_phase1_network_preflight.py 2) PASS時のみ Athr限定実行（1アーティスト） python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_athr.json" 3) report生成 python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_athr_report.json" 4) guard互換確認 python run_compare_phase1_guard.py --target-year 2025 5) 必須ドキュメント更新 - docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R 見出し） - fair/gallery - 対象人数 - 成功人数 - 取得件数（画像枚数） - 成功率% - 失敗理由上位（works関連ノート含む） - docs/03_STATE_SNAPSHOT_NEXT_TASKS.md - docs/04_TASK_PROGRESS_LOG.md 【完了条件】 - preflight 2連続PASSを確認 - Athrで works優先抽出の実効を確認 - `failed_cases[].notes` に `works_page_tried` / `works_page_found` / `works_candidates_count` が残る - 0件なら次アクション可能な粒度で理由が残る - 03/04/RAG内訳メモが更新される 【報告フォーマット（短く固定）】 1) 変更ファイル一覧 2) 実行コマンド 3) 生成物パス 4) exit code 5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行
1件のタスクが進行中


運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-RESTART) ①-1再検証: frieze_london / Athr を1ギャラリー1アーティストで works優先抽出の実効確認（preflight恒久対策反映後の再開）



【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_*.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) 2回PASS時のみ Athr限定実行（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json"

3) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json"

4) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

5) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-RESTART 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASSを確認
- Athrで works優先抽出の実効を確認
- failed_cases[].notes に works_page_tried / works_page_found / works_candidates_count が残る
- 0件の場合は次アクション可能な粒度で理由が残る
- 03/04/RAG内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行


5 件の過去のメッセージ
変更ファイル一覧
[RAG_EXTRACTION_BREAKDOWN_JA.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\RAG_EXTRACTION_BREAKDOWN_JA.md:492)
[03_STATE_SNAPSHOT_NEXT_TASKS.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\03_STATE_SNAPSHOT_NEXT_TASKS.md:6700)
[04_TASK_PROGRESS_LOG.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\04_TASK_PROGRESS_LOG.md:2983)
実行コマンド
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py
phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json"
phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json"
phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json"
python run_compare_phase1_guard.py --target-year 2025
生成物パス
[phase1_network_preflight_summary_20260227T022556Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T022556Z.json)
[phase1_network_preflight_summary_20260227T022617Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T022617Z.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json)
[phase1_guard_summary_2025_20260227T022757Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_guard_summary_2025_20260227T022757Z.json)
exit code
preflight #1: 0
preflight #2: 0
Athr collect: 0
report初回: 1（cp932 UnicodeEncodeError）
report再実行（PYTHONUTF8=1）: 0
guard: 0
補足: failed_cases[].notes に works_candidates_count (line 0) を確認。Athr結果は 対象1 / 成功0 / 画像0。

次の最優先タスク（1つ）+ MODEL_HINT + 理由1行
TASK A-2R-FIX) ①-1 Athrのworks candidates=0原因を切り分けて最小修正し、Athr単独で再実測
MODEL_HINT: HIGH
理由: preflight条件は回復したため、残るボトルネックは Athr 詳細ページでの画像候補抽出ロジック（works候補0）の実装修正に集約されたため。

今回のようにタスク終了の時点で、必ず、プロンプト全文だすようにしてほしい。

了解です。
今後は毎タスク終了時に、必ず次タスクのプロンプト全文を1つのコードブロックで添えて報告します。


いやだから、いまでてないので、出して

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX) ①-1 Athr の works candidates=0 を1ギャラリー1アーティストで原因分解し、最小修正→再実測する

MODEL_HINT: HIGH
理由: preflightは安定したため、Athrの失敗は抽出ロジック本体（works候補0）の切り分けと最小修正が中心になるため。

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) PASS時のみ Athr限定で失敗ケースの原因分解（1アーティスト）
- 直近 summary の failed_cases から Athr 対象の source_url / notes を確認
- `works_page_tried / works_page_found / works_candidates_count` と実HTML上の画像候補要素の乖離を特定
- ドメイン専用ハックにせず、既存の汎用抽出経路（worksページ優先→fallback）で最小修正案を作成

3) 最小修正を実装（必要最小限）
- 取得ループ内LLM加工は禁止を維持
- 機能削除禁止、既存成功ケースを壊さない差分に限定

4) Athr限定で再実測（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json"

5) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json"

6) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

7) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-FIX 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASSを確認
- Athrで `works_candidates_count` が0になる原因を説明可能な粒度で特定
- 最小修正後の再実測結果を提示（改善有無どちらでも可）
- failed_cases[].notes に works関連ノートが残る
- 03/04/RAG内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX) ①-1 Athr の works candidates=0 を1ギャラリー1アーティストで原因分解し、最小修正→再実測する



【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) PASS時のみ Athr限定で失敗ケースの原因分解（1アーティスト）
- 直近 summary の failed_cases から Athr 対象の source_url / notes を確認
- works_page_tried / works_page_found / works_candidates_count と実HTML上の画像候補要素の乖離を特定
- ドメイン専用ハックにせず、既存の汎用抽出経路（worksページ優先→fallback）で最小修正案を作成

3) 最小修正を実装（必要最小限）
- 取得ループ内LLM加工は禁止を維持
- 機能削除禁止、既存成功ケースを壊さない差分に限定

4) Athr限定で再実測（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json"

5) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json"

6) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

7) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-FIX 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASSを確認
- Athrで works_candidates_count が0になる原因を説明可能な粒度で特定
- 最小修正後の再実測結果を提示（改善有無どちらでも可）
- failed_cases[].notes に works関連ノートが残る
- 03/04/RAG内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行


5 件の過去のメッセージ
変更ファイル一覧
[run_phase1_seed10_artist_image_collect.py](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\run_phase1_seed10_artist_image_collect.py:511)
[run_phase1_seed10_artist_image_collect_report.py](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\run_phase1_seed10_artist_image_collect_report.py:216)
[docs/RAG_EXTRACTION_BREAKDOWN_JA.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\RAG_EXTRACTION_BREAKDOWN_JA.md:567)
[docs/03_STATE_SNAPSHOT_NEXT_TASKS.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\03_STATE_SNAPSHOT_NEXT_TASKS.md:6718)
[docs/04_TASK_PROGRESS_LOG.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\04_TASK_PROGRESS_LOG.md:3005)
実行コマンド
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py
phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json"
phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json"
python run_compare_phase1_guard.py --target-year 2025
生成物パス
[phase1_network_preflight_summary_20260227T023327Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T023327Z.json)
[phase1_network_preflight_summary_20260227T023343Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T023343Z.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json)
[phase1_guard_summary_2025_20260227T023851Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_guard_summary_2025_20260227T023851Z.json)
exit code
preflight #1: 0
preflight #2: 0
Athr collect: 0
report: 0
guard: 0
次の最優先タスク（1つ）+ MODEL_HINT + 理由1行
TASK A-2B-RESTART) ①-2 frieze_london / Gallery Baton を1ギャラリー1アーティストで works優先抽出再検証
MODEL_HINT: HIGH
理由: 優先順で次の未完課題に進み、Athr修正が他ギャラリーのworks抽出にも副作用なく適用できるかを実測で確認するため。
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2B-RESTART) ①-2再検証: frieze_london / Gallery Baton を1ギャラリー1アーティストで works優先抽出の実効確認

MODEL_HINT: HIGH
理由: Athrで入れた汎用修正（data-lazy対応）の横展開影響を、次優先ギャラリーで実測検証する必要があるため。

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_*.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) 2回PASS時のみ Gallery Baton限定実行（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Gallery Baton" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_restart_gallery_baton.json"

3) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_restart_gallery_baton.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_restart_gallery_baton_report.json"

4) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

5) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2B-RESTART 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASSを確認
- Gallery Batonで works優先抽出の実効を確認
- failed_cases[].notes に works_page_tried / works_page_found / works_candidates_count が残る（失敗時）
- 0件の場合は次アクション可能な粒度で理由が残る
- 03/04/RAG内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行

ユーザーの添付画像
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX) ①-1 で抽出されたRAG画像は、全くダメです。
添付画像もご覧頂いた上で、以下、問題点（以下、全て解決してください。ひとつの課題を一回（1タスク）でクリアしようとしなくてもいいです。キャパオーバーや荒が出そうな場合は分割し、一つ一つ確実に進めること）

1. ファイル名が、ArtistNameが入っていない。意味の分からない数字の羅列と、biographyしかなく、これで、どうやってARTISTを検索するんですか？保存ルールの5-4) Artist Works Images（4-4の成果物）をもう一度徹底的にみてください。01に無いことを勝手にしないでください
2. これはなんていう個人アーティストのページから抽出している？いろんな作品が混ざっている。やり直しなので、一旦このRAG画像は全て消去してください。
3.どこから取っているか全くわからないので、私の方から指定します。athrsのara-abduというアーティストの作品を取ってみてください。 
4. ヒントとしては、各Artistページの\Worksというページで表示されています

以上です、まずは、上記を整理し、最初のタスク計画をプロンプト全文を出して示してください

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX-1) ①-1初動修正: Athr の誤抽出画像を全退避し、SSOT 5-4準拠の命名へ最小修正したうえで、Sara Abdu の Works 由来画像のみを1ギャラリー1アーティストで再取得する

MODEL_HINT: VERY_HIGH
理由: 既存成果物の全退避・命名規則準拠・取得元の厳密固定・再抽出を同時に満たす必要があり、仕様逸脱リスクが高いため。

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 5-4) Artist Works Images（4-4の成果物・命名/保存ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) 既存Athr誤抽出画像を全退避（削除ではなく _trash へ移動）
- 対象: data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__*
- 退避先: _trash/task_a2r_fix1_athr_reset_<timestamp>/
- 退避後、対象フォルダ内の Athr 画像 0件を確認

3) 原因分解（Sara Abdu 固定）
- 対象 artist を Athr の Sara Abdu に固定（source_url も記録）
- `failed_cases[].notes` と HTML実体を照合し、worksページ由来であることを確認
- 取得元URLを明示（artist detail / works URL）

4) 最小修正（汎用のみ）
- SSOT 5-4 の命名規則に合わせ、ファイル名へ artist名（検索可能な識別子）を必須で含める
- ドメイン専用 if 文は禁止（Athr専用ハック禁止）
- 取得ループ内LLM加工は禁止を維持
- 仕様衝突が出た場合は実装前に 01 を更新してから進む

5) Sara Abdu 単独で再実測（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json"

6) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json"

7) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

8) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-FIX-1 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
  - 退避元/退避先/退避件数
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- 旧Athr画像が _trash に退避され、作業前汚染が解消
- Sara Abdu の works由来画像のみ再取得される（混在なし）
- ファイル名が SSOT 5-4 準拠で artist検索可能
- 取得元URL（どの個別Artistページ/Worksページか）をログで追跡可能
- 03/04/RAG 内訳が更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX-1) ①-1初動修正: Athr の誤抽出画像を全退避し、SSOT 5-4準拠の命名へ最小修正したうえで、Sara Abdu の Works 由来画像のみを1ギャラリー1アーティストで再取得する



【必須参照（章ID明示）】 
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 5-4) Artist Works Images（4-4の成果物・命名/保存ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/
- data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) 既存Athr誤抽出画像を全退避（削除ではなく _trash へ移動）
- 対象: data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__*
- 退避先: _trash/task_a2r_fix1_athr_reset_<timestamp>/
- 退避後、対象フォルダ内の Athr 画像 0件を確認

3) 原因分解（Sara Abdu 固定）
- 対象 artist を Athr の Sara Abdu に固定（source_url も記録）
- failed_cases[].notes と HTML実体を照合し、worksページ由来であることを確認
- 取得元URLを明示（artist detail / works URL）

4) 最小修正（汎用のみ）
- SSOT 5-4 の命名規則に合わせ、ファイル名へ artist名（検索可能な識別子）を必須で含める
- ドメイン専用 if 文は禁止（Athr専用ハック禁止）
- 取得ループ内LLM加工は禁止を維持
- 仕様衝突が出た場合は実装前に 01 を更新してから進む

5) Sara Abdu 単独で再実測（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json"

6) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json"

7) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

8) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-FIX-1 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
  - 退避元/退避先/退避件数
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- 旧Athr画像が _trash に退避され、作業前汚染が解消
- Sara Abdu の works由来画像のみ再取得される（混在なし）
- ファイル名が SSOT 5-4 準拠で artist検索可能
- 取得元URL（どの個別Artistページ/Worksページか）をログで追跡可能
- 03/04/RAG 内訳が更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行


8 件の過去のメッセージ
変更ファイル一覧
[run_phase1_seed10_artist_image_collect.py](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\run_phase1_seed10_artist_image_collect.py:114)
[run_phase1_seed10_artist_image_collect_report.py](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\run_phase1_seed10_artist_image_collect_report.py:218)
[docs/RAG_EXTRACTION_BREAKDOWN_JA.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\RAG_EXTRACTION_BREAKDOWN_JA.md:652)
[docs/03_STATE_SNAPSHOT_NEXT_TASKS.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\03_STATE_SNAPSHOT_NEXT_TASKS.md:6736)
[docs/04_TASK_PROGRESS_LOG.md](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\docs\04_TASK_PROGRESS_LOG.md:3021)
実行コマンド
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py
Athr既存画像退避（athr__* を _trash/task_a2r_fix1_athr_reset_20260227T120334Z へ移動）
phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json"
phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json"
python run_compare_phase1_guard.py --target-year 2025
生成物パス
[phase1_network_preflight_summary_20260227T030220Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T030220Z.json)
[phase1_network_preflight_summary_20260227T030241Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_network_preflight_summary_20260227T030241Z.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json)
[phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json)
[phase1_guard_summary_2025_20260227T030932Z.json](C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_guard_summary_2025_20260227T030932Z.json)
退避先: _trash/task_a2r_fix1_athr_reset_20260227T120334Z（before=5, after=0）
退避先: _trash/task_a2r_fix1_athr_rerun_20260227T120827Z（再実測用）
exit code
preflight #1: 0
preflight #2: 0
collect (Sara Abdu only): 0
report: 0
guard: 0
次の最優先タスク（1つ）+ MODEL_HINT + 理由1行
TASK A-2B-FIX-1) ①-2: frieze_london / Gallery Baton を1ギャラリー1アーティストで works優先抽出再検証
MODEL_HINT: HIGH
理由: 優先順の次課題で、今回の汎用修正（命名/works抽出）が別ギャラリーでも安定するか実測確認が必要なため。
運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2B-FIX-1) ①-2初動検証: frieze_london / Gallery Baton を1ギャラリー1アーティストで works優先抽出し、Athr修正の横展開有効性を確認する

MODEL_HINT: HIGH
理由: Athrで入れた汎用修正（artist命名/works抽出）が他ギャラリーで破綻しないことを実測確認する必要があるため。

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
  - 5-4) Artist Works Images（4-4の成果物・命名/保存ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) PASS時のみ Gallery Baton 限定実行（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Gallery Baton" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_fix1_gallery_baton.json"

3) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_fix1_gallery_baton.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_fix1_gallery_baton_report.json"

4) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

5) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2B-FIX-1 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- Gallery Baton で works優先抽出の実効を確認
- ファイル名が SSOT 5-4 準拠で artist検索可能
- 取得元URL（detail / works URL）がログで追跡可能
- 03/04/RAG 内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX-1) ①-1ありがとう。前回上げた問題は解決できています
さらに追加修正、課題を以下にあげます

・01の4-4) Artist：作品画像、【年の抽出ルール（作品画像）】にあるように、最新年順の抽出の実装は入っている？Worksページにある各作品画像周りに、年代のキャプションは確実にあるが、今回のRAG画像は最新年順にとれていません。今あるRAG画像は全てゴミ箱に入れてた上で、年の抽出ルールを実装し、athrsのara-abduのみ再抽出してください。

以上です、まずは、上記を整理し、最初のタスク計画をプロンプト全文を出して示してください

運用ルールは前回と同じ。参照は 01/02/03/04 のみ。
次の作業：
TASK A-2R-FIX-2) ①-1追加修正: Athr / Sara Abdu を1ギャラリー1アーティストで「年の抽出ルール（作品画像）」実装・再検証（最新年順抽出）

MODEL_HINT: HIGH
理由: 抽出ロジック（作品年パース・降順ソート）に手を入れつつ、既存運用（fail-fast/汎用化/非ハードコード）を維持する必要があるため。

【必須参照（章ID明示）】
- 01（SSOT）
  - 4-0) ①〜④共通ルール
  - 4-4) Artist：作品画像（抽出ルール）
    - 【年の抽出ルール（作品画像）】
  - 5-4) Artist Works Images（4-4の成果物・命名/保存ルール）
  - 6-2) ドメイン専用ハードコード増殖の禁止
  - 6-3) 品質ライン（試作10ギャラリーの運用）
  - 10) 仕様変更ルール（事故防止）
  - SSOT整合ゲート
- 02（DERIVED）
  - CARD_ID: 10_NO_HERO_IMAGES
  - CARD_ID: 11_IMAGE_TARGET_LINE
  - CARD_ID: 14_CATEGORY_4_0_COMMON
  - CARD_ID: 16_SSOT_COMPLIANCE_GATE

【参照ファイル】
- run_phase1_network_preflight.py
- config/phase1_network_preflight_profile.json
- run_phase1_seed10_artist_image_collect.py
- run_phase1_seed10_artist_image_collect_report.py
- data/phase1_seed10/raw/artists_frieze_london_2025.jsonl
- data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【実施手順（この順で固定）】
1) preflight 2回（PASS必須）
python run_phase1_network_preflight.py
python run_phase1_network_preflight.py

2) 既存 Sara Abdu 画像を全退避（削除ではなく _trash へ移動）
- 対象:
  - data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*
- 退避先:
  - _trash/task_a2r_fix2_sara_abdu_reset_<timestamp>/
- 退避後、対象フォルダ内の該当画像 0件を確認

3) 年抽出ルールの実装（汎用のみ）
- 4-4【年の抽出ルール（作品画像）】に合わせて、worksページの各作品近傍テキスト/alt/captionから年を抽出
- 抽出した年で作品候補を最新年順（降順）に並べる
- 年不明は末尾扱い（ただし候補から除外しない）
- ドメイン専用 if 文は禁止（Athr専用ハック禁止）

4) Sara Abdu 単独で再実測（1ギャラリー=1アーティスト）
python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json"

5) report生成
python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu_report.json"

6) guard互換確認
python run_compare_phase1_guard.py --target-year 2025

7) 必須ドキュメント更新
- docs/RAG_EXTRACTION_BREAKDOWN_JA.md（TASK A-2R-FIX-2 見出し）
  - fair/gallery
  - 対象人数
  - 成功人数
  - 取得件数（画像枚数）
  - 成功率%
  - 失敗理由上位（works関連ノート含む）
  - 失敗0件ギャラリー（該当なしでも明記）
  - 退避元/退避先/退避件数
  - 年抽出結果（上位5件の年配列）と降順性確認
- docs/03_STATE_SNAPSHOT_NEXT_TASKS.md
- docs/04_TASK_PROGRESS_LOG.md

【完了条件】
- preflight 2連続PASS
- 旧 Sara Abdu 画像が _trash へ退避され、対象フォルダに混在がない
- Sara Abdu の再抽出画像が最新年順（降順）で取得される
- summary/report で年抽出の根拠（候補年・並び順）が追跡できる
- 03/04/RAG 内訳メモが更新される

【報告フォーマット（短く固定）】
1) 変更ファイル一覧
2) 実行コマンド
3) 生成物パス
4) exit code
5) 次の最優先タスク（1つ）+ MODEL_HINT + 理由1行



