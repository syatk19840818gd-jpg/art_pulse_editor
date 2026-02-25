# 04_TASK_PROGRESS_LOG.md

最終更新: 2026-02-26 01:14 JST  
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
- 取れない分はログに残して前進する（失敗をログ化して割り切る）。

---

## 2. 全体の進捗サマリ（現時点）

- 完了: **TASK 1 ～ TASK 96**
- 次の予定: **TASK 97**
- 直近の重点:
  - TarutaniRAG 側で比較/guard の「型」を作成 → Phase1本体（Exhibitions/Artists）へ横展開
  - Phase1 guard 本体 / history 比較 / fixture / matrix / schema文書化 / category文脈まで整備
  - category profile を外部設定化し、設定ミス時の安全フォールバックも実装済み

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

## 10. 現在の次タスク（TASK97）

[ ] 97) artists回答QA retry-run daily chain recovery chain report rollup から failed run 向け retry manifest を生成するCLIを追加し、要再対応runの再実行入口を短縮する（本体前進）
- 目的：
  - TASK96で生成される `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` から failed run を抽出し、再実行manifestを自動生成する
- 制約：
  - 取得ループ内LLM加工は追加しない（Post-fetch分離）
  - 既存daily chain/recovery chain report/rollup本体ロジックは変更せず、manifest生成CLI追加のみに限定する
- 成立条件：
  - `python run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py --rollup-json "..."`（例）が実行できる
  - `--latest` で最新 `artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json` を自動解決できる
  - 生成manifestに `source_summary_path` / `failed_step_names` / `retry_manifest_path`（同等）を保存できる
  - failed run 0件でもクラッシュせず、空manifest（または0件明示）を保存できる

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
