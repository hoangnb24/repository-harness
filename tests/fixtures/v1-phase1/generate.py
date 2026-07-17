#!/usr/bin/env python3
"""Generate deterministic, unmistakably test-only Phase 1 fixtures."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = HERE
POS = OUTPUT / "positive"
NEG = OUTPUT / "negative"
GENERATED: set[str] = set()

# This material is deliberately public, deterministic, and labeled unsafe. It
# exists only to make fixture signatures reproducible. It must never be loaded
# by a production trust bundle or signing workflow.
TEST_ONLY_LABEL_PREFIX = "repository-harness UNSAFE TEST ONLY private seed "

Q = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, Q - 2, Q) % Q
I = pow(2, (Q - 1) // 4, Q)


def xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(D * y * y + 1, Q - 2, Q) % Q
    x = pow(xx, (Q + 3) // 8, Q)
    if (x * x - xx) % Q:
        x = x * I % Q
    return Q - x if x & 1 else x


BY = 4 * pow(5, Q - 2, Q) % Q
B = (xrecover(BY), BY)


def edwards_add(p: tuple[int, int], q: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = p
    x2, y2 = q
    den = D * x1 * x2 * y1 * y2
    return (
        (x1 * y2 + x2 * y1) * pow(1 + den, Q - 2, Q) % Q,
        (y1 * y2 + x1 * x2) * pow(1 - den, Q - 2, Q) % Q,
    )


def scalarmult(p: tuple[int, int], n: int) -> tuple[int, int]:
    result = (0, 1)
    addend = p
    while n:
        if n & 1:
            result = edwards_add(result, addend)
        addend = edwards_add(addend, addend)
        n >>= 1
    return result


def encodepoint(p: tuple[int, int]) -> bytes:
    x, y = p
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def key_seed(label: str) -> bytes:
    return hashlib.sha256((TEST_ONLY_LABEL_PREFIX + label).encode()).digest()


def public_key(seed: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return encodepoint(scalarmult(B, a))


def sign(seed: bytes, message: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    prefix = h[32:]
    pub = public_key(seed)
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % L
    encoded_r = encodepoint(scalarmult(B, r))
    k = int.from_bytes(hashlib.sha512(encoded_r + pub + message).digest(), "little") % L
    s = (r + k * a) % L
    return encoded_r + s.to_bytes(32, "little")


def jcs_string(value: str) -> str:
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise ValueError("lone surrogate is not valid JCS")
    out = ['"']
    short = {8: "\\b", 9: "\\t", 10: "\\n", 12: "\\f", 13: "\\r"}
    for ch in value:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif cp in short:
            out.append(short[cp])
        elif cp < 0x20:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def utf16_key(value: str) -> bytes:
    return value.encode("utf-16-be", "surrogatepass")


def jcs(value: object) -> bytes:
    def render(item: object) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, int) and not isinstance(item, bool):
            if abs(item) > 9007199254740991:
                raise ValueError("integer is outside interoperable JCS range")
            return str(item)
        if isinstance(item, float):
            raise ValueError("security fixture contracts forbid floating point")
        if isinstance(item, str):
            return jcs_string(item)
        if isinstance(item, list):
            return "[" + ",".join(render(v) for v in item) + "]"
        if isinstance(item, dict):
            keys = sorted(item, key=utf16_key)
            return "{" + ",".join(jcs_string(k) + ":" + render(item[k]) for k in keys) + "}"
        raise TypeError(type(item))

    return render(value).encode("utf-8")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(jcs(value)).hexdigest()


def signed_message(domain: str, value: object) -> bytes:
    return hashlib.sha256(domain.encode() + b"\0" + jcs(value)).digest()


def key(label: str) -> dict[str, str]:
    raw = public_key(key_seed(label))
    return {
        "key_id": "ed25519-sha256:" + hashlib.sha256(raw).hexdigest(),
        "algorithm": "ed25519",
        "public_key_base64": base64.b64encode(raw).decode(),
        "test_fixture": True
    }


def raw_key(raw: bytes) -> dict[str, object]:
    return {
        "key_id": "ed25519-sha256:" + hashlib.sha256(raw).hexdigest(),
        "algorithm": "ed25519",
        "public_key_base64": base64.b64encode(raw).decode(),
        "test_fixture": True,
    }


def envelope(payload: object, trust_domain: str, role: str, sequence: int,
             domain: str, signer_labels: list[str]) -> dict[str, object]:
    message = signed_message(domain, payload)
    signatures = []
    for label in signer_labels:
        signer = key(label)
        signatures.append({
            "key_id": signer["key_id"],
            "algorithm": "ed25519",
            "signature": base64.b64encode(sign(key_seed(label), message)).decode()
        })
    return {
        "schema": "repository-harness-signature-envelope/v1",
        "trust_domain": trust_domain,
        "role": role,
        "sequence": sequence,
        "payload_sha256": canonical_digest(payload),
        "signatures": signatures
    }


def write_json(path: Path, value: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.name.endswith(".signatures.json"):
        path.write_bytes(jcs(value))
        GENERATED.add(path.relative_to(OUTPUT).as_posix())
        return
    if compact:
        text = json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    GENERATED.add(path.relative_to(OUTPUT).as_posix())


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    GENERATED.add(path.relative_to(OUTPUT).as_posix())


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    GENERATED.add(path.relative_to(OUTPUT).as_posix())


def trust_bundle(domain: str, sequence: int, root_labels: list[str],
                 release_labels: list[str], role: str,
                 previous: str | None = None, revoked: list[str] | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": "repository-harness-trust-bundle/v1",
        "trust_domain": domain,
        "sequence": sequence,
        "test_fixture_notice": "UNSAFE-TEST-ONLY-NOT-FOR-RELEASE",
        "roots": {"threshold": 2, "keys": [key(label) for label in root_labels]},
        "roles": [{"name": role, "threshold": 2, "keys": [key(label) for label in release_labels]}],
        "revoked_key_ids": revoked or []
    }
    if previous:
        value["previous_bundle_sha256"] = previous
    return value


def file_asset(asset_id: str, source: str, disposition: str, destination: str) -> dict[str, object]:
    data = (ROOT / source).read_bytes()
    return {
        "id": asset_id,
        "source": source,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "disposition": disposition,
        "destination": destination
    }


def generate_trust() -> None:
    core_roots = [f"core-root-{i}" for i in range(1, 4)]
    core_release = [f"core-release-{i}" for i in range(1, 4)]
    bridge_roots = [f"bridge-root-{i}" for i in range(1, 4)]
    bridge_release = [f"bridge-release-{i}" for i in range(1, 4)]
    next_roots = [f"core-next-root-{i}" for i in range(1, 4)]

    core_bundle = trust_bundle("repository-harness-core", 1, core_roots, core_release, "core-release")
    bridge_bundle = trust_bundle("repository-harness-bridge", 1, bridge_roots, bridge_release, "bridge-release")
    write_json(POS / "core-trust-bundle.json", core_bundle)
    write_json(POS / "core-trust-bundle.signatures.json", envelope(
        core_bundle, "repository-harness-core", "core-root", 1,
        "repository-harness-core-trust-bundle-v1", core_roots[:2]))
    write_json(POS / "bridge-trust-bundle.json", bridge_bundle)
    write_json(POS / "bridge-trust-bundle.signatures.json", envelope(
        bridge_bundle, "repository-harness-bridge", "bridge-root", 1,
        "repository-harness-bridge-trust-bundle-v1", bridge_roots[:2]))
    write_json(POS / "test-bootstrap-anchors.json", {
        "schema": "repository-harness-test-bootstrap-anchors/v1",
        "test_fixture_notice": "UNSAFE-TEST-ONLY-NOT-A-RELEASE-TRUST-BUNDLE",
        "core": {
            "trust_domain": "repository-harness-core",
            "root_threshold": 2,
            "root_keys": [key(label) for label in core_roots],
            "exact_bundle_digest": canonical_digest(core_bundle)
        },
        "bridge": {
            "trust_domain": "repository-harness-bridge",
            "root_threshold": 2,
            "root_keys": [key(label) for label in bridge_roots],
            "exact_bundle_digest": canonical_digest(bridge_bundle)
        }
    })

    core_index = {
        "schema": "repository-harness-payload-index/v1",
        "trust_domain": "repository-harness-core",
        "role": "core-release",
        "sequence": 42,
        "release": "1.0.0-test.1",
        "source_commit": "1" * 40,
        "tag": "harness-v1-core-v1.0.0-test.1",
        "assets": [
            file_asset("decision-template", "docs/templates/decision.md", "managed-v1", "docs/templates/decision.md"),
            file_asset("story-template", "docs/templates/story.md", "optional-v1", "docs/templates/story.md")
        ]
    }
    bridge_index = {
        "schema": "repository-harness-bridge-payload-index/v1",
        "trust_domain": "repository-harness-bridge",
        "role": "bridge-release",
        "sequence": 7,
        "release": "1.0.0-test.1",
        "source_commit": "2" * 40,
        "tag": "harness-v0-bridge-v1.0.0-test.1",
        "assets": [file_asset(
            "v0-schema-001", "release/contracts/v1/v0/schemas/001-init.sql",
            "bridge-only-legacy", "share/repository-harness-v0/schemas/001-init.sql")]
    }
    write_json(POS / "core-payload-index.json", core_index)
    write_json(POS / "core-payload-index-reencoded.json", core_index, compact=True)
    write_json(POS / "core-payload-index.signatures.json", envelope(
        core_index, "repository-harness-core", "core-release", 42,
        "repository-harness-payload-index-v1", core_release[:2]))
    write_json(POS / "bridge-payload-index.json", bridge_index)
    write_json(POS / "bridge-payload-index.signatures.json", envelope(
        bridge_index, "repository-harness-bridge", "bridge-release", 7,
        "repository-harness-bridge-payload-index-v1", bridge_release[:2]))

    write_json(POS / "high-water-marks.json", {
        "schema": "repository-harness-high-water-marks/v1",
        "marks": [
            {"trust_domain": "repository-harness-core", "role": "core-release", "sequence": 42, "digest": canonical_digest(core_index)},
            {"trust_domain": "repository-harness-bridge", "role": "bridge-release", "sequence": 7, "digest": canonical_digest(bridge_index)}
        ],
        "first_install": {"core_exact_digest": canonical_digest(core_index), "bridge_minimum_sequence": 7}
    })

    freeze = dict(core_index)
    freeze.update(sequence=41, release="0.9.9-test.rollback", tag="harness-v1-core-v0.9.9-test.rollback")
    write_json(NEG / "freeze-payload-index.json", freeze)
    write_json(NEG / "freeze-payload-index.signatures.json", envelope(
        freeze, "repository-harness-core", "core-release", 41,
        "repository-harness-payload-index-v1", core_release[:2]))

    rollback = {
        "schema": "repository-harness-rollback-authorization/v1",
        "trust_domain": "repository-harness-core",
        "root_bundle_sequence": 1,
        "role": "core-release",
        "authorized_sequence": 41,
        "authorized_digest": canonical_digest(freeze)
    }
    write_json(POS / "authorized-rollback.json", rollback)
    write_json(POS / "authorized-rollback.signatures.json", envelope(
        rollback, "repository-harness-core", "core-root", 1,
        "repository-harness-core-rollback-authorization-v1", core_roots[:2]))
    wrong = dict(rollback)
    wrong["authorized_digest"] = "0" * 64
    write_json(NEG / "wrong-rollback.json", wrong)
    write_json(NEG / "wrong-rollback.signatures.json", envelope(
        wrong, "repository-harness-core", "core-root", 1,
        "repository-harness-core-rollback-authorization-v1", core_roots[:2]))
    wrong_root_sequence = dict(rollback)
    wrong_root_sequence["root_bundle_sequence"] = 2
    write_json(NEG / "wrong-root-bundle-sequence-rollback.json", wrong_root_sequence)
    write_json(NEG / "wrong-root-bundle-sequence-rollback.signatures.json", envelope(
        wrong_root_sequence, "repository-harness-core", "core-root", 2,
        "repository-harness-core-rollback-authorization-v1", core_roots[:2]))

    one_signature = envelope(core_index, "repository-harness-core", "core-release", 42,
                             "repository-harness-payload-index-v1", core_release[:1])
    write_json(NEG / "bad-threshold.signatures.json", one_signature)
    bad_signature = envelope(core_index, "repository-harness-core", "core-release", 42,
                             "repository-harness-payload-index-v1", core_release[:2])
    raw_sig = bytearray(base64.b64decode(bad_signature["signatures"][0]["signature"]))
    raw_sig[0] ^= 1
    bad_signature["signatures"][0]["signature"] = base64.b64encode(raw_sig).decode()
    write_json(NEG / "bad-signature.signatures.json", bad_signature)
    write_json(NEG / "key-crossover.signatures.json", envelope(
        core_index, "repository-harness-core", "core-release", 42,
        "repository-harness-payload-index-v1", bridge_release[:2]))
    write_json(NEG / "key-role-crossover.signatures.json", envelope(
        core_index, "repository-harness-core", "core-release", 42,
        "repository-harness-payload-index-v1", core_roots[:2]))
    write_json(NEG / "unknown-key.signatures.json", envelope(
        core_index, "repository-harness-core", "core-release", 42,
        "repository-harness-payload-index-v1", [core_release[0], "unknown-release-key"]))

    identity = b"\x01" + b"\x00" * 31
    order_two = (Q - 1).to_bytes(32, "little")
    zero_signature = identity + b"\x00" * 32
    message = signed_message("repository-harness-payload-index-v1", core_index)
    for filename, case_name, raw_public in [
        ("ed25519-identity.json", "identity-public-key", identity),
        ("ed25519-order-two.json", "order-two-small-order-public-key", order_two),
        ("ed25519-zero-scalar.json", "zero-signature-scalar", public_key(key_seed(core_release[0]))),
    ]:
        write_json(NEG / filename, {
            "schema": "repository-harness-ed25519-negative-vector/v1",
            "case": case_name,
            "public_key_base64": base64.b64encode(raw_public).decode(),
            "message_base64": base64.b64encode(message).decode(),
            "signature_base64": base64.b64encode(zero_signature).decode(),
        })
    forged_key_objects = [raw_key(identity), raw_key(order_two), key(core_release[2])]
    write_json(NEG / "forged-2-of-3-keys.json", {
        "schema": "repository-harness-forged-test-keys/v1",
        "test_fixture_notice": "UNSAFE-TEST-ONLY-SMALL-ORDER-KEYS",
        "keys": forged_key_objects,
    })
    forged_envelope = {
        "schema": "repository-harness-signature-envelope/v1",
        "trust_domain": "repository-harness-core",
        "role": "core-release",
        "sequence": 42,
        "payload_sha256": canonical_digest(core_index),
        "signatures": [
            {"key_id": forged_key_objects[0]["key_id"], "algorithm": "ed25519", "signature": base64.b64encode(zero_signature).decode()},
            {"key_id": forged_key_objects[1]["key_id"], "algorithm": "ed25519", "signature": base64.b64encode(zero_signature).decode()},
        ],
    }
    write_json(NEG / "forged-2-of-3.signatures.json", forged_envelope)

    decomposed = json.loads(json.dumps(core_index))
    decomposed["assets"][0]["destination"] = "docs/t" + unicodedata.normalize("NFD", "é") + "mplates/decision.md"
    write_json(NEG / "unicode-reencoded-index.json", decomposed)
    duplicate = (POS / "core-payload-index-reencoded.json").read_text(encoding="utf-8")
    duplicate = duplicate.replace('"sequence":42', '"sequence":42,"sequence":42', 1)
    write_text(NEG / "duplicate-key-index.json", duplicate)

    revoked_id = key(core_release[0])["key_id"]
    revocation = trust_bundle("repository-harness-core", 2, core_roots, core_release,
                              "core-release", canonical_digest(core_bundle), [revoked_id])
    write_json(POS / "revocation-trust-bundle.json", revocation)
    write_json(POS / "revocation-trust-bundle.signatures.json", envelope(
        revocation, "repository-harness-core", "core-root", 2,
        "repository-harness-core-trust-bundle-v1", core_roots[:2]))
    updated = dict(core_index)
    updated.update(sequence=43, release="1.0.0-test.2", tag="harness-v1-core-v1.0.0-test.2")
    write_json(POS / "post-revocation-payload-index.json", updated)
    write_json(POS / "post-revocation-payload-index.signatures.json", envelope(
        updated, "repository-harness-core", "core-release", 43,
        "repository-harness-payload-index-v1", core_release[1:]))
    write_json(NEG / "revoked-payload-index.signatures.json", envelope(
        core_index, "repository-harness-core", "core-release", 42,
        "repository-harness-payload-index-v1", core_release[:2]))

    rotation = trust_bundle("repository-harness-core", 3, next_roots, core_release,
                            "core-release", canonical_digest(revocation), [revoked_id])
    write_json(POS / "root-rotation-trust-bundle.json", rotation)
    write_json(POS / "root-rotation-trust-bundle.signatures.json", envelope(
        rotation, "repository-harness-core", "core-root-rotation", 3,
        "repository-harness-core-trust-bundle-v1", core_roots[:2] + next_roots[:2]))

    supported_platforms = ["macos-arm64", "macos-x64", "linux-x64", "linux-arm64", "windows-x64"]
    availability_assets = []
    for category in ["binary-per-supported-platform", "checksum-per-binary"]:
        for platform in supported_platforms:
            suffix = ".sha256" if category == "checksum-per-binary" else ""
            binary = f"harness-v0-migrate-{platform}{'.exe' if platform == 'windows-x64' else ''}"
            path = f"artifacts/{binary}{suffix}"
            availability_assets.append({
                "category": category,
                "platform": platform,
                "path": path,
                "sha256": hashlib.sha256(f"{category}:{platform}:{path}".encode()).hexdigest(),
            })
    for category, path in [
        ("authenticated-index-or-attestation", "metadata/payload-index.json"),
        ("supported-input-matrix", "metadata/supported-input-matrix.json"),
        ("release-notes", "metadata/release-notes.md"),
        ("source-tag", "metadata/source-tag.txt"),
        ("reproducible-build-instructions", "metadata/reproducible-build.md"),
    ]:
        availability_assets.append({
            "category": category,
            "platform": "all",
            "path": path,
            "sha256": hashlib.sha256(f"{category}:all:{path}".encode()).hexdigest(),
        })
    availability = {
        "schema": "repository-harness-bridge-availability-receipt/v1",
        "trust_domain": "repository-harness-bridge",
        "role": "bridge-release",
        "sequence": 8,
        "owner": "release-maintainers",
        "month": "2027-03",
        "retention_through": "2028-06-30T23:59:59Z",
        "weekly_checks": ["2027-03-01T00:00:00Z", "2027-03-08T00:00:00Z", "2027-03-15T00:00:00Z", "2027-03-22T00:00:00Z", "2027-03-29T00:00:00Z"],
        "assets": availability_assets,
        "result": "available-and-integrity-verified"
    }
    write_json(POS / "availability-receipt.json", availability)
    write_json(POS / "availability-receipt.signatures.json", envelope(
        availability, "repository-harness-bridge", "bridge-release", 8,
        "repository-harness-bridge-availability-receipt-v1", bridge_release[:2]))
    gap = json.loads(json.dumps(availability))
    gap["weekly_checks"][1] = "2027-03-08T00:00:01Z"
    write_json(NEG / "availability-gap-over-seven.json", gap)
    decreasing = json.loads(json.dumps(availability))
    decreasing["weekly_checks"][2] = "2027-03-07T00:00:00Z"
    write_json(NEG / "availability-decreasing.json", decreasing)
    wrong_month = json.loads(json.dumps(availability))
    wrong_month["weekly_checks"][0] = "2027-02-28T23:59:59Z"
    write_json(NEG / "availability-wrong-month.json", wrong_month)
    missing_start = json.loads(json.dumps(availability))
    missing_start["weekly_checks"] = ["2027-03-08T00:00:01Z", "2027-03-15T00:00:01Z", "2027-03-22T00:00:01Z", "2027-03-29T00:00:01Z"]
    write_json(NEG / "availability-missing-start-coverage.json", missing_start)
    missing_end = json.loads(json.dumps(availability))
    missing_end["weekly_checks"] = ["2027-03-01T00:00:00Z", "2027-03-08T00:00:00Z", "2027-03-15T00:00:00Z", "2027-03-22T00:00:00Z"]
    write_json(NEG / "availability-missing-end-coverage.json", missing_end)
    naive_timestamp = json.loads(json.dumps(availability))
    naive_timestamp["weekly_checks"][0] = "2027-03-01T00:00:00"
    write_json(NEG / "availability-naive-timestamp.json", naive_timestamp)
    incomplete = json.loads(json.dumps(availability))
    incomplete["assets"] = [asset for asset in incomplete["assets"] if asset["category"] != "source-tag"]
    write_json(NEG / "availability-incomplete-set.json", incomplete)
    missing_platform = json.loads(json.dumps(availability))
    missing_platform["assets"] = [asset for asset in missing_platform["assets"] if asset["platform"] != "windows-x64"]
    write_json(NEG / "availability-missing-platform.json", missing_platform)


def generate_archive() -> None:
    archive = b"REPOSITORY-HARNESS UNSAFE TEST ONLY AGE/X25519 CIPHERTEXT FIXTURE\n" + bytes(range(64))
    archive_path = POS / "archive" / "conversion.age"
    write_bytes(archive_path, archive)
    tampered = bytearray(archive)
    tampered[-1] ^= 1
    tampered_path = NEG / "archive" / "conversion.age"
    write_bytes(tampered_path, tampered)
    digest = hashlib.sha256(archive).hexdigest()
    write_json(POS / "archive" / "manifest.json", {
        "schema": "repository-harness-v0-archive-manifest/v1",
        "conversion_id": "fixture-wal-only",
        "source_schema": 1,
        "confidentiality_mode": "encrypted-age-x25519",
        "recipient_fingerprints": ["age1fixtureowner000000000000000000000000000000000000000000000000000"],
        "members": [{"path": "raw/harness.db", "sha256": "b" * 64, "bytes": 8192, "capture": "pre-copy-post-equal"}],
        "standalone_backup_sha256": "c" * 64,
        "archive_sha256": digest,
        "custody": "repository-owner-indefinite-write-once"
    })
    write_json(NEG / "archive" / "manifest.json", json.loads((POS / "archive" / "manifest.json").read_text()))


def generate_contract_negatives() -> None:
    bootstrap = json.loads((ROOT / "release/contracts/v1/bootstrap-identity.json").read_text(encoding="utf-8"))
    added_step = json.loads(json.dumps(bootstrap))
    added_step["verification_order"].append("trust-adjacent-key")
    write_json(NEG / "bootstrap-added-step.json", added_step)
    reordered = json.loads(json.dumps(bootstrap))
    reordered["verification_order"][1], reordered["verification_order"][2] = reordered["verification_order"][2], reordered["verification_order"][1]
    write_json(NEG / "bootstrap-reordered.json", reordered)
    domain_mismatch = json.loads(json.dumps(bootstrap))
    domain_mismatch["bridge"]["signature_domains"]["payload_index"] = bootstrap["core"]["signature_domains"]["payload_index"]
    write_json(NEG / "bootstrap-domain-mismatch.json", domain_mismatch)
    tag_mismatch = json.loads(json.dumps(bootstrap))
    tag_mismatch["bridge"]["tag_namespace"] = "harness-v1-core-v*"
    write_json(NEG / "bootstrap-tag-mismatch.json", tag_mismatch)
    sequence_mismatch = json.loads(json.dumps(bootstrap))
    sequence_mismatch["bridge"]["sequence_namespaces"]["release"] = "core-release"
    write_json(NEG / "bootstrap-sequence-mismatch.json", sequence_mismatch)
    role_crossover = json.loads(json.dumps(bootstrap))
    role_crossover["bridge"]["roles"]["release"] = bootstrap["core"]["roles"]["release"]
    write_json(NEG / "bootstrap-role-crossover.json", role_crossover)
    workflow_state_mismatch = json.loads(json.dumps(bootstrap))
    workflow_state_mismatch["core"]["workflow_lifecycle"]["state"] = "reserved-absent"
    write_json(NEG / "bootstrap-workflow-state-mismatch.json", workflow_state_mismatch)
    workflow_path_mismatch = json.loads(json.dumps(bootstrap))
    workflow_path_mismatch["bridge"]["protected_workflow"] = ".github/workflows/not-the-reserved-bridge-release.yml@refs/heads/main"
    write_json(NEG / "bootstrap-workflow-path-mismatch.json", workflow_path_mismatch)
    unknown_field = json.loads(json.dumps(bootstrap))
    unknown_field["downloaded_key"] = "trusted"
    write_json(NEG / "bootstrap-unknown-field.json", unknown_field)

    grammar = json.loads((ROOT / "release/contracts/v1/command-grammars.json").read_text(encoding="utf-8"))
    extra_command = json.loads(json.dumps(grammar))
    extra_command["core"]["top_level"].append("migrate")
    extra_command["core"]["commands"].append({"name": "migrate", "mutation": "legacy", "options": [], "exits": [0]})
    write_json(NEG / "extra-core-command.json", extra_command)
    reordered_command = json.loads(json.dumps(grammar))
    reordered_command["core"]["top_level"][0:2] = reversed(reordered_command["core"]["top_level"][0:2])
    reordered_command["core"]["commands"][0:2] = reversed(reordered_command["core"]["commands"][0:2])
    write_json(NEG / "reordered-core-command.json", reordered_command)

    command_binding = json.loads((ROOT / "release/contracts/v1/command-implementation-binding.json").read_text(encoding="utf-8"))
    entrypoint_mismatch = json.loads(json.dumps(command_binding))
    entrypoint_mismatch["surfaces"]["bridge"]["future_entrypoints"][0] = "scripts/bin/harness-v0-convert"
    write_json(NEG / "command-binding-entrypoint-mismatch.json", entrypoint_mismatch)
    binding_state_mismatch = json.loads(json.dumps(command_binding))
    binding_state_mismatch["surfaces"]["core"]["entrypoint_state"] = "absent"
    write_json(NEG / "command-binding-state-mismatch.json", binding_state_mismatch)
    binding_unknown_field = json.loads(json.dumps(command_binding))
    binding_unknown_field["surfaces"]["core"]["live_command_source"] = "scripts/bin/harness"
    write_json(NEG / "command-binding-unknown-field.json", binding_unknown_field)

    release_inventory = json.loads((ROOT / "release/contracts/v1/release-artifacts.json").read_text(encoding="utf-8"))
    extra_platform = json.loads(json.dumps(release_inventory))
    extra_platform["platforms"].append({"platform": "linux-riscv64", "target": "riscv64gc-unknown-linux-gnu", "runner": "ubuntu-latest", "binary": "harness-cli-linux-riscv64", "checksum": "harness-cli-linux-riscv64.sha256"})
    write_json(NEG / "release-extra-platform.json", extra_platform)
    binary_drift = json.loads(json.dumps(release_inventory))
    binary_drift["platforms"][2]["binary"] = "harness-linux-x64"
    binary_drift["platforms"][2]["checksum"] = "harness-linux-x64.sha256"
    write_json(NEG / "release-binary-drift.json", binary_drift)

    manifest = json.loads((HERE / "positive/manifest.json").read_text(encoding="utf-8"))
    malformed = json.loads(json.dumps(manifest))
    malformed["schema"] = "repository-harness-manifest/v2"
    write_json(NEG / "malformed-schema-manifest.json", malformed)
    output = json.loads((HERE / "positive/output-envelope.json").read_text(encoding="utf-8"))
    output["details"]["operations"] = [{
        "operation_id": "write-manifest",
        "kind": "write-manifest",
        "path": ".harness/manifest.json",
        "disposition": "managed-v1",
        "before_sha256": None,
        "after_sha256": "a" * 64,
        "shell_command": "forbidden",
    }]
    write_json(NEG / "output-operation-unknown-field.json", output)

    write_json(OUTPUT / "trust-cases.json", {
        "schema": "repository-harness-trust-cases/v1",
        "positive": ["core-2-of-3", "bridge-2-of-3", "disjoint-key-sets", "benign-json-reencoding", "same-sequence-same-digest-idempotent", "exact-root-authorized-rollback", "newer-root-signed-revocation", "post-revocation-two-valid-signers", "old-and-new-threshold-root-rotation", "bridge-monthly-availability-receipt"],
        "negative": ["one-of-three-threshold", "bad-ed25519-signature", "identity-public-key", "order-two-small-order-public-key", "zero-signature-scalar", "small-order-forged-two-of-three", "unknown-release-key", "root-key-on-release-role", "bridge-key-on-core-index", "duplicate-json-member", "unicode-semantic-reencoding", "lower-sequence-freeze", "same-sequence-different-digest", "rollback-wrong-digest", "rollback-wrong-active-root-bundle-sequence", "revoked-key-no-longer-counts", "root-rotation-old-threshold-only", "root-rotation-new-threshold-only", "availability-gap-over-seven", "availability-decreasing", "availability-wrong-month", "availability-missing-start-coverage", "availability-missing-end-coverage", "availability-naive-timestamp", "availability-incomplete-complete-set", "availability-missing-platform", "bootstrap-order-domain-role-tag-sequence-mismatch", "malformed-schema", "unknown-field"],
    })


def generate_wal_fixture() -> None:
    destination = HERE / "v0-capture" / "wal-only" / "source"
    expected_path = destination.parent / "expected.json"
    if not expected_path.is_file():
        raise RuntimeError("the immutable WAL fixture is missing; restore it from Git")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    for name, digest in expected["files"].items():
        path = destination / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"immutable WAL fixture differs: {name}; restore it from Git")


def set_output(path: Path) -> None:
    global OUTPUT, POS, NEG
    OUTPUT = path
    POS = OUTPUT / "positive"
    NEG = OUTPUT / "negative"


def generate_all(output: Path) -> set[str]:
    set_output(output)
    GENERATED.clear()
    POS.mkdir(parents=True, exist_ok=True)
    NEG.mkdir(parents=True, exist_ok=True)
    generate_trust()
    generate_archive()
    generate_contract_negatives()
    generate_wal_fixture()
    manifest_path = OUTPUT / "generated-files.txt"
    manifest_entries = sorted(GENERATED | {"generated-files.txt"})
    manifest_path.write_text("\n".join(manifest_entries) + "\n", encoding="utf-8")
    GENERATED.add("generated-files.txt")
    return set(GENERATED)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="regenerate in a temporary directory and compare exact committed bytes")
    arguments = parser.parse_args()
    if arguments.check:
        with tempfile.TemporaryDirectory(prefix="harness-v1-fixture-check-") as temporary:
            generated = generate_all(Path(temporary))
            for relative in sorted(generated):
                expected = HERE / relative
                actual = Path(temporary) / relative
                if not expected.is_file() or expected.read_bytes() != actual.read_bytes():
                    raise RuntimeError(f"committed generated fixture differs: {relative}; run generate.py")
        print(f"deterministic fixture regeneration check passed ({len(generated)} files)")
    else:
        generated = generate_all(HERE)
        print(f"generated {len(generated)} deterministic fixture files and verified immutable WAL fixture")


if __name__ == "__main__":
    main()
