# 04_TASK_PROGRESS_LOG.md

最終更新: 2026-03-01 16:35 JST  
対象プロジェクト: ART_PULSE_EDITOR（Phase1 seed10 / Guard運用整備）  
位置づけ: 実装進捗ログ（01=SSOT、02=索引、03=現行運用タスクの補助ログ）

---

## 0. このファイルの役割

- このファイルは、実装の進み具合（TASKの完了/保留/次タスク）を時系列で追えるようにするためのログです。
- 正式仕様は **01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）** を最優先とします。
- 02_RAG_SPEC_DERIVED.md は索引（カード集）、03_STATE_SNAPSHOT_NEXT_TASKS.md は「今日やること」です。
- 本ファイルは、**新チャットへ引っ越すときに実装履歴の文脈を渡すための補助**として使います。

---

## 1. 重要な運用方針（固定）

- 01（SSOT）が唯一の正本。仕様変更はまず01を更新してから実装へ反映する。
- 02は索引（参照用）。衝突したら01が正。
- 03は実行順の管理（NEXT_TASKS / CHANGELOG）。
- 取得ループ内で LLM 加工（headline_ja 等）をしない。**Fetch と Enrichment は分離**（Post-fetch バッチ）。
- 完成機能を勝手に削除/無効化しない（削除・置換・挙動変更は合意制）。
- ドメイン専用ハードコードを増やさない（頻出ドメイン × 汎用ロジックのみ改善）。
- 共通化できる判定・抽出ロジックは共通モジュールへ統合し、個別スクリプトへの重複実装を増やさない（変更点1箇所の運用を固定）。
- 取れない分はログに残して前進する（失敗をログ化して割り切る）。
- `data/gallery_lists/skipped_galleries_registry.csv` の登録は、Artists/Exhibitions の画像・テキスト抽出すべてに共通適用する。
- R2保存/削除の guarded 自動同期は、Artists/Exhibitions の画像・テキスト・ベクターを含むRAG全体に共通適用する。
- タスク終了時の出力は「【タスク終了時に行うこと】」テンプレを固定し、03更新は必ず 02→01→03 の順で実施後に報告5項目を出力する。

---

## 2. 全体の進捗サマリ（現時点）

- 完了: **TASK 1 ～ TASK 104**
- 次の予定: **TASK 109（Artists/Exhibitions 共通テンプレ運用の実行ゲート）**
- 直近の重点:
  - TarutaniRAG 側で比較/guard の「型」を作成 → Phase1本体（Exhibitions/Artists）へ横展開
  - Phase1 guard 本体 / history 比較 / fixture / matrix / schema文書化 / category文脈まで整備
  - category profile を外部設定化し、設定ミス時の安全フォールバックも実装済み
  - 03本タスク107を「Artistsテキスト抽出（10ギャラリー）＋共通スキップ/共通R2同期確認」に軌道修正

---

## 3. 初期基盤（TASK1〜5 完了）

[x] 1) ギャラリーリストCSVを repo に配置してコミットする（完了）
- 置き場所：`data/gallery_lists/`
- ファイル：
  - `gallery_list_frieze_london.csv`（95件）
  - `gallery_list_liste.csv`（52件）
- 形式：CSV / ヘッダーなし / UTF-8 / 1行=1ギャラリー

[x] 2) 02_RAG_SPEC_DERIVED.md（カテゴリ別カード集）を生成して固定する（3本立ての土台）
- 01（SSOT）を読み、RAG抽出・保存に必要なルールを「カテゴリ別カード」で整理
- 02は参照しやすさのための索引。衝突したら必ず01が正
- Phase1で必要な範囲（4-0共通 / 4-1 Exhibitions Text）から開始

[x] 3) Phase 1 用の最小実行入口スクリプトを作る（seed10）
- 入口: `python run_phase1_seed10.py`
- seed10定義：
  - frieze = `gallery_list_frieze_london.csv` 先頭5件
  - liste  = `gallery_list_liste.csv` 先頭5件
- 目的：UIより先に「取得→保存」が通ることを確認

[x] 4) 4-1 Exhibitions Text だけで「取得→保存→再実行でスキップ」を成立させる
- まずは 4-1 Exhibitions Text のみで成立させる
- 成立条件：
  - 1回目：取得→保存→完走
  - 2回目：同じコマンドで自動スキップ（台帳が効く）

[x] 5) 台帳（visited_pages / failed_fetches など）を保存し、失敗をログ化して割り切れる状態にする
- 目的：取れない分はログに残して前進
- 成立条件：失敗URLが一覧で追える / 再実行で同じ失敗を無限に繰り返さない

---

## 4. Phase1 seed10 安定化 + TarutaniRAG導線（TASK6〜16）

### 4.1 Phase1 seed10 / Fetch-Enrichment分離

[x] 6) （余力があれば）Enrichment（見出し/かな等）を「事後バッチ」で回す導線を作る
- FetchとEnrichmentは分離（取得ループ内で逐次実行しない）
- UIはPhase2でOK。まずはバッチ/CLIで成立
- 以後の運用ルールとして固定

### 4.2 Tarutani_Text（機能⑤向け）導線の実装

[x] 7) Tarutani_Text 取り込み（条件付き：忘れ防止ゲート）
- 着手条件：
  - Phase1 seed10 が2回連続で完走
  - 例外終了なし（exit code 0）
  - `failed_fetches` が残るのはOK（ログ化されていればOK）
- 目的：機能⑤用の文章RAG（作品画像は扱わない）
- 運用ルール：着手前に「TarutaniRAGの配置場所/形式」をユーザーへ確認

[x] 8) Tarutani_Text の Post-fetch Enrichment 入口を作る
- 目的：`tarutani_text.jsonl` に対して `headline_ja` 付与を事後バッチで回す入口
- 制約：取り込みループ内で LLM を呼ばない
- 成立条件：
  - `python run_enrichment_tarutani_text.py`（例）が実行可能
  - requests/summary が出力できる

[x] 9) Tarutani_Text の `headline_ja` を事後バッチで実生成し、jsonlへ反映する
- 目的：TASK8の requests を使って `headline_ja` を生成し更新
- 制約：fetch ループでは実行しない
- 成立条件：
  - 生成結果の保存
  - `tarutani_text.jsonl` の `headline_ja` が一部以上更新
  - 更新件数/未更新件数の summary 保存
- 実行メモ：Tarutani_data のR2同期（source/derived/logs）導線の下準備にも接続

[x] 9.5) TarutaniRAG向けPDF抽出を実装し、既存PDFをバックフィルする
- 目的：Tarutani_Text に限り、PDF本文を抽出して `text` を埋める
- 制約：TarutaniRAGのみ対象（他カテゴリPDF処理は変えない）
- 成立条件：
  - `text` 空件数の減少
  - 抽出失敗は `text=""` のまま + `extract_status` 理由保存
  - 再Enrichmentで更新件数 summary を確認
- 実行メモ：backfill / 再Enrichment とも更新完了確認済み

[x] 10) Tarutani_Text の Embedding / Index 入口を作る
- 目的：`headline_ja` 付与済み `tarutani_text.jsonl` をベクトル化 + 検索用index生成
- 制約：fetchループに組み込まない（Post-fetch バッチ）
- 成立条件：
  - `python run_vectorize_tarutani_text.py`（例）が実行可能
  - embedding入力件数 / skip件数 / 生成物パスの summary 保存
  - index + meta の生成
- 実行メモ：`chunk_size=1000`, `overlap=200`, `embedding_input_count=76`

[x] X) SSOT追記：埋め込み入力メタ3項目（`text_len` / `embed_input_len` / `is_truncated`）の明文化と実装反映
- 目的：取りこぼし分析のための埋め込みメタをSSOTと実装で統一
- 01の5-9へ追記済み
- `run_vectorize_tarutani_text.py` の meta 出力へ3項目を追加済み
- 76件すべてで確認済み

[x] X-2) ストレージ方針をSSOTで明文化し、Tarutani派生データ/ログのR2バックアップ導線を追加
- 目的：共通ストレージ方針の運用ぶれ防止
- 01の5-5/5-7/5-8追記
- `run_tarutani_r2_sync.py` の scope を `source/derived/logs/all` へ拡張
- 実行メモ：冪等（初回 upload / 再実行 skipped）確認済み

[x] X-3) Exhibition / Artist 章へ保存方針の最小追記（SSOT明確化）
- 目的：Exhibition/Artist章でも共通方針（5-7/5-8）参照と保存分類を明確化
- 01の5-1/5-3へ最小追記
- 02の該当カード（CARD 04/05/15）を01準拠で更新
- R2キー分類・manifest最小項目を統一方針で整理

### 4.3 TarutaniRAG 検索〜回答（機能⑤）CLIの検証導線

[x] 11) Tarutani_Text の検索スモークCLIを作る（chunk index検証）
- `run_search_tarutani_text.py --query "..."` で top-k 検索確認
- `source_path / chunk_index / score` を出力
- 検索summary（入力クエリ、k、出力先）保存
- 実行メモ：検索優先度プロファイル（`config/tarutani_text_search_profile.json`）も導入

[x] 12) Tarutani_Text 検索結果を機能⑤向けコンテキストJSONに整形する
- `run_build_tarutani_context.py --query "..."` を実装
- `source_path / chunk_index / score / excerpt` を含む context JSON 生成
- 03のCHANGELOG反映

[x] 13) 機能⑤向け回答スモークCLIを作る（Tarutani context利用）
- `run_answer_tarutani_advisor.py --question "..." --query "..."` を実装
- 回答本文 + 根拠（`source_path / chunk_index / score / excerpt`）保存
- Tarutani_Text は検索結果一覧に混ぜず、根拠セクション専用で扱う
- 実行メモ：数値競合（700/180）の優先規則も調整済み

[x] 14) 機能⑤回答CLIに再現モード（context固定入力）を追加
- `--context-path` 指定で既存 context JSON を使って再生成
- `query経由（再検索）` と `context固定入力` の両モードを summary で識別
- 検証/比較の再現性向上

[x] 15) 機能⑤回答の比較レポートCLIを作る（query再生成 vs context固定）
- `run_compare_tarutani_answers.py` を実装
- 回答本文長・根拠件数・主要数値（例: 700/180）の差分サマリ保存
- 再現性確認を短時間で回せる導線を作成

[x] 16) 機能⑤回答に差分ガードを追加する（数値競合アラート）
- 比較結果を使い、主要数値差分をガード
- `--fail-on-mismatch` で差分検知時に非0終了
- 差分なしは exit 0
- 実行メモ：
  - 最新context指定: `guard_passed=true`（exit 0）
  - 旧context指定: `mismatch_fields=['contains_700','contains_180']`（exit 2）

---

## 5. Phase1本体へ復帰（Tarutaniの比較/guardの“型”を横展開）TASK17〜18

[x] 17) Phase1本体へ復帰：Tarutaniで作った比較ガードの“型”をExhibitions/Artistへ横展開する準備
- 目的：
  - Tarutani側の「再現モード・比較・guard」の実績を、Phase1本体へ転用するための共通見張り項目を整理
  - Tarutani側の追加深掘りではなく、本体優先へ戻す
- 明文化した共通ガード項目（例）：
  - 必須キー存在
  - 内部整合
  - summary↔ledger整合
  - manifest/台帳整合
  - failed_fetches を「存在しただけで失敗」としない前進運用チェック
- TASK18（実装）へ接続

[x] 18) Exhibitions/Artists向け比較CLI + guard最小版を実装する
- `run_compare_phase1_guard.py --target-year 2025`
- G1〜G4（共通ガード項目）をCLI化
- `--fail-on-mismatch` で非0終了
- summary JSON保存
- 実行メモ：
  - 2025で `guard_passed=true` / `mismatches=0` / exit 0
  - 2024で不一致確認（`mismatches=7` / exit 2）

---

## 6. Phase1 guard の回帰比較・CI運用化（TASK19〜20）

[x] 19) Phase1 guardの回帰比較CLIを追加する（前回runとの比較）
- `run_compare_phase1_guard_history.py`
- 差分対象：
  - `records_saved_total`
  - `skipped_total`
  - `failed_fetches_total_ledger`
  - `visited_pages_total_ledger`
  - `mismatch_fields`
- `--fail-on-regression` 指定時のみ回帰で非0終了
- 比較前提の互換性チェック（`target_year` / 生成元CLI / `guard_schema_version` 任意）も実装
- 終了コード：
  - 0 = 差分なし/回帰なし
  - 2 = 回帰あり
  - 3 = 比較不成立（互換性NG）

[x] 20) Phase1 guard比較の運用化（baseline自動解決 + CI向け終了コード整理）
- baseline未指定時の auto 解決を実装
  - `current` 除外
  - `target_year` 一致
  - 生成元CLI一致
  - 過去summary優先 / `guard_passed=true` / schema一致 を優先
- `--strict-compatibility` を追加
  - 比較不成立を exit 3 で明示
- summaryに運用メタを追加：
  - `baseline_resolution_mode`
  - `baseline_candidates_checked`
  - `baseline_selected_reason`
  - `strict_compatibility`
  - `exit_code_meaning`
- CI向けの終了コード運用（0/2/3）を固定

---

## 7. seed10固定依存の棚卸しと汎化（TASK21〜24）

[x] 21) Phase1 guardをseed10以外へ拡張する準備（入力パス/年/カテゴリの汎化点整理）
- seed10固定箇所の棚卸しを実施（A〜E）
  - A) ファイル名固定
  - B) ディレクトリ固定（`data/phase1_seed10/logs`）
  - C) `target_year` 固定
  - D) カテゴリ固定（Exhibitions前提）
  - E) baseline探索の命名依存
- 汎化方針を明文化：
  - 既定値は現行seed10を維持
  - 新引数は追加のみ
  - summaryは項目追加で後方互換
- TASK22/23/カテゴリ対応へ接続

[x] 22) Phase1 guard本体のパス/年汎化を実装する（seed10互換維持）
- `run_compare_phase1_guard.py` に `--logs-dir` 追加
- 未指定時は従来どおり `data/phase1_seed10/logs`
- summaryに `category`（既定 `exhibitions_text`）と `logs_dir` を保存
- 既存コマンド互換を維持

[x] 23) Phase1 guard history比較のパス/探索汎化を実装する（seed10互換維持）
- `--baseline-search-dir` 未指定時に `--current-summary` 親ディレクトリを既定探索先に
- `--summary-glob` を追加（既定は従来互換）
- summaryに保存：
  - `baseline_auto_search_dir`
  - `baseline_candidates_checked`
  - `baseline_resolution_mode`
  - `summary_glob_effective`
- manual baseline 指定時の優先動作も明確化

[x] 24) Phase1 guard CLIの共通関数化（path解決/summary保存）を最小実装する
- `phase1_guard_common.py` を追加
- 共通化したもの（最小）：
  - `resolve_logs_dir`
  - `paths_equal`
  - `write_summary_json`
  - `utc_now_iso`
  - `utc_timestamp_compact`
  - `EXIT_CODE_MEANING`
- 判定ロジックはCLI側に残して挙動変更を避ける
- 既存の exit code 規約（0/2/3）を維持

---

## 8. fixture / matrix / 文書化（再現性と安全性の整備）TASK25〜30

[x] 25) Phase1 guard系CLIの共通fixture/テストデータ整理（回帰/非互換の再現性向上）
- `tests/fixtures/phase1_guard/{pass,regression,incompatible}` を整備
- `fixture_manifest.json` に case定義を集約
- `README.md` と `run_guard_fixture_matrix.sh` を追加
- 3ケース（pass/regression/incompatible）の再現手順を固定化

[x] 26) Phase1 guard本体のsummary/ledger見張り項目を最小強化する（安全側）
- 追加見張り項目：
  - `GX_SKIP_BREAKDOWN_SUM_MATCH`
  - `GX_FAILED_REASON_COUNTS_SUM_MATCH`
  - `GX_RECORDS_RELATIONS_MATCH`
- 後方互換方針：
  - キー不足は mismatch にせず `missing_keys` / `skipped_checks` に記録
- summary拡張：
  - `additional_guard_checks`
  - `additional_guard_check_results`
  - `missing_keys`
  - `skipped_checks`
- 既存判定ロジックは変更しない（追加のみ）

[x] 27) Phase1 guard history比較の追加見張り項目差分を見える化する（安全側）
- history summary に追加：
  - `additional_guard_checks_diff`
  - `additional_guard_checks_changed_fields`
  - `additional_guard_check_transitions`
  - `additional_guard_checks_comparison_mode`
  - `additional_guard_checks_missing_in`
- 旧summary（追加項目なし）との比較でも、比較不成立にせず後方互換で継続

[x] 28) guard本体/history比較のsummary schemaを軽く文書化して運用読み方を固定化する
- `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md` を追加
- 内容：
  - guard本体 summary の主要キー一覧
  - history比較 summary の主要キー一覧
  - exit code（0/2/3）の意味
  - fixture再現手順
  - TASK26/27の追加項目の読み方
  - 旧summaryとの後方互換方針

[x] 29) guard fixture matrix 実行を1コマンド化して手元/CIの入口を揃える（安全側）
- `run_phase1_guard_fixture_matrix.py` を追加
- `fixture_manifest.json` 駆動で pass/regression/incompatible 一括実行
- wrapper 自身の終了コード：
  - 0 = matrix pass
  - 1 = matrix fail
- 内側CLIの終了コード（0/2/3）は期待値として検証
- `--fail-fast` による早期停止も確認

[x] 30) guard schema version の安定付与/文書化を整えて互換判定を固定化する（安全側）
- `guard_schema_version` を共通定数化（`phase1_guard_common.py`）
- history summary に schema比較文脈を追加：
  - `current_guard_schema_version`
  - `baseline_guard_schema_version`
  - `guard_schema_version_comparison_mode`
  - `guard_schema_version_compatible`
  - `guard_schema_version_policy`
- 互換判定ルール固定：
  - both_present一致 → 互換OK
  - both_present不一致 → schema互換NG
  - current_only / baseline_only / both_missing → 後方互換（warning）
- strict時は schema不一致を incompatible（exit 3）へ昇格
- 既存の回帰判定ロジック・終了コード規約は維持

---

## 9. category 対応（Exhibitions/Artists 文脈の土台整備）TASK31〜38

[x] 31) `--category` の最小実体化：カテゴリ別必須ファイル集合の入口を追加する（安全側）
- `phase1_guard_common.py` に category profile 定義を追加
  - `exhibitions_text` = active
  - `artists_text` = reserved_minimal
- `run_compare_phase1_guard.py` にカテゴリ入口を追加
- summary追加：
  - `category_required_files_profile`
  - `required_input_files_effective`
  - `category_support_mode`
  - `category_warnings`
- 未対応カテゴリは fallback warning で継続（クラッシュさせない）

[x] 32) history比較に category 文脈を追加し、カテゴリ互換情報をsummary化する（安全側）
- history summary に追加：
  - `current_category`
  - `baseline_category`
  - `category_comparison_mode`
  - `category_effective_for_comparison`
  - `category_compatible`
  - `category_compatibility_policy`
  - `category_warnings`
- category互換ルール（可視化優先）：
  - both_present一致 → 互換OK
  - both_present不一致 → `category_compatible=false`
  - current_only / baseline_only / both_missing → 後方互換 warning
- strict時は category不一致を incompatible（exit 3）へ昇格

[x] 33) category mismatch の固定再現fixtureを追加し、history比較の運用再現性を固める（安全側）
- fixture追加：
  - `tests/fixtures/phase1_guard/category_mismatch/...`
- manifest に2ケース追加：
  - `category_mismatch_non_strict`（expected 0）
  - `category_mismatch_strict`（expected 3）
- README更新：
  - category mismatch の確認キー
  - non-strict/strict の期待exit code
- matrixで5ケース通過を確認

[x] 34) artists_text の最小guard運用を reserved_minimal から一段進める（必須集合の具体化）
- `artists_text` 向け category profile を具体化（activation条件付き）
- `run_compare_phase1_guard.py` に追加：
  - `required_summary_keys_effective`
  - `category_profile_version`（v1.1）
  - `category_support_mode_configured`
  - `category_activation_conditions`
  - `category_data_presence`（`artists_*_<year>.jsonl` 探索）
- support_mode判断：
  - artistsデータ検出時のみ `provisional_minimal`
  - 未検出時は `reserved_minimal` 維持 + warning
- `exhibitions_text` の既定挙動は維持

[x] 35) artists_text 用の最小fixture（pass/欠落warning）を追加して再現性を固定する（安全側）
- guard本体向け fixture 追加：
  - `artists_reserved_warning`
  - `artists_provisional_pass`
- `category_fixture_manifest.json` を追加
- `run_phase1_guard_category_fixture_matrix.py` を追加
  - wrapper exit: `0=matrix pass / 1=matrix fail`
  - `summary_checks_passed` / `summary_check_failures` を保持
- 既存history matrix（5ケース）に影響なし

[x] 36) artists_text 用の history比較fixture（category同一/不一致）を追加し、history再現性を固定する
- fixture追加：
  - `tests/fixtures/phase1_guard/artists_history/...`
- `fixture_manifest.json` に3ケース追加：
  - `artists_history_compatible`（expected 0）
  - `artists_vs_exhibitions_category_mismatch_non_strict`（expected 0）
  - `artists_vs_exhibitions_category_mismatch_strict`（expected 3）
- `run_phase1_guard_fixture_matrix.py` を最小拡張し、`expected_summary_checks` の機械検証を追加
- docs/README へ artists history fixture の確認手順を追記

[x] 37) category profile（必須集合/activation条件）の設定ファイル化準備を行い、コード直書きを減らす（土台整備）
- 追加設定ファイル：
  - `config/phase1_guard_category_profiles.json`
  - `exhibitions_text` / `artists_text` を現行内蔵profileと同値で定義
- `phase1_guard_common.py` に外部設定読み込み入口を追加：
  - `DEFAULT_CATEGORY_PROFILE_CONFIG_PATH`
  - `DEFAULT_CATEGORY_PROFILES`（内蔵fallback）
  - `load_category_profiles(...)`
  - `get_effective_category_profiles(...)`
- `run_compare_phase1_guard.py` に `--category-profile-config` を追加
- summaryに config 文脈を追加：
  - `category_profile_source`
  - `category_profile_config_path`
  - `category_profile_config_loaded`
  - `category_profile_config_error`
  - `category_profile_config_version_effective`
- 安全フォールバック（config不在/壊れ/不正）でも落とさず builtin で継続

[x] 38) category profile 設定ファイルのスキーマ検証を最小追加し、設定ミス検知を安定化する（安全側）
- `phase1_guard_common.py` に `validate_category_profiles_config(config_obj)` を追加
- 最小スキーマ検証内容：
  - root dict
  - `categories` dict
  - 必須カテゴリ（`exhibitions_text` / `artists_text`）
  - 各category profileの最低限キーと型
- error code体系を統一：
  - `config_missing:*`
  - `config_json_decode_error:*`
  - `config_schema_error:*`
- `run_compare_phase1_guard.py` は判定ロジック不変
- summaryへ詳細メタを追加：
  - `category_profile_config_error_detail`
- fallback確認（missing / bad json / bad schema missing / bad schema type）を実施
- fixture matrix / category matrix とも継続OK

---

## 10. 現在の次タスク（TASK105）

[x] 99) artists回答QA retry-run daily chain recovery chain report rollup起点retry-run summary の軽量レポートCLIを追加し、failed/recovered run を `--latest` で即確認できるようにする（本体前進）
- 目的：
  - TASK98で生成される `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を短く集約し、失敗runと参照先daily summaryを即確認できる導線を追加する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 既存retry-run本体ロジックは変更せず、report CLI追加のみに限定する
- 成立条件：
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "..."`（例）が実行できる
  - `--latest` で最新 `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を自動解決できる
  - report JSONに `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`（同等）を保存できる

[x] 100) Phase1 seed10 の artists画像収集（実測）CLIを追加し、5枚/人・70%超えの達成状況を summary で可視化する（本体前進）
- 目的：
  - seed10（artists対象）で画像収集を実行し、現状の取得率（目標: 1人あたり5枚 / 取得率70%超）を実測で把握する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 既存Exhibitions/Tarutani/guard/history/lint/matrixの既存処理を壊さない
  - ドメイン専用ハードコードを増やさない
- 成立条件：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` が実行できる
  - summary JSONに `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `failed_cases` を保存できる

[x] 101) artists画像収集実測summaryの軽量レポートCLIを追加し、5枚達成率/失敗理由上位/ドメイン別失敗を1コマンドで確認できるようにする（本体前進）
- 目的：
  - TASK100のsummaryを短く集約し、改善優先順位（どこで失敗しているか）を日次で即判断できるようにする
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 画像収集本体ロジックは変更せず、report CLI追加のみに限定する
- 成立条件：
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "..."`（例）が実行できる
  - `--latest` で最新 `phase1_seed10_artist_image_collect_summary_*.json` を自動解決できる
  - report JSONに `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `top_failed_reasons` / `top_failed_domains`（同等）を保存できる

[x] 102) artists画像収集実測reportのrollup CLIを追加し、直近N回の達成率推移と失敗理由変化を1コマンドで抽出できるようにする（本体前進）
- 目的：
  - TASK101のreportを複数回集約し、改善施策の効き目（達成率/失敗要因変化）を時系列で確認できるようにする
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 画像収集本体・report本体ロジックは変更せず、rollup CLI追加のみに限定する
- 成立条件：
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20`（例）が実行できる
  - rollup JSONに `total_reports` / `threshold_passed_rate` / `success_rate_trend` / `top_failed_reasons_trend`（同等）を保存できる

[x] 103) artists画像収集実測rollupから優先再収集manifestを生成し、失敗理由/ドメイン上位への再試行入口を短縮する（本体前進）
- 目的：
  - TASK102のrollupを起点に再収集対象を抽出し、改善ループの実行手順を短縮する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 画像収集本体/報告/rollupロジックは変更せず、manifest生成CLI追加のみに限定する
- 成立条件：
  - `python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest`（例）が実行できる
  - manifestに `source_rollup_path` / `cases[]`（`artist_id/source_url/reason/domain`）を保存できる

[x] 104) artists画像収集retry manifestをワンショット実行するCLIを追加し、再収集導線を1コマンド化する（本体前進）
- 目的：
  - TASK103で作成したretry manifestを直接実行し、再収集手順を短縮する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 画像収集本体ロジックは変更せず、実行ラッパー追加のみに限定する
- 成立条件：
  - `python run_phase1_seed10_artist_image_collect_retry_run.py --latest`（例）が実行できる
  - summaryに `retry_manifest_path` / `executed_cases` / `wrapper_exit_code`（同等）を保存できる

[x] 105) ブロッカー解消：DNS/外向き通信回復後に artists 画像収集を再実測し、改善ループを再開する（本体前進）
- 目的：
  - DNS/外向き通信の回復状態を確認し、artists画像収集の再実測（5枚目標）を再実行して現状を把握する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 既存画像収集本体ロジックは原則変更しない（今回は再実測中心）
- 成立条件：
  - `curl` / `socket` で通信状態を確認する
  - 画像収集summary/report/rollup/guardを再実行し、失敗理由を次アクション可能な粒度で残す

[x] 106) 環境ブロッカー継続対応：DNS/外向き通信回復後の artists画像収集再実測を再開し、5枚達成率の改善ループへ戻す（本体前進）
- 目的：
  - DNS/外向き通信回復を確認したうえで、artists画像収集を再実測して改善ループを再開する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 既存画像収集本体ロジックは原則変更しない（再実測中心）
- 現状：
  - 2026-02-26 12:44 JST 時点で DNS 回復確認（`curl`/`socket` とも成功）
  - 再実測で `network_dns_probe_ok=true`、`artists_with_ge_target_images=66/81`、`success_rate_ge_target=0.814815` を確認
[ ] 107) artists画像収集report rollupの最新判定を補正し、最新成功run（TASK106）を正しく推移集計へ反映する（本体前進）

---

## 11. 補足メモ（引っ越し時に重要）

### 11.1 新チャットへ渡すべきファイル（推奨）
- 01_PROJECT_SPEC_CURRENT_FULL.docx（SSOT）
- 02_RAG_SPEC_DERIVED.md（索引）
- 03_STATE_SNAPSHOT_NEXT_TASKS.md（現行タスク）
- 04_TASK_PROGRESS_LOG.md（本ファイル）

### 11.2 なくてもよいもの（通常）
- `debug_bundle_seed10*.tgz`
- `run_log_seed10.txt`
- DNS切り分け時の一時ログ
- 古い一時デバッグファイル（必要時のみ再提示）

### 11.3 重要な実装上の状態（認識合わせ）
- `saved=0` の問題は、**「取得ゼロ」ではなく既存64件がすでに raw にあるため**と判別できる表示に改善済み
- 台帳保存形式は dict 寄せ（ロード互換あり）
- TarutaniRAG は比較/guard の型づくりに大きく貢献済みだが、今後は **Phase1本体優先**（Tarutani側は保守モード）
- guard系CLIは以下の運用が成立済み：
  - 単発guard（本体）
  - history比較（回帰検知）
  - fixture/matrix（再現性）
  - schema version運用
  - category文脈（Exhibitions/Artists）
  - category profile 外部設定 + 安全フォールバック + スキーマ検証

---

## 12. 次の実装に入るときの一言（運用テンプレ）

- 本体ロジックを変える前に、まず 01/02/03 の整合を確認
- 取得ループにLLM処理を入れない
- 既存の終了コード規約（0/2/3）を壊さない
- 追加は「可視化/後方互換優先」で、小さく進める
- 変更後は fixture / matrix で再現性を確認してから前進

---

## 13. TASK43 実行ログ（統合matrix入口）

[x] 43) guard検証（history/category/lint）の統合matrix入口を追加し、手元/CIの実行導線を一本化する（安全側）
- 追加ファイル：
  - `run_phase1_guard_all_matrices.py`
- 実装内容（最小差分）：
  - 実行順 `lint -> category -> history` を固定し、3系統matrix wrapperを順次実行
  - fail-fastは採用せず、1件失敗しても残りを実行して総合summaryに残す
  - 統合summary（`phase1_guard_all_matrices_*.json`）へ `all_passed / wrapper_exit_code / execution_order / matrices[] / warnings` を保存
  - 統合wrapper終了コードを `0=all_pass / 1=any_fail` に固定
- 動作確認：
  - `python run_phase1_guard_all_matrices.py` → exit 0
  - `python run_phase1_guard_all_matrices.py --output-json "data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json" --pretty` → exit 0
  - `python run_phase1_guard_lint_fixture_matrix.py` → exit 0
  - `python run_phase1_guard_category_fixture_matrix.py` → exit 0
  - `python run_phase1_guard_fixture_matrix.py` → exit 0
- 統合summary保存先：
  - `data/phase1_seed10/logs/phase1_guard_all_matrices_20260224T075951Z.json`
  - `data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json`

## 14. TASK44 実行ログ（統合summaryレポートCLI）

[x] 44) 統合matrix summaryの軽量レポートCLIを追加し、CI失敗時の切り分けを高速化する（安全側）
- 追加ファイル：
  - `run_phase1_guard_all_matrices_report.py`
- 実装内容：
  - `--summary-path` / `--latest` の2経路で統合summaryを読取
  - `all_passed` / `wrapper_exit_code` / `execution_order` / `failed_matrices` / `child_summary_paths` を短く出力
  - 任意 `--output-json` でレポートJSONを保存
- 動作確認：
  - report CLI の指定コマンドで exit 0 を確認

## 15. TASK45 実行ログ（report fixture matrix）

[x] 45) report CLIの固定再現fixtureを追加し、summary欠落/破損時の挙動を1コマンドで検証できるようにする（安全側）
- 追加ファイル：
  - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
  - `tests/fixtures/phase1_guard/report/valid/phase1_guard_all_matrices_valid.json`
  - `tests/fixtures/phase1_guard/report/bad_json/phase1_guard_all_matrices_bad.json`
- 実装内容：
  - valid/missing/bad_json の3ケースを固定再現
  - matrix summary に expected/actual exit と summary checks を保存
- 動作確認：
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py` で exit 0

## 16. TASK46 実行ログ（report終了ポリシー拡張）

[x] 46) report CLIに `--fail-on-failed-matrix` を追加し、統合summaryが失敗状態なら非0終了を選べるようにした（安全側）
- 変更ファイル：
  - `run_phase1_guard_all_matrices_report.py`
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
  - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
  - `tests/fixtures/phase1_guard/report/failed/phase1_guard_all_matrices_failed.json`
- 実装内容：
  - 既定（フラグなし）：後方互換で summary読取成功時は exit 0
  - strict（`--fail-on-failed-matrix`）：`all_passed=false` を exit 1 へ昇格
  - 追加メタ：`fail_on_failed_matrix` / `exit_policy` / `exit_reason` / `report_exit_code`
  - report fixture matrix を 5ケースへ拡張（default/strict差を固定再現）
- 動作確認（要点）：
  - latest summary（all_passed=true）で strict指定しても exit 0
  - failed fixture summary（all_passed=false）で
    - フラグなし exit 0
    - strict指定 exit 1
  - `--summary-path /tmp/not_found.json --fail-on-failed-matrix` で exit 1
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py` で exit 0（5ケース）

## 17. TASK47 実行ログ（report fixture policy可視化）

[x] 47) report fixture matrixに終了ポリシー可視化キーを追加し、CIログ読解を固定化した（安全側）
- 変更ファイル：
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
  - `tests/fixtures/phase1_guard/report_fixture_manifest.json`
  - `tests/fixtures/phase1_guard/README.md`
  - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
- 実装内容：
  - `cases[]` に `policy_expected` / `policy_actual` / `policy_match` を追加
  - `policy_expected` は manifest未指定時 `fail_on_failed_matrix` から導出
  - strict/default の policy 差を固定可視化
- 動作確認：
  - report fixture matrix（5ケース）exit 0
  - failed summary の default: exit 0 / strict: exit 1

## 18. TASK48 実行ログ（policy_match guard反映）

[x] 48) report fixture matrixに `policy_match` guard を追加し、終了ポリシー齟齬をwrapper失敗として検知できるようにした（安全側）
- 変更ファイル：
  - `run_phase1_guard_all_matrices_report_fixture_matrix.py`
  - `tests/fixtures/phase1_guard/README.md`
  - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
- 実装内容：
  - `policy_check_mode=enforce_when_available` を追加
  - `policy_actual` 取得時は `policy_match=false` を fail 条件へ反映
  - `policy_actual` 未取得（missing/bad_json）は warning-only 維持
  - summary に `policy_guard_applied` / `policy_guard_passed` / `policy_guard_reason` を保存
- 動作確認：
  - 通常manifestは exit 0
  - `/tmp` 一時manifestで mismatch を作ると exit 1

## 19. TASK49 実行ログ（negative fixture常設化）

[x] 49) report fixture matrixにpolicy mismatch専用negative fixtureを追加し、policy_guard失敗経路を固定再現した（安全側）
- 追加ファイル：
  - `tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json`
- 変更ファイル：
  - `tests/fixtures/phase1_guard/README.md`
  - `docs/PHASE1_GUARD_SUMMARY_SCHEMA.md`
- 実装内容：
  - green manifest とは分離した negative manifest を常設
  - strictケースで `policy_expected` を意図的に不一致化し、`policy_match=false` を固定再現
  - report CLI本体ロジックは未変更
- 動作確認：
  - `python run_phase1_guard_all_matrices_report_fixture_matrix.py` → exit 0（green）
  - `python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path "tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json"` → exit 1（negative）
  - negative summary で `policy_match=false` / `policy_guard_passed=false` / `policy_guard_reason=policy_mismatch_enforced` を確認

## 20. TASK50 実行ログ（Phase1本体へ復帰：artists_text最小入口）

[x] 50) `run_phase1_seed10.py` に artists_text の最小取得入口を追加し、Exhibitionsと並走できる状態にした（安全側）
- 変更ファイル：
  - `run_phase1_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--include-artists-text` を追加（未指定時は従来どおり exhibitions_text のみ）
  - artists_text 専用の raw 出力と台帳を追加
    - `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl`
    - `data/phase1_seed10/raw/artists_liste_2025.jsonl`
    - `data/phase1_seed10/logs/visited_pages_artists_seed10_2025.json`
    - `data/phase1_seed10/logs/failed_fetches_artists_seed10_2025.json`
  - run summary に artists 系メタ（saved/skipped/failed/path）を追加
  - 取得ループ内LLM加工は追加せず（Post-fetch分離を維持）
- 動作確認：
  - `python run_phase1_seed10.py` → exit 0（既存互換）
  - `python run_phase1_seed10.py --include-artists-text` → exit 0（並走）
  - `python run_phase1_seed10.py --include-artists-text` → exit 0（再実行の台帳スキップ）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（guard側の既存互換）

## 21. TASK51 実行ログ（artists_url CSV拡張）

[x] 51) artists_text の入力ソースをCSV拡張で分離し、seed10取得率の改善余地を作った（本体前進・最小）
- 変更ファイル：
  - `run_phase1_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `GallerySeed` に `artists_url`（任意）を追加し、CSV 3列目を読込（2列CSVはそのまま有効）
  - `resolve_artists_list_url(...)` を追加し、artists入口URL解決を以下に固定
    - 優先: `artists_url`
    - fallback: `exhibitions_url`
  - artists取得ループの list fetch/台帳キーを `artists_list_url` 基準へ切替
  - run summary に artists入口URL解決メタを追加
    - `artists_list_source_counts`
    - `artists_list_source_counts_by_fair`
    - `artists_list_url_artists_url_used`
    - `artists_list_url_exhibitions_fallback_used`
- 動作確認：
  - `python run_phase1_seed10.py` → exit 0（既存互換）
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_phase1_seed10.py --include-artists-text` → exit 0（再実行）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
  - summary確認:
    - `artists_list_source_counts={'artists_url': 10}`
    - `artists_list_url_artists_url_used=10`
    - `artists_list_url_exhibitions_fallback_used=0`

## 22. TASK52 実行ログ（artists_url実データ拡充）

[x] 52) artists_text のCSV入力（artists_url列）を実データ拡充し、seed10で new_saved 発生を確認した（本体前進）
- 実施内容：
  - seed10対象10行（frieze/liste 各先頭5行）の `artists_url` 補完済みを確認
  - 通信回復後に artists 台帳を初期化して再取得を実行
- 実行結果：
  - 1回目: artists `saved=81 failed_new=1 skipped=0`
  - 2回目: artists `saved=0 failed_new=0 skipped=82`
  - summary退避: `data/phase1_seed10/logs/run_summary_seed10_2025_task53_first_pass.json`
    - `artists_records_saved_total=81`（`new_saved>0` 達成）
    - `artists_list_url_artists_url_used=10`
    - `artists_list_url_exhibitions_fallback_used=0`
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0

## 23. TASK53 実行ログ（通信ブロッカー解消）

[x] 53) ブロッカー解消：外向き通信回復後に artists_text の `new_saved>0` を再検証し、TASK52を完了
- 実施内容：
  - 通信確認（sandbox外）：
    - `curl -I https://example.com` → HTTP/2 200
    - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → 104.18.26.120
  - artists cooldown影響除外：
    - `failed_fetches_artists_seed10_2025.json` をバックアップ後に空dictへ初期化
- 再実行で `new_saved>0` を確認し、TASK52完了条件を満たした

## 24. TASK54 実行ログ（artists Post-fetch Enrichment入口）

[x] 54) artists_text のPost-fetch Enrichment入口をseed10本体へ追加した（本体前進・最小）
- 変更ファイル：
  - `run_phase1_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_phase1_seed10.py` に artists raw から未付与候補を抽出する Post-fetch 処理を追加
  - 生成物（上書き生成）：
    - `data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl`
  - run summary に artists enrichment メタを追加：
    - `artists_enrichment_mode`
    - `artists_enrichment_candidates_total`
    - `artists_enrichment_requests_created`
    - `artists_enrichment_requests_output_path`
    - `artists_enrichment_raw_records_total`
    - `artists_enrichment_raw_records_by_fair`
    - `artists_enrichment_counters`
    - `artists_enrichment_warnings`
  - 取得ループ内LLM加工は追加せず、Post-fetch分離を維持
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py` → exit 0（既存互換）
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_phase1_seed10.py --include-artists-text` → exit 0（再実行）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
  - summary確認：
    - `artists_enrichment_mode=post_fetch_requests_only`
    - `artists_enrichment_candidates_total=81`
    - `artists_enrichment_requests_created=81`
    - `artists_enrichment_requests_output_path=data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl`
    - `artists_enrichment_raw_records_total=81`

## 25. TASK55 実行ログ（artists Enrichment apply）

[x] 55) artists_text のEnrichment applyバッチを追加し、requestsから `headline_ja` をrawへ反映（本体前進）
- 変更ファイル：
  - `run_enrichment_artists_seed10_apply.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - artists requests（`data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl`）を読み込み、
    `artists_frieze_london_2025.jsonl` / `artists_liste_2025.jsonl` の `headline_ja` を更新する applyバッチを追加
  - apply結果の output/summary を `data/phase1_seed10/derived/` に保存
  - 接続失敗時に処理停止しないよう、Post-fetch範囲で見出しフォールバック生成を実装（取得ループ内LLM加工はなし）
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_enrichment_artists_seed10_apply.py` → exit 0（`updated=81`）
  - `python run_enrichment_artists_seed10_apply.py` → exit 0（`updated=0`、冪等）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/artists_enrichment_apply_output_2025_20260224T100342Z.jsonl`
  - `data/phase1_seed10/derived/artists_enrichment_apply_summary_2025_20260224T100342Z.json`
  - `data/phase1_seed10/derived/artists_enrichment_apply_output_2025_20260224T100355Z.jsonl`
  - `data/phase1_seed10/derived/artists_enrichment_apply_summary_2025_20260224T100355Z.json`

## 26. TASK56 実行ログ（artists Embedding/Index入口）

[x] 56) artists_text のEmbedding/Index入口を追加し、検索用生成物をseed10派生データとして保存（本体前進）
- 変更ファイル：
  - `run_vectorize_artists_seed10.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - artists raw（frieze/liste）を入力に、Post-fetchベクトル化CLIを追加
  - 生成物：
    - `data/phase1_seed10/derived/vector/artists_text_index_2025.npy`
    - `data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl`
    - `data/phase1_seed10/derived/vector/artists_text_vectorize_failed_2025.jsonl`
    - `data/phase1_seed10/derived/vector/artists_text_vectorize_summary_2025.json`
    - `data/phase1_seed10/derived/vector/artists_text_artifact_manifest_2025.json`
  - summaryに `input_total / embedded_total / skipped_total / output_paths` を保存
  - 既存guard/history/lintロジックには変更なし
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_enrichment_artists_seed10_apply.py` → exit 0
  - `python run_vectorize_artists_seed10.py` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実行結果：
  - `input_total=81`
  - `embedded_total=0`
  - `skipped_total=0`
  - `failed_total=81`（接続失敗）

## 27. TASK57 実行ログ（artists vectorize 接続ブロッカー解消）

[x] 57) ブロッカー解消：artists_text vectorize の外向き接続を回復し、`embedded_total>0` を再確認（本体前進）
- 変更ファイル：
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実施内容：
  - 外向き接続確認（sandbox外）：
    - `curl -I https://example.com` → HTTP/2 200
    - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → `104.18.27.120`
  - 指定フローを再実行：
    - `python run_phase1_seed10.py --include-artists-text` → exit 0
    - `python run_enrichment_artists_seed10_apply.py` → exit 0
    - `python run_vectorize_artists_seed10.py` → exit 0
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実行結果：
  - `artists_text_vectorize_summary_2025.json` で `input_total=81 / embedded_total=81 / skipped_total=0 / failed_total=0`
  - 生成物：
    - `data/phase1_seed10/derived/vector/artists_text_index_2025.npy`
    - `data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl`
    - `data/phase1_seed10/derived/vector/artists_text_vectorize_summary_2025.json`
    - `data/phase1_seed10/derived/vector/artists_text_artifact_manifest_2025.json`
- 補足：
  - `run_phase1_seed10.py --include-artists-text` は artists 側 `saved=0 skipped=10`（既存failed台帳のcooldownスキップ）だったが、既存raw 81件を入力に vectorize は正常完走し `embedded_total>0` を達成。

## 28. TASK58 実行ログ（artists 検索スモークCLI）

[x] 58) artists_text の検索スモークCLIを追加し、vector生成物から top-k を確認（本体前進）
- 変更ファイル：
  - `run_search_artists_seed10.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - artists vector生成物（index/meta）を入力に、`RETRIEVAL_QUERY` で top-k 検索を行うCLIを追加
  - 結果行に `source_url` / `record_id` / `score` / `vector_index` / `fair_slug` を保存
  - search summary に `query` / `k_requested` / `k_returned` / `output_paths` を保存
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_enrichment_artists_seed10_apply.py` → exit 0
  - `python run_vectorize_artists_seed10.py` → exit 0
  - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/vector/search/artists_text_search_results_20260224T102557Z.jsonl`
  - `data/phase1_seed10/derived/vector/search/artists_text_search_summary_20260224T102557Z.json`

## 29. TASK59 実行ログ（artists context JSON整形）

[x] 59) artists_text の検索結果を context JSON に整形し、Phase2接続入力を固定（本体前進）
- 変更ファイル：
  - `run_build_artists_context_seed10.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_search_artists_seed10.py` を内部実行し、top-k 検索結果を context JSON へ整形するCLIを追加
  - context item に `source_url` / `record_id` / `score` / `excerpt` / `headline_ja` / `vector_index` を保存
  - context summary に `query` / `k_requested` / `k_returned` / `input_paths` / `output_paths` を保存
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_enrichment_artists_seed10_apply.py` → exit 0
  - `python run_vectorize_artists_seed10.py` → exit 0
  - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0
  - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0（`k_returned=5`）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/context/artists_text_context_20260224T103230Z.json`
  - `data/phase1_seed10/derived/context/artists_text_context_summary_20260224T103230Z.json`

## 30. TASK60 実行ログ（artists 回答スモークCLI）

[x] 60) artists_text の回答スモークCLIを追加し、context JSON から根拠付き回答を出力（本体前進）
- 変更ファイル：
  - `run_answer_artists_seed10.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--question` / `--query` で context再生成→回答生成→根拠同梱保存までを行うCLIを追加
  - 出力JSONに `answer` / `answer_status` / `evidence(source_url, record_id, score, excerpt)` を保存
  - summaryに `question` / `query` / `context_path` / `output_paths` / `k_returned` を保存
  - LLM失敗時の最小フォールバック（`answer_status=fallback` + evidence保存）を追加
- 動作確認（2026-02-24）：
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_enrichment_artists_seed10_apply.py` → exit 0
  - `python run_vectorize_artists_seed10.py` → exit 0
  - `python run_search_artists_seed10.py --query "contemporary painting"` → exit 0
  - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
  - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0（`answer_status=ok`, `k_returned=5`）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_text_answer_20260224T104404Z.json`
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T104404Z.json`

## 31. TASK61 実行ログ（artists 回答比較CLI）

[x] 61) artists_text の回答比較CLIを追加し、query再生成 / context固定の差分可視化入口を作る（本体前進）
- 変更ファイル：
  - `run_compare_artists_answers.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_answer_artists_seed10.py` を query再生成モード / context固定モードで2回実行し、差分を1つのsummaryへ集約するCLIを追加
  - 比較summaryへ `answer_chars` / `evidence_count` / `mismatch_fields` / `differences` を保存
  - `--fail-on-mismatch` 指定時のみ mismatch で exit 2（未指定は exit 0）を実装
- 動作確認（2026-02-24）：
  - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
  - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
  - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T105015Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実行結果（比較summary）：
  - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T105153Z.json`
  - `mismatch_fields=['answer_chars','numeric_tokens']`
  - `query_rebuild.answer_chars=732` / `fixed_context.answer_chars=769`
  - `query_rebuild.evidence_count=5` / `fixed_context.evidence_count=5`

## 32. TASK62 実行ログ（artists 回答CLIの最小ガード）

[x] 62) artists_text 回答CLIの最小ガードを追加し、空回答/根拠欠落を非0終了で検知できるようにする（本体前進）
- 変更ファイル：
  - `run_answer_artists_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_answer_artists_seed10.py` に `--fail-on-invalid-output` を追加
  - 最小ガードを追加：
    - `answer` 非空
    - `evidence` 1件以上
    - 各evidenceの必須キー（`source_url` / `record_id` / `score` / `excerpt`）存在
  - answer JSON / summary JSON に `output_valid` / `invalid_reasons` / `fail_on_invalid_output` を保存
- 動作確認（2026-02-24）：
  - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 1（sandbox DNS）
  - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 1（sandbox DNS）
  - 外向き接続付きで再実行：
    - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
    - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0（`output_valid=true`）
    - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T110028Z.json"` → exit 0
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
  - 無効出力ケース確認（/tmpの一時invalid context）：
    - `python run_answer_artists_seed10.py --question "ガード動作確認" --context-path /tmp/artists_invalid_context_task62.json --fail-on-invalid-output` → exit 2
    - `invalid_reasons=['empty_evidence_value:0.source_url','empty_evidence_value:0.record_id','empty_evidence_value:0.excerpt']`
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T110049Z.json`（正常）
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T110214Z.json`（無効ケース）

## 33. TASK63 実行ログ（artists 回答比較の最小回帰ガード）

[x] 63) artists_text 回答比較CLIに最小回帰ガードを追加し、差分悪化時のみ非0終了にする（本体前進）
- 変更ファイル：
  - `run_compare_artists_answers.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_compare_artists_answers.py` に `--fail-on-regression` を追加（既定は後方互換で `False`）
  - 差分 (`mismatch_fields`) と回帰 (`regression_reasons`) を分離
  - 回帰条件（最小）：
    - `answer_status` 悪化（`ok < fallback < error`）
    - `output_valid` 悪化（`true -> false`）
    - `evidence_count` 減少
  - summaryへ `fail_on_regression` / `guard_passed` / `regression_detected` / `regression_reasons` / `regression_warnings` / `compare_exit_code` / `exit_reason` を追加
- 動作確認（2026-02-24）：
  - 通常系（外向き接続あり）：
    - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
    - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0
    - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T111221Z.json"` → exit 0
    - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T111221Z.json" --fail-on-regression` → exit 0（`guard_passed=true`）
  - 回帰系（意図的な無効context）：
    - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "/tmp/artists_invalid_context_task63.json" --fail-on-regression` → exit 2
    - `guard_passed=false`
    - `regression_reasons=['output_valid_regressed:true->false','evidence_count_decreased:5->1']`
  - 既存互換：
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111318Z.json`
  - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111347Z.json`
  - `data/phase1_seed10/derived/answer/artists_text_answer_compare_20260224T111430Z.json`

## 34. TASK64 実行ログ（artists 回答QA統合スモークCLI）

[x] 64) artists回答導線のQA統合スモークCLIを追加し、context生成→回答→比較を1コマンドで実行できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_smoke.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_smoke.py` を追加し、以下を順次実行する統合入口を実装
    - context build（`run_build_artists_context_seed10.py`）
    - answer generate（`run_answer_artists_seed10.py --fail-on-invalid-output`）
    - answer compare（`run_compare_artists_answers.py`、`--fail-on-regression` 任意）
  - QA summary に `all_passed` / `wrapper_exit_code` / `steps[].name|command|exit_code|output_paths` を保存
  - wrapper 終了コードを `0=all_passed / 1=any_step_failed` で固定
- 動作確認（2026-02-24）：
  - sandbox内実行（ネットワーク制約確認）：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 1
    - 要因：`context_build` が DNS失敗（`Temporary failure in name resolution`）
  - 外向き接続付きで再実行：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-regression` → exit 0
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T112201Z.json`（sandbox DNS失敗 run）
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T112405Z.json`（通常 run）
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T112518Z.json`（`--fail-on-regression` run）

## 35. TASK65 実行ログ（artists 根拠整形フォールバック最小強化）

[x] 65) artists回答の根拠整形を最小強化し、excerpt/headline欠落時フォールバックを安定化する（本体前進）
- 変更ファイル：
  - `run_answer_artists_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_answer_artists_seed10.py` に raw参照インデックス（record_id/source_url）を追加
  - evidence整形のフォールバックを追加
    - `excerpt` 欠落時：`headline_ja` → raw `text` 断片（260字）
    - `headline_ja` 欠落時：raw `headline_ja` → `excerpt` 先頭（80字）
  - summary / answer payload に以下メタを追加
    - `evidence_fallback_excerpt_count`
    - `evidence_fallback_headline_count`
    - `evidence_source_row_missing_count`
  - `--fail-on-invalid-output` の既存終了規約は維持
- 動作確認（2026-02-24）：
  - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 0
  - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 0
  - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T120544Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
  - 欠落再現（/tmp 一時context）：
    - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --context-path /tmp/artists_context_task65_missing_excerpt_headline.json --fail-on-invalid-output` → exit 0
    - `evidence_fallback_excerpt_count=2` / `evidence_fallback_headline_count=2` / `output_valid=true` を確認
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T120624Z.json`
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T120844Z.json`

## 36. TASK66 実行ログ（artists QA統合CLIのcontext固定再現モード）

[x] 66) artists回答QA統合CLIにcontext固定再現モードを追加し、日次runと再現runの入口を一本化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_smoke.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_smoke.py` に `--context-path` を追加し、`--query` と排他制御を実装
    - 両方指定 / 両方未指定は非0終了（exit 1）+ エラーsummary保存
  - 実行モードを追加
    - `qa_input_mode=query_rebuild`：context build -> answer -> compare（既存互換）
    - `qa_input_mode=fixed_context`：context build/compare を `skipped`、answerのみ実行
  - fixed_context + `--fail-on-regression` は warning-only で継続
    - `fail_on_regression_ignored_without_query`
  - summary拡張：
    - `qa_input_mode`
    - `context_path_effective`
    - `query_effective`
    - `steps[].status`（`ok/failed/skipped`）
    - `errors`（引数エラー時）
- 動作確認（2026-02-24）：
  - queryモード：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting"` → exit 0
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-regression` → exit 0
  - fixed_contextモード：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 0
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --fail-on-regression` → exit 0（warning-only）
  - 引数エラー：
    - `python run_artists_answer_qa_smoke.py --question "test" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 1
    - `python run_artists_answer_qa_smoke.py --question "test"` → exit 1
  - 既存互換：
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131612Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131713Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T131835Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132100Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132130Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T132137Z.json`

## 37. TASK67 実行ログ（artists QA統合CLIのbatch実行入口）

[x] 67) artists回答QA統合CLIに複数query一括実行モードを追加し、日次確認を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_smoke.py`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_smoke.py` に `--batch-manifest` を追加（`.json` / `.jsonl`）
  - batchケースごとに同CLIの単発モードをsubprocess実行し、既存ロジックを再利用
  - batch summary へ以下を保存
    - `total_cases` / `passed_cases` / `failed_cases`
    - `cases[].summary_path` / `cases[].exit_code`
    - `cases[].status` / `cases[].stdout_tail` / `cases[].stderr_tail`
  - 単発モード（`--query` / `--context-path`）の挙動は後方互換を維持
- 動作確認（2026-02-24）：
  - 要件コマンド（query再生成）：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_query_required.json"` → exit 1（DNS: `Temporary failure in name resolution`）
    - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_required.json"` → exit 1（同上）
  - 機能成立確認（fixed_context）：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_fixed_context.json"` → exit 0
    - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_fixed.json"` → exit 0（`total_cases=2`, `passed_cases=2`）
  - 既存互換：
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_query_required.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_required.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_fixed_context.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task67_batch_fixed.json`

## 38. TASK68 実行ログ（artists evidence重複統合 + 表示順安定化）

[x] 68) artists回答の根拠整形を最小強化し、重複source統合と表示順の安定化を行う（本体前進）
- 変更ファイル：
  - `run_answer_artists_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_answer_artists_seed10.py` の evidence 生成後に、安定ソートと重複統合を追加
    - 安定ソート：`score` 降順 + tie-break（`rank` / `source_url` / `record_id` / `vector_index`）
    - 重複統合：`source_url + record_id` 同一を1件に統合（先頭採用）
  - summary/payload に以下を追加
    - `evidence_dedup_removed_count`
    - `evidence_sorted`
  - `--fail-on-invalid-output` の既存終了規約は維持
- 動作確認（2026-02-24）：
  - 指定コマンド（query系）：
    - `python run_build_artists_context_seed10.py --query "contemporary painting"` → exit 1（DNS: `Temporary failure in name resolution`）
    - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --fail-on-invalid-output` → exit 1（同上）
    - `python run_compare_artists_answers.py --question "この検索結果から注目作家の傾向を教えて" --query "contemporary painting" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json"` → exit 1（query再生成側がDNS失敗）
  - 機能成立確認（fixed_context）：
    - `python run_answer_artists_seed10.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --fail-on-invalid-output` → exit 0
      - `evidence_sorted=true`
      - `evidence_dedup_removed_count=0`
    - 重複再現（/tmp一時context）
      - `python run_answer_artists_seed10.py --question "重複整形確認" --context-path /tmp/artists_context_task68_dedup.json --fail-on-invalid-output` → exit 0
      - `evidence_dedup_removed_count=1`
  - 既存互換：
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T134716Z.json`
  - `data/phase1_seed10/derived/answer/artists_text_answer_summary_20260224T134739Z.json`

## 39. TASK69 実行ログ（artists QA batch case単位回帰ガード適用）

[x] 69) artists回答QA統合CLIのbatch caseごとに回帰ガード適用を追加し、失敗検知をケース単位で固定化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_smoke.py`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - batch case summary を拡張
    - `fail_on_regression_effective`
    - `guard_passed`（compare summary取得時）
    - `compare_summary_path` / `compare_exit_code`
    - `regression_reasons`
    - `case_failure_kind`
  - manifest defaults 反映を明示
    - `fail_on_regression_default` は manifest の defaults を優先して保存
  - caseの失敗理由を分類して summary から追跡可能化
    - `regression_guard_failed` / `query_rebuild_failed` / `fixed_context_failed` / `invalid_case_config` / `none`
- 動作確認（2026-02-24）：
  - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"` → exit 1
    - DNS制約で queryケース2件とも失敗（`case_failure_kind=query_rebuild_failed`）
    - case2は manifest override で `fail_on_regression_effective=true` を確認
  - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task69_regression.json"` → exit 1
    - `fixed_context_pass` は exit 0
    - `query_rebuild_regression_check` は DNS制約で exit 1
    - case単位で pass/fail を切り分けて保存されることを確認
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T140420Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T140432Z.json`
  - `/tmp/artists_answer_qa_batch_manifest_task69_regression.json`

## 40. TASK70 実行ログ（artists QA batch結果の集約JSONL出力）

[x] 70) artists回答QA統合CLIのbatch実行結果を集約JSONL化し、日次確認対象を1ファイルで追えるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_smoke.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - batch実行時に `summary_path` と同じディレクトリへ `"{summary_stem}_cases.jsonl"` を出力
  - JSONL 1行1caseで以下を保存（最低限）
    - `case_id` / `question` / `query` / `context_path` / `exit_code` / `guard_passed` / `summary_path`
  - 追加の補助項目：
    - `qa_input_mode` / `fail_on_regression_effective` / `case_failure_kind` / `compare_exit_code` / `compare_summary_path` / `regression_reasons`
  - batch summary JSONに以下を追加：
    - `batch_cases_jsonl_path`
    - `batch_cases_jsonl_written`
    - `batch_cases_jsonl_count`
- 動作確認（2026-02-24）：
  - 単発後方互換（fixed_context）：
    - `python run_artists_answer_qa_smoke.py --question "この検索結果から注目作家の傾向を教えて" --context-path "data/phase1_seed10/derived/context/artists_text_context_20260224T131736Z.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_fixed_context.json"` → exit 0
    - 単発モードでは `*_cases.jsonl` 未生成を確認
  - batch green（fixed_context 2件）：
    - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed.json"` → exit 0
    - `batch_cases_jsonl_written=true`, `batch_cases_jsonl_count=2`
  - batch失敗混在（sample manifest）：
    - `python run_artists_answer_qa_smoke.py --batch-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_batch_manifest_sample.json"` → exit 1
    - DNS制約で queryケースが `query_rebuild_failed` だが、JSONL出力は維持
  - 既存互換：
    - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_fixed_context.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task70_batch_fixed_cases.jsonl`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T142921Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T142921Z_cases.jsonl`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T142932Z.json`

## 41. TASK71 実行ログ（artists QA batch JSONL軽量レポートCLI）

[x] 71) artists回答QA batch集約JSONLの軽量レポートCLIを追加し、失敗case一覧と子summary参照を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_batch_report.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_batch_report.py` を新規追加
    - `--cases-jsonl` で対象JSONLを明示読み込み
    - `--latest` で最新 `artists_answer_qa_smoke_summary_*_cases.jsonl` を自動解決
    - レポートへ `total_cases` / `failed_cases` / `failed_case_ids` / `summary_paths_to_check` を保存
    - 既定で `{cases_stem}_report.json` を出力
- 動作確認（2026-02-24）：
  - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed.json"` → exit 0
  - `python run_artists_answer_qa_batch_report.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases.jsonl"` → exit 0
  - `python run_artists_answer_qa_batch_report.py --latest` → exit 0
  - `python run_artists_answer_qa_batch_report.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_20260224T142921Z_cases.jsonl"` → exit 0（`failed_case_ids=['contemporary_painting','abstract_art']` を確認）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases.jsonl`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task71_batch_fixed_cases_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T143834Z.json`

## 42. TASK72 実行ログ（artists QA失敗case再実行manifest生成CLI）

[x] 72) artists回答QA batch集約JSONLから失敗case再実行manifestを生成するCLIを追加し、日次復旧導線を短縮する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_retry_manifest.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_retry_manifest.py` を新規追加
    - `--cases-jsonl` で対象JSONLを明示読み込み
    - `--latest` で最新 `artists_answer_qa_smoke_summary_*_cases.jsonl` を自動解決
    - 失敗case（`exit_code != 0`）のみ抽出し、再実行manifestを生成
    - case項目に `case_id/question/query/context_path/fail_on_regression` を保存
    - 失敗0件でも `cases=[]` と `notes=['no_failed_cases_found']` を保存し、exit 0で継続
- 動作確認（2026-02-24）：
  - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed.json"` → exit 0
  - `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases.jsonl"` → exit 0
  - `python run_artists_answer_qa_retry_manifest.py --latest` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases.jsonl`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task72_batch_fixed_cases_retry_manifest.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T144521Z.json`

## 43. TASK73 実行ログ（artists QA retry manifest ワンショット実行CLI）

[x] 73) artists回答QA retry manifest をそのまま実行するワンショットCLIを追加し、失敗case復旧を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_retry_run.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_retry_run.py` を追加
    - 入力モード：`--retry-manifest` / `--latest`（排他、両方指定/未指定は exit 1）
    - `--latest` で最新 `artists_answer_qa_smoke_summary_*_retry_manifest.json` を自動解決
    - `cases=[]` manifest は no-op 成功（exit 0、`executed_cases=0`）として処理
    - validケースは `run_artists_answer_qa_smoke.py --batch-manifest ...` を subprocess 再利用して実行（ロジック重複回避）
    - 親summaryへ `retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `child_batch_exit_code` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `invalid_case_count` / `invalid_case_ids` を保存
    - 親CLI exit code を `0=success(no-op含む)` / `1=failure` に正規化
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_smoke.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed.json"` → exit 0
  - `python run_artists_answer_qa_retry_manifest.py --cases-jsonl "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases.jsonl"` → exit 0
  - `python run_artists_answer_qa_retry_run.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases_retry_manifest.json"` → exit 0（no-op）
  - `python run_artists_answer_qa_retry_run.py --latest` → exit 0（no-op）
  - `python run_artists_answer_qa_retry_run.py --retry-manifest "/tmp/artists_answer_qa_retry_manifest_task73_invalid.json"` → exit 1（child batch fail）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases.jsonl`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_smoke_summary_task73_batch_fixed_cases_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162427Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162436Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162445Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T162445Z_child_batch_summary.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T162450Z.json`

## 44. TASK74 実行ログ（artists QA retry run summary 軽量レポートCLI）

[x] 74) artists回答QA retry run summary の軽量レポートCLIを追加し、failed/recovered を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_retry_run_report.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_retry_run_report.py` を追加
    - 入力モード：`--summary-path` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_retry_run_summary_*.json` から `_child_batch_summary` / `_report` を除外して本体summaryを解決
    - レポートへ `retry_manifest_path` / `retry_manifest_case_count` / `executed_cases` / `wrapper_exit_code` / `all_passed` / `child_batch_summary_path` / `child_batch_cases_jsonl_path` / `notes` を保存
    - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可）
    - exit code を `0=report_generated / 1=summary_not_found_or_invalid` で固定
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_retry_run.py --latest` → exit 0
  - `python run_artists_answer_qa_retry_run_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T163348Z.json"` → exit 0
  - `python run_artists_answer_qa_retry_run_report.py --latest` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T163348Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_summary_20260224T163348Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260224T163434Z.json`

## 45. TASK75 実行ログ（artists QA 日次復旧ワンショットCLI）

[x] 75) artists回答QAの日次復旧ワンショットCLIを追加し、batch実行→report→retry manifest→retry run→retry report を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery.py` を追加
    - 入力：`--batch-manifest`（必須）/ `--output-json`（任意）
    - 子CLIを順次再利用して実行：
      - `run_artists_answer_qa_smoke.py --batch-manifest ...`
      - `run_artists_answer_qa_batch_report.py --cases-jsonl ...`
      - `run_artists_answer_qa_retry_manifest.py --cases-jsonl ...`
      - `run_artists_answer_qa_retry_run.py --retry-manifest ...`
      - `run_artists_answer_qa_retry_run_report.py --summary-path ...`
    - daily summary へ `steps[].name/command/exit_code/status/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存
    - retry対象0件（`retry_run_mode=noop_empty_retry_manifest`）は no-op 成功として記録
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
  - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json" --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260224T164617Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest_batch_smoke_summary.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest_batch_smoke_summary_cases.jsonl`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest_retry_run_summary.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_latest_retry_run_report.json`

## 46. TASK76 実行ログ（artists QA daily recovery summary 軽量レポートCLI）

[x] 76) artists回答QA日次復旧ワンショットの軽量レポートCLIを追加し、daily summary から failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_report.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_report.py` を追加
    - 入力モード：`--summary-path` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_summary_*.json` から `_report.json` と child summary 系（`_batch_smoke_summary` / `_batch_report` / `_retry_manifest` / `_retry_run_summary` / `_retry_run_report`）を除外して本体summaryを解決
    - レポートへ `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes` / `report_exit_code` / `exit_reason` を保存
    - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可）
    - exit code を `0=report_generated / 1=summary_not_found_or_invalid` で固定
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
  - `python run_artists_answer_qa_daily_recovery_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z.json"` → exit 0
  - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T075527Z.json`

## 47. TASK77 実行ログ（artists QA daily recovery report rollup CLI）

[x] 77) artists回答QA日次復旧レポートのrollup CLIを追加し、failed step あり run を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_report_rollup.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_report_rollup.py` を追加
    - 入力：`--latest-n`（既定20）/ `--search-dir`（既定 `data/phase1_seed10/derived/answer`）/ `--glob` / `--output-json`
    - 対象は `artists_answer_qa_daily_recovery_summary_*_report.json` のみを集約し、child report（`_batch_report` / `_retry_run_report`）は除外
    - rollup JSON へ `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存
    - 既定出力は `artists_answer_qa_daily_recovery_report_rollup_<timestamp>.json`
    - exit code は `0=rollup_generated / 1=report_not_found_or_invalid`
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 0
  - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
  - 再実行確認（失敗混在ケース）：
    - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 1（`all_passed=false`）
    - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0（`failed_steps=['batch_smoke','retry_run']`）
    - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0（`failed_run_count=1`）
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T080328Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_summary_20260225T075505Z_report.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T080328Z.json`

## 48. TASK78 実行ログ（artists QA daily recovery report rollup -> retry manifest）

[x] 78) artists回答QA日次復旧レポートrollupから failed run 向け retry manifest を生成するCLIを追加し、要再対応runだけを即再実行できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py` を追加
    - 入力モード：`--rollup-json` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_report_rollup_*.json` から最新を自動解決
    - `failed_runs[]` を `cases[]` に変換し、`source_summary_path` / `failed_step_names` / `child_summary_paths_to_check` / `batch_manifest_path` を保存
    - top-level に `retry_manifest_path` / `rollup_failed_run_count` / `retry_case_count` / `notes` を保存
    - failed run 0件でも `cases=[]` manifest を生成し、exit 0 を維持
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery.py --batch-manifest "/tmp/artists_answer_qa_batch_manifest_task67_fixed.json"` → exit 1
  - `python run_artists_answer_qa_daily_recovery_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z.json"` → exit 0（failed run 0件）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T081259Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z_retry_manifest.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T081303Z.json`

## 49. TASK79 実行ログ（artists QA daily recovery retry manifest ワンショット実行CLI）

[x] 79) artists回答QA日次復旧retry manifest（rollup起点）をそのまま実行するワンショットCLIを追加し、failed run再実行を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を追加
    - 入力モード：`--retry-manifest` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json` の最新を解決
    - retry manifest `cases[]` を順次実行し、`run_artists_answer_qa_daily_recovery.py --batch-manifest ... --output-json ...` をsubprocess再利用
    - summaryへ `retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries` / `cases[]`（`case_id` / `exit_code` / `daily_summary_path`）を保存
    - 0件manifestは no-op成功（`executed_runs=0` / `retry_run_mode=noop_empty_retry_manifest`）で exit 0
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085050Z.json"` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1（`executed_runs=2`, `failed_runs=2`）
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085050Z_retry_manifest.json"` → exit 1（`executed_runs=2`, `failed_runs=2`）
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T080328Z_retry_manifest.json"` → exit 0（no-op）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085111Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085123Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085135Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T085123Z.json`

## 50. TASK80 実行ログ（artists QA daily recovery retry run summary 軽量レポートCLI）

[x] 80) artists回答QA日次復旧retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py` を追加
    - 入力モード：`--summary-path` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` から `_report.json` と `_failed_run_` を除外し、本体summaryのみ解決
    - レポートへ `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存
    - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可）
    - exit code は `0=report_generated / 1=summary_not_found_or_invalid`
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1（failed runあり）
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085951Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_report_rollup_20260225T085951Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T085952Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T085954Z.json`

## 51. TASK81 実行ログ（artists QA daily recovery retry run report rollup CLI）

[x] 81) artists回答QA日次復旧retry run reportのrollup CLIを追加し、failed/recovered runの推移を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py` を追加
    - 対象：`artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json`
    - 入力：`--latest-n`（既定20）/ `--search-dir`（既定 `data/phase1_seed10/derived/answer`）/ `--glob` / `--output-json`
    - rollup JSONへ `total_reports` / `failed_run_count` / `failed_runs[]` を保存
      - `failed_runs[]` は `summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check` を保持
    - fail判定は `failed_case_ids` / `failed_runs` / `all_passed` / `wrapper_exit_code` を組み合わせて評価
    - exit code は `0=rollup_generated / 1=reports_not_found_or_invalid`
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T091123Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T091123Z_report.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T091126Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T091126Z.json`

## 52. TASK82 実行ログ（retry run report rollup起点 retry manifest 生成CLI）

[x] 82) artists回答QA日次復旧retry run report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` を追加
    - 入力：`--rollup-json` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` から `*_retry_manifest.json` を除外して解決
    - rollupの `failed_runs[]` から対象summaryを読み、failed caseを抽出して retry manifest へ変換
    - 出力manifestへ `source_summary_path` / `source_summary_paths` / `failed_case_ids` / `retry_manifest_path` / `cases[]` を保存
    - `cases[].batch_manifest_path` を保持し、既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` で再利用可能化
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --rollup-json /tmp/artists_retry_run_report_rollup_empty_task82.json` → exit 0（failed_runs=0 / retry_cases=0）
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z_retry_manifest.json"` → exit 1
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T093039Z_retry_manifest.json`
  - `/tmp/artists_retry_run_report_rollup_empty_task82_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T093039Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T093046Z.json`

## 53. TASK83 実行ログ（retry run report rollup起点manifest ワンショット実行CLI）

[x] 83) artists回答QA日次復旧retry run report rollup起点manifestをそのまま実行するワンショットCLIを追加し、要再対応run再実行を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py` を追加
    - 既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を subprocess で再利用する薄い実行ラッパーとして実装
    - 入力：`--retry-manifest` / `--latest`（排他）
    - `--latest` 既定globを `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` に固定
    - `--output-json` は既存実行CLIへ透過委譲し、summaryキー（`retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`）は既存仕様を維持
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094043Z_retry_manifest.json"` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --retry-manifest "/tmp/artists_retry_run_report_rollup_empty_task82_retry_manifest.json"` → exit 0（no-op）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094043Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094043Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094051Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094111Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T094051Z.json`

## 54. TASK84 実行ログ（retry run summary軽量レポートCLI）

[x] 84) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py` を追加
    - 入力モード：`--summary-path` / `--latest`（排他）
    - `--latest` は `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` から `_report.json` と `_failed_run_` を除外して本体summaryのみ解決
    - レポートへ `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存
    - 既定出力は `<summary_stem>_report.json`（`--output-json` で上書き可）
    - exit code は `0=report_generated / 1=summary_not_found_or_invalid`
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py --latest-n 20` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest.py --latest` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094707Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094656Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T094656Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094707Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T094707Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T094725Z.json`

## 55. TASK85 実行ログ（retry run summary report rollup CLI）

[x] 85) artists回答QA日次復旧retry run summary report のrollup CLIを追加し、failed/recovered run推移を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py` を追加
    - 入力：`--latest-n` / `--search-dir` / `--glob` / `--output-json`
    - 出力top-levelに `schema_name` / `schema_version` / `artifact_kind` / `generated_at` / `generated_by` を追加
    - 最小共通化として `is_target_report(...)` / `list_candidate_reports(...)` を新規実装し、対象探索の include/exclude/sort を1か所へ集約
    - `failed_runs[]` に `summary_path` / `failed_case_count` / `failed_case_ids` / `child_daily_summaries_to_check` を保存
    - exit code は `0=rollup_generated / 1=invalid_input_or_not_found`
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py --latest` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T100815Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T100815Z_report.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_report_rollup_20260225T100830Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T100835Z.json`
- 削除候補メモ（未削除）：
  - 今回該当なし（実データ削除は未実施）

## 56. TASK86 実行ログ（retry run report rollup起点 retry manifest生成CLI）

[x] 86) artists回答QA日次復旧retry run summary report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
- 変更ファイル：
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - 既存 `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py` を TASK85 の rollup 出力に対して運用適用
  - `--latest` 解決（`artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json` / `*_retry_manifest.json`除外）を確認
  - 生成manifestの保存キー（`source_summary_path` / `failed_case_ids` / `retry_manifest_path` / `cases[]`）を確認
- 動作確認（2026-02-25）：
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
- 削除候補メモ（未削除）：
  - 今回該当なし（実データ削除は未実施）

## 57. TASK87 実行ログ（retry run report rollup起点retry manifest ワンショット実行CLI）

[x] 87) artists回答QA日次復旧retry run report rollup起点retry manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
- 変更ファイル：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py` を追加
    - 既存 `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py` を subprocess で再利用する薄い実行ラッパーとして実装
    - 入力：`--retry-manifest` / `--latest`（排他）
    - `--latest` 既定globを `artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json` に固定
    - `--output-json` は既存実行CLIへ透過委譲し、summaryキー（`retry_manifest_path` / `executed_runs` / `wrapper_exit_code` / `child_daily_summaries`）は既存仕様を維持
- 動作確認（2026-02-25）：
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
- 削除候補メモ（未削除）：
  - 今回該当なし（実データ削除は未実施）

## 58. TASK88 実行ログ（retry run summary軽量レポートCLI + 最小共通整理）

[x] 88) artists回答QA日次復旧retry run report rollup起点retry run summary の軽量レポートCLIを追加し、failed/recovered run を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `qa_artifact_utils.py`（新規）
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py`（新規）
  - `run_aqa_retry_run_report_rollup.py`（新規）
  - `run_aqa_retry_run_report_rollup_manifest.py`（新規）
  - `run_aqa_retry_run_report_rollup_retry_run.py`（新規）
  - `run_aqa_retry_run_report_rollup_retry_run_report.py`（新規）
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_manifest_report_rollup.py`
  - `run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py`
  - `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py`
  - `run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - TASK88本体として `run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py` を追加
    - 入力: `--summary-path` / `--latest`（排他）
    - 出力: `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes`
    - exit: `0=report_generated` / `1=summary_not_found_or_invalid`
  - 軽量共通整理として `qa_artifact_utils.py` を追加
    - TASK85〜88系の artifact registry（`artifact_kind/schema_name/schema_version/glob/exclude`）
    - `resolve_latest_artifact(...)` / `list_candidate_artifacts(...)` を共通化
    - `build_artifact_header(...)` で共通メタ付与を統一
  - TASK85/86/87系に共通化を反映（既存本体ロジックは維持）
  - 命名長の運用負荷軽減として短い入口ラッパー4本を追加（長いCLI名は後方互換で維持）
- 動作確認（2026-02-25）：
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest.py --latest` → exit 1
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --latest` → exit 0
  - `python run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z.json"` → exit 0
  - `python run_aqa_retry_run_report_rollup_retry_run_report.py --latest` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T105331Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T105421Z.json`
- CLEANUP_CANDIDATES（集約先）：
  - 以降は `CLEANUP_CANDIDATES_MASTER` に一本化して管理（2026-02-25）

## 59. TASK89 実行ログ（retry-run導線ワンショット日次チェーンCLI）

[x] 89) artists回答QA retry-run導線（TASK85〜88）を短い入口でワンショット実行するCLIを追加し、日次復旧の運用手順を固定する（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain.py` を追加し、短い入口4本（TASK85〜88）を subprocess で順次実行するチェーン導線を実装
    - `run_aqa_retry_run_report_rollup.py`
    - `run_aqa_retry_run_report_rollup_manifest.py`
    - `run_aqa_retry_run_report_rollup_retry_run.py`
    - `run_aqa_retry_run_report_rollup_retry_run_report.py`
  - chain summaryへ `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存
  - 上流失敗時は後続stepを `skipped` で明示する運用に統一
  - retry対象0件（empty manifest）では no-op 成功（exit 0）を維持
  - `qa_artifact_utils.py` の registry に `retry_run_daily_chain_summary` を追加（artifact識別メタ統一）
- 動作確認（2026-02-25）：
  - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_latest.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T112755Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_latest.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T112809Z.json`
- CLEANUP_CANDIDATES（集約先）：
  - 以降は `CLEANUP_CANDIDATES_MASTER` に一本化して管理（2026-02-25）
- 2026-02-25：TASK 90 実施。`run_aqa_retry_run_daily_chain_report.py` を追加し、daily chain summary（`artists_answer_qa_retry_run_daily_chain_summary_*.json`）の軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、report JSONへ `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK91: daily chain report rollup CLI）を追加。

## 60. TASK90 実行ログ（daily chain summary軽量レポートCLI）

[x] 90) artists回答QA retry-run daily chain summary の軽量レポートCLIを追加し、failed step と参照先summaryを1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_report.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_report.py` を追加
    - 入力：`--summary-path` / `--latest`（排他）
    - `--latest` は `qa_artifact_utils.resolve_latest_artifact(...)` で解決
    - report出力に `all_passed` / `wrapper_exit_code` / `failed_steps` / `child_summary_paths_to_check` / `notes` を保存
    - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与
    - exit規約：`0=report_generated` / `1=summary_not_found_or_invalid`
- 動作確認（2026-02-25）：
  - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T115603Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T115617Z.json`
- 2026-02-25：TASK 91 実施。`run_aqa_retry_run_daily_chain_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_summary_*_report.json` を最新N件で集約して failed run 推移を抽出する導線を実装。`qa_artifact_utils.py` の `list_candidate_artifacts` / `build_artifact_header` を再利用し、rollup出力に `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK92: daily chain report rollup起点retry manifest生成CLI）を追加。

## 61. TASK91 実行ログ（daily chain report rollup CLI）

[x] 91) artists回答QA retry-run daily chain report のrollup CLIを追加し、failed run推移を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_report_rollup.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_report_rollup.py` を追加
    - 入力：`--latest-n` / `--search-dir` / `--glob` / `--output-json`
    - `qa_artifact_utils.list_candidate_artifacts(...)` で report 候補を共通解決
    - rollup出力に `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存
    - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与
    - exit規約：`0=rollup_generated` / `1=invalid_input_or_not_found`
  - `qa_artifact_utils.py` に `retry_run_daily_chain_report_rollup` artifact定義を追加
- 動作確認（2026-02-25）：
  - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T120703Z.json"` → exit 0
  - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T120703Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_summary_20260225T120703Z_report.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T120723Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T120703Z.json`
- 2026-02-25：TASK 92 実施。`run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` を追加し、`artists_answer_qa_retry_run_daily_chain_report_rollup_*.json` から failed run を抽出して retry manifest を生成する導線（`--rollup-json` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、manifest出力に `artifact_kind/schema_name/schema_version/generated_at/generated_by` を付与。動作確認は `python run_aqa_retry_run_daily_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK93: daily chain report rollup起点manifestワンショット実行CLI）を追加。
- 2026-02-25：TASK 93 実施。`run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py` を追加し、daily chain report rollup起点 retry manifest のワンショット実行導線（`--retry-manifest` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` を使って最新manifestを解決し、既存 `run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲して retry-run本体ロジックの重複を回避。動作確認は `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --latest`（exit 0, no-op）/ `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "...143017Z_retry_manifest.json"`（exit 0, no-op）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK94: daily chain report rollup起点の復旧導線をワンショット化）を追加。
- 2026-02-26：TASK 94 実施。`run_aqa_retry_run_daily_chain_recovery_chain.py` を追加し、daily chain report rollup起点の復旧導線（`report_rollup -> retry_manifest -> retry_run`）を1コマンド化。既存3本の短い入口CLIを subprocess で順次再利用し、chain summaryへ `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK95: chain summary軽量レポートCLI）を追加。
- 2026-02-26：TASK 95 実施。`run_aqa_retry_run_daily_chain_recovery_chain_report.py` を追加し、`artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json` から failed step と参照先summaryを抽出する軽量レポート導線（`--summary-path` / `--latest`）を実装。`qa_artifact_utils.py` の `resolve_latest_artifact` / `build_artifact_header` を再利用し、`retry_run_daily_chain_recovery_chain_report` artifact定義を追加。あわせて `retry_run_daily_chain_recovery_chain_summary` に `_report.json` 除外を追加し、`--latest` 解決でreport誤選択を防止。動作確認は `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest`（exit 0）/ `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T160126Z.json"`（exit 0）/ `python run_compare_phase1_guard.py --target-year 2025`（exit 0）。次タスク（TASK96: chain report rollup CLI）を追加。

## 62. TASK92 実行ログ（daily chain report rollup起点retry manifest生成CLI）

[x] 92) artists回答QA retry-run daily chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` を追加
    - 入力：`--rollup-json` / `--latest`（排他）、`--search-dir` / `--glob` / `--output-manifest`
    - `--latest` は `qa_artifact_utils.resolve_latest_artifact(...)` で rollup 本体を解決
    - manifestに `source_summary_path` / `failed_step_names` / `retry_manifest_path` を保存
    - failed run 0件時は `notes=["no_failed_runs_in_rollup"]` 付き空manifestを保存し exit 0
    - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を標準付与
  - `qa_artifact_utils.py` に `retry_run_daily_chain_report_rollup` の `exclude_substrings=["_retry_manifest.json"]` を追加
  - `qa_artifact_utils.py` に `retry_run_daily_chain_report_rollup_retry_manifest` artifact定義を追加
- 動作確認（2026-02-25）：
  - `python run_aqa_retry_run_daily_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T121322Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T121322Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T121322Z_retry_manifest.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T121331Z.json`

## 63. TASK93 実行ログ（daily chain report rollup起点manifestワンショット実行CLI）

[x] 93) artists回答QA retry-run daily chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--retry-manifest` / `--latest`（排他）で入力を受ける薄い実行ラッパーを追加
  - `--latest` は `qa_artifact_utils.resolve_latest_artifact(...)` で `artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json` を解決
  - 本体処理は `run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲（ロジック重複なし）
  - 新規summaryは作らず、子CLI生成の summary を正本として採用
- 動作確認（2026-02-25）：
  - `python run_aqa_retry_run_daily_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --latest` → exit 0（no-op, `executed_runs=0`）
  - `python run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z_retry_manifest.json"` → exit 0（no-op）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T143017Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T143206Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T143211Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T143053Z.json`

## 64. TASK94 実行ログ（daily chain report rollup起点の復旧導線ワンショットCLI）

[x] 94) artists回答QA retry-run daily chain report rollup起点の復旧導線をワンショット化し、rollup→manifest→retry-runを1コマンドで順次実行できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_recovery_chain.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_recovery_chain.py` を追加
  - `run_aqa_retry_run_daily_chain_report_rollup.py` / `run_aqa_retry_run_daily_chain_retry_manifest_from_report_rollup.py` / `run_aqa_retry_run_daily_chain_retry_run_from_report_rollup_manifest.py` を subprocess で順次実行
  - chain summary に `steps[].name/command/exit_code/output_paths` / `all_passed` / `wrapper_exit_code` / `notes` を保存
  - `qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_summary` artifact定義を追加し、schema識別メタ（`artifact_kind/schema_name/schema_version/generated_at/generated_by`）を付与
- 動作確認（2026-02-26）：
  - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest --output-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T155516Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_latest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T155516Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_report_rollup_20260225T155516Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T155516Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T155522Z.json`

## 65. TASK96 実行ログ（daily chain recovery chain report rollup CLI）

[x] 96) artists回答QA retry-run daily chain recovery chain report のrollup CLIを追加し、failed step推移を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py` を追加
  - 入力：`--latest-n` / `--search-dir` / `--glob` / `--output-json`
  - `qa_artifact_utils.list_candidate_artifacts(...)` で report 候補を共通解決
  - rollup JSONに `total_reports` / `failed_run_count` / `failed_runs[]`（`summary_path` / `failed_step_count` / `failed_step_names` / `child_summary_paths_to_check`）を保存
  - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与
  - `qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_report_rollup` artifact 定義を追加
- 動作確認（2026-02-26）：
  - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T161147Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T161147Z_report.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T161201Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T161204Z.json`

## 66. TASK97 実行ログ（recovery chain report rollup起点retry manifest生成CLI）

[x] 97) artists回答QA retry-run daily chain recovery chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py` を追加
  - 入力：`--rollup-json` / `--latest`（排他）、`--search-dir` / `--glob` / `--output-manifest`
  - `qa_artifact_utils.resolve_latest_artifact(...)` で rollup 本体を `--latest` 解決
  - manifestに `source_summary_path` / `failed_step_names` / `retry_manifest_path` / `cases[]` を保存
  - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与
  - `qa_artifact_utils.py` に以下を反映：
    - `retry_run_daily_chain_recovery_chain_report_rollup` に `exclude_substrings=[\"_retry_manifest.json\"]`
    - `retry_run_daily_chain_recovery_chain_report_rollup_retry_manifest` artifact定義を追加
  - failed run 0件時は no-op扱い（`notes=[\"no_failed_runs_in_rollup\"]`）で exit 0
- 動作確認（2026-02-26）：
  - `python run_aqa_retry_run_daily_chain_recovery_chain.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --rollup-json "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T163124Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T163112Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_20260225T163112Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T163137Z.json`
- 運用メモ：
  - 同系統導線は TASK98/99 で一区切りにし、その後は画像収集（seed10）側へ主軸を戻す判断を行う


## 67. TASK98 実行ログ（recovery chain report rollup起点manifestワンショット実行CLI）

[x] 98) artists回答QA retry-run daily chain recovery chain report rollup起点manifestをワンショット実行するCLIを追加し、`--latest` だけで再実行できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py` を追加
  - 入力：`--retry-manifest` / `--latest`（排他）、`--search-dir` / `--glob` / `--output-json`
  - `qa_artifact_utils.resolve_latest_artifact(...)` で最新 retry manifest を解決
  - `qa_artifact_utils.py` に `retry_run_daily_chain_recovery_chain_retry_run_summary_from_report_rollup_manifest` artifact定義を追加（TASK99の `--latest` 解決準備）
  - 既存 `run_aqa_retry_run_report_rollup_retry_run.py` へ subprocess 委譲し、retry-run本体ロジックの重複実装を回避
  - no-op（`cases=[]`）時は子CLIの summary で `executed_runs=0` / `notes=["no_failed_runs_in_manifest"]` を確認し、wrapper exit 0 を維持
- 動作確認（2026-02-26）：
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --retry-manifest "data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z_retry_manifest.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_20260225T164200Z_retry_manifest.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T164211Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T164217Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T164228Z.json`

## 68. TASK99 実行ログ（recovery chain report rollup起点retry-run summary軽量レポートCLI）

[x] 99) artists回答QA retry-run daily chain recovery chain report rollup起点retry-run summary の軽量レポートCLIを追加し、failed/recovered run を `--latest` で即確認できるようにする（本体前進）
- 変更ファイル：
  - `run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--summary-path` / `--latest`（排他）で retry-run summary を読み、軽量reportを生成するCLIを追加
  - `qa_artifact_utils.resolve_latest_artifact(...)` を使って `artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json` を `--latest` 解決
  - reportに `retry_manifest_path` / `executed_runs` / `failed_runs` / `failed_case_ids` / `child_daily_summaries_to_check` / `notes` を保存
  - `qa_artifact_utils.build_artifact_header(...)` により schema識別メタ（`artifact_kind/schema_name/schema_version/generated_at/generated_by`）を標準付与
  - 追加要件対応：入力summaryの `retry_manifest_path` が `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*_retry_manifest.json` 系かを検証し、不一致時は `notes` に理由を残して `exit_reason=summary_out_of_scope_for_task99` / exit 1
- 動作確認（2026-02-26）：
  - `python run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py --latest-n 20` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --latest` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T165814Z.json"` → exit 0
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py --summary-path "/tmp/task99_retry_summary_manifest_mismatch.json"` → exit 1（scope mismatchを検知）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T165814Z.json`
  - `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20260225T165814Z_report.json`
  - `/tmp/task99_retry_summary_manifest_mismatch_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T165825Z.json`

## 69. TASK100 実行ログ（Phase1 seed10 artists画像収集 実測CLI）

[x] 100) Phase1 seed10 の artists画像収集（実測）CLIを追加し、5枚/人・70%超えの達成状況を summary で可視化する（本体前進）
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect.py`（新規）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - seed10 artists raw（`artists_*_2025.jsonl`）を対象に画像候補を抽出し、`target_images_per_artist` まで保存する実測CLIを追加
  - summaryへ `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `failed_cases` / `domain_stats` を保存
  - summaryに schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与
- 動作確認（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実測結果（summary）：
  - `seed_artist_count=81`
  - `artists_with_ge_target_images=0`
  - `success_rate_ge_target=0.0`
  - `threshold_passed=false`
  - `failed_cases=81`（先頭理由例: DNS解決失敗）
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T232825Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T232825Z.json`

## 70. TASK101 実行ログ（artists画像収集実測summary 軽量レポートCLI）

[x] 101) artists画像収集実測summaryの軽量レポートCLIを追加し、5枚達成率/失敗理由上位/ドメイン別失敗を1コマンドで確認できるようにする（本体前進）
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect_report.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--summary-path` / `--latest` で artists画像収集summaryを読み、軽量reportを生成するCLIを追加
  - `qa_artifact_utils.resolve_latest_artifact(...)` で `phase1_seed10_artist_image_collect_summary_*.json` の `--latest` 解決を共通化
  - reportへ `seed_artist_count` / `artists_with_ge_target_images` / `success_rate_ge_target` / `threshold_passed` / `top_failed_reasons` / `top_failed_domains` / `notes` を保存
  - `qa_artifact_utils.build_artifact_header(...)` で schema識別メタ（`artifact_kind/schema_name/schema_version/generated_at/generated_by`）を付与
- 動作確認（2026-02-26 JST）：
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

## 71. TASK102 実行ログ（artists画像収集実測report rollup CLI）

[x] 102) artists画像収集実測reportのrollup CLIを追加し、直近N回の達成率推移と失敗理由変化を1コマンドで抽出できるようにする（本体前進）
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect_report_rollup.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--latest-n` / `--search-dir` / `--glob` / `--output-json` で report集計できる rollup CLI を追加
  - `qa_artifact_utils.list_candidate_artifacts(...)` で `phase1_seed10_artist_image_collect_summary_*_report.json` の最新N件を共通解決
  - rollupへ `total_reports` / `threshold_passed_count` / `threshold_passed_rate` / `success_rate_trend` / `top_failed_reasons_trend` / `top_failed_domains_trend` を保存
  - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与
- 動作確認（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実測rollup要点：
  - `total_reports=2`
  - `threshold_passed_count=0`
  - `threshold_passed_rate=0.0`
  - `top_failed_reasons_aggregate=[{\"reason\":\"html_fetch_failed\",\"count\":162}]`
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T234412Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260225T234412Z_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260225T234417Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260225T234417Z.json`

## 72. TASK103 実行ログ（artists画像収集実測rollup起点retry manifest生成CLI）

[x] 103) artists画像収集実測rollupから優先再収集manifestを生成し、失敗理由/ドメイン上位への再試行入口を短縮する（本体前進）
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect_retry_manifest.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--rollup-json` / `--latest`（排他）で rollupを入力し、再収集対象 `cases[]` を生成するCLIを追加
  - `--max-cases` / `--min-failed-count` / `--failed-reasons` / `--failed-domains` で対象抽出を調整可能化
  - `qa_artifact_utils.resolve_latest_artifact(...)` を再利用して `--latest` 解決を共通化
  - manifestへ `source_rollup_path` / `failed_reason_filter` / `failed_domain_filter` / `cases[]`（`artist_id` / `source_url` / `reason` / `domain`）を保存
  - schema識別メタ（`artifact_kind` / `schema_name` / `schema_version` / `generated_at` / `generated_by`）を付与
  - failedケース0件時は `notes=[\"no_retry_cases_selected\"]` を残して exit 0 を維持
- 動作確認（2026-02-26 JST）：
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

## 73. TASK104 実行ログ（artists画像収集retry manifestワンショット実行CLI）

[x] 104) artists画像収集retry manifestをワンショット実行するCLIを追加し、再収集導線を1コマンド化する（本体前進）
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect_retry_run.py`（新規）
  - `qa_artifact_utils.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容：
  - `--retry-manifest` / `--latest`（排他）で retry manifest を入力し、既存 `run_phase1_seed10_artist_image_collect.py` を subprocess 委譲実行する薄いラッパーを追加
  - `qa_artifact_utils.resolve_latest_artifact(...)` で最新 manifest を解決
  - wrapper summary に `retry_manifest_path` / `executed_cases` / `wrapper_exit_code` / `child_collect_summaries` と schema識別メタを保存
  - no-op（`cases=[]`）時は `executed_cases=0` / `notes=["no_retry_cases_in_manifest","no_retry_cases_selected"]` で exit 0
  - `qa_artifact_utils.py` の `phase1_seed10_artist_image_collect_report_rollup` へ `_retry_manifest.json` 除外を追加し、`--latest` の誤判定を防止
  - `qa_artifact_utils.py` に `phase1_seed10_artist_image_collect_retry_run_summary` artifact定義を追加
- 動作確認（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_phase1_seed10_artist_image_collect_retry_manifest.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_retry_run.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T023049Z_retry_manifest.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_retry_run.py --retry-manifest /tmp/phase1_seed10_artist_image_collect_retry_manifest_empty_task104.json` → exit 0（no-op）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T023049Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T023049Z_retry_manifest.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_retry_run_summary_20260226T023102Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_retry_run_summary_20260226T023109Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_retry_run_summary_20260226T023125Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T023115Z.json`

## 74. HOTFIX 実行ログ（artists画像抽出0件の原因切り分け + 最小修正）

- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容（最小差分）：
  - `fetch_html` / `fetch_image` に `www` 有無の汎用URLフォールバックを追加（ドメイン専用分岐なし）
  - requests retry adapter（`urllib3 Retry`）を追加し、接続/一時失敗の再試行を有効化
  - DNS事前診断（`network_dns_probe_host=example.com` / `network_dns_probe_ok`）を summary へ追加
  - 失敗理由を `html_fetch_failed:dns_resolution_error:<domain>` 形式に正規化して保存
  - `failed_cases` に `domain` / `reason_code` を追加し、次段の集計で原因追跡しやすくした
- 動作確認（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実行結果（要点）：
  - `network_dns_probe_ok=false`
  - `failed_cases=81`
  - `top_reason=html_fetch_failed:dns_resolution_error:<domain>` に収束（原因の明示化）
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T030506Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T030506Z.json`

## 75. TASK105 実行ログ（DNS/外向き通信回復後の再実測）

[x] 105) ブロッカー解消：DNS/外向き通信回復後に artists 画像収集を再実測し、改善ループを再開する（本体前進）
- 参照章ID（01/02）：
  - 01: `4-0) ①～④共通ルール`, `4-4) Artist：作品画像（抽出ルール）`, `5-8) 同期方式（R2正本 + local cache）`, `6-3) 品質ライン（試作10ギャラリーの運用）`
  - 02: `CARD_ID: 09_FAILURE_LOGGING`, `CARD_ID: 10_NO_HERO_IMAGES`, `CARD_ID: 11_IMAGE_TARGET_LINE`, `CARD_ID: 14_CATEGORY_4_0_COMMON`
- 実行コマンド（2026-02-26 JST）：
  - `curl -I https://example.com` → exit 6（`Could not resolve host`）
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1（`gaierror`）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T031350Z.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実測要約：
  - `network_dns_probe_ok=false`（DNS未回復）
  - `seed_artist_count=81`, `artists_with_ge_1_image=0`, `artists_with_ge_target_images=0`
  - `success_rate_ge_target=0.0`, `threshold_passed=false`
  - `failed_cases` 主要 reason: `html_fetch_failed`（81件）
  - `top_failed_domains`: `theapproach.co.uk`, `athrart.com`, `gallerybaton.com`, `aplusart.asia`, `afriartgallery.org`（各10件）
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T031350Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T031350Z_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T031350Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T031350Z.json`
- 判定：
  - 環境ブロッカー継続（DNS未回復）。コード追加は広げず、環境回復後の再実測再開へ進める。

## 76. TASK106 実行ログ（環境ブロッカー継続対応・再実測）

[ ] 106) 環境ブロッカー継続対応：DNS/外向き通信回復後の artists画像収集再実測を再開し、5枚達成率の改善ループへ戻す（本体前進）
- 参照章ID（01/02）：
  - 01: `4-0) ①～④共通ルール`, `4-4) Artist：作品画像（抽出ルール）`, `5-8) 同期方式（R2正本 + local cache）`, `6-3) 品質ライン（試作10ギャラリーの運用）`
  - 02: `CARD_ID: 09_FAILURE_LOGGING`, `CARD_ID: 10_NO_HERO_IMAGES`, `CARD_ID: 11_IMAGE_TARGET_LINE`, `CARD_ID: 14_CATEGORY_4_0_COMMON`
- 実行コマンド（2026-02-26 JST）：
  - `curl -I https://example.com` → exit 6（`Could not resolve host`）
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1（`gaierror`）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T032922Z.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実測要約：
  - `network_dns_probe_ok=false`（DNS未回復継続）
  - `seed_artist_count=81`, `artists_with_ge_1_image=0`, `artists_with_ge_target_images=0`
  - `success_rate_ge_target=0.0`, `threshold_passed=false`
  - `failed_cases` 主要 reason: `html_fetch_failed`（81件）
  - `top_failed_domains`: `theapproach.co.uk`, `athrart.com`, `gallerybaton.com`, `aplusart.asia`, `afriartgallery.org`
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T032922Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T032922Z_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T032922Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T032922Z.json`
- 判定：
  - 通信回復条件を満たさないため、TASK106は継続管理（[ ]）とする。
  - コード改修は追加せず、環境回復後に同手順を再実行する。

## 77. TASK106 実行ログ（通信回復後の再実測・完了）

[x] 106) 環境ブロッカー継続対応：DNS/外向き通信回復後の artists画像収集再実測を再開し、5枚達成率の改善ループへ戻す（本体前進）
- 参照章ID（01/02）：
  - 01: `4-0) ①～④共通ルール`, `4-4) Artist：作品画像（抽出ルール）`, `5-8) 同期方式（R2正本 + local cache）`, `6-3) 品質ライン（試作10ギャラリーの運用）`
  - 02: `CARD_ID: 09_FAILURE_LOGGING`, `CARD_ID: 10_NO_HERO_IMAGES`, `CARD_ID: 11_IMAGE_TARGET_LINE`, `CARD_ID: 14_CATEGORY_4_0_COMMON`
- 実行コマンド（2026-02-26 JST）：
  - `curl -I https://example.com` → exit 0
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 0（`104.18.26.120`）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T032922Z.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実測要約（collect summary）：
  - `network_dns_probe_ok=true`
  - `seed_artist_count=81`, `artists_with_ge_1_image=70`, `artists_with_ge_target_images=66`
  - `success_rate_ge_target=0.814815`, `threshold_passed=true`, `total_images_saved=343`
  - `failed_cases` 主要 reason: `no_image_candidates_found`（11件）, `insufficient_image_candidates_after_download`（4件）
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T033809Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T033809Z_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T034342Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T032922Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T034342Z.json`
- 判定：
  - TASK106完了（通信回復後の実測で目標ライン達成）。
  - ただし rollup の最新判定が `20260226T033809Z_report.json` を拾わず、`latest_success_rate` が旧summary（`...032922Z`）を参照する不整合を確認。次タスクで補正する。

## 78. 運用ルール更新（RAG抽出の内訳表示を恒久化）

- 目的：
  - 「RAG抽出時は必ず中身の内訳（どのgallery/fairで何人対象か）を表示・保存する」を恒久ルールとして固定。
- 仕様/索引の反映：
  - SSOT追記: `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`（6-3）
    - `RAG抽出の実行summary/reportには、対象内訳（最低: fair/gallery単位の対象人数・成功人数・成功率）を必須で残す。`
  - DERIVED追記: `docs/02_RAG_SPEC_DERIVED.md`（`CARD_ID: 14_CATEGORY_4_0_COMMON`）
- 実装反映：
  - `run_phase1_seed10_artist_image_collect.py`
    - summaryに `fair_breakdown` / `gallery_breakdown` を追加
    - 実行時に `[BREAKDOWN] gallery ...` を標準出力
  - `run_phase1_seed10_artist_image_collect_report.py`
    - reportに `fair_breakdown` / `gallery_breakdown` を追加
  - `run_phase1_seed10_artist_image_collect_report_rollup.py`
    - rollupに `gallery_breakdown_trend` / `latest_gallery_breakdown` を追加
- 実行コマンド（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report_rollup.py --latest-n 20` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T040337Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T040337Z_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260226T040402Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T040407Z.json`
- 確認結果（要点）：
  - 標準出力で gallery別内訳（fair/galleryごとの artists, ge1, ge_target, rate）を確認
  - report JSONで `gallery_breakdown` 10件を確認
  - rollup JSONで `gallery_breakdown_trend` / `latest_gallery_breakdown` を保存

## 79. 運用ルール追補（内訳に取得画像枚数・取得率%を必須化）

- 目的：
  - 内訳表示に「何枚取得されたか」「取得率何%か」を必須化し、実行結果だけで判断可能にする。
- 変更ファイル：
  - `run_phase1_seed10_artist_image_collect.py`
  - `run_phase1_seed10_artist_image_collect_report.py`
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
  - `docs/02_RAG_SPEC_DERIVED.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実行コマンド（2026-02-26 JST）：
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T_breakdown_pct_check.json` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T_breakdown_pct_check.json` → exit 0
- 生成物：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T_breakdown_pct_check.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T_breakdown_pct_check_report.json`
- 反映内容（要点）：
  - summary/reportに `success_rate_ge_target_pct` を追加
  - `gallery_breakdown` 各行に `images_saved_total` と `success_rate_ge_target_pct` を追加
  - 標準出力の内訳表示を `images=...` / `(...%)` 付きへ更新
  - SSOT/DERIVEDの文言を「対象人数・成功人数・取得画像枚数・成功率%」へ更新

## 80. 運用ルール追補（exhibitions/textにも同一内訳フォーマットを適用）

- 目的：
  - 内訳表示ルールを画像収集だけでなく、`run_phase1_seed10.py` のテキスト抽出（exhibitions_text / artists_text）にも適用する。
- 変更ファイル：
  - `run_phase1_seed10.py`
  - `run_phase1_seed10_artist_image_collect.py`
  - `run_phase1_seed10_artist_image_collect_report.py`
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
  - `docs/02_RAG_SPEC_DERIVED.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実行コマンド（2026-02-26 JST）：
  - `python -m py_compile run_phase1_seed10.py run_phase1_seed10_artist_image_collect.py run_phase1_seed10_artist_image_collect_report.py` → exit 0
  - `python run_phase1_seed10.py --include-artists-text` → exit 1（`ModuleNotFoundError: No module named 'bs4'`）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物（確認できたもの）：
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T041157Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T041157Z_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T041711Z.json`
- 反映内容（要点）：
  - `run_phase1_seed10.py` summaryに以下を追加：
    - `exhibitions_text_fair_breakdown` / `exhibitions_text_gallery_breakdown`
    - `artists_text_fair_breakdown` / `artists_text_gallery_breakdown`
    - 各カテゴリの `*_seed_gallery_count` / `*_galleries_with_ge_1_record` / `*_success_rate_ge_1_record_pct`
  - console表示に `[BREAKDOWN][exhibitions_text][gallery]` / `[BREAKDOWN][artists_text][gallery]` を追加
  - 画像側の内訳表示は `images` と `%` を含む形式に統一
  - SSOT/DERIVED文言を「取得件数（画像=取得画像枚数、テキスト=抽出レコード件数）」に更新

## 81. 実行環境対応（bs4未導入時のテキスト抽出フォールバック）

- 背景：
  - `python run_phase1_seed10.py --include-artists-text` 実行時に `ModuleNotFoundError: No module named 'bs4'` が発生。
  - `pip install beautifulsoup4 lxml` は DNS 解決失敗で導入不可（環境依存）。
- 変更ファイル：
  - `run_phase1_seed10.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容（最小差分）：
  - `bs4` importをoptional化し、未導入時は標準ライブラリ `html.parser` ベースのフォールバックを使用
  - リンク抽出/本文抽出を `extract_links_from_html` / `VisibleTextHTMLParser` へ切替可能化
  - summaryに `html_parser_backend` を追加
  - exhibitions_text / artists_text の内訳を summary/console に保存・表示
    - `*_fair_breakdown` / `*_gallery_breakdown`
    - `*_seed_gallery_count` / `*_galleries_with_ge_1_record`
    - `*_success_rate_ge_1_record_pct`
- 実行コマンド（2026-02-26 JST）：
  - `python -m py_compile run_phase1_seed10.py` → exit 0
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T042243Z.json`
- 実測確認：
  - `html_parser_backend=stdlib_html_parser_fallback`
  - `exhibitions_text_gallery_breakdown` 件数=10
  - `artists_text_gallery_breakdown` 件数=10

## 82. Artists一覧URL→詳細URL固定ルール対応（一覧ページ直抽出禁止）

- 変更ファイル：
  - `run_phase1_seed10.py`
  - `run_phase1_seed10_artist_image_collect.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容（最小差分）：
  - `run_phase1_seed10.py`
    - `extract_candidate_artist_urls(...)` の一覧ページフォールバック（`[list_page_url]`）を廃止。
    - artists候補URLは「一覧URLそのもの」「一覧パス相当URL」を除外し、詳細ページらしいURLのみ通すよう修正。
    - 詳細候補0件時は `NO_ARTIST_DETAIL_LINKS` を failed_fetches / visited_pages に記録。
  - `run_phase1_seed10_artist_image_collect.py`
    - 一覧URLを直接画像抽出対象にしないよう変更。
    - 一覧URL入力時は、まず詳細URLを抽出してから各詳細ページで画像候補抽出するフローへ変更。
    - 同一ギャラリーに詳細URL行が既に存在する場合、一覧URL行ターゲットは除外（過去raw混在の影響を抑止）。
    - summary `notes` に `artist_collect_source_rule=detail_pages_only` を追加。
- 実行コマンド（2026-02-26 JST）：
  - `python -m py_compile run_phase1_seed10.py run_phase1_seed10_artist_image_collect.py` → exit 0
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_detail_rule_check2.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物：
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_detail_rule_check2.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T050315Z.json`
- 確認結果（要点）：
  - artists画像summaryで `seed_artist_count=72`（一覧URL行の一部除外後）/ `success_rate_ge_target=0.847222` を確認。
  - `adamsandollman.com` / `arcadiamissa.com` は `reason=html_fetch_failed:dns_resolution_error:*`（sandbox内DNS制約）で、一覧ページ直抽出ではなく詳細URL解決フェーズで失敗していることを確認。

## CLEANUP_CANDIDATES_MASTER（集約管理）

本節は削除候補の棚卸し専用。2026-02-25 からは「候補は `_trash` へ先に退避」を実運用化。
（今回の退避総数: 384件、カテゴリ間で件数重複あり）

- 2026-02-25（TASK93）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK94）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK95）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK96）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK97）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK98）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK99）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK100）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK101）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK102）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK103）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK104）:
  - path: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_report_rollup_20260225T235146Z_retry_manifest_retry_manifest.json`
    - 理由: TASK104実装途中で `--latest` 誤判定（rollupが retry_manifest を拾う）時に生成された中間manifest
    - 状態: 削除候補（実削除/実移動は未実施）
- 2026-02-26（TASK105）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（TASK106）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（内訳表示ルール恒久化）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（内訳表示ルール追補）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（内訳表示ルール追補: exhibitions/text適用）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（bs4フォールバック対応）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）
- 2026-02-26（一覧URL→詳細URL固定ルール対応）:
  - 今回の実装では新規の削除候補追加なし（実削除/実移動とも未実施）

- path: `/tmp/artists_retry_run_report_rollup_empty_task87_retry_manifest.json`
  - 理由: no-op検証専用の一時manifest
  - 追加Task: TASK88
  - 状態: `_trash` 退避済み（`_trash/20260225T123434Z_cleanup_candidates/tmp/artists_retry_run_report_rollup_empty_task87_retry_manifest.json`）
- path: `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_failed_run_*_daily_summary*.json`
  - 理由: retry run失敗時の子summary群で大量生成される中間確認用出力
  - 追加Task: TASK88
  - 状態: `_trash` 退避済み（364件）
  - 退避先: `_trash/20260225T123434Z_cleanup_candidates/data/phase1_seed10/derived/answer/`
- path: `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json`
  - 理由: 同時刻summary本体が残るため、運用で必要分だけ残せばよい派生report群
  - 追加Task: TASK88/TASK89
  - 状態: `_trash` 退避済み（123件、`*_failed_run_*_daily_summary*.json` と重複あり）
  - 退避先: `_trash/20260225T123434Z_cleanup_candidates/data/phase1_seed10/derived/answer/`
- path: `data/phase1_seed10/derived/answer/artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_20991231T235959Z_report.json`
  - 理由: TASK89の no-op スモーク用に投入した人工seed report（上記report群に含まれる）
  - 追加Task: TASK89
  - 状態: `_trash` 退避済み（上記123件に内包）

_trash 運用方針:
- 削除候補はまず `_trash/<timestamp>_cleanup_candidates/` へ移動し、一定期間の参照確認後に手動削除する。
- 自動大量削除は行わない。削除実行時は都度、候補一覧と影響範囲を確認する。

## 83. 運用ルール更新（RAG内訳の日本語集約ファイル化）

- 背景:
  - 回答本文に内訳を毎回展開するとトークン増になるため、確認用内訳を1ファイルへ集約する運用へ変更。
- 追加ファイル:
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
- 運用ルール:
  - RAG抽出タスクごとに、上記ファイルへ見出し追記。
  - 最低内訳: fair/gallery単位の対象人数・成功人数・取得件数（画像枚数/テキスト件数）・成功率%。
- 初回反映:
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json` を基に TASK106 相当の内訳を記録。

## 84. 運用ルール更新（Codex Efficiency Protocol 導入）

- Codex Efficiency Protocol導入（往復削減・短縮プロンプト・ゲート・MODEL_HINT 4段階）を運用固定。
- 既存の `CLEANUP_CANDIDATES_MASTER` / `_trash` 方針は維持（今回も実削除なし）。


## 85. TASK107 ゲート発動対応（原因分解＋最小修正）

- 参照章ID:
  - 01: 4-0 / 4-4 / 5-8 / 6-3 / Codex Efficiency Protocol
  - 02: CARD_ID 09 / 10 / 11 / 14
- 変更ファイル:
  - `run_phase1_seed10.py`
  - `run_phase1_seed10_artist_image_collect.py`
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実行コマンドとexit:
  - `curl -I --max-time 15 https://example.com` → exit 6（Could not resolve host）
  - `python run_phase1_seed10.py --include-artists-text` → exit 0（saved=0, artists_failed_new=10）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0（no targets）
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 失敗理由上位（今回）:
  - artists_text: DNS_ERROR 10件
  - exhibitions_text: DNS_ERROR 10件
  - artists失敗段: 一覧URLフェーズ 9件 / 詳細URLフェーズ 1件
- ゲート判定（定量）:
  - `artists_failed_fetches_new_in_run / artists_text_seed_gallery_count = 10/10 = 100%`（>20%）
  - `records_saved_total=0` かつ `artists_records_saved_total=0`
- 最小修正内容:
  - `run_phase1_seed10.py`: `should_skip_failed_url` で `DNS_ERROR` は max-retry/cooldown スキップ対象から除外
  - `run_phase1_seed10_artist_image_collect.py`: no-target早期終了でも `network_dns_probe_ok` を必ずsummary記録
- 生成物:
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T074456Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T074456Z.json`
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 86. 運用ルール再設計（SSOT整合ゲートの恒久化）

- 目的:
  - 01未準拠の実装（一覧URL直抽出、上限値の流用など）の再発を防止する。
- 反映先:
  - 01: `SSOT整合ゲート（再発防止・強制運用）` を追加
  - 02: `CARD_ID: 16_SSOT_COMPLIANCE_GATE` を追加
  - 03: `SSOT整合チェック（再発防止：必須）` を追加
- 固定した運用:
  - 実装前に 01章ID/02 CARD_ID/変更対象関数の対応を明示
  - Artistsは「一覧URL→詳細URL→詳細ページ抽出」を必須化（一覧URL直抽出禁止）
  - カテゴリ上限値の流用ミス禁止
  - 実装後に内訳メモと失敗理由上位を 03/04 へ必ず記録
- 備考:
  - 実削除・実移動は実施せず（CLEANUP_CANDIDATES_MASTER / _trash 方針維持）


## 87. TASK108 再実測（DNS回復確認）

- 実行コマンドとexit:
  - `curl -I --max-time 15 https://example.com` → exit 6
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `python run_phase1_seed10.py --include-artists-text` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物:
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T081940Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T081949Z.json`
- ゲート再判定（定量）:
  - `artists_failed_fetches_new_in_run / artists_text_seed_gallery_count = 10/10 = 100%`
  - `records_saved_total=0`, `artists_records_saved_total=0`
  - `artists_with_ge_1_image=0`, `total_images_saved=0`
- 失敗理由上位:
  - artists_text: DNS_ERROR 10件
  - exhibitions_text: DNS_ERROR 10件
  - 段階切り分け（artists）: 一覧URL段 9件 / 詳細URL段 1件
- 結論:
  - 環境ブロッカー継続。コード追加は広げず、DNS回復後に再実測を再開する。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 88. DNS運用固定化（preflight fail-fast導入）

- 追加ファイル:
  - `run_phase1_network_preflight.py`
- 目的:
  - DNS不安定時に本体実行を止め、原因切り分けを先に完了させる。
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 1（この実行環境では DNS/HTTP 到達不可）
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T082637Z.json`
- 運用固定:
  - preflight失敗時は fetch/collect を回さない。
  - 環境復旧後に preflight から再開する。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 89. TASK109 DNS preflightゲート判定（本体停止）

- 参照章ID:
  - 01: 4-0 / 4-4 / 5-8 / 6-3 / SSOT整合ゲート / Codex Efficiency Protocol
  - 02: CARD_ID 09 / 10 / 11 / 14 / 16
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T083115Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T083134Z.json`
- ゲート判定:
  - `dns_ok_rate=0.000 (0/21)`
  - `http_probe_ok=false`
  - preflight fail のため本体実行を停止（空回り防止）
- 失敗理由上位:
  - `http_probe_failed:example.com`
  - `dns_ok_rate_below_threshold:0.000`
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 90. 保存運用ルール更新（Artist画像ローカルキャッシュの階層固定）

- 方針:
  - Artist Works Images のローカル作業キャッシュは `FAIR_SLUG` 単位で一本化する。
  - gallery単位ディレクトリ分割は行わず、識別はファイル名/メタデータで保持する。
- 反映先:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`（SSOT整合ゲート + 5-4注記）
  - `docs/02_RAG_SPEC_DERIVED.md`（CARD_ID:16）
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`（SSOT整合チェック）
- 備考:
  - 実削除・実移動なし（既存 `_trash` / CLEANUP_CANDIDATES_MASTER 方針を維持）

## 91. 暫定運用固定（artists抽出上限を各gallery 1件へ）

- 背景:
  - 抽出品質が不安定なため、検証フェーズは対象を各gallery 1アーティストに限定して安定化を優先。
- 反映:
  - `run_phase1_seed10.py`: `MAX_ARTISTS_PER_GALLERY=1`（暫定）
  - `run_phase1_seed10_artist_image_collect.py`: `MAX_ARTISTS_PER_GALLERY_FOR_COLLECT=1`（暫定）
  - summaryへ `artists_per_gallery_cap_mode=temporary_test_cap` / `max_artists_per_gallery_for_collect=1` を記録
  - 01/02/03へ「暫定1→段階引き上げ→最終80復帰」ルールを追記
- 備考:
  - 実削除なし。安定確認後に段階引き上げタスクを実施する。

## 92. TASK A-1（内訳可視化固定: 0件ギャラリー補完）

- 変更ファイル:
  - `run_phase1_seed10_artist_image_collect_report.py`
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容:
  - report生成時に seed10対象CSV（frieze/liste各先頭5）を読み、`gallery_breakdown` を0件補完する処理を追加。
  - 既存の重複追記防止は維持（同一summary_pathは再追記しない）。
- 実行コマンドとexit:
  - `python run_phase1_seed10_artist_image_collect_report.py --latest` → exit 0
- 確認結果:
  - consoleの `gallery_breakdown` に 10ギャラリー表示（0件含む）
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` の最新RUN節でも0件ギャラリー行を反映
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 93. TASK A-2（Athr / works優先抽出）

- 変更ファイル:
  - `run_phase1_seed10_artist_image_collect.py`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- 実装内容（最小差分）:
  - works優先抽出を追加（`extract_works_candidate_urls`）
  - 優先順: worksリンク（href/anchorにworks）→ `artist_detail_url/works` → 0件時のみ詳細ページfallback
  - 除外優先: exhibitions/profile/bio/about/news/press/contact 系リンク
  - 失敗ノート拡張: `works_page_tried` / `works_page_found` / `works_candidates_count` / `works_not_found_fallback_used`
  - Athr限定検証用フィルタ引数を追加: `--only-fair-slug` / `--only-gallery-name` / `--only-source-url`
- 実行コマンドとexit:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr.json` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr_report.json` → exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr_report.json`
- 確認メモ:
  - この実行環境では `athrart.com` が `html_fetch_failed:dns_resolution_error` で詳細ページ未取得。
  - works優先ロジックの実ドメイン検証は到達可能環境で再確認が必要。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 94. TASK D0（DNS恒久化 + preflight強制運用）

- 参照章ID:
  - 01: 4-0 / 6-3 / SSOT整合ゲート / Codex Efficiency Protocol
  - 02: CARD_ID 09 / 14 / 16
- 恒久化設定確認:
  - `/etc/wsl.conf` に `generateResolvConf=false`
  - `/etc/resolv.conf` に `nameserver 1.1.1.1`, `nameserver 8.8.8.8`, `options timeout:2 attempts:2`
  - `~/.bashrc` に `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` 固定済み
  - `.venv_art_pulse_editor/bin/activate` に同環境変数を追記（今回）
- 実行コマンドとexit:
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `curl -I --max-time 15 https://example.com` → exit 6
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_phase1_network_preflight.py`（再実行） → exit 1
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T105901Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T105956Z.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T110007Z.json`
- 判定:
  - `dns_ok_rate=0.000 (0/21)` が連続のため、preflight fail-fast規約で本体抽出は停止。
  - TASK D0は完了ではなく「環境ブロッカー継続（preflight連続PASS待ち）」。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 95. TASK D0-2（DNS復旧再確認 + preflight連続PASS判定）

- 参照章ID:
  - 01: 4-0 / 6-3 / SSOT整合ゲート / Codex Efficiency Protocol
  - 02: CARD_ID 09 / 14 / 16
- 実行コマンドとexit:
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `curl -I --max-time 15 https://example.com` → exit 6
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_phase1_network_preflight.py`（再実行） → exit 1
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T110249Z.json`（同秒実行で2回目が上書き）
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260226T110306Z.json`
- 判定:
  - preflight 2連続PASS未達（`dns_ok_rate=0.000 (0/21)` 継続）。
  - fail-fast規約により本体抽出は未実行。
  - 環境ブロッカー継続（DNS復旧待ち）。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 96. TASK D0-3（DNS実機切り分け + preflight連続PASS判定）

- 実行コマンドとexit:
  - `cat /etc/wsl.conf` → exit 0
  - `cat /etc/resolv.conf` → exit 0
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `curl -I --max-time 15 https://example.com` → exit 6
  - `python -c "import requests; print(requests.get('https://example.com', timeout=15).status_code)"` → exit 1
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_phase1_network_preflight.py`（再実行） → exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T110720Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T110731Z.json`
- 判定:
  - DNS解決失敗が継続（socket/curl/requests/preflight 全系統でNG）。
  - preflight fail-fast規約により本体抽出（seed10 fetch / image collect / guard）は未実行。
  - ゲート解除不可、環境ブロッカー継続。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 97. TASK D0-4（Windows側ネットワーク要因切り分け）

- 実行コマンドとexit:
  - `powershell.exe -NoProfile -Command "Get-ItemProperty ... Internet Settings ..."` → exit 0
  - `powershell.exe -NoProfile -Command "Get-DnsClientServerAddress ..."` → exit 0
  - `powershell.exe -NoProfile -Command "Resolve-DnsName example.com ..."` → exit 0
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `curl -I --max-time 15 https://example.com` → exit 6
  - `python -c "import requests; print(requests.get('https://example.com', timeout=15).status_code)"` → exit 1
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_phase1_network_preflight.py`（再実行） → exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T110720Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T110731Z.json`
- 主要判定:
  - Windowsホスト側DNSは解決できる一方、WSL側（この実行環境）で名前解決失敗が継続。
  - preflight 2連続PASS未達のため、fail-fast規約で本体抽出は未実行。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 98. TASK D0-5（Windows側DNS干渉要因の切り分け）

- 実行コマンドとexit:
  - `powershell.exe ... Internet Settings / WinHTTP / DNS` → exit 0
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → exit 1
  - `curl -I --max-time 10 https://example.com` → exit 6
  - `python -c "import requests; print(requests.get('https://example.com', timeout=15).status_code)"` → exit 1
  - `python run_phase1_network_preflight.py` → exit 1
  - `python run_phase1_network_preflight.py`（再実行） → exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T111235Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T111236Z.json`
- 判定:
  - Windows側ではDNS解決成功（Resolve-DnsName）だが、WSL側のみ名前解決失敗が継続。
  - preflight 2連続PASS未達のため本体抽出は未実行（fail-fast維持）。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 99. TASK D0-6（Windows側干渉停止タスクの実行前切り分け）

- 実行コマンドとexit:
  - `powershell.exe ... Internet Settings / WinHTTP / DNS / adapters` → exit 0
  - `powershell.exe ... Get-Service (VPN/セキュリティ絞り込み)` → exit 0（該当なし）
  - `powershell.exe ... Get-Process (vpn/secure絞り込み)` → exit 0（`Secure System` 以外なし）
- 判定:
  - Windows側ではDNS解決成功だが、WSL側のみ名前解決失敗が継続。
  - 停止対象を自動特定できないため、手動で VPN/セキュリティDNS保護の停止確認が必要。
  - `wsl --shutdown` を伴う復旧はユーザー操作が必要（このセッションでは実行不可）。
- 参照生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T111235Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T111236Z.json`
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 100. TASK D0-6.1（preflight 2連続PASSの正本確定 + 恒久化）

- ユーザー端末での実行結果（正本）:
  - `cat /etc/wsl.conf` → `generateResolvConf = false`
  - `cat /etc/resolv.conf` → `1.1.1.1 / 8.8.8.8`
  - `python -c "import socket; print(socket.gethostbyname('example.com'))"` → 成功
  - `curl -I --max-time 15 https://example.com` → 成功（HTTP/2 200）
  - `python run_phase1_network_preflight.py` → success
  - `python run_phase1_network_preflight.py` → success
- 正本ログ:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T112859Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T112908Z.json`
- 恒久化設定:
  - Windows側 `C:\Users\syatk\.wslconfig` を作成:
    - `[wsl2]`
    - `dnsTunneling=true`
    - `autoProxy=true`
- 判定:
  - D0ゲート解除（preflight連続PASS達成）。
  - 次タスクは A-2（Athr works優先の実ドメイン再検証）へ再開。
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 101. TASK A-2R（Athr works優先 再検証）

- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 1
  - `sleep 1; python run_phase1_network_preflight.py` → exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115105Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115106Z.json`
- 判定:
  - preflight 2連続PASS未達（`dns_ok_rate=0.000 (0/21)`）
  - fail-fast規約により Athr本体抽出（collect/report/guard）は未実行
  - A-2Rは継続（DNSブロッカー再発）
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

## 102. TASK D0-7（preflight再取得 + A-2R即再開判定）

- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 1
  - `sleep 1; python run_phase1_network_preflight.py` → exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115331Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115342Z.json`
- 判定:
  - preflight 2連続PASS未達（`dns_ok_rate=0.000 (0/21)`）
  - fail-fast規約により A-2R本体（Athr collect/report/guard）は未実行
  - D0ブロッカー継続
- CLEANUP_CANDIDATES_MASTER:
  - 今回新規候補なし（実削除/実移動なし）

---
## PREP-20260227 result (re-understand + operational fix before start)

- SSOT references checked:
  - 4-0) common extraction rules
  - 4-4) artist works images
  - 5-7) storage
  - 5-8) R2 source of truth + local cache
  - 6-2) no domain-specific hardcode proliferation
  - 6-3) quality line and required breakdown records
- Re-understood problems:
  - Prior run mixed outputs from multiple galleries, making issue 1-5 root-cause isolation hard.
  - RAG runtime data under `data/phase1_seed10` was still git-tracked, conflicting with SSOT operation.
- Fixes applied:
  - Moved 34 files to `_trash/artist_works_images_cleanup_20260227T021440Z`.
  - Verified `data/phase1_seed10/derived/images/artist_works_images/2025/` is now 0 files.
  - Added `.gitignore` entry: `data/phase1_seed10/`.
  - Executed `git rm -r --cached data/phase1_seed10` (483 files untracked from index; local files remain).
- Next:
  - Start A-2R with fail-fast gate (preflight x2 PASS required), and run Athr only as one-gallery/one-artist.

---
## PREP-R2-SYNC（Phase1 R2同期CLIの導入）

- 変更ファイル:
  - `run_phase1_seed10_r2_sync.py` 追加
- 実装内容:
  - phase1 の `raw/derived/enrichment/logs` を対象にR2同期するCLIを実装
  - `--dry-run` / `--scope` / `--target-year` / `--manifest-path` / `--manifest-r2-key` を実装
  - apply時に `phase1_seed10_artifact_manifest.json` を更新し、R2へアップロード
- 実行コマンド/exit:
  - `python run_phase1_seed10_r2_sync.py --scope all --dry-run` ? exit 0
  - `python run_phase1_seed10_r2_sync.py --scope all` ? exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181020Z.json`
  - `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json`
- 実行結果:
  - status=OK, uploaded=360, skipped=134, failed=0
  - manifest upload: `phase1_seed10/derived/phase1_seed10_artifact_manifest.json` (uploaded=true)
- 判定:
  - R2同期基盤を導入し、以降のタスクで再利用可能

- 追記（再実行結果）:
  - `python run_phase1_seed10_r2_sync.py --scope all` ? exit 0
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181511Z.json`
  - 結果: uploaded=1 / skipped=494 / failed=0
  - `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json` の `failed_count=0` を確認


## 103. TASK A-2R（Athr works優先 再検証）/ 2026-02-27

- 実行コマンド/exit:
  - `python run_phase1_network_preflight.py` ? exit 1
  - `python run_phase1_network_preflight.py` ? exit 1
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020117Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020135Z.json`
- 結果:
  - 2回ともPASS条件未達（`passed=False`, `http_probe_ok=False`）
  - fail-fast により Athr collect/report/guard は未実行
- 備考:
  - 主因: `http_probe_failed:example.com`
  - 03/04/RAG には blocker-only で記録


## 104. TASK D0-A2R-BLOCKER-ROOTCAUSE（preflight失敗の根因切り分け + 修正）

- 事象:
  - `run_phase1_network_preflight.py` の `https://example.com` probe で
    DNS成功でも `CERTIFICATE_VERIFY_FAILED` が1件で fail 判定
- 修正内容:
  - `run_phase1_network_preflight.py`
    - probe URLを安定先（Google/GitHub/Cloudflare）へ切替可能に
    - `--profile-json` / `--probe-url` / `--dns-threshold` / `--http-required-successes`
    - `failure_kind` とHTTP詳細をsummaryへ追加
    - 同秒実行時の衝突回避で `_01`, `_02` 連番出力を追加
  - `config/phase1_network_preflight_profile.json` 更新
- 再実行:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T021906Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T021937Z.json`
- 判定:
  - `dns_ok_rate=1.000`, `http_ok_count=3/3`, `http_required_successes=2`
  - fail-fast 条件（2連続PASS）を満たす


## 105. TASK A-2R-RESTART（Athr works優先 再開）

- 実行コマンド/exit:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json"` ? exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json"` ? exit 1（cp932文字化け）
  - `set PYTHONUTF8=1 && python run_phase1_seed10_artist_image_collect_report.py ...` ? exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` ? exit 0
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T022556Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T022617Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T022757Z.json`
- 結果:
  - Athr: seed_artist_count=1, artists_with_ge_target_images=0, total_images_saved=0
  - failed reason: `no_image_candidates_found_on_artist_detail`（domain=`athrart.com`）
  - works notes: `works_page_tried:3` / `works_page_found:3` / `works_candidates_count:0`
  - guard結果: `guard_passed=True`


## 106. TASK A-2R-FIX（Athr works candidates=0 修正 + 再検証）

- 実行コマンド/exit:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json"` ? exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json"` ? exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` ? exit 0
- 修正:
  - `run_phase1_seed10_artist_image_collect.py`: `extract_image_candidates` に `data-lazy` 対応を追加
  - `run_phase1_seed10_artist_image_collect_report.py`: Windows consoleのエンコード対策を追加
- 結果:
  - Athr: seed_artist_count=1 / artists_with_ge_target_images=1 / total_images_saved=5
  - guard_passed=true（mismatches=0）


## 107. TASK A-2R-FIX-1（Athr絞り込み + Sara Abdu Works再検証）

- 実行コマンド/exit:
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_network_preflight.py` ? exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json"` ? exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json"` ? exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` ? exit 0
- 退避:
  - before=5 / after=0
  - `_trash/task_a2r_fix1_athr_reset_20260227T120334Z`
- 修正:
  - `run_phase1_seed10_artist_image_collect.py` の `data-lazy` 対応、artist slug判定、`works_urls_tried` 記録
  - `run_phase1_seed10_artist_image_collect_report.py` の stdout encoding 対応
- 結果:
  - Athr/Sara Abdu: images_saved=5, target_met=true
  - guard_passed=true

## 108. TASK A-2R-FIX-2（Athr / Sara Abdu 年抽出ルール実装 + 再検証）

- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 退避:
  - 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*`
  - 退避先: `_trash/task_a2r_fix2_sara_abdu_reset_20260227_161353`
  - 退避件数: 5（退避後 `athr__sara-abdu__*` は 0件）
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - 作品画像候補ごとに worksページ近傍テキスト/alt/figcaption から年を抽出
    - 並び順を `year desc`（年不明は末尾）へ変更
    - summaryに `year_sort_audit` と `*_years_top5` / `*_year_desc_ok` を保存
  - `run_phase1_seed10_artist_image_collect_report.py`
    - reportへ `year_sort_audit` を転記
    - breakdown追記時に年抽出監査行を出力
- 年抽出検証（Sara Abdu）:
  - works候補上位5年: `[2024, 2024, 2024, 2022, 2022]`
  - 保存画像上位5年: `[2024, 2024, 2024, 2022, 2022]`
  - 降順判定: `works_candidate_year_desc_ok=true` / `selected_image_year_desc_ok=true`
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T071428Z.json`
- 補足:
  - report内「失敗0件ギャラリー」は 9件（Athr以外は images_saved_total=0）

## 109. TASK A-2R-FIX-3（年抽出 evidence_text 保存 + 再検証）

- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 退避: `athr__sara-abdu__*` → `_trash/task_a2r_fix3_sara_abdu_reset_20260227_162659`（5件、退避後0件）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - 年抽出時のコンテキストから `evidence_text`（120文字）を生成
    - `works_candidate_year_evidence_top5` / `selected_image_year_evidence_top5` に `evidence_text` を保存
  - `run_phase1_seed10_artist_image_collect_report.py`
    - `year_sort_audit` の `selected_image_year_evidence_top5[].evidence_text` を RAG内訳へ転記
- 検証:
  - `selected_image_years_top5=[2024, 2024, 2024, 2022, 2022]`
  - `selected_image_year_desc_ok=true`
  - summary/report とも `selected_image_year_evidence_top5[].evidence_text` を確認
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T072648Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T072648Z_01.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T072806Z.json`

## 110. TASK A-2R-FIX-4（evidence_text ノイズ除去 + 再検証）

- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 退避: `athr__sara-abdu__*` → `_trash/task_a2r_fix4_sara_abdu_reset_20260227_163444`（5件、退避後0件）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --only-source-url "https://athrart.com/artists/33-sara-abdu/biography" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `sanitize_evidence_text` を追加
    - `evidence_text` 生成時に `key=value` 形式の属性断片・壊れたentity断片・不要記号を除去
    - 120文字短縮ルールは維持
  - `run_phase1_seed10_artist_image_collect_report.py`
    - 既存の evidence_text 転記ロジックは維持（挙動変更なし）
- 検証:
  - `selected_image_years_top5=[2024, 2024, 2024, 2022, 2022]`
  - `selected_image_year_desc_ok=true`
  - `selected_image_year_evidence_top5` は summary/report とも属性ノイズ判定 `False`
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T073427Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T073427Z_01.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T073546Z.json`

## 111. TASK A-2B-CLOSE-1（Gallery Baton works優先検証）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` / `docs/03,04,RAG`
- 実行コマンドとexit:
  - 存在確認4件 → すべて OK
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 対象artist特定: `https://gallerybaton.com/artists/35-liam-gillick`（`artist_id_hint=f0c2c137...`）
  - 退避: `gallery-baton__*` → `_trash/task_a2b_close1_gallery_baton_reset_20260227_170505`（moved=0, remain=0）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Gallery Baton" --only-source-url "https://gallerybaton.com/artists/35-liam-gillick" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `selected_image_years_top5=[2025, 2025, 2025, 2025, 2024]`, `selected_image_year_desc_ok=true`
  - selected URL/evidence で `exhibition/profile/hero` 混入は 0件
  - `works_urls_tried=['https://gallerybaton.com/artists/35-liam-gillick']`
    - `/works` サフィックスURLは未出現だが、同一URL内の作品群から抽出できているため ①-2 は実運用上クリア判定
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T080417Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T080417Z_01.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T080554Z.json`

## 112. TASK A-2A-CLOSE-1（A+ Works of Art works優先検証）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` / `docs/03,04,RAG`
- 実行コマンドとexit:
  - 存在確認4件 → すべて OK
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 対象artist特定: `https://aplusart.asia/artists/46-ahmad-fuad-osman`（`artist_id_hint=92ed6306...`）
  - 退避: `a-works-of-art__*` → `_trash/task_a2a_close1_a_plus_works_reset_20260227_171149`（moved=0, remain=0）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-gallery-name "A+ Works of Art" --only-source-url "https://aplusart.asia/artists/46-ahmad-fuad-osman" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `selected_image_years_top5=[None, None, None, None, None]`（年情報なし）
  - `works_urls_tried=['https://aplusart.asia/artists/']` で、artist detail (`.../artists/46-ahmad-fuad-osman`) ではなく一覧系へ逸脱
  - selected URL に `thuy-anh` / `kentaro` 等の他作家トークンを確認（対象外作家混入）
  - exhibition/profile/hero 混入は0件だが、①-3完了条件（対象作家作品のみ）は未達
- 結論:
  - TASK A-2A-CLOSE-1 は「検証済み・未解決」。
  - 次タスクで「artist一致性を維持した works 優先抽出」へ修正が必要。
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T081126Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T081126Z_01.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T081204Z.json`

## 112-2. TASK A-2A-CLOSE-2（A+ Works of Art 最終確定）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `docs/03,04,RAG`
- 実行コマンドとexit:
  - 存在確認4件 → すべて OK
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/35-chong-kim-chiew" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/41-gan-chin-lee" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong_report.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan_report.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `works_only_artist_match_unique_count`
    - `works_only_artist_match_unique_urls_top20`
    - 上記を `per_artist_counts` / `year_sort_audit` へ出力
- 判定:
  - Chong: `saved_images=3`, `target_met=false`, `works_only_artist_match_unique_count=3`
  - Gan: `saved_images=0`, `target_met=false`, `works_only_artist_match_unique_count=0`
  - 01 6-2準拠: works-only範囲で追加ユニークソース不足のため、5/5未達を理由付き確定
  - 再開条件: 「サイト側でworks画像が追加される」または「01仕様変更」
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T060151Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T060209Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260228T060753Z.json`

## 113. TASK A-2A-FIX-1（A+ Works of Art artist一致性ガード修正）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` / `docs/03,04,RAG`
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 退避: `a-works-of-art__*` → `_trash/task_a2a_fix1_a_plus_works_reset_20260227_172057`（moved=5, remain=0）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-gallery-name "A+ Works of Art" --only-source-url "https://aplusart.asia/artists/46-ahmad-fuad-osman" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - source_url から artist一致性トークンを生成し、候補URL/近傍テキストで一致しない候補を除外するガードを追加
    - `extract_works_candidate_urls` で `/artists` 等の一覧系URLを除外し、`<artist>/works` を優先探索
  - `run_phase1_seed10_artist_image_collect_report.py`
    - 既存の `year_sort_audit` 転記ロジックを維持（FIX-1での追加破壊なし）
- 判定:
  - 改善点:
    - `works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']` へ修正
    - `selected_image_years_top5=[2024, 2023, 2022, 2021, 2019]`（降順OK）
    - selected evidenceに `thuy-anh` / `kentaro` 等の対象外作家トークン混入は再現せず
  - 残課題:
    - selected URL は 5/5 が `/exhibitions/main_image_override/`（Exhibitions系）
    - ①-3完了条件「WORKS優先のみ（Exhibitions/Profile/hero混入ゼロ）」は未達
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T082034Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T082034Z_01.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T082116Z.json`

## 114. TASK A-2A-FIX-2（A+ Works of Art works-only画像選別ガード強化）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `docs/03,04,RAG`
- 実行コマンドとexit:
  - 存在確認4件 → すべて OK
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 退避: `a-works-of-art__*` → `_trash/task_a2a_fix2_a_plus_works_reset_20260227_173343`（moved=5, remain=0）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-gallery-name "A+ Works of Art" --only-source-url "https://aplusart.asia/artists/46-ahmad-fuad-osman" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `WORKS_ONLY_REJECT_TOKENS` を追加（`/exhibitions`, `main_image_override`, `profile`, `hero` など）
    - `candidate_violates_works_only()` を追加
    - works候補/フォールバック候補の保存前で works-only違反候補を除外
    - `POSITIVE_TOKENS` から `exhibition` を除去（Exhibitions画像の加点防止）
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']`
  - `selected_image_years_top5=[1989, 1953, None, None, None]`, `selected_image_year_desc_ok=true`
  - selected URL/evidence で `exhibition/profile/hero` 混入は 0件
  - ①-3（A+ Works of Art）はクローズ判定
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T083132Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T083140Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T083459Z.json`

## 115. TASK A-4-CLOSE-1（The Approach 破損画像原因切り分け + 再発防止）

- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
  - 変更対象: `run_phase1_seed10_artist_image_collect.py` / `run_phase1_seed10_artist_image_collect_report.py` / `docs/03,04,RAG`
- 対象artist（1ギャラリー=1アーティスト）:
  - source_url: `https://www.theapproach.co.uk/artists/phillip-allen/`
  - artist_id: `261b72a7aa4795ef88ba0454da500ad744e247771e0d42a72da4c53a8b97f12f`
  - 想定保存prefix: `the-approach__phillip-allen__261b72a7`
- 実行コマンドとexit:
  - 存在確認4件 → すべて OK
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - 退避: `the-approach__*` → `_trash/task_a4_close1_the_approach_reset_20260227_174931`（moved=0, remain=0）→ exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "The Approach" --only-source-url "https://www.theapproach.co.uk/artists/phillip-allen/" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach.json"` → exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_report.json` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0
- 原因切り分け（壊れ画像）:
  - 旧ファイル（`_trash/artist_works_images_cleanup_20260227T021440Z/...the-approach__...jpg`）は 5/5 で payloadシグネチャが `.avif`、保存拡張子は `.jpg`
  - content-type/実バイトと保存拡張子の不整合により、閲覧側で「壊れ画像」扱いが発生
  - HTML payloadや空payloadは今回対象外（再現なし）
- 実装（汎用のみ）:
  - `run_phase1_seed10_artist_image_collect.py`
    - `detect_extension` を content-type優先へ変更
    - `sniff_extension_from_payload` を追加（jpeg/png/webp/avif）
    - payloadシグネチャと拡張子が不一致の場合はシグネチャ拡張子を採用
    - `looks_like_html_payload` / `MIN_IMAGE_PAYLOAD_BYTES` を追加して健全性チェック
    - `image/svg+xml` を不許可（非作品向け壊れ要因を抑止）
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `works_urls_tried=['https://www.theapproach.co.uk/artists/phillip-allen/works']`
  - `selected_image_years_top5=[2025, None, None, None, None]`, `selected_image_year_desc_ok=true`
  - selected URL/evidence で `exhibition/profile/hero` 混入は 0件
  - 保存ファイルは `.avif` で 5件、payloadシグネチャ一致、HTML payload 0件（この判定は後に再オープン）
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T084453Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T084504Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T085012Z.json`

## 116. TASK A-4-CLOSE-1-REOPEN（JPEG/100KB ホットフィックス + 全画像再生成）

- 再オープン理由（ユーザー確認）:
  - `.avif` は閲覧環境で読めないため運用不可
  - 100KB目標の圧縮が効かず、10KB級/800KB級が混在
- 実装（汎用のみ）:
  - `run_phase1_seed10_artist_image_collect.py`
    - 画像取得ヘッダを `image/jpeg,image/png,image/*` 優先へ変更（avif/webp優先を除外）
    - `normalize_image_payload_for_rag` を追加し、保存前に JPEG へ正規化
    - `IMAGE_TARGET_SIZE_KB=100` を基準に品質（95→20）と縮小率（1.0→0.2）で段階圧縮
    - 実画像サイズが小さすぎる候補（`<120x120`）を除外
- 実行コマンドとexit（要点）:
  - The Approach 単独再実測（jpegfix）:
    - 退避: `_trash/task_a4_close1_jpegfix_reset_20260227_180052`（moved=5）
    - collect/report/guard: exit 0
  - 既存画像の全再生成（2025配下）:
    - 退避1: `_trash/task_img_jpeg100_refit_reset_20260227_180338`（moved=20）
    - collect(refit): 初回 exit 1（cp932出力で失敗）→ `set PYTHONUTF8=1` で再実行 exit 0
    - 退避2: `_trash/task_img_jpeg100_refit2_reset_20260227_180938`（moved=40）
    - collect(refit2): exit 0
    - 退避3: `_trash/task_img_jpeg100_refit3_reset_20260227_181519`（moved=39）
    - collect(refit3): exit 0
    - report(refit3): exit 0
    - guard(refit3): exit 0
- 最終検証（refit3）:
  - 保存枚数: 39（`.jpg` のみ）
  - サイズ分布: `min=19,096B / max=102,358B / >120KB=0 / <10KB=0`
  - 80〜120KB帯: 29枚（約74%）
  - 失敗は `Amanita` の 1件のみ（`insufficient_image_candidates_after_download`、works URL 404由来）
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_jpegfix.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_jpegfix_report.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T091928Z.json`

## 117. TASK CACHE-POLICY-FIX（成功画像保持 + 無効画像のみ隔離）

- 背景（ユーザー指示）:
  - 失敗時に成功画像まで全退避すると非効率（容量/再取得コスト増）
  - Amanita 4枚はページ上限で妥当（失敗扱いしない運用）
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - 既存キャッシュ検証 `validate_cached_image_file` を追加
    - 不正キャッシュのみ `_trash/invalid_cached_images_<run_ts>/<year>/<fair>/` へ隔離
    - 成功済みの既存画像は保持し、再取得対象から除外しない
- 動作確認:
  - The Approach 単独再実行で既存5枚を保持したまま `saved_images=5` 維持
  - 出力画像は `.jpg` のみ
  - サイズ分布（2025配下）: `max=102,358B`, `>120KB=0`, `<10KB=0`
- 備考:
  - Amanita の 4枚は source 側候補不足（works URL 404）であり、運用上は許容

## 118. TASK RAG-IMAGE-SSOT-REFIT-20260227（SSOT画像ルール再実装 + 全再抽出）

- 背景:
  - SSOT画像ルール（4-4 / 5-4）に対して、`artist_works_images_{FAIR_SLUG}.jsonl` 未生成、`image_url_hash`重複排除欠如、`max_year_seen/current_topN`追跡不足が残っていたため、collectorを再実装。
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `artist_works_images_{fair_slug}.jsonl` 出力を追加（`works_image_urls/hashes/captions/years/r2_keys` ほか）
    - `image_url_hash` で重複候補除外を追加
    - `max_year_seen` と `works_image_topN_candidate_hashes_prev` の保存更新を追加
    - hero/portrait 判定を強信号化（作品情報シグナルがある場合は除外しない）
    - 既存Windows cp932出力クラッシュ対策（stdout reconfigure）を追加
- 実行:
  - preflight 2回:
    - `phase1_network_preflight_summary_20260227T100141Z.json` PASS
    - `phase1_network_preflight_summary_20260227T100141Z_01.json` PASS
  - 全再抽出前退避:
    - `data/phase1_seed10/derived/images/artist_works_images/2025/*` →
      `_trash/task_rag_image_full_reextract_20260227_100225/`（39 files moved）
  - collect（全件）:
    - `phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227.json`（exit 0）
    - 結果: processed=8, ge_target=7, success_rate=87.5%
  - report:
    - `phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227_report.json`（exit 0）
  - guard:
    - `phase1_guard_summary_2025_20260227T100759Z.json`（exit 0, guard_passed=true）
- 生成物:
  - `data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl`
  - `data/phase1_seed10/derived/artist_works_images_liste.jsonl`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T100759Z.json`


## 119. TASK TARUTANI-SSOT-REFIT-20260227（TarutaniRAG SSOT差分修正 + 再ベクター化）

- 修正対象:
  - un_tarutani_text_import.py
    - docx抽出を python-docx へ変更
    - PDF抽出を import 本体へ実装（pypdf）
  - un_tarutani_r2_sync.py
    - source R2 key を data/Tarutani_data/... ミラーへ修正
  - un_vectorize_tarutani_text.py
    - manifest に chunk_size_chars, chunk_overlap_chars, ecords_count, code_commit_id を追加
- 再生成手順:
  - 旧成果物を _trash/task_tarutani_refit_20260227_102918/ へ退避
  - python run_tarutani_text_import.py 再実行
  - 旧 headline_ja を source_path で復元（16件）
  - python run_vectorize_tarutani_text.py 再実行
  - python run_tarutani_r2_sync.py --scope source --dry-run で key 規則確認
- 結果:
  - tarutani_text: 16 records
  - extract_status: DOCX_TEXT_EXTRACTED=8, PDF_TEXT_EXTRACTED=8
  - vectorize: chunks=74, embedded=74, failed=0
  - manifest: 追加項目反映済み

## 120. TASK PREP-R2-GUARD-20260227（R2同期ガード固定 + スナップショット確定）

- 目的:
  - 01 5-8 / 02 CARD 05 に沿って、R2同期の「dry-run確認後のみapply/prune」をCLIで強制する。
- 変更ファイル:
  - `run_phase1_seed10_r2_sync.py`
  - `run_tarutani_r2_sync.py`
- 実装内容:
  - 共通:
    - `--require-dry-run-log` 追加（同一scopeの最新dry-runログを必須化）
    - `--max-prune` 追加（削除候補が上限超過時は削除を実行せず `GUARD_BLOCKED`）
    - summary JSON に `dry_run_guard` / `max_prune` / `guard_blocked` を保存
  - Tarutani同期:
    - 既定 `--scope` を `all` に変更（sourceのみ実行の取りこぼし防止）
- 実行コマンドとexit:
  - `python run_phase1_seed10_r2_sync.py --scope all` → exit 0
  - `python run_tarutani_r2_sync.py --scope all` → exit 0
  - `python run_phase1_seed10_r2_sync.py --scope all --dry-run --prune` → exit 0
  - `python run_tarutani_r2_sync.py --scope all --dry-run --prune --prune-prefix tarutani/source` → exit 0
  - `python run_phase1_seed10_r2_sync.py --scope logs --prune` → exit 0
  - `python run_tarutani_r2_sync.py --scope all --prune --prune-prefix tarutani/source` → exit 0
- 結果:
  - Phase1 apply: `uploaded=47, failed=0`
  - Phase1限定prune: `pruned=487, prune_failed=0`
  - Tarutani apply: `uploaded=23, failed=0`
  - Tarutani限定prune: `pruned=64, prune_failed=0`
  - R2確認:
    - `phase1_seed10/derived/images=39`, `phase1_seed10/derived/vector=5`
    - `tarutani/vectors=5`, `data/Tarutani_data/*=16`
    - 旧 `tarutani/source/*` は削除済み
- 基準スナップショット:
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260227T121330Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_r2_sync_logs_20260227T121741Z.json`
  - `data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121540Z.json`
  - `data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121748Z.json`

## 121. TASK PREP-R2-RUNBOOK-CLI-20260227（R2同期1コマンド化）

- 目的:
  - dry-run/apply/prune の実行順ミスを防ぐため、R2同期を1コマンドで実行する。
- 追加:
  - `run_r2_sync_runbook.py`
    - 実行順固定: `phase1 dry-run --prune` → `tarutani dry-run --prune` → `phase1 apply guarded` → `tarutani apply guarded`
    - guarded apply は `--require-dry-run-log` / `--max-prune` を自動付与
    - 既定で `tarutani/source` を prune 対象に含める（`--no-tarutani-legacy-source-prune` で無効化可）
    - summary を `data/phase1_seed10/logs/r2_sync_runbook_summary_*.json` に保存
- 動作確認:
  - `python run_r2_sync_runbook.py --help` → exit 0
  - `python -m py_compile run_r2_sync_runbook.py` → exit 0

## 122. TASK A-3A-CLOSE-1（Adams and Ollman 理由付きスキップ記録）

- 実行前確認:
  - docs/01_PROJECT_SPEC_CURRENT_FULL.docx, docs/02_RAG_SPEC_DERIVED.md, docs/03_STATE_SNAPSHOT_NEXT_TASKS.md, docs/04_TASK_PROGRESS_LOG.md の存在を確認
  - SSOT章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - CARD_ID: 10, 11, 14, 16
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_network_preflight.py` → exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --only-source-url "https://adamsandollman.com/Past-Exhibitions" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman.json"` → exit 0（no targets）
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman_report.json"` → exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` → exit 0（guard_passed=false）
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close1_adams_ollman_reset_20260227_220415/`
  - moved=0, src_remaining=0
- 判定:
  - 結果は「理由付きスキップ」
  - 主因: `artists_frieze_london_2025.jsonl` に `Adams and Ollman` のartistレコードが存在せず、`seed_artist_count=0` で実測対象が作れない
  - 再開条件: artists raw に対象galleryのartist 1件以上を生成後、同タスクを再実行


## 123. TASK A-3A-FIX-1 (Adams and Ollman: seed 1 record -> re-measure)
- Pre-check:
  - Confirmed docs/01, docs/02, docs/03, docs/04
  - SSOT chapter IDs: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- Commands and exit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - Added seed row to `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl` (with backup)
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --only-source-url "https://adamsandollman.com/Jonathan-Berger-1" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=false`)
- Trash move:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close1_adams_ollman_reset_20260227_222418/`
  - moved=0, src_remaining=0
- Result:
  - `seed_artist_count=1` (previous no-target condition resolved)
  - `works_urls_tried=['https://adamsandollman.com/Jonathan-Berger-1/works']`
  - `works_candidates_count=0`, `saved_images=0`, `selected_image_years_top5=[]`
  - fail reason: `no_image_candidates_found_on_artist_detail`
- Next:
  - Verify generic extraction improvements quickly; if still zero, move to reasoned skip under 01 section 6-2.

## 124. TASK A-3A-CLOSE-2 (Adams and Ollman final validation -> reasoned skip)
- SSOT/CARD gate:
  - 01: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- Commands and exit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --only-source-url "https://adamsandollman.com/Jonathan-Berger-1" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=false`)
- Trash reset:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close2_adams_ollman_reset_20260227_225228/`
  - moved=0, src_remaining=0
- Generic logic validation:
  - Added non-`img` extraction paths in `run_phase1_seed10_artist_image_collect.py`:
    - `src/data-src/data-original/data-lazy-src/data-lazy/poster`
    - non-`img` `srcset`
    - inline image URL references
  - Added metadata noise guard (`meta` preview image rejection) and non-image ref filtering.
  - `Jonathan-Berger-1/works` remained at candidate=0 after guard-compliant filtering.
- Final result:
  - `works_urls_tried=['https://adamsandollman.com/Jonathan-Berger-1/works']`
  - `works_candidates_count=0`, `saved_images=0`
  - fail reason: `no_image_candidates_found_on_artist_detail`
  - decision: reasoned skip fixed under 01 section 6-2.
  - skip registry: `data/gallery_lists/skipped_galleries_registry.csv` に1行追記済み（gallery, ExhibitionURL, ArtistsURL, reason）。

## 125. TASK SKIP-REGISTRY-AUTO-1 (auto skip by gallery registry)
- Purpose:
  - Galleries listed in `data/gallery_lists/skipped_galleries_registry.csv` should be skipped automatically in image collect runs.
- Implementation:
  - `run_phase1_seed10_artist_image_collect.py`
    - load CSV registry at startup (`SKIPPED_GALLERIES_REGISTRY_PATH`)
    - auto-filter targets by `gallery_name_en` match
    - write skip audit to summary:
      - `skip_registry_path`
      - `skip_registry_gallery_count`
      - `skipped_by_registry_count`
      - `skipped_by_registry[]` (gallery/fair/source/exhibition/artists/reason)
      - note: `auto_skipped_by_registry:<count>`
- Smoke verification:
  - command:
    - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --only-source-url "https://adamsandollman.com/Jonathan-Berger-1" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_skip_registry_smoke.json"`
  - result:
    - `seed_artist_count=0`
    - `skipped_by_registry_count=1`
    - target gallery was auto-skipped without extraction.

## 126. TASK A-3B-CLOSE-1 (Arcadia Missa: 0-case rerun)
- 実行前確認:
  - docs/01, docs/02, docs/03, docs/04 の存在を確認
  - SSOT章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - Arcadia seed追加: `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl`（backup作成後に1行追加）
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Arcadia Missa" --only-source-url "https://arcadiamissa.com/brad-kronz/" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa_report.json"` -> exit 0（初回並列時の一時 not found は再実行で解消）
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0（guard_passed=false）
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/arcadia-missa__*`
  - dst: `_trash/task_a3b_close1_arcadia_missa_reset_20260227_232758/`
  - moved=0, src_remaining=0
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `works_urls_tried=['https://arcadiamissa.com/brad-kronz/works']`
  - selected URL に `exhibition/profile/hero` トークン混入なし
  - `selected_image_years_top5=[2026, 2026, 2026, 2026, 2026]`, `selected_image_year_desc_ok=true`
  - ③-2 Arcadia Missa の0件課題は解消（skip registry 追記なし）


## 127. TASK A-3B-DUP-FIX-1 (Arcadia Missa duplicate-photo fix)
- ??:
  - Arcadia Missa ??????2???????URL??????????
- ??:
  - `image_url_hash` ? raw URL ?????`-1024x683` ? `-2048x1365` ???????
  - ?hash metadata ? fallback ?????????????????
- ??:
  - `run_phase1_seed10_artist_image_collect.py`
    - `normalize_image_url_for_dedupe` ???`-WxH` suffix???
    - `image_url_hash` ????????????
    - metadata???? normalized URL identity ??????
- ??:
  - ??1: `_trash/task_a3b_dupfix_arcadia_reset_20260227_234325/`?moved=5?
  - ??2: `_trash/task_a3b_dupfix_arcadia_rerun_reset_20260227_234524/`?moved=4?
  - collect: `phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa.json` -> exit 0
  - report: `phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa_report.json` -> exit 0
  - guard: `phase1_guard_summary_2025_20260227T144647Z.json` -> exit 0
- ??:
  - selected URL?4???????????0??
  - `saved_images=4`, `target_met=false`, reason=`insufficient_image_candidates_after_download`

## 128. TASK A-3B-FIX-2 (Arcadia Missa / Brad Kronz 4枚止まり修正)
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Arcadia Missa" --only-source-url "https://arcadiamissa.com/brad-kronz/" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_fix5_arcadia_missa_brad_kronz.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_fix5_arcadia_missa_brad_kronz.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_fix5_arcadia_missa_brad_kronz_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=false`)
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/arcadia-missa__brad-kronz__*`
  - dst1: `_trash/task_a3b_brad_kronz_reset_20260227_235637/` (moved=4)
  - dst2: `_trash/task_a3b_brad_kronz_rerun_reset_20260227_235809/` (moved=4)
  - dst3: `_trash/task_a3b_brad_kronz_artist_filter_reset_20260228_000001/` (moved=5)
- 修正:
  - stale metadata hash を再取得除外に使わないよう修正（実在・有効なローカルキャッシュのみ既知扱い）
  - 不足補充時の `max_year_seen` / `topN` 候補除外を削除
  - artist一致性判定の「artistページ配下なら無条件許可」を廃止
- 結果:
  - `saved_images=5`, `target_met=true`
  - `selected_image_years_top5=[2026, 2026, 2026, 2026, 2025]`（降順OK）
  - 5件すべて Brad Kronz 由来URL、他作家混入なし

## 129. TASK R2-SYNC-RULE-1 (Arcadia Missa 5枚のR2反映と運用固定)
- 事象:
  - Arcadia Missa の5枚はローカル生成済みだが、R2は未反映だった。
- 原因:
  - `run_phase1_seed10_artist_image_collect.py` はローカル保存のみで、R2同期は自動実行しない。
- 実行:
  - `python run_phase1_seed10_r2_sync.py --scope derived --dry-run --prune` -> exit 0
  - `python run_phase1_seed10_r2_sync.py --scope derived --prune --require-dry-run-log --max-prune 600` -> exit 0
- 結果:
  - Arcadia Missa / Brad Kronz 5枚 (`img_01`〜`img_05`) をR2へUPLOAD済み
  - summary: `data/phase1_seed10/logs/phase1_seed10_r2_sync_derived_20260227T154435Z.json`
- 運用固定:
  - 今後は「RAG生成タスク完了条件」に R2同期（dry-run -> guarded apply）を必須で含める。

## 130. TASK R2-AUTO-SYNC-1 (追加/削除反映の自動化実装)
- 背景:
  - 手動同期では追加/削除の高頻度更新を追従できないため、自動化を必須化。
- 実装:
  - 追加: `r2_auto_sync.py`（自動同期オーケストレータ）
    - 排他ロック: `data/r2_auto_sync/auto_sync.lock`
    - 状態管理: `data/r2_auto_sync/auto_sync_state.json`
    - 監査ログ: `data/r2_auto_sync/logs/r2_auto_sync_<target>_<timestamp>.json`
    - フロー: dry-run(--prune) -> 判定 -> guarded apply
    - 削除安全策: prune候補が2回連続で同一のときのみ prune 実行
      - 1回目は upload/update のみ反映（pruneは保留）
  - 追加: `run_r2_auto_sync.py`（手動トリガー用CLI）
  - 主要生成スクリプトへ自動フック接続:
    - `run_phase1_seed10.py` -> target `phase1_all`
    - `run_phase1_seed10_artist_image_collect.py` -> target `phase1_derived`
    - `run_vectorize_artists_seed10.py` -> target `phase1_derived`
    - `run_enrichment_seed10.py` -> target `phase1_derived`
    - `run_tarutani_text_import.py` -> target `tarutani_all`
    - `run_vectorize_tarutani_text.py` -> target `tarutani_all`
    - `run_enrichment_tarutani_text.py` -> target `tarutani_all`
- 実行結果（smoke）:
  - `python run_r2_auto_sync.py --target phase1_derived --trigger smoke`
  - status=`ok` を確認
- 仕様メモ:
  - 追加/更新は自動でR2反映
  - 削除は「2回連続一致」後に自動反映

## 131. TASK R2-AUTO-SYNC-2 (テキスト抽出系の自動同期フック拡張)
- 目的:
  - 画像以外（今後のテキスト抽出/適用系）で同期抜けが発生しないよう、未接続スクリプトを補完。
- 追加フック:
  - `run_enrichment_artists_seed10_apply.py` -> target `phase1_derived`
  - `run_enrichment_tarutani_text_apply.py` -> target `tarutani_all`
  - `run_tarutani_text_pdf_backfill.py` -> target `tarutani_all`
- 運用固定:
  - 今後追加するテキスト抽出・変換・apply系スクリプトも、終了時 `auto_sync_after_job` 呼び出しを必須化。

## 132. TASK A-5-CLOSE-1 (Anca Poterașu Gallery 非anetta再実測)
- 実装前確認:
  - docs/01, docs/02, docs/03, docs/04 存在確認OK
  - 01章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02 CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- 対象:
  - gallery: `Anca Poterașu Gallery`
  - source_url: `https://www.ancapoterasu.com/artists/aurora-kiraly/`（anetta以外）
  - artist_id: `3ef1b6fb...`（text_hash）
  - 想定保存prefix: `anca-potera-u-gallery__aurora-kiraly__`
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://www.ancapoterasu.com/artists/aurora-kiraly/" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a5_close1_anca_potera_u.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a5_close1_anca_potera_u.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a5_close1_anca_potera_u_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=false`)
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/liste/anca-potera-u-gallery__*`
  - dst: `_trash/task_a5_close1_anca_potera_u_reset_20260228_031259/`
  - moved=5, src_remaining=0
- 修正:
  - `run_phase1_seed10_artist_image_collect.py`
    - `only-source-url` 指定時、gallery上限(1件)適用前に対象sourceを絞り込むように変更
- 結果:
  - `saved_images=4`, `target_met=false`（不足理由: `insufficient_image_candidates_after_download`）
  - `works_urls_tried` に works系URLあり（`.../aurora-kiraly/works` 404 -> fallback）
  - selected画像のURL/evidenceで logo/icon/hero/profile/exhibition 混入は確認されず
## 133. TASK A-3A-CLOSE-3 (Adams and Ollman skip finalization)
- 実施日時: 2026-02-27
- SSOT/DERIVED確認:
  - 01章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02 CARD_ID: 10, 11, 14, 16
- 変更対象と1対1紐付け:
  - `run_phase1_seed10_artist_image_collect.py`: skip registry 自動除外（既存ロジックを再検証）
  - `data/gallery_lists/skipped_galleries_registry.csv`: Adams and Ollman 登録状態確認（重複追記なし）
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`, `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`, `docs/04_TASK_PROGRESS_LOG.md`: 判断根拠/再開条件を記録
- 実行コマンド:
  - `python run_phase1_network_preflight.py`
  - `python run_phase1_network_preflight.py`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json"`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify_report.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - preflight 2連続PASS
  - summary `notes` に `auto_skipped_by_registry:1` を確認
  - `per_artist_counts=0`、新規画像保存0件（抽出実行なし）
  - 理由付きスキップを正式確定（01 6-2 準拠）
- 理由付きスキップ:
  - 理由: 公開HTML/DOM上で作品画像候補が取得不能。ドメイン専用if追加は 01 6-2 に抵触。
  - 再開条件: works画像URLの公開化、または汎用ロジックで再現可能な抽出要件の成立。
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T185628Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T185636Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T185732Z.json`

## 134. POLICY-UPDATE-ARTIST-GLOBAL-DEDUPE (01 4-0-A 方針変更の反映)
- 実施日時: 2026-02-28
- 変更方針（01 4-0-A）:
  - 旧: 同一フェア内の別ギャラリーで同一artistを再抽出しない
  - 新: Artist系抽出（artists_text / artist works images）で、全フェア・全ギャラリー横断の同一artist再抽出を禁止（自動スキップ）
  - 例外: ExhibitionsRAG のartist重複は許容（スキップしない）
- 実装:
  - `run_phase1_seed10.py`
    - artists_text 抽出で global dedupe を追加（`DUPLICATE_ARTIST_GLOBAL_EXISTING` / `DUPLICATE_ARTIST_GLOBAL_IN_RUN`）
    - summary に `artists_global_dedupe_*` / `artist_master_global_*` を追加
    - 出力のcp932落ち回避（stdout `backslashreplace`）を追加
  - `run_phase1_seed10_artist_image_collect.py`
    - `artist_master_global.json`（`data/phase1_seed10/logs/artist_master_global.json`）を導入
    - 既存 `artist_works_images_*.jsonl` から既知artistを読み込み、cross-fair/cross-gallery で自動スキップ
    - summary に `skipped_by_global_artist_dedupe*` と `artist_master_global_*` を追加
  - `docs/02_RAG_SPEC_DERIVED.md`
    - CARD 06 / CARD 16 に「全フェア横断artist重複禁止（ExhibitionsRAG除外）」を追記
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
    - 上記ポリシー更新と実装メモを追記

## 135. TASK 4-0-A-FAILED-RETRY-GATE-1 (image collect failed ledger + test override)
- 実施日時: 2026-02-28
- 目的:
  - 4-0-A の「一度見たもの（失敗）を永続化し、次回探索を抑制」を image collect 側でも実装。
  - ただしテスト段階で再検証不能にならないよう、強制再試行スイッチを追加。
- 変更:
  - `run_phase1_seed10_artist_image_collect.py`
    - 追加CLI: `--force-retry-failed`, `--clear-failed-ledger none|target|all`
    - 追加台帳: `data/phase1_seed10/logs/failed_fetches_artist_image_collect_2025.json`
    - failed URL 判定: `cooldown(3600s) + max_retries(3) + non-retryable reason`
    - summary 追加: `failed_fetches_*`, `force_retry_failed`, `clear_failed_ledger_scope`
  - `docs/02_RAG_SPEC_DERIVED.md`
    - CARD 16 に failed ledger + test override 運用を追記
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
    - 実装メモを追記
- 実行コマンド:
  - `python -m py_compile run_phase1_seed10_artist_image_collect.py`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name "Adams and Ollman" --clear-failed-ledger target --force-retry-failed --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_failed_ledger_gate_smoke.json"`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://www.ancapoterasu.com/artists/aurora-kiraly/" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_failed_ledger_verify_aurora.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - smoke summary で `force_retry_failed=true`, `clear_failed_ledger_scope=target` を確認。
  - aurora実測は `processed=1`, `ge_target=1` を維持し、`failed_fetches_*` 追加で回帰なし。
  - guard: `guard_passed=true`。

## 136. TASK MAX-ARTISTS-PER-GALLERY-3 (10ギャラリー再適用 / 既存成功保持)
- 実施日時: 2026-02-28
- 目的:
  - `{MAX_ARTISTS_PER_GALLERY}` を 3 に変更し、テスト10ギャラリーへ適用（skip 1件のため実質9ギャラリー運用）。
  - 既存成功画像は削除せず、追加分のみ抽出する。
- 変更:
  - `run_phase1_seed10.py`: `MAX_ARTISTS_PER_GALLERY = 3`
  - `run_phase1_seed10_artist_image_collect.py`: `MAX_ARTISTS_PER_GALLERY_FOR_COLLECT = 3`
- 実行コマンド:
  - `python run_phase1_network_preflight.py` (x2)
  - `python run_phase1_seed10.py`
  - `python run_phase1_seed10.py --include-artists-text`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_v2.json"`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_v2.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_v2_report.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - preflight 2連続 PASS
  - `processed=25`, `artists_with_ge_target_images=18`, `success_rate=72%`
  - `max_artists_per_gallery_for_collect=3`, `auto_skipped_by_registry:1`
  - skip対象: `Adams and Ollman`（抽出実行なし）
  - Arcadia Missa は raw artist 母数が1件のため `artists=1` のまま（`artists_frieze_london_2025.jsonl`）
  - guard: `guard_passed=true`

## 137. TASK A-REPRO-FIX-1 (再現性回復 第1段)
- 実施日時: 2026-02-28
- SSOT/DERIVED確認:
  - 01章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02 CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - 保存前 payload hash 重複ガードを追加（同一artist内の同一実体重複を最終除外）
    - token空 seed（例: `https://athrart.com/artists/30-/biography`）を抽出対象から除外
    - `--force-retry-failed` 時は `.../works` の page失敗を再評価（他の非再試行規則は維持）
    - metadata へ `works_image_payload_hashes` を追加
- 退避:
  - `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\_trash\task_a_repro_fix1_reset_20260228_124820\`
    - `athr__30__*` 5件
    - `gallery-baton__song-burnsoo__*` 5件
    - `a-works-of-art__chong-kim-chiew__*` 5件
    - `a-works-of-art__gan-chin-lee__*` 5件
  - 追加退避（再実測前）:
    - `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\_trash\task_a_repro_fix1_redo_20260228_125649\`
    - `song-burnsoo` 5件 / `chong-kim-chiew` 5件
- 実行コマンド:
  - `python run_phase1_network_preflight.py` x2
  - `python run_phase1_seed10.py --include-artists-text`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --force-retry-failed --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix1.json"`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix1.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix1_report.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - preflight 2連続PASS
  - `athr__30__*` は再生成されず（`skipped_invalid_artist_seed_count=1`）
  - Song Burnsoo: 5件ユニーク化（同一実体5連続重複を解消）
  - Chong Kim Chiew: 同一実体5連続重複を解消（3件ユニーク）
  - Gan Chin Lee: 再抽出0件（重複再生成なし）
  - `--force-retry-failed` で works URL 再評価を確認（`KNOWN_FAILED_URL_COOLDOWN` ではなく `html_fetch_failed ... 404` を記録）
  - guard: `guard_passed=true`

## 138. TASK A-REPRO-FIX-2 (候補落ち改善: artist一致性/works導線/画像variant)
- 実施日時: 2026-02-28
- 変更:
  - `run_phase1_seed10_artist_image_collect.py`
    - artist一致性の汎用緩和（artist配下ページで work情報信号を利用）
    - works URL抽出を artist配下優先に変更（`/artworks` `/publications` `/projects` の横流れ抑制）
    - 画像取得時に `tiny -> large/medium` variant を試行
    - 年抽出の次元値誤認識を抑制（`4000x2667` などを year から除外）
    - foreign person slug 検知を追加（他作家名らしき slug を緩和経路で除外）
- 実行:
  - `python run_phase1_network_preflight.py` x2
  - `python run_phase1_seed10.py --include-artists-text`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --force-retry-failed --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix2.json"`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix2.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix2_report.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - `processed=24`, `artists_with_ge_target_images=21`, `success_rate=87.5%`, `threshold_passed=true`
  - 改善確認:
    - The Approach: 3名すべて 5/5
    - Afriart: 3名すべて 5/5
    - Anca Poterașu: 3名すべて 5/5
  - 残課題:
    - A+ Works of Art: `Chong Kim Chiew=3/5`（要追加2件）
  - guard: `guard_passed=true`

## 139. TASK A-REPRO-FIX-3 (Gan混入起点の再現性修正)
- 実施日時: 2026-02-28
- 事象:
  - ユーザー指摘の `Gan Chin Lee` について、seed未存在ではなく `data/phase1_seed10/raw/artists_liste_2025.jsonl` に存在を確認。
  - 問題は「A+ Works / Gan の既存5枚が他作家混入」だったため、誤混入キャッシュを除去対象として扱う方針に変更。
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `--force-retry-failed` 時の failed URL 再評価を page種別へ拡張（works配下のみ再評価から拡張）。
    - artist一致判定に artist配下ページ（`/artists/...` 配下）の緩和を維持しつつ、URLの foreign person slug 排除を適用。
    - 既存メタ再利用時に、captionの foreign person name 検出を追加し他作家混入キャッシュを除外。
- データ補正:
  - 既存誤混入 `a-works-of-art__gan-chin-lee__*` 5件を `_trash/task_a_repro_fix3_gan_reset_manual/` に退避。
- 実行:
  - `python run_phase1_network_preflight.py` x2
  - `python run_phase1_seed10.py --include-artists-text`
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --force-retry-failed --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix3.json"`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix3.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix3_report.json"`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - preflight 2連続PASS。
  - 全体: `processed=24`, `ge_target=17`, `success_rate=70.83%`, `threshold_passed=true`。
  - A+ Works:
    - `Ahmad Fuad Osman=5/5`
    - `Chong Kim Chiew=3/5`（未達継続）
  - `Gan Chin Lee=0/5`（他作家混入5枚は除去済み、誤成功を停止）
  - guard: `guard_passed=true`

## 140. TASK A-REPRO-FIX-4 (A+ Works / Chong 3/5→5/5 補完)
- 実施日時: 2026-02-28
- SSOT/DERIVED確認:
  - 01章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02 CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
  - `docs/02_RAG_SPEC_DERIVED.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
- preflight:
  - `python run_phase1_network_preflight.py` x2 → 2連続PASS
- 実装:
  - `run_phase1_seed10_artist_image_collect.py`
    - `candidate_matches_artist` の foreign person slug 判定を過剰適用しないよう修正
    - `token_matches==0` かつ `evidence_text` が他人名と判定される場合のみ除外
- 再実測:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url https://aplusart.asia/artists/35-chong-kim-chiew --force-retry-failed --clear-failed-ledger target --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong.json`
  - 結果: `saved_images=3`, `target_met=false`, reason=`no_new_images_ge_max_year_seen`
- 切り分け結果（コード内関数で直接検証）:
  - works URL群: 5件
  - works-only + artist一致性の両方を満たす候補はサイズ違いを除くと正規化ユニーク3件のみ
  - 追加2件は、works-only条件内では新規ユニーク候補を確認できず
- 付随修正:
  - ユーザー指摘の `the-approach__tom-allen__...__img_03.jpg` 欠落は、前回 quarantine 起因を確認
  - `_trash/invalid_cached_images_20260228T051411Z/.../img_03.jpg` から本来パスへ復元済み
- 生成物:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260228T053620Z.json`

## 141. TASK A-REPRO-FIX-5 (Chong 5枚化可否の最終確定)
- 実施日時: 2026-02-28
- SSOT/DERIVED確認:
  - 01章ID: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02 CARD_ID: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- preflight:
  - `python run_phase1_network_preflight.py` x2 → PASS
- 実行:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url https://aplusart.asia/artists/35-chong-kim-chiew --force-retry-failed --clear-failed-ledger target --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix5_chong.json`
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix5_chong.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix5_chong_report.json`
  - `python run_compare_phase1_guard.py --target-year 2025`
- 結果:
  - `saved_images=3`, `target_met=false`, reason=`no_new_images_ge_max_year_seen`
  - works URLは5件確認済み
  - 追加監査で works-only + artist一致性を同時に満たす候補は正規化ユニーク3件のみ
- 最終判定（01:6-2準拠）:
  - domain専用ハードコード無しの汎用ロジック範囲では、Chongの5枚化は現時点で不可
  - 理由付き確定: `A+ Works / Chong Kim Chiew = 3/5（works-only source上限）`
  - 再開条件:
    - works配下に新規ユニーク作品画像が公開される
    - または 01の仕様変更で works-only 条件緩和が合意される

## 142. TASK A-REPRO-CHECK-ALL-1 (max=3 全体再計測 + 未達のみ再抽出対象化)
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10.py --include-artists-text` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
- 全体再計測結果:
  - `processed=24`, `artists_with_ge_target_images=17`, `success_rate=70.83%`, `threshold_passed=true`
  - `auto_skipped_by_registry:1`（`Adams and Ollman`）
  - 未達ギャラリー内訳:
    - `frieze_london/The Approach`: 0/3 達成（1,2,4枚）
    - `liste/A+ Works of Art`: 1/3 達成（5,3,0枚）
    - `liste/Amanita`: 1/3 達成（4,5,4枚）
- 未達のみ再抽出対象化:
  - 出力: `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`
  - 件数: 7
  - 対象:
    - The Approach: `phillip-allen`, `tom-allen`, `helene-appel`
    - A+ Works of Art: `chong-kim-chiew`, `gan-chin-lee`
    - Amanita: `eva-beresin`, `nicholas-campbell`
- 事後補正（2026-02-28）:
  - 本タスク実行時、`run_phase1_seed10.py` と image collect を並列実行してしまい、The Approach の判定値が崩れた（競合）。
  - 影響: `the-approach__tom-allen__72951a84__img_05.jpg` が `_trash/invalid_cached_images_20260228T061552Z/...` へ誤退避。
  - 復旧: 上記 `img_05` を元パスへ復元し、Tom は再度 5枚状態へ回復。
  - 修正方針: 同一領域を触る `run_phase1_seed10.py` と `run_phase1_seed10_artist_image_collect.py` は今後並列実行しない。
  - 再抽出対象CSVを補正し、The Approach 3件を除外。現行の対象は A+ Works 2件 + Amanita 2件（計4件）。
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T061444Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T061444Z_01.json`
  - `data/phase1_seed10/logs/run_summary_seed10_2025.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260228T062247Z.json`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 143. TASK A-REPRO-TRIAGE-2（未達5件の原因分類確定 + 再抽出対象最小化）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 変更対象とルールの1対1紐付け:
  - `run_phase1_seed10_artist_image_collect.py`: 既存監査ログで分類可能か検証（変更不要） <- 01:4-0-A/6-3/10, 02:14/16
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`: 未達再抽出対象の最小化 <- 01:6-2/10, 02:16
  - `docs/03,04,RAG`: 判定根拠・次FIX入力の記録 <- 01:10, 02:16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - 分析入力固定:
    - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json`
    - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1_report.json`
    - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260228T062247Z.json`
- 原因分類（5件）:
  - Arcadia Missa 0/5 #1 -> `SEED_INVALID`
    - 根拠: `gallery_breakdown.artist_count=1`（fixed summary）、Arcadia failed_cases 0件
  - Arcadia Missa 0/5 #2 -> `SEED_INVALID`
    - 根拠: 同上（max=3想定の追加2枠に対応するseedが固定summaryに存在しない）
  - Athr 0/5（`https://athrart.com/artists/30-/biography`） -> `SEED_INVALID`
    - 根拠: `skipped_invalid_artist_seed.reason_code=invalid_artist_seed_token_empty`
  - A+ Works 0/5（Gan） -> `ARTIST_CONSISTENCY_FILTERED_ALL`
    - 根拠: failed_case `works_candidates_count:27` / `artist_consistency_filtered:27` / `works_only_artist_match_unique:0`
  - A+ Works 3/5（Chong） -> `NO_NEW_IMAGES_GE_MAX_YEAR_SEEN`
    - 根拠: failed_case `reason=no_new_images_ge_max_year_seen`、`works_only_artist_match_unique_count=3`
- 再抽出対象CSVの最小化:
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`
  - 除外: Arcadia 2件（seed不在）, Athr 1件（seed不正）, Chong 1件（上限確定）
  - 残存: `A+ Works / Gan Chin Lee` 1件のみ
- 実装差分:
  - `run_phase1_seed10_artist_image_collect.py` は変更なし（固定summary内の既存監査項目で分類に十分）
- 生成物:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T064558Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260228T064611Z.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_triage_task_a_repro_triage_2.json`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 144. TASK A-REPRO-FIX-7（A+ Works / Gan 0/5 再修正・再実測）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/41-gan-chin-lee" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix7_gan.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix7_gan.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix7_gan_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
- 退避:
  - src=`data/phase1_seed10/derived/images/artist_works_images/2025/liste/a-works-of-art__gan-chin-lee__*`
  - dst=`_trash/task_a_repro_fix7_gan_reset_20260228_163555/`
  - moved=0 / remaining=0
- 実装差分:
  - `run_phase1_seed10_artist_image_collect.py`
    - `candidate_matches_artist` に compact alnum fallback を追加（汎用の記法ゆれ吸収）
- 結果:
  - `saved_images=0/5`, `target_met=false`
  - `reason=insufficient_image_candidates_after_download`
  - 根拠: `works_candidates_count:27` / `artist_consistency_filtered:27` / `works_only_artist_match_unique:0`
- 判定（01 6-2準拠）:
  - works-only 公開面で Gan 一致候補が現時点0件のため未達確定（暫定）
  - 再開条件: works配下のGan一致情報追加、または01仕様変更
- 更新ファイル:
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 145. TASK A-REPRO-FIX-8（A+ Works / Gan seed根拠再監査 + works-only整合維持の最小修正）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- 実行コマンドとexit:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/41-gan-chin-lee" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix8_gan.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix8_gan.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix8_gan_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
- 実装差分:
  - `run_phase1_seed10_artist_image_collect.py`
    - `is_redirected_to_generic_listing()` を追加
    - `fetch_html_with_playwright` / `fetch_html` で artist詳細URLが `/artists/` へ収束した場合を失敗化
    - case reason を `seed_invalid_redirected_to_listing` で確定できるよう修正
- 監査結果:
  - `https://aplusart.asia/artists/41-gan-chin-lee` は実アクセスで `https://aplusart.asia/artists/` へ遷移
  - summary:
    - `reason=seed_invalid_redirected_to_listing`
    - `notes` に `html_redirected_to_generic_listing:aplusart.asia:/artists/` を記録
    - `saved_images=0/5`
- 判定（01 6-2準拠）:
  - Gan未達は artist一致性ロジックではなく seed URL無効が主因
  - 再開条件: A+ Works 側で Gan の有効詳細URLを再取得できること
- 更新ファイル:
  - `run_phase1_seed10_artist_image_collect.py`
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 146. TASK A-REPRO-FIX-9（Gan有効source_url再解決→単独再実測）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- preflight:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
- seed再解決:
  - `https://aplusart.asia/artists/` のartist導線を再収集
  - Ganの候補は `https://aplusart.asia/artists/41-gan-chin-lee/` のみ（sitemap由来）
  - 実アクセス確認: 上記URLは `https://aplusart.asia/artists/` へ302（有効詳細URLなし）
  - `data/phase1_seed10/raw/artists_liste_2025.jsonl` のGan行 `source_url` を canonical（末尾`/`）へ更新（重複行追加なし）
- 実行コマンドとexit:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/41-gan-chin-lee/" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
- 結果:
  - `reason=seed_invalid_redirected_to_listing`
  - `saved_images=0/5`, `target_met=false`
  - `notes` に `html_redirected_to_generic_listing:aplusart.asia:/artists/` を記録
- 判定（01 6-2準拠）:
  - 有効source_url再解決は未達（導線上にGan詳細URLなし）
  - 次は artists raw再生成で seed再供給を先行
- 更新ファイル:
  - `data/phase1_seed10/raw/artists_liste_2025.jsonl`
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 147. TASK A-REPRO-FIX-10（A+ Works artists raw再生成→Gan seed再供給→単独再実測）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- preflight:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
- raw再生成:
  - `python run_phase1_seed10.py --include-artists-text` -> exit 0
  - 結果: artistsは `saved=0`, `skipped=26`（`DUPLICATE_TEXT_HASH_EXISTING=24`, `KNOWN_FAILED_URL_NON_RETRYABLE=2`）
- Gan seed再供給監査:
  - artists導線 `https://aplusart.asia/artists/` からGan有効詳細URLの再解決を試行
  - sitemapにも Gan URL は存在するが、`https://aplusart.asia/artists/41-gan-chin-lee/` は実アクセスで `/artists/` へ302
  - 有効source_url未解消のため、Gan行は canonical URL（末尾`/`）で維持
- 単独再実測:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url "https://aplusart.asia/artists/41-gan-chin-lee/" --force-retry-failed --clear-failed-ledger target --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan.json"` -> exit 0
  - `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan_report.json"` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
- 結果:
  - `reason=seed_invalid_redirected_to_listing`
  - `saved_images=0/5`, `target_met=false`
  - `notes`: `html_redirected_to_generic_listing:aplusart.asia:/artists/`
- 判定（01 6-2準拠）:
  - FIX-10時点では有効seed再供給に未達（サイト側導線でGan詳細URLが失効）
  - 再開条件: Gan詳細URLの復活、または seed供給元の更新ロジック実装
- 更新ファイル:
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`

## 148. TASK A-REPRO-FIX-11（Arcadia/Athr の 0枚枠を seed補正のみで解消）
- 実施日時:
  - 2026-02-28
- SSOT整合ゲート（実装前確認）:
  - 01章ID: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
  - 02 CARD_ID: 10 / 11 / 14 / 16
- 事前確認:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` / `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` / `docs/04_TASK_PROGRESS_LOG.md` の存在OK
- preflight:
  - `python run_phase1_network_preflight.py` -> exit 0
  - `python run_phase1_network_preflight.py` -> exit 0
- seed監査:
  - `artists_frieze_london_2025.jsonl`:
    - Arcadia seed数: 1（Bradのみ）
    - Athr token空seed: 複数残存（`/artists/<id>-/biography`）
  - `phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json`:
    - Arcadia 2枠: `SEED_INVALID`
    - Athr 1枠: `SEED_INVALID`
- seed補正（最小）:
  - Arcadia:
    - `https://arcadiamissa.com/hannah-black/` 追加
    - `https://arcadiamissa.com/jesse-darling/` 追加
  - Athr:
    - `30-/biography` -> `30-ahaad-alamoudi/biography/`
    - `35-/biography` -> `35-mohammad-alfaraj/biography/`
    - `36-/biography` -> `36-zahrah-alghamdi/biography/`
    - `40-/biography` -> `40-ayman-yossri-daydban/biography/`
- 単独再実測（0枚枠のみ）:
  - Arcadia 追加候補1 `hannah-black` -> `saved_images=5/5`, `target_met=true`
  - Arcadia 追加候補2 `jesse-darling` -> `saved_images=5/5`, `target_met=true`
  - Athr 置換候補1 `ahaad-alamoudi` -> `saved_images=5/5`, `target_met=true`
  - 3ケースとも `failed_cases=[]`
- report/guard:
  - report 3本生成 -> 全て exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 / `guard_passed=true`
- 判定:
  - Arcadia/Athr の 0枚枠は seed補正のみで解消（ロジック改修不要）
- 更新ファイル:
  - `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl`
  - `docs/RAG_EXTRACTION_BREAKDOWN_JA.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`
  - `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`


## 149. TASK MAX5-ROLLUP (2026-02-28 10:06:08Z)
- SSOT??: 01(4-0,4-4,5-4,6-2,6-3,10) / 02(CARD 10,11,14,16) / 03 / 04
- ??:
  - run_phase1_seed10.py: MAX_ARTISTS_PER_GALLERY 3 -> 5
  - run_phase1_seed10_artist_image_collect.py: MAX_ARTISTS_PER_GALLERY_FOR_COLLECT 3 -> 5
  - run_phase1_seed10_artist_image_collect.py: works404 fallback?? / dedupe / index?????????
- preflight:
  - python run_phase1_network_preflight.py -> exit 0 (2?PASS)
- ???:
  - python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --force-retry-failed --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_all_20260228.json -> exit 0
- report/guard:
  - python run_phase1_seed10_artist_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_all_20260228.json --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_all_20260228_report.json -> exit 0
  - python run_compare_phase1_guard.py --target-year 2025 -> exit 0 (guard_passed=true)
- ??:
  - processed=43, ge_target=32, success_rate=74.42%
  - gallery breakdown: Arcadia 100%, Athr 100%, Gallery Baton 100%, The Approach 0%, A+ Works 20%, Addis 100%, Afriart 100%, Amanita 60%, Anca 100%
- ??:
  - ??????????????
  - Adams and Ollman ? skip registry ??? auto-skip?


## 150. TASK MAX5-STABILITY-1 (2026-02-28 10:46:02Z)
- ??: 01(4-0,4-0-A,4-4,5-4,6-2,6-3,10) / 02(CARD 10,11,14,16) / 03 / 04
- ??????:
  - `run_phase1_seed10_artist_image_collect.py`
    - orphan??? `_trash/orphan_artist_images_<ts>/...` ???????cleaner??
    - works 404 ?? detail fallback ??? lenient artist match ????????if???
    - seed_supply_by_gallery / seed_supply_under_cap ? summary???
    - ??metadata????? local_path ?????
  - `run_phase1_seed10_artist_image_collect_report.py`
    - seed?????cap???? report/breakdown ???
- preflight:
  - `python run_phase1_network_preflight.py` x2 -> PASS
- ????:
  - The Approach
    - `python run_phase1_seed10_artist_image_collect.py ... --only-gallery-name "The Approach" ...` -> exit 0
    - result: processed=5 / ge_target=2 / images=17
  - Arcadia Missa
    - `... --only-gallery-name "Arcadia Missa" ...` -> exit 0
    - result: processed=3 / ge_target=3 / images=15
  - A+ Works of Art
    - `... --only-gallery-name "A+ Works of Art" ...` -> exit 0
    - result: processed=5 / ge_target=1 / images=9
  - report 3? + `python run_compare_phase1_guard.py --target-year 2025` -> guard_passed=true
- ??:
  - Tom Allen ? payload???3??????????orphan cleanup ???????????
  - Arcadia ??????? seed?????3/5?????????


## TASK THE-APPROACH-REFETCH-FIX-1 (2026-02-28)
- 目的: The Approachでtom/phillipが全体実行時に再低下する再現性崩れを、汎用ロジックのみで修正。
- 実装: run_phase1_seed10_artist_image_collect.py に metadata不足時の再fetch条件を追加。
- 実測: preflight PASS後、tom=5/5, phillip=5/5、さらにThe Approach全体5名で5/5達成。
- 判定: 個別ifなしで回復。guard_passed=true。


## TASK MAX5-UNRESOLVED-1 (2026-02-28)
- 参照: 01(4-0,4-0-A,4-4,5-4,6-2,6-3,10) / 02(CARD 10,11,14,16) / 03 / 04
- preflight: 2連続PASS
- 入力summary: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_all_20260228.json
- 再抽出CSV: data/gallery_lists/reextract_targets_task_max5_unresolved_1.csv
  - 最小化結果: 3件（A+ Worksのみ）
  - 除外: skip registry登録済み / The Approachは回復確認済み / Amanita 4枚許容
- 再抽出実行（1件=1artist）:
  - Gan Chin Lee: 0/5（seed_invalid_redirected_to_listing）
  - Ha Ninh Pham: 1/5（insufficient_image_candidates_after_download）
  - Ho Rui An: 0/5（insufficient_image_candidates_after_download）
- 統合summary: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_unresolved_1.json
- report/guard:
  - report: ..._task_max5_unresolved_1_report.json
  - guard: phase1_guard_summary_2025_20260228T112231Z.json (guard_passed=true)
- 判定: 未達件数は減少せず。A+ Worksのseed/導線側課題として継続。


## TASK MAX5-CLOSE-GATE-1 (2026-02-28)
- 参照: 01(4-0,4-0-A,4-4,5-4,6-2,6-3,10) / 02(CARD 10,11,14,16) / 03 / 04
- preflight: 2連続PASS
- 固定入力:
  - max5_all: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_all_20260228.json
  - unresolved: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_unresolved_1.json
  - unresolved_report: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max5_unresolved_1_report.json
  - reextract_csv: data/gallery_lists/reextract_targets_task_max5_unresolved_1.csv
- 判定:
  - Arcadia Missa: detail_seed_total=3 / configured_cap=5 -> closed_supply_cap（供給上限確定）
  - A+ Works:
    - Gan: seed_invalid_redirected_to_listing 連続継続 -> closed_seed_invalid
    - Ha Ninh / Ho Rui An: insufficient_image_candidates_after_download 連続継続 -> closed_candidate_limit
- 反映:
  - reextract csv reason_code を closed_* へ更新し凍結
  - skip registry は未更新（gallery丸ごとskip扱いにしないため）
- 補助出力: data/phase1_seed10/logs/phase1_seed10_max5_close_gate_1_decision.json


## TASK MAX80-RUN-ALL-1 (2026-02-28)
- 参照: 01(4-0,4-0-A,4-4,5-4,6-2,6-3,10) / 02(CARD 10,11,14,16) / 03 / 04
- 設定変更:
  - run_phase1_seed10.py: MAX_ARTISTS_PER_GALLERY=80
  - run_phase1_seed10_artist_image_collect.py: MAX_ARTISTS_PER_GALLERY_FOR_COLLECT=80
- preflight: 2連続PASS
- 実行:
  - python run_phase1_seed10.py --include-artists-text
  - python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --force-retry-failed --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_max80_all_20260228.json
  - python run_phase1_seed10_artist_image_collect_report.py --summary-path ...task_max80_all_20260228.json --output-json ...task_max80_all_20260228_report.json
  - python run_compare_phase1_guard.py --target-year 2025
- 結果:
  - processed=180 / ge_target=145 / success_rate=80.56% / threshold_passed=true
  - gallery: Athr 100%, Gallery Baton 100%, The Approach 100%, Addis 73.91%, Afriart 93.33%, Amanita 64.29%, Anca 87.5%, A+ Works 25.0%
  - skip反映: Adams and Ollman / Arcadia Missa は抽出対象0（自動スキップ）
  - guard_passed=true

## TASK T-107-ARTISTS-TEXT (2026-02-28)
- 参照: 01(4-0,4-0-A,4-2,5-3,5-8,6-2,6-3,10) / 02(CARD 05,14,15,16) / 03 / 04
- 初回最小化方針: `run_phase1_seed10.py` に `--max-artists-per-gallery` を追加し、初回は `1` で実行
- 共通スキップ対応: `data/gallery_lists/skipped_galleries_registry.csv` を `run_phase1_seed10.py` で読み込み、seed10対象へ事前適用
- 実行:
  - `python run_phase1_network_preflight.py` x2 -> PASS
  - `python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 1` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=true`)
  - `python run_phase1_seed10_r2_sync.py --scope raw --dry-run --prune` -> exit 0
  - `python run_phase1_seed10_r2_sync.py --scope raw --prune --require-dry-run-log --max-prune 600` -> exit 0
- 結果:
  - skip_registry applied: before=10, after=8, skipped=2
  - `max_artists_per_gallery=1`
  - artists_text: `artists_records_saved_total=0` / `artists_existing_records_total=225` / `artists_skipped_total=8`（既存重複）
  - R2同期: auto-sync `phase1_all status=ok`、手動raw同期 `uploaded=0 / skipped=6 / pruned=0`

## TASK T-107-ARTISTS-TEXT-FOLLOWUP (2026-02-28)
- 原因修正:
  - `run_phase1_seed10.py` で `max-artists-per-gallery` の適用位置を修正
  - 変更前: 候補URL抽出段階でcap適用（既存重複に当たると新規0になりやすい）
  - 変更後: 候補は広めに走査し、保存成功件数でcap適用
- 再実測:
  - `python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=true`)
- 結果:
  - artists_text 新規 +4
    - The Approach: +3（Rezi Van Lankveld / John Maclean / Hana Miletic）
    - Gallery Baton: +1（Germaine Kruip）
  - `total_artist_text_records=232`（run後）


## 151. TASK T-108-ARTISTS-TEXT-CLOSE-2????????????
- ?????:
  - 01/02/03/04 ?????OK
  - preflight 2??PASS?`phase1_network_preflight_summary_20260301T042809Z.json`?
- ??????:
  - `phase1_artist_link_utils.py` ? text/image ?????????
  - `python -m py_compile phase1_artist_link_utils.py run_phase1_seed10.py run_phase1_seed10_artist_image_collect.py` PASS
- Arcadia/Adams ????:
  - candidates: Arcadia=18, Adams=20?????>=5?????
  - `data/gallery_lists/skipped_galleries_registry.csv` ??2????backup: `...bak_20260301_132907`?
- ??:
  - 1?? `run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` ? `KNOWN_FAILED_URL_NON_RETRYABLE`???????????
  - `failed_fetches_artists_seed10_2025.json` ? Arcadia/Adams ???2?????backup: `...bak_20260301_134210`?
  - 2?????????????`artists_records_saved_total=42` ????Arcadia=18, Adams=20????
- guard:

## 152. TASK108完了反映（タスク終了テンプレ運用固定）
- 03の `NEXT_TASKS` で `108)` を `[x]` に更新し、完了実行内容を追記。
- TASKプロンプト末尾の出力テンプレを「【タスク終了時に行うこと】」へ統一（03更新: 02→01→03 を先行実施）。
- 01/02/04 に同運用を追記し、今後のタスク終了時に恒久適用する。

## 153. TASK T-109-ARTISTS-TEXT-COVERAGE-70-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - summary: `phase1_network_preflight_summary_20260301T070641Z.json` / `...070651Z.json`
- 実行:
  - `python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80` -> exit 0
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`guard_passed=true`)
- coverage分析:
  - 生成: `data/gallery_lists/reextract_targets_artists_text_task_t109.csv`
  - 全体: `data/gallery_lists/reextract_targets_artists_text_task_t109_all_coverage.csv`
  - 結果: 10ギャラリー中 7ギャラリーが `coverage>=0.70`（70.00%）
  - 未達3件: Athr(0.4359), A+ Works of Art(0.6364), Addis Fine Art(0.6757)
  - 主因: `DUPLICATE_TEXT_HASH_EXISTING`（重複除外による保存抑制）
- R2:
  - `python run_phase1_seed10_r2_sync.py --scope raw --dry-run --prune` -> exit 0
  - `python run_phase1_seed10_r2_sync.py --scope raw --prune --require-dry-run-log --max-prune 600` -> exit 0
  - apply結果: uploaded=0 / skipped=6 / pruned=0（manifestのみ更新）

## 154. TASK T-110-ARTISTS-TEXT-UNMET-ROOTCAUSE-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T073501Z.json`
  - `phase1_network_preflight_summary_20260301T073513Z.json`
- 根因分類（未達3件）:
  - Athr: `DUPLICATE_TEXT_HASH_EXISTING=26`, `DUPLICATE_ARTIST_GLOBAL_EXISTING=6`, `DUPLICATE_ARTIST_GLOBAL_IN_RUN=5`
  - A+ Works of Art: `DUPLICATE_TEXT_HASH_EXISTING=28`, `DUPLICATE_ARTIST_GLOBAL_IN_RUN=13`, `DUPLICATE_ARTIST_GLOBAL_EXISTING=3`
  - Addis Fine Art: `DUPLICATE_TEXT_HASH_EXISTING=25`, `DUPLICATE_ARTIST_GLOBAL_IN_RUN=9`, `DUPLICATE_ARTIST_GLOBAL_EXISTING=3`
  - ラベル確定: 3件とも `DUPLICATE_TEXT_HASH_DOMINANT`
- 判定:
  - 追加改修は見送り（6-2準拠）
  - 理由: 改修候補は重複除外ポリシーの仕様変更を伴い、リンク共通モジュール範囲外
  - 再開条件: SSOTで artist_text 重複除外ポリシー（text_hash粒度）変更の合意が出た場合のみ
- 反映:
  - `data/gallery_lists/reextract_targets_artists_text_task_t109.csv` の reason を `closed_duplicate_text_hash_dominant` へ更新
  - guard: `python run_compare_phase1_guard.py --target-year 2025` -> exit 0 (`phase1_guard_summary_2025_20260301T073600Z.json`)
  - `phase1_guard_summary_2025_20260301T044222Z.json` / guard_passed=true
- R2:
  - `run_phase1_seed10_r2_sync.py --scope raw --dry-run --prune` ??
  - ?????? guard fail ??????? `--prune --require-dry-run-log --max-prune 600` ???
- ??:
  - Arcadia/Adams status = reopened???: candidates>=5 + ???????
  - 70%???????????????????

## 155. TASK ADAMS-IMAGE-DEDUP-RETEST-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T081919Z.json`
  - `phase1_network_preflight_summary_20260301T081919Z_01.json`
- 実装（汎用のみ）:
  - `run_phase1_seed10_artist_image_collect.py`
  - `normalize_image_url_for_dedupe()` に Cargo系変換パスの正規化を追加
    - `/w/<size>/...` と `/t/original/...` を同一元画像として扱う
- 退避:
  - `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*.jpg`
  - `_trash/task_adams_dedupe_fix_20260301_172123/` へ10件移動
- 単独再実測（Adamsのみ）:
  - Jonathan Berger: `saved_images=0/5`（`works_candidates_count:0`）
  - Jose Bonell: `saved_images=5/5`（重複なし）
  - Katherine Bradford: `saved_images=5/5`（重複なし）
- 証跡:
  - summary:
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_jonathan_berger.json`
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_jose_bonell.json`
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_katherine_bradford.json`
  - report:
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_jonathan_berger_report.json`
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_jose_bonell_report.json`
    - `phase1_seed10_artist_image_collect_summary_task_adams_retest_katherine_bradford_report.json`
  - guard:
    - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
  - `phase1_guard_summary_2025_20260301T082640Z.json` / `guard_passed=true`

## 156. TASK ADAMS-AUTO3-SEED-CLEANUP-1
- 背景:
  - `Jonathan-Berger-1` は自動抽出ではなく、rawに残っていた手動seed（`Artist page seed for ...`）由来と判明。
- 対応:
  - `run_phase1_seed10_artist_image_collect.py`
    - `load_artist_targets()` / `collect_seed_supply_by_gallery()` で手動seed marker行を汎用除外。
  - raw cleanup:
    - `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl`
    - backup: `artists_frieze_london_2025.jsonl.bak_20260301_173725`
    - 手動seed 4行を除去。
- Adams 自動3名（固定指定なし）:
  - 抽出対象（先頭3）: Jose Bonell 2 / Katherine Bradford / Mariel Capanna 1
  - Jose: 3/5（重複なし、未達）
  - Katherine: 5/5（重複なし）
  - Mariel: 5/5（重複なし）
- 証跡:
  - `phase1_seed10_artist_image_collect_summary_task_adams_auto3_jose.json`
  - `phase1_seed10_artist_image_collect_summary_task_adams_auto3_katherine.json`
  - `phase1_seed10_artist_image_collect_summary_task_adams_auto3_mariel.json`
  - guard: `phase1_guard_summary_2025_20260301T084032Z.json` (`guard_passed=true`)

## 157. TASK REPRO-ALL10x1-THEN-MAX80-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T090923Z_01.json`
  - `phase1_network_preflight_summary_20260301T090923Z.json`
- Step1（回帰テスト最小化）:
  - `data/gallery_lists/reextract_targets_repro_all10x1.csv` を自動生成（10ギャラリー×各1名）
  - 各対象の既存5枚を `_trash/task_repro_all10x1_20260301_181032/` へ退避
  - 各1名を単独再抽出（`--force-retry-failed --clear-failed-ledger target`）
  - rollup: `phase1_seed10_artist_image_collect_summary_task_repro_all10x1_rollup_20260301_181032.json`
  - 判定: 10/10 で `saved_images=5` / `target_met=true` / `unique_stems=5/5`
- Step2（MAX80全体）:
  - `phase1_seed10_artist_image_collect_summary_task_repro_all10x1_then_max80_all.json`
  - 結果: processed=225 / ge_target=184 / success_rate=81.78% / threshold_passed=true
  - Arcadia Missa: ge_target=18/18 (100.0%)
  - Adams and Ollman: ge_target=18/20 (90.0%)
  - A+ Works of Art: ge_target=7/28 (25.0%)（横ばい）
- report/guard:
  - report: `phase1_seed10_artist_image_collect_summary_task_repro_all10x1_then_max80_all_report.json`
  - guard: `phase1_guard_summary_2025_20260301T095934Z.json` (`guard_passed=true`)

## 158. TASK ARTISTS-IMAGE-CLOSE-1
- 運用確定: `data/gallery_lists/skipped_galleries_registry.csv` を 0件（空）に設定。
- 判定: Artists画像RAG抽出（10ギャラリー、MAX80、現行汎用コード）は本テストで完成扱い。

## 159. TASK RAG-BREAKDOWN-JA-RULE-1
- 共通ルール更新（01/02/03/04整合）:
  - RAG抽出の内訳記録は `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` に集約する。
  - 上記内訳は日本語で記述する（英語のみ記載は禁止）。
  - この日本語内訳ルールは全RAGカテゴリ（Artists/Exhibitions/Tarutani、画像/テキスト/ベクター、同期）へ常時適用する。
- 反映先:
  - `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
  - `docs/02_RAG_SPEC_DERIVED.md`
  - `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
  - `docs/04_TASK_PROGRESS_LOG.md`

## 160. TASK T-111-ARTISTS-TEXT-CANONICAL-DEDUPE-REGRESSION-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T114537Z.json`
  - `phase1_network_preflight_summary_20260301T114538Z.json`
- 事前分析（未達3件 baseline）:
  - coverage: Athr `17/39`, A+ Works `28/44`, Addis `25/37`
  - `DUPLICATE_TEXT_HASH_EXISTING`: Athr=26 / A+ Works=28 / Addis=25
- 実装（汎用のみ）:
  - `phase1_artist_link_utils.py`
    - `canonicalize_artist_detail_url()` 追加
    - `score_artist_detail_url_quality()` 追加
  - `run_phase1_seed10.py`
    - Artists候補URLの重複整理を canonical 基準へ更新
    - known/saved 判定を「従来hash + canonical hash」互換へ更新
    - `text_hash` 重複除外ポリシーは変更なし
- 構文確認:
  - `python -m py_compile phase1_artist_link_utils.py run_phase1_seed10.py` -> exit 0
- 最小回帰テスト:
  - 退避: `_trash/task_t111_artists_text_regression_20260301_204859/`
  - 実行: `python run_phase1_seed10.py --include-artists-text --max-artists-per-gallery 80`
  - guard: `phase1_guard_summary_2025_20260301T122227Z.json` (`guard_passed=true`)
- 判定:
  - 未達3件の coverage は同値維持（低下なし）
    - Athr `17/39`, A+ Works `28/44`, Addis `25/37`
  - 改善は限定的（重複主因が `text_hash` ポリシー領域のため）
- R2:
  - dry-run: `phase1_seed10_r2_sync_raw_20260301T122355Z.json`
  - apply: `phase1_seed10_r2_sync_raw_20260301T122420Z.json`（uploaded=2, skipped=5, pruned=0）

## 161. TASK T-112-EXHIBITIONS-IMAGE-BOOTSTRAP-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T124423Z_01.json`
  - `phase1_network_preflight_summary_20260301T124423Z.json`
- 実装（汎用のみ）:
  - `run_phase1_seed10_exhibition_image_collect.py` を追加（Exhibitions画像収集）
  - `run_phase1_seed10_exhibition_image_collect_report.py` を追加（summaryレポート）
  - 共通流用: `run_phase1_seed10_artist_image_collect.py` の URL正規化/画像候補抽出/重複除外/画像正規化を再利用
- 最小スコープ実測:
  - 対象: `liste / A+ Works of Art / https://aplusart.asia/exhibitions/110-after-all-we-carry-solo-exhibition-by-sarah-radzi`
  - 結果: `saved_images=5/5`, `target_met=true`, `hero/profile/logo` 混入0, 重複0
  - summary: `phase1_seed10_exhibition_image_collect_summary_task_t112_bootstrap.json`
  - report: `phase1_seed10_exhibition_image_collect_summary_task_t112_bootstrap_report.json`
- 修正（同タスク内）:
  - 拡張子命名の不整合（`..jpg`）を修正（`.jpg` へ統一）
  - 旧誤命名5枚を `_trash/task_t112_fix_ext_20260301_125450/` へ退避
  - `data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl` を再生成（backup: `.bak_20260301_t112_extfix`）
- guard:
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
  - `phase1_guard_summary_2025_20260301T125846Z.json`（`guard_passed=true`）
- R2同期（derived）:
  - dry-run: `phase1_seed10_r2_sync_derived_20260301T125542Z.json`
  - apply: `phase1_seed10_r2_sync_derived_20260301T125828Z.json`（uploaded=7, skipped=995, pruned=5, failed=0）

## 162. TASK T-113-EXHIBITIONS-IMAGE-COVERAGE-10G-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T130604Z_01.json`
  - `phase1_network_preflight_summary_20260301T130604Z.json`
- 対象CSV作成:
  - `data/gallery_lists/reextract_targets_exhibitions_image_task_t113.csv`
  - 内容: 10ギャラリー×各1exhibition（skip registry反映）
- 実行:
  - `python run_phase1_seed10_exhibition_image_collect.py --target-year 2025 --target-images-per-exhibition 5 --targets-csv data/gallery_lists/reextract_targets_exhibitions_image_task_t113.csv --output-json data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t113_min10x1.json`
  - `python run_phase1_seed10_exhibition_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t113_min10x1.json --output-json data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t113_min10x1_report.json`
- 実測結果:
  - `seed=10`, `ge1=10`, `ge_target=8`, `saved_images_total=42`
  - 抽出0件ギャラリー: 0
  - hero/profile/logo 混入件数: 0
  - 重複保存件数（URL/payload）: 0/0
- guard:
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
  - `phase1_guard_summary_2025_20260301T131452Z.json`（`guard_passed=true`）
- R2同期（derived）:
  - dry-run: `phase1_seed10_r2_sync_derived_20260301T131504Z.json`
  - apply: `phase1_seed10_r2_sync_derived_20260301T131849Z.json`（uploaded=44, skipped=1001, pruned=0, failed=0）

## 163. TASK T-114-EXHIBITIONS-IMAGE-EXPAND-10G-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T133030Z.json`
- 対象CSV作成:
  - `data/gallery_lists/reextract_targets_exhibitions_image_task_t114.csv`
  - 生成条件: 10ギャラリー対象、各ギャラリー最大5 exhibition、5/5達成済みsource_urlを除外、skip registry反映
  - 初期件数: 36件
- 実装:
  - `run_phase1_seed10_exhibition_image_collect.py` に `--targets-csv` 入力を追加
  - ファイル名長による保存失敗回避として exhibition slug 上限を短縮（`max_len=48`）
- 実行:
  - collect:
    - `python run_phase1_seed10_exhibition_image_collect.py --target-year 2025 --target-images-per-exhibition 5 --targets-csv data/gallery_lists/reextract_targets_exhibitions_image_task_t114.csv --output-json data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t114_expand.json`
  - report:
    - `python run_phase1_seed10_exhibition_image_collect_report.py --summary-path data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t114_expand.json --output-json data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t114_expand_report.json`
- 実測結果:
  - `seed=36`, `ge1=28`, `ge_target=16`, `saved_images_total=103`
  - `ge_1率=0.777778`, `ge_target率=0.444444`
  - 抽出0件ギャラリー: 1
  - hero/profile/logo混入件数: 0
  - 重複保存件数: URL=0 / payload=0
- 運用整形:
  - `reextract_targets_exhibitions_image_task_t114.csv` を「未達のみ」に再生成
  - 最終件数: 20件
- guard:
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
  - `phase1_guard_summary_2025_20260301T134852Z.json`（`guard_passed=true`）
- R2同期（derived）:
  - dry-run: `phase1_seed10_r2_sync_derived_20260301T134924Z.json`
  - apply: `phase1_seed10_r2_sync_derived_20260301T135502Z.json`（uploaded=146, skipped=1043, pruned=0, failed=0）

## 164. FIX EXHIBITIONS_IMAGE_PER_EXHIBITION_MAX=1（SSOT是正）
- 背景:
  - SSOT 01（4-2/5-2）で `EXHIBITION_IMAGE_PER_EXHIBITION_MAX=1` が明記されているにも関わらず、collector既定値が5だった。
- 実装修正:
  - `run_phase1_seed10_exhibition_image_collect.py`
    - `--target-images-per-exhibition` 既定を `1` に変更
    - 実行時に常に `1` へ強制（引数で5を指定してもSSOT優先で1）
- 既存データ是正:
  - `data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl`
  - `data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl`
  - source_url単位で1件へ正規化（frieze: 128→20 / liste: 104→24）
  - 余剰画像を `_trash/task_exhibition_one_image_enforce_20260301_232524/` へ退避
  - 正規化後の整合: metadata 44件 / 実ファイル44件 / 欠損参照0
- 追加再補完:
  - 欠損行6件を除去後、`reextract_targets_exhibitions_image_missing_fix.csv` で再収集
  - `phase1_seed10_exhibition_image_collect_summary_task_fix_exhibition_one_image_missing_refill.json`（seed=6, ge1=6, saved=6）
- 検証:
  - guard: `phase1_guard_summary_2025_20260301T142922Z.json`（`guard_passed=true`）
- R2同期（derived）:
  - dry-run: `phase1_seed10_r2_sync_derived_20260301T142948Z.json`
  - apply: `phase1_seed10_r2_sync_derived_20260301T143256Z.json`（uploaded=12, pruned=147, failed=0）

## 165. TASK T-115-EXHIBITIONS-TEXT-SSOT-RECOVERY-1
- preflight:
  - `python run_phase1_network_preflight.py` x2 PASS
  - `phase1_network_preflight_summary_20260301T160009Z_01.json`
  - `phase1_network_preflight_summary_20260301T160009Z.json`
- 監査（Before固定）:
  - `run_phase1_exhibitions_text_audit.py` で基準値を保存
  - `exhibitions_text_ssot_recovery_audit_before_20260302.json`
  - totals: `rows=118 / non2025=15 / source_url重複=52 / date=0 / headline=0 / summary=0 / participating=0 / sources=0`
- バックアップ:
  - `exhibitions_frieze_london_2025.jsonl.bak_20260302_010015`
  - `exhibitions_liste_2025.jsonl.bak_20260302_010015`
- 実装（汎用のみ）:
  - 追加: `phase1_exhibitions_text_utils.py`
    - URL canonical化、対象年判定、日付抽出、Participating Artists抽出、PDF抽出・本文結合補助、sources統合
  - 追加: `run_phase1_exhibitions_text_raw_cleanup.py`
    - 非2025行除去、source_url重複統合、drop理由ログ出力
  - 追加: `run_enrichment_seed10_apply.py`
    - `run_enrichment_seed10.py` の結果を raw へ適用（headline_ja/summary_ja）
  - 追加: `run_phase1_exhibitions_text_audit.py`
    - Before/After監査をJSON化
  - 修正: `run_phase1_seed10.py`
    - Exhibitions Textを共通ユーティリティへ置換
    - `KNOWN_SAVED_SOURCE_URL` スキップ、`sources` 永続化、重複時sources追記
    - `exhibition_start_date/end_date/date_source/date_confidence` 保存
    - 起動前 manifest 最小同期（raw dry-run -> guarded apply）
- データ症状是正:
  - cleanup初回: `exhibitions_text_raw_cleanup_20260302.json`（`118 -> 58`）
  - cleanup再適用: `exhibitions_text_raw_cleanup_20260302_post_patch.json`（`80 -> 59`）
  - final確認: `exhibitions_text_raw_cleanup_20260302_final.json`（`59 -> 59`）
- 再実行:
  - `python run_phase1_seed10.py`
  - `python run_enrichment_seed10.py`
  - `python run_enrichment_seed10_apply.py`
- 監査（After最終）:
  - `exhibitions_text_ssot_recovery_audit_after_final_20260302.json`
  - totals: `rows=59 / non2025=0 / source_url重複=0 / date=57 / headline=59 / summary=59 / participating=22 / pdf_merge=0 / sources=59`
- guard:
  - `python run_compare_phase1_guard.py --target-year 2025` -> exit 0
  - `phase1_guard_summary_2025_20260301T164759Z.json`（`guard_passed=true`）
- R2同期:
  - raw:
    - dry-run `phase1_seed10_r2_sync_raw_20260301T164819Z.json`
    - apply   `phase1_seed10_r2_sync_raw_20260301T164836Z.json`
  - derived:
    - dry-run `phase1_seed10_r2_sync_derived_20260301T164852Z.json`
    - apply   `phase1_seed10_r2_sync_derived_20260301T165145Z.json`

 
 # #   1 6 6 .   T A S K   T - 1 1 6 - E X H I B I T I O N S - I M A G E - M A X 7 
 
 -   p r e f l i g h t : 
 
     -   p y t h o n   r u n _ p h a s e 1 _ n e t w o r k _ p r e f l i g h t . p y   x 2   P A S S 
 
     -   p h a s e 1 _ n e t w o r k _ p r e f l i g h t _ s u m m a r y _ 2 0 2 6 0 3 0 2 T 0 1 5 8 4 6 Z . j s o n 
 
     -   p h a s e 1 _ n e t w o r k _ p r e f l i g h t _ s u m m a r y _ 2 0 2 6 0 3 0 2 T 0 1 5 9 0 4 Z . j s o n 
 
 -   0 1 �!0 2 �!0 3   �f�e�: 
 
     1 .   d o c s / 0 2 _ R A G _ S P E C _ D E R I V E D . m d   g0  C A R D _ I D = 1 0 / 1 1 / 1 4 / 1 6 / 0 5   L0�N�Vn0;u�P�b�Qh0teTY0�0S0h0�0�x��
 
     2 .   d o c s / 0 1 _ P R O J E C T _ S P E C _ C U R R E N T _ F U L L . d o c x   g0  4 - 0 / 4 - 1 / 5 - 2 / 5 - 8 / 6 - 2 / 6 - 3 / 1 0   n0�0�0�0�0�Q�x��
 
     3 .   d o c s / 0 3 _ S T A T E _ S N A P S H O T _ N E X T _ T A S K S . m d   k0  M A X 7   �[L��0E x h i b i t i o n s �0�0�0�0�OYu�0�	�
 
 -   6�c�_�{�: 
 
     -   d a t a / g a l l e r y _ l i s t s / r e e x t r a c t _ t a r g e t s _ e x h i b i t i o n s _ i m a g e _ t a s k _ t 1 1 6 . c s v 
 
     -   
 
 u n _ p h a s e 1 _ s e e d 1 0 _ e x h i b i t i o n _ i m a g e _ c o l l e c t . p y �	 a r g e t _ y e a r = 2 0 2 5   +   1 U\1 ;u�P  /   m a x 7 _ t a r g e t _ u p d a t e 	�
 
 -   6�c�W�: 
 
     -   d a t a / p h a s e 1 _ s e e d 1 0 / l o g s / p h a s e 1 _ s e e d 1 0 _ e x h i b i t i o n _ i m a g e _ c o l l e c t _ s u m m a r y _ t a s k _ t 1 1 6 _ m a x 7 . j s o n 
 
 -   r e p o r t : 
 
     -   d a t a / p h a s e 1 _ s e e d 1 0 / l o g s / p h a s e 1 _ s e e d 1 0 _ e x h i b i t i o n _ i m a g e _ c o l l e c t _ s u m m a r y _ t a s k _ t 1 1 6 _ m a x 7 _ r e p o r t . j s o n 
 
 -   g u a r d : 
 
     -   p y t h o n   r u n _ c o m p a r e _ p h a s e 1 _ g u a r d . p y   - - t a r g e t - y e a r   2 0 2 5   - >   g u a r d _ p a s s e d = t r u e 
 
 -   R 2 : 
 
     -   d r y - r u n :   p h a s e 1 _ s e e d 1 0 _ r 2 _ s y n c _ d e r i v e d _ 2 0 2 6 0 3 0 2 T 0 2 0 6 2 0 Z . j s o n 
 
     -   a p p l y / p r u n e :   p h a s e 1 _ s e e d 1 0 _ r 2 _ s y n c _ d e r i v e d _ 2 0 2 6 0 3 0 2 T 0 2 1 2 4 7 Z . j s o n �u p l o a d e d = 0 	�
 
 -   �l�:   E x h i b i t i o n s �0�0�0�0\Omio0�s(W\Pbk-N0;u�P�SƖk0Ɩ-N
 
 
## 167. TASK_R2_SYNC_UNIFY_01 (run_r2_sync.py 一本化)
- `run_r2_sync.py` + `config/r2_sync_targets.json` を導入し、同期入口を統一。
- 運用固定: default=`plan`、`apply-upload`/`apply-prune` は `--apply --run-id` 必須。
- scope固定: defaultは `phase1_seed10_formal` / `tarutani_source`、`gallery_lists` は opt-in。
- 参照: `data/phase1_seed10/logs/r2_sync_unify_task_r2_sync_unify_01.md`

## 168. TASK_R2_SYNC_PLAN_01 (plan 2回 + stability)
- 全scopeで plan(dry-run) を2回実施し、prune候補集合のstabilityを確認。
- 判定: stability PASS（scope別に比較）。
- 参照: `data/phase1_seed10/logs/r2_sync_plan_task_r2_sync_plan_01.md`

## 169. TASK_R2_SYNC_APPLY_UPLOAD_01 (uploadのみ)
- 対象: `phase1_seed10_formal` + `tarutani_source`（gallery_lists除外）。
- 結果: upload成功、post-planで `missing_remote=0` / `size_diff=0` を確認。
- 実績: `phase1_seed10_formal uploaded=88`, `tarutani_source uploaded=77`。
- 参照: `data/phase1_seed10/logs/r2_sync_apply_upload_task_r2_sync_apply_upload_01.md`

## 170. TASK_R2_SYNC_APPLY_PRUNE_01 (phase1_seed10_formalのみ)
- 対象: `phase1_seed10_formal` のみで prune 実施（tarutani_sourceは不要、gallery_listsは禁止）。
- 結果: `extra_remote 72 -> 0`、`deleted_count=72`、post-plan `missing=0 / size_diff=0 / extra=0`。
- 参照: `data/phase1_seed10/logs/r2_sync_apply_prune_task_r2_sync_apply_prune_01.md`

## 171. TASK_R2_SYNC_CLEANUP_OLD_SCRIPTS_01 (旧入口削除)
- 旧同期入口4本を削除: `run_phase1_seed10_r2_sync.py` / `run_tarutani_r2_sync.py` / `run_r2_auto_sync.py` / `r2_auto_sync.py`。
- 用語区別を固定: 「旧スクリプト削除（repo削除）」と「同期削除(prune)（R2側のextra_remote削除）」は別。
- 現在入口は `run_r2_sync.py` のみ。Phase2(TASK293)は user OK pending で未着手。
- 参照: `data/phase1_seed10/logs/r2_sync_old_scripts_cleanup_task_oldsync_cleanup01.md`

## 172. TASK293_NEXT_14 = PHASE2_MILESTONE_DOC_UPDATE_FOR_FEATURES_01_TO_06
- 目的: Phase2で実装済みの機能①〜⑥を、03/04に節目として正確に反映（docs更新のみ）。
- 事前確認: 01/02/03/04を確認し、01/02の定義どおり「⑥=Gallery list」が正であることを再確認。
- 変更: `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` と `docs/04_TASK_PROGRESS_LOG.md` のみ更新。`docs/01_PROJECT_SPEC_CURRENT_FULL.docx` は未変更（仕様変更ではないため）。
- 到達点要約: ①Art Pulse overview+draft、②Exhibition Search read-only、③Artist Search read-only、④Advisor type1+type2(minimal+tuning)、⑤Exclusive Advisor type1+type2(minimal+tuning)、⑥Gallery list read-only baseline+tuning。
- 判定: Phase2 minimal implementation milestone documented.

## 172B. TASK293_NEXT_14 (ASCII mirror)
- Purpose: milestone documentation update for Phase2 features 01-06 (docs-only).
- Checked: 01/02/03/04; confirmed Feature 06 is Gallery list in SSOT.
- Changed: docs/03_STATE_SNAPSHOT_NEXT_TASKS.md and docs/04_TASK_PROGRESS_LOG.md only.
- Unchanged: docs/01_PROJECT_SPEC_CURRENT_FULL.docx (no spec change).
- Result: Phase2 minimal implementation milestone documented.

## 173. TASK293_CLOSEOUT_01 = PHASE2_POLISH_CLOSEOUT_REVIEW_AND_DOC_SYNC_03_04
- 目的: Phase2 baseline/minimal実装 + polishing完了の現在地を03/04へcloseout同期（docsのみ更新）。
- 事前確認: copy freeze=`COPY_FREEZE_OK`、01/02の定義どおり「⑥=Gallery list」が正。
- 変更: `docs/03_STATE_SNAPSHOT_NEXT_TASKS.md` と `docs/04_TASK_PROGRESS_LOG.md` のみ更新。`docs/01_PROJECT_SPEC_CURRENT_FULL.docx` / `docs/02_RAG_SPEC_DERIVED.md` は未変更（仕様変更なし、closeout syncのため）。
- 到達点要約: ①Art Pulse、②Exhibition Search、③Artist Search、④Advisor(type1/type2 tuned)、⑤Exclusive Advisor(type1/type2 tuned)、⑥Gallery list(read-only+tuning) を確認済み。
- 判定: Phase2 polish closeout documented（copy freeze OKを記録）。
- 次の最優先タスク: TASK293_NEXT_16 = PHASE2_CLOSEOUT_REVIEW_AND_GO_NO_GO_FOR_NEXT_PHASE

## 2026-03-11 CURRENT_HISTORY_REBASELINE_SYNC

- scope: docs sync only (01/02/03/04). no code/data move, no R2 sync run.
- baseline state fixed:
  - feature 1 Art Pulse = completed
  - feature 2 Exhibition Search = completed
  - feature 3 Artist Search = almost completed
  - feature 4 Advisor = not started

### A) Artists Text enrichment full apply (confirmed)
- target fields: `headline_ja`, `summary_ja`, `artist_name_kana`
- status: full apply completed for 2025 formal raw
- artifact examples:
  - `data/phase1_seed10/derived/artists_enrichment_apply_output_2025_*.jsonl`
  - `data/phase1_seed10/logs/artists_enrichment_apply_summary_2025_*.json`

### B) Artists target hygiene guard (confirmed)
- issue type: not LLM generation failure; request/apply target lookup mismatch
- fixed behavior: utility URL targets are handled by generic guard status
  - `SKIPPED_TARGET_GUARD_NON_ARTIST_UTILITY_URL`
- current confirmation:
  - `SKIPPED_TARGET_ROW_NOT_FOUND = 0`
  - utility URL guard rows = 3

### C) Artist Search re-baseline (confirmed)
- read-only route exists in `app.py` + `phase2_artist_search_readonly.py`
- enrichment read path for `headline_ja` / `summary_ja` / `artist_name_kana` is confirmed
- status: "almost completed" (not "unstarted")

### D) Roadmap change before Advisor (new official)
- before starting feature 4 Advisor, insert mandatory phase:
  - enrichment current/history canonical rebaseline
  - storage contract fix: `current` day-to-day canonical, `history` audit archive
  - app/read-only current-first reads
  - R2 as primary persistent sync target for current, aligned with local current fallback

### Next
- highest priority: `PRE_ADVISOR_STORAGE_CONTRACT_01`

## 2026-03-11 TASK290 PRE_ADVISOR_STORAGE_CONTRACT_01

- scope: contract freeze only before feature 4 Advisor.
- no action in this task:
  - no code migration
  - no data move
  - no directory migration execution
  - no R2 sync execution

### Contract decisions (frozen)
- current root: `data/current/enrichment/`
- history roots:
  - `data/history/enrichment/artists/`
  - `data/history/enrichment/exhibitions/`
- current fixed filenames:
  - `artists_enrichment_apply_output_2025.jsonl`
  - `artists_enrichment_apply_summary_2025.json`
  - `exhibitions_enrichment_apply_output_2025.jsonl`
  - `exhibitions_enrichment_apply_summary_2025.json`
- history policy: timestamped apply output/summary are immutable audit artifacts.
- writer policy: history timestamp write first, then atomic promote to current fixed names.
- reader policy: app/read-only/advisor are current-first; migration period only allows legacy derived latest-glob fallback.
- R2 policy: primary persistent target is current; history is backup/audit lane.
- anti-mixing policy: default readers never point to history.
- migration policy: reorganize legacy timestamped artifacts into history (no delete-first), bootstrap current from latest successful pair per category/year.

### A2-A8 execution order memo
1. A2: scaffold current/history directories and placeholder contract checks (no payload move).
2. A3: implement writer dual-lane (history write -> current promote), dry-run mode only first.
3. A4: seed initial current artifacts from latest successful legacy timestamped pairs (controlled migration).
4. A5: switch read-only loaders to current-first with legacy derived fallback guard.
5. A6: align app/advisor shared readers to the same current-first contract.
6. A7: update `config/r2_sync_targets.json` scopes to include current as primary and history as audit lane.
7. A8: execute migration+sync validation runbook (first actual move/sync task, outside TASK290).


## 2026-03-11 TASK290B STORAGE_ROOT_REBASELINE_01

- scope: docs-only root-name correction (no code change, no data move, no R2 sync run).
- contract idea unchanged from TASK290:
  - current/history separation
  - writer: history first -> current promote
  - reader: current first
  - R2: current primary target
- root change only:
  - current: `data/current/enrichment/`
  - history: `data/history/enrichment/artists/`, `data/history/enrichment/exhibitions/`
- role clarification:
  - `data/phase1_seed10/` remains seed10 working/validation artifacts lane, not long-term canonical root.
- Next highest priority: `291) A2_STORAGE_LAYOUT_SCAFFOLD_01`

## 2026-03-11 TASK291 A2_STORAGE_LAYOUT_SCAFFOLD_01
- scope: introduce storage scaffold only.
- result:
  - added canonical directories for enrichment current/history.
  - centralized enrichment current/history path contract for follow-up writer/reader tasks.
- not done: no payload move, no reader switch, no R2 sync execution.

## 2026-03-11 TASK292 A3_WRITER_HISTORY_PROMOTION_01
- scope: writer contract switch only (artists/exhibitions apply).
- result:
  - writers now persist timestamped artifacts into history first.
  - current fixed-name artifacts are promoted after successful history write.
- not done: no migration of legacy timestamp artifacts; no reader switch.

## 2026-03-11 TASK293 A4_MIGRATION_PLAN_AND_DRYRUN_01
- scope: migration planning and dry-run only.
- result:
  - inventoried legacy enrichment apply outputs/summaries under seed10 lanes.
  - produced dry-run manifest with action classification (seed_current_copy/history_copy/skip).
  - selected initial current candidate pair per category/year.
- not done: no file move/copy execution in this task.

## 2026-03-11 TASK294 A5_MIGRATION_EXECUTE_COPY_01
- scope: execute migration by copy only (non-destructive).
- result:
  - copied selected legacy timestamp artifacts to new history lanes.
  - seeded new current fixed-name artifacts for artists/exhibitions.
  - kept legacy artifacts in place (no delete/move).

## 2026-03-11 TASK295 A6_READER_CURRENT_FIRST_SWITCH_01
- scope: switch readers only.
- result:
  - app/read-only loaders now read current enrichment first.
  - migration-period fallback remains legacy seed10 latest only.
  - history lane is not included in default app/read-only query path.

## 2026-03-11 TASK296 A7_R2_TARGETS_CURRENT_FIRST_UPDATE_01
- scope: R2 target contract update + plan/dry-run verification only.
- result:
  - r2 targets aligned to current-primary / history-audit.
  - legacy seed10 target removed from default primary lane and treated as legacy lane.
  - `run_r2_sync.py` plan path validated on updated target contract.

## 2026-03-11 TASK297 A8_GUARDED_R2_SYNC_EXECUTION_01
- scope: guarded upload execution only.
- result:
  - executed `plan -> apply-upload` for `enrichment_current_primary` and `enrichment_history_audit`.
  - upload completed for both lanes; no prune/delete execution.

## 2026-03-11 TASK298 A9_PHASE2_CURRENT_CANONICAL_SMOKE_01
- scope: lightweight smoke for features 1/2/3 on current canonical baseline.
- result:
  - Art Pulse / Exhibition Search / Artist Search smoke passed under current-first baseline.
  - confirmed no history default reference in app/read-only paths.
  - current-present environment did not require legacy fallback warning.

## 2026-03-11 TASK299 LEGACY_ENRICHMENT_ARTIFACT_CLEANUP_01
- scope: cleanup legacy enrichment apply output/summary duplicates in seed10 lanes only.
- result:
  - removed redundant legacy enrichment apply artifacts already copied into current/history lanes.
  - retained current/history canonical artifacts and migration/audit latest traces.
  - no code change; no raw/formal/image cleanup.

## 2026-03-11 TASK300 A10_PHASE4_ADVISOR_KICKOFF_01
- scope: advisor kickoff only (type1 main, type2 gate check).
- result:
  - advisor type1 grounded draft path connected to current-canonical read-only context.
  - minimal app UI path and lightweight smoke passed.
  - type2 kept as gate-only path (not implementation-complete).

## 2026-03-11 TASK301 DOC_SYNC_POST_ADVISOR_KICKOFF_01
- scope: docs-only sync for post-kickoff baseline.
- result:
  - 01/02/03/04 aligned to: current/history rebaseline complete, advisor kickoff complete.
  - next highest-priority task updated to `A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01`.
- not done: no code change, no R2 prune/delete, no seed10-decoupling body migration.

## 2026-03-11 TASK302 DOC_SYNC_ARTIST_TEXT_INCIDENT_HOLD_01
- scope: docs-only minimal sync (03/04 only).
- result:
  - A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01 is set to hold.
  - Feature 3 remains almost completed, but Artist Text canonical incident blocks completion/finalization for now.
  - incident focus: duplicate raw/enrichment, artist_name trailing digits, identity key missing, raw/APPLIED partial mismatch.
  - Next highest priority replaced: from TASK302(A11) to ARTIST_TEXT_CANONICAL_INCIDENT_RESPONSE_01.
  - after incident response, re-evaluate whether 01/02 updates are required.
- not done: no 01/02 edits, no code/data changes, no R2 sync, no feature 5/6 progression.

## 2026-03-11 DOC_SYNC_ARTIST_TEXT_CANONICAL_EXECUTE_GO_04
- scope: docs-only milestone sync after Artist Text canonical repair execute (03/04 only).
- result:
  - execute verdict: GO (`artist_text_canonical_execute_20260311T124118Z`).
  - preflight passed (sha256/action totals/fair counts/backfill/review+quarantine/multi-APPLIED resolution checks all OK).
  - staging+promote completed: repaired raw=223 (frieze=126, liste=97), drop=65, quarantine=2, backfill=39, current artists APPLIED=223.
  - smoke passed: Feature3 trailing digit display=0, exact join=223/223, multi-APPLIED unresolved=0; Feature1 artist candidate issue count=0.
  - rollback not executed.
  - residuals: same-name collision review 1 group/2 rows (Germaine Kruip), quarantine manual disposition 2 rows, Artist Works Images metadata trailing digit 32 rows.
  - Next highest priority fixed to `P0_ARTIST_TEXT_CANONICAL_REVIEW_BUCKET_RESOLUTION_01`; Works metadata cleanup is next after this.
- not done: no 01/02 edits, no code/data/R2 changes in this docs sync, no Advisor progression, no feature 5/6 progression.

## 2026-03-11 DOC_SYNC_ARTIST_TEXT_CANONICAL_RESIDUAL_CLOSEOUT_01
- scope: docs-only closeout sync for Artist Text canonical incident (03/04 only).
- result:
  - review/quarantine resolution completed: Germaine Kruip review bucket resolved (`same_person_identity_unified`), quarantine 2 rows disposition fixed.
  - Artist Works Images metadata trailing-digit cleanup completed: 32 rows (frieze=20, liste=12) -> 0.
  - incident residual is now 0; incident close judged complete.
  - smoke maintained: Feature3 total=223 (frieze=126, liste=97), trailing-digit display=0, exact join=223/223, multi-APPLIED unresolved=0; Feature1 issue count=0.
  - invariant confirmed: Text raw/current apply/enrichment remained unchanged during metadata cleanup; current artists apply APPLIED=223.
  - Next highest priority returned to `A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01` (resume after incident close).
- not done: no 01/02 edits, no code/data/R2 changes in this docs sync, no execute rerun, no feature 5/6 progression.

## 2026-03-12 TASK305 DOC_MIN_SYNC_FOR_A11_02
- scope: docs-only minimal sync for A11 closeout notes (03/04 only).
- result:
  - 03 updated with Advisor state note: latest available year only for Advisor context + type1-centered checkbox UI; type2 remains gate-only.
  - A11 key behavior fixed in docs: when valid year exists, use max available year only and drop year-unknown rows; when all rows are year-unknown, keep fallback behavior.
  - Advisor UI note fixed in docs: `画像生成を希望する（利用条件あり）` checkbox, OFF=type1, ON=type2 gate check only.
  - minimal display note recorded: Advisor summary includes `参照年`.
  - execution confirmation summary recorded from latest A11 smoke: Exhibition/Artist/Cross queries returned grounded answers; checkbox ON path remained `gate_hold` with `api_called=false` under gate-only.
  - next highest priority set to `A11_PHASE4_ADVISOR_BROWSER_UI_FINAL_SMOKE_03` (real-browser final confirmation).
- not done: no 01/02 edits, no code/data/R2 changes, no feature 5/6 progression.

## 2026-03-12 TASK306 DOC_CLOSE_A11_PHASE4_ADVISOR_03
- scope: docs-only close sync for A11 completion (03/04 only).
- result:
  - A11 close confirmed for Feature 4 Advisor: type1 quality tuning complete, latest available year only active, type1-centered checkbox UI active, and type2 remains gate-only.
  - tiny fix recorded: type1 heading area includes 参照年: ... directly under Advisor回答（日本語 / type 1）.
  - real-browser final smoke confirmed from 	mp_ui_smoke_a11_03/a11_browser_ui_final_smoke_03_gatehold_summary_fresh_context.json: Exhibition/Artist/Cross x OFF/ON all passed (overall_ok=true), gate_hold route OK, type1-primary + evidence display OK.
  - operational note: depending on environment/billing/API state, checkbox ON may end in image_failed instead of gate_hold; both paths keep type1 answer/evidence as primary output.
  - next highest priority moved to A12_PHASE5_EXCLUSIVE_ADVISOR_KICKOFF_01.
- not done: no 01/02 edits, no code/data/R2 changes, no Feature 5 implementation started, no Feature 6 progression.
- correction (TASK306): tiny fix text is "参照年: ..." under "Advisor回答（日本語 / type 1）".
- correction (TASK306): smoke summary path is "tmp_ui_smoke_a11_03/a11_browser_ui_final_smoke_03_gatehold_summary_fresh_context.json".
- correction (TASK306): tiny fix means a reference-year caption is shown directly under the type1 answer heading.

## 2026-03-12 TASK307 DOC_MIN_SYNC_FOR_A12_01
- scope: docs-only minimal sync for A12 result capture (03/04 only).
- result:
  - A12 type2 is officially enabled in code for Feature 4 Advisor (checkbox ON runs type2 as auxiliary output after type1).
  - type2 gate policy is now lightweight precheck only (`OPENAI_API_KEY` / type1 grounded success / question present / prompt composable).
  - fail-soft is fixed: user-facing failure/unavailable notice is a unified short message in main UI, while technical status/checks/errors remain in dev details.
  - latest available year only behavior remains unchanged for advisor grounding (`参照年` + evidence display maintained).
  - 6-run smoke executed (Exhibition/Artist/Cross x OFF/ON): OFF stayed type1-stable; ON stayed type1-primary + type2 section visible.
  - fail-soft path verified (`precheck_failed`, `api_called=false`) from `tmp_ui_smoke_a12_01/a12_failsoft_onecase.json`.
  - success-path real image generation is not yet verified due environment billing limit (`billing_hard_limit_reached`) in ON runs.
- evidence:
  - `tmp_ui_smoke_a12_01/a12_type2_enable_smoke_normal3.json`
  - `tmp_ui_smoke_a12_01/a12_failsoft_onecase.json`
- next highest priority: `A12_PHASE4_ADVISOR_TYPE2_SUCCESS_PATH_SMOKE_WHEN_ENV_READY_01`.
- sequence note: after the success-path confirmation task, move to `A12_PHASE5_EXCLUSIVE_ADVISOR_KICKOFF_01`.

## 2026-03-12 TASK308 DOC_EMERGENCY_SYNC_ENRICHMENT_BATCH_POLICY_01
- scope: docs-only emergency sync for enrichment cost/batch incident (01/02/03/04 only).
- audit facts fixed into docs:
  - Artists / Exhibitions bulk apply had no confirmed Batch API execution evidence in repo audit; history outputs showed `enrich_mode=openai_direct_apply` even when summaries carried `enrich_use_openai_batch="1"`.
  - repeated direct apply is treated as the primary incident candidate; repeat-apply hard guard and promote gate by evidence are now fixed as mandatory contract in docs.
  - direct OpenAI is now documented as preview/sample only; bulk apply is documented as Batch API required and enforced.
  - current promote is documented to require batch evidence + rerun-guard evidence; evidence-missing runs must not promote.
- roadmap update:
  - immediate priority is switched from Advisor success-path smoke to enrichment batch-safety hardening (`EMERGENCY_FIX_ENRICHMENT_BATCH_ENFORCEMENT_AND_REPEAT_APPLY_HARD_GUARD_01`).
  - ordered follow-up is fixed as: batch enforcement/hard guard -> safety verification -> localized repair only if needed -> A12 success-path smoke -> feature 5/6.
- data judgment:
  - full re-take is not required by this incident alone; only localized repair should be considered if concrete row-level defects are later confirmed.
- Feature 4 preservation note:
  - A11 completion state is retained (type1 quality tuning / checkbox UI / latest available year only / `参照年`).
  - A12 implementation state is retained (type2 officially enabled in code, lightweight precheck, fail-soft unified short message).
  - A12 success-path smoke remains unverified due environment/billing block (`billing_hard_limit_reached`); priority is lowered, not rolled back.
## 2026-03-13 TASK309 DOC_MIN_SYNC_RUNTIME_POLICY_FOR_ENRICHMENT_REQUESTS_01
- scope: docs-only runtime policy sync for enrichment requests artifacts (01/02/03/04).
- result:
  - `*_enrichment_requests_{year}.jsonl` is fixed as runtime input artifact (non-canonical, app/read-only non-reference).
  - seed10 lane is reaffirmed as working/validation lane only; requests are not long-term canonical assets.
  - retention rule fixed: keep only while batch/resume/guard/lock is active; after terminal + history summary/manifest + current promote verdict with evidence, requests become deletable.
  - no move/delete executed in this task; runtime path migration and cleanup are deferred to a follow-up implementation task.
- not done: no code/data/R2 change, no enrichment rerun, no bulk/sample execution, no Feature 4/5/6 progression.

## 2026-03-13 TASK310 DOC_MIN_SYNC_FOR_RUNTIME_PATH_VERIFY_01
- scope: docs-only minimal sync after runtime path verify verdict GO (01/02/03/04).
- result:
  - runtime active requests paths are fixed in docs:
    - `data/runtime/enrichment_requests/artists/artists_enrichment_requests_2025.jsonl`
    - `data/runtime/enrichment_requests/exhibitions/exhibitions_enrichment_requests_2025.jsonl`
  - runtime subdir roles are fixed: `_completed` (archive) / `_reports` (migration-retention audit).
  - verify GO is recorded from implementation verification:
    - apply preflight shows runtime `requests_path` for both categories
    - migration report hash/size matches runtime file and legacy seed10 requests are detached from production path
    - retention helper synthetic checks confirm keep on missing evidence and allow only on terminal+evidence complete
  - main roadmap is preserved; this sync does not trigger bulk/sample/API execution.
- not done: no code/data/R2 changes, no batch/sample run, no tmp harness cleanup/refactor.

## 2026-03-13 TASK311 DOC_SYNC_CANCEL_EMERGENCY_BULK_APPLY_AND_RESUME_ADVISOR_01
- scope: docs-only minimal priority sync (03/04 only) after `VERIFY_TEXT_RAG_AND_ENRICHMENT_STILL_PRESENT_01` verdict `STILL_PRESENT`.
- result:
  - raw/current enrichment/summary files remain present and readable for Artists / Exhibitions.
  - current outputs remain usable (`artists: total=287, APPLIED=284, utility skip=3`; `exhibitions: total=83, APPLIED=83`) with `headline_ja/summary_ja` missing count `0` in APPLIED rows.
  - read-only current-first assumption remains valid (`phase2_common_readonly.py` + artist/exhibition readonly loaders).
  - `EMERGENCY_BULK_RUN_ENRICHMENT_BATCH_APPLY_01` stays available but is deferred now (no execute), and immediate priority is returned to `A11_PHASE4_ADVISOR_TYPE1_QUALITY_TUNING_01`.
- not done: no bulk apply execution, no API submit/call, no code/data/R2 change, no docs 01/02 update.

## 2026-03-17 TASK312 DOCS_SYNC_ADVISOR_TEXT_ONLY_COMPLETE_AND_NEXT_IMAGE_TEXT_TUNING_16
- scope: docs-only sync for Feature 4 Advisor lane status (01/02/03/04).
- result:
  - Feature 4 Advisor type1 text-only question lane is recorded as completed/locked (lane scope), with explicit note that Feature 4 overall is not closed.
  - text-only achieved set is fixed in docs: selected/reference split, fixed prose helper ban, generic intent focus, same-focus ranking tuning, caption/page-description suppression, fragment guard, grounded enrichment, OpenAI-path suppression for `anchor > 0` snippet-only outputs.
  - operational judgment is fixed: text-only lane is now tiny-fix-only on regression recurrence (no broad redesign by default).
  - next immediate task is switched to `ADVISOR_TYPE1_IMAGE_ATTACHED_TEXT_QUESTION_TUNING_01`.
  - image-attached text-question precision tuning is explicitly tracked as the next Feature 4 work item.
- not done:
  - no code/data/app behavior changes.
  - no statement that “Feature 4 Advisor fully complete”.

## 2026-03-17 TASK313 DOCS_SYNC_AFTER_ADVISOR_IMAGE_ATTACHED_COMPLETION
- scope: docs-only sync for Feature 4 Advisor final type1 lane status after image-attached tuning/eval/rollback stabilization (01/02/03/04).
- result:
  - Feature 4 Advisor type1 text-only question lane remains completed/locked and tiny-fix-only on regression recurrence.
  - Feature 4 Advisor type1 image-attached text-question lane is now recorded as completed/locked after real-image human eval.
  - accepted stable behavior is fixed in docs for image-attached lane: transient in-memory visual observation only, no persist/vectorize/RAG-mix, observation first, asked-mode alignment, grounded reference only as secondary support when needed, and non-reference answers should not let proper nouns become the main subject.
  - tuning history is fixed in log only: `TUNING_01` introduced visual observation, `TUNING_02` established baseline mode control / display fix / proper noun suppression, `TUNING_03` over-tightened purity and regressed on real-image eval, and `TUNING_03_ROLLBACK` restored the accepted stable state on top of the TUNING_02 baseline.
  - text-only lane was rechecked during image-attached tuning and no major regression was accepted.
  - roadmap priority is moved forward to `A12_PHASE5_EXCLUSIVE_ADVISOR_KICKOFF_01`, while Feature 4 type1 stays tiny-fix-only and type2 remains connected/secondary rather than newly declared complete.
- not done:
  - no code/data/app behavior changes.
  - no statement that Feature 4 Advisor as a whole or type2 is fully complete.




## 2026-03-17 TASK314 DOCS_CORRECTION_AFTER_ADVISOR_TYPE1_COMPLETION
- scope: docs-only correction after Feature 4 Advisor type1 completion sync (01/02/03/04).
- result:
  - type1 text-only and image-attached text-question lanes remain completed/locked in docs.
  - docs are corrected so Feature 4 overall is still open: type2 image-generation lane is connected, but not yet validated/accepted.
  - immediate priority is moved back inside Feature 4 to `A12_PHASE4_ADVISOR_TYPE2_SUCCESS_PATH_SMOKE_WHEN_ENV_READY_01`.
  - Feature 5 Exclusive Advisor is returned to the post-Feature-4 position rather than the current top priority.
- not done:
  - no code/data/app behavior changes.
  - no rollback of the accepted type1 lane completion state.


## 2026-03-18 TASK315 DOC_SYNC_PHASE4_ADVISOR_TYPE2_ACCEPT_TEXT_ONLY_PENDING_IMAGE_ATTACHED_01
- scope: docs-only sync for the latest accepted/pending split inside Feature 4 Advisor type2 (01/02/03/04 only).
- result:
  - Feature 4 Advisor type1 text-only and image-attached text-question lanes remain completed/locked and tiny-fix-only on regression recurrence.
  - Feature 4 Advisor type2 text-only -> image generation lane is now recorded as accepted.
  - accepted runtime is fixed in docs as `gpt-image-1` / `low` / `1024x1024` / `1 image`.
  - accepted text-only type2 progression is summarized in docs as: gate uses truncated grounded text, model/cost drift is fixed to SSOT, `gpt-image-1` low experiment is accepted, medium-fidelity tuning is in place, and the visual nucleus tiny fix is applied.
  - text-only image generation is recorded as accepted across painting / installation / photograph; one installation fail-soft occurred during iteration but a rerun succeeded, so it is not recorded as a persistent blocker.
  - Feature 4 overall remains open because image-attached -> image generation is still pending validation/smoke.
  - immediate priority is moved to `A17_PHASE4_ADVISOR_TYPE2_IMAGE_ATTACHED_TO_IMAGE_GENERATION_SMOKE_01`; Feature 5 returns to the post-Feature-4 position.
- not done:
  - no code/data/app behavior changes.
  - image-attached -> image generation is not declared accepted.
  - Feature 4 Advisor as a whole is not declared fully complete.


## 2026-03-19 TASK316 DOC_SYNC_PHASE4_ADVISOR_POST_A17_TO_A30_01
- scope: docs-only sync for Feature 4 Advisor after type2 acceptance expansion, UI cleanup batches, and follow-up stabilization (01/02/03/04 only).
- result:
  - Feature 4 Advisor type1 text-only and image-attached text-question lanes remain completed/locked and tiny-fix-only on regression recurrence.
  - Feature 4 Advisor type2 text-only -> image generation remains accepted, and image-attached -> image generation is now recorded as smoke-success / accepted.
  - accepted runtime is fixed in docs as `gpt-image-1` / `low` / `1024x1024` / `1 image`.
  - type2 accepted progression is summarized as: gate uses truncated grounded text, model drift correction, `gpt-image-1 + low` adoption, medium/format fidelity tuning, and visual nucleus tiny fix.
  - text-only image generation is accepted across painting / installation / photograph, and image-attached -> image generation smoke also succeeded without opening a persistent blocker.
  - Advisor UI cleanup batches are recorded as completed: aligned fair/select + image-generation checkbox, uploader-note removal, debug panels hidden by flag, compact single image view with fullscreen-icon removal, reset/progress display, fair filter warning fix, reference cards unified with search UI, and scrollable long summaries inside cards.
  - follow-up is recorded as session-only with no persistence (no R2/file/DB/JSON/CSV writes), using fixed anchor + compressed memory + latest one-turn context, Q1/Q2 numbering, input auto-clear for initial/follow-up questions, output normalization, length tuning around ~700 chars, linebreak render preservation, and partial re-grounding via fixed-core + dynamic reference refresh.
  - follow-up crash root-cause is recorded as an `effective_fair` undefined path in the new reference refresh branch; this is fixed and treated as a root fix for that crash path.
  - Feature 4 Advisor is now treated as accepted/completed for the current scope; future handling is major-regression-only tiny fix.
  - next roadmap priority is moved to `A12_PHASE5_EXCLUSIVE_ADVISOR_KICKOFF_01`.
- not done:
  - no code/data/app behavior changes in this docs sync.
  - no claim beyond the accepted/current-scope behavior already implemented in repo.
