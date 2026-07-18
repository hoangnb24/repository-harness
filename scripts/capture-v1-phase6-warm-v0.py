#!/usr/bin/env python3
"""Capture an owner-authorized warm V0 fixture without reading rows publicly.

Raw files and the standalone SQLite backup are written only beneath a new,
external private directory. Standard output is a fixed allowlist summary; it
never contains source paths, SQLite rows, command output, or raw bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
IDENTITY = re.compile(r"^[a-z][a-z0-9-]{2,127}$")
REPOSITORY = re.compile(r"^https://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]+[.]git$")
ALLOWED_CLI_PATHS = {"scripts/bin/harness-cli", "scripts/bin/harness-cli.exe"}
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", None)


class CaptureError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise CaptureError(message)


def canonical_bytes(document: dict[str, Any], omitted: str | None = None) -> bytes:
    content = dict(document)
    if omitted is not None:
        content.pop(omitted, None)
    return json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while chunk := os.read(fd, 1024 * 1024):
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest()


def inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        fail(f"non-canonical capture path: {value}")
    return path


def git(source: Path, *arguments: str) -> str:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    }
    result = subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        fail("source Git identity could not be verified")
    return result.stdout.strip()


def open_beneath(root_fd: int, value: str) -> int:
    if O_NOFOLLOW is None:
        fail("capture platform lacks mandatory O_NOFOLLOW support")
    path = relative_path(value)
    current = os.dup(root_fd)
    try:
        for index, component in enumerate(path.parts):
            final = index == len(path.parts) - 1
            flags = os.O_RDONLY | O_NOFOLLOW
            if not final:
                flags |= getattr(os, "O_DIRECTORY", 0)
            next_fd = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = next_fd
        info = os.fstat(current)
        if not stat.S_ISREG(info.st_mode):
            fail(f"capture input is not a regular file: {value}")
        return current
    except Exception:
        os.close(current)
        raise


def directory_token(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns)


def member_token(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def stat_at(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def open_directory_at(parent_fd: int, name: str, label: str) -> int | None:
    if O_NOFOLLOW is None:
        fail("capture platform lacks mandatory O_NOFOLLOW support")
    before = stat_at(parent_fd, name)
    if before is None:
        return None
    if not stat.S_ISDIR(before.st_mode):
        fail(f"{label} is not a real directory")
    try:
        descriptor = os.open(
            name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as error:
        fail(f"{label} could not be opened safely: {error.strerror}")
    after = os.fstat(descriptor)
    if after.st_dev != before.st_dev or after.st_ino != before.st_ino:
        os.close(descriptor)
        fail(f"{label} changed while it was opened")
    return descriptor


def scan_changesets(
    descriptor: int,
    prefix: str,
    records: list[tuple[str, str]],
    members: dict[str, tuple[int, int, int, int, int, int]],
    directories: dict[str, tuple[int, int, int, int]],
) -> None:
    try:
        names = sorted(os.listdir(descriptor))
    except OSError as error:
        fail(f"recognized changeset root could not be listed: {error.strerror}")
    for name in names:
        if name in {"", ".", ".."} or "/" in name:
            fail("recognized changeset root contains an unsupported member")
        path = f"{prefix}/{name}"
        info = stat_at(descriptor, name)
        if info is None:
            fail("recognized changeset root changed while it was scanned")
        if stat.S_ISDIR(info.st_mode):
            child = open_directory_at(
                descriptor, name, "recognized changeset directory"
            )
            if child is None:
                fail("recognized changeset directory disappeared")
            try:
                directories[path] = directory_token(os.fstat(child))
                scan_changesets(child, path, records, members, directories)
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(info.st_mode) or not name.endswith(".jsonl"):
            fail("recognized changeset root contains an unsupported member")
        records.append(("changeset", path))
        members[path] = member_token(info)


def discover(
    root_fd: int, cli_path: str
) -> tuple[
    list[tuple[str, str]],
    dict[str, tuple[int, int, int, int, int, int]],
    dict[str, tuple[int, int, int, int]],
]:
    records: list[tuple[str, str]] = []
    members: dict[str, tuple[int, int, int, int, int, int]] = {}
    directories = {"": directory_token(os.fstat(root_fd))}

    for category, value, optional in [
        ("database", "harness.db", False),
        ("wal", "harness.db-wal", True),
        ("shm", "harness.db-shm", True),
        ("v0-cli", cli_path, False),
    ]:
        path = relative_path(value)
        parent = os.dup(root_fd)
        try:
            for component in path.parts[:-1]:
                child = open_directory_at(parent, component, f"capture parent {value}")
                if child is None:
                    if optional:
                        parent = -1
                        break
                    fail(f"required capture parent is missing: {value}")
                os.close(parent)
                parent = child
            if parent == -1:
                continue
            info = stat_at(parent, path.parts[-1])
            if info is None:
                if optional:
                    continue
                fail(f"required capture member is missing: {value}")
            if not stat.S_ISREG(info.st_mode):
                fail(f"capture input is not a regular file: {value}")
            records.append((category, value))
            members[value] = member_token(info)
        finally:
            if parent >= 0:
                os.close(parent)

    harness = open_directory_at(root_fd, ".harness", "recognized harness root")
    if harness is not None:
        try:
            directories[".harness"] = directory_token(os.fstat(harness))
            provenance = stat_at(harness, "v0-provenance.json")
            if provenance is not None:
                if not stat.S_ISREG(provenance.st_mode):
                    fail("recognized provenance is not a regular file")
                value = ".harness/v0-provenance.json"
                records.append(("provenance", value))
                members[value] = member_token(provenance)
            changesets = open_directory_at(
                harness, "changesets", "recognized changeset root"
            )
            if changesets is not None:
                try:
                    directories[".harness/changesets"] = directory_token(
                        os.fstat(changesets)
                    )
                    scan_changesets(
                        changesets,
                        ".harness/changesets",
                        records,
                        members,
                        directories,
                    )
                finally:
                    os.close(changesets)
        finally:
            os.close(harness)
    records.sort(key=lambda item: (item[0], item[1]))
    return records, members, directories


def require_same_namespace(
    expected: tuple[
        list[tuple[str, str]],
        dict[str, tuple[int, int, int, int, int, int]],
        dict[str, tuple[int, int, int, int]],
    ],
    actual: tuple[
        list[tuple[str, str]],
        dict[str, tuple[int, int, int, int, int, int]],
        dict[str, tuple[int, int, int, int]],
    ],
    stage: str,
) -> None:
    if actual[0] != expected[0] or actual[1] != expected[1]:
        fail(f"live source namespace changed {stage}")
    if actual[2] != expected[2]:
        fail(f"live source directory token changed {stage}")


def deterministic_test_hook() -> None:
    ready_value = os.environ.get("HARNESS_PHASE6_CAPTURE_TEST_READY_FD")
    continue_value = os.environ.get("HARNESS_PHASE6_CAPTURE_TEST_CONTINUE_FD")
    if ready_value is None and continue_value is None:
        return
    if ready_value is None or continue_value is None:
        fail("capture test hook requires both inherited descriptors")
    try:
        ready_fd = int(ready_value)
        continue_fd = int(continue_value)
        if ready_fd < 3 or continue_fd < 3:
            raise ValueError
        os.write(ready_fd, b"1")
        if os.read(continue_fd, 1) != b"1":
            fail("capture test hook continuation was not acknowledged")
    except (OSError, ValueError) as error:
        raise CaptureError("capture test hook descriptors are invalid") from error


def copy_from_fd(fd: int, destination: Path) -> None:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        while chunk := os.read(fd, 1024 * 1024):
            view = memoryview(chunk)
            while view:
                written = os.write(output, view)
                view = view[written:]
        os.fsync(output)
        os.lseek(fd, 0, os.SEEK_SET)
    finally:
        os.close(output)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--destination-root", required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--pilot-id", required=True)
    parser.add_argument("--canonical-repository", required=True)
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--cli-path", default="scripts/bin/harness-cli")
    parser.add_argument("--writers-quiesced", action="store_true")
    return parser.parse_args()


def capture(arguments: argparse.Namespace) -> dict[str, Any]:
    if O_NOFOLLOW is None:
        fail("capture platform lacks mandatory O_NOFOLLOW support")
    source_input = Path(arguments.source_root)
    destination = Path(arguments.destination_root)
    if not source_input.is_absolute() or not destination.is_absolute():
        fail("source and destination roots must be absolute")
    if source_input.is_symlink():
        fail("source root must be a real directory")
    source = source_input.resolve(strict=True)
    destination = destination.parent.resolve(strict=True) / destination.name
    if source.is_symlink() or not source.is_dir():
        fail("source root must be a real directory")
    if destination.exists():
        fail("private destination must not already exist")
    if inside(destination, ROOT) or inside(destination, source) or inside(source, destination):
        fail("private destination must be external to source and candidate repository")
    if not arguments.writers_quiesced:
        fail("--writers-quiesced is required before capture")
    if not COMMIT.fullmatch(arguments.expected_revision):
        fail("expected revision must be a full Git commit")
    if not IDENTITY.fullmatch(arguments.pilot_id) or not IDENTITY.fullmatch(
        arguments.capture_id
    ):
        fail("pilot and capture IDs must be canonical lower kebab-case")
    if not UTC.fullmatch(arguments.captured_at):
        fail("captured-at must be strict RFC 3339 UTC seconds")
    if not REPOSITORY.fullmatch(arguments.canonical_repository):
        fail("canonical repository must be an HTTPS .git identity")
    if arguments.cli_path not in ALLOWED_CLI_PATHS:
        fail("CLI path is outside the recognized V0 allowlist")

    revision = git(source, "rev-parse", "HEAD^{commit}")
    if revision != arguments.expected_revision:
        fail("live tracked revision differs from the authorized starting revision")
    if git(source, "status", "--porcelain=v1", "--untracked-files=no"):
        fail("live tracked files must be clean before warm capture")
    tree = git(source, "rev-parse", "HEAD^{tree}")

    destination.mkdir(mode=0o700, parents=True)
    raw = destination / "raw"
    recovery = destination / "recovery"
    raw.mkdir(mode=0o700)
    recovery.mkdir(mode=0o700)

    root_fd = os.open(
        source,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | O_NOFOLLOW,
    )
    root_identity = os.fstat(root_fd)
    initial_namespace = discover(root_fd, arguments.cli_path)
    handles: list[tuple[str, str, int, os.stat_result, str]] = []
    artifacts: list[dict[str, Any]] = []
    try:
        for category, value in initial_namespace[0]:
            fd = open_beneath(root_fd, value)
            before = os.fstat(fd)
            expected_token = initial_namespace[1][value]
            if member_token(before) != expected_token:
                fail(f"live source changed while opening capture member: {value}")
            before_sha256 = sha256_fd(fd)
            handles.append((category, value, fd, before, before_sha256))

        require_same_namespace(
            initial_namespace,
            discover(root_fd, arguments.cli_path),
            "during descriptor acquisition",
        )
        deterministic_test_hook()

        for category, value, fd, before, before_sha256 in handles:
            target = raw / value
            copy_from_fd(fd, target)
            if sha256_file(target) != before_sha256:
                fail(f"private copy digest mismatch for {value}")
            artifacts.append(
                {
                    "category": category,
                    "path": value,
                    "bytes": before.st_size,
                    "sha256": before_sha256,
                }
            )

        for _, value, _, _, _ in handles:
            source_path = raw / value
            recovery_path = recovery / value
            recovery_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(source_path, recovery_path)
            os.chmod(recovery_path, 0o600)

        recovery_database = recovery / "harness.db"
        standalone = destination / "standalone-backup.sqlite"
        source_connection = sqlite3.connect(str(recovery_database))
        backup_connection = sqlite3.connect(str(standalone))
        try:
            source_connection.backup(backup_connection)
            backup_connection.commit()
        except sqlite3.Error as error:
            fail(f"private staged SQLite backup failed: {error.__class__.__name__}")
        finally:
            backup_connection.close()
            source_connection.close()
        os.chmod(standalone, 0o600)

        require_same_namespace(
            initial_namespace,
            discover(root_fd, arguments.cli_path),
            "during capture",
        )
        for _, value, fd, before, before_sha256 in handles:
            after = os.fstat(fd)
            if (
                after.st_dev != before.st_dev
                or after.st_ino != before.st_ino
                or after.st_size != before.st_size
                or sha256_fd(fd) != before_sha256
            ):
                fail(f"live source changed during capture: {value}")
            reopened = open_beneath(root_fd, value)
            try:
                current = os.fstat(reopened)
                if (
                    current.st_dev != before.st_dev
                    or current.st_ino != before.st_ino
                    or current.st_size != before.st_size
                    or sha256_fd(reopened) != before_sha256
                ):
                    fail(f"live source namespace changed during capture: {value}")
            finally:
                os.close(reopened)
        current_root = os.stat(source, follow_symlinks=False)
        if (
            current_root.st_dev != root_identity.st_dev
            or current_root.st_ino != root_identity.st_ino
        ):
            fail("live source root changed during capture")

        manifest: dict[str, Any] = {
            "schema": "repository-harness-phase6-warm-v0-capture/v1",
            "capture_id": arguments.capture_id,
            "pilot_id": arguments.pilot_id,
            "canonical_repository": arguments.canonical_repository,
            "starting_revision": revision,
            "starting_tree": tree,
            "captured_at": arguments.captured_at,
            "coordination": {
                "writers_quiesced": True,
                "copy_method": "retained-read-handles-pre-copy-post",
                "recovery_method": "private-staged-db-wal-online-backup",
            },
            "artifacts": sorted(artifacts, key=lambda item: (item["category"], item["path"])),
            "standalone_backup": {
                "path": "standalone-backup.sqlite",
                "bytes": standalone.stat().st_size,
                "sha256": sha256_file(standalone),
            },
            "source_unchanged": True,
            "capture_sha256": "",
        }
        manifest["capture_sha256"] = hashlib.sha256(
            canonical_bytes(manifest, "capture_sha256")
        ).hexdigest()
        manifest_path = destination / "public-capture.json"
        descriptor = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            payload = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    fail("short write while creating public capture manifest")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return {
            "schema": "repository-harness-phase6-warm-v0-capture-summary/v1",
            "result": "captured",
            "capture_id": arguments.capture_id,
            "artifact_categories": sorted({item["category"] for item in artifacts}),
            "public_manifest_sha256": sha256_file(manifest_path),
            "source_unchanged": True,
        }
    finally:
        for _, _, fd, _, _ in handles:
            os.close(fd)
        os.close(root_fd)


def main() -> int:
    try:
        summary = capture(parse_arguments())
    except (CaptureError, OSError) as error:
        print(f"warm V0 capture failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
