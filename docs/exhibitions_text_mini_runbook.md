# Exhibitions Text Mini Runbook (TASK285)

## Scope
- This is a closeout-phase operation frame for Exhibitions Text controlled operation.
- Default mode is no recurring weekly proof-run.
- Full detailed runbook is incident-only.

## Normal Mode (minimum checks only)
1. Boundary non-overlap:
   - READY, ESCALATE, HOLDING, REJECT must remain disjoint (overlap=0).
2. Prior continuity:
   - expected prior run/state continuity must match before any write.
3. Backup integrity:
   - backup must be created and hash-matched before state update.
4. Post-check counters:
   - boundary/integrity/escalate_blocker counters must stay zero.

## Incident Mode (escalate to detailed runbook)
Enter detailed runbook only when any of these fire:
- `ratio_two_consecutive` fired
- `route_degradation` fired
- boundary breach
- integrity breach (`coverage_review`, `reject`, `join_blocker`, `escalate_blocker`)
- temporal gap anomaly
- monitored state corruption
- operation-relevant spec change (01/02)

## Restore / No-op
- No-op:
  - same-run re-ingestion must remain no-op.
- Restore:
  - restore immediately when fail-safe condition is met (state corruption, hash mismatch, boundary/integrity blocker).

## Manual Approval Gate
- ESCALATE -> READY reintegration always requires manual approval.
