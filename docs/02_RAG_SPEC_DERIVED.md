02_RAG_SPEC_DERIVED
版: 2026-03-30 JST
参照正本: `docs/01_PROJECT_SPEC_CURRENT_FULL.docx`

目的
- 01 の運用要点を、実装時に参照しやすい形へ圧縮した索引です。
- 仕様の正本は常に 01 です。差分があれば 01 を優先します。

現行アプリ構成
- Feature 1: Art Pulse
- Feature 2: Exhibition Search
- Feature 3: Artist Search
- Feature 4: Advisor
- Feature 6: Gallery list
- Feature 7: ArtWork Search

現行 RAG / retrieval family
- Artist Works Images
- Artist Text
- Exhibitions Image
- Exhibitions Text

固定原則
- app / readonly は current-first を維持する。
- source / derived / vector / logs の family 分離を崩さない。
- 取得ループ内で LLM 加工をしない。Fetch と enrichment は分離する。
- 画像検索 Feature 7 は既存 Artist Works Images を再利用し、新しい RAG family は追加しない。
- current は日常参照の正本、history は監査用、R2 は current family の永続同期先とする。

CARD 01: current-first runtime
- app runtime は `data/current/...` を第一参照にする。
- local は作業 fallback として扱い、永続の正本役にはしない。

CARD 02: gallery / fair split
- Frieze London と Liste Art Fair Basel は、raw / derived / vector / logs の各 family で混在させない。
- CSV 由来の gallery list を起点に処理する。

CARD 03: enrichment separation
- Fetch は取得と保存に集中する。
- `headline_ja` / `summary_ja` などの後処理は enrichment batch に分離する。

CARD 04: vector families
- Artist Text vector family と Artist Works Images vector family は別管理にする。
- Exhibitions Text / Exhibitions Image も同様に family を分ける。
- manifest による差分同期を前提にし、個別の存在確認で運用しない。

CARD 05: app feature baseline
- Feature 4 Advisor は accepted baseline として維持する。
- Feature 6 Gallery list は read-only 一覧機能として維持する。
- Feature 7 ArtWork Search は独立機能として維持し、Advisor 系へ吸収しない。

CARD 06: storage and sync
- R2 remote mutation は guarded flow でのみ扱う。
- local cleanup や docs sync は remote apply と切り離して扱う。
- prune は plan / review / apply を分ける。

CARD 07: output hygiene
- raw heading / source-like label / metadata leak を通常回答へ出さない。
- UI 表示は人間向け本文を優先し、内部メモ文を先頭に出さない。

CARD 08: deletion baseline as of 2026-03-30
- 専用の artist-specific advisor lane は廃止済み。
- その専用 text corpus / config / vector / docs / UI route は現行 baseline から除外済み。
- 今後の handoff / task planning では、現行構成に含まれないものとして扱う。
