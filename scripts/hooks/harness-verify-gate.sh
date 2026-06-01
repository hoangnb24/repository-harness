#!/usr/bin/env bash
# Harness verify gate — mechanical enforcement of the Pre-Close Verification
# Gate (docs/FEATURE_INTAKE.md) and lint hygiene. Invoked by .githooks/pre-commit
# and .githooks/pre-push. Blocks the git action (non-zero exit) when a gate
# fails. See docs/decisions/0014-distill-upstream-observability-concepts.md.
#
# Two gates:
#   1. Lint / quick-validate — auto-detected per stack; blocks on failure.
#   2. Verify Register integrity (docs/TEST_MATRIX.md) — blocks on any
#      `Result: fail` row; at commit time also blocks `never-run` when the
#      commit closes a stage (STAGE.md staged).
#
# Bypass: `git commit/push --no-verify` skips this hook entirely. Agents MUST
# NOT use --no-verify to bypass the gate without explicit human authorization
# (AGENTS.md § Harness Change Policy). A human override should carry a reason.

set -u

mode="${1:-pre-commit}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$repo_root" || exit 0

matrix="docs/TEST_MATRIX.md"
fail=0

say() { printf '%s\n' "$*" >&2; }

# --- Gate 1: lint / quick validate -----------------------------------------
run_validate() {
  local cmd="" s t pm
  if [ -f package.json ]; then
    pm="npm"; [ -f yarn.lock ] && pm="yarn"; [ -f pnpm-lock.yaml ] && pm="pnpm"
    for s in validate lint typecheck check; do
      if command -v jq >/dev/null 2>&1; then
        jq -e --arg s "$s" '.scripts[$s]' package.json >/dev/null 2>&1 || continue
      else
        grep -qE "\"$s\"[[:space:]]*:" package.json || continue
      fi
      case "$pm" in
        npm)  cmd="npm run $s --silent" ;;
        yarn) cmd="yarn $s" ;;
        pnpm) cmd="pnpm run $s" ;;
      esac
      break
    done
  fi
  if [ -z "$cmd" ] && [ -f Makefile ]; then
    for t in validate lint check; do
      grep -qE "^$t:" Makefile && { cmd="make $t"; break; }
    done
  fi
  if [ -z "$cmd" ] && [ -f Cargo.toml ]; then
    cmd="cargo clippy --quiet -- -D warnings"
  fi
  if [ -z "$cmd" ]; then
    say "  [lint] no validate/lint command detected — skipped"
    return 0
  fi
  say "  [lint] running: $cmd"
  if eval "$cmd" >&2; then
    say "  [lint] passed"
    return 0
  fi
  say "  [lint] FAILED — fix the errors above (do not bypass with --no-verify)"
  return 1
}

# --- Gate 2: Verify Register integrity --------------------------------------
# STAGE_CLOSE: this commit moves a stage forward (STAGE.md staged) → strict.
stage_close=0
if [ "$mode" = "pre-commit" ]; then
  if git diff --cached --name-only -- STAGE.md 2>/dev/null | grep -qx "STAGE.md"; then
    stage_close=1
  fi
fi

check_register() {
  [ -f "$matrix" ] || { say "  [verify] no $matrix — skipped"; return 0; }
  local violations
  violations="$(awk -v strict="$stage_close" '
    /^## / && !/^## Verification Register/ { inreg=0 }
    /^## Verification Register/ { inreg=1; next }
    inreg && /^\|/ {
      n=split($0, a, "|");
      story=a[2];     gsub(/^[ \t]+|[ \t]+$/,"",story);
      result=a[n-1];  gsub(/^[ \t]+|[ \t]+$/,"",result);
      rl=tolower(result);
      if (story=="Story" || story ~ /^-+$/ || story=="TBD" || story=="") next;
      if (rl ~ /fail/)                        print "fail\t" story " (Result: " result ")";
      else if (rl ~ /never-run/ && strict=="1") print "never-run\t" story " (Result: " result ")";
    }
  ' "$matrix")"
  if [ -n "$violations" ]; then
    say "  [verify] Pre-Close Verification Gate BLOCKED:"
    printf '%s\n' "$violations" | while IFS=$'\t' read -r kind detail; do
      if [ "$kind" = "fail" ]; then
        say "    - failing proof committed: $detail"
      else
        say "    - stage close with unverified story: $detail"
      fi
    done
    say "  [verify] Run the story's Verify command, record Result: pass in"
    say "           $matrix § Verification Register, or document why none exists."
    return 1
  fi
  say "  [verify] register clean"
  return 0
}

# --- Run gates --------------------------------------------------------------
say "harness verify gate ($mode):"
run_validate || fail=1
check_register || fail=1

if [ "$fail" -ne 0 ]; then
  say ""
  say "Commit/push blocked by harness verify gate. Fix the items above."
  say "Bypassing with --no-verify requires explicit human sign-off (AGENTS.md)."
  exit 1
fi
exit 0
