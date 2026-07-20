#!/usr/bin/env python3
"""Cryptographically verify and close GitHub/Sigstore Phase 7 provenance."""

from __future__ import annotations

import json
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import Any, Callable

from v1_build_receipt_common import (
    PLATFORMS,
    ROOT,
    ReceiptError,
    canonical_json_bytes,
    check,
    minimal_subprocess_environment,
    sha256_bytes,
    relative_filename,
)


PROVENANCE_RECORD_NAME = "provenance-verification.json"
EXPECTED_REPOSITORY = "hoangnb24/repository-harness"
EXPECTED_SOURCE_REF = "refs/heads/refactor/harness-v1"
EXPECTED_WORKFLOW_PATH = ".github/workflows/harness-v1-release.yml"
EXPECTED_EVENT = "workflow_dispatch"
EXPECTED_ISSUER = "https://token.actions.githubusercontent.com"
EXPECTED_PREDICATE = "https://slsa.dev/provenance/v1"
MAX_BUNDLE_BYTES = 1024 * 1024
REVISION = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[bytes]]


def expected_workflow_ref(repository: str, workflow_path: str, source_ref: str) -> str:
    return f"{repository}/{workflow_path}@{source_ref}"


def expected_certificate_identity(repository: str, workflow_path: str, source_ref: str) -> str:
    return f"https://github.com/{repository}/{workflow_path}@{source_ref}"


def safe_regular_bytes(path: Path, label: str, *, maximum: int | None = None) -> bytes:
    check(path.is_file() and not path.is_symlink(), f"{label} is missing or unsafe")
    metadata = path.lstat()
    check(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file")
    payload = path.read_bytes()
    check(payload, f"{label} is empty")
    if maximum is not None:
        check(len(payload) <= maximum, f"{label} exceeds the bounded evidence size")
    return payload


def default_command_runner(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        with tempfile.TemporaryDirectory(prefix="phase7-gh-home-") as gh_home:
            verifier_environment = minimal_subprocess_environment()
            verifier_environment.update(
                {
                    "HOME": gh_home,
                    "USERPROFILE": gh_home,
                    "XDG_CONFIG_HOME": f"{gh_home}/config",
                    "XDG_STATE_HOME": f"{gh_home}/state",
                    "XDG_CACHE_HOME": f"{gh_home}/cache",
                }
            )
            return subprocess.run(
                arguments,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=verifier_environment,
                timeout=30,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReceiptError("GitHub attestation verifier is unavailable") from error


def verification_command(
    artifact: Path,
    bundle: Path,
    *,
    repository: str,
    workflow_path: str,
    source_ref: str,
    candidate_sha: str,
    workflow_sha: str,
) -> list[str]:
    return [
        "gh", "attestation", "verify", str(artifact),
        "--repo", repository,
        "--bundle", str(bundle),
        "--predicate-type", EXPECTED_PREDICATE,
        "--cert-oidc-issuer", EXPECTED_ISSUER,
        "--cert-identity", expected_certificate_identity(repository, workflow_path, source_ref),
        "--signer-digest", workflow_sha,
        "--source-digest", candidate_sha,
        "--source-ref", source_ref,
        "--deny-self-hosted-runners",
        "--format", "json",
    ]


def exact_mapping(value: Any, expected: dict[str, Any], label: str) -> None:
    check(isinstance(value, dict), f"verified attestation {label} is missing")
    for key, expected_value in expected.items():
        check(value.get(key) == expected_value, f"verified attestation {label}.{key} mismatch")


def validate_verified_output(
    payload: bytes,
    *,
    repository: str,
    workflow_path: str,
    source_ref: str,
    candidate_sha: str,
    workflow_sha: str,
    artifact_name: str,
    artifact_sha256: str,
) -> None:
    try:
        values = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReceiptError("gh attestation verify returned invalid JSON") from error
    check(isinstance(values, list) and len(values) == 1, "exactly one signed attestation must verify")
    result = values[0].get("verificationResult") if isinstance(values[0], dict) else None
    check(isinstance(result, dict), "verified attestation result is missing")
    statement = result.get("statement")
    check(isinstance(statement, dict), "verified attestation statement is missing")
    check(statement.get("predicateType") == EXPECTED_PREDICATE, "verified attestation predicate type mismatch")
    check(
        statement.get("subject") == [{"name": artifact_name, "digest": {"sha256": artifact_sha256}}],
        "verified attestation subject name or digest mismatch",
    )

    predicate = statement.get("predicate")
    check(isinstance(predicate, dict), "verified build provenance predicate is missing")
    definition = predicate.get("buildDefinition")
    check(isinstance(definition, dict), "verified build definition is missing")
    exact_mapping(
        definition.get("externalParameters", {}).get("workflow")
        if isinstance(definition.get("externalParameters"), dict) else None,
        {"repository": f"https://github.com/{repository}", "path": workflow_path, "ref": source_ref},
        "workflow",
    )
    internal = definition.get("internalParameters")
    check(
        isinstance(internal, dict)
        and isinstance(internal.get("github"), dict)
        and internal["github"].get("event_name") == EXPECTED_EVENT,
        "verified attestation event mismatch",
    )
    dependencies = definition.get("resolvedDependencies")
    check(isinstance(dependencies, list) and len(dependencies) == 1, "verified source dependency is not exact")
    exact_mapping(
        dependencies[0],
        {
            "uri": f"git+https://github.com/{repository}@{source_ref}",
            "digest": {"gitCommit": candidate_sha},
        },
        "source dependency",
    )

    signature = result.get("signature")
    certificate = signature.get("certificate") if isinstance(signature, dict) else None
    identity = expected_certificate_identity(repository, workflow_path, source_ref)
    exact_mapping(
        certificate,
        {
            "subjectAlternativeName": identity,
            "issuer": EXPECTED_ISSUER,
            "githubWorkflowTrigger": EXPECTED_EVENT,
            "githubWorkflowSHA": workflow_sha,
            "githubWorkflowRepository": repository,
            "githubWorkflowRef": source_ref,
            "buildSignerURI": identity,
            "buildSignerDigest": workflow_sha,
            "runnerEnvironment": "github-hosted",
            "sourceRepositoryURI": f"https://github.com/{repository}",
            "sourceRepositoryDigest": candidate_sha,
            "sourceRepositoryRef": source_ref,
            "buildConfigURI": identity,
            "buildConfigDigest": workflow_sha,
            "buildTrigger": EXPECTED_EVENT,
            "sourceRepositoryVisibilityAtSigning": "public",
        },
        "certificate",
    )
    timestamps = result.get("verifiedTimestamps")
    check(
        isinstance(timestamps, list)
        and timestamps
        and any(isinstance(item, dict) and item.get("type") == "Tlog" for item in timestamps),
        "verified attestation lacks a transparency-log timestamp",
    )


def verify_signed_bundle(
    artifact: Path,
    bundle: Path,
    *,
    repository: str = EXPECTED_REPOSITORY,
    workflow_path: str = EXPECTED_WORKFLOW_PATH,
    source_ref: str = EXPECTED_SOURCE_REF,
    candidate_sha: str,
    workflow_sha: str,
    artifact_name: str,
    artifact_sha256: str,
    command_runner: CommandRunner = default_command_runner,
) -> None:
    check(repository == EXPECTED_REPOSITORY, "unexpected attestation repository")
    check(workflow_path == EXPECTED_WORKFLOW_PATH, "unexpected attestation workflow path")
    check(source_ref == EXPECTED_SOURCE_REF, "unexpected attestation source ref")
    check(REVISION.fullmatch(candidate_sha) is not None, "candidate SHA is not exact 40-hex")
    check(REVISION.fullmatch(workflow_sha) is not None, "workflow SHA is not exact 40-hex")
    check(candidate_sha == workflow_sha, "candidate and workflow SHA must be identical")
    check(SHA256.fullmatch(artifact_sha256) is not None, "artifact SHA-256 is invalid")
    check(artifact.name == artifact_name, "artifact name does not match the expected platform artifact")
    artifact_payload = safe_regular_bytes(artifact, "attestation subject artifact")
    safe_regular_bytes(bundle, "Sigstore attestation bundle", maximum=MAX_BUNDLE_BYTES)
    check(sha256_bytes(artifact_payload) == artifact_sha256, "attestation subject artifact digest mismatch")
    command = verification_command(
        artifact,
        bundle,
        repository=repository,
        workflow_path=workflow_path,
        source_ref=source_ref,
        candidate_sha=candidate_sha,
        workflow_sha=workflow_sha,
    )
    result = command_runner(command)
    check(result.returncode == 0, "GitHub/Sigstore attestation verification failed closed")
    validate_verified_output(
        result.stdout,
        repository=repository,
        workflow_path=workflow_path,
        source_ref=source_ref,
        candidate_sha=candidate_sha,
        workflow_sha=workflow_sha,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
    )


def verification_record(
    *,
    platform_name: str,
    target: str,
    runner: str,
    artifact_name: str,
    artifact_sha256: str,
    bundle_name: str,
    bundle_sha256: str,
    candidate_sha: str,
    workflow_sha: str,
) -> dict[str, Any]:
    check(platform_name in PLATFORMS, "provenance platform is unsupported")
    check(PLATFORMS[platform_name] == (target, runner, artifact_name), "provenance artifact tuple mismatch")
    document = {
        "schema": "repository-harness-v1-provenance-verification/v1",
        "evidence_kind": "github-sigstore-build-provenance-verification-non-production",
        "verifier": {
            "name": "gh-attestation-verify",
            "predicate_type": EXPECTED_PREDICATE,
            "oidc_issuer": EXPECTED_ISSUER,
            "transparency_log_verified": True,
        },
        "identity": {
            "repository": EXPECTED_REPOSITORY,
            "repository_visibility": "public",
            "event_name": EXPECTED_EVENT,
            "source_ref": EXPECTED_SOURCE_REF,
            "candidate_sha": candidate_sha,
            "workflow_path": EXPECTED_WORKFLOW_PATH,
            "workflow_ref": expected_workflow_ref(EXPECTED_REPOSITORY, EXPECTED_WORKFLOW_PATH, EXPECTED_SOURCE_REF),
            "workflow_sha": workflow_sha,
        },
        "artifact": {
            "platform": platform_name,
            "target": target,
            "runner": runner,
            "name": artifact_name,
            "sha256": artifact_sha256,
        },
        "attestation": {"bundle_path": bundle_name, "bundle_sha256": bundle_sha256},
        "result": "verified-before-execution",
        "authority": {
            "provenance": "github-sigstore-attested",
            "production": False,
            "promotable": False,
            "production_signing_authorized": False,
            "phase7_accepted": False,
            "phase8": "closed",
        },
    }
    return validate_verification_record(document)


def validate_verification_record(document: Any) -> dict[str, Any]:
    check(isinstance(document, dict), "provenance verification record is not an object")
    check(
        set(document) == {"schema", "evidence_kind", "verifier", "identity", "artifact", "attestation", "result", "authority"},
        "provenance verification record fields are not closed",
    )
    check(document["schema"] == "repository-harness-v1-provenance-verification/v1", "provenance verification schema identity changed")
    check(document["evidence_kind"] == "github-sigstore-build-provenance-verification-non-production", "provenance verification production boundary changed")
    check(
        document["verifier"]
        == {
            "name": "gh-attestation-verify",
            "predicate_type": EXPECTED_PREDICATE,
            "oidc_issuer": EXPECTED_ISSUER,
            "transparency_log_verified": True,
        },
        "provenance verifier identity changed",
    )
    identity = document.get("identity")
    check(isinstance(identity, dict) and set(identity) == {"repository", "repository_visibility", "event_name", "source_ref", "candidate_sha", "workflow_path", "workflow_ref", "workflow_sha"}, "provenance identity fields are not closed")
    check(
        identity["repository"] == EXPECTED_REPOSITORY
        and identity["repository_visibility"] == "public"
        and identity["event_name"] == EXPECTED_EVENT
        and identity["source_ref"] == EXPECTED_SOURCE_REF
        and identity["workflow_path"] == EXPECTED_WORKFLOW_PATH
        and identity["workflow_ref"] == expected_workflow_ref(EXPECTED_REPOSITORY, EXPECTED_WORKFLOW_PATH, EXPECTED_SOURCE_REF)
        and isinstance(identity["candidate_sha"], str)
        and isinstance(identity["workflow_sha"], str)
        and REVISION.fullmatch(identity["candidate_sha"]) is not None
        and REVISION.fullmatch(identity["workflow_sha"]) is not None,
        "provenance identity is invalid",
    )
    artifact = document.get("artifact")
    check(isinstance(artifact, dict) and set(artifact) == {"platform", "target", "runner", "name", "sha256"}, "provenance artifact fields are not closed")
    platform_name = artifact["platform"]
    check(
        PLATFORMS.get(platform_name)
        == (
            document["artifact"]["target"],
            document["artifact"]["runner"],
            document["artifact"]["name"],
        ),
        "provenance record platform tuple mismatch",
    )
    check(
        isinstance(artifact["sha256"], str)
        and SHA256.fullmatch(artifact["sha256"]) is not None,
        "provenance artifact digest is invalid",
    )
    attestation = document.get("attestation")
    check(isinstance(attestation, dict) and set(attestation) == {"bundle_path", "bundle_sha256"}, "provenance attestation fields are not closed")
    check(
        isinstance(attestation["bundle_path"], str)
        and isinstance(attestation["bundle_sha256"], str),
        "provenance bundle identity is invalid",
    )
    relative_filename(attestation["bundle_path"], "provenance bundle path")
    check(attestation["bundle_path"].endswith(".sigstore.json") and SHA256.fullmatch(attestation["bundle_sha256"]) is not None, "provenance bundle identity is invalid")
    check(document["result"] == "verified-before-execution", "provenance verification result changed")
    check(
        document["authority"]
        == {
            "provenance": "github-sigstore-attested",
            "production": False,
            "promotable": False,
            "production_signing_authorized": False,
            "phase7_accepted": False,
            "phase8": "closed",
        },
        "provenance verification opened blocked authority",
    )
    check(identity["candidate_sha"] == identity["workflow_sha"], "provenance record candidate/workflow SHA mismatch")
    return document


def canonical_record_bytes(document: dict[str, Any]) -> bytes:
    return canonical_json_bytes(validate_verification_record(document))
