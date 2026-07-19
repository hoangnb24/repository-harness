#!/usr/bin/env python3
"""Materialize signed test-fixture release input outside a target repository."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent


def canonical(document: object) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if not output.is_absolute() or output.exists() or not output.parent.is_dir():
        parser.error("--output must be a new absolute directory with an existing parent")
    output.mkdir(mode=0o700)
    release = output / "release"
    source = release / "source" / "docs" / "templates"
    source.mkdir(parents=True)
    positive = ROOT / "tests/fixtures/v1-phase1/positive"
    phase2 = ROOT / "tests/fixtures/v1-phase2"
    members = {
        phase2 / "current-core-payload-index.json": release / "payload-index.json",
        phase2 / "current-core-payload-index.signatures.json": release / "payload-index.signatures.json",
        positive / "core-trust-bundle.json": release / "trust-bundle.json",
        positive / "core-trust-bundle.signatures.json": release / "trust-bundle.signatures.json",
        ROOT / "release/contracts/v1/path-dispositions.json": release / "path-ledger.json",
        ROOT / "docs/templates/decision.md": source / "decision.md",
        ROOT / "docs/templates/story.md": source / "story.md",
    }
    for source_path, destination in members.items():
        shutil.copyfile(source_path, destination)
    anchors = json.loads((positive / "test-bootstrap-anchors.json").read_text(encoding="utf-8"))["core"]
    ledger = json.loads((release / "path-ledger.json").read_text(encoding="utf-8"))
    trust = {
        "schema": "repository-harness-external-trust-input/v1",
        "trust_policy": "test-fixtures",
        "path_ledger_sha256": hashlib.sha256(canonical(ledger).rstrip(b"\n")).hexdigest(),
        "freshness": {"mode": "first-install-minimum-sequence", "sequence": 44},
        "trusted_root": {
            "trust_domain": anchors["trust_domain"],
            "sequence": 1,
            "bundle_sha256": anchors["exact_bundle_digest"],
            "threshold": anchors["root_threshold"],
            "keys": [
                {
                    "key_id": key["key_id"],
                    "public_key_base64": key["public_key_base64"],
                    "test_fixture": True,
                }
                for key in anchors["root_keys"]
            ],
            "revoked_key_ids": [],
        },
    }
    (output / "trust-state.json").write_bytes(canonical(trust))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
