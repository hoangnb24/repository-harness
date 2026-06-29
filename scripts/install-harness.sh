#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-harness.sh [options] [path]

Apply the Harness v0 files and folders to a target project directory.

Options:
  -d, --directory <path>  Target directory. Defaults to the current directory.
  -y, --yes              Accept defaults and skip prompts.
      --merge            On protected-path conflict, keep existing files in
                         place and install only missing Harness files.
      --refresh-agent-shim
                         Refresh an existing AGENTS.md into the small Harness
                         shim after backing it up. Old Harness-generated files
                         are replaced; custom files receive a marked block.
      --claude           Also install or refresh CLAUDE.md so Claude Code
                         auto-loads the harness context. Claude Code never
                         auto-loads AGENTS.md; the shim @-imports AGENTS.md
                         and docs/FEATURE_INTAKE.md inside a marked block.
                         Existing CLAUDE.md files get the block appended
                         after a backup; a stale block is refreshed in place.
      --override         On protected-path conflict, back up and replace
                         AGENTS.md, docs/, and scripts/.
      --force            Overwrite existing files after backing them up.
      --dry-run          Show what would change without writing files.
  -h, --help             Show this help.

Safety:
  If AGENTS.md, docs/, or scripts/ already exist, interactive installs ask
  whether to merge missing files, override after backup, or stop. Merge is the
  safe update path for repositories that already have Harness: existing files
  stay in place and new Harness files are appended by path. Non-
  interactive installs stop unless --merge or --override is provided. If a
  target .gitignore already exists, Harness appends its local database rules
  unless --force is used.

Examples:
  scripts/install-harness.sh
  scripts/install-harness.sh --directory /path/to/project --yes
  scripts/install-harness.sh ./my-project --force
  curl -fsSL https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh | bash -s -- --yes
  curl -fsSL https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh | bash -s -- --merge --yes
  curl -fsSL https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh | bash -s -- --merge --refresh-agent-shim --yes
  curl -fsSL https://raw.githubusercontent.com/hoangnb24/repository-harness/main/scripts/install-harness.sh | bash -s -- --claude --yes
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

  if [ "$relative" = ".gitignore" ] && [ -e "$target" ] && [ "$FORCE" -eq 0 ]; then
    merge_gitignore "$target"
    return
  fi

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

merge_gitignore() {
  local target="$1"
  local marker="# Harness durable layer"
local rules="harness.db
harness.db-wal
harness.db-shm
scripts/bin/harness-cli
scripts/bin/harness-cli.exe"

if grep -Fxq "harness.db" "$target" &&
   grep -Fxq "harness.db-wal" "$target" &&
   grep -Fxq "harness.db-shm" "$target" &&
   grep -Fxq "scripts/bin/harness-cli" "$target" &&
   grep -Fxq "scripts/bin/harness-cli.exe" "$target"; then
    log "skip     .gitignore (harness rules already present)"
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    log "update   .gitignore (append harness rules)"
  else
    {
      [ -s "$target" ] && printf '\n'
      printf '%s\n%s\n' "$marker" "$rules"
    } >> "$target"
    log "updated  .gitignore (appended harness rules)"
  fi
  UPDATED=$((UPDATED + 1))
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

agent_shim_block() {
  cat <<'EOF'
<!-- HARNESS:BEGIN -->
## Harness

This repo uses Harness. Before work, read:

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTEXT_RULES.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/bin/harness-cli query matrix`

Use the Rust Harness CLI at `scripts/bin/harness-cli` as the main operational
tool. Before a step that could use an external tool, run
`scripts/bin/harness-cli query tools --capability <name> --status present` to
see what is equipped; an absent capability is a clean skip.
<!-- HARNESS:END -->
EOF
}

claude_shim_block() {
  cat <<'EOF'
<!-- HARNESS:BEGIN -->
## Harness

Claude Code loads this file into every session, but it does not auto-load
`AGENTS.md`. The bare `@` lines below import the always-required harness
context (the "Must in all lanes" set from `docs/CONTEXT_RULES.md`) at
context-load time. Never wrap them in backticks; that disables the import.

@AGENTS.md

@docs/FEATURE_INTAKE.md

Also run `scripts/bin/harness-cli query matrix` before starting work.

Lane-dependent context (`README.md`, `docs/HARNESS.md`, `docs/ARCHITECTURE.md`,
`docs/CONTEXT_RULES.md`, product docs, stories, decisions) is intentionally not
imported — read it per lane, as `docs/CONTEXT_RULES.md` prescribes.
<!-- HARNESS:END -->
EOF
}

is_old_harness_agent_file() {
  local target="$1"

  grep -Fxq "# Agent Operating Guide" "$target" &&
    grep -Fxq "This repository is in Harness v0. There is no product implementation yet." "$target" &&
    grep -Fxq "## Source Of Truth" "$target" &&
    grep -Fxq "## Task Loop" "$target" &&
    grep -Fxq "## Done Definition" "$target"
}

backup_agent_file() {
  local target="$TARGET_DIR/AGENTS.md"

  [ -e "$target" ] || return 0
  mkdir -p "$BACKUP_DIR"
  [ -e "$BACKUP_DIR/AGENTS.md" ] && return 0
  cp -p "$target" "$BACKUP_DIR/AGENTS.md"
}

extract_obvious_agent_custom_section() {
  local target="$1"
  local output="$2"

  awk '
    /^## (Project-specific|Project Specific|Local|Custom).*Instructions/ {
      capture = 1
      print
      next
    }
    /^## / && capture {
      capture = 0
    }
    capture {
      print
    }
  ' "$target" > "$output"
}

insert_agent_custom_section() {
  local target="$1"
  local custom="$2"
  local tmp

  [ -s "$custom" ] || return 0
  tmp="$(mktemp)"
  awk '
    $0 == "Add project-specific agent instructions here." {
      while ((getline line < custom_file) > 0) {
        print line
      }
      next
    }
    { print }
  ' custom_file="$custom" "$target" > "$tmp"
  mv "$tmp" "$target"
}

append_or_replace_agent_harness_block() {
  local target="$TARGET_DIR/AGENTS.md"
  local tmp

  tmp="$(mktemp)"
  if grep -Fq "<!-- HARNESS:BEGIN -->" "$target" &&
     grep -Fq "<!-- HARNESS:END -->" "$target"; then
    awk '
      /<!-- HARNESS:BEGIN -->/ {
        while ((getline line < block_file) > 0) {
          print line
        }
        in_block = 1
        next
      }
      /<!-- HARNESS:END -->/ && in_block {
        in_block = 0
        next
      }
      !in_block { print }
    ' block_file=<(agent_shim_block) "$target" > "$tmp"
  else
    {
      cat "$target"
      printf '\n'
      agent_shim_block
    } > "$tmp"
  fi
  mv "$tmp" "$target"
}

refresh_agent_shim() {
  [ "$REFRESH_AGENT_SHIM" -eq 1 ] || return 0

  local target="$TARGET_DIR/AGENTS.md"
  [ -e "$target" ] || return 0

  if [ "$SOURCE_MODE" = "local" ] && [ "$SOURCE_ROOT/AGENTS.md" -ef "$target" ]; then
    log "skip     AGENTS.md (source file)"
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    if is_old_harness_agent_file "$target"; then
      log "refresh  AGENTS.md (old Harness guide -> shim, backup first)"
    else
      log "refresh  AGENTS.md (append or replace marked Harness block, backup first)"
    fi
    UPDATED=$((UPDATED + 1))
    return 0
  fi

  backup_agent_file
  if is_old_harness_agent_file "$target"; then
    local custom_tmp
    custom_tmp="$(mktemp)"
    extract_obvious_agent_custom_section "$target" "$custom_tmp"
    write_source_file "AGENTS.md" "$target"
    insert_agent_custom_section "$target" "$custom_tmp"
    rm -f "$custom_tmp"
    log "updated  AGENTS.md (old Harness guide -> shim; backup: ${BACKUP_DIR#$TARGET_DIR/}/AGENTS.md)"
  else
    append_or_replace_agent_harness_block
    log "updated  AGENTS.md (refreshed Harness block; backup: ${BACKUP_DIR#$TARGET_DIR/}/AGENTS.md)"
  fi
  UPDATED=$((UPDATED + 1))
}

backup_claude_file() {
  local target="$TARGET_DIR/CLAUDE.md"

  [ -e "$target" ] || return 0
  mkdir -p "$BACKUP_DIR"
  [ -e "$BACKUP_DIR/CLAUDE.md" ] && return 0
  cp -p "$target" "$BACKUP_DIR/CLAUDE.md"
}

write_claude_shim() {
  [ "$INSTALL_CLAUDE_SHIM" -eq 1 ] || return 0

  local target="$TARGET_DIR/CLAUDE.md"
  local block_tmp tmp

  if [ "$SOURCE_MODE" = "local" ] && [ -e "$target" ] &&
     [ "$SOURCE_ROOT/CLAUDE.md" -ef "$target" ]; then
    log "skip     CLAUDE.md (source file)"
    SKIPPED=$((SKIPPED + 1))
    return 0
  fi

  block_tmp="$(mktemp)"
  claude_shim_block > "$block_tmp"

  if [ -e "$target" ] &&
     grep -Fq "<!-- HARNESS:BEGIN -->" "$target" &&
     grep -Fq "<!-- HARNESS:END -->" "$target"; then
    local current_tmp
    current_tmp="$(mktemp)"
    awk '
      /<!-- HARNESS:BEGIN -->/ { in_block = 1 }
      in_block { print }
      /<!-- HARNESS:END -->/ { in_block = 0 }
    ' "$target" > "$current_tmp"
    if cmp -s "$current_tmp" "$block_tmp"; then
      log "skip     CLAUDE.md (Harness block current)"
      SKIPPED=$((SKIPPED + 1))
      rm -f "$current_tmp" "$block_tmp"
      return 0
    fi
    rm -f "$current_tmp"

    if [ "$DRY_RUN" -eq 1 ]; then
      log "update   CLAUDE.md (refresh marked Harness block, backup first)"
    else
      backup_claude_file
      tmp="$(mktemp)"
      awk '
        /<!-- HARNESS:BEGIN -->/ {
          while ((getline line < block_file) > 0) {
            print line
          }
          in_block = 1
          next
        }
        /<!-- HARNESS:END -->/ && in_block {
          in_block = 0
          next
        }
        !in_block { print }
      ' block_file="$block_tmp" "$target" > "$tmp"
      mv "$tmp" "$target"
      log "updated  CLAUDE.md (refreshed Harness block; backup: ${BACKUP_DIR#$TARGET_DIR/}/CLAUDE.md)"
    fi
    UPDATED=$((UPDATED + 1))
  elif [ -e "$target" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      log "update   CLAUDE.md (append Harness block, backup first)"
    else
      backup_claude_file
      {
        printf '\n'
        cat "$block_tmp"
      } >> "$target"
      log "updated  CLAUDE.md (appended Harness block; backup: ${BACKUP_DIR#$TARGET_DIR/}/CLAUDE.md)"
    fi
    UPDATED=$((UPDATED + 1))
  else
    if [ "$DRY_RUN" -eq 1 ]; then
      log "create   CLAUDE.md"
    else
      {
        printf '# Project Rules\n\n'
        cat "$block_tmp"
      } > "$target"
      log "created  CLAUDE.md"
    fi
    CREATED=$((CREATED + 1))
  fi
  rm -f "$block_tmp"
}

detect_cli_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os:$arch" in
    Darwin:arm64)  printf 'macos-arm64' ;;
    Darwin:x86_64) printf 'macos-x64' ;;
    Linux:x86_64)  printf 'linux-x64' ;;
    Linux:aarch64|Linux:arm64) printf 'linux-arm64' ;;
    *)
      fail "Unsupported Harness CLI platform: $os/$arch."
      ;;
  esac
}

sha256_file() {
  local file="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{ print $1 }'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{ print $1 }'
  else
    fail "shasum or sha256sum is required to verify the Harness CLI download"
  fi
}

download_file() {
  local url="$1"
  local target="$2"
  curl -fsSL "$url" -o "$target" || fail "Could not download $url"
}

read_cli_release_tag() {
  local tag_file="scripts/harness-cli-release-tag"
  local tag=""

  if [ "$SOURCE_MODE" = "local" ]; then
    if [ -f "$SOURCE_ROOT/$tag_file" ]; then
      tag="$(awk 'NF && $1 !~ /^#/ { print $1; exit }' "$SOURCE_ROOT/$tag_file")"
    fi
  else
    local tmp_file
    tmp_file="$(mktemp)"
    if curl -fsSL "$SOURCE_BASE_URL/$tag_file" -o "$tmp_file" 2>/dev/null; then
      tag="$(awk 'NF && $1 !~ /^#/ { print $1; exit }' "$tmp_file")"
    fi
    rm -f "$tmp_file"
  fi

  printf '%s\n' "$tag"
}

default_cli_base_url() {
  local release_tag="${HARNESS_CLI_RELEASE_TAG:-}"

  if [ -z "$release_tag" ]; then
    release_tag="$(read_cli_release_tag)"
  fi

  if [ -n "$release_tag" ] && [ "$release_tag" != "latest" ]; then
    printf 'https://github.com/hoangnb24/repository-harness/releases/download/%s\n' "$release_tag"
  else
    printf 'https://github.com/hoangnb24/repository-harness/releases/latest/download\n'
  fi
}

install_harness_cli_binary() {
  [ "$INSTALL_RUST_CLI" -eq 1 ] || return 0

  local platform binary_name binary_url checksum_url target tmp_dir binary_tmp checksum_tmp expected actual
  platform="${HARNESS_CLI_PLATFORM:-$(detect_cli_platform)}"
  binary_name="harness-cli-$platform"
  binary_url="$CLI_BASE_URL/$binary_name"
  checksum_url="$binary_url.sha256"
  target="$TARGET_DIR/scripts/bin/harness-cli"

  if [ -e "$target" ] && [ "$CONFLICT_ACTION" = "merge" ] && [ "$FORCE" -eq 0 ]; then
    log "skip     scripts/bin/harness-cli (merge keeps existing file)"
    SKIPPED=$((SKIPPED + 1))
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    log "download $binary_name -> scripts/bin/harness-cli"
    log "verify   $binary_name.sha256"
    CREATED=$((CREATED + 1))
    return 0
  fi

  command -v curl >/dev/null 2>&1 || fail "curl is required to download the Harness CLI"

  tmp_dir="$(mktemp -d)"
  binary_tmp="$tmp_dir/$binary_name"
  checksum_tmp="$tmp_dir/$binary_name.sha256"

  download_file "$binary_url" "$binary_tmp"
  download_file "$checksum_url" "$checksum_tmp"

  expected="$(awk '{ print $1; exit }' "$checksum_tmp")"
  [ -n "$expected" ] || fail "Checksum file is empty: $checksum_url"
  actual="$(sha256_file "$binary_tmp")"
  if [ "$actual" != "$expected" ]; then
    rm -rf "$tmp_dir"
    fail "Checksum mismatch for $binary_name: expected $expected, got $actual"
  fi

  mkdir -p "$(dirname "$target")"
  if [ -e "$target" ]; then
    if [ "$FORCE" -eq 1 ]; then
      mkdir -p "$BACKUP_DIR/scripts/bin"
      cp -p "$target" "$BACKUP_DIR/scripts/bin/harness-cli"
    fi
    UPDATED=$((UPDATED + 1))
    log "updated  scripts/bin/harness-cli"
  else
    CREATED=$((CREATED + 1))
    log "created  scripts/bin/harness-cli"
  fi

  cp "$binary_tmp" "$target"
  chmod 755 "$target"
  rm -rf "$tmp_dir"
  log "verified scripts/bin/harness-cli ($platform)"
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
INSTALL_RUST_CLI=1
REFRESH_AGENT_SHIM=0
INSTALL_CLAUDE_SHIM=0
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
    --merge)
      REQUESTED_CONFLICT_ACTION="merge"
      shift
      ;;
    --refresh-agent-shim)
      REFRESH_AGENT_SHIM=1
      shift
      ;;
    --claude)
      INSTALL_CLAUDE_SHIM=1
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
SOURCE_BASE_URL="${HARNESS_SOURCE_BASE_URL:-https://raw.githubusercontent.com/hoangnb24/repository-harness/main}"
SOURCE_BASE_URL="${SOURCE_BASE_URL%/}"
CLI_BASE_URL="${HARNESS_CLI_BASE_URL:-}"
CLI_BASE_URL="${CLI_BASE_URL%/}"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../AGENTS.md" ] && [ -f "$SCRIPT_DIR/../docs/HARNESS.md" ]; then
  SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
  SOURCE_MODE="local"
fi

if [ -z "$CLI_BASE_URL" ]; then
  CLI_BASE_URL="$(default_cli_base_url)"
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
if [ "$INSTALL_RUST_CLI" -eq 1 ]; then
  log "Harness CLI source: $CLI_BASE_URL"
else
  log "Harness CLI source: skipped"
fi
log "Target project: $TARGET_DIR"

while IFS= read -r relative; do
  copy_file "$relative"
done <<'EOF'
AGENTS.md
README.md
docs/ARCHITECTURE.md
docs/BRAINSTORM.md
docs/CONTEXT_RULES.md
docs/FEATURE_INTAKE.md
docs/GIT_WORKFLOW.md
docs/GLOSSARY.md
docs/HARNESS.md
docs/HARNESS_AUDIT.md
docs/HARNESS_BACKLOG.md
docs/HARNESS_COMPONENTS.md
docs/HARNESS_MATURITY.md
docs/IMPROVEMENT_PROTOCOL.md
docs/README.md
docs/TEST_MATRIX.md
docs/TOOL_REGISTRY.md
docs/TRACE_SPEC.md
docs/VALIDATION_INTEGRITY.md
docs/decisions/0001-harness-first-development.md
docs/decisions/0002-post-spec-product-lifecycle.md
docs/decisions/0003-generic-spec-intake-harness.md
docs/decisions/0004-sqlite-durable-layer.md
docs/decisions/0005-prebuilt-rust-harness-cli.md
docs/decisions/0006-phase-4-benchmark-triage.md
docs/decisions/0007-improvement-proposal-rules.md
docs/decisions/0008-validation-integrity-anti-cheat.md
docs/decisions/README.md
docs/product/README.md
docs/stories/README.md
docs/stories/US-001-add-brainstorm-workflow.md
docs/stories/US-002-add-git-branch-workflow.md
docs/stories/backlog.md
docs/stories/epics/E04-validation-integrity/US-003-anti-cheat-validation-integrity/design.md
docs/stories/epics/E04-validation-integrity/US-003-anti-cheat-validation-integrity/execplan.md
docs/stories/epics/E04-validation-integrity/US-003-anti-cheat-validation-integrity/overview.md
docs/stories/epics/E04-validation-integrity/US-003-anti-cheat-validation-integrity/validation.md
docs/templates/brainstorm.md
docs/templates/decision.md
docs/templates/spec-intake.md
docs/templates/story.md
docs/templates/validation-report.md
docs/templates/high-risk-story/design.md
docs/templates/high-risk-story/execplan.md
docs/templates/high-risk-story/overview.md
docs/templates/high-risk-story/validation.md
scripts/README.md
scripts/schema/001-init.sql
scripts/schema/002-story-verify.sql
scripts/schema/003-tool-registry.sql
scripts/schema/004-intervention.sql
scripts/schema/005-tool-extensions.sql
scripts/validation-integrity-check.py
.github/CODEOWNERS
.github/pull_request_template.md
.github/workflows/harness-validation.yml
.gitignore
EOF

refresh_agent_shim
write_claude_shim
install_harness_cli_binary

log ""
log "Done. Created: $CREATED, updated: $UPDATED, skipped: $SKIPPED."

if [ "$SKIPPED" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
  log "Existing files were left untouched. Re-run with --force to overwrite with backups."
fi

if [ "$FORCE" -eq 1 ] && [ "$UPDATED" -gt 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  log "Backups were written to: $BACKUP_DIR"
fi
