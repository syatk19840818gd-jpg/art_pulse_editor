# 04_TASK_PROGRESS_LOG.md

最終更新: 2026-02-24 17:01 JST  
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

- 完了: **TASK 1 ～ TASK 43**
- 次の予定: **TASK 44**
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

## 10. 現在の次タスク（TASK44）

[ ] 44) 統合matrix summaryの軽量レポートCLIを追加し、CI失敗時の切り分けを高速化する（安全側）
- 目的：
  - `run_phase1_guard_all_matrices.py` が出力する統合summaryを1画面で読めるレポートへ整形し、失敗matrixの特定を即時化する
- 制約：
  - guard/history/lint 各CLIおよび各matrix wrapperの判定ロジックは変更しない（summary読取CLIのみ追加）
- 成立条件：
  - `--summary-path` / `--latest` の2経路でレポート生成ができる
  - `all_passed` / 失敗matrix名 / `actual_exit_code` / `summary_path` を最低限出力できる
  - 03 の CHANGELOG に反映

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
