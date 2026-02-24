# Phase1 Guard Fixtures

This directory provides reproducible JSON inputs for Phase1 guard/history smoke checks.

## One-command matrix runner (history compare)

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

## One-command matrix runner (guard category profile)

Run guard-category fixtures from `category_fixture_manifest.json`:

```bash
python run_phase1_guard_category_fixture_matrix.py
```

Optional fail-fast mode:

```bash
python run_phase1_guard_category_fixture_matrix.py --fail-fast
```

Wrapper exit code meanings:

- `0`: matrix pass (all cases matched expected exit codes and summary checks)
- `1`: matrix fail

Important: this runner executes `run_compare_phase1_guard.py` (guard本体) and validates both:

- expected exit code
- expected summary keys/values (`summary_checks_passed`)

## One-command matrix runner (category profile lint)

Run lint fixtures from `lint_fixture_manifest.json`:

```bash
python run_phase1_guard_lint_fixture_matrix.py
```

Optional fail-fast mode:

```bash
python run_phase1_guard_lint_fixture_matrix.py --fail-fast
```

Wrapper exit code meanings:

- `0`: matrix pass (all lint cases matched expected exit codes and summary checks)
- `1`: matrix fail

Important: this runner executes `run_phase1_guard_category_profile_lint.py` (lint本体) and validates both:

- expected exit code (`0/1`)
- expected lint summary keys/values (`summary_checks_passed`)

## One-command matrix runner (all guard matrices)

Run lint/category/history matrices sequentially:

```bash
python run_phase1_guard_all_matrices.py
```

Optional pretty output + explicit summary path:

```bash
python run_phase1_guard_all_matrices.py --output-json data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json --pretty
```

Wrapper exit code meanings:

- `0`: all matrix wrappers passed
- `1`: at least one matrix wrapper failed or was not executed

Important: this wrapper does not change inner matrix logic.  
Inner matrix wrappers still keep their own `0/1` contract, and inner CLIs keep existing exit rules (`guard 0/2`, `history 0/2/3`, `lint 0/1`).

### Lightweight integrated report (TASK44)

Generate a short triage report from integrated summary:

```bash
python run_phase1_guard_all_matrices_report.py --summary-path data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json
python run_phase1_guard_all_matrices_report.py --latest
```

Optional JSON output:

```bash
python run_phase1_guard_all_matrices_report.py --latest --output-json data/phase1_seed10/logs/phase1_guard_all_matrices_report_latest.json
```

Report CLI exit codes:

- `0`: report generated
- `1`: summary missing/invalid

Optional strict policy for CI:

```bash
python run_phase1_guard_all_matrices_report.py --summary-path data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json --fail-on-failed-matrix
```

Policy behavior:

- default (flag omitted): readable summary -> `exit 0` even when `all_passed=false`
- with `--fail-on-failed-matrix`: readable summary + `all_passed=false` -> `exit 1`

### Report CLI fixture matrix (TASK45)

Run fixed report fixtures (valid/missing/bad_json) in one command:

```bash
python run_phase1_guard_all_matrices_report_fixture_matrix.py
```

Run policy-mismatch negative fixture (expected wrapper fail):

```bash
python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json
```

Cases:

- `report_valid_summary` -> expected exit `0`
- `report_missing_summary` -> expected exit `1`
- `report_bad_json_summary` -> expected exit `1`
- `report_failed_summary_default_policy` -> expected exit `0`
- `report_failed_summary_strict_policy` -> expected exit `1` (`--fail-on-failed-matrix`)

Matrix wrapper exit codes:

- `0`: all fixture cases matched expected result
- `1`: at least one fixture case mismatch
- negative policy manifest is expected to return wrapper exit `1` (failure is the expected result)

Policy-visibility keys in matrix `cases[]` (TASK47):

- `fail_on_failed_matrix` (input flag used for the case)
- `policy_expected` (manifest-defined expected policy)
- `policy_actual` (read from report output JSON `exit_policy`)
- `policy_match` (`policy_expected == policy_actual`)

Policy guard keys in matrix `cases[]` (TASK48):

- `policy_check_mode` (default: `enforce_when_available`)
- `policy_guard_applied` (`policy_actual` is available)
- `policy_guard_passed`
- `policy_guard_reason`

Guard behavior:

- if `policy_actual` exists and `policy_check_mode=enforce_when_available`, `policy_match=false` makes the case fail
- if `policy_actual` is unavailable (missing/bad_json), case keeps backward-compatible warning-only handling

## Cases

- `pass`: compatible comparison, no regression, expected exit code `0`
- `regression`: compatible comparison with regression, expected exit code `2` (`--fail-on-regression`)
- `incompatible`: incompatible comparison, expected exit code `3` (`--strict-compatibility`)
- `category_mismatch_non_strict`: category only mismatch, expected exit code `0` (warning-only, comparison continues)
- `category_mismatch_strict`: category only mismatch, expected exit code `3` (`--strict-compatibility`)
- `artists_history_compatible`: artists_text vs artists_text, expected exit code `0`
- `artists_vs_exhibitions_category_mismatch_non_strict`: artists_text vs exhibitions_text (non-strict), expected exit code `0`
- `artists_vs_exhibitions_category_mismatch_strict`: artists_text vs exhibitions_text (strict), expected exit code `3`

Fixture metadata is defined in `fixture_manifest.json`.

Guard category fixture metadata is defined in `category_fixture_manifest.json`.
Lint fixture metadata is defined in `lint_fixture_manifest.json`.

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

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/artists_history/current_artists_compatible_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/artists_history/baseline_artists_compatible_2025.json \
  --fail-on-regression
```

Expected exit code (artists compatible): `0`

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/artists_history/current_artists_compatible_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/artists_history/baseline_exhibitions_2025.json
```

Expected exit code (artists vs exhibitions non-strict): `0`

```bash
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/artists_history/current_artists_compatible_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/artists_history/baseline_exhibitions_2025.json \
  --strict-compatibility
```

Expected exit code (artists vs exhibitions strict): `3`

## Option flags reminder

- `--fail-on-regression`: return non-zero only when regression is detected (compatible comparison).
- `--strict-compatibility`: return non-zero when compatibility checks fail.
- matrix runner `--fail-fast`: stop at the first expected/actual mismatch.

## Category profile fixtures (guard CLI)

Category profile fixtures are under `tests/fixtures/phase1_guard/category/`:

- `artists_reserved_warning`: no `artists_*_<year>.jsonl` in fixture raw dir
  - expected: `category_support_mode=reserved_minimal`
  - expected: `category_data_presence.has_artists_data=false`
- `artists_provisional_pass`: has `artists_*_<year>.jsonl` in fixture raw dir
  - expected: `category_support_mode=provisional_minimal`
  - expected: `category_data_presence.has_artists_data=true`

Individual commands:

```bash
python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir tests/fixtures/phase1_guard/category/artists_reserved_warning/logs
python run_compare_phase1_guard.py --target-year 2025 --category artists_text --logs-dir tests/fixtures/phase1_guard/category/artists_provisional_pass/logs
```

Summary keys to read:

- `category_support_mode`
- `category_support_mode_configured`
- `required_summary_keys_effective`
- `category_activation_conditions`
- `category_data_presence`
- `category_warnings`

Category fixture matrix checks (TASK41):

- reserved case:
  - `category_support_mode=reserved_minimal`
  - `category_activation_conditions` non-empty
  - `category_data_presence` exists and `has_artists_data=false`
- provisional case:
  - `category_support_mode=provisional_minimal`
  - `category_activation_conditions` non-empty
  - `category_data_presence` exists and `has_artists_data=true`

## Category profile lint fixtures

Lint fixture files are under `tests/fixtures/phase1_guard/lint/`:

- `valid/phase1_guard_category_profiles_valid.json`
- `bad_json/phase1_guard_bad_config.json`
- `bad_schema/phase1_guard_bad_schema_config.json`
- `missing/phase1_guard_missing_config.json` (intentionally absent)

Individual commands:

```bash
python run_phase1_guard_category_profile_lint.py --config-path tests/fixtures/phase1_guard/lint/valid/phase1_guard_category_profiles_valid.json
python run_phase1_guard_category_profile_lint.py --config-path tests/fixtures/phase1_guard/lint/missing/phase1_guard_missing_config.json
python run_phase1_guard_category_profile_lint.py --config-path tests/fixtures/phase1_guard/lint/bad_json/phase1_guard_bad_config.json
python run_phase1_guard_category_profile_lint.py --config-path tests/fixtures/phase1_guard/lint/bad_schema/phase1_guard_bad_schema_config.json
```

Expected lint exit codes:

- valid: `0`
- missing: `1` (`config_missing:*`)
- bad json: `1` (`config_json_decode_error:*`)
- bad schema: `1` (`config_schema_error:*`)

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

## Artists history fixture checks

`artists_history_*` cases are dedicated to TASK36 category-context reproducibility in artists flow.

Read these keys in generated history summary:

- `current_category`
- `baseline_category`
- `category_comparison_mode`
- `category_effective_for_comparison`
- `category_compatible`
- `comparison_compatible`
- strict mismatch only: `compatibility_errors` contains `category_mismatch:*`
