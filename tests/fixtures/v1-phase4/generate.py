#!/usr/bin/env python3
"""Generate immutable schema 1..=13 and WAL-only Phase 4 fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCHEMAS = ROOT / "release/contracts/v1/v0/schemas"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def apply_schema(database: Path, maximum: int) -> None:
    connection = sqlite3.connect(database)
    for version in range(1, maximum + 1):
        sql = (SCHEMAS / f"{version:03d}-{schema_name(version)}.sql").read_text()
        connection.executescript(sql)
    connection.commit()
    connection.close()


def schema_name(version: int) -> str:
    names = [
        "init",
        "story-verify",
        "tool-registry",
        "intervention",
        "tool-extensions",
        "changeset-applied",
        "story-dependencies",
        "story-hierarchy",
        "improvement-identity",
        "story-backlog-links",
        "legacy-evidence-snapshots",
        "review-finding-closure",
        "changeset-content-sha",
    ]
    return names[version - 1]


def common_files(directory: Path, version: int) -> None:
    (directory / "AGENTS.md").write_text(f"# Fixture schema {version}\n", encoding="utf-8")
    changesets = directory / ".harness/changesets"
    changesets.mkdir(parents=True)
    changeset = (
        '{"op":"changeset.header","version":1,"run_id":"fixture-schema-',
        f'{version}","base_schema_version":{version}}}\n',
        '{"op":"story.add","version":2,"id":"US-FIXTURE","payload":{}}\n',
    )
    (changesets / "fixture.changeset.jsonl").write_text("".join(changeset), encoding="utf-8")


def generate_schemas() -> None:
    for version in range(1, 14):
        directory = HERE / f"schema-{version:02d}"
        reset(directory)
        apply_schema(directory / "harness.db", version)
        common_files(directory, version)
        if version == 13:
            (directory / ".harness/v0-provenance.json").write_text(
                '{"installer":"harness-cli","schema":13}\n', encoding="utf-8"
            )
            (directory / ".harness/foreign-tool.bin").write_bytes(b"foreign-unowned\x00bytes\n")


def generate_wal_only() -> None:
    base = HERE / "wal-base.tmp"
    if base.exists():
        base.unlink()
    apply_schema(base, 13)
    writer = sqlite3.connect(base)
    writer.execute("PRAGMA journal_mode=WAL")
    reader = sqlite3.connect(base)
    reader.execute("BEGIN")
    reader.execute("SELECT COUNT(*) FROM story").fetchone()
    writer.execute(
        "INSERT INTO story(id,title,risk_lane,status) VALUES(?,?,?,?)",
        ("US-WAL", "wal-only-committed-row", "high_risk", "in_progress"),
    )
    writer.commit()
    directory = HERE / "wal-only-schema-13"
    reset(directory)
    shutil.copyfile(base, directory / "harness.db")
    shutil.copyfile(Path(str(base) + "-wal"), directory / "harness.db-wal")
    shutil.copyfile(Path(str(base) + "-shm"), directory / "harness.db-shm")
    common_files(directory, 13)
    writer.close()
    reader.close()
    for suffix in ("", "-wal", "-shm"):
        Path(str(base) + suffix).unlink(missing_ok=True)


def inventory() -> None:
    entries = []
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and path.name not in {"inventory.json", "generate.py", "README.md"}:
            entries.append(
                {
                    "path": path.relative_to(HERE).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    (HERE / "inventory.json").write_text(
        json.dumps(
            {"schema": "repository-harness-v0-fixture-inventory/v1", "files": entries},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    generate_schemas()
    generate_wal_only()
    inventory()
