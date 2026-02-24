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
- `category_mismatch_non_strict`: category only mismatch, expected exit code `0` (warning-only, comparison continues)
- `category_mismatch_strict`: category only mismatch, expected exit code `3` (`--strict-compatibility`)

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

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json
```

Expected exit code (non-strict): `0`

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json \
  --strict-compatibility
```

Expected exit code (strict): `3`

## Option flags reminder

- `--fail-on-regression`: return non-zero only when regression is detected (compatible comparison).
- `--strict-compatibility`: return non-zero when compatibility checks fail.
- matrix runner `--fail-fast`: stop at the first expected/actual mismatch.

## Schema version check (guard_schema_version)

- Fixture `pass`/`regression` pairs use matching `guard_schema_version` (`1.0`).
- `incompatible` fixture demonstrates compatibility failure by `target_year` mismatch; schema fields may be missing on one side and are treated as backward-compatible warnings.
- To test schema mismatch without modifying fixture originals, use temporary copies:

```bash
cp tests/fixtures/phase1_guard/pass/current_pass_2025.json /tmp/current_schema_mismatch.json
cp tests/fixtures/phase1_guard/pass/baseline_pass_2025.json /tmp/baseline_schema_mismatch.json
python - <<'PY'
import json
from pathlib import Path
p = Path('/tmp/current_schema_mismatch.json')
obj = json.loads(p.read_text(encoding='utf-8'))
obj['guard_schema_version'] = '2.0'
p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(p)
PY
```

Expected:

- non-strict: summary is produced and schema mismatch is recorded
- strict (`--strict-compatibility`): incompatible (`exit 3`)

## Category context check (history summary)

- history summary now stores category context:
  - `current_category`, `baseline_category`
  - `category_comparison_mode`
  - `category_effective_for_comparison`
  - `category_compatible`
- fixed fixture `category_mismatch/*` reproduces both-present mismatch:
  - non-strict: `exit 0`, `category_compatible=false`, warning-only
  - strict: `exit 3`, category mismatch is added to `compatibility_errors`
- verify these keys on category mismatch runs:
  - `current_category`, `baseline_category`
  - `category_comparison_mode`
  - `category_effective_for_comparison`
  - `category_compatible`
  - `category_warnings`
- old summary files without category are treated as backward-compatible warnings (`current_only` / `baseline_only` / `both_missing`), not immediate failure in non-strict mode.
