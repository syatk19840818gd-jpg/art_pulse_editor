02_RAG仕様_派生索引
版: 2026-04-10 JST
参照正本: `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`

目的
- 01 の運用要点を、実装時に参照しやすい形へ圧縮した索引です。
- 仕様の正本は常に 01 です。差分があれば 01 を優先します。

現行アプリ構成
- 機能1: Art Pulse
- 機能2: Exhibition Search
- 機能3: Artist Search
- 機能4: Advisor
- 機能6: Gallery list
- 機能7: ArtWork Search

現行RAG / 取得ファミリー
- Artist Works Images 系
- Artist Text 系
- Exhibitions Image 系
- Exhibitions Text 系

skip 契約（01 派生・2026-04-10 同期）
- `all_rag_zero` は既存の generic skip 契約として継続する。
- `exhibition_text_only` を `all_rag_zero` と同列の generic skip 判定として追加する。
- `exhibition_text_only` の判定条件は以下で固定する。
  - `artist_count == 0`
  - `artist_image_rows == 0`
  - `artist_image_count == 0`
  - `exhibition_count > 0`
  - `exhibition_image_count == 0`
- 判定実装は gallery/host 固定分岐ではなく shared helper 契約で扱う。
- closeout 契約にも接続し、closeout 主導線で同一ルールを適用する。

pre-enrichment 自動 skip
- `run_phase1_seed10_exhibition_image_collect.py` 終了後、raw+image 集計由来で pre-enrichment 判定を実施する。
- pre-enrichment 判定後は以下を自動実行する。
  - skip 判定
  - skip registry upsert
  - gallery list 除外
- downstream は skip registry を強制尊重する。
  - artists enrichment
  - exhibitions enrichment
  - artists text vector
  - artist works images vector

skip registry / active list
- skip registry 登録済み gallery は以下 3 館。
  - City Galerie Wien（`all_rag_zero`）
  - Copperfield（retroactive 追加、最終的に `exhibition_text_only` 扱い）
  - Coulisse Gallery（retroactive 追加、最終的に `exhibition_text_only` 扱い）
- 上記 3 館は active gallery list から除外済み。
- `data/current/raw/exhibitions_liste_2025.jsonl` から以下を purge 済み。
  - Copperfield 3 行
  - Coulisse Gallery 1 行
- 今後の target selection / Gallery list / phase1 runners / closeout 主導線は registry-aware 前提で自動除外する。

closeout 主導線の拡張
- `run_block_closeout` 主導線に `skip_registry_gallery_list_cleanup` ステージを追加する。
- 契約上の実行順は以下を含む。
  - `current_write`
  - `xlsx_update`
  - `skip_registry_gallery_list_cleanup`
  - `r2_sync`
- dry-run report は以下の出力を必須とする。
  - `all_rag_zero_detected_rows`
  - `skip_registry_plan`
  - `gallery_list_removal_plan`
- 将来の `all_rag_zero` / `exhibition_text_only` 館も block closeout 主導線で自動 skip される。
- 最終合格判定は引き続き workbook の人間確認を必須とする。

現在地（圧縮）
- true next block（`phase3_block_scope_candidate_after_new10.csv`）は完了。
- true next は closeout apply 完了・人間確認 OK まで到達済み。
- ただし `City Galerie Wien` は最終的に skip registry 側へ移管済み。
- 次 real scope block（active list / skip registry 反映後の 10 館）も closeout apply 完了・workbook OK 済み。
- 同 block 完了後、`Copperfield` / `Coulisse Gallery` は `exhibition_text_only` 契約へ昇格し、retroactive purge 済み。

API 無駄打ち禁止（今回の反映）
- 今回の skip/purge 契約追加は offline-only で実施する。
  - API 実行 0
  - rerun 0
  - closeout apply 0
  - R2 apply 0
  - docs 更新 0
- 今後も `exhibition_text_only` は pre-enrichment で停止し、無駄な API lane に流さない。

次タスク（短縮）
- skip registry 反映済み active list から、次の real scope を定義する。
- 次 block は raw verify-first から開始する。

固定原則
- app / readonly は current-first を維持する。
- source / derived / vector / logs のファミリー分離を崩さない。
- 取得ループ内でLLM加工をしない。Fetch と enrichment は分離する。
