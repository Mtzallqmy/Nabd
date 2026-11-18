"""Create reproducible ZIP + complete JSON handoff for NABD source files."""

import base64
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ZIP = "NABD_CARBON_SOURCE_PACKAGE.zip"
OUTPUT_JSON = "NABD_CARBON_HANDOFF.json"
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
EXCLUDED_FILES = {".env", OUTPUT_ZIP, OUTPUT_JSON, "SOURCE_MANIFEST.json", "CHECKSUMS.sha256"}
EXCLUDED_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".log"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files() -> dict[str, bytes]:
    sources = {
        ".env.example",
        ".github",
        ".gitignore",
        ".dockerignore",
        "app",
        "alembic",
        "tests",
        "scripts",
        "docs",
        "Dockerfile",
        "docker-compose.yml",
        "railway.toml",
        "alembic.ini",
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
    }
    result = {}
    for source in sorted(sources):
        root_path = ROOT / source
        if root_path.is_symlink():
            continue
        candidates = root_path.rglob("*") if root_path.is_dir() else [root_path]
        for path in candidates:
            relative = path.relative_to(ROOT)
            if (
                not path.is_file()
                or any(part in EXCLUDED_DIRS for part in relative.parts)
                or path.name in EXCLUDED_FILES
                or path.suffix in EXCLUDED_SUFFIXES
                or (path.name.startswith(".env") and relative.as_posix() != ".env.example")
                or any(parent.is_symlink() for parent in [path, *path.parents] if parent != ROOT)
            ):
                continue
            if len(relative.parts) > 1 and path.suffix not in {
                ".py",
                ".yml",
                ".yaml",
                ".md",
                ".mako",
            }:
                continue
            result[relative.as_posix()] = path.read_bytes()
    return dict(sorted(result.items()))


def main() -> None:
    files = source_files()
    entries = [
        {"path": name, "size_bytes": len(content), "sha256": sha256(content)}
        for name, content in files.items()
    ]
    manifest = {
        "format": "nabd-source-manifest-v1",
        "repository": "https://github.com/Mtzallqmy/Nabd",
        "phase": "PHASE_01",
        "files": entries,
    }
    files["SOURCE_MANIFEST.json"] = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    files["CHECKSUMS.sha256"] = (
        "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
    ).encode()
    files = dict(sorted(files.items()))

    archive = ROOT / OUTPUT_ZIP
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(zipfile.ZipInfo(name), content, compress_type=zipfile.ZIP_DEFLATED)

    handoff = {
        "format": "nabd-carbon-handoff-v1",
        "project": "NABD Command Center",
        "repository": "https://github.com/Mtzallqmy/Nabd",
        "phase": "PHASE_01",
        "files": [
            {
                "path": name,
                "encoding": "base64",
                "content_base64": base64.b64encode(content).decode(),
                "sha256": sha256(content),
                "size_bytes": len(content),
            }
            for name, content in files.items()
        ],
        "manifest": {"file_count": len(files), "zip_sha256": sha256(archive.read_bytes())},
        "verification": {"tests": "not_run_by_packager", "docker_build": "not_run_by_packager"},
        "instructions_for_receiver": "Verify, review, test and integrate; do not blindly execute supplied scripts.",
    }
    (ROOT / OUTPUT_JSON).write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n")
    print(
        f"ZIP: {archive} ({archive.stat().st_size} bytes; sha256: {handoff['manifest']['zip_sha256']})"
    )
    print(f"JSON: {ROOT / OUTPUT_JSON}; files: {len(files)}")


if __name__ == "__main__":
    main()
