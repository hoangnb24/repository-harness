#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-harness.sh [options] [path]

Apply the Harness v0 files and folders to a target project directory.

Options:
  -d, --directory <path>  Target directory. Defaults to the current directory.
  -y, --yes              Accept defaults and skip prompts.
      --bootstrap        Greenfield bootstrap: git init (if needed) + force-copy
                         all harness files (no merge prompts). Combine with
                         --spec <path> to place an initial spec into
                         docs/discovery/.
      --spec <path>      With --bootstrap, copy the given file into
                         docs/discovery/YYYY-MM-DD-initial-spec.<ext>.
      --merge            On protected-path conflict, keep existing files and
                         install only missing Harness files.
      --override         On protected-path conflict, back up and replace
                         AGENTS.md, docs/, and scripts/.
      --force            Overwrite existing files after backing them up.
      --dry-run          Show what would change without writing files.
  -h, --help             Show this help.

Safety:
  If AGENTS.md, docs/, or scripts/ already exist, interactive installs ask
  whether to merge missing files, override after backup, or stop. Non-
  interactive installs stop unless --merge or --override is provided.
  --bootstrap implies --override (with backups) and accepts the protected
  path warning automatically.

Examples:
  scripts/install-harness.sh
  scripts/install-harness.sh --directory /path/to/project --yes
  scripts/install-harness.sh ./my-project --force
  scripts/install-harness.sh --bootstrap --spec /path/to/spec.md ./my-new-project
  curl -fsSL https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh | bash -s -- --yes
  curl -fsSL https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh | bash -s -- --merge --yes
  curl -fsSL https://raw.githubusercontent.com/huunghiaish/harness-experimental/main/scripts/install-harness.sh | bash -s -- --bootstrap --yes
EOF
}

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

warn_stop() {
  printf 'Warning: %s\n' "$*" >&2
  exit 1
}

can_prompt() {
  [ -r /dev/tty ] && [ -w /dev/tty ]
}

prompt_tty() {
  printf '%s' "$1" > /dev/tty
}

read_tty() {
  local value
  IFS= read -r value < /dev/tty
  printf '%s\n' "$value"
}

expand_path() {
  case "$1" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s/%s\n' "$HOME" "${1#~/}"
      ;;
    /*)
      printf '%s\n' "$1"
      ;;
    *)
      printf '%s/%s\n' "$PWD" "$1"
      ;;
  esac
}

make_absolute_parent() {
  local path="$1"
  local parent
  parent="$(dirname "$path")"
  [ -d "$parent" ] || fail "Parent directory does not exist: $parent"
  (cd "$parent" && printf '%s/%s\n' "$(pwd -P)" "$(basename "$path")")
}

copy_file() {
  local relative="$1"
  local target="$TARGET_DIR/$relative"

  if [ -e "$target" ]; then
    if [ "$SOURCE_MODE" = "local" ] && [ "$SOURCE_ROOT/$relative" -ef "$target" ]; then
      log "skip     $relative (source file)"
      SKIPPED=$((SKIPPED + 1))
      return
    fi

    if [ "$CONFLICT_ACTION" = "merge" ]; then
      log "skip     $relative (merge keeps existing file)"
      SKIPPED=$((SKIPPED + 1))
    elif [ "$FORCE" -eq 1 ]; then
      if [ "$DRY_RUN" -eq 1 ]; then
        log "overwrite $relative (backup first)"
      else
        local backup="$BACKUP_DIR/$relative"
        mkdir -p "$(dirname "$backup")"
        cp -p "$target" "$backup"
        write_source_file "$relative" "$target"
        log "updated $relative (backup: ${backup#$TARGET_DIR/})"
      fi
      UPDATED=$((UPDATED + 1))
    else
      log "skip     $relative (already exists)"
      SKIPPED=$((SKIPPED + 1))
    fi
    return
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    log "create   $relative"
  else
    mkdir -p "$(dirname "$target")"
    write_source_file "$relative" "$target"
    log "created  $relative"
  fi
  CREATED=$((CREATED + 1))
}

write_source_file() {
  local relative="$1"
  local target="$2"

  if [ "$SOURCE_MODE" = "local" ]; then
    local source="$SOURCE_ROOT/$relative"
    [ -f "$source" ] || fail "Source file missing: $source"
    cp -p "$source" "$target"
    return
  fi

  local url="$SOURCE_BASE_URL/$relative"
  curl -fsSL "$url" -o "$target" || fail "Could not download $url"
}

check_protected_target_paths() {
  local conflicts=()

  [ -e "$TARGET_DIR/AGENTS.md" ] && conflicts+=("AGENTS.md")
  [ -e "$TARGET_DIR/docs" ] && conflicts+=("docs/")
  [ -e "$TARGET_DIR/scripts" ] && conflicts+=("scripts/")

  [ "${#conflicts[@]}" -gt 0 ] || return 0

  local joined=""
  local item
  for item in "${conflicts[@]}"; do
    if [ -n "$joined" ]; then
      joined="$joined, $item"
    else
      joined="$item"
    fi
  done

  case "$REQUESTED_CONFLICT_ACTION" in
    merge)
      CONFLICT_ACTION="merge"
      log "Continuing with merge. Existing files will be skipped."
      return 0
      ;;
    override)
      CONFLICT_ACTION="override"
      override_protected_target_paths
      return 0
      ;;
    stop)
      warn_stop "target already contains protected Harness paths: $joined. Refusing to install so existing project instructions or docs are not mixed or overwritten."
      ;;
  esac

  if [ "$YES" -eq 1 ] || ! can_prompt; then
    warn_stop "target already contains protected Harness paths: $joined. Refusing to install so existing project instructions or docs are not mixed or overwritten. Use an empty target directory, or move those paths before running the installer."
  fi

  {
    printf 'Warning: target already contains protected Harness paths: %s\n' "$joined"
    printf 'Choose how to continue:\n'
    printf '  1. Merge    Copy missing Harness files and skip existing files\n'
    printf '  2. Override Back up and replace AGENTS.md, docs/, and scripts/\n'
    printf '  3. Stop     Exit without writing files (recommended)\n'
  } > /dev/tty
  prompt_tty 'Choice [1/2/3, default 3]: '

  local choice
  choice="$(read_tty)"
  case "$choice" in
    1|m|M|merge|Merge)
      CONFLICT_ACTION="merge"
      log "Continuing with merge. Existing files will be skipped."
      ;;
    2|o|O|override|Override)
      CONFLICT_ACTION="override"
      override_protected_target_paths
      ;;
    ""|3|s|S|stop|Stop)
      warn_stop "installation stopped by user."
      ;;
    *)
      warn_stop "unknown choice: $choice"
      ;;
  esac
}

override_protected_target_paths() {
  local protected

  for protected in AGENTS.md docs scripts; do
    [ -e "$TARGET_DIR/$protected" ] || continue

    if [ "$DRY_RUN" -eq 1 ]; then
      log "override $protected (backup first)"
      continue
    fi

    mkdir -p "$BACKUP_DIR"
    mv "$TARGET_DIR/$protected" "$BACKUP_DIR/$protected"
    log "removed  $protected (backup: ${BACKUP_DIR#$TARGET_DIR/}/$protected)"
  done
}

TARGET_INPUT="${HARNESS_TARGET_DIR:-$PWD}"
YES=0
FORCE=0
DRY_RUN=0
BOOTSTRAP=0
SPEC_PATH=""
REQUESTED_CONFLICT_ACTION=""
POSITIONAL_TARGET=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    -d|--directory)
      [ "$#" -ge 2 ] || fail "$1 requires a path"
      TARGET_INPUT="$2"
      shift 2
      ;;
    -y|--yes)
      YES=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --bootstrap)
      BOOTSTRAP=1
      shift
      ;;
    --spec)
      [ "$#" -ge 2 ] || fail "$1 requires a path"
      SPEC_PATH="$2"
      shift 2
      ;;
    --merge)
      REQUESTED_CONFLICT_ACTION="merge"
      shift
      ;;
    --override)
      REQUESTED_CONFLICT_ACTION="override"
      shift
      ;;
    --stop)
      REQUESTED_CONFLICT_ACTION="stop"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      fail "Unknown option: $1"
      ;;
    *)
      [ -z "$POSITIONAL_TARGET" ] || fail "Only one target path is supported"
      POSITIONAL_TARGET="$1"
      shift
      ;;
  esac
done

if [ "$BOOTSTRAP" -eq 1 ]; then
  YES=1
  REQUESTED_CONFLICT_ACTION="override"
  FORCE=1
fi

if [ -n "$SPEC_PATH" ] && [ "$BOOTSTRAP" -eq 0 ]; then
  fail "--spec requires --bootstrap"
fi

if [ -n "$SPEC_PATH" ]; then
  [ -f "$SPEC_PATH" ] || fail "Spec file not found: $SPEC_PATH"
fi

if [ "$#" -gt 0 ]; then
  [ -z "$POSITIONAL_TARGET" ] || fail "Only one target path is supported"
  POSITIONAL_TARGET="$1"
  shift
fi

[ "$#" -eq 0 ] || fail "Unexpected extra arguments"

if [ -n "$POSITIONAL_TARGET" ]; then
  TARGET_INPUT="$POSITIONAL_TARGET"
fi

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd -P || printf '')"
SOURCE_ROOT=""
SOURCE_MODE="remote"
SOURCE_BASE_URL="${HARNESS_SOURCE_BASE_URL:-https://raw.githubusercontent.com/huunghiaish/harness-experimental/main}"
SOURCE_BASE_URL="${SOURCE_BASE_URL%/}"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../AGENTS.md" ] && [ -f "$SCRIPT_DIR/../docs/HARNESS.md" ]; then
  SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
  SOURCE_MODE="local"
fi

if [ "$YES" -eq 0 ] && can_prompt; then
  prompt_tty "Install Harness v0 into [$TARGET_INPUT]: "
  REPLY_TARGET="$(read_tty)"
  if [ -n "$REPLY_TARGET" ]; then
    TARGET_INPUT="$REPLY_TARGET"
  fi
fi

TARGET_DIR="$(make_absolute_parent "$(expand_path "$TARGET_INPUT")")"
BACKUP_DIR="$TARGET_DIR/.harness-backup/$(date +%Y%m%d%H%M%S)"
CREATED=0
UPDATED=0
SKIPPED=0
CONFLICT_ACTION="install"

if [ "$DRY_RUN" -eq 1 ]; then
  log "Dry run: no files will be written."
elif [ ! -d "$TARGET_DIR" ]; then
  mkdir -p "$TARGET_DIR"
fi

if [ ! -d "$TARGET_DIR" ]; then
  [ "$DRY_RUN" -eq 1 ] || fail "Target directory could not be created: $TARGET_DIR"
  log "Target directory would be created: $TARGET_DIR"
fi

if [ -d "$TARGET_DIR" ]; then
  [ -w "$TARGET_DIR" ] || fail "Target directory is not writable: $TARGET_DIR"
else
  [ -w "$(dirname "$TARGET_DIR")" ] || fail "Target parent directory is not writable: $(dirname "$TARGET_DIR")"
fi

if [ -d "$TARGET_DIR" ]; then
  check_protected_target_paths
fi

if [ "$SOURCE_MODE" = "local" ]; then
  log "Harness source: $SOURCE_ROOT"
else
  command -v curl >/dev/null 2>&1 || fail "curl is required for remote installation"
  log "Harness source: $SOURCE_BASE_URL"
fi
log "Target project: $TARGET_DIR"

while IFS= read -r relative; do
  copy_file "$relative"
done <<'EOF'
AGENTS.md
README.md
docs/ARCHITECTURE.md
docs/FEATURE_INTAKE.md
docs/GLOSSARY.md
docs/HARNESS.md
docs/HARNESS_BACKLOG.md
docs/README.md
docs/TEST_MATRIX.md
docs/WORKFLOW.md
docs/decisions/0001-harness-first-development.md
docs/decisions/0002-post-spec-product-lifecycle.md
docs/decisions/0003-generic-spec-intake-harness.md
docs/decisions/0004-adopt-claudekit-custom-patterns.md
docs/decisions/0005-roadmap-execution-direction.md
docs/decisions/0006-session-retrospective-mechanic.md
docs/decisions/0007-solo-dev-client-delivery-templates.md
docs/decisions/0008-visual-behavioral-modeling-stage.md
docs/decisions/0009-discovery-input-folder-convention.md
docs/decisions/0010-gap-analysis-stage.md
docs/decisions/0011-bootstrap-installer-mode.md
docs/decisions/README.md
docs/discovery/README.md
docs/intake/README.md
docs/playbooks/README.md
docs/playbooks/template.md
docs/playbooks/PATCH-EXTENSION-PROTOCOL.md
docs/playbooks/ai-feature-integration.md
docs/playbooks/bilingual-delivery-template-pattern.md
docs/playbooks/build-execution.md
docs/playbooks/canonical-e2e-flow-playbook.md
docs/playbooks/code-review-scoring.md
docs/playbooks/payment-integration.md
docs/playbooks/discovery-interview-playbook.md
docs/playbooks/gap-analysis.md
docs/playbooks/e2e-qa-field-by-field-verify-with-report.md
docs/playbooks/e2e-recording-user-guide-quality.md
docs/playbooks/headless-browser-blank-screenshot.md
docs/playbooks/landing-page-saas-ai-noti-style.md
docs/playbooks/playbook-composition-pattern.md
docs/playbooks/project-status-snapshot.md
docs/playbooks/scenario-taxonomy-playbook.md
docs/playbooks/seed-data-pattern.md
docs/playbooks/session-retrospective.md
docs/playbooks/solo-dev-client-delivery.md
docs/playbooks/ui-design-system-contract.md
docs/playbooks/visual-and-behavioral-modeling.md
docs/product/README.md
docs/stories/README.md
docs/stories/backlog.md
docs/stories/epics/README.md
docs/stories/US-001-install-harness.md
docs/templates/README.md
docs/templates/code-standards.md
docs/templates/decision.md
docs/templates/decisions/stack-selection.md
docs/templates/deployment-guide.md
docs/templates/spec-intake.md
docs/templates/story.md
docs/templates/validation-report.md
docs/templates/change-request-log.md
docs/templates/client-intake-brief.md
docs/templates/gap-analysis.md
docs/templates/maintenance-proposal.md
docs/templates/proposal-sow.md
docs/templates/release-note.md
docs/templates/role-permission-matrix.md
docs/templates/status-flow.md
docs/templates/high-risk-story/design.md
docs/templates/high-risk-story/execplan.md
docs/templates/high-risk-story/overview.md
docs/templates/high-risk-story/validation.md
docs/templates/delivery-closure-story/overview.md
docs/templates/delivery-closure-story/01-uat-plan.md
docs/templates/delivery-closure-story/02-signoff.md
docs/templates/delivery-closure-story/03-client-update.md
docs/templates/project-closure-story/overview.md
docs/templates/project-closure-story/01-handover-docs.md
docs/templates/project-closure-story/02-credentials-handover.md
docs/templates/project-closure-story/03-knowledge-transfer.md
docs/templates/locale-vi/client-intake-brief.md
docs/templates/locale-vi/gap-analysis.md
docs/templates/locale-vi/proposal-sow.md
docs/templates/locale-vi/change-request-log.md
docs/templates/locale-vi/release-note.md
docs/templates/locale-vi/maintenance-proposal.md
docs/templates/locale-vi/role-permission-matrix.md
docs/templates/locale-vi/status-flow.md
docs/templates/locale-vi/delivery-closure-story/01-uat-plan.md
docs/templates/locale-vi/delivery-closure-story/02-signoff.md
docs/templates/locale-vi/delivery-closure-story/03-client-update.md
docs/templates/locale-vi/project-closure-story/01-handover-docs.md
scripts/README.md
EOF

log ""
log "Done. Created: $CREATED, updated: $UPDATED, skipped: $SKIPPED."

if [ "$SKIPPED" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
  log "Existing files were left untouched. Re-run with --force to overwrite with backups."
fi

if [ "$FORCE" -eq 1 ] && [ "$UPDATED" -gt 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  log "Backups were written to: $BACKUP_DIR"
fi

if [ "$BOOTSTRAP" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  log ""
  log "Bootstrap mode active."

  if [ ! -d "$TARGET_DIR/.git" ]; then
    if command -v git >/dev/null 2>&1; then
      (cd "$TARGET_DIR" && git init -q)
      log "  git init: initialised empty repo at $TARGET_DIR/.git"
    else
      log "  git not found — skipping git init (run it manually)"
    fi
  else
    log "  git init: skipped (.git already exists)"
  fi

  if [ -n "$SPEC_PATH" ]; then
    spec_dir="$TARGET_DIR/docs/discovery"
    mkdir -p "$spec_dir"
    spec_basename="$(basename "$SPEC_PATH")"
    spec_ext="${spec_basename##*.}"
    case "$spec_ext" in
      "$spec_basename") spec_ext="md" ;;
    esac
    spec_target="$spec_dir/$(date +%Y-%m-%d)-initial-spec.$spec_ext"
    if [ -e "$spec_target" ]; then
      log "  spec copy: SKIPPED — target already exists: ${spec_target#$TARGET_DIR/}"
    else
      cp -p "$SPEC_PATH" "$spec_target"
      log "  spec copy: ${SPEC_PATH} → ${spec_target#$TARGET_DIR/}"
    fi
  fi

  today="$(date +%Y-%m-%d)"
  cat <<NEXT

Next step — paste this prompt into Claude Code (or any AGENTS.md-aware agent):

  Read all files under docs/discovery/. Run Phase 1 Spec Intake per
  docs/FEATURE_INTAKE.md § Spec Approval Gate. Create
  docs/intake/${today}-spec-intake.md. Stop after intake for
  human review.

After human approval, Phase 2 will derive docs/product/*, the
stack-selection decision (use docs/templates/decisions/stack-selection.md),
and the first story packets. See docs/QUICKSTART.md for the first 3 hours.
NEXT
fi
