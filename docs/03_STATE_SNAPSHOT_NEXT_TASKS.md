03_STATE_SNAPSHOT_NEXT_TASKS
PROJECT_SLUG: ART_PULSE_EDITOR
LAST_UPDATED: 2026-03-30 JST

DOC_PATHS
- SSOT_01: `./docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
- DERIVED_02: `./docs/02_RAG_SPEC_DERIVED.md`
- STATE_03: `./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- LOG_04: `./docs/04_TASK_PROGRESS_LOG.md`

STATE_SNAPSHOT
- Feature 1 Art Pulse: completed
- Feature 2 Exhibition Search: completed
- Feature 3 Artist Search: stable / accepted for current scope
- Feature 4 Advisor: completed / accepted baseline
- Feature 6 Gallery list: current implementation exists
- Feature 7 ArtWork Search: current implementation exists / accepted for current scope
- current/history rebaseline lane: completed
- cleanup lane: closed
- immediate priority: explicit user taskベースで main roadmap を進める

ACTIVE DATA / RETRIEVAL FAMILIES
- Artist Works Images
- Artist Text
- Exhibitions Image
- Exhibitions Text

CURRENT OPERATING RULES
- app runtime は current-first を維持する
- shared/common は feature-specific logic で汚さない
- fetch / enrichment / vectorize / sync は family 分離を崩さない
- Feature 7 は独立 feature のまま維持する
- R2 apply / prune は explicit task のみで実施する

NEXT_TASKS
- [ ] Feature 3 / Feature 4 / Feature 7 の current-only runtime を verify-first で継続監視する
- [ ] Gallery list の read-only quality を必要時に微修正する
- [ ] current/history family の prune candidates は explicit task 時のみ整理する

REMOVAL SYNC NOTE (2026-03-30)
- 廃止済みの artist-specific advisor lane と、その専用 text corpus / config / vector / UI route / docs 記述は baseline から除外済みです。
- 今後の handoff では、現行構成を Feature 1 / 2 / 3 / 4 / 6 / 7 だけで扱います。

HANDOFF MEMO
- 仕様確認は 01 を最優先にする
- 実装判断の近道は 02 を参照する
- 進捗と next task はこの 03 を更新する
