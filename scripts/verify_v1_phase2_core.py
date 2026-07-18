#!/usr/bin/env python3
"""Mechanical positive/negative proof for the Repository Harness V1 Phase 2 core."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import Any, Callable

from verify_v1_phase1_contracts import ContractError, validate_schema

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "contracts" / "v1"
CLI = ROOT / "scripts" / "bin" / ("harness.exe" if os.name == "nt" else "harness")
SOURCE = ROOT / "crates" / "harness-core" / "src" / "command_spec.rs"
EXPECTED_TOP_LEVEL = ["install", "update", "audit", "scaffold", "status", "version"]
EXPECTED_EXITS = {
    "install": [0, 2, 3, 4, 64, 70, 74],
    "update": [0, 2, 3, 4, 64, 70, 74],
    "audit": [0, 2, 3, 64, 70, 74],
    "scaffold": [0, 3, 4, 64, 70, 74],
    "status": [0, 3, 64, 70, 74],
    "version": [0, 64, 70],
}
FORBIDDEN_COMMANDS = [
    "migrate", "inspect", "export", "archive", "preview", "apply", "resume", "rollback",
    "init", "intake", "story", "query", "db",
]


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


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=duplicate_rejecting_object)


def parse_envelope(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    envelope = json.loads(result.stdout, object_pairs_hook=duplicate_rejecting_object)
    validate_schema(envelope, load_json(CONTRACT / "schemas/output-envelope-v1.schema.json"))
    return envelope


def expect_schema_failure(value: Any, schema: dict[str, Any], label: str) -> None:
    try:
        validate_schema(value, schema)
    except ContractError:
        return
    raise VerificationError(f"negative schema fixture unexpectedly passed: {label}")


def run_cli(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CLI), *arguments],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def source_spec() -> dict[str, Any]:
    source = SOURCE.read_text(encoding="utf-8")
    match = re.search(
        r"// CORE_COMMAND_SPEC_JSON_BEGIN.*?pub const CORE_COMMAND_SPEC_JSON: &str = r#\"(?P<json>.*?)\"#;.*?// CORE_COMMAND_SPEC_JSON_END",
        source,
        re.DOTALL,
    )
    check(match is not None, "source command extraction markers are missing")
    return json.loads(match.group("json"), object_pairs_hook=duplicate_rejecting_object)


def assert_exact_grammar(candidate: dict[str, Any], authority: dict[str, Any]) -> None:
    check(candidate == authority, "command order/options/exits/mutation boundary differs")
    check(candidate["top_level"] == EXPECTED_TOP_LEVEL, "top-level command order differs")
    check([entry["name"] for entry in candidate["commands"]] == EXPECTED_TOP_LEVEL, "source command definition order differs")
    check({entry["name"]: entry["exits"] for entry in candidate["commands"]} == EXPECTED_EXITS, "source exit matrix differs")


def expect_grammar_failure(candidate: dict[str, Any], authority: dict[str, Any], label: str) -> None:
    try:
        assert_exact_grammar(candidate, authority)
    except VerificationError:
        return
    raise VerificationError(f"negative grammar drift passed: {label}")


def proof_live_grammar() -> None:
    grammar = load_json(CONTRACT / "command-grammars.json")
    authority = grammar["core"]
    binding = load_json(CONTRACT / "command-implementation-binding.json")
    check(binding["binding_state"] == "core-live-bridge-live-unpromoted", "binding lifecycle is not core-live/bridge-live-unpromoted")
    check(binding["surfaces"]["core"]["entrypoints"] == authority["binary"], "binding binary identities differ")
    check(binding["surfaces"]["core"]["live_binding"]["source_command_definitions"] == SOURCE.relative_to(ROOT).as_posix(), "binding source path differs")
    check(CLI.is_file() and (os.name == "nt" or os.access(CLI, os.X_OK)), "platform-native scripts/bin/harness identity is not live")
    help_result = run_cli(["--help"], ROOT)
    check(help_result.returncode == 0 and help_result.stderr == "", "live machine help failed")
    help_spec = json.loads(help_result.stdout, object_pairs_hook=duplicate_rejecting_object)
    assert_exact_grammar(help_spec, authority)
    assert_exact_grammar(source_spec(), authority)

    extra = json.loads(json.dumps(authority))
    extra["top_level"].append("migrate")
    expect_grammar_failure(extra, authority, "extra command")
    reordered = json.loads(json.dumps(authority))
    reordered["top_level"][0:2] = reversed(reordered["top_level"][0:2])
    expect_grammar_failure(reordered, authority, "reordered command")
    option_drift = json.loads(json.dumps(authority))
    option_drift["commands"][0]["options"].append("--database")
    expect_grammar_failure(option_drift, authority, "extra option")
    exit_drift = json.loads(json.dumps(authority))
    exit_drift["commands"][2]["exits"].append(5)
    expect_grammar_failure(exit_drift, authority, "extra exit")


def proof_closed_dispatch_and_identity() -> None:
    for command in FORBIDDEN_COMMANDS + ["help", "unknown"]:
        result = run_cli([command], ROOT)
        check(result.returncode == 64, f"forbidden command {command} did not exit 64")
        check(result.stdout == "", f"forbidden command {command} emitted success output")
    version = run_cli(["version"], ROOT)
    alias = run_cli(["--version"], ROOT)
    check(version.returncode == alias.returncode == 0, "version identity failed")
    check(version.stdout == alias.stdout and version.stderr == alias.stderr == "", "version and --version differ")
    cargo = (ROOT / "crates/harness-core/Cargo.toml").read_text(encoding="utf-8")
    check('name = "harness-core"' in cargo and 'name = "harness"' in cargo, "Cargo binary is not harness/harness.exe")
    main_source = (ROOT / "crates/harness-core/src/main.rs").read_text(encoding="utf-8")
    check(
        main_source.index("if matches!(&command, Command::Version")
        < main_source.index("std::env::current_dir"),
        "live version constructs or opens repository state",
    )
    bridge_cli = ROOT / "scripts/bin" / ("harness-v0-migrate.exe" if os.name == "nt" else "harness-v0-migrate")
    check(bridge_cli.is_file(), "Phase 4 live-unpromoted bridge identity is missing")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def manifest(roles: list[dict[str, Any]]) -> bytes:
    return (json.dumps({
        "schema": "repository-harness-manifest/v1",
        "repository_mode": "fresh-v1",
        "compatibility": {
            "cli_min": "1.0.0",
            "cli_max": "1.0.0",
            "template_release_min": "1.0.0",
            "template_release_max": "1.0.0",
        },
        "payload": {
            "trust_domain": "repository-harness-core",
            "role": "core-release",
            "sequence": 44,
            "index_sha256": "0e2f88897e5c18ce8b1515a0c6de2f6bcfac97994fac3320965afd51ef1ddcdb",
        },
        "roles": roles,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def role(role_id: str, asset: str, path: str, contents: bytes, *, activation: str = "active", markers: list[str] | None = None) -> dict[str, Any]:
    return {
        "role": role_id,
        "asset": asset,
        "activation": activation,
        "ownership": "managed-file",
        "origin": "created",
        "required": True,
        "path": path,
        "template": asset,
        "template_release": "1.0.0",
        "base_sha256": sha256(contents),
        "current_sha256": sha256(contents),
        "update_policy": "replace-if-base",
        "unresolved_markers": markers or [],
    }


def tree_snapshot(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            result[relative] = (stat.S_IMODE(path.stat().st_mode), sha256(path.read_bytes()))
        elif path.is_dir():
            result[relative + "/"] = (stat.S_IMODE(path.stat().st_mode), "directory")
    return result


def proof_audit_no_exec_and_determinism() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-v1-audit-canary-") as temporary:
        root = Path(temporary)
        (root / ".harness").mkdir()
        canary = b"#!/usr/bin/env sh\nprintf executed > audit-spawned-canary\n"
        definition = b"# Declared Tool Definition\n\ntarget-tool = ./audit-canary.sh\nproof-command = ./audit-canary.sh\n\n[canary bytes](audit-canary.sh)\n"
        (root / "audit-canary.sh").write_bytes(canary)
        (root / "audit-canary.sh").chmod(0o755)
        (root / "tool-definition.md").write_bytes(definition)
        roles = [
            role("audit_canary", "audit-canary", "audit-canary.sh", canary),
            role("tool_definition", "tool-definition", "tool-definition.md", definition),
        ]
        (root / ".harness/manifest.json").write_bytes(manifest(roles))
        before = tree_snapshot(root)
        first = run_cli(["audit", "--json"], root)
        second = run_cli(["audit", "--json"], root)
        check(first.returncode == second.returncode == 0, f"audit canary was not ready: {first.stderr}{first.stdout}")
        check(first.stdout == second.stdout and first.stderr == second.stderr == "", "audit output is nondeterministic")
        envelope = parse_envelope(first)
        check(envelope["outcome"] == "ready" and envelope["mutation"] == "none", "audit envelope is not ready/read-only")
        check(tree_snapshot(root) == before, "audit changed declared filesystem state")
        check(not (root / "audit-spawned-canary").exists(), "audit executed the target-tool canary")


def proof_manifest_and_output_boundaries() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-v1-manifest-") as temporary:
        root = Path(temporary)
        (root / ".harness").mkdir()
        unresolved = b"# Managed\nREPOSITORY-HARNESS-UNRESOLVED(agent_map:test-command)\n"
        marker = "REPOSITORY-HARNESS-UNRESOLVED(agent_map:test-command)"
        (root / "managed.md").write_bytes(unresolved)
        (root / ".harness/manifest.json").write_bytes(manifest([
            role("agent_map", "agent-map", "managed.md", unresolved, activation="unresolved", markers=[marker])
        ]))
        first = run_cli(["audit", "--json"], root)
        second = run_cli(["audit", "--json"], root)
        check(first.returncode == second.returncode == 2 and first.stdout == second.stdout, "unresolved audit is not deterministic exit 2")
        check(parse_envelope(first)["details"]["readiness"] == "unresolved", "unresolved envelope differs")

        value = json.loads((root / ".harness/manifest.json").read_text())
        value["tasks"] = []
        (root / ".harness/manifest.json").write_text(json.dumps(value), encoding="utf-8")
        invalid = run_cli(["audit", "--json"], root)
        check(invalid.returncode == 3, "forbidden operational manifest field did not exit 3")
        invalid_envelope = parse_envelope(invalid)
        check(invalid_envelope["outcome"] == "invalid", "forbidden manifest field was not invalid")
        encoded = json.dumps(invalid_envelope)
        for forbidden in ["raw_command_output", "telemetry", '"tasks"']:
            check(forbidden not in encoded, f"output envelope leaked operational field {forbidden}")


def proof_mutation_refusal_is_noop() -> None:
    cases = [
        (["install"], 4),
        (["install", "--preview"], 4),
        (["install", "--resume", "op-phase3"], 4),
        (["update"], 4),
        (["update", "--rollback", "op-phase3"], 4),
        (["scaffold", "--template", "decision-template", "--destination", "docs/decision.md"], 4),
        (["scaffold", "--template", "decision-template", "--destination", "docs/decision.md", "--preview"], 4),
        (["migrate"], 64),
        (["install", "--non-interactive"], 64),
    ]
    with tempfile.TemporaryDirectory(prefix="harness-v1-mutation-noop-") as temporary:
        root = Path(temporary)
        (root / "owned.txt").write_text("target-owned\n", encoding="utf-8")
        before = tree_snapshot(root)
        for arguments, expected in cases:
            result = run_cli(arguments, root)
            check(result.returncode == expected, f"{' '.join(arguments)} exited {result.returncode}, expected {expected}")
            check(tree_snapshot(root) == before, f"{' '.join(arguments)} mutated Phase 2 repository bytes")
        check(not (root / ".harness").exists(), "Phase 2 mutation refusal created Harness state")


def proof_dependency_and_port_boundary() -> None:
    cargo = (ROOT / "crates/harness-core/Cargo.toml").read_text(encoding="utf-8")
    dependency_block = cargo.split("[dependencies]", 1)[1].split("[dev-dependencies]", 1)[0]
    for forbidden in ["rusqlite", "harness-cli", "sqlite", "tokio", "reqwest"]:
        check(forbidden not in dependency_block, f"pure core depends on forbidden {forbidden}")
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "crates/harness-core/src").glob("*.rs")))
    for forbidden in ["std::process::Command", "Command::new(", "rusqlite::", "tokio::process"]:
        check(forbidden not in source, f"pure core contains process/database executor surface: {forbidden}")
    ports = (ROOT / "crates/harness-core/src/ports.rs").read_text(encoding="utf-8")
    for required in ["trait FileSystemPort", "trait ManifestPort", "trait ReleasePort", "trait TrustPort"]:
        check(required in ports, f"explicit dependency-injection port missing: {required}")
    check("fn write" not in ports and "process" not in ports.lower(), "Phase 2 port surface can write or spawn")


def proof_independent_trust_and_lifecycle_tests() -> None:
    ports = (ROOT / "crates/harness-core/src/ports.rs").read_text(encoding="utf-8")
    trust = (ROOT / "crates/harness-core/src/trust.rs").read_text(encoding="utf-8")
    tests = (ROOT / "crates/harness-core/tests/phase2_core.rs").read_text(encoding="utf-8")
    material = re.search(r"pub struct ReleaseMaterial \{(?P<body>.*?)\n\}", ports, re.DOTALL)
    check(material is not None, "release material structure is missing")
    for forbidden in ["trusted_root", "trust_policy", "freshness"]:
        check(forbidden not in material.group("body"), f"downloaded release material can select {forbidden}")
    for required in [
        "pub struct ReleaseTrustInput", "pub trait TrustPort", "trust_bundle_signatures",
        "FirstInstallExactDigest", "FirstInstallMinimumSequence", "path_ledger_sha256",
    ]:
        check(required in ports, f"independent trust input omits {required}")
    for required in [
        "CORE_BUNDLE_SIGNATURE_DOMAIN", "previous_bundle_sha256", "CORE_ROTATION_ROLE",
        "authorize_release_freshness", "verify_rollback", "retained_release_high_water",
        "production policy rejects test-fixture", "parse_canonical_envelope",
    ]:
        check(required in trust, f"trust lifecycle implementation omits {required}")
    for executed_case in [
        "trust_bundle_requires_independent_anchor_and_detached_envelope",
        "trust_lifecycle_rejects_stale_revoked_and_incomplete_rotation_states",
        "rollback_requires_exact_active_root_authorization_and_retains_high_water",
        "offline_first_install_pin_is_mandatory_and_fixture_trust_is_test_only",
        "path_ledger_requires_an_independent_canonical_digest_pin",
        "detached_signature_envelopes_require_canonical_jcs_bytes",
        "WRONG_ROOT_ROLLBACK", "ROTATION_TRUST_SIGNATURES", "REVOCATION_TRUST_SIGNATURES",
    ]:
        check(executed_case in tests, f"executed trust adversary coverage omits {executed_case}")


def proof_snapshot_unicode_and_runtime_error_tests() -> None:
    filesystem = (ROOT / "crates/harness-core/src/infrastructure.rs").read_text(encoding="utf-8")
    application = (ROOT / "crates/harness-core/src/application.rs").read_text(encoding="utf-8")
    unicode_table = (ROOT / "crates/harness-core/src/unicode_casefold.rs").read_text(encoding="utf-8")
    tests = (ROOT / "crates/harness-core/tests/phase2_core.rs").read_text(encoding="utf-8")
    for required in [
        "root: std::os::fd::OwnedFd", "validate_root_namespace", "read_declared_unix_with_hook",
        "AfterFirstRead", "AfterSecondRead", "bytes != verification_bytes", "st_ctime_nsec",
        "safe command-scoped filesystem snapshots are unavailable on this platform until Phase 7",
        "command_snapshot_pins_root_and_rejects_root_namespace_replacement",
        "synchronized_ancestor_and_final_swaps_fail_closed",
        "same_size_in_place_rewrite_between_exact_reads_fails_closed",
    ]:
        check(required in filesystem, f"snapshot implementation/proof omits {required}")
    check('UNICODE_CASEFOLD_VERSION: &str = "13.0.0"' in unicode_table, "Unicode fold table is not version pinned")
    for required in ["ſ", "ﬀ"]:
        check(required in unicode_table, f"Unicode fold coverage omits {required!r}")
    check("PortError::Io { path, message }" in application and "Outcome::Unsupported" in application,
          "I/O failures are not kept separate from validated invalid state")
    for executed_case in ["changed_snapshot_uses_documented_read_only_exit_74", "io_errors_map_to_exit_74"]:
        check(executed_case in tests, f"runtime error mapping coverage omits {executed_case}")


def proof_schema_commonmark_and_human_parity() -> None:
    schema = load_json(CONTRACT / "schemas/manifest-v1.schema.json")
    markdown = (ROOT / "crates/harness-core/src/markdown.rs").read_text(encoding="utf-8")
    tests = (ROOT / "crates/harness-core/tests/phase2_core.rs").read_text(encoding="utf-8")
    application = (ROOT / "crates/harness-core/src/application.rs").read_text(encoding="utf-8")
    interface = (ROOT / "crates/harness-core/src/interface.rs").read_text(encoding="utf-8")
    main_source = (ROOT / "crates/harness-core/src/main.rs").read_text(encoding="utf-8")
    for required in [
        "pulldown_cmark", "Parser::new", "Tag::Link", "Tag::Image", "Tag::Heading",
        "Event::SoftBreak", "github_anchor", "parses_multiline_commonmark_links_and_headings",
    ]:
        check(required in markdown, f"CommonMark structural implementation omits {required}")
    for executed_case in [
        "commonmark_links_and_anchors_are_structural_without_false_code_links",
        "same_document_commonmark_fragments_validate_percent_unicode_and_duplicates",
        "runtime_manifest_validation_matches_closed_schema_constraints",
        "extra_closing_marker_and_control_character_output_injection_are_invalid",
        "human_output_is_a_case_preserving_projection_of_the_json_envelope",
        "output_write_failures_use_contracted_exit_instead_of_panicking",
    ]:
        check(executed_case in tests or executed_case in interface or executed_case in main_source,
              f"structural/schema/rendering coverage omits {executed_case}")
    check("has_uri_scheme" in application and "raw.split_once('#')" in application
          and "scheme.len() == 1" in application and "C:/Users/alice" in tests,
          "relative-link audit does not separate URI schemes, path encoding, and fragments")
    check("print!(" not in main_source and "eprintln!(" not in main_source,
          "CLI output still uses panic-on-write macros")

    with tempfile.TemporaryDirectory(prefix="harness-v1-schema-differential-") as temporary:
        root = Path(temporary)
        (root / ".harness").mkdir()
        (root / "Docs").mkdir()
        contents = b"# Case Sensitive Heading\n"
        (root / "Docs/CaseSensitive.md").write_bytes(contents)
        valid = json.loads(manifest([role(
            "case_sensitive", "case-sensitive", "Docs/CaseSensitive.md", contents
        )]))
        (root / ".harness/manifest.json").write_text(json.dumps(valid), encoding="utf-8")

        machine = run_cli(["audit", "--json"], root)
        human = run_cli(["audit"], root)
        check(machine.returncode == human.returncode == 0, "valid schema/parity fixture did not audit ready")
        envelope = parse_envelope(machine)
        projections = {
            "schema": "schema", "command": "command", "outcome": "outcome",
            "exit_code": "exit-code", "mutation": "mutation", "repository_mode": "repository-mode",
        }
        for field, label in projections.items():
            check(f"{label}: {envelope[field]}\n" in human.stdout, f"human output omits JSON field {field}")
        check("release-role: core-release\n" in human.stdout, "human output omits release role")
        check("release-sequence: 44\n" in human.stdout, "human output omits release sequence")
        check("details-readiness: ready\n" in human.stdout, "human output omits readiness")

        maximum = json.loads(json.dumps(valid))
        maximum["payload"]["sequence"] = 9007199254740991
        validate_schema(maximum, schema)
        (root / ".harness/manifest.json").write_text(json.dumps(maximum), encoding="utf-8")
        maximum_result = run_cli(["audit", "--json"], root)
        check(maximum_result.returncode == 0, "runtime rejected schema-valid interoperable maximum sequence")
        check(parse_envelope(maximum_result)["release"]["sequence"] == 9007199254740991,
              "runtime changed the schema-valid interoperable maximum sequence")

        cases: list[tuple[str, str, Any]] = [
            ("bad role", "/roles/0/role", "Bad-Role"),
            ("bad asset", "/roles/0/asset", "_asset"),
            ("bad digest", "/roles/0/current_sha256", "A" * 64),
            ("zero sequence", "/payload/sequence", 0),
            ("non-interoperable sequence", "/payload/sequence", 9007199254740992),
            ("wrong domain", "/payload/trust_domain", "repository-harness-bridge"),
        ]
        for label, pointer, replacement in cases:
            candidate = json.loads(json.dumps(valid))
            cursor = candidate
            components = pointer.strip("/").split("/")
            for component in components[:-1]:
                cursor = cursor[int(component)] if isinstance(cursor, list) else cursor[component]
            final = components[-1]
            if isinstance(cursor, list):
                cursor[int(final)] = replacement
            else:
                cursor[final] = replacement
            expect_schema_failure(candidate, schema, label)
            (root / ".harness/manifest.json").write_text(json.dumps(candidate), encoding="utf-8")
            result = run_cli(["audit", "--json"], root)
            check(result.returncode == 3, f"runtime accepted schema-negative fixture: {label}")
            check(parse_envelope(result)["outcome"] == "invalid", f"schema negative was miscategorized: {label}")

        injected = json.loads(json.dumps(valid))
        injected["roles"][0]["path"] = "evil\ninjected.md"
        (root / ".harness/manifest.json").write_text(json.dumps(injected), encoding="utf-8")
        rendered = run_cli(["audit"], root)
        check(rendered.returncode == 3, "control-character path was accepted")
        check("evil\\u{a}injected.md" in rendered.stdout and "evil\ninjected.md" not in rendered.stdout,
              "human output permits control-character line injection")


def proof_workflow_lifecycle_guard() -> None:
    identity = load_json(CONTRACT / "bootstrap-identity.json")
    lifecycle = identity["core"]["workflow_lifecycle"]
    check(identity["repository"] == "hoangnb24/repository-harness", "bootstrap repository identity differs")
    check(identity["core"]["protected_workflow"] == ".github/workflows/harness-v1-release.yml@refs/heads/main", "protected workflow identity differs")
    check(lifecycle["state"] == "source-present-unpromoted", "core workflow source is not present-unpromoted")
    check(lifecycle["production_bootstrap_acceptance"] == "blocked-until-promotion-gate", "production bootstrap was promoted")
    check(lifecycle["external_evidence"] == {"repository_protection": "required-not-present", "pinned_artifact_attestation": "required-not-present"}, "external evidence was falsely claimed")
    workflow = (ROOT / ".github/workflows/harness-v1-release.yml").read_text(encoding="utf-8")
    for fragment in [
        "github.repository == 'hoangnb24/repository-harness'",
        "prove-before-promotion:",
        "promotion-blocked:",
        "needs: prove-before-promotion",
        "mkdir -p scripts/bin",
        "New-Item -ItemType Directory -Force scripts/bin",
        "exit 1",
    ]:
        check(fragment in workflow, f"workflow proof-before-promotion structure omits {fragment}")
    for forbidden in ["contents: write", "id-token: write", "gh release create", "git push", "git tag"]:
        check(forbidden not in workflow, f"unpromoted workflow contains promotion capability: {forbidden}")
    bridge = identity["bridge"]["workflow_lifecycle"]
    check(bridge["state"] == "source-present-unpromoted" and bridge["source_path"] == ".github/workflows/harness-v0-bridge-release.yml",
          "bridge lifecycle is not source-present-unpromoted")
    check(bridge["production_bootstrap_acceptance"] == "blocked-until-promotion-gate", "bridge production bootstrap was promoted")
    check(bridge["external_evidence"] == {"repository_protection": "required-not-present", "pinned_artifact_attestation": "required-not-present"},
          "bridge external evidence was falsely claimed")
    bridge_workflow = (ROOT / ".github/workflows/harness-v0-bridge-release.yml").read_text(encoding="utf-8")
    for fragment in ["Repository Harness V0 Bridge Proof (Unpromoted)", "prove-before-promotion:",
                     "promotion-blocked:", "Phase 7, repository-protection, and pinned artifact-attestation evidence are not present", "exit 1"]:
        check(fragment in bridge_workflow, f"bridge workflow proof-before-promotion structure omits {fragment}")
    for forbidden in ["contents: write", "id-token: write", "gh release create", "git push", "git tag"]:
        check(forbidden not in bridge_workflow, f"unpromoted bridge workflow contains promotion capability: {forbidden}")


def proof_story_packet_and_phase3_boundary() -> None:
    story = ROOT / "docs/stories/US-107-v1-pure-core"
    for name in ["overview.md", "design.md", "execplan.md", "validation.md"]:
        path = story / name
        check(path.is_file() and path.stat().st_size > 1000, f"US-107 packet is missing/incomplete: {name}")
    design = (story / "design.md").read_text(encoding="utf-8")
    validation = (story / "validation.md").read_text(encoding="utf-8")
    for phrase in ["FileSystemPort", "ManifestPort", "ReleasePort", "TrustPort", "audit-canary.sh", "openat", "Phase 3"]:
        check(phrase in design, f"US-107 design omits concrete boundary: {phrase}")
    for phrase in [
        "Residual Phase 3 Gates", "Residual Phase 4 And Phase 7 Gates",
        "46 tests", "11/11 proof groups", "accepted exact candidate", "integrated as `e77e028`",
        "journal ownership", "target edit", "exit 4",
    ]:
        check(phrase in validation, f"US-107 validation omits residual gate: {phrase}")


def main() -> None:
    os.chdir(ROOT)
    proof("live CLI help and source definitions exactly match frozen grammar", proof_live_grammar)
    proof("exact harness/harness.exe identity and closed six-command dispatch", proof_closed_dispatch_and_identity)
    proof("audit is deterministic, read-only, and never executes target canary", proof_audit_no_exec_and_determinism)
    proof("manifest forbidden fields, unresolved exits, and output determinism", proof_manifest_and_output_boundaries)
    proof("Phase 2 install/update/scaffold and recovery states are safe no-ops", proof_mutation_refusal_is_noop)
    proof("pure filesystem/manifest/release/trust ports have no DB or process executor", proof_dependency_and_port_boundary)
    proof("independent pinned trust and authenticated lifecycle adversaries pass", proof_independent_trust_and_lifecycle_tests)
    proof("pinned snapshots, Unicode folding, and exit mappings pass runtime tests", proof_snapshot_unicode_and_runtime_error_tests)
    proof("schema differential, CommonMark structure, and human/JSON parity pass", proof_schema_commonmark_and_human_parity)
    proof("core and bridge workflows are source-present-unpromoted with promotion blocked", proof_workflow_lifecycle_guard)
    proof("US-107 records concrete Phase 2 proof and residual Phase 3 gates", proof_story_packet_and_phase3_boundary)
    print(f"V1 Phase 2 pure core verification passed ({PASS_COUNT} proof groups)")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, ContractError, OSError, json.JSONDecodeError) as error:
        print(f"V1 Phase 2 pure core verification failed: {error}", file=os.sys.stderr)
        raise SystemExit(1) from error
