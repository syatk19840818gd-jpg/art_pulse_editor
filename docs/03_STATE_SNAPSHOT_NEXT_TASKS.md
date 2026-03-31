03_STATE_SNAPSHOT_NEXT_TASKS
PROJECT_SLUG: ART_PULSE_EDITOR
LAST_UPDATED: 2026-03-31 JST

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
- R2 default sync contract is current-only mirror: `data/current` -> `data/current`
- R2 log canonical path is `logs/r2_sync/`; retired `data/r2_auto_sync/` lane must not be recreated
- one `sync` run reflects additions and deletions for current in the same scope
- `data/history` is excluded from R2 sync and is retained on GitHub side only
- `phase1_seed10` is retired from R2 and GitHub; keep it local-only only when a manual legacy helper still needs it
- new RAG outputs must write to `data/current/...` only
- preview / request report / legacy logs / trial artifacts use `data/runtime/...` neutral lanes, not `data/phase1_seed10/...`
- legacy local `phase1_seed10` helpers may remain on disk, but remote `phase1_seed10` is not part of the default sync mainline and new writes must not revive that path

NEXT_TASKS
- [x] R2 current-only mirror contract finalized in `run_r2_sync.py` / `config/r2_sync_targets.json`
- [x] R2 log lane unified to `logs/r2_sync/` and retired `data/r2_auto_sync/`
- [x] `data/history` removed from R2 sync targets
- [x] history remote residue cleanup applied live on R2 and post-check confirmed `would_prune=0`
- [x] `phase1_seed10` remote residue cleanup applied live on R2; final actual listing confirmed hidden `.bak` residue removed and prefix now empty
- [x] local `phase1_seed10` write paths retired; canonical RAG outputs remain `data/current/...` and local-only helper artifacts now use neutral runtime paths
- [x] Tarutani_data remote residue cleanup applied live on R2 and post-check confirmed `would_prune=0`
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
