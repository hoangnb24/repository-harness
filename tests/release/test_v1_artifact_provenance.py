#!/usr/bin/env python3
"""Adversarial GitHub/Sigstore identity and byte-binding tests."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import v1_artifact_provenance as provenance  # noqa: E402
import run_v1_phase7_execution_proof as execution  # noqa: E402
from v1_build_receipt_common import (  # noqa: E402
    ReceiptError,
    minimal_subprocess_environment,
    sha256_bytes,
)


CANDIDATE = "1" * 40
ARTIFACT_NAME = "harness-linux-x64"


def verified_document(*, artifact_sha: str, mutation=None) -> bytes:
    repository = provenance.EXPECTED_REPOSITORY
    source_ref = provenance.EXPECTED_SOURCE_REF
    workflow_path = provenance.EXPECTED_WORKFLOW_PATH
    identity = provenance.expected_certificate_identity(repository, workflow_path, source_ref)
    document = [{"verificationResult": {
        "statement": {
            "predicateType": provenance.EXPECTED_PREDICATE,
            "subject": [{"name": ARTIFACT_NAME, "digest": {"sha256": artifact_sha}}],
            "predicate": {"buildDefinition": {
                "externalParameters": {"workflow": {
                    "repository": f"https://github.com/{repository}",
                    "path": workflow_path,
                    "ref": source_ref,
                }},
                "internalParameters": {"github": {"event_name": provenance.EXPECTED_EVENT}},
                "resolvedDependencies": [{
                    "uri": f"git+https://github.com/{repository}@{source_ref}",
                    "digest": {"gitCommit": CANDIDATE},
                }],
            }},
        },
        "signature": {"certificate": {
            "subjectAlternativeName": identity,
            "issuer": provenance.EXPECTED_ISSUER,
            "githubWorkflowTrigger": provenance.EXPECTED_EVENT,
            "githubWorkflowSHA": CANDIDATE,
            "githubWorkflowRepository": repository,
            "githubWorkflowRef": source_ref,
            "buildSignerURI": identity,
            "buildSignerDigest": CANDIDATE,
            "runnerEnvironment": "github-hosted",
            "sourceRepositoryURI": f"https://github.com/{repository}",
            "sourceRepositoryDigest": CANDIDATE,
            "sourceRepositoryRef": source_ref,
            "buildConfigURI": identity,
            "buildConfigDigest": CANDIDATE,
            "buildTrigger": provenance.EXPECTED_EVENT,
            "sourceRepositoryVisibilityAtSigning": "public",
        }},
        "verifiedTimestamps": [{"type": "Tlog", "timestamp": "2026-07-19T00:00:00Z"}],
    }}]
    if mutation is not None:
        mutation(document)
    return json.dumps(document).encode()


class ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="phase7-provenance-")
        self.root = Path(self.temporary.name)
        self.artifact = self.root / ARTIFACT_NAME
        self.artifact.write_bytes(b"native-artifact-bytes\n")
        self.bundle = self.root / f"{ARTIFACT_NAME}.sigstore.json"
        self.bundle.write_bytes(b'{"signed":"bundle"}\n')
        self.digest = sha256_bytes(self.artifact.read_bytes())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def runner(self, mutation=None, *, returncode=0):
        def run(arguments):
            self.assertIn("--repo", arguments)
            self.assertIn("--cert-identity", arguments)
            self.assertNotIn("--signer-workflow", arguments)
            self.assertIn("--source-ref", arguments)
            self.assertIn("--source-digest", arguments)
            self.assertIn("--signer-digest", arguments)
            self.assertIn("--deny-self-hosted-runners", arguments)
            return subprocess.CompletedProcess(
                arguments,
                returncode,
                verified_document(artifact_sha=self.digest, mutation=mutation),
                b"verification failed" if returncode else b"",
            )
        return run

    def verify(self, **changes):
        values = {
            "repository": provenance.EXPECTED_REPOSITORY,
            "workflow_path": provenance.EXPECTED_WORKFLOW_PATH,
            "source_ref": provenance.EXPECTED_SOURCE_REF,
            "candidate_sha": CANDIDATE,
            "workflow_sha": CANDIDATE,
            "artifact_name": ARTIFACT_NAME,
            "artifact_sha256": self.digest,
            "command_runner": self.runner(),
        }
        values.update(changes)
        return provenance.verify_signed_bundle(self.artifact, self.bundle, **values)

    def test_exact_identity_and_signed_bundle_verify(self) -> None:
        self.verify()

    def test_real_gh_parser_accepts_the_non_conflicting_exact_flag_set(self) -> None:
        self.bundle.write_bytes(b"{}\n")
        command = provenance.verification_command(
            self.artifact,
            self.bundle,
            repository=provenance.EXPECTED_REPOSITORY,
            workflow_path=provenance.EXPECTED_WORKFLOW_PATH,
            source_ref=provenance.EXPECTED_SOURCE_REF,
            candidate_sha=CANDIDATE,
            workflow_sha=CANDIDATE,
        )
        self.assertIn("--cert-identity", command)
        self.assertNotIn("--signer-workflow", command)
        self.assertFalse((ROOT / ".local").exists())
        result = provenance.default_command_runner(command)
        self.assertFalse((ROOT / ".local").exists())
        stderr = result.stderr.decode(errors="replace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error getting bundle version", stderr)
        self.assertNotIn("mutually exclusive", stderr.casefold())
        self.assertNotIn("cannot use --cert-identity with --signer-workflow", stderr.casefold())

    def test_candidate_subprocess_environment_is_minimal_and_blocks_injection_channels(self) -> None:
        source = {
            "PATH": "/usr/bin",
            "SYSTEMROOT": "C:\\Windows",
            "WINDIR": "C:\\Windows",
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            "COMSPEC": "C:\\Windows\\System32\\cmd.exe",
            "TEMP": "C:\\Temp",
            "TMP": "C:\\Temp",
            "TMPDIR": "/tmp",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "C.UTF-8",
            "LC_CTYPE": "UTF-8",
            "HOME": "/home/runner",
            "XDG_CACHE_HOME": "/home/runner/.cache",
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://token.invalid",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "oidc-secret",
            "ACTIONS_RUNTIME_TOKEN": "runtime-secret",
            "ACTIONS_CACHE_URL": "https://cache.invalid",
            "GITHUB_TOKEN": "github-secret",
            "GH_TOKEN": "gh-secret",
            "GITHUB_CUSTOM_CREDENTIAL": "custom-secret",
            "GITHUB_ENV": "/tmp/github-env",
            "GITHUB_PATH": "/tmp/github-path",
            "GITHUB_OUTPUT": "/tmp/github-output",
            "GITHUB_STEP_SUMMARY": "/tmp/github-summary",
            "PYTHONPATH": "/tmp/python-injection",
            "PYTHONHOME": "/tmp/python-home-injection",
            "HARNESS_V1_PLATFORM": "attacker-platform",
            "HARNESS_V1_UNAPPROVED": "attacker-value",
        }
        trusted_harness = {"HARNESS_V1_PLATFORM": "linux-x64"}
        scrubbed = minimal_subprocess_environment(
            source,
            trusted_harness=trusted_harness,
        )
        self.assertEqual(
            scrubbed,
            {
                "PATH": "/usr/bin",
                "SYSTEMROOT": "C:\\Windows",
                "WINDIR": "C:\\Windows",
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
                "COMSPEC": "C:\\Windows\\System32\\cmd.exe",
                "TEMP": "C:\\Temp",
                "TMP": "C:\\Temp",
                "TMPDIR": "/tmp",
                "LANG": "en_US.UTF-8",
                "LC_ALL": "C.UTF-8",
                "LC_CTYPE": "UTF-8",
                "HARNESS_V1_PLATFORM": "linux-x64",
            },
        )
        result = execution.invoke(
            [
                sys.executable,
                "-c",
                "import json,os; print(json.dumps(dict(os.environ), sort_keys=True))",
            ],
            self.root,
            trusted_harness,
            source_environment=source,
        )
        self.assertEqual(result.returncode, 0)
        child = json.loads(result.stdout)
        self.assertEqual(child["HARNESS_V1_PLATFORM"], "linux-x64")
        for name in (
            "ACTIONS_ID_TOKEN_REQUEST_URL",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
            "ACTIONS_RUNTIME_TOKEN",
            "ACTIONS_CACHE_URL",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_CUSTOM_CREDENTIAL",
            "GITHUB_ENV",
            "GITHUB_PATH",
            "GITHUB_OUTPUT",
            "GITHUB_STEP_SUMMARY",
            "PYTHONPATH",
            "PYTHONHOME",
            "HOME",
            "XDG_CACHE_HOME",
            "HARNESS_V1_UNAPPROVED",
        ):
            self.assertNotIn(name, child)

    def test_unapproved_trusted_harness_binding_is_rejected(self) -> None:
        with self.assertRaises(ReceiptError):
            minimal_subprocess_environment(
                {"PATH": "/usr/bin"},
                trusted_harness={"HARNESS_V1_UNAPPROVED": "value"},
            )

    def test_missing_attestation_and_checksum_only_fail_closed(self) -> None:
        self.bundle.unlink()
        with self.assertRaises(ReceiptError):
            self.verify()
        self.bundle.write_bytes(b'{"signed":"bundle"}\n')
        with self.assertRaises(ReceiptError):
            self.verify(command_runner=self.runner(returncode=1))

    def test_wrong_artifact_digest_repo_workflow_ref_or_sha_fail_closed(self) -> None:
        adversaries = (
            {"artifact_sha256": "0" * 64},
            {"repository": "attacker/repository-harness"},
            {"workflow_path": ".github/workflows/attacker.yml"},
            {"source_ref": "refs/heads/main"},
            {"candidate_sha": "2" * 40},
            {"workflow_sha": "2" * 40},
        )
        for changes in adversaries:
            with self.subTest(changes=changes), self.assertRaises(ReceiptError):
                self.verify(**changes)

    def test_signed_subject_certificate_event_and_transparency_substitution_fail_closed(self) -> None:
        mutations = (
            lambda value: value[0]["verificationResult"]["statement"]["subject"][0].update(name="substituted"),
            lambda value: value[0]["verificationResult"]["signature"]["certificate"].update(sourceRepositoryDigest="2" * 40),
            lambda value: value[0]["verificationResult"]["signature"]["certificate"].update(githubWorkflowTrigger="workflow_dispatch"),
            lambda value: value[0]["verificationResult"].update(verifiedTimestamps=[]),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ReceiptError):
                self.verify(command_runner=self.runner(mutation))

    def test_closed_record_rejects_credentials_and_authority_overclaim(self) -> None:
        record = provenance.verification_record(
            platform_name="linux-x64",
            target="x86_64-unknown-linux-gnu",
            runner="ubuntu-24.04",
            artifact_name=ARTIFACT_NAME,
            artifact_sha256=self.digest,
            bundle_name=f"{ARTIFACT_NAME}.sigstore.json",
            bundle_sha256=sha256_bytes(self.bundle.read_bytes()),
            candidate_sha=CANDIDATE,
            workflow_sha=CANDIDATE,
        )
        credential = deepcopy(record)
        credential["github_token"] = "secret"
        with self.assertRaises(ReceiptError):
            provenance.validate_verification_record(credential)
        overclaim = deepcopy(record)
        overclaim["authority"]["production"] = True
        with self.assertRaises(ReceiptError):
            provenance.validate_verification_record(overclaim)


if __name__ == "__main__":
    unittest.main(verbosity=2)
