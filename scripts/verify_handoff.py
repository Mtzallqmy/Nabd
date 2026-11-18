"""Independently check NABD ZIP/JSON content identity and SHA-256 hashes."""

import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        bool(path)
        and not p.is_absolute()
        and not any(part in {"", ".", ".."} for part in path.split("/"))
        and "\\" not in path
        and ":" not in path
    )


def verify():
    zip_path = ROOT / "NABD_CARBON_SOURCE_PACKAGE.zip"
    json_path = ROOT / "NABD_CARBON_HANDOFF.json"
    if not zip_path.is_file() or not json_path.is_file():
        raise ValueError("ZIP or JSON file missing")
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    if handoff.get("format") != "nabd-carbon-handoff-v1":
        raise ValueError("Unexpected handoff format")
    if handoff["manifest"]["zip_sha256"] != sha(zip_path.read_bytes()):
        raise ValueError("ZIP checksum mismatch")
    decoded = {}
    for row in handoff.get("files", []):
        name = row["path"]
        if not safe_path(name) or name in decoded:
            raise ValueError(f"Unsafe/duplicate path: {name}")
        content = base64.b64decode(row["content_base64"], validate=True)
        if len(content) != row["size_bytes"] or sha(content) != row["sha256"]:
            raise ValueError(f"Content integrity mismatch: {name}")
        decoded[name] = content
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None:
            raise ValueError("Corrupt ZIP member")
        names = zf.namelist()
        if any(not safe_path(n) for n in names) or len(set(names)) != len(names):
            raise ValueError("Unsafe/duplicate ZIP paths")
        if set(names) != set(decoded):
            raise ValueError("ZIP and JSON file lists differ")
        for name in names:
            if zf.read(name) != decoded[name]:
                raise ValueError(f"ZIP/JSON file contents differ: {name}")
    if handoff["manifest"]["file_count"] != len(decoded):
        raise ValueError("Manifest count mismatch")
    manifest = json.loads(decoded["SOURCE_MANIFEST.json"])
    rows = manifest["files"]
    names = {row["path"] for row in rows}
    if len(names) != len(rows) or names != decoded.keys() - {
        "SOURCE_MANIFEST.json",
        "CHECKSUMS.sha256",
    }:
        raise ValueError("Source manifest coverage mismatch")
    checksums = []
    for row in rows:
        content = decoded[row["path"]]
        if len(content) != row["size_bytes"] or sha(content) != row["sha256"]:
            raise ValueError("Source manifest mismatch")
        checksums.append(f"{row['sha256']}  {row['path']}\n")
    if "".join(checksums).encode() != decoded["CHECKSUMS.sha256"]:
        raise ValueError("Checksum listing mismatch")
    print(f"PASS: ZIP, JSON, manifest and SHA-256 match ({len(decoded)} files)")
    return True


if __name__ == "__main__":
    try:
        verify()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
