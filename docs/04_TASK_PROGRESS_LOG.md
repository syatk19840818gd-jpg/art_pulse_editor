# 04_TASK_PROGRESS_LOG

Last updated: 2026-03-31 JST
Project: ART_PULSE_EDITOR

## 0. Document roles
- 01 is source-of-truth.
- 02 is the derived operating contract.
- 03 is current state and next tasks.
- 04 is implementation/progress log.

## 1. Current baseline
- Feature 1 Art Pulse: completed
- Feature 2 Exhibition Search: completed
- Feature 3 Artist Search: stable
- Feature 4 Advisor: accepted baseline
- Feature 6 Gallery list: active read-only feature
- Feature 7 ArtWork Search: active feature

## 2. 2026-03-30 baseline cleanup/removal sync
- Removed retired advisor lane UI / route / import / session state from app.
- Removed retired advisor readonly / draft / type2 files.
- Removed retired text corpus / vector / config / sync-log / import / enrichment / vectorize artifacts.
- Synced docs 01 / 02 / 03 / 04 to current baseline.

## 3. What remains preserved
- Feature 4 Advisor accepted baseline
- Feature 2 / 3 / 7 read paths
- current-first storage contract
- shared/common generic structure

## 4. Next-task policy
- Keep retired lane excluded from baseline.
- Keep task logs aligned only to Feature 1 / 2 / 3 / 4 / 6 / 7 baseline.
- Proceed the main roadmap by explicit user task.

## 5. 2026-03-30 closeout sync (this chat)
- R2 remote residue prune completed using narrow legacy scopes only.
- Post-check completed: narrow scopes and broad current scopes both `would_prune=0` for the pruned residues.
- Feature 6 Gallery list verify-first completed: read-only quality OK, no fix required.
- Feature 3 / 4 / 7 current-only runtime verify-first completed: no regression found.
- Feature 7 independent-feature contract remains intact (not absorbed into Advisor).
- No additional tiny-fix task is required at this point.

## 6. 2026-03-31 R2 current-only mirror finalization
- `config/r2_sync_targets.json` was simplified so the only default R2 mainline is `current_root_mirror` (`data/current` -> `data/current`).
- `data/history` was removed from R2 sync targets and is now treated as GitHub-side retention only.
- `run_r2_sync.py` keeps remote mutation behind `sync --apply`, and one sync run now reflects upload + delete together for the current mirror contract.
- Live plan confirmed `current_root_mirror` had `would_upload=0` and `would_prune=0`, while `tarutani_data_retired_mirror` had `would_prune=93`.
- Live apply deleted 93 objects from `data/Tarutani_data` on R2 with zero failures.
- Live post-check confirmed `current_root_mirror` and all Tarutani cleanup scopes at `would_prune=0`.

## 7. 2026-03-31 final remote residue cleanup
- Verify-first confirmed the current R2 mainline remained `data/current` only, and `phase1_seed10` was no longer present in active R2 sync targets.
- Verify-first found no active runtime or default sync dependency on remote `phase1_seed10`; remaining references are local legacy helpers / logs outside the default R2 mirror contract.
- Live plan for `history_remote_residue_cleanup` reported `would_prune=20`.
- Live plan for `phase1_seed10_remote_residue_cleanup` reported `would_prune=601`.
- Live apply deleted 20 objects from `data/history` and 601 objects from `phase1_seed10` on R2 with zero failures.
- Live post-check confirmed `current_root_mirror`, `history_remote_residue_cleanup`, and `phase1_seed10_remote_residue_cleanup` all at `would_prune=0`.

## 8. 2026-03-31 phase1_seed10 final retire-and-cleanup
- Actual R2 listing, not the previous post-check summary, was treated as source-of-truth for `phase1_seed10`.
- That listing found one remaining real object: `phase1_seed10/logs/failed_fetches_artists_seed10_2025.json.bak_20260301_134210`.
- `phase1_seed10` / `phase1_seed10/` placeholder keys were both absent; the visible folder came from the remaining real object, not a folder marker.
- Root cause: cleanup scopes still inherited global exclude `**/*.bak*`, so the prior cleanup plan/post-check did not see the leftover `.bak` object.
- `run_r2_sync.py` and `config/r2_sync_targets.json` were updated so explicit retired/cleanup scopes can ignore global excludes and fully converge remote prefixes to empty.
- Live re-plan then reported `would_prune=1` for `phase1_seed10_remote_residue_cleanup`.
- Live apply deleted that final object with zero failures.
- Final actual R2 listing returned `object_count=0`, and `head_object` for both `phase1_seed10` and `phase1_seed10/` returned 404.
- Final storage policy: `phase1_seed10` is not kept on R2 and is not promoted to GitHub retention; if any legacy helper still needs it, keep it local-only.

## 9. 2026-03-31 local phase1_seed10 path retirement
- Verified `data/phase1_seed10/...` references across config, preview scripts, enrichment helpers, collect scripts, and formalize/recovery helpers.
- Canonical RAG outputs were already shared-helper based and stayed on `data/current/...`; no active canonical output path is allowed to write under `data/phase1_seed10/...`.
- `phase2_art_pulse_config.py` now points the deprecated local legacy root alias at `data/runtime/legacy_phase1`, so leftover helper imports no longer recreate writes under `data/phase1_seed10/...`.
- Preview outputs moved to `data/runtime/enrichment_requests/_reports/previews/...`.
- Runtime request/request-summary artifacts from `run_enrichment_seed10.py` moved off the legacy lane to `data/runtime/enrichment_requests/...` and `_reports/...`, and the old automatic R2 sync hook was removed from that helper.
- Legacy-only logs / trial / trash helpers now resolve to neutral runtime paths instead of `data/phase1_seed10/...`.
- Repo-wide code search after the change found no remaining Python write path under `data/phase1_seed10/...`; the only direct path reference left is the `app.py` read fallback for old remote keys.

## 10. 2026-03-31 R2 log lane unification
- Verify-first confirmed active `run_r2_sync.py` already wrote plan / apply / listing / run logs to `logs/r2_sync/`.
- `data/r2_auto_sync/` contained only retired auto-sync residue: historical summary logs and an unused `auto_sync_state.json` for the old `phase1_*` auto-sync flow.
- `run_r2_sync.py` now labels `logs/r2_sync/` as the canonical R2 sync log directory.
- Retired `data/r2_auto_sync/` was removed so R2 logs/state no longer live in a parallel lane.

## 11. 2026-03-31 phase transition decision (Phase 2 closeout -> Phase 3)
- User decision is recorded as final for this project cycle: Phase 2 is closed/completed.
- Next roadmap stage is fixed as Phase 3: gallery expansion.
- Expansion operations keep the current contracts unchanged: current-only runtime, family separation, guarded sync, and fetch-enrichment separation.
- Cleanup lane remains closed; roadmap progress continues in explicit-user-task mode.
- Note for later verification: live enrichment batch smoke can be run as an optional follow-up check, but it is not a blocker for the Phase 2 to Phase 3 transition decision.

## 12. 2026-03-31 Phase 3 operating policy clarification
- Phase 3 does not use unchecked multi-wave execution.
- The formal review checkpoint remains every 10 galleries.
- Each selection block is fixed at 10 galleries with split `Frieze 5 + Liste 5`.
- Selection order follows the provided CSV order (top-down alphabetical order).
- `rag_gellery_breakdown_master.xlsx` update plus human review of extraction rates is required after each 10-gallery block.
- Standard speed target is up to 20 galleries per cycle.
- 30 galleries is not treated as the standard operating target at this time.
- The cycle target is achieved only by reviewed 10-gallery blocks; the second 10 starts only after review of the first 10.
- This policy is adopted to balance speed and operational safety while keeping explicit-user-task execution.
