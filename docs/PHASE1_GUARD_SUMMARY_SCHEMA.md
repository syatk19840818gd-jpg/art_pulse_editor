# Phase1 Guard Summary Schema Guide

## 1. Purpose

This document fixes how to read summary JSON outputs from the Phase1 guard CLIs.

- Target CLI 1: `run_compare_phase1_guard.py` (single-run guard check)
- Target CLI 2: `run_compare_phase1_guard_history.py` (current vs baseline history compare)

The goal is to prevent interpretation drift in local operations and CI.
This guide standardizes:

- key meaning
- read order
- exit code interpretation
- fixture-based reproduction

This document does not change CLI logic. It is an operations reading guide.

## 2. Target CLIs and Basic Commands

### 2.1 Guard CLI (single-run)

```bash
python run_compare_phase1_guard.py --target-year 2025
python run_compare_phase1_guard.py --target-year 2025 --fail-on-mismatch
```

- `--fail-on-mismatch`: return non-zero only when mismatches exist (exit `2`)

### 2.2 History CLI (current vs baseline)

```bash
python run_compare_phase1_guard_history.py --current-summary "<path>"
python run_compare_phase1_guard_history.py --current-summary "<path>" --fail-on-regression
python run_compare_phase1_guard_history.py --current-summary "<path>" --strict-compatibility
```

- `--fail-on-regression`: return exit `2` when regression is detected
- `--strict-compatibility`: return exit `3` when comparison is incompatible

## 3. Guard Summary (`run_compare_phase1_guard.py`)

Typical file:

- `data/phase1_seed10/logs/phase1_guard_summary_YYYY_YYYYMMDDTHHMMSSZ.json`

### 3.1 Top-level keys (current schema)

- `started_at`
- `completed_at`
- `generated_by`
- `guard_schema_version`
- `target_year`
- `category`
- `category_profile_version`
- `category_profile_source`
- `category_profile_config_path`
- `category_profile_config_loaded`
- `category_profile_config_error`
- `category_profile_config_error_detail` (optional)
- `category_profile_config_version_effective`
- `category_required_files_profile`
- `required_input_files_effective`
- `required_summary_keys_effective`
- `category_support_mode`
- `category_support_mode_configured`
- `category_activation_conditions`
- `category_data_presence`
- `category_warnings`
- `logs_dir`
- `fail_on_mismatch`
- `guard_passed`
- `mismatches`
- `mismatch_fields`
- `additional_guard_checks`
- `additional_guard_check_results`
- `missing_keys`
- `skipped_checks`
- `input_paths`
- `check_results`

### 3.2 Core judgment keys

- `guard_passed`: final pass/fail boolean for this run
- `mismatch_fields`: mismatch identifiers (primary root cause list)
- `mismatches`: count of `mismatch_fields`

Category notes:

- `--category` default is `exhibitions_text` (backward-compatible default).
- category profile is loaded from external config by default (`config/phase1_guard_category_profiles.json`).
  - success: `category_profile_source=external_config`
  - missing/invalid config: `category_profile_source=builtin_fallback` and `category_profile_config_error` is recorded
    - `config_missing:*`
    - `config_json_decode_error:*`
    - `config_schema_error:*`
- unknown category values fall back to `exhibitions_text` and are recorded in `category_warnings`.
- `category_required_files_profile` is the effective required-files profile used for this run.
- `required_input_files_effective` shows which required inputs were actually resolved.
- `required_summary_keys_effective` shows category-specific required summary keys used in this run.
- current support modes:
  - `active`: `exhibitions_text`
  - `reserved_minimal`: `artists_text` (no artists data detected; activation conditions remain)
  - `provisional_minimal`: `artists_text` (artists data detected; still minimal profile)
- `category_activation_conditions` lists what must be satisfied to move beyond reserved mode.
- `category_data_presence` records artists-data detection signals (`raw_candidate_count`, etc.).
- `category_support_mode_configured` is the mode from profile definition, while
  `category_support_mode` is the effective mode after runtime detection.

### 3.3 Existing check groups (`check_results`)

- `run_summary_load`
- `required_summary_keys`
- `output_files`
- `visited_ledger`
- `failed_ledger`
- `internal_consistency`
- `summary_vs_ledger_counts`
- `failed_fetches_schema`
- `manifest`

### 3.4 Additional checks from TASK26

- `additional_guard_checks`:
  - `GX_SKIP_BREAKDOWN_SUM_MATCH`
  - `GX_FAILED_REASON_COUNTS_SUM_MATCH`
  - `GX_RECORDS_RELATIONS_MATCH`
- `additional_guard_check_results`: per-check status/passed/value details
- `missing_keys`: missing input keys (backward-compatible skip context)
- `skipped_checks`: checks skipped for backward compatibility

### 3.5 Data fields used by additional checks

- `skipped_total`
- `skip_breakdown` or `skipped_by_reason` (either accepted)
- `failed_fetches_reason_counts`
- `failed_fetches_total_ledger`
- `existing_records_total`
- `new_records_saved_total`
- `records_total_after_run`
- `records_saved_total` (semantic-aware check)

### 3.6 Recommended read order (single-run)

1. `guard_passed`
2. `mismatch_fields`
3. `additional_guard_check_results`
4. `check_results.internal_consistency`
5. `check_results.summary_vs_ledger_counts`
6. `input_paths` (what was actually compared)

## 4. History Summary (`run_compare_phase1_guard_history.py`)

Typical file:

- `data/.../phase1_guard_history_compare_YYYYMMDDTHHMMSSZ.json`

### 4.1 Top-level keys

- `started_at`
- `completed_at`
- `generated_by`
- `current_summary_path`
- `baseline_summary_path`
- `comparison_compatible`
- `compatibility_errors`
- `compatibility_warnings`
- `baseline_resolution_mode`
- `baseline_candidates_checked`
- `baseline_selected_reason`
- `baseline_auto_search_dir`
- `summary_glob_effective`
- `current_guard_schema_version`
- `baseline_guard_schema_version`
- `guard_schema_version_comparison_mode`
- `guard_schema_version_compatible`
- `guard_schema_version_policy`
- `current_category`
- `baseline_category`
- `category_comparison_mode`
- `category_effective_for_comparison`
- `category_compatible`
- `category_compatibility_policy`
- `category_warnings`
- `current_category_profile_config_source`
- `current_category_profile_config_path`
- `current_category_profile_config_loaded`
- `current_category_profile_config_error`
- `current_category_profile_config_error_detail`
- `current_category_profile_config_version_effective`
- `baseline_category_profile_config_source`
- `baseline_category_profile_config_path`
- `baseline_category_profile_config_loaded`
- `baseline_category_profile_config_error`
- `baseline_category_profile_config_error_detail`
- `baseline_category_profile_config_version_effective`
- `category_profile_config_comparison_mode`
- `category_profile_config_same_source`
- `category_profile_config_same_version`
- `category_profile_config_effective_for_comparison`
- `category_profile_config_warnings`
- `baseline_candidate_paths`
- `baseline_candidate_details`
- `diffs`
- `additional_guard_checks_diff`
- `additional_guard_checks_changed_fields`
- `additional_guard_check_transitions`
- `additional_guard_checks_comparison_mode`
- `additional_guard_checks_missing_in`
- `regression_passed`
- `regression_reasons`
- `fail_on_regression`
- `strict_compatibility`
- `exit_code`
- `exit_code_meaning`

### 4.2 Compatibility block

- `comparison_compatible`: whether baseline/current can be compared
- `compatibility_errors`: hard incompatibility reasons
- `strict_compatibility`: if true, incompatibility returns exit `3`

Schema version policy:

- `guard_schema_version_policy`: `both_present_must_match;missing_allowed_with_warning`
- `guard_schema_version_comparison_mode`:
  - `both_present`: compare exact string equality
  - `current_only`, `baseline_only`, `both_missing`: backward-compatible mode
- `guard_schema_version_compatible`:
  - `true` when equal in `both_present`, or when either side is missing
  - `false` only for `both_present` + mismatch

Strict/non-strict behavior:

- non-strict: schema mismatch is recorded in `compatibility_errors`, comparison summary is still written
- `--strict-compatibility`: schema mismatch is treated as incompatible (`exit 3`)
- missing schema version on old summary is warning-only (not immediate incompatible)

Compatibility evaluation order (summary perspective):

1. summary load and source CLI validity (`generated_by`/signature)
2. `target_year` compatibility
3. `guard_schema_version` compatibility (with backward-compatible missing handling)
4. `category` compatibility context (visualization-first; strict promotes mismatch to incompatible)

Category compatibility policy:

- `category_compatibility_policy`: `both_present_must_match;missing_allowed_with_warning;strict_mismatch_incompatible`
- `category_comparison_mode`:
  - `both_present`: category strings exist on both sides
  - `current_only` / `baseline_only` / `both_missing`: backward-compatible missing handling
- `category_compatible`:
  - `true` for matched categories or missing-side backward-compatible modes
  - `false` only when both present and mismatched
- `category_effective_for_comparison`:
  - resolved category context when possible
  - `unresolved_mismatch` when both present but mismatched
- strict/non-strict:
  - non-strict: mismatched category is warning-only and comparison continues
  - strict (`--strict-compatibility`): category mismatch is promoted into `compatibility_errors` and can return exit `3`

Category profile config context (visualization-only):

- history summary copies current/baseline guard config context:
  - `current_category_profile_config_*`
  - `baseline_category_profile_config_*`
- `category_profile_config_comparison_mode`:
  - `both_present` / `current_only` / `baseline_only` / `both_missing`
- `category_profile_config_same_source` and `category_profile_config_same_version`:
  - `true`/`false` when both values exist
  - `null` when either side is missing
- `category_profile_config_effective_for_comparison`:
  - typically `external_config`, `builtin_fallback`, `mixed`, or `unknown`
- `category_profile_config_warnings`:
  - records missing context and source/version mismatch as warning signals
- backward compatibility:
  - old summaries without config-context keys remain comparable
  - strict/non-strict behavior is unchanged by this block (warning-only, no new incompatibility rules)

### 4.3 Baseline resolution block

- `baseline_resolution_mode`: `manual`, `auto_*`, `auto_not_found`
- `baseline_auto_search_dir`: actual auto search directory
- `baseline_candidates_checked`: number of candidates scanned
- `baseline_selected_reason`: chosen baseline reason
- `summary_glob_effective`: candidate glob used in auto mode

### 4.4 Numeric/mismatch diffs

`diffs` includes:

- `records_saved_total`
- `skipped_total`
- `failed_fetches_total_ledger`
- `visited_pages_total_ledger`
- `mismatches`
- `mismatch_fields` (`added` / `removed` / `common`)

### 4.5 Additional check visualization (TASK27)

- `additional_guard_checks_diff`:
  - `changed_to_fail`
  - `changed_to_pass`
  - `changed_to_skipped`
  - `changed_from_skipped`
  - `unchanged_pass`
  - `unchanged_fail`
  - `unchanged_skipped`
  - `added_checks`
  - `removed_checks`
- `additional_guard_checks_changed_fields`: flattened changed check list
- `additional_guard_check_transitions`: check-by-check transition map
- `additional_guard_checks_comparison_mode`:
  - `both_present`, `current_only`, `baseline_only`, `both_missing`
- `additional_guard_checks_missing_in`: which side lacks additional check payload

### 4.6 Regression judgment (unchanged logic)

History regression reasons are based on existing logic:

- `guard_passed` baseline true -> current false
- `mismatches` increase
- new `mismatch_fields` added

These are emitted in `regression_reasons`.

## 5. Exit Codes (0/2/3)

Exit code meaning comes from `phase1_guard_common.py` and summary `exit_code_meaning`.

- `0`: pass (or no fail condition triggered by flags)
- `2`: regression (for history with `--fail-on-regression`) or mismatch (for guard with `--fail-on-mismatch`)
- `3`: incompatible (history with `--strict-compatibility`)

### 5.1 CLI + flag mapping

- Guard CLI:
  - no `--fail-on-mismatch`: always writes summary, exit can remain `0`
  - with `--fail-on-mismatch`: mismatches -> exit `2`
- History CLI:
  - with `--fail-on-regression`: regression -> exit `2`
  - with `--strict-compatibility`: incompatible -> exit `3`

## 6. Operations Read Order

### 6.1 Human (local)

1. check process exit code
2. open summary JSON
3. read `guard_passed` or `comparison_compatible` / `regression_passed`
4. read `mismatch_fields` or `regression_reasons`
5. read additional visualization fields for quick root-cause targeting

### 6.2 CI

1. gate on exit code (`0/2/3`)
2. upload summary artifact
3. parse:
   - `compatibility_errors`
   - `mismatch_fields`
   - `additional_guard_checks_changed_fields`

### 6.3 Triage priority

1. `compatibility_errors`
2. `mismatch_fields`
3. `additional_guard_checks_changed_fields`
4. `additional_guard_check_transitions`

## 7. Fixture Reproduction (minimum)

Base fixture directory:

- `tests/fixtures/phase1_guard/`

Commands:

```bash
# pass -> exit 0
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/pass/current_pass_with_additional_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/pass/baseline_pass_with_additional_2025.json

# regression -> exit 2
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/regression/current_regression_with_additional_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/regression/baseline_regression_with_additional_2025.json \
  --fail-on-regression

# incompatible -> exit 3
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/incompatible/current_incompatible_with_additional_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/incompatible/baseline_incompatible_2024.json \
  --strict-compatibility

# category mismatch (non-strict) -> exit 0
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json

# category mismatch (strict) -> exit 3
python run_compare_phase1_guard_history.py \
  --current-summary tests/fixtures/phase1_guard/category_mismatch/current_category_mismatch_2025.json \
  --baseline-summary tests/fixtures/phase1_guard/category_mismatch/baseline_category_mismatch_2025.json \
  --strict-compatibility
```

Category mismatch read points in history summary:

- `current_category`
- `baseline_category`
- `category_comparison_mode` (expected: `both_present`)
- `category_effective_for_comparison` (expected: `unresolved_mismatch`)
- `category_compatible` (expected: `false`)
- `category_warnings`
- strict mode: mismatch reason appears in `compatibility_errors`

### 7.1 Matrix runner summary (one-command entry)

Use one-command matrix execution:

```bash
python run_phase1_guard_fixture_matrix.py
```

Matrix summary file:

- `data/phase1_seed10/logs/phase1_guard_fixture_matrix_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `all_cases_passed`
- `total_cases`
- `passed_cases`
- `failed_cases`
- `cases` (each case result)
  - `case_name`
  - `expected_exit_code` (inner CLI expectation: `0/2/3`)
  - `actual_exit_code`
  - `summary_checks_passed`
  - `summary_check_failures`
  - `pass_fail`
  - `output_summary_path`
- `wrapper_exit_code` (matrix wrapper exit: `0/1`)

TASK36 artists-history fixture pair is included in this matrix:

- compatible: `artists_text` vs `artists_text` (`category_compatible=true`, exit `0`)
- mismatch strict: `artists_text` vs `exhibitions_text` + `--strict-compatibility` (exit `3`)

### 7.2 Category profile fixture matrix summary (guard CLI)

Use guard-category one-command execution:

```bash
python run_phase1_guard_category_fixture_matrix.py
```

Matrix summary file:

- `data/phase1_seed10/logs/phase1_guard_category_fixture_matrix_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `all_cases_passed`
- `cases[].expected_exit_code`
- `cases[].actual_exit_code`
- `cases[].summary_checks_passed`
- `cases[].summary_check_failures`
- `cases[].output_summary_path`
- activation-focused checks:
  - reserved: `category_support_mode=reserved_minimal`
  - provisional: `category_support_mode=provisional_minimal`
  - both: `category_activation_conditions` non-empty and `category_data_presence` present

### 7.3 Category profile config lint summary

Use config-only lint before guard runs:

```bash
python run_phase1_guard_category_profile_lint.py --config-path "config/phase1_guard_category_profiles.json"
```

Lint summary file:

- `data/phase1_seed10/logs/phase1_guard_category_profile_lint_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `checked_at`
- `source_cli`
- `config_path`
- `config_exists`
- `config_valid`
- `config_error_code`
- `config_error_detail`
- `category_profile_source` (`external_config` / `builtin_fallback`)
- `category_profile_config_loaded`
- `category_profile_config_version_effective`
- `exit_code` (`0=lint_pass`, `1=lint_fail`)

Error code families (aligned with guard config loader):

- `config_missing:*`
- `config_json_decode_error:*`
- `config_schema_error:*`

### 7.4 Category profile lint fixture matrix summary

Use one-command lint matrix execution:

```bash
python run_phase1_guard_lint_fixture_matrix.py
```

Matrix summary file:

- `data/phase1_seed10/logs/phase1_guard_lint_fixture_matrix_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `all_cases_passed`
- `total_cases`
- `passed_cases`
- `failed_cases`
- `cases[]`
  - `case_name`
  - `expected_exit_code` (lint expectation: `0/1`)
  - `actual_exit_code`
  - `summary_checks_passed`
  - `summary_check_failures`
  - `output_summary_path`
- `wrapper_exit_code` (`0=matrix_pass`, `1=matrix_fail`)

### 7.5 Integrated all-matrices summary (lint/category/history)

Use unified one-command execution:

```bash
python run_phase1_guard_all_matrices.py
python run_phase1_guard_all_matrices.py --output-json data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json --pretty
```

Integrated summary file:

- `data/phase1_seed10/logs/phase1_guard_all_matrices_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `all_passed`
- `wrapper_exit_code` (`0=all_pass`, `1=any_fail`)
- `execution_order` (default: `["lint", "category", "history"]`)
- `executed_matrices`
- `matrices[]`
  - `name`
  - `expected_exit_code` (matrix wrapper expectation: always `0`)
  - `actual_exit_code`
  - `pass_fail`
  - `summary_path` (nullable when matrix summary is missing)
  - `stdout_tail`
  - `stderr_tail`
  - `error` (wrapper launch error only)
- `warnings`

Operational note:

- This wrapper only orchestrates existing matrix wrappers.
- Inner matrix logic is unchanged.
- Use per-matrix `summary_path` to drill down into failure causes.

### 7.6 Integrated summary report CLI (TASK44)

Use report CLI for quick triage:

```bash
python run_phase1_guard_all_matrices_report.py --summary-path data/phase1_seed10/logs/phase1_guard_all_matrices_latest.json
python run_phase1_guard_all_matrices_report.py --latest
```

Optional report JSON:

```bash
python run_phase1_guard_all_matrices_report.py --latest --output-json data/phase1_seed10/logs/phase1_guard_all_matrices_report_latest.json
```

Report output keys:

- `all_passed`
- `wrapper_exit_code`
- `execution_order`
- `failed_matrices` (`name` / `actual_exit_code` / `summary_path`)
- `child_summary_paths`
- `fail_on_failed_matrix`
- `exit_policy`
- `exit_reason`
- `report_exit_code`

Report CLI exit codes:

- `0`: report generated
- `1`: summary not found or invalid JSON/schema

Policy option:

- `--fail-on-failed-matrix`
  - summary readable + `all_passed=true` -> `0`
  - summary readable + `all_passed=false` -> `1`
  - summary missing/invalid -> `1` (same as default)

### 7.7 Report CLI fixture matrix summary (TASK45)

Use one-command report fixture matrix:

```bash
python run_phase1_guard_all_matrices_report_fixture_matrix.py
python run_phase1_guard_all_matrices_report_fixture_matrix.py --manifest-path tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json
```

Matrix summary file:

- `data/phase1_seed10/logs/phase1_guard_all_matrices_report_fixture_matrix_YYYYMMDDTHHMMSSZ.json`

Minimum keys to read:

- `all_cases_passed`
- `cases[].expected_exit_code`
- `cases[].actual_exit_code`
- `cases[].summary_checks_passed`
- `cases[].summary_check_failures`
- `cases[].report_output_path`
- `cases[].fail_on_failed_matrix`
- `cases[].policy_expected` (manifest-defined)
- `cases[].policy_actual` (read from report output `exit_policy`)
- `cases[].policy_match`
- `cases[].policy_check_mode`
- `cases[].policy_guard_applied`
- `cases[].policy_guard_passed`
- `cases[].policy_guard_reason`
- `wrapper_exit_code` (`0=matrix_pass`, `1=matrix_fail`)

TASK46 policy cases included:

- `report_failed_summary_default_policy` (exit `0`)
- `report_failed_summary_strict_policy` (exit `1`, with `--fail-on-failed-matrix`)

TASK47 read-note:

- strict case should record `policy_actual=fail_on_failed_matrix`
- default case should record `policy_actual=default_report_only`
- when report JSON is not generated (missing/bad_json), `policy_actual` can be `null`

TASK48 policy guard note:

- summary top-level keeps `policy_check_mode` (default `enforce_when_available`)
- when `policy_actual` exists and `policy_match=false`, matrix case becomes fail
- when `policy_actual` is unavailable (missing/bad_json), keep warning-only backward compatibility

TASK49 negative fixture note:

- negative manifest: `tests/fixtures/phase1_guard/report_fixture_manifest_negative_policy.json`
- expected wrapper result for this manifest: `exit 1` (policy guard failure is intentional)

## 8. Backward Compatibility Notes (TASK26/27)

- Old guard summaries may not include `additional_guard_check_results`.
- History compare does not treat this as incompatibility.
- Missing additional check payload is represented by:
  - `additional_guard_checks_comparison_mode`
  - `additional_guard_checks_missing_in`
- This keeps comparison executable while making missing context explicit.
