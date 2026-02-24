# Phase1 Guard Fixtures

This directory provides reproducible JSON inputs for Phase1 guard/history smoke checks.

## One-command matrix runner (recommended)

Run all fixture cases from `fixture_manifest.json`:

```bash
python run_phase1_guard_fixture_matrix.py
```

Optional fail-fast mode:

```bash
python run_phase1_guard_fixture_matrix.py --fail-fast
```

Wrapper exit code meanings:

- `0`: matrix pass (all cases matched expected exit codes)
- `1`: matrix fail (at least one mismatch or execution error)

Important: inner CLI exit codes (`run_compare_phase1_guard_history.py`) are still `0/2/3`.
The matrix runner treats those as case expectations and validates them per fixture.

## Cases

- `pass`: compatible comparison, no regression, expected exit code `0`
- `regression`: compatible comparison with regression, expected exit code `2` (`--fail-on-regression`)
- `incompatible`: incompatible comparison, expected exit code `3` (`--strict-compatibility`)

Fixture metadata is defined in `fixture_manifest.json`.

## Recommended order

1. Guard CLI sanity check

```bash
python run_compare_phase1_guard.py --target-year 2025
```

2. History compare with fixed fixtures

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/pass/current_pass_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/pass/baseline_pass_2025.json \
  --fail-on-regression
```

Expected exit code: `0`

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/regression/current_regression_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/regression/baseline_regression_2025.json \
  --fail-on-regression
```

Expected exit code: `2`

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json \
  --strict-compatibility
```

Expected exit code: `3`

## Option flags reminder

- `--fail-on-regression`: return non-zero only when regression is detected (compatible comparison).
- `--strict-compatibility`: return non-zero when compatibility checks fail.
- matrix runner `--fail-fast`: stop at the first expected/actual mismatch.
