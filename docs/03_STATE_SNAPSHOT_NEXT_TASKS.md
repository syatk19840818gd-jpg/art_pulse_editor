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
- Feature 6 Gallery list: active read-only feature / verify-first completed
- Feature 7 ArtWork Search: current implementation exists / accepted for current scope
- current/history rebaseline lane: completed
- cleanup lane: closed
- immediate priority: proceed main roadmap by explicit user task only

ACTIVE DATA / RETRIEVAL FAMILIES
- Artist Works Images
- Artist Text
- Exhibitions Image
- Exhibitions Text

CURRENT OPERATING RULES
- app runtime keeps current-first behavior
- shared/common remains feature-neutral
- fetch / enrichment / vectorize / sync keeps family separation
- Feature 7 remains an independent feature (not absorbed into Advisor)
- R2 apply / prune is executed only as explicit task

NEXT_TASKS
- [x] R2 remote residue prune by narrow scopes completed (post-check: narrow/broad `would_prune=0`)
- [x] Feature 6 Gallery list read-only quality verify-first completed (no issue found)
- [x] Feature 3 / Feature 4 / Feature 7 current-only runtime verify-first completed (no regression found)
- [ ] Continue main roadmap in explicit-user-task mode (cleanup lane remains closed)

REMOVAL SYNC NOTE (2026-03-30)
- Retired artist-specific advisor lane and dedicated text corpus / config / vector / UI route / docs are excluded from baseline.
- Ongoing handoff and task planning treat active baseline as Feature 1 / 2 / 3 / 4 / 6 / 7 only.

HANDOFF MEMO
- Read source-of-truth from 01 first.
- Use 02 as derived operating contract.
- Keep progress and next-task sync in this 03.
