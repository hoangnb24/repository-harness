#!/usr/bin/env python3
"""Validate Harness anti-cheat guardrails.

The script is intentionally stack-neutral. It checks that the repository has
the physical surfaces needed for validation integrity and, after the baseline
commit, rejects protected policy/test/proof changes without review evidence.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/VALIDATION_INTEGRITY.md",
    "docs/GIT_WORKFLOW.md",
    "docs/HARNESS.md",
    "docs/FEATURE_INTAKE.md",
    "docs/TRACE_SPEC.md",
    "docs/templates/story.md",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/workflows/harness-validation.yml",
    "scripts/validation-integrity-check.py",
]

PROTECTED_PATTERNS = [
    "AGENTS.md",
    "docs/HARNESS.md",
    "docs/FEATURE_INTAKE.md",
    "docs/TEST_MATRIX.md",
    "docs/TRACE_SPEC.md",
    "docs/GIT_WORKFLOW.md",
    "docs/VALIDATION_INTEGRITY.md",
    "docs/templates/*",
    "docs/templates/high-risk-story/*",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/workflows/*",
    "scripts/validation-integrity-check.py",
]

TEST_OR_PROOF_PATTERNS = [
    "test/*",
    "tests/*",
    "**/test/*",
    "**/tests/*",
    "**/__tests__/*",
    "**/*.test.*",
    "**/*.spec.*",
    "**/fixtures/*",
    "**/__fixtures__/*",
    "**/snapshots/*",
    "**/__snapshots__/*",
    "docs/TEST_MATRIX.md",
    "docs/templates/story.md",
    "docs/templates/high-risk-story/validation.md",
    ".github/workflows/*",
]

DANGEROUS_TEST_RE = re.compile(
    r"\b(skip|only|xfail|xdescribe|xit)\b|"
    r"\bassert\s+True\b|"
    r"coverage.*(-|=|:)\s*[0-9]{1,2}\b",
    re.IGNORECASE,
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = proc.stdout.strip() or proc.stderr.strip()
    return proc.returncode, output


def has_head() -> bool:
    code, _ = run_git(["rev-parse", "--verify", "HEAD"])
    return code == 0


def has_remote() -> bool:
    code, output = run_git(["remote"])
    return code == 0 and bool(output.strip())


def changed_files(base: str | None) -> list[str]:
    if base:
        code, output = run_git(["diff", "--name-only", f"{base}...HEAD"])
        if code == 0:
            return sorted({line.strip() for line in output.splitlines() if line.strip()})
    if has_head():
        code, output = run_git(["diff", "--name-only", "HEAD"])
        if code == 0:
            return sorted({line.strip() for line in output.splitlines() if line.strip()})
    code, output = run_git(["status", "--porcelain"])
    if code != 0:
        return []
    files: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        name = line[3:].strip()
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        if name:
            files.add(name)
    return sorted(files)


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def grep_required(path: str, snippets: list[str], errors: list[str]) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in content:
            errors.append(f"{path} is missing required snippet: {snippet}")


def static_checks(bootstrap: bool) -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).exists():
            errors.append(f"missing required validation-integrity file: {path}")

    if errors:
        return errors

    grep_required(
        "docs/HARNESS.md",
        ["docs/VALIDATION_INTEGRITY.md", "Validation Integrity"],
        errors,
    )
    grep_required(
        "docs/GIT_WORKFLOW.md",
        ["Validation integrity", "python3 scripts/validation-integrity-check.py"],
        errors,
    )
    grep_required(
        "docs/FEATURE_INTAKE.md",
        ["Validation integrity", "docs/VALIDATION_INTEGRITY.md"],
        errors,
    )
    grep_required(
        "docs/TRACE_SPEC.md",
        ["Validation integrity", "changed tests"],
        errors,
    )
    grep_required(
        "docs/templates/story.md",
        ["## Validation Integrity", "Tests changed:"],
        errors,
    )
    grep_required(
        ".github/pull_request_template.md",
        ["Validation Integrity", "Tests changed"],
        errors,
    )
    grep_required(
        ".github/workflows/harness-validation.yml",
        ["validation-integrity-check.py"],
        errors,
    )

    codeowners = (ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")
    for protected in ["docs/HARNESS.md", "docs/VALIDATION_INTEGRITY.md", ".github/workflows/"]:
        if protected not in codeowners:
            errors.append(f".github/CODEOWNERS does not cover {protected}")
    if "@repo-owner" in codeowners and not bootstrap and has_remote():
        errors.append("replace @repo-owner in .github/CODEOWNERS before using a remote")

    return errors


def change_checks(files: list[str], bootstrap: bool) -> list[str]:
    if bootstrap:
        return []

    errors: list[str] = []
    protected_changed = [f for f in files if matches(f, PROTECTED_PATTERNS)]
    test_or_proof_changed = [f for f in files if matches(f, TEST_OR_PROOF_PATTERNS)]
    decision_changed = any(fnmatch.fnmatch(f, "docs/decisions/*.md") for f in files)
    story_changed = any(fnmatch.fnmatch(f, "docs/stories/*.md") or fnmatch.fnmatch(f, "docs/stories/*/*.md") or fnmatch.fnmatch(f, "docs/stories/*/*/*.md") for f in files)

    if protected_changed and not decision_changed:
        errors.append(
            "protected validation/policy files changed without a docs/decisions/*.md record: "
            + ", ".join(protected_changed)
        )

    if test_or_proof_changed and not story_changed:
        errors.append(
            "test/proof files changed without story evidence: "
            + ", ".join(test_or_proof_changed)
        )

    for path in test_or_proof_changed:
        full_path = ROOT / path
        if full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if DANGEROUS_TEST_RE.search(content) and not decision_changed:
                errors.append(
                    f"{path} contains possible test weakening and needs a decision record"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Base ref for PR diffs, such as origin/main")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Allow initial repository setup before the baseline commit.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Use bootstrap mode before the baseline commit and normal mode after.",
    )
    args = parser.parse_args()
    bootstrap_mode = args.bootstrap or (args.auto and not has_head())

    errors = static_checks(bootstrap_mode)
    if args.bootstrap and has_head():
        errors.append("--bootstrap is only allowed before the first baseline commit")
    if not has_head() and not bootstrap_mode:
        errors.append("repository has no baseline commit; run with --bootstrap only for initial setup")

    files = changed_files(args.base)
    errors.extend(change_checks(files, bootstrap_mode))

    if errors:
        print("Validation integrity check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation integrity check passed.")
    if files:
        print("Changed files inspected:")
        for path in files:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
