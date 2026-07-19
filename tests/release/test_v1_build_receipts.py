#!/usr/bin/env python3
"""Focused capture-boundary and read-only build-receipt adversaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import capture_v1_build_receipt as capture  # noqa: E402
import verify_v1_build_receipts as verifier  # noqa: E402
from v1_artifact_provenance import (  # noqa: E402
    EXPECTED_EVENT,
    EXPECTED_ISSUER,
    EXPECTED_REPOSITORY,
    EXPECTED_SOURCE_REF,
    EXPECTED_WORKFLOW_PATH,
    PROVENANCE_RECORD_NAME,
    canonical_record_bytes,
    expected_certificate_identity,
    verification_record,
)
from v1_build_receipt_common import (  # noqa: E402
    CARGO_LOCK_PATH,
    COMMAND_BINDING_PATH,
    COMMAND_GRAMMAR_PATH,
    PLATFORMS,
    RECEIPT_NAME,
    WORKFLOW_PATH,
    ReceiptError,
    canonical_json_bytes,
    exact_core_help_bytes,
    load_json,
    sha256_bytes,
    sha256_file,
)


def git_text(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def git_bytes(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def current_expected() -> tuple[dict, dict, bytes]:
    candidate = git_text("rev-parse", "HEAD")
    workflow_revision = candidate
    tree = git_text("rev-parse", "HEAD^{tree}")
    identity = {
        "source_commit": candidate,
        "source_tree": tree,
        "cargo_lock": {"path": CARGO_LOCK_PATH, "sha256": sha256_file(ROOT / CARGO_LOCK_PATH)},
        "command_implementation_binding": {
            "path": COMMAND_BINDING_PATH,
            "sha256": sha256_file(ROOT / COMMAND_BINDING_PATH),
        },
    }
    execution_workflow = {
        "path": WORKFLOW_PATH,
        "revision": workflow_revision,
        "sha256": sha256_bytes(git_bytes("show", f"{workflow_revision}:{WORKFLOW_PATH}")),
    }
    return identity, execution_workflow, exact_core_help_bytes(load_json(ROOT / COMMAND_GRAMMAR_PATH))


def fake_gh(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    artifact = Path(arguments[3])
    value = lambda flag: arguments[arguments.index(flag) + 1]
    repository = value("--repo")
    source_ref = value("--source-ref")
    candidate = value("--source-digest")
    workflow_sha = value("--signer-digest")
    artifact_sha = sha256_file(artifact)
    identity = expected_certificate_identity(repository, EXPECTED_WORKFLOW_PATH, source_ref)
    document = [{
        "verificationResult": {
            "statement": {
                "predicateType": "https://slsa.dev/provenance/v1",
                "subject": [{"name": artifact.name, "digest": {"sha256": artifact_sha}}],
                "predicate": {
                    "buildDefinition": {
                        "externalParameters": {"workflow": {
                            "repository": f"https://github.com/{repository}",
                            "path": EXPECTED_WORKFLOW_PATH,
                            "ref": source_ref,
                        }},
                        "internalParameters": {"github": {"event_name": EXPECTED_EVENT}},
                        "resolvedDependencies": [{
                            "uri": f"git+https://github.com/{repository}@{source_ref}",
                            "digest": {"gitCommit": candidate},
                        }],
                    }
                },
            },
            "signature": {"certificate": {
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
                "sourceRepositoryDigest": candidate,
                "sourceRepositoryRef": source_ref,
                "buildConfigURI": identity,
                "buildConfigDigest": workflow_sha,
                "buildTrigger": EXPECTED_EVENT,
                "sourceRepositoryVisibilityAtSigning": "public",
            }},
            "verifiedTimestamps": [{"type": "Tlog", "timestamp": "2026-07-19T00:00:00Z"}],
        }
    }]
    return subprocess.CompletedProcess(arguments, 0, json.dumps(document).encode(), b"")


class ReceiptFactory:
    def __init__(self, root: Path):
        self.root = root
        self.expected, self.execution_workflow, self.help_bytes = current_expected()

    def write(self, directory: Path, platform_name: str) -> dict:
        directory.mkdir()
        target, runner, artifact_name = PLATFORMS[platform_name]
        artifact_bytes = f"non-executable-test-artifact:{platform_name}\n".encode("ascii")
        artifact_sha = sha256_bytes(artifact_bytes)
        checksum_bytes = f"{artifact_sha}  {artifact_name}\n".encode("ascii")
        help_name = f"{artifact_name}.help.json"
        bundle_name = f"{artifact_name}.sigstore.json"
        bundle_bytes = b'{"synthetic":"signed-bundle-fixture"}\n'
        record = verification_record(
            platform_name=platform_name,
            target=target,
            runner=runner,
            artifact_name=artifact_name,
            artifact_sha256=artifact_sha,
            bundle_name=bundle_name,
            bundle_sha256=sha256_bytes(bundle_bytes),
            candidate_sha=self.expected["source_commit"],
            workflow_sha=self.execution_workflow["revision"],
        )
        record_bytes = canonical_record_bytes(record)
        document = capture.build_receipt_document(
            candidate_identity=self.expected,
            execution_workflow_identity=self.execution_workflow,
            platform_name=platform_name,
            target=target,
            runner=runner,
            artifact_name=artifact_name,
            artifact_bytes=artifact_bytes,
            checksum_bytes=checksum_bytes,
            help_name=help_name,
            help_bytes=self.help_bytes,
            bundle_name=bundle_name,
            bundle_bytes=bundle_bytes,
            verification_name=PROVENANCE_RECORD_NAME,
            verification_bytes=record_bytes,
            provenance_record=record,
        )
        (directory / artifact_name).write_bytes(artifact_bytes)
        (directory / f"{artifact_name}.sha256").write_bytes(checksum_bytes)
        (directory / help_name).write_bytes(self.help_bytes)
        (directory / bundle_name).write_bytes(bundle_bytes)
        (directory / PROVENANCE_RECORD_NAME).write_bytes(record_bytes)
        (directory / RECEIPT_NAME).write_bytes(canonical_json_bytes(document))
        return document

    def single(self, platform_name: str = "macos-arm64") -> tuple[Path, dict]:
        directory = self.root / f"single-{platform_name}"
        return directory, self.write(directory, platform_name)

    def five(self) -> Path:
        collection = self.root / "collection"
        collection.mkdir()
        for platform_name in PLATFORMS:
            self.write(
                collection / f"{verifier.ARTIFACT_DIRECTORY_PREFIX}{platform_name}",
                platform_name,
            )
        return collection


class CaptureBoundaryTests(unittest.TestCase):
    def test_entrypoints_cannot_create_repository_bytecode_or_invalidate_clean_status(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=ROOT.parent,
            prefix="phase7-capture-import-",
        ) as temporary:
            repository = Path(temporary)
            scripts = repository / "scripts"
            scripts.mkdir()
            for name in (
                "capture_v1_build_receipt.py",
                "finalize_v1_build_receipt.py",
                "v1_artifact_provenance.py",
                "v1_build_receipt_common.py",
            ):
                shutil.copyfile(ROOT / "scripts" / name, scripts / name)

            def repository_git(*arguments: str) -> bytes:
                return subprocess.check_output(
                    ["git", *arguments],
                    cwd=repository,
                    stderr=subprocess.DEVNULL,
                )

            subprocess.check_call(
                ["git", "init", "-q"],
                cwd=repository,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            repository_git("config", "user.name", "Phase 7 Test")
            repository_git("config", "user.email", "phase7-test@example.invalid")
            repository_git("add", "scripts")
            repository_git("commit", "-q", "-m", "capture import fixture")
            candidate = repository_git("rev-parse", "HEAD").decode("ascii").strip()

            def bytecode_paths() -> set[Path]:
                return {
                    path.relative_to(repository)
                    for path in scripts.rglob("*")
                    if path.name == "__pycache__" or path.suffix == ".pyc"
                }

            self.assertEqual(bytecode_paths(), set(), "fixture must start without repository bytecode")
            self.assertEqual(
                repository_git("status", "--porcelain=v1", "--untracked-files=all"),
                b"",
            )
            environment = os.environ.copy()
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            environment.pop("PYTHONPYCACHEPREFIX", None)
            capture_result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "pycache_prefix=",
                    str(scripts / "capture_v1_build_receipt.py"),
                    "--candidate",
                    candidate,
                    "--workflow-revision",
                    candidate,
                    "--platform",
                    "regression-probe",
                    "--target",
                    "regression-probe",
                    "--runner",
                    "regression-probe",
                    "--output",
                    str(repository.parent / "never-created-receipt"),
                ],
                cwd=repository,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            capture_error = capture_result.stderr.decode(errors="replace")
            self.assertEqual(capture_result.returncode, 1, capture_error)
            self.assertIn("unsupported platform: regression-probe", capture_error)
            self.assertNotIn("worktree changes", capture_error)
            self.assertEqual(bytecode_paths(), set())
            self.assertEqual(
                repository_git("status", "--porcelain=v1", "--untracked-files=all"),
                b"",
            )

            finalizer_result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "pycache_prefix=",
                    str(scripts / "finalize_v1_build_receipt.py"),
                ],
                cwd=repository,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            self.assertEqual(finalizer_result.returncode, 2)
            self.assertEqual(bytecode_paths(), set())
            self.assertEqual(
                repository_git("status", "--porcelain=v1", "--untracked-files=all"),
                b"",
            )

    def test_rejects_non_exact_candidate_before_git(self) -> None:
        with self.assertRaisesRegex(ReceiptError, "exactly 40"):
            capture.validate_candidate("main")
        with self.assertRaisesRegex(ReceiptError, "workflow revision must be exactly 40"):
            capture.committed_execution_workflow_identity("main")

    def test_accepts_only_native_exact_tuple(self) -> None:
        result = capture.validate_tuple(
            "macos-arm64",
            "aarch64-apple-darwin",
            "macos-15",
            system="Darwin",
            machine="arm64",
            rust_target="aarch64-apple-darwin",
        )
        self.assertEqual(result, PLATFORMS["macos-arm64"])
        for changed in (
            {"runner": "macos-15-intel"},
            {"machine": "x86_64"},
            {"rust_target": "x86_64-apple-darwin"},
        ):
            values = {
                "platform_name": "macos-arm64",
                "target": "aarch64-apple-darwin",
                "runner": "macos-15",
                "system": "Darwin",
                "machine": "arm64",
                "rust_target": "aarch64-apple-darwin",
            }
            values.update(changed)
            with self.assertRaises(ReceiptError):
                capture.validate_tuple(**values)

    def test_output_must_be_new_external_non_symlink_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT.parent, prefix="phase7-output-boundary-") as temporary:
            parent = Path(temporary)
            accepted = parent / "new-receipt"
            self.assertEqual(capture.validate_new_output_path(str(accepted)), accepted.resolve())

            existing = parent / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(ReceiptError, "must not already exist"):
                capture.validate_new_output_path(str(existing))

            with self.assertRaisesRegex(ReceiptError, "traversal"):
                capture.validate_new_output_path(str(parent / "nested" / ".." / "escape"))

            symlink_parent = parent / "linked"
            symlink_parent.symlink_to(parent, target_is_directory=True)
            with self.assertRaisesRegex(ReceiptError, "symlink"):
                capture.validate_new_output_path(str(symlink_parent / "receipt"))

        with self.assertRaisesRegex(ReceiptError, "outside the repository"):
            capture.validate_new_output_path(str(ROOT / "target" / "new-build-receipt"))


class VerifierAdversaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT.parent, prefix="phase7-receipt-test-")
        self.root = Path(self.temporary.name)
        self.factory = ReceiptFactory(self.root)
        self.candidate = self.factory.expected["source_commit"]
        self.workflow_revision = self.factory.execution_workflow["revision"]
        self.expected = (self.factory.expected, self.factory.execution_workflow, self.factory.help_bytes)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def rewrite(self, directory: Path, document: dict) -> None:
        (directory / RECEIPT_NAME).write_bytes(canonical_json_bytes(document))

    def assert_rejected(self, directory: Path, mutate) -> None:
        document = load_json(directory / RECEIPT_NAME)
        mutate(document, directory)
        self.rewrite(directory, document)
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

    def test_valid_single_and_exact_five_are_read_without_execution(self) -> None:
        self.assertEqual(self.candidate, self.workflow_revision)
        single, _ = self.factory.single()
        self.assertEqual(
            verifier.verify_collection(single, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh),
            ["macos-arm64"],
        )
        collection = self.factory.five()
        self.assertEqual(
            verifier.verify_collection(collection, self.candidate, self.workflow_revision, True, expected=self.expected, command_runner=fake_gh),
            list(PLATFORMS),
        )

    def test_missing_and_duplicate_platforms_are_rejected(self) -> None:
        collection = self.factory.five()
        shutil.rmtree(collection / f"{verifier.ARTIFACT_DIRECTORY_PREFIX}linux-arm64")
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(collection, self.candidate, self.workflow_revision, True, expected=self.expected, command_runner=fake_gh)

        collection = self.root / "duplicate-collection"
        collection.mkdir()
        for platform_name in PLATFORMS:
            directory = collection / f"{verifier.ARTIFACT_DIRECTORY_PREFIX}{platform_name}"
            document = self.factory.write(directory, platform_name)
            if platform_name == "macos-x64":
                document["environment"] = {
                    "platform": "macos-arm64",
                    "target": "aarch64-apple-darwin",
                    "runner": "macos-15",
                }
                self.rewrite(directory, document)
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(collection, self.candidate, self.workflow_revision, True, expected=self.expected, command_runner=fake_gh)

    def test_candidate_workflow_and_input_drift_are_rejected(self) -> None:
        for name, mutation in (
            ("candidate", lambda document: document["candidate"].update(source_commit="0" * 40)),
            ("workflow", lambda document: document["execution_workflow"].update(sha256="0" * 64)),
            ("lock", lambda document: document["candidate"]["cargo_lock"].update(sha256="0" * 64)),
            ("binding", lambda document: document["candidate"]["command_implementation_binding"].update(sha256="0" * 64)),
        ):
            directory = self.root / f"drift-{name}"
            document = self.factory.write(directory, "linux-x64")
            mutation(document)
            self.rewrite(directory, document)
            with self.assertRaises(ReceiptError, msg=name):
                verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

    def test_byte_checksum_and_help_substitution_are_rejected(self) -> None:
        for field, replacement in (
            ("artifact", b"substituted artifact\n"),
            ("checksum", b"0" * 64 + b"  substituted\n"),
            ("help_output", b'{"top_level":[]}\n'),
        ):
            directory, document = self.factory.single({"artifact": "macos-x64", "checksum": "linux-x64", "help_output": "linux-arm64"}[field])
            (directory / document["files"][field]["path"]).write_bytes(replacement)
            with self.assertRaises(ReceiptError, msg=field):
                verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

    def test_unsupported_claim_extra_file_and_traversal_are_rejected(self) -> None:
        directory, _ = self.factory.single("windows-x64")
        self.assert_rejected(directory, lambda document, _: document["results"].update(installer="passed"))

        directory, _ = self.factory.single("macos-arm64")
        self.assert_rejected(directory, lambda document, _: document["authority"].update(production=True))

        directory, _ = self.factory.single("macos-x64")
        (directory / "extra.txt").write_text("extra\n", encoding="utf-8")
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

        directory, _ = self.factory.single("linux-x64")
        self.assert_rejected(directory, lambda document, _: document["files"]["artifact"].update(path="../artifact"))

    def test_missing_or_mismatched_attestation_evidence_is_rejected(self) -> None:
        directory, document = self.factory.single("linux-x64")
        (directory / document["files"]["attestation_bundle"]["path"]).unlink()
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

        directory, document = self.factory.single("linux-arm64")
        (directory / document["files"]["attestation_bundle"]["path"]).write_bytes(b"substituted bundle\n")
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

    def test_duplicate_keys_command_fields_and_symlinks_are_rejected_without_execution(self) -> None:
        directory, _ = self.factory.single("linux-arm64")
        receipt = directory / RECEIPT_NAME
        payload = receipt.read_bytes()
        receipt.write_bytes(payload.replace(b'{"authority":', b'{"schema":"duplicate","authority":', 1))
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)

        directory, _ = self.factory.single("windows-x64")
        marker = self.root / "receipt-command-ran"
        self.assert_rejected(
            directory,
            lambda document, _: document["results"].update(command=f"touch {marker}"),
        )
        self.assertFalse(marker.exists())

        directory, document = self.factory.single("macos-x64")
        artifact = directory / document["files"]["artifact"]["path"]
        artifact.unlink()
        artifact.symlink_to(directory / document["files"]["help_output"]["path"])
        with self.assertRaises(ReceiptError):
            verifier.verify_collection(directory, self.candidate, self.workflow_revision, False, expected=self.expected, command_runner=fake_gh)


if __name__ == "__main__":
    unittest.main(verbosity=2)
