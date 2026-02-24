#!/usr/bin/env bash
set -u

run_case() {
  local case_id="$1"
  local expected="$2"
  shift 2
  "$@"
  local actual=$?
  echo "[CASE] ${case_id} expected=${expected} actual=${actual}"
  if [ "${actual}" -ne "${expected}" ]; then
    return 1
  fi
  return 0
}

root="tests/fixtures/phase1_guard"

run_case "pass" 0 \
  python run_compare_phase1_guard_history.py \
    --current-summary "${root}/pass/current_pass_2025.json" \
    --baseline-summary "${root}/pass/baseline_pass_2025.json" \
    --fail-on-regression || exit 1

run_case "regression" 2 \
  python run_compare_phase1_guard_history.py \
    --current-summary "${root}/regression/current_regression_2025.json" \
    --baseline-summary "${root}/regression/baseline_regression_2025.json" \
    --fail-on-regression || exit 1

run_case "incompatible" 3 \
  python run_compare_phase1_guard_history.py \
    --current-summary "${root}/incompatible/current_incompatible_2025.json" \
    --baseline-summary "${root}/incompatible/baseline_incompatible_2024.json" \
    --strict-compatibility || exit 1

echo "[DONE] all fixture cases passed expected exit codes"
