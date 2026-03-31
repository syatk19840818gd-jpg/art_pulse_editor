03_STATE_SNAPSHOT_NEXT_TASKS
PROJECT_SLUG: ART_PULSE_EDITOR
LAST_UPDATED: 2026-03-31 JST

DOC_PATHS
- SSOT_01: `./docs/01_PROJECT_SPEC_CURRENT_FULL.docx`
- DERIVED_02: `./docs/02_RAG_SPEC_DERIVED.md`
- STATE_03: `./docs/03_STATE_SNAPSHOT_NEXT_TASKS.md`
- LOG_04: `./docs/04_TASK_PROGRESS_LOG.md`

STATE_SNAPSHOT
- Phase status: Phase 2 completed (user decision), Phase 3 gallery expansion is the next main stage
- Feature 1 Art Pulse: completed
- Feature 2 Exhibition Search: completed
- Feature 3 Artist Search: stable / accepted for current scope
- Feature 4 Advisor: completed / accepted baseline
- Feature 6 Gallery list: active read-only feature / verify-first completed
- Feature 7 ArtWork Search: current implementation exists / accepted for current scope
- current/history rebaseline lane: completed
- cleanup lane: closed
- immediate priority: Phase 3 gallery expansion by explicit user task only

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
- cleanup lane remains closed during Phase 3 expansion

PHASE 3 OPERATING POLICY (FIXED)
- Selection block is fixed at 10 galleries.
- Each 10-gallery block is always split as Frieze 5 + Liste 5.
- Selection order follows the provided CSV order (top-down alphabetical order).
- After every 10 galleries, `rag_gellery_breakdown_master.xlsx` must be updated.
- Human review of extraction rates is mandatory after every 10-gallery block.
- Standard progression target is up to 20 galleries per cycle.
- 30 galleries is not a standard operating target at this stage.
- The second 10-gallery block may start only after review of the previous 10-gallery block.
- 20 galleries is a two-block reviewed progression target, not a single unchecked bulk run.
- Expansion goal is stable repeatable operations with balanced speed and safety.

NEXT_TASKS
- [ ] Finalize the next 10-gallery block scope (Frieze 5 + Liste 5 in CSV top-down order).
- [ ] Run the next 10-gallery block under the fixed Phase 3 operating order.
- [ ] Update `rag_gellery_breakdown_master.xlsx` immediately after the block.
- [ ] Perform mandatory human review of extraction rates after the block update.
- [ ] Decide whether to proceed to the next 10 galleries within the same cycle.
- [ ] Continue main roadmap in explicit-user-task mode (cleanup lane remains closed)

REMOVAL SYNC NOTE (2026-03-30)
- Retired artist-specific advisor lane and dedicated text corpus / config / vector / UI route / docs are excluded from baseline.
- Ongoing handoff and task planning treat active baseline as Feature 1 / 2 / 3 / 4 / 6 / 7 only.

HANDOFF MEMO
- Read source-of-truth from 01 first.
- Use 02 as derived operating contract.
- Keep progress and next-task sync in this 03.
