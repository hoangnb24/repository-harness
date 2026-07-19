#!/usr/bin/env python3
"""Verify fail-closed Phase 5 public trust provisioning in premerge."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/premerge.yml"
VARIABLE = "PHASE5_TRUSTED_OWNER_REGISTRY_BASE64"
EXPECTED_DIGEST = "f55a117eb20df727ee21cb922345d62bce3f3afc4458ba5a8b057dc430c9bb6d"
EXPECTED_PROVISION_SHA256 = (
    "3cc5c57bb2c3410db7eaf6184000596c28ef3eb056dac0c1415dd4902ca080ca"
)
GITHUB_CONTEXT = re.compile(
    r"(?<![A-Za-z0-9_])(?P<context>vars|secrets|steps)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


class WorkflowContractError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowContractError(message)


def section(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    require(start_index >= 0, f"workflow section is missing: {start}")
    end_index = source.find(end, start_index + len(start))
    require(end_index >= 0, f"workflow section terminator is missing: {end}")
    return source[start_index:end_index]


def github_expression_bodies(source: str) -> list[str]:
    bodies: list[str] = []
    cursor = 0
    while True:
        start = source.find("${{", cursor)
        if start < 0:
            return bodies
        index = start + len("${{")
        masked: list[str] = []
        in_string = False
        while index < len(source):
            if in_string:
                if source[index] == "'":
                    if index + 1 < len(source) and source[index + 1] == "'":
                        masked.extend((" ", " "))
                        index += 2
                        continue
                    in_string = False
                masked.append(" ")
                index += 1
                continue
            if source[index] == "'":
                in_string = True
                masked.append(" ")
                index += 1
                continue
            if source.startswith("}}", index):
                bodies.append("".join(masked))
                cursor = index + len("}}")
                break
            masked.append(source[index])
            index += 1
        else:
            raise WorkflowContractError("GitHub expression is not closed")


def verify_text(source: str) -> None:
    validate = section(source, "  validate:\n", "\n  windows-installer:\n")
    provision_marker = "      - name: Provision pinned Phase 5 public trust registry\n"
    checkout_marker = "      - name: Checkout\n"
    premerge_marker = "      - name: Run pre-merge contract\n"
    upgrade_marker = "      - name: Prove Linux initial-to-candidate upgrade\n"
    provision_index = validate.find(provision_marker)
    checkout_index = validate.find(checkout_marker)
    premerge_index = validate.find(premerge_marker)
    require(
        0 <= provision_index < checkout_index < premerge_index,
        "Phase 5 trust must provision before checkout and premerge execution",
    )
    steps_index = validate.find("    steps:\n")
    require(
        steps_index >= 0
        and not validate[steps_index + len("    steps:\n") : provision_index].strip(),
        "Phase 5 trust provisioning is not the first validation step",
    )

    provision = section(validate, provision_marker, checkout_marker)
    require(
        hashlib.sha256(provision.encode("utf-8")).hexdigest()
        == EXPECTED_PROVISION_SHA256,
        "Phase 5 trust provisioning statements changed",
    )
    require(
        provision.count(f"${{{{ vars.{VARIABLE} }}}}") == 1,
        "Phase 5 public registry variable is absent or ambiguous",
    )
    for required in (
        "        id: phase5-trust\n",
        f"          {VARIABLE}: ${{{{ vars.{VARIABLE} }}}}\n",
        f'          [[ -n "${{{VARIABLE}:-}}" ]] || {{\n',
        '          registry="$(mktemp "$RUNNER_TEMP/phase5-trusted-owner-registry.XXXXXX.json")"\n',
        '            "$RUNNER_TEMP"/*) ;;\n',
        '            "$GITHUB_WORKSPACE"|"$GITHUB_WORKSPACE"/*)\n',
        f'          printf \'%s\' "${VARIABLE}" | base64 --decode > "$registry" || {{\n',
        f'          expected_digest="{EXPECTED_DIGEST}"\n',
        '          actual_digest="$(sha256sum "$registry" | awk \'{print $1}\')"\n',
        '          [[ "$actual_digest" == "$expected_digest" ]] || {\n',
        '          echo "registry=$registry" >> "$GITHUB_OUTPUT"\n',
    ):
        require(required in provision, f"Phase 5 trust provisioning omits: {required.strip()}")
    for prohibited in (
        "git show",
        "git cat-file",
        "tests/",
        "docs/",
        "scripts/",
        "curl ",
        "wget ",
        "cp ",
    ):
        require(
            prohibited not in provision,
            f"Phase 5 trust provisioning reads candidate or network input: {prohibited}",
        )

    premerge = section(validate, premerge_marker, upgrade_marker)
    require(
        premerge
        == (
            premerge_marker
            + "        env:\n"
            + "          HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY: "
            + "${{ steps.phase5-trust.outputs.registry }}\n"
            + "          HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY_SHA256: "
            + EXPECTED_DIGEST
            + "\n"
            + "        run: scripts/validate-premerge.sh\n\n"
        ),
        "premerge does not forward the exact paired verified trust inputs",
    )
    require(
        source.count(provision) == 1 and source.count(premerge) == 1,
        "allowed Phase 5 trust workflow blocks are duplicated",
    )
    outside_allowed_sites = source.replace(provision, "", 1).replace(premerge, "", 1)
    for expression in github_expression_bodies(outside_allowed_sites):
        access = GITHUB_CONTEXT.search(expression)
        require(
            access is None,
            "GitHub expression accesses forbidden workflow context outside exact "
            f"Phase 5 sites: {access.group('context') if access else 'unknown'}",
        )
    folded_outside = outside_allowed_sites.casefold()
    for sensitive_marker in (
        VARIABLE,
        "HARNESS_PHASE5_TRUSTED_OWNER_REGISTRY",
        "phase5-trust",
        EXPECTED_DIGEST,
    ):
        require(
            sensitive_marker.casefold() not in folded_outside,
            f"Phase 5 trust material escapes its exact workflow sites: {sensitive_marker}",
        )
    require(
        source.count(EXPECTED_DIGEST) == 2,
        "pinned Phase 5 public registry digest is missing or ambiguous",
    )
    require(
        source.count(f"vars.{VARIABLE}") == 1,
        "candidate execution can re-read or substitute the registry variable",
    )


def main() -> int:
    try:
        verify_text(WORKFLOW.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, WorkflowContractError) as error:
        print(f"Phase 5 premerge trust workflow verification failed: {error}", file=sys.stderr)
        return 1
    print("Phase 5 premerge trust is external, digest-pinned, paired, and fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
