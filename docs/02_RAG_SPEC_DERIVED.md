02_RAG仕様_派生索引
版: 2026-04-02 JST
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

fixed10再実行クローズアウト（2026-04-02）
- fixed10再実行ブロックは条件付きGOでクローズ済み。
- year gate / 2-digit date extraction の verify-first 改善を経て再実行を実施。
- Exhibitions Text の delta-only 再実行が完了。
- Exhibition Image の delta-only 再実行が完了。
- exhibitions enrichment の apply 件数: 27。
- artists enrichment の apply 件数: no-op。
- xlsx 再更新: overwrite=10 / append=0。
- Exhibition cap は 25 に変更済み。
- Chris Sharp Gallery は改善反映あり。
- residual は継続監視とし、Bombon は 403 residual、Callirrhoë は image 0 residual を明記して維持する。
- 次順序は docs 更新 -> Artist 側タスク -> initial10 Exhibitions delta-only backfill。

enrichment model 統一（artists / exhibitions 共通）
- `artist_name_kana` は `gpt-5-mini`
- `headline_ja` は `gpt-5-mini`
- `summary_ja` は `gpt-5-mini`

固定原則
- app / readonly は current-first を維持する。
- source / derived / vector / logs のファミリー分離を崩さない。
- 取得ループ内でLLM加工をしない。Fetch と enrichment は分離する。
- 画像検索の機能7は既存 Artist Works Images を再利用し、新しいRAGファミリーは追加しない。
- current は日常参照の正本、history は監査用、R2 は current ファミリーの永続同期先とする。

カード01: current-first runtime
- app runtime は `data/current/...` を第一参照にする。
- local は作業用 fallback として扱い、永続の正本役にはしない。

カード02: gallery / fair 分離
- Frieze London と Liste Art Fair Basel は、raw / derived / vector / logs の各ファミリーで混在させない。
- CSV由来の gallery list を起点に処理する。

カード03: enrichment 分離
- Fetch は取得と保存に集中する。
- `headline_ja` / `summary_ja` / `artist_name_kana` の後処理は enrichment batch に分離する。
- artists / exhibitions の enrichment model は `gpt-5-mini` 統一を維持する。

カード04: vector ファミリー
- Artist Text vector family と Artist Works Images vector family は別管理にする。
- Exhibitions Text / Exhibitions Image も同様にファミリーを分ける。
- manifest による差分同期を前提にし、個別の存在確認で運用しない。

カード05: アプリ機能ベースライン
- 機能4 Advisor は accepted baseline として維持する。
- 機能6 Gallery list は read-only 一覧機能として維持する。
- 機能7 ArtWork Search は独立機能として維持し、Advisor 系へ吸収しない。

カード06: 保存と同期
- R2 remote mutation は guarded flow でのみ扱う。
- R2 の本契約は current-only mirror とし、`data/current` 全体を1 scope で扱う。
- R2 log canonical path は `logs/r2_sync/` とし、plan / apply / post-check / listing / run log はこの1レーンに統一する。旧 `data/r2_auto_sync/` レーンは retired とする。
- `data/history` は R2 sync 対象外とし、GitHub 側の保持に寄せる。R2 上の history residue cleanup は 2026-03-31 に完了済み。
- apply は `sync` 1回で current scope の upload + delete を反映し、例外は current 外の明示 scope に限定する。
- `phase1_seed10` は R2 mainline 契約外の legacy residue とし、2026-03-31 の実R2 listing で確認された hidden `.bak` object 1件を削除して remote residue cleanup を完了した。`phase1_seed10` は R2 にも GitHub にも保持せず、必要なら local-only に限定する。
- 新規RAG生成物は `data/current/...` だけを正規出力先とし、`data/phase1_seed10/...` への新規書き込みは read fallback を除いて禁止する。
- local legacy logs / preview helpers は残りうるが、default R2 sync 本流には含めない。継続利用する場合も canonical output は `data/current/...` に固定し、preview / request report / legacy logs / trial artifacts は `data/runtime/...` の中立 path に寄せる。

カード07: 出力衛生
- raw heading / source-like label / metadata leak を通常回答へ出さない。
- UI表示は人間向け本文を優先し、内部メモ文を先頭に出さない。

カード08: 2026-03-30 時点の削除ベースライン
- 専用の artist-specific advisor lane は廃止済み。
- その専用 text corpus / config / vector / docs / UI route は現行 baseline から除外済み。
- 今後の handoff / task planning では、現行構成に含まれないものとして扱う。
