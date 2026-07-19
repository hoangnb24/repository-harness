#!/usr/bin/env python3
"""Verify signed provenance, then finalize a Phase 7 build receipt."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform as host_platform
import sys

# Prevent importing capture/provenance helpers from dirtying the checked-out
# candidate when this finalizer runs without workflow-level bytecode controls.
sys.dont_write_bytecode = True

from capture_v1_build_receipt import (
    build_receipt_document,
    committed_candidate_identity,
    committed_execution_workflow_identity,
    git_text,
    run_fixed,
    rust_host,
    validate_tuple,
    write_new_file,
)
from v1_artifact_provenance import (
    MAX_BUNDLE_BYTES,
    PROVENANCE_RECORD_NAME,
    canonical_record_bytes,
    safe_regular_bytes,
    verification_record,
    verify_signed_bundle,
)
from v1_build_receipt_common import (
    COMMAND_GRAMMAR_PATH,
    RECEIPT_NAME,
    ROOT,
    ReceiptError,
    canonical_json_bytes,
    check,
    exact_core_help_bytes,
    minimal_subprocess_environment,
    load_json,
    parse_json_bytes,
    sha256_bytes,
)


def finalize(arguments: argparse.Namespace) -> Path:
    output = Path(arguments.receipt_directory)
    check(output.is_absolute() and output.is_dir() and not output.is_symlink(), "receipt directory is missing or unsafe")
    candidate = git_text("rev-parse", "HEAD")
    check(candidate == arguments.candidate, "candidate does not equal HEAD")
    tree = git_text("rev-parse", "HEAD^{tree}")
    target, runner, artifact_name = validate_tuple(
        arguments.platform,
        arguments.target,
        arguments.runner,
        system=host_platform.system(),
        machine=host_platform.machine(),
        rust_target=rust_host(),
    )
    artifact = output / artifact_name
    checksum = output / f"{artifact_name}.sha256"
    artifact_bytes = safe_regular_bytes(artifact, "native artifact")
    checksum_bytes = safe_regular_bytes(checksum, "native artifact checksum")
    artifact_sha = sha256_bytes(artifact_bytes)
    check(checksum_bytes == f"{artifact_sha}  {artifact_name}\n".encode("ascii"), "artifact checksum record mismatch")
    check({item.name for item in output.iterdir()} == {artifact_name, checksum.name}, "unfinalized receipt directory has extra members")

    source_bundle = Path(arguments.bundle)
    bundle_bytes = safe_regular_bytes(source_bundle, "Sigstore attestation bundle", maximum=MAX_BUNDLE_BYTES)
    bundle_name = f"{artifact_name}.sigstore.json"
    bundle_path = output / bundle_name
    write_new_file(bundle_path, bundle_bytes, 0o644)
    verify_signed_bundle(
        artifact,
        bundle_path,
        candidate_sha=arguments.candidate,
        workflow_sha=arguments.workflow_revision,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha,
    )
    record = verification_record(
        platform_name=arguments.platform,
        target=target,
        runner=runner,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha,
        bundle_name=bundle_name,
        bundle_sha256=sha256_bytes(bundle_bytes),
        candidate_sha=arguments.candidate,
        workflow_sha=arguments.workflow_revision,
    )
    record_bytes = canonical_record_bytes(record)
    write_new_file(output / PROVENANCE_RECORD_NAME, record_bytes, 0o644)

    # The artifact is executed only after the exact signed bundle has verified.
    check(sha256_bytes(safe_regular_bytes(artifact, "verified artifact")) == artifact_sha, "artifact changed after provenance verification")
    if os.name != "nt":
        artifact.chmod(0o755)
    execution_environment = minimal_subprocess_environment(
        trusted_harness={
            "HARNESS_V1_ARTIFACT_SHA256": artifact_sha,
            "HARNESS_V1_PLATFORM": arguments.platform,
        }
    )
    help_result = run_fixed([str(artifact), "--help"], environment=execution_environment)
    check(help_result.returncode == 0, "native V1 harness --help failed after provenance verification")
    check(help_result.stderr == b"", "native V1 harness --help wrote stderr")
    grammar = load_json(ROOT / COMMAND_GRAMMAR_PATH)
    expected_help = exact_core_help_bytes(grammar)
    help_document = parse_json_bytes(help_result.stdout, "native V1 harness --help")
    check(help_result.stdout == expected_help and help_document == grammar["core"], "native V1 harness --help is not the exact six-command JSON grammar")
    help_name = f"{artifact_name}.help.json"
    write_new_file(output / help_name, help_result.stdout, 0o644)

    document = build_receipt_document(
        candidate_identity=committed_candidate_identity(candidate, tree),
        execution_workflow_identity=committed_execution_workflow_identity(arguments.workflow_revision),
        platform_name=arguments.platform,
        target=target,
        runner=runner,
        artifact_name=artifact_name,
        artifact_bytes=artifact_bytes,
        checksum_bytes=checksum_bytes,
        help_name=help_name,
        help_bytes=help_result.stdout,
        bundle_name=bundle_name,
        bundle_bytes=bundle_bytes,
        verification_name=PROVENANCE_RECORD_NAME,
        verification_bytes=record_bytes,
        provenance_record=record,
    )
    write_new_file(output / RECEIPT_NAME, canonical_json_bytes(document), 0o644)
    return output


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--workflow-revision", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--receipt-directory", required=True)
    parser.add_argument("--bundle", required=True)
    return parser.parse_args()


def main() -> int:
    try:
        output = finalize(parse_arguments())
    except (OSError, ReceiptError) as error:
        print(f"V1 build receipt finalization failed: {error}", file=sys.stderr)
        return 1
    print(f"V1 GitHub/Sigstore-attested non-production build receipt finalized: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
