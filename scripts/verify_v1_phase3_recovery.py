#!/usr/bin/env python3
"""Mechanical proof for Repository Harness V1 Phase 3 mutation/recovery."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "crates" / "harness-core"
RECOVERY = CORE / "src" / "recovery.rs"
APPLICATION = CORE / "src" / "application.rs"
INTEGRATION = CORE / "tests" / "phase3_recovery.rs"
STORY = ROOT / "docs" / "stories" / "US-108-v1-install-update-recovery"
ALLOWED_LATER_CHANGESETS = {
    ".harness/changesets/harness_v1_phase4_bridge.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_00_intake.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_01_story.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_02_proof_contract.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_03_build_receipts.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_04_execution_proof.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_05_review_corrections.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_06_cross_binding_corrections.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_07_github_attestation.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_08_windows_compile_fix.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_11_premerge_bytecode_boundary.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_12_premerge_bytecode_causality.changeset.jsonl",
    ".harness/changesets/harness_v1_phase7_13_windows_progress_suppression.changeset.jsonl",
}


class VerificationError(RuntimeError):
    pass


PASS_COUNT = 0


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def proof(label: str, function: Callable[[], None]) -> None:
    global PASS_COUNT
    function()
    PASS_COUNT += 1
    print(f"ok {PASS_COUNT:02d} - {label}")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class RustFunctionItem:
    name: str
    start: int
    body_start: int
    body_end: int
    attributes: tuple[str, ...]


def mask_rust_non_code(source: str) -> str:
    """Preserve offsets while masking comments and Rust string/char literals."""
    masked = list(source)

    def blank(start: int, end: int) -> None:
        for offset in range(start, end):
            if masked[offset] != "\n":
                masked[offset] = " "

    offset = 0
    while offset < len(source):
        if source.startswith("//", offset):
            end = source.find("\n", offset + 2)
            end = len(source) if end == -1 else end
            blank(offset, end)
            offset = end
            continue
        if source.startswith("/*", offset):
            depth = 1
            end = offset + 2
            while end < len(source) and depth:
                if source.startswith("/*", end):
                    depth += 1
                    end += 2
                elif source.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            check(depth == 0, "unterminated Rust block comment")
            blank(offset, end)
            offset = end
            continue
        raw = re.match(r'(?:br|r)(?P<hashes>#{0,32})"', source[offset:])
        if raw and (offset == 0 or not (source[offset - 1].isalnum() or source[offset - 1] == "_")):
            delimiter = '"' + raw.group("hashes")
            end = source.find(delimiter, offset + raw.end())
            check(end != -1, "unterminated Rust raw string")
            end += len(delimiter)
            blank(offset, end)
            offset = end
            continue
        if source[offset] == '"':
            end = offset + 1
            while end < len(source):
                if source[end] == "\\":
                    end += 2
                elif source[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
            check(end <= len(source) and source[end - 1] == '"', "unterminated Rust string")
            blank(offset, end)
            offset = end
            continue
        if source[offset] == "'":
            end = offset + 1
            if end < len(source) and source[end] == "\\":
                end += 2
            else:
                end += 1
            if end < len(source) and source[end] == "'":
                end += 1
                blank(offset, end)
                offset = end
                continue
        offset += 1
    return "".join(masked)


def balanced_end(masked: str, opening: int, left: str, right: str) -> int:
    check(masked[opening] == left, f"Rust structural scan expected {left}")
    depth = 0
    for offset in range(opening, len(masked)):
        if masked[offset] == left:
            depth += 1
        elif masked[offset] == right:
            depth -= 1
            if depth == 0:
                return offset + 1
    raise VerificationError(f"unclosed Rust {left}{right} block")


def balanced_start(masked: str, closing: int, left: str, right: str) -> int:
    check(masked[closing] == right, f"Rust structural scan expected {right}")
    depth = 0
    for offset in range(closing, -1, -1):
        if masked[offset] == right:
            depth += 1
        elif masked[offset] == left:
            depth -= 1
            if depth == 0:
                return offset
    raise VerificationError(f"unopened Rust {left}{right} block")


def rust_function_item_start(masked: str, fn_start: int) -> int:
    """Return the start of a Rust function item, including its qualifiers."""
    item_start = fn_start
    cursor = fn_start
    qualifiers = {"async", "const", "default", "extern", "safe", "unsafe"}
    while cursor > 0:
        while cursor > 0 and masked[cursor - 1].isspace():
            cursor -= 1
        if cursor == 0:
            return item_start

        if masked[cursor - 1] == ")":
            visibility_open = balanced_start(masked, cursor - 1, "(", ")")
            word_end = visibility_open
            while word_end > 0 and masked[word_end - 1].isspace():
                word_end -= 1
            word_start = word_end
            while word_start > 0 and (
                masked[word_start - 1].isalnum()
                or masked[word_start - 1] == "_"
            ):
                word_start -= 1
            if masked[word_start:word_end] == "pub":
                item_start = word_start
                cursor = word_start
                continue
            return item_start

        word_end = cursor
        word_start = word_end
        while word_start > 0 and (
            masked[word_start - 1].isalnum() or masked[word_start - 1] == "_"
        ):
            word_start -= 1
        word = masked[word_start:word_end]
        if word == "pub" or word in qualifiers:
            item_start = word_start
            cursor = word_start
            continue
        return item_start
    return item_start


def outer_attributes(source: str, item_start: int) -> tuple[str, ...]:
    masked = mask_rust_non_code(source)
    cursor = item_start
    attributes: list[str] = []
    while cursor > 0:
        while cursor > 0 and masked[cursor - 1].isspace():
            cursor -= 1
        if cursor == 0 or masked[cursor - 1] != "]":
            break
        attribute_end = cursor
        attribute_open = balanced_start(masked, cursor - 1, "[", "]")
        hash_offset = attribute_open
        while hash_offset > 0 and masked[hash_offset - 1].isspace():
            hash_offset -= 1
        if hash_offset == 0 or masked[hash_offset - 1] != "#":
            break
        attribute_start = hash_offset - 1
        attributes.insert(0, source[attribute_start:attribute_end].strip())
        cursor = attribute_start
    return tuple(attributes)


def find_rust_function(
    source: str,
    name: str,
    range_start: int = 0,
    range_end: int | None = None,
) -> RustFunctionItem:
    masked = mask_rust_non_code(source)
    limit = len(source) if range_end is None else range_end
    matches: list[RustFunctionItem] = []
    pattern = re.compile(rf"\bfn\s+{re.escape(name)}\s*\(")
    for match in pattern.finditer(masked, range_start, limit):
        item_start = rust_function_item_start(masked, match.start())
        body_start = masked.find("{", match.end(), limit)
        semicolon = masked.find(";", match.end(), limit)
        if body_start == -1 or (semicolon != -1 and semicolon < body_start):
            continue
        body_end = balanced_end(masked, body_start, "{", "}")
        check(body_end <= limit, f"Rust function {name} escapes its owning scope")
        matches.append(
            RustFunctionItem(
                name=name,
                start=item_start,
                body_start=body_start,
                body_end=body_end,
                attributes=outer_attributes(source, item_start),
            )
        )
    check(len(matches) == 1, f"expected one structural Rust function named {name}")
    return matches[0]


def mutation_impl_range(source: str) -> tuple[int, int]:
    masked = mask_rust_non_code(source)
    match = re.search(r"\bimpl\s+MutationPort\s+for\s+OsMutationPort\s*\{", masked)
    check(match is not None, "OsMutationPort MutationPort implementation is missing")
    opening = masked.find("{", match.start(), match.end())
    return opening + 1, balanced_end(masked, opening, "{", "}") - 1


def cfg_blocks(source: str, item: RustFunctionItem) -> list[tuple[str, int, int, int]]:
    masked = mask_rust_non_code(source)
    blocks: list[tuple[str, int, int, int]] = []
    pattern = re.compile(r"#\s*\[\s*(?:r#)?cfg\s*\(")
    for match in pattern.finditer(masked, item.body_start + 1, item.body_end - 1):
        attribute_open = masked.find("[", match.start(), match.end())
        attribute_end = balanced_end(masked, attribute_open, "[", "]")
        block_start = attribute_end
        while block_start < item.body_end and masked[block_start].isspace():
            block_start += 1
        check(
            block_start < item.body_end and masked[block_start] == "{",
            f"cfg attribute in {item.name} is not attached directly to a block",
        )
        block_end = balanced_end(masked, block_start, "{", "}")
        blocks.append(
            (
                source[match.start():attribute_end],
                match.start(),
                block_start,
                block_end,
            )
        )
    return blocks


def top_level_rust_expressions(source: str) -> tuple[list[str], str]:
    masked = mask_rust_non_code(source)
    depths = {"(": 0, "[": 0, "{": 0}
    pairs = {")": "(", "]": "[", "}": "{"}
    statements: list[str] = []
    start = 0
    for offset, character in enumerate(masked):
        if character in depths:
            depths[character] += 1
        elif character in pairs:
            depths[pairs[character]] -= 1
            check(depths[pairs[character]] >= 0, "unbalanced Rust expression")
        elif character == ";" and not any(depths.values()):
            statements.append(source[start:offset].strip())
            start = offset + 1
    check(not any(depths.values()), "unbalanced Rust expression")
    return statements, source[start:].strip()


def compact_rust_code(source: str) -> str:
    return re.sub(r"\s+", "", mask_rust_non_code(source))


def proof_exact_plan_binding() -> None:
    source = text(RECOVERY)
    for fragment in [
        "operations_from_writes",
        "public_operation_digest",
        "request.operations != expected_operations",
        "public operations are not the exact projection of planned writes",
        "plan_operation_id",
        "expected_create_witness_path",
        'format!("witness-',
        "operation identifier does not commit the exact mutation plan",
        "accepted_preview_cannot_authorize_mismatched_planned_write_bytes",
        "unrelated_private_staged_path_is_rejected_before_zero_filesystem_mutation",
        "backup_manifest_and_kind_invariants_fail_before_zero_filesystem_mutation",
    ]:
        check(fragment in source, f"exact request/preview binding omits {fragment}")


def proof_authenticated_recovery_binding() -> None:
    source = text(RECOVERY)
    integration = text(INTEGRATION)
    for fragment in [
        "journal.operations != expected_operations",
        "recovery operation identifier does not authorize the exact post-images",
        "RecoveryScope",
        "authorization.assets",
        "asset.sha256",
        "asset.bytes",
        "verify_authenticated_post_images",
        "verify_probe_owned_evidence",
        "verify_owned_evidence_read_only",
        "validate_candidate_transition",
        "validate_payload_transition",
        "RootIdentity",
        "journal_matches_current_root",
        "recovery journal belongs to a different repository root",
        "link_owned_once",
        "step_requires_create_witness",
        "deterministic authenticated managed-block post-image",
        "recomputed_unkeyed_journal_digest_cannot_change_authorized_manifest_post_image",
        "nested_operation_unknown_field_is_rejected_even_with_recomputed_body_digest",
        "fabricated_applied_create_without_hard_link_witness_is_not_trusted_on_resume",
        "fabricated_update_journal_cannot_patch_authoritative_target_owned_role",
        "fabricated_fresh_journal_cannot_claim_preexisting_before_images",
        "fabricated_scaffold_journal_cannot_expand_beyond_bound_destination",
        "rollback_refuses_scaffold_target_delete_without_hard_link_witness",
        "rollback_refuses_fresh_manifest_delete_without_hard_link_witness",
        "fabricated_recovery_downgrade_is_rejected_before_zero_mutation",
        "copied_interrupted_update_journal_is_not_actionable_in_another_repository_root",
        "copied_committed_update_journal_cannot_drive_rollback_in_another_repository_root",
    ]:
        check(
            fragment in source or fragment in integration,
            f"authenticated recovery binding omits {fragment}",
        )


def validate_portable_journal_validation_boundary(source: str) -> None:
    helper = find_rust_function(source, "operation_root_path")
    check(
        not has_conditional_outer_attribute(helper),
        "pure recovery operation-root formatter is cfg-gated",
    )
    ownership = find_rust_function(source, "validate_journal_ownership")
    check(
        not has_conditional_outer_attribute(ownership),
        "journal ownership validation is cfg-gated",
    )
    ownership_body = source[ownership.body_start + 1 : ownership.body_end - 1]
    check(
        "let operation_root = operation_root_path(operation_id);" in ownership_body,
        "journal ownership validation does not use the portable pure formatter",
    )
    check(
        "OsMutationPort::operation_root" not in mask_rust_non_code(source),
        "platform-neutral recovery validation calls a Unix-only mutation method",
    )

    impl_start, impl_end = mutation_impl_range(source)
    expected_inert_bindings = {
        "apply": "let_=(request,validate_candidate)",
        "recover": "let_=(command,operation_id,mode,authorization,validate_candidate,)",
    }
    for method_name in ("apply", "recover"):
        method = find_rust_function(source, method_name, impl_start, impl_end)
        check(
            not has_conditional_outer_attribute(method),
            f"required {method_name} method is cfg-gated",
        )
        blocks = cfg_blocks(source, method)
        check(
            len(blocks) == 2,
            f"{method_name} must contain only Unix and non-Unix dispatch blocks",
        )
        unix = [
            block
            for block in blocks
            if compact_rust_code(block[0]) == "#[cfg(unix)]"
        ]
        non_unix = [
            block
            for block in blocks
            if compact_rust_code(block[0]) == "#[cfg(not(unix))]"
        ]
        check(len(unix) == 1, f"{method_name} must contain one exact cfg(unix) block")
        check(
            len(non_unix) == 1,
            f"{method_name} must contain one exact cfg(not(unix)) block",
        )
        cursor = method.body_start + 1
        for _, attribute_start, _, dispatch_end in sorted(
            blocks,
            key=lambda block: block[1],
        ):
            check(
                attribute_start >= cursor
                and not compact_rust_code(source[cursor:attribute_start]),
                f"{method_name} has executable work outside platform dispatch",
            )
            cursor = dispatch_end
        check(
            not compact_rust_code(source[cursor : method.body_end - 1]),
            f"{method_name} has executable work after platform dispatch",
        )
        _, _, block_start, block_end = non_unix[0]
        block_body = source[block_start + 1 : block_end - 1]
        statements, tail = top_level_rust_expressions(block_body)
        check(
            [compact_rust_code(statement) for statement in statements]
            == [expected_inert_bindings[method_name]],
            f"non-Unix {method_name} performs work before refusing",
        )
        compact_tail = compact_rust_code(tail)
        check(
            compact_tail
            == (
                "Err(MutationFailure::before_journal(PortError::Io{"
                "path:.into(),message:.into(),}))"
            ),
            f"non-Unix {method_name} does not unconditionally fail before journaling",
        )


def has_conditional_outer_attribute(item: RustFunctionItem) -> bool:
    return any(
        re.match(
            r"#\s*\[\s*(?:r#)?cfg(?:_attr)?\b",
            mask_rust_non_code(attribute),
        )
        for attribute in item.attributes
    )


def expect_portability_rejection(label: str, source: str) -> None:
    try:
        validate_portable_journal_validation_boundary(source)
    except VerificationError:
        print(f"ok - rejected {label}")
        return
    raise VerificationError(f"portable journal validation accepted adversary: {label}")


def proof_portable_journal_validation_boundary() -> None:
    validate_portable_journal_validation_boundary(text(RECOVERY))


def proof_portable_journal_validation_adversaries() -> None:
    source = text(RECOVERY)
    helper = "fn operation_root_path(operation_id: &str) -> String"
    check(helper in source, "portable recovery operation-root formatter is missing")
    expect_portability_rejection(
        "intervening helper attribute",
        source.replace(helper, f"#[cfg(unix)]\n#[inline]\n{helper}", 1),
    )
    for label, prefix in (
        (
            "separate-line block comment after helper cfg",
            "#[cfg(unix)]\n/* formatter must stay portable */\n",
        ),
        (
            "same-line block comment after helper cfg",
            "#[cfg(unix)] /* formatter must stay portable */ ",
        ),
        (
            "nested block and line comments between helper attributes",
            "#[cfg(unix)]\n"
            "/* outer comment /* nested comment */ still outer */\n"
            "#[inline]\n"
            "// adjacent line comment\n",
        ),
        (
            "same-line comments around an intervening helper attribute",
            "#[cfg(unix)] /* first */ #[inline] /* second */ ",
        ),
    ):
        expect_portability_rejection(
            label,
            source.replace(helper, f"{prefix}{helper}", 1),
        )
    for label, expression in (
        ("not-windows helper cfg", "not(windows)"),
        ("Unix-or-Linux helper cfg", 'any(unix, target_os = "linux")'),
        (
            "compound Windows-excluding helper cfg",
            'all(not(target_os = "windows"), any(unix, target_os = "linux"))',
        ),
    ):
        expect_portability_rejection(
            label,
            source.replace(helper, f"#[cfg({expression})]\n{helper}", 1),
        )
    expect_portability_rejection(
        "cfg-attr Windows exclusion",
        source.replace(
            helper,
            f"#[cfg_attr(windows, cfg(any()))]\n{helper}",
            1,
        ),
    )
    for label, attribute in (
        ("raw cfg helper", "#[r#cfg(unix)]"),
        (
            "raw cfg_attr helper",
            "#[r#cfg_attr(windows, cfg(any()))]",
        ),
        (
            "commented and spaced raw cfg helper",
            "#[ /* raw conditional */ r#cfg /* condition */ (unix) ]",
        ),
    ):
        expect_portability_rejection(
            label,
            source.replace(helper, f"{attribute}\n{helper}", 1),
        )
    for label, prefix in (
        ("pub(crate) helper visibility", "#[cfg(unix)]\npub(crate) "),
        (
            "inline pub(crate) helper visibility",
            "#[cfg(unix)]\n#[inline]\npub(crate) ",
        ),
        ("public helper visibility", "#[cfg(unix)]\npub "),
        ("async restricted helper", "#[cfg(unix)]\npub(crate) async "),
        (
            "qualified restricted helper",
            '#[cfg(unix)]\npub(super) unsafe extern "Rust" ',
        ),
        (
            "commented in-path const helper",
            "#[cfg_attr(windows, cfg(any()))]\n"
            "/* preserve item association */ pub(in crate) const ",
        ),
    ):
        expect_portability_rejection(
            label,
            source.replace(helper, f"{prefix}{helper}", 1),
        )

    impl_start, impl_end = mutation_impl_range(source)
    inert_arguments = {
        "apply": "(request, validate_candidate)",
        "recover": "(command, operation_id, mode, authorization, validate_candidate,)",
    }
    for method_name in ("apply", "recover"):
        method_declaration = f"    fn {method_name}("
        check(
            method_declaration in source,
            f"cannot seed outer-attribute adversary for {method_name}",
        )
        for label, prefix in (
            ("cfg", "    #[cfg(unix)]\n"),
            ("cfg_attr", "    #[cfg_attr(windows, cfg(any()))]\n"),
            ("raw cfg", "    #[r#cfg(unix)]\n"),
            (
                "raw cfg_attr",
                "    #[r#cfg_attr(windows, cfg(any()))]\n",
            ),
            (
                "commented and spaced raw cfg_attr",
                "    #[ /* raw conditional */ r#cfg_attr "
                "/* condition */ (windows, cfg(any())) ]\n",
            ),
            (
                "cfg with intervening attribute and comment",
                "    #[cfg(not(windows))]\n"
                "    /* required method must remain portable */\n"
                "    #[inline]\n",
            ),
        ):
            expect_portability_rejection(
                f"{label}-hidden {method_name} method",
                source.replace(
                    method_declaration,
                    f"{prefix}{method_declaration}",
                    1,
                ),
            )
        method = find_rust_function(source, method_name, impl_start, impl_end)
        non_unix = [
            block
            for block in cfg_blocks(source, method)
            if compact_rust_code(block[0]) == "#[cfg(not(unix))]"
        ]
        check(len(non_unix) == 1, f"cannot seed non-Unix {method_name} adversary")
        _, attribute_start, block_start, block_end = non_unix[0]
        for label, injected in (
            (
                "unconditional filesystem write before refusal",
                '        std::fs::write(".harness/phase7-gap", b"x").unwrap();\n',
            ),
            (
                "Windows cfg filesystem write before refusal",
                "        #[cfg(windows)]\n"
                "        {\n"
                '            let _ = std::fs::write(".harness/phase7-gap", b"x");\n'
                "        }\n",
            ),
            (
                "raw non-Unix cfg filesystem write before refusal",
                "        #[r#cfg(not(unix))]\n"
                "        {\n"
                '            let _ = std::fs::write(".harness/phase7-gap", b"x");\n'
                "        }\n",
            ),
            (
                "target-os Windows cfg statement before refusal",
                '        #[cfg(target_os = "windows")]\n'
                '        std::fs::write(".harness/phase7-gap", b"x").unwrap();\n',
            ),
            (
                "compound Windows cfg filesystem write before refusal",
                '        #[cfg(all(not(unix), target_os = "windows"))]\n'
                "        {\n"
                '            let _ = std::fs::write(".harness/phase7-gap", b"x");\n'
                "        }\n",
            ),
            (
                "raw cfg_attr filesystem write before refusal",
                "        #[r#cfg_attr(not(unix), cfg(not(unix)))]\n"
                "        {\n"
                '            let _ = std::fs::write(".harness/phase7-gap", b"x");\n'
                "        }\n",
            ),
        ):
            expect_portability_rejection(
                f"{method_name} {label}",
                source[:attribute_start] + injected + source[attribute_start:],
            )
        expect_portability_rejection(
            f"{method_name} unconditional filesystem write after refusal",
            source[:block_end]
            + '        std::fs::write(".harness/phase7-gap", b"x").unwrap();\n'
            + source[block_end:],
        )
        success = f"""{{
            let _ = {inert_arguments[method_name]};
            // safe descriptor-anchored mutation is unavailable until Phase 7
            Ok(MutationResult::RolledBack)
        }}"""
        mutated = source[:block_start] + success + source[block_end:]
        expect_portability_rejection(
            f"non-Unix {method_name} success with unused refusal marker",
            mutated,
        )


def proof_atomic_race_boundary() -> None:
    source = text(RECOVERY)
    for fragment in [
        "OFlags::NOFOLLOW",
        "RenameFlags::NOREPLACE",
        "RenameFlags::EXCHANGE",
        "exchanged_stat.st_ino != destination_stat.st_ino",
        "intervening bytes were preserved",
        "root_path",
        "same_root_stat",
        "rollback_rejects_repository_root_pathname_replacement",
        'target_os = "linux"',
        'target_os = "macos"',
        "Phase 7 platform gate remains closed",
        "final_component_swap_is_reversed_without_clobbering_intervening_bytes",
    ]:
        check(fragment in source, f"final-component race proof omits {fragment}")


def proof_manifest_last_and_rollback() -> None:
    source = text(RECOVERY)
    integration = text(INTEGRATION)
    check("manifest_index + 1 != journal.steps.len()" in source, "manifest-last check missing")
    for fragment in [
        "JournalState::RollingBack",
        "journal.state = JournalState::RollingBack",
        "restore_missing_manifest",
        "removed new manifest before rollback",
        "restored old manifest last journal fsync",
        "validate_recovery_manifest_state",
        "manifest_is_committed_last_and_rollback_removes_exact_created_images",
        "rollback_does_not_restore_old_manifest_when_manifest_step_was_never_applied",
        "target_edit_blocks_rollback_before_any_restoration",
    ]:
        check(fragment in source, f"rollback protocol omits {fragment}")
    for test in [
        "every_committed_update_rollback_checkpoint_resumes_in_reverse_with_old_manifest_last",
        "human_edit_during_committed_update_rollback_is_preserved_before_old_manifest_restore",
        "rollback_deliberately_requires_live_release_authorization_before_using_local_evidence",
    ]:
        check(test in integration, f"rollback integration oracle is missing: {test}")


def proof_status_probe_and_exact_rerun() -> None:
    recovery = text(RECOVERY)
    application = text(APPLICATION)
    integration = text(INTEGRATION)
    grammar = json.loads(text(ROOT / "release/contracts/v1/command-grammars.json"))
    status = next(command for command in grammar["core"]["commands"] if command["name"] == "status")
    check(status["exits"] == [0, 3, 64, 70, 74], "frozen status exits changed")
    check("fn probe_recovery(&self)" in recovery, "read-only mutation-boundary probe missing")
    check(
        "JournalState::Prepared | JournalState::Applying" in recovery,
        "probe broadened beyond actionable nonterminal states",
    )
    check("if status { 3 } else { 4 }" in application, "status/mutator recovery exits are conflated")
    for test in [
        "status_and_exact_rerun_report_recovery_without_replay_and_audit_is_read_only",
        "recovery_status_preserves_authoritative_manifest_mode_and_declared_readiness",
        "damaged_applying_update_evidence_is_non_actionable_and_preserves_the_tree",
    ]:
        check(test in integration, f"read-only recovery oracle missing: {test}")


def proof_signed_mutation_behaviors() -> None:
    source = text(INTEGRATION)
    expected = [
        "signed_install_requires_exact_confirmation_commits_manifest_last_and_is_idempotent",
        "preview_sha256_matches_the_exact_emitted_operations_array",
        "scaffold_is_exact_and_update_preserves_target_owned_bytes",
        "identical_preexisting_asset_commits_brownfield_mode_and_target_ownership",
        "fresh_install_recovery_commits_exact_v0_archive_receipt_without_reading_sqlite",
        "custody_replacement_between_pin_and_first_read_is_rejected_without_manifest",
        "recovery_revalidates_the_previewed_custody_directory_identity",
        "managed_file_drift_returns_exact_three_way_review_without_writing",
        "managed_block_update_replaces_only_authenticated_interior",
    ]
    for name in expected:
        check(f"fn {name}" in source, f"signed integration proof missing: {name}")
    check("core-payload-index.signatures.json" in source, "integration does not use signed release")
    check("test-bootstrap-anchors.json" in source, "integration does not use pinned test roots")


def proof_kill_points_and_idempotency() -> None:
    source = text(INTEGRATION)
    check("for checkpoint in 1..=18" in source, "all 18 install kill points are not enumerated")
    check("for checkpoint in 1..=15" in source, "all 15 update kill points are not enumerated")
    check(
        "for checkpoint in 1..=13" in source,
        "all 13 committed-update rollback checkpoints are not enumerated",
    )
    check(
        "every_install_kill_point_has_a_deterministic_rerun_resume_or_rollback" in source,
        "kill-point recovery proof missing",
    )
    check(
        "every_update_backup_exchange_and_manifest_kill_point_resumes_deterministically"
        in source,
        "update backup/exchange kill-point proof missing",
    )
    check(source.count("idempotent-noop") >= 2, "install/scaffold idempotency assertions missing")
    recovery = text(RECOVERY)
    check("write_owned_once" in recovery and "existing == bytes" in recovery, "pre-journal rerun cannot reuse exact evidence")


def proof_closed_dependency_and_execution_boundary() -> None:
    cargo = text(CORE / "Cargo.toml")
    sources = "\n".join(text(path) for path in sorted((CORE / "src").glob("*.rs")))
    for forbidden in ["rusqlite", "sqlite", "changeset"]:
        check(forbidden not in cargo.lower(), f"harness-core dependency includes {forbidden}")
    for forbidden in ["std::process::Command", "Command::new(", "language detection"]:
        check(forbidden not in sources, f"core can execute/infer a target boundary: {forbidden}")
    grammar = json.loads(text(ROOT / "release/contracts/v1/command-grammars.json"))["core"]
    check(grammar["top_level"] == ["install", "update", "audit", "scaffold", "status", "version"], "six-command grammar changed")


def proof_phase4_and_phase7_gates() -> None:
    main = text(CORE / "src" / "main.rs")
    check("UnavailableReleasePort" in main and "UnavailableTrustPort" in main, "production release/trust was promoted")
    check(
        "HarnessCore::with_mutations" in main
        and "DirectoryReleasePort" in main
        and "JsonTrustPort" in main
        and main.index("authenticate_executable_and_platform()")
        < main.index("parse(std::env::args_os().skip(1))"),
        "Phase 7 local mutation path lacks external trust or pre-execution authentication",
    )
    check((ROOT / "crates/harness-v0-migrate").is_dir(), "Phase 4 isolated bridge crate is missing")
    check((ROOT / ".github/workflows/harness-v0-bridge-release.yml").is_file(), "Phase 4 unpromoted bridge workflow is missing")
    cargo = text(ROOT / "crates/harness-core/Cargo.toml").lower()
    check("harness-v0-migrate" not in cargo and "rusqlite" not in cargo,
          "Phase 4 bridge or SQLite dependency entered permanent core")
    check("safe descriptor-anchored mutation is unavailable until Phase 7" in text(RECOVERY), "non-Unix fail-closed boundary missing")
    phase7 = text(ROOT / "docs/stories/US-112-v1-phase7-portability-release-proof/validation.md")
    check(
        "no complete five-platform" in phase7
        and "no acceptance or promotion" in phase7
        and "github-sigstore-attested" in phase7
        and "production signing remains blocked" in phase7,
        "Phase 7 local execution work opened platform or promotion authority",
    )


def proof_protected_paths_unchanged() -> None:
    changed_lines = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    changed = "\n".join(
        line
        for line in changed_lines
        if len(line) < 4 or line[3:] not in ALLOWED_LATER_CHANGESETS
    )
    check(
        ".harness/changesets/unrelated.changeset.jsonl"
        not in ALLOWED_LATER_CHANGESETS,
        "later-phase changeset boundary admits an unrelated path",
    )
    for forbidden in [
        ".harness/changesets/",
        "repomix-output.xml",
        "crates/harness-cli/",
        "scripts/schema/",
    ]:
        check(forbidden not in changed, f"protected Phase 3 path changed: {forbidden}")


def proof_story_packet() -> None:
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        path = STORY / name
        check(path.is_file() and path.stat().st_size > 1000, f"US-108 packet incomplete: {name}")
    combined = "\n".join(text(STORY / name) for name in ["overview.md", "design.md", "execplan.md", "validation.md"])
    for phrase in [
        "manifest-last",
        "hard link",
        "st_dev",
        "st_ino",
        "same-UID malicious process",
        "three-way",
        "never-auto-patch",
        "target-owned",
        "creates/<step-id>.link",
        "fsync",
        "atomic",
        "Phase 4",
        "Phase 7",
    ]:
        check(phrase in combined, f"US-108 packet omits {phrase}")


def main() -> None:
    proof("planned writes exactly bind public preview operations", proof_exact_plan_binding)
    proof("recovery binds exact authenticated and derived post-images", proof_authenticated_recovery_binding)
    proof(
        "journal validation compiles portably without exposing Unix mutation",
        proof_portable_journal_validation_boundary,
    )
    proof(
        "portable journal validation cfg and non-Unix success adversaries fail closed",
        proof_portable_journal_validation_adversaries,
    )
    proof("descriptor-anchored atomic replacement detects final-component races", proof_atomic_race_boundary)
    proof("manifest-last rollback restores only applied owned images", proof_manifest_last_and_rollback)
    proof("status probe and exact rerun are read-only and contract-correct", proof_status_probe_and_exact_rerun)
    proof("signed install/update/scaffold ownership behaviors are covered", proof_signed_mutation_behaviors)
    proof("all install/update kill points and idempotent reruns are covered", proof_kill_points_and_idempotency)
    proof("six-command core has no database, changeset, or target execution dependency", proof_closed_dependency_and_execution_boundary)
    proof(
        "Phase 4 production and Phase 7 acceptance/promotion gates remain closed",
        proof_phase4_and_phase7_gates,
    )
    proof("protected V0, changeset, database, and repomix paths are untouched", proof_protected_paths_unchanged)
    proof("US-108 implementation, design, execution, and validation packet exists", proof_story_packet)
    print(f"V1 Phase 3 recovery verification passed ({PASS_COUNT} proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"V1 Phase 3 recovery verification failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error
