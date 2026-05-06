# DOCS_RECOVERY_LOCK_2026-04-22（01〜04復旧・再発防止）

- この文書群は、2026-02-23 正常系 ZIP を安全基底として確認し、2026-02-23〜2026-03-25 の git 保存済み増分を事故前最新 `10f51bd3` まで回収したうえで、2026-03-30 以降の有効追補を救出して再構成した。
- 2026-03-30 `e6de6b2`（件名: `⑤完全削除`）で 01〜04 の文字数が 95〜99% 級に急減したため、この差分は削除事故疑いとして正本差分に採用しない。
- 01 は正本であり、追加・局所変更のみ許可する。明示承認なしの全文再生成、全置換、全削除、大規模要約圧縮、変更対象外章の移動を禁止する。
- docs 更新は対象段落アンカーを指定した局所 patch とし、更新前後に `git diff --word-diff -- docs/...` を確認する。不自然な大量削除、文字化け、見出し数/主要段落数/文字数の急減があれば中止する。
- 02 は 01 の派生索引、03 は現在地、04 は時系列ログである。02/03/04 で新仕様を作らず、矛盾時は 01 を優先する。
- 大きい docs 更新は一回の全文書き直しではなく、複数の局所 patch に分割する。01 更新では変更対象外の章見出し数・主要段落数が急減していないことを完了条件にする。
- 今後の Codex task 作成時は、`01全置換禁止`、`docs更新は局所patch`、`不自然な削除diffが出たら即中止`、`diff確認が完了するまで成功扱いにしない` を必ず明記する。

---

# 復元本文: 2026-03-25 `10f51bd3` 事故前最新索引

02_RAG_SPEC_DERIVED（RAG抽出・保存 “カテゴリ別カード集”】【索引専用】）
版：vFinal（SSOT参照：01_PROJECT_SPEC_CURRENT_FULL.docx）

目的（この02の役割）
- 01（正本）の内容を「変えずに」、Codex/LLMが検索・参照しやすい “索引カード” に落とす。
- 01の全文を毎回なめずに、実装判断で迷う箇所へ最短で到達するための「道しるべ」。
- 重要：仕様の正本は常に 01。02は“参照用のまとめ”であり、矛盾が出たら 01 を優先する。

使い方（Codex/LLM向け）
- 実装中に迷ったら、まずこの02で「CARD_ID」検索 → 該当カードの「SSOT参照（01の場所）」へ戻る。
- “固定”と書かれた項目は勝手に変更しない（01の固定ルール由来）。
- “推奨”は実装上の安定運用のための提案。採用したら一貫して維持する（manifest同期があるため）。

============================================================
CARD_ID: 00_DOC_CONTROL（この02の運用）
============================================================
- 01（正本）…人間が読む正本。仕様の最終決定は常に01。
- 02（本ファイル）…索引カード集。01と同じ内容を“検索しやすく”再配置。
- 03（STATE_SNAPSHOT＋NEXT_TASKS）…進捗で更新される運用ドキュメント（節目で更新するバッチ同期対象）。

変更ポリシー（事故防止）
- 02は「01の固定ルール」を“短く再掲”するのはOK。
- 02で新仕様を作らない（新仕様は01へパッチ→反映）。
- パス/ファイル名/ハッシュ定義/分離ルールは、01の“固定”を最優先。

============================================================
CARD_ID: 01_PARAMS_CURRENT（可変パラメータの正本）
============================================================
SSOT参照（01）
- 「0. 可変パラメータ（数値の正本）」配下
SSOT_TAG: 01>「0. 可変パラメータ（数値の正本）」配下

ここにある数値は “唯一の正本”
- 例：TARGET_YEAR / 1ギャラリーの最大Exhibition数 / 画像枚数上限 / 成功率ライン / 等
- 実装は、数値をコードに直書きせず「PARAMS_CURRENT」から参照する前提。

============================================================
CARD_ID: 02_INPUT_GALLERY_LIST（ギャラリーリストCSV）
============================================================
SSOT参照（01）
- 「⑥「Gallery list」」配下（CSV形式・パースルール）
SSOT_TAG: 01>「⑥「Gallery list」」配下（CSV形式・パースルール）

固定：CSVの役割
- 取得対象の全ギャラリー一覧（Frieze / Listeを分けて保持）。
- “seed10” などのテストは、このCSVの先頭から件数で切り出す。

推奨：保存場所（repo内）
- data/gallery_lists/
  - gallery_list_frieze_london.csv
  - gallery_list_liste.csv

注意：CSV形式
- ヘッダーなし / UTF-8
- 1行1レコード：ギャラリー名（地域等含む）, Exhibitions一覧URL, Artists一覧URL

============================================================
CARD_ID: 03_TERMS_GUARD（用語の誤読防止：Modeは使わない）
============================================================
SSOT参照（01）
- 「用語整理（迷子防止）」の Phase 定義
- 「質問タイプ（ユーザーが選択）」の定義
SSOT_TAG: 01>「Phase：8章『ROADMAP』で定義…」 | 01>「質問タイプ（ユーザーが選択）」

固定：用語統一（事故防止）
- Phase：SSOTのROADMAPで定義される開発段階。
- 本プロジェクトでは「Mode」という用語を正本概念として使わない（誤読を生む）。
- UI/挙動の分岐は「質問タイプ1/2」＋（画像検索ON/OFF等の既存UI要素）で表現する。
- 02/03で新しい“モード体系”を作らない（必要なら01へパッチ）。

============================================================
CARD_ID: 04_STORAGE_KEYS（r2_key命名規則・分離）
============================================================
SSOT参照（01）
- 「r2_key の命名規則（固定｜フォルダ分離の徹底）」配下
SSOT_TAG: 01>「r2_key の命名規則（固定｜フォルダ分離の徹底）」配下

固定：r2_key（混在防止）
- 規則：data/{FAIR_SLUG}/images/{image_url_hash}.{ext}
- FAIR_SLUG = frieze_london / liste
- 物理フォルダ（バケット内のパス）レベルでデータ混在を防止する。
- Exhibition/Artist の保存も FAIR_SLUG × 保存分類（source / derived / logs / vectors）でカテゴリ分離する（SSOT 5-1/5-3 + 5-7/5-8 追記）。

例外（Tarutani_data系）
- Tarutani_data は、ローカルのディレクトリ構造自体がメタデータの正本。
- そのため、ハッシュリネーム禁止。ローカル構造をR2 Keyにも採用（ミラー運用）。

============================================================
CARD_ID: 05_MANIFEST_SYNC（current/history を含む同期方式）
============================================================
SSOT参照（01）
- 「5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)」配下 → 「C) キャッシュ更新判定（固定）」
SSOT_TAG: 01>5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)>C) キャッシュ更新判定（固定）

固定：同期は manifest が正本
- ローカル保存 / R2保存の同期状態は “manifest” で管理。
- 画像や本文の個別存在確認に依存しない（事故防止）。
- current は機械・人間が日常参照する常用正本（アプリ運用の第一参照）。
- history は監査/比較用の履歴置き場（通常の検索/表示パスには混在させない）。
- R2 は current を永続同期する主対象。local current fallback と整合して運用する。
- 旧表現「R2正本 + local cache」は、上記の役割分担（R2主対象 / current常用 / history監査）として読む。
- 共通ストレージ方針（SSOT 5-7/5-8）：
  - 原本（source）は R2正本
  - 派生データ（jsonl / index / meta / manifest）は R2正本
  - ベクトル（vector/index/meta）は R2正本（ローカルは作業キャッシュ）
  - local data/ は抽出・検証・開発用キャッシュ（正本ではない）
  - ログは local 保存を必須、重要ログは R2 logs へバックアップ推奨
  - Gitには原則ログ/データ本体を入れない（肥大化防止）

C) キャッシュ更新判定（固定）
- R2に “manifest”（例：artifact_manifest.json）を1つ置き、「対象year」「各ファイルの更新時刻/etag/hash」だけを持つ
- localはmanifestが変わった時だけ再ダウンロードする
- manifest最小例（フィールド名は固定、値は例）：
    { "target_year": 2025, "generated_at": "...", "files":
    [{"path":"...","etag":"...","sha256":"...","bytes":12345}] }
  ※ manifest（例：artifact_manifest.json）の files[].path は R2上の object key（＝r2_key）を入れる。ローカルの実ファイルパスは実装側で map する。
- 判定ルール：files のいずれかで etag or sha256 が変わったら、そのファイルだけ再DL。
- vector再現性の最低項目（SSOT 5-8 追記）：
  - embedding_model / embedding_dim / chunk_size_chars / chunk_overlap_chars / generated_at / records_count / code_commit_id（取得可能な場合）

============================================================
CARD_ID: 06_SKIP_DEDUP_CORE（重複取得をしない：基準）
============================================================
SSOT参照（01）
- 「重複取得をしない（超重要）」配下
SSOT_TAG: 01>「重複取得をしない（超重要）」配下

固定：スキップの思想
- “同じものを何度も取りに行かない” が最重要。
- ただし “保存すべきレコード” を作らずにスキップして、空レコード量産/メタ欠落を起こさない。

テキスト重複（方針）
- text_hash が同じなら「新規レコードは作らずスキップ」し、sources だけを増やす
  - 必要なら別台帳：text_sources.json に追記

画像重複（方針）
- image_url_hash が同じなら “画像DL/保存” はスキップしてよい
- ただし、Exhibition/Artist側の “紐づけレコード” は必ず保存し、image_url_hash を参照させる
  - 画像ファイルが同一でも「どの展示/どの作家から来たか」は別情報
- Artist系抽出（artists_text / artist works images）の artist 重複は「全フェア・全ギャラリー横断」で禁止。
  - `artist_master_global.json`（artist_identity_key / first_source_url）を参照し、既知artistは自動スキップする。
  - 例外: ExhibitionsRAG 側の artist 重複は許容し、この自動スキップは適用しない。
  - canonical_source_key は dedup / join / repair dry-run 判定用の別キーとして扱う（`source_url` と混同しない）。
  - `source_url` は provenance/live link の原本として保持し、canonical化のために書換しない。
  - artist_name canonicalization（最小固定）：leading numeric id 除去 / trailing `-1,-2,...` 除去 / biography|works|about 等の非氏名segment無視 / numeric-only結果は invalid。
  - same-name collision は自動 merge しない。review bucket へ送る。
  - identity backfill 不能行は quarantine 扱いにする（通常joinへ混在させない）。

============================================================
CARD_ID: 07_PDF_HANDLING（PDFリンクの扱い）
============================================================
SSOT参照（01）
- 4-0 本体冒頭の「対象年の判定」ブロック
- 4-0 本体の「PDF扱い」ブロック
SSOT_TAG: 01>4-0 本体冒頭の「対象年の判定」ブロック | 4-0 本体の「PDF扱い」ブロック

固定：PDFは “保存” だけ（要約しない）
- テキスト抽出できるPDF：全文を保存してOK（要約しない）
- テキスト抽出できないPDF（画像PDF/スキャン等）：本文は読まず pdf_url だけメタ保存

注意：リンク扱いの事故
- HTMLページ内のPDFリンクを “通常ページ” と同じ扱いで巡回すると事故りやすい
- PDFは上記ルールのみに従う（＝例外処理として扱う）

============================================================
CARD_ID: 08_POST_FETCH_ENRICHMENT（FetchとEnrichmentの分離）
============================================================
SSOT参照（01）
- 「Post-fetch/Enrichment」行（Fetch後の事後処理）配下
SSOT_TAG: 01>「Post-fetch/Enrichment」行（Fetch後の事後処理）配下

固定：取得ループ内で LLM加工を逐次実行しない
- headline_ja / artist_name_kana 等の生成は “事後バッチ” で行う
- Fetchは “保存できる素材を集める” ことに集中

固定：バッチ入口
- fetch（保存）→ jsonl/csv 生成 → enrichment_batch（後処理）
- 失敗が出ても、Fetch全体が止まらない構造にする
- Artists / Exhibitions の enrichment bulk apply は Batch API required and enforced
- direct OpenAI は preview/sample only（bulk apply では禁止）
- bulk apply summary / manifest には `api_mode` / `batch_used` / `batch_job_id` / `input_bundle_hash` / `target_rows` / `updated_rows` / `rerun_guard_verdict` / `process_lock_id` を必須保存する
- repeat apply hard guard を必須とし、同一入力束の再applyは明示ガードで止める
- canonical incident 対応フロー（固定最小）：repair dry-run（manifest/summary 生成）→ review bucket/quarantine 確認 → repair execute。
- Artist Text / Artist Works Images / enrichment join は canonical_source_key + artist identity（artist_name_key / artist_identity_key）整合を前提に実行する。
- multi-APPLIED source group は dry-run で検出し、execute 前に keep/drop 方針を確定する。

============================================================
CARD_ID: 09_FAILURE_LOGGING（失敗をログ化して割り切る）
============================================================
SSOT参照（01）
- 「失敗ログ/割り切り運用（頻出ドメイン×汎用ロジックのみ改善）」配下
SSOT_TAG: 01>「失敗ログ/割り切り運用（頻出ドメイン×汎用ロジックのみ改善）」配下

固定：割り切り前提
- 取れない分はログに残して前進（無限ループしない）
- 改善投資は「頻出ドメイン」の汎用ロジックに限定
- 少数ドメイン専用改善は原則しない

推奨：失敗ログの最低フィールド
- url
- category（4-1/4-2…）
- reason（status_code/timeout/parse_error 等）
- attempt_count
- last_attempt_at

============================================================
CARD_ID: 10_NO_HERO_IMAGES（作家ヒーロー画像を取らない）
============================================================
SSOT参照（01）
- 「作家のヒーロー画像（プロフィール写真）は収集しない」配下
SSOT_TAG: 01>「作家のヒーロー画像（プロフィール写真）は収集しない」配下

固定：除外対象
- 作家の顔写真/プロフィール写真/ヘッダー等（展示作品画像とは別）
- 作品画像（展示内の作品）を優先する

推奨：判定の目安
- “profile / portrait / headshot / avatar / bio” などの文脈は除外候補
- 取れない場合はログに残して前進（ドメイン専用分岐は増やさない）

============================================================
CARD_ID: 11_IMAGE_TARGET_LINE（画像抽出の標準ライン：SSOT準拠）
============================================================
SSOT参照（01）
- 「6-3) 品質ライン（試作10ギャラリーの運用）」
- 「6-2) ドメイン専用ハードコード増殖の禁止（重要）」＋「6-5) 失敗の扱い」
SSOT_TAG: 01>「6-3) 品質ライン（試作10ギャラリーの運用）」 | 01>「取れない分はログに残して割り切る（ゼロよりマシを優先）。」

固定：当面の標準ライン（※数値は01のPARAMS_CURRENTを正とする）
- まず “取得率{ QUALITY_TARGET_SUCCESS_RATE }%超” を標準ラインとして前進（SSOT準拠）
- 例の説明（SSOTの例示）：1人あたり作品画像取得の上限×成功率でラインを考える
- 改善は「頻出ドメイン×汎用化」だけに限定し、取れない分はログ化して割り切る

※追跡目標（KPI等）は“固定索引”の02ではなく、03_STATE_SNAPSHOT/NEXT_TASKSで更新管理する。

============================================================
CARD_ID: 12_IMAGE_SIZE_ESTIMATE（画像サイズ想定）
============================================================
SSOT参照（01）
- 「# RAG：画像容量の目安」配下（{ IMAGE_TARGET_SIZE_KB }）
SSOT_TAG: 01># RAG：画像容量の目安 / { IMAGE_TARGET_SIZE_KB }

固定：見積り基準
- 画像1枚あたり { IMAGE_TARGET_SIZE_KB }KB を基準にする（ストレージ/帯域コストの見積り）

============================================================
CARD_ID: 13_SEED10_STRATEGY（seed10の目的と定義）
============================================================
参照（03：運用）
- 03_STATE_SNAPSHOT_NEXT_TASKS.md の「seed10の定義」配下
NOTE: seed10は “運用上の最小検証手順” なので、仕様の正本（01）ではなく運用（03）で管理する

固定：seed10の目的
- まず “小さく最後まで通す”（取得→保存→再実行スキップ）
- UIは後回し。Phase 1のCLIで成立させる

推奨：seed10の定義（例）
- frieze：ギャラリーリスト先頭5件
- liste：ギャラリーリスト先頭5件

============================================================
CARD_ID: 14_CATEGORY_4_0_COMMON（4-0 共通ルール）
============================================================
SSOT参照（01）
- 「4-0) ①～④共通ルール（①～④カテゴリ共通）」配下
SSOT_TAG: 01>「4-0) ①～④共通ルール（①～④カテゴリ共通）」配下

固定：4-0は全カテゴリの土台
- 対象年の判定（TARGET_YEAR）
- PDF扱い
- 重複取得の思想（text_hash / image_url_hash）
- 失敗ログと割り切り
- manifestで同期
- RAG抽出実行時は、summary/reportに「対象内訳（最低: fair/gallery単位の対象人数・成功人数・取得件数・成功率%）」を必須で残す
- 画像収集: 取得件数 = 取得画像枚数
- テキスト抽出: 取得件数 = 抽出レコード件数
- 共通化できる判定・抽出ロジックはカテゴリ横断で共通モジュールへ集約し、個別スクリプトの重複実装を禁止する（修正点1箇所固定）。

============================================================
CARD_ID: 16_SSOT_COMPLIANCE_GATE（実装逸脱の再発防止）
============================================================
SSOT参照（01）
- 「SSOT整合ゲート（再発防止・強制運用）」配下
SSOT_TAG: 01>「SSOT整合ゲート（再発防止・強制運用）」

固定：実装前/実装後の強制ゲート
- 実装前に、01章ID + 02 CARD_ID の対応を明示してから変更する。
- 共通化可能な処理（URL判定/候補抽出/重複判定など）を新規に個別実装しない。既存共通モジュールを再利用し、未整備なら先に共通化してから各カテゴリへ適用する。
- Artistsは「一覧URL→詳細URL抽出→詳細ページ抽出」以外を禁止（一覧URL直抽出を禁止）。
- カテゴリ別上限値の流用ミスを禁止（Exhibitions用上限をArtistsに流用しない）。
- Artist Works Images のローカル作業キャッシュは FAIR_SLUG 単位で一本化し、gallery単位ディレクトリ分割は行わない（識別はファイル名/メタデータで保持）。
- 暫定運用（2026-02-26）：artists抽出上限は安定化まで各gallery 1件。安定確認後に段階引き上げし、最終80へ戻す。
- Artist系抽出（artists_text / artist works images）の重複防止は同一フェア内に限定しない。異なるフェア間でも同一artistは再抽出せず自動スキップする（ExhibitionsRAG は対象外）。
- 実装後は、失敗理由上位・対象内訳を 03/04 と `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` に記録する。
- `docs/RAG_EXTRACTION_BREAKDOWN_JA.md` の内訳記録は日本語で記述する（英語のみの記載は禁止）。
- 上記の日本語内訳ルールは、全RAGカテゴリ（Artists/Exhibitions/Tarutani、画像/テキスト/ベクター、同期）へ恒久適用する。
- タスク終了時の出力テンプレは「【タスク終了時に行うこと】」を固定採用し、03更新は必ず 02→01→03 の順で実施する。
- 03更新時は、対象TASKを `[x]` に変更し、CHANGELOG/LAST_UPDATED/完了実行内容を同時更新する。
- 理由付きスキップを確定したgalleryは `data/gallery_lists/skipped_galleries_registry.csv` に1行追記し、以後の Artists/Exhibitions の画像・テキスト抽出すべてで共通の自動スキップ対象とする。
- RAG成果物（Artists/Exhibitions の images/text/vector/derived）はローカル生成のみではR2へ反映されない。`run_r2_sync.py` で `plan -> apply-upload -> apply-prune` を明示実行して反映する。
- 同期運用（固定）: 同期入口は `run_r2_sync.py` に一本化し、追加/更新は `apply-upload`、削除反映は `apply-prune`（confirm + max-prune + stability確認）で実行する。
- 実装ゲート（固定）: 新規に追加する「RAGを変更し得るスクリプト」（画像抽出/テキスト抽出/ベクター化/enrichment apply）は、同期時に `run_r2_sync.py` の明示実行を必須とする（カテゴリ共通）。
- 失敗URLの運用（固定）: image collect は failed URL ledger を永続化し、次回は cooldown + retry上限で自動スキップする。テスト時のみ `--force-retry-failed` と `--clear-failed-ledger target|all` で一時解除する。

運用ゲート（増殖防止）
- 失敗率高止まり/保存0連続時は、report/rollup/manifest追加ではなく原因分解と最小修正を優先する。

============================================================
CARD_ID: 15_CATEGORY_4_1_EXHIBITIONS_TEXT（4-1) Exhibitions：Text）
============================================================
SSOT参照（01）
- 「4-1) Exhibitions：Text（抽出ルール）」配下
- 「5-1) Exhibitions Text（4-1の成果物）」配下
- 「5-3) Artist Text（4-3の成果物）」配下
- 「5-8) 同期方式（R2正本 + local cache）」配下
SSOT_TAG: 01>「4-1) Exhibitions：Text（抽出ルール）」配下
SSOT_TAG: 01>「5-1) Exhibitions Text（4-1の成果物）」配下
SSOT_TAG: 01>「5-3) Artist Text（4-3の成果物）」配下
SSOT_TAG: 01>5-8) 同期方式（R2正本 + local cache）

固定：最初に成立させるカテゴリ
- 4-1だけで「取得→保存→再実行でスキップ」を成立させる
- 他カテゴリ（4-2/4-3/4-4）は後回しでOK

推奨：保存単位
- gallery → exhibitions一覧 → 各exhibitionページ → テキスト抽出→保存
- 失敗があっても全体が止まらない（ログ化して前進）
- Exhibition/Artist 保存章の追記（01 5-1/5-3）により、保存分類は source / derived / logs / vectors を採用し、manifest最低項目は 5-8 規定へ統一。

============================================================
CARD_ID: 16_TARUTANI_TEXT_SCOPE（Tarutani_Textの扱い）
============================================================
SSOT参照（01）
- 「Tarutani_Text（4-5の成果物）」配下
- 「5-9) 埋め込みモデル（固定｜ベクトル空間を壊さないため）」配下
SSOT_TAG: 01>「Tarutani_Text（4-5の成果物）」配下
SSOT_TAG: 01>5-9) 埋め込みモデル（固定｜ベクトル空間を壊さないため）

固定：文章データ（作品画像ではない）
- Tarutani_Text は “文章RAG” の対象
- 作品画像（Tarutani_Works）は別扱い（UI表示/リンク生成しない方針など、SSOTに従う）
- TarutaniRAGの埋め込みは、先頭2000字1本ではなく「1,000字チャンク + 200字オーバーラップ」で分割し、各チャンクを個別に埋め込む（SSOT 5-9 例外規定）
- 埋め込み時メタとして `text_len` / `embed_input_len` / `is_truncated` を保存する（SSOT 5-9）
- Tarutani_Text検索は、埋め込み類似度を基準にしつつ source_path 単位の優先度プロファイルと同一source偏り抑制（max_per_source）を併用してよい（優先度は設定ファイル管理、個別ハードコード禁止）
- 数値・実績が競合する場合は、最新の要約資料（例：`曲線と直線_概要.docx`）と rank 上位根拠を優先し、旧資料値は補足扱いにする（SSOT 01 追記準拠）
- Tarutani原本（Text配下）は R2正本、source_path はローカル元位置メタとして保持する
- Tarutani派生データ（tarutani_text.jsonl / enrichment / import summary / vector関連）も R2バックアップ対象
- Tarutani logs の重要ログは R2 logs バックアップ対象

推奨：投入タイミング
- Phase1（seed10）が2回連続で完走してから
- 先にFrieze/Listeの抽出・保存が安定していることが前提

============================================================
CARD_ID: 17_ENV_KEYS_R2（R2環境変数の名前ゆれ対策）
============================================================
SSOT参照（01）
- SSOTは「R2接続情報（endpoint/bucket/access/secret等）の概念」を示すが、環境変数名の正本までは固定していない（このカードは実装上の推奨名）
SSOT_TAG: 01>「Secrets（…R2接続情報…）」

固定：envの存在チェック
- ローカル .env と Streamlit Secrets の両方で揃える
- “名前ゆれ” は ALIASES で吸収（アプリ側で保険）

推奨：必須キー（例）
- R2_ENDPOINT / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_BUCKET

============================================================
CARD_ID: 18_STREAMLIT_ENTRY（Streamlit入口）
============================================================
SSOT参照（01）
- 「Streamlit」配下（デプロイ/入口）
SSOT_TAG: 01>「Streamlit」配下（デプロイ/入口）

固定：入口は app.py（Streamlit Cloud main file path）
- ローカル：streamlit run app.py
- Cloud：Main file path = app.py
- app/read-only は current を優先参照し、manifest差分時のみ R2 current から必要分を同期する。
- history は監査用途のみで、通常の read-only 検索導線には載せない（anti-mixing）。

============================================================
CARD_ID: 19_NO_FEATURE_REMOVAL（機能削除の禁止）
============================================================
SSOT参照（01）
- 「既に作られた機能をAIが勝手に削除/無効化しない」配下
SSOT_TAG: 01>「既に作られた機能をAIが勝手に削除/無効化しない」配下

固定：絶対ルール
- 既存機能を勝手に削除/無効化しない
- 影響が出る変更は、削除対象/影響範囲/代替案を示して合意を取る

============================================================
CARD_ID: 20_DEV_FLOW_MIN（最小の開発フロー）
============================================================
SSOT参照（01）
- 「開発フロー（Phase1→Phase2）」配下
SSOT_TAG: 01>「開発フロー（Phase1→Phase2）」配下

固定：Phase1はCLIで成立させてからUIへ
- まずは seed10 で “取得→保存→再実行スキップ” を成立
- その後に Streamlit UI（Mode1/Mode2）へ拡張

推奨：節目での締め
- 小Taskごとに03更新は必須ではない。
- 変更ファイル / 実行コマンド / 生成物 / 次の最優先タスクを短く残し、03/04は数Taskごと・実行フェーズ完了時・長めの中断前・handoff前のいずれかでまとめて更新する。

============================================================
CARD_ID: 21_CURRENT_HISTORY_OPERATION（current/history運用索引）
============================================================
SSOT参照（01）
- 「5-7) 共通：ストレージ」配下
- 「5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)」配下
SSOT_TAG: 01>5-7) 共通：ストレージ
SSOT_TAG: 01>5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)

固定：役割分担（索引）
- current: 機械・人間の常用正本（アプリの普段の読み先）
- history: 監査・比較の履歴置き場（非デフォルト経路）
- runtime: runtime input / staging lane（非canonical、デフォルトの app/read-only 参照先ではない）
- `_trash`: 明示的 hold lane（temp / backup / review-needed artifact の単一退避先）
- `data/phase1_seed10/`: working/validation lane（長期 canonical root ではない）
- R2: current 永続同期の主対象
- local fallback: R2未達/差分時に current 運用を継続するための補助
- app/read-only: current-first。history は audit lane であり default runtime lane に混ぜない

============================================================
CARD_ID: 22_PRE_ADVISOR_STORAGE_CONTRACT_01（実装前契約固定）
============================================================
SSOT参照（01）
- 5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)
- PRE_ADVISOR_STORAGE_CONTRACT_01 (frozen before Feature 4 Advisor)
SSOT_TAG: 01>5-8) Sync Model (R2 primary + current/history + local fallback | fixed minimal ops)

固定：path契約
- current root: `data/current/enrichment/`
- history roots:
  - `data/history/enrichment/artists/`
  - `data/history/enrichment/exhibitions/`

固定：artifact契約
- current fixed filenames (year scoped):
  - `artists_enrichment_apply_output_2025.jsonl`
  - `artists_enrichment_apply_summary_2025.json`
  - `exhibitions_enrichment_apply_output_2025.jsonl`
  - `exhibitions_enrichment_apply_summary_2025.json`
- history keeps timestamped apply output / summary as immutable audit artifacts.
- `data/phase1_seed10/` is a seed10 working/validation lane and is not the long-term canonical root for current/history.
- `*_enrichment_requests_{year}.jsonl` is a runtime input artifact generated from raw; it is non-canonical and not a default app/read-only reference source.
- active runtime requests paths (2025):
  - `data/runtime/enrichment_requests/artists/artists_enrichment_requests_2025.jsonl`
  - `data/runtime/enrichment_requests/exhibitions/exhibitions_enrichment_requests_2025.jsonl`
- runtime subdirs:
  - `_completed/` is archive lane for terminal-complete requests artifacts
  - `_reports/` is migration/retention audit lane（常時生成しない。verify / migration / retention 監査時のみ）
- requests runtime retention policy:
  - keep while batch is `in_progress` / `validating` / `finalizing`, or while resume path is open (`rerun_guard_verdict=resume_existing_batch` with active guard/lock).
  - deletable after batch reaches terminal state and history output/summary/manifest plus current promote verdict are fixed with batch/guard evidence fields.
  - long-term retention is not required because requests can be regenerated from raw when needed.
- verify status: runtime-path switch and retention safety verify are GO (preflight path checks + migration-report/file consistency + synthetic retention checks passed).
- artifact policy (derived from 01 hygiene constitution):
  - optional artifact is opt-in only via `ART_PULSE_OUTPUT_ARTIFACTS`
  - `preview` / `diagnostics` / `report` / `latest` / `diff` / `inventory` are default-off
  - do not keep duplicate mirror storage across current/history/runtime/trial/backup lanes
  - do not add new temp / backup / report root when current/history/runtime/`_trash` already cover the role
  - `latest` + timestamped dual retention is prohibited by default; timestamped single-source is preferred
  - exception: `run_r2_sync.py` plan log is an essential artifact because `apply-prune` guard consumes it
  - `run_phase1_seed10_exhibition_image_collect.py` `summary_latest` is default-off; timestamped summary is standard
  - `run_text_enrichment_delta_promote.py` dry-run previews / diagnostics / category report / run report are optional artifacts only

固定：writer/readers/sync責務
- writer:
  - write timestamped artifacts to history first
  - promote to current fixed filenames only after successful write
  - bulk apply promote requires batch evidence + rerun-guard evidence; evidence-missing runs must not promote to current
- readers (app/read-only/advisor):
  - current-first
  - legacy fallback, if kept for incident review, is historical-only and does not define canonical storage
- R2:
  - primary persistent sync target = current
  - history is backup/audit lane (non-default runtime lane)

固定：anti-mixing / migration
- do not mix current and history in default query paths.
- app default readers must not point to history.
- runtime guarantee: app/read-only must continue to function even if history lane is absent.
- canonical current storage:
  - `data/current/raw/*.jsonl`
  - `data/current/vector/artists/*`
  - `data/current/images/metadata/*.jsonl`
  - `data/current/images/cache/**`
- `data/phase1_seed10/` is not the long-term canonical root; it remains a working / validation / retained-lane legacy parent.
- retained lane ledgers stay in `data/phase1_seed10/logs/`:
  - `visited_pages*`
  - `failed_fetches_seed10_2025.json`
  - `failed_fetches_artists_seed10_2025.json`
  - `failed_fetches_artist_image_collect_{year}.json`
  - `artist_master_global.json`
- current ledgers family:
  - `data/current/ledgers/` is the current ledger family root for ledgers that are formally read from current.
  - retained lane main ledgers remain in `data/phase1_seed10/logs/` and are not moved by default.
  - current-ledger R2 scope is `current_ledgers_family` (`local_root=data/current/ledgers`, `r2_prefix=data/current/ledgers`, `include_globs=["**/*"]`).
- canonical storage closeout note:
  - raw / artists vector / image metadata / image cache are already rebased to current and must not be described as active `phase1_seed10` canonical roots
  - future ledger revisit, if any, is a behavior-contract task rather than a default storage-move task

## TASK285 Closeout Update (Exhibitions Text Controlled Operation)
- status: COMPLETED
- final_lane_state: READY=58 / ESCALATE=5 / HOLDING=6 / REJECT=0
- steady_state_policy: routine weekly proof runs are discontinued; normal operation does not require recurring weekly proof runs.
- reopen_trigger: blocker fired (ratio_two_consecutive / route_degradation / boundary breach / integrity breach), spec change, or monitored state corruption.
- runbook_policy: use minimal normal-mode checks only; enter full detailed runbook only for incident mode.

## TASK286 Phase1 Closeout Signoff and Phase1.5 Exit Review Freeze
- phase1_signoff: COMPLETED at 10-gallery operational scope for 5 RAG categories (not a full hundreds-scale guarantee).
- phase1_5_added: Exit Review is mandatory before Phase 2.
- fixed_execution_order: 1) Tarutani_Text -> 2) Artist Works Images -> 3) Artist Text -> 4) Exhibitions Image -> 5) Exhibitions Text.
- fixed_per_category_steps: final check -> minimal fix if needed -> minimal re-validation -> Exit Review completion declaration.
- fixed_review_axes_6: generality; risky implementation check; commonization/reuse; quality-line fit (70%); operational resilience; next-phase connectivity.
- fix_classification: A) local fix, B) common core promotion candidate.
- minimum_artifacts: per-category review report; re-validation evidence only when fixes are applied; one cross-category common-core promotion summary after all 5.
- phase2_gate: start Phase 2 only after Phase 1.5 completion.
- phase2_phase3_path: Phase 2 uses 10-gallery RAG for features 1-6; Phase 3 expands first to about 150 then to 200+.
- operation_policy: do not increase routine weekly proof runs; use minimal normal-mode checks and incident-mode detailed runbook only when triggers fire.

============================================================
CARD_ID: 23_POST_ADVISOR_KICKOFF_CURRENT_CANONICAL_INDEX
============================================================
SSOT source:
- 01 section 7 (current baseline)
- 01 section 8 (Phase 2 milestones)
- 01 section 5-8 (sync model: current/history/R2/local fallback)

Index update (2026-03-21):
- phase status:
  - feature 1 Art Pulse: completed
  - feature 2 Exhibition Search: completed
  - feature 3 Artist Search: stable / almost completed
  - feature 4 Advisor: completed / accepted for the current scope
  - feature 5 Exclusive Advisor: not started / explicit user instruction required
  - feature 6 Gallery list: not started
  - feature 7 ArtWork Search: current implementation exists / accepted for current scope
- current/history rebaseline: completed (A2-A9)
  - storage scaffold in `data/current/enrichment/` and `data/history/enrichment/{artists,exhibitions}/`
  - writer contract: history timestamp write first, then current fixed-name promotion only when batch evidence + rerun-guard evidence are present for bulk apply
  - reader contract: current-first; any remaining legacy fallback is historical-only and not a canonical root
  - R2 contract: current primary lane, history audit lane, guarded upload completed
- canonical storage steady state:
  - raw family = `data/current/raw/*.jsonl`
  - artists vector family = `data/current/vector/artists/*`
  - image metadata family = `data/current/images/metadata/*.jsonl`
  - image cache family = `data/current/images/cache/**`
  - `data/phase1_seed10/` is no longer the long-term canonical root; its main live role is working/validation plus retained ledgers
- ledger retained lane closeout:
  - retained = `visited_pages*`, `failed_fetches_seed10_2025.json`, `failed_fetches_artists_seed10_2025.json`, `failed_fetches_artist_image_collect_{year}.json`, `artist_master_global.json`
  - current-ledger family = `data/current/ledgers/` (formal current ledger family; not a blanket move of retained lane ledgers)
- enrichment emergency override:
  - Artists / Exhibitions bulk apply must move to Batch API enforced mode before the next production-style apply
  - direct OpenAI remains allowed only for preview/sample lanes
- advisor readonly/context index:
  - advisor type1 context is grounded via existing current-first read-only routes
    - art pulse overview
    - exhibitions enrichment current output
    - artists enrichment current output
  - evidence refs/source refs are shown from read-only outputs
  - lane operation note: Feature 4 Advisor is accepted/completed for the current scope and future handling is major-regression-only tiny fix.
  - follow-up note: Advisor follow-up is session-only, no persistence, keeps reference refresh lightweight via fixed-core + dynamic-refresh rather than full re-grounding, and uses Q-numbering plus initial/follow-up input clear and uploader clear inside session UI only.
- repo/output hygiene steady state:
  - cleanup lane is completed; steady-state policy is “増えた artifact を後で消す” ではなく “default で増やさない”
  - optional artifact is opt-in only; no default `preview` / `diagnostics` / `report` / `latest` / `diff` / `inventory`
  - no new temp / backup / report root; no duplicate mirror storage; no default latest alias when timestamped single-source is sufficient
  - historical `tests/` fixtures, stale `_trial` provenance, backup mirror bundles, and `_trash/ADOPT*` are not active dependencies
- text enrichment small-delta incident handling:
  - standard first-response = `existing-artifact diagnosis -> intentional drop -> localized repair -> no-reextraction delta promote`
  - standard entrypoint = `run_text_enrichment_delta_promote.py`
  - `run_artist_text_canonical_dryrun.py` / `run_artist_text_canonical_execute.py` are retired one-off scripts
  - full rerun / full rebuild / re-extraction / canonical rebuild / promote rerun are last-resort + user-confirmed only

Next (from STATE/NEXT):
- docs sync to the current handoff baseline is completed
- cleanup lane is completed/fixed; return to main roadmap only by explicit user task
- do not auto-start Feature 5 and do not reopen cleanup without explicit user instruction
- treat Feature 7 ArtWork Search as a separate implemented-and-accepted app lane; it does not start Feature 5

============================================================
CARD_ID: 24_PROOF_LANE_CLOSEOUT_AND_CURRENT_ONLY_RUNTIME_20260322
============================================================
SSOT source:
- 01 section 5-7 (common storage)
- 01 section 5-8 (sync model)
- 01 section 6 (operation rules)
- 01 section 8 (roadmap / execution guard)

Closeout update (2026-03-22):
- proof lane status:
  - cleanup / storage rebase / hygiene / aggressive prune / ledger closeout / R2 sync / old-prefix cleanup / strict current-only hardening / no-API smoke are completed.
  - the proof criteria fixed in this chat are treated as satisfied for 1) Exhibitions Text, 2) Exhibitions Image, 3) Artist Text, 4) Artist Works Images, and 5) save-path / skip / contract verification.
- current formal families:
  - `data/current/raw/*.jsonl`
  - `data/current/vector/artists/*`
  - `data/current/images/metadata/*.jsonl`
  - `data/current/images/cache/**`
  - `data/current/enrichment/*.jsonl`
  - `data/history/enrichment/{artists,exhibitions}/*`
  - `data/runtime/enrichment_requests/{artists,exhibitions}/*`
  - `data/Tarutani_data/*`
- R2 formal reflection:
  - `artists_vector_current`
  - `raw_current_primary`
  - `images_metadata_current`
  - `images_cache_current`
  - final verify verdict for the four current families is fixed as `would_upload=0 / would_prune=0`.
- legacy / old-prefix cleanup closeout:
  - completed legacy prune scopes:
    - `phase1_seed10_legacy_images_prune`
    - `phase1_seed10_legacy_image_metadata_prune`
    - `phase1_seed10_legacy_vector_prune`
    - `phase1_seed10_legacy_request_prune`
  - completed old-prefix cleanup scopes:
    - `phase1_seed10_derived_manifest_legacy_prune`
    - `phase1_seed10_source_legacy_prune`
    - `tarutani_legacy_vectors_prune`
    - `tarutani_legacy_logs_prune`
    - `tarutani_legacy_derived_prune`
  - final verify verdict for the above cleanup scopes is fixed as `would_upload=0 / would_prune=0`.
- top-level interpretation:
  - `data/` is the formal keep root.
  - `phase1_seed10/` remains only because `data/phase1_seed10/logs/` is the retained-ledger lane.
  - old `tarutani/` prefix is cleanup-complete and is not an active runtime family root.
- strict current-only runtime contract:
  - 1)/3) text readonly/runtime read paths are strict current-only.
  - `phase2_common_readonly.py` text enrichment resolver is fixed to strict current-only and no longer falls back to legacy `phase1_seed10/derived`.
  - `run_phase1_seed10.py` no longer touches legacy `data/phase1_seed10/derived`.
  - 2)/4) image readonly/runtime read paths remain current image metadata + current image cache only.
- no-API runtime proof:
  - 1) Exhibitions Text runtime read succeeded from current raw + current enrichment only.
  - 3) Artist Text runtime read succeeded from current raw + current enrichment only.
  - 2) Exhibitions Image / 4) Artist Works Images runtime read succeeded from current image metadata + current image cache only.
  - rerun skip proof is accepted: existing artifacts stop at local dry-run / skip / no-op and do not advance into API execution.
  - new-save contract proof is accepted: new raw/image/vector outputs resolve to the current formal lanes.
- operation note:
  - cleanup is no longer an active default lane.
  - return to the main roadmap is allowed.
  - Feature 5 / Exclusive Advisor must still start only on explicit user instruction.

============================================================
CARD_ID: 25_FEATURE7_ARTWORK_SEARCH_ACCEPTED_ROUTE_AND_MANUAL_VALIDATION_20260324
============================================================
SSOT source:
- 01 section 2 (Feature 7 ArtWork Search)
- 01 section 3 (RAG category note)
- 01 section 5-8 / 5-9 (storage + retrieval contract)
- 01 section 8 (roadmap / execution guard)

Index card:
- status:
  - current implementation exists
  - accepted for current scope
  - manual browser validation passed
- feature classification:
  - Feature 7 ArtWork Search is an implemented app feature
  - it is not a new RAG category
  - it reuses the existing Artist Works Images corpus only
- corpus:
  - Artist Works Images only
  - excluded from initial scope: Exhibitions Image / Tarutani / Artist Text / Exhibitions Text
- query:
  - japanese text -> `gpt-5-mini` rewrite -> short English search query -> OpenCLIP -> image retrieval
  - english text -> direct OpenCLIP -> image retrieval
  - image -> direct OpenCLIP -> image retrieval
- engine:
  - OpenCLIP
  - local execution only
- dependency:
  - `torch`
  - `open-clip-torch`
- initial scope:
  - 10-gallery current corpus
  - query input = text or image
- retrieval view:
  - similarity emphasis may include color / shape / composition / overall impression
  - initial display is a similar-image list plus attached metadata such as artist / gallery / fair / source_url
- current-family contract:
  - existing current image metadata + current image cache only
  - do not describe this feature as a new image corpus or a new image-storage family
- implementation / acceptance evidence:
  - minimum readonly module + minimal app UI exist
  - import success
  - initial artifact build success
  - text query success
  - image query success
  - fair filter success
  - second-run artifact load reuse success
  - app render passed
  - AppTest text UI path returned `errors=0 / exceptions=0`
  - uploader reset nonce behavior confirmed query-image state discard
  - Feature 7 UI is aligned with Feature 2/3 style:
    - fair select options = `Frieze London` / `Liste Art Fair Basel` / `Frieze London + Liste Art Fair Basel`
    - default fair select = `Frieze London + Liste Art Fair Basel`
    - title = `artist_name（artist_name_kana）`
    - `summary_ja` is shown
    - one image card per result uses full-width fixed-height thumbnail style
    - count caption follows shared style (`件数: 読込= / ヒット= / frieze= / liste=` and `検索結果: ○件（横スクロールで閲覧 / タップで画像拡大）`)
    - legacy inline status labels (`artifact=` / `mode=` / `fair:`) are removed from normal UI
  - Cloud anonymous verify-only can be blocked when the Cloud app is private; treat that state as access configuration, not as a Feature 7 behavior regression.
  - manual browser validation passed for `青い幾何学` / `青い絵画` / `人物` / `植物` / `blue geometric abstraction`
  - additional manual validation passed for `鳥` / `未来的` / `繊細` / `細かい` / `情熱` / `極彩色`
- closeout:
  - Google Translation was evaluated/planned but is not the adopted final route
  - japanese dictionary-expansion helper is removed
  - weighted-max merge is removed
  - Google Translation code / dependency / path are removed from the repo implementation
- not adopted:
  - Google Translation route
  - row text rerank is not adopted because image-level binding is weak and artist/page-level text can easily contaminate image retrieval quality
- acceptance note:
  - Feature 7 is accepted for current scope
  - current scope keeps OpenCLIP, no re-extraction, no duplicate image storage, no re-vectorization redesign, and no row-text rerank

============================================================
CARD_ID: 26_FEATURE7_ARTWORK_SEARCH_STORAGE_AND_GATE_CONTRACT_20260324
============================================================
SSOT source:
- 01 section 5-8 (storage / sync)
- 01 section 5-9 (embedding / retrieval)
- 01 section 8 (roadmap / execution guard)

Storage contract:
- canonical input:
  - `data/current/images/metadata/*.jsonl`
  - `data/current/images/cache/**`
- new artifact only:
  - OpenCLIP embeddings
  - ANN / search index
  - id map
- current implementation path:
  - `data/current/vector/artist_works_images/*`
- R2 reflection:
  - Feature 7 current artifacts (`embeddings` / `search index` / `id map`) are reflected via scope `artist_works_images_vector_current`.
  - reflection is kept scope-local and is not mixed with unrelated families.
- prohibited:
  - duplicate image store
  - separate ArtWork Search image cache
  - Feature 7-only image re-save
  - re-extraction by default
- query image handling:
  - session-only
  - no save
  - no R2 upload
  - no corpus mix
- query rewrite contract:
  - japanese text is rewritten by `gpt-5-mini` into one short English search query before OpenCLIP retrieval
  - english text remains direct OpenCLIP
  - image remains direct OpenCLIP
  - keep OpenCLIP itself unchanged
  - no re-vectorization redesign
  - no row-text rerank layer

Implementation / operation gates:
- verify-first was completed before minimum implementation and artifact build
- do not silently trigger API / re-extraction / rebuild
- any cost-incurring execution still requires explicit user confirmation first
- Feature 5 remains explicit-user-instruction-only
- Feature 7 is a separate implemented-and-accepted app lane and must not be treated as Feature 5 kickoff
- Feature 2/3 cleanup note:
  - `answer_artist_followup()` and `answer_exhibition_followup()` are removed as unused functions.
  - they were not used by the active Feature 2/3 search route; this is dependency residue cleanup, not route behavior change.
- gitignore note:
  - `.gitignore` remained unchanged in this lane.
  - reason: `data/current/` was already ignored by directory-family rule; the issue was file-fixed R2 scope design, not gitignore coverage.
- current acceptance note:
  - manual browser validation passed and Feature 7 is accepted for current scope
  - japanese text path is `gpt-5-mini` rewrite -> short English search query -> OpenCLIP
  - english text path is direct OpenCLIP
  - image path is direct OpenCLIP


============================================================
CARD_ID: 27_FEATURE1_TO_7_LOCAL_DEPENDENCY_AUDIT_AND_COMMON_HYDRATE_FIX_20260324
============================================================
SSOT source:
- 01 section 5-8 (sync model: current/history/R2/local fallback)
- 01 section 6 (operation constitution / no duplicate / no blind rerun)
- 01 section 8 (phase roadmap guard)

Absolute operation rule (re-confirmed in implementation):
- Cloud runtime must prioritize GitHub checkout + R2 current families.
- User PC is treated as potentially offline; local-only existence must not be a runtime precondition.
- local files are debug/working fallback only and must not become the default source-of-truth dependency.

Cross-feature audit result (Feature 1-7):
- Feature 1 / 2 / 3 / 4 / 5 / 6: no local-only blocker on the active read path.
- Feature 7: local-only blocker was found and fixed via common layer.

Common blocker cause:
- current vector family hydration was not covered by the common path->R2 resolver.
- Feature 7 had a local existence gate that could skip corpus/state load when local current files were missing.

Adopted fix contract (common-first, no feature-specific helper sprawl):
- `phase2_common_readonly.py`:
  - add `hydrate_path_from_r2(...)` as shared hydrate entry.
  - include `data/current/vector/**` in shared path->R2 mapping.
  - keep `safe_load_jsonl(...)` and current-first enrichment resolver on the shared hydrate path.
- `phase2_artwork_search_readonly.py`:
  - switch Feature 7 metadata / image-cache / vector artifact loading to the shared hydrate path.
  - remove reliance on file-local-only loading assumptions in the accepted route.

Non-change boundary:
- no query route redesign.
- no rewrite policy change (`gpt-5-mini` jp-only rewrite remains fixed).
- no R2 scope expansion beyond existing current families.
- no duplicate storage family is introduced.


============================================================
CARD_ID: 28_FEATURE7_SINGLE_WIDE_IMAGE_CONTAIN_TINY_FIX_20260324
============================================================
SSOT source:
- 01 section 2 (Feature 7 UI contract)
- 01 section 6 (tiny-fix lane / no scope creep)

Accepted tiny-fix summary:
- scope: UI-only tiny fix for Feature 7 result-card image rendering.
- issue: narrow-window rendering could crop the Feature 7 single-wide card image.
- fix: align single-wide rendering with Feature 2 exhibition-card image contract:
  - `background-image`
  - `background-size: contain`
  - `background-position: center center`
  - `background-repeat: no-repeat`
- layout contract preserved: one image / full-width / fixed-height card image lane.

Non-change boundary (explicit):
- no UI wording change.
- no count-caption change.
- no card text structure change.
- no search / rewrite / hydrate / R2 contract change in this tiny-fix lane.

---

# 2026-04-22 削除事故後ソースから救出した現行追補

以下は、2026-03-30 の大量削除差分を正本採用せず、削除事故後の現行 docs から有効な契約・運用情報だけを救出するための追補である。既存本文の代替ではなく、事故前最新本文への追加情報として扱う。

02_RAG仕様_派生索引
版: 2026-04-22 JST（実装固定更新: `rag_gellery_breakdown_master.xlsx` 反映時の根拠入力群整合ルール）
参照正本: `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`

目的
- 本書は 01 正本の運用要点を実装参照向けに圧縮した索引である。
- 仕様の最終判断は常に 01 を優先する。

現行アプリ構成
- 機能1: Art Pulse
- 機能2: Exhibition Search
- 機能3: Artist Search
- 機能4: Advisor
- 機能6: Gallery list
- 機能7: ArtWork Search

正本契約（current / history / `rag_gellery_breakdown_master.xlsx`）
- source of truth は `data/current` の current formal artifacts とする。
- runtime current enrichment は `status == APPLIED` のみを保持する。
- `SKIPPED_*` / `BATCH_PARSE_FAILED` などの非APPLIED行は history/audit 側に保持し、runtime current へ混在させない。
- summary/path 記録は canonical current path を指す。

修正1〜修正5で確定した契約
- 修正1（closeout / current-write）
  - `rag_gellery_breakdown_master.xlsx` は current formal artifacts から導出する。
  - closeout 系は `current_write -> skip_registry_gallery_list_cleanup -> xlsx_update -> r2_sync` の順で運用する。
- 修正2（current enrichment source-of-truth）
  - Artist / Exhibition とも current runtime は materialized current builder を通す。
  - raw/current/history の整合を保持し、runtime current と history/audit を分離する。
- 修正3-A〜3-D（Exhibition Text）
  - stale request は current raw 基準で自動再同期する。
  - `openai_output_not_json` は tolerant parse で汎用救済する。
  - Exhibition Text は `rag_gellery_breakdown_master.xlsx 446 / raw 446 / current enrichment 446 / loader enriched 446` へ到達済み。
- 修正4（Artist vector / loader）
  - `artists text vector` は `fair_slug + normalize_url(source_url) + text_hash` を canonical row key とする。
  - `artist works images vector` は `image_id` を row key とする。
  - Artist loader dedup は `fair_slug + normalized source_url + text_hash` 契約で固定する。
- 修正5（`rag_gellery_breakdown_master.xlsx` Artist一致列）
  - Artist一致列（総抽出Artist数 / 画像テキストArtist一致数 / Artist一致率）は shared artist match key で算出する。
  - `テキスト抽出Artist数` は text canonical row key 件数として維持する。

名前ベース契約（Artist / Exhibition 境界）
- Artist
  - cross-gallery same-name skip は収集段の契約として実装済み。
  - first-write-wins global no-refetch を維持する。
- Exhibition
  - 同姓同名アーティスト名 / 同名展覧会名を理由に skip しない。
  - skip は year判定・source_url既知・text hash重複・gallery skip 契約など別理由でのみ実施する。

dedup と skip の役割分離
- source_url dedup: 同一URL再訪抑止。
- canonical key dedup: vector/loader の重複排除。
- gallery skip: `all_rag_zero` / `exhibition_text_only` の館単位除外。
- Artist cross-gallery same-name skip: 収集段の global artist identity 契約。

`rag_gellery_breakdown_master.xlsx` 表示契約（標準デフォルト）
- `rag_gellery_breakdown_master.xlsx` は合計数表示を標準デフォルトとする。
- フェア別合計と全体合計を維持する。
- 今後の `rag_gellery_breakdown_master.xlsx` 更新でも合計数表示を消さない。
- `rag_gellery_breakdown_master.xlsx` の値は current formal artifacts から機械導出する。

`rag_gellery_breakdown_master.xlsx` 反映時の根拠入力群整合ルール（再発防止）
- `rag_gellery_breakdown_master.xlsx` の Artist側 B〜H は artist raw と artist image metadata、Exhibition側 I〜M は exhibition raw と exhibition image metadata を根拠入力群として current formal artifacts から算出する。
- closeout apply / xlsx_update で trial root を使う場合は、artists / exhibitions それぞれの raw と image metadata が同一scope / 同一trial-current文脈で current_write に反映済みであることを前提確認する。
- enrichment / vector の成立だけでは Artist側 B〜H の根拠にはならない。Artist側 B〜H を更新するには artist raw と artist image metadata の根拠入力群が必要である。
- closeout apply 後の `rag_gellery_breakdown_master.xlsx` 人間確認では、Artist側 B〜H と Exhibition側 I〜M の片側だけが説明不能に 0 になっていないかを確認する。片側だけ 0 の場合は完了扱いにせず、根拠入力群 / trial root / current_write の整合を直して same scope で再反映する。

count の読み方（運用固定）
- row/slot count
  - `Artistテキスト数`: raw row count
  - `Artist画像枚数`: image metadata slot count
- canonical key count
  - `テキスト抽出Artist数`: `normalize_url(source_url) + text_hash`
  - Artist Works vector: `image_id`

block必須工程チェックリスト（圧縮索引）
1. 次 block 再開判定
2. scope 定義
3. raw verify-first
4. artists image collect verify-first
5. exhibitions image collect verify-first
6. `rag_gellery_breakdown_master.xlsx` 更新 + 人間確認（抽出率・館ごとの中身確認の早期確認）
7. artists enrichment preflight
8. artists enrichment submit
9. artists enrichment check
10. artists enrichment apply
11. exhibitions enrichment preflight
12. exhibitions enrichment submit
13. exhibitions enrichment check
14. exhibitions enrichment apply
15. artists text vector verify-first
16. artist works images vector verify-first
17. run_block_closeout verify-first（Artist作品画像 duplicate audit gate 含む）
18. run_block_closeout apply（R2なし）
19. closeout / cleanup 反映後の更新済み `rag_gellery_breakdown_master.xlsx` 人間確認（最終整合確認）
20. `current_required_rag_full` plan
21. `current_required_rag_full` apply
22. `current_required_rag_full` post-check
23. docs同期

raw verify-first→artists image collect verify-first 成果物受け渡し固定ルール（再発防止）
- raw verify-first には、`dry-run 診断` と `rebuild verify-first（artists raw trial生成）` の2種類がある。
- `dry-run 診断` は診断JSONのみを出力し、artists image collect verify-first 用の artist raw artifact は生成しない。
- artists image collect verify-first を成立させるには、raw verify-first を同一scope の `rebuild verify-first` として実行し、`--include-artists-text` を付与して同一 `trial_root` / 同一 `run-id` に artist raw artifact を作る。
- artists image collect verify-first は、同一 `trial_root` / 同一 `run-id` / 同一scope 配下の `data/current/raw/artists_*_2025.jsonl` を入力前提として読む。
- `raw verify-first dry-run 診断 -> そのまま artists image collect verify-first` は禁止とする。
- 正しい導線は `raw verify-first dry-run 診断（入口確認）` または `raw verify-first rebuild verify-first（artists raw trial生成）-> artists image collect verify-first` とする。

工程6 / 工程19 の確認対象固定（再発防止）
- 工程6と工程19の確認対象は、常に公式 `rag_gellery_breakdown_master.xlsx` とする。
- `_trial` 配下の CSV / MD / JSON は確認補助資料であり、`rag_gellery_breakdown_master.xlsx` の代替にはしない。
- 工程6 / 工程19 は、`rag_gellery_breakdown_master.xlsx` を更新・確認して初めて完了扱いとする。

closeout 前の必須ゲート（索引）
- 早期 `rag_gellery_breakdown_master.xlsx` 人間確認（工程6）完了前に enrichment 工程（工程7以降）へ進まない。
- 工程7（artists enrichment preflight）開始前に、scope 対象の request 母集団が存在することを確認する。
- 工程7は、scope・io_root・request lane が一致した状態で実行する。
- 工程7で `exit 0` / `status ok` でも、`scoped_request_rows=0` または `target_rows=0` は blocker として扱う。
- `target_rows=0` の場合は工程8 `artists enrichment submit` へ進まない。
- 工程7が `target_rows=0` の場合は、同一Task内で「request 母集団確認 → 必要なら same scope / same io_root で request 生成 → preflight 再実行」まで実施し、不要なTask分割を行わない。
- raw verify-first→artists image collect verify-first の成果物受け渡し条件（同一scope / 同一trial_root / 同一run-id の artist raw成果物）が未成立の場合は artists image collect verify-first を開始しない。
- `rag_gellery_breakdown_master.xlsx` と current raw の突合はカテゴリ別（artists / exhibitions 別）で行い、片側 0/0 を館全体 raw なしと誤読しない。
- 未完了工程が1つでもある場合は `run_block_closeout apply（R2なし）` へ進まない。
- Exhibition enrichment（preflight / submit / check / apply）を飛ばさない。
- `run_block_closeout verify-first` は current Artist作品画像 duplicate audit を含み、`duplicate_cluster_count > 0` または `blocking_errors` がある場合は closeout apply へ進まない。
- 工程19の `rag_gellery_breakdown_master.xlsx` 人間確認完了前に `current_required_rag_full` へ進まない。
- block 完了後の正式 R2 手順は narrow hotfix sync ではなく `current_required_rag_full` を用いる。
- `current_required_rag_full` は `plan -> apply -> post-check` を必ず順に実行し、`missing local->R2 = 0`、`remote_only = 0`、`size_mismatch = 0` を確認する。
- `current_required_rag_full` post-check 完了前に次 block を開始しない。

今後の Codex task 作成固定ルール（索引）
- 毎回「この block の必須工程一覧」を明記する。
- 毎回「今回がどの段階か」を明記する。
- 毎回「未完了工程が残るなら次へ進まない」を明記する。
- closeout 後の R2 手順として毎回 `current_required_rag_full` の `plan / apply / post-check` を task 本文に明記する。
- `run_block_closeout verify-first` task には「Artist作品画像 duplicate audit gate を含む」ことを毎回明記する。
- `rag_gellery_breakdown_master.xlsx` の合計数表示（フェア別合計 + 全体合計）は標準デフォルトとして維持し、今後の更新でも消さない。

次タスク入口（docs同期後）
- まず `次 block 再開判定` に進む。
- 再開判定では、直前 block の `current_required_rag_full` 完了ログと duplicate gate 導線固定済みであることを前提確認する。
- 再開判定完了前に次 block 開始へは進まない。

block 完了ごとの個別履歴・数値結果は `04_TASK_PROGRESS_LOG.md` を参照する。


固定原則
- app/readonly は current-first を維持する。
- source/derived/vector/logs のファミリー分離を崩さない。
- 取得ループ内でLLM加工をしない（fetch と enrichment を分離）。

2026-04-18 アプリ機能調整ラウンド同期（現行仕様）
- 本節は、前回 docs 同期以降にこのチャットで確定した「現行アプリ仕様」のみを追記する。
- 新ブロック再開前に、アプリ機能確認を優先する運用を採用した。

機能2 / 機能3（Exhibition Search / Artist Search）
- 検索結果は 30件ずつのページング表示を維持する。
- ページ切替 UI を用いる。
- 案内文・件数表示・検索結果表示の文字色は通常の黒字を標準とする。

機能7（Art Work Search）
- 案内文・件数表示・検索結果表示の文字色は通常の黒字を標準とする。
- upload 文字の重複表示を解消した状態を現行とする。
- 30件ページング前提を維持し、過剰表示を抑える。
- 画像未取得・不整合画像が不自然に上位へ出る挙動を抑制した現行実装を維持する。

機能4（Advisor）
- upload 文字重複を解消した現行表示を維持する。
- broad / 抽象質問でも参照多様性を持たせる。
- 固定テンプレは禁止し、broad 質問で同一参照への過度固定を避ける。

機能1（Art Pulse）現行仕様
- 3見出し固定は廃止し、単一記事1本を現行契約とする。
- 文字数目安は 1000字前後、実運用許容は 800〜1200字程度とする。
- 本文構成は、同一記事内で「指定年・指定フェアのトレンド」から「おすすめ Artist / Exhibition」へ自然接続する2構成とする。
- 主要固有名詞（Artist / Exhibition）は RAG 根拠ベースで扱う。内部知識は補完的にのみ利用可。
- 表示は本文 → サムネイル（最大4枚）→ 根拠URL の順とする。
- 根拠表示ラベルは `根拠URL` を用いる。
- 本文文字数表示は `/1000` を用いる。
- Artist 名 / Exhibition 名リンク付与は維持する。

Art Pulse 調整時の運用ルール
- API コスト抑制のため、Art Pulse の実テストはユーザー本人が実施する。
- Codex は静的確認と原因分析を担当し、live API テストを行わない。


2026-04-21 作品検索 現況（最小追補）
- 画像なし再発は先行検証で主因を「ヒット選定非抑制 + 旧パス / メタデータ / `id_map` 不整合」と確定し、プレビュー優先ロジックを採用した。
- `payload_hash` 全面結合補正は一度試行したが回帰を起こしたため撤回した。
- `SAFE_FULL 117` の限定補正と、`UNRESOLVED 150`（`dry-run` で旧ローカル実体全件存在確認）の限定昇格により現行キャッシュ側で救済した。
- 全4636行の再監査でプレビュー表示可能 `4636/4636`、画像なし残件 `0` を確認した。
- `liste` metadata 側未ベクトル化 40 件へ限定ベクトル化 + 限定追記を実施し、ベクトル成果物行数は `4636 -> 4676` となった。
- 機能1/4/7 の画像系は現行専用前提を維持する。



2026-04-22 Phase 3 ブロック完了同期（圧縮索引）
- 今回範囲は Phase 3 の `current` 必須 RAG 正式導線であり、raw verify-first から `current_required_rag_full post-check` まで完了した。
- closeout の正式引数として `--artists-raw-trial-root`、`--artists-image-metadata-trial-root`、`--exhibitions-image-metadata-trial-root` を使い、同一範囲 / 同一 trial-current 文脈で生データと画像メタデータを `current_write` に入れる運用を固定した。
- `Hauser & Wirth` は人間確認済みのため skip 維持とし、今回の再反映対象へ戻さない。
- `rag_gellery_breakdown_master.xlsx` は再反映と人間確認が完了し、Artist側 0 問題は same scope の根拠入力群再反映で解消済みとする。
- `data/current/enrichment/*_enrichment_apply_output*.jsonl` は、`current` に採用済みの enrichment 結果を示す正規監査出力とする。成功した `current` 採用 1 元レコード = 1 JSONL 行で扱い、同一 `fair_slug + text_hash + source_url` の二重追加を禁止する。
- artists 正規監査出力は 1459 件、exhibitions 正規監査出力は 609 件。artists は `rag_gellery_breakdown_master.xlsx` の 1471 件と 12 件差があるが、raw 重複 6 件 + 未適用元レコード 6 件で説明可能であり、監査上の意味は整合している。
- `current_required_rag_full` は plan / apply / post-check まで完了し、post-check は `would_upload=0` / `would_prune=0` で完了した。

## 2026-04-24 Phase 3 block 完了ログ（工程18〜23）
- 現在地: Phase 3 の当該 block は工程23（docs同期）まで完了。
- 直前 block の remote parity は current_required_rag_full post-check で 0差分を確認（would_upload=0 / would_prune=0 / missing=0 / remote_only=0 / size_mismatch=0）。
- exhibitions 迂回処理は full stuck batch cancel、completed canary A/B 再利用、delta-only 75件（25+50）で回復し、apply 85件完了。
- 運用固定: exhibition_text_only は非skip、exhibition_image_only のみ skip。
- 状態固定: Silke Lindner は未skip維持、Petrine は skip 維持。
- 5（exhibitions image collect verify-first）で発生した公式更新副作用事故を起点に、verify-first で公式4ファイルを更新しない恒久ガードを導入して再発防止を固定。
- 今後方針: enrichment は delta-only（既取得・既適用済みの再送禁止、未取得・欠損・未適用・失敗分のみ処理）。
- 18. run_block_closeout apply（R2なし）完了。
- 19. rag_gellery_breakdown_master.xlsx 人間確認 OK。
- 20. current_required_rag_full plan 完了（would_upload=19 / would_prune=0 / missing=0 / remote_only=0 / size_mismatch=19）。
- 21. current_required_rag_full apply 完了（uploaded_count=19 / deleted_count=0 / upload_failed_count=0 / delete_failed_count=0）。
- 22. current_required_rag_full post-check 完了（would_upload=0 / would_prune=0 / missing=0 / remote_only=0 / size_mismatch=0）。

## 2026-04-26 docs同期索引（Phase 3 今回block）
- 現在地: 今回blockは工程22（`current_required_rag_full post-check`）まで完了し、本工程23でdocs同期を実施。
- scope 10館（Frieze 5 + Liste 5）で raw / image / enrichment / vector / closeout / R2 まで完了。
- artists text vector は `--delta-candidates-jsonl` を標準導線とし、current raw 起点候補生成と `whole_current_rebuild` は通常blockで禁止。
- artist works images vector は trial生成（1628）→ duplicate cleanup（1625）→ closeout merge（current 7049→8674）を標準導線として固定。
- closeout duplicate gate 停止時は「trial-only cleanup → 17再確認 → 18 apply（R2なし）」で復帰する。
- R2正式同期は `current_required_rag_full` の `plan → apply（--max-delete 0）→ post-check` を実施し、最終差分ゼロ（would_upload=0 / would_prune=0 / remote_only=0 / size_mismatch=0）を完了条件とする。

## 2026-05-04 docs同期追記（運用ルール・検索画像修正・Cloud運用）

### 1) Codexのcommit/push運用
- 今後はCodexにcommit/pushを任せない。
- Codexの役割は、実装・静的確認・smoke・差分提示までとする。
- commit/pushはユーザー本人が実行する。
- Codexタスクには必ず以下を含める。
  - commitしない
  - pushしない
  - `git status --short` を提示
  - `git diff --stat` を提示
  - 変更ファイル一覧を提示
  - 確認結果を提示
  - ユーザー実行用のcommit/pushコマンド案のみ提示
- 旧テンプレの「commit/push済みを完了条件に含める」運用は廃止する。

### 2) Cloud確認の基本手順
- ユーザー本人のcommit/push後、Cloud挙動確認は以下を基本とする。
  1. 最新deploy確認
  2. Clear cache
  3. Reboot app
  4. 実画面確認
- 特に `app.py` / `phase2_*_readonly.py` / import / cache / 検索 / 画像表示 / R2参照 / current読み込み契約 / Streamlit表示関連の変更では毎回実施する。
- docs-onlyやローカル限定作業では必須ではない。
- Cloudログに古いImportErrorや古いapp.py相当の挙動が残る場合は、古いプロセス/キャッシュ残留を優先疑いとする。

### 3) ImportErrorの検証ルール
- `py_compile` 単体ではImportErrorを保証できない。
- app.pyやimport周り変更時は以下を必須検証とする。
  - `python -c "import app"`
  - `python -m py_compile app.py 関連readonlyファイル`
- `phase2_common_readonly.py` 等からdirect importを増やす場合は、定義名/import名/呼び出し側の突合を必ず行う。
- 不要なdirect import追加は避け、可能なら対象readonly内ローカルhelperで完結させる。

### 4) Art Work Search: Robert Barry型（B+C複合）
- 事象: Robert Barry / Francesca Mininiで、過去に「参考画像なし」や結果脱落が発生。
- 原因:
  - vector/raw/current cacheには存在し、画像実体も存在。
  - ただし `r2_key` / `image_url` が空で、`local_path` のみ current cache を参照。
  - Cloud想定ではlocal_path依存のみだとpreview判定で落ち、preview-gating後に結果から脱落しうる。
- 解決方針:
  - `local_path` が `data/current/images/cache/artist_works_images/...` を指す場合、文字列変換のみで derived `r2_key` を軽量補完。
  - 既存 `r2_key` がある場合は上書きしない。
  - 個別ハードコード（gallery/artist/source URL、blue/Robert Barry専用）禁止。
  - `data/current` 更新なし、R2アクセスなし、重い走査なし。
- 最終確認: Art Work Searchで `blue` / Robert Barry は画像付き表示を確認済み。

### 5) Art Work Searchで禁止する重い実装
- 検索導線で以下を禁止する。
  - `os.walk`
  - `rglob`
  - `images/cache` 全件scan
  - 全画像hash計算
  - 検索ごとの大量R2 HEAD/hydrate
  - 検索ごとの大量data URI生成
  - 全件画像解決
- 方針: row内既存フィールド + 軽量文字列変換を優先し、必要最小限・表示ページ分中心で解決する。

### 6) Artist/Exhibition Searchの「参考画像なし」方針
- Artist/Exhibitionでは「参考画像なし」カード自体は許容する。
- ただし画像なしカードは後方へ回す（削除しない）。
- 画像ありグループ内順位・画像なしグループ内順位は保持。
- total件数を減らさない。ページングは並び替え後に実施する。
- Art Work Searchとは性質が異なるため、Artist/Exhibitionでは画像なし完全排除を行わない。

### 7) Artist判定・Exhibition判定の現時点
- Artist Searchは、候補フィールド存在のみではなく実カード描画に近い画像解決基準で後方化する方式へ修正済み（実画面確認済み）。
- Exhibition Searchは現行後方化で実画面OK。現時点で追加修正は行わず、問題再発時のみ別Taskで描画条件との完全一致を検討する。

### 8) Artist/Exhibition 画像なし実体監査（2026-05-04）
- 監査ログ: `logs/artist_exhibition_no_image_integrity_audit_20260504.json`（アプリ必須ファイルではなくcommit対象はユーザー判断）。
- 監査キーワード: `絵画 / painting / installation / blue / sculpture / abstract`
- 結果:
  - Artist: 画像なし300件、`A=300`、`B/C/D/E/F/G=0`
  - Exhibition: 画像なし407件、`A=407`、`B/C/D/E/F/G=0`
- 判定: 監査範囲ではArtist/Exhibitionの画像なしはすべて真の画像なし。Robert Barry型はArtist/Exhibitionでは未検出。追加修正は不要。

