# 04_TASK_PROGRESS_LOG.md

最終更新: 2026-02-26 20:53 JST  
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

- 完了: **TASK 1 ～ TASK 104**
- 次の予定: **TASK 107（rollup最新判定補正）**
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
