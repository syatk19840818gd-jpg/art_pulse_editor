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
- R2: current 永続同期の主対象
- local fallback: R2未達/差分時に current 運用を継続するための補助

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
  - `_reports/` is migration/retention audit report lane
- requests runtime retention policy:
  - keep while batch is `in_progress` / `validating` / `finalizing`, or while resume path is open (`rerun_guard_verdict=resume_existing_batch` with active guard/lock).
  - deletable after batch reaches terminal state and history output/summary/manifest plus current promote verdict are fixed with batch/guard evidence fields.
  - long-term retention is not required because requests can be regenerated from raw when needed.
- verify status: runtime-path switch and retention safety verify are GO (preflight path checks + migration-report/file consistency + synthetic retention checks passed).

固定：writer/readers/sync責務
- writer:
  - write timestamped artifacts to history first
  - promote to current fixed filenames only after successful write
  - bulk apply promote requires batch evidence + rerun-guard evidence; evidence-missing runs must not promote to current
- readers (app/read-only/advisor):
  - current-first
  - migration period only: fallback to legacy `data/phase1_seed10/derived/*_enrichment_apply_output_2025_*.jsonl` latest glob
- R2:
  - primary persistent sync target = current
  - history is backup/audit lane (non-default runtime lane)

固定：anti-mixing / migration
- do not mix current and history in default query paths.
- app default readers must not point to history.
- runtime guarantee: app/read-only must continue to function even if history lane is absent.
- migration next step:
  - reorganize existing timestamped artifacts into history (no deletion-first policy)
  - bootstrap current from latest successful timestamped pair (apply_output + apply_summary) per category/year

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

Index update (2026-03-18):
- phase status:
  - feature 1 Art Pulse: completed
  - feature 2 Exhibition Search: completed
  - feature 3 Artist Search: incident-closed and stable
  - feature 4 Advisor:
    - type1 text-only question lane is completed/locked
    - type1 image-attached text-question lane is completed/locked
    - type1 text-only implemented set (derived index): selected/reference entity split, fixed prose helper ban, generic intent focus, same-focus ranking tuning, caption/page-description suppression, fragment guard, grounded enrichment, and OpenAI-path snippet-only suppression when anchor > 0
    - type1 image-attached implemented set (derived index): transient visual observation via in-memory image payload only, no persist/vectorize/RAG-mix, observation-first answer weighting, asked-mode alignment, display/describe/reference mode salvage, non-reference proper-noun suppression, and grounded reference only as secondary support when needed
  - advisor type2:
    - text-only -> image generation lane is accepted
    - fixed runtime is `gpt-image-1` / `low` / `1024x1024` / `1 image`
    - current prompt build keeps medium fidelity and visual-nucleus-first ordering
    - image-attached -> image generation lane remains pending validation/smoke and is the next validation/tuning target inside Feature 4
- current/history rebaseline: completed (A2-A9)
  - storage scaffold in `data/current/enrichment/` and `data/history/enrichment/{artists,exhibitions}/`
  - writer contract: history timestamp write first, then current fixed-name promotion only when batch evidence + rerun-guard evidence are present for bulk apply
  - reader contract: current-first + migration-only legacy fallback (history is not default ref)
  - R2 contract: current primary lane, history audit lane, guarded upload completed
- enrichment emergency override:
  - Artists / Exhibitions bulk apply must move to Batch API enforced mode before the next production-style apply
  - direct OpenAI remains allowed only for preview/sample lanes
- advisor readonly/context index:
  - advisor type1 context is grounded via existing current-first read-only routes
    - art pulse overview
    - exhibitions enrichment current output
    - artists enrichment current output
  - evidence refs/source refs are shown from read-only outputs
  - lane operation note: type1 text-only and image-attached lanes are now tiny-fix-only on regression recurrence; type2 text-only accepted scope stays stable while image-attached -> image generation is validated next

Next (from STATE/NEXT):
- A17_PHASE4_ADVISOR_TYPE2_IMAGE_ATTACHED_TO_IMAGE_GENERATION_SMOKE_01

