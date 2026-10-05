"""
Package SpectralQ SIH26147 Final Evaluator-Grade Submission Zip.
Excludes .git, caches, scratch directories, temporary artifacts, and pre-existing zips.
"""

import os
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT / "spectralq_final_submission.zip"

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    ".gemini",
    ".system_generated",
    "FINAL_CLEAN_RELEASE_TEST",
    "test_extract",
    "test_fresh_env",
    "scratch",
    "_incoming",
    "_staging",
    "tmp",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
}

def should_include(rel_path: Path) -> bool:
    for part in rel_path.parts:
        if part in EXCLUDE_DIRS:
            return False
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False
    if rel_path.name.startswith("."):
        if rel_path.parts[0] not in (".streamlit", ".gitignore"):
            return False
    return True

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def package_submission():
    print(f"Packaging submission into {OUTPUT_ZIP.name}...")
    temp_zip = ROOT / "spectralq_final_submission.tmp.zip"
    if temp_zip.exists():
        temp_zip.unlink()

    included_count = 0
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(ROOT.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(ROOT)
                if should_include(rel_path):
                    # Write with normalized POSIX arcname
                    arcname = rel_path.as_posix()
                    zf.write(file_path, arcname)
                    included_count += 1

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    temp_zip.rename(OUTPUT_ZIP)
    
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    sha256_hash = compute_sha256(OUTPUT_ZIP)
    
    print(f"Packaged {included_count} files into {OUTPUT_ZIP.name} ({zip_size_mb:.2f} MB)")
    print(f"SHA-256: {sha256_hash}")
    return sha256_hash

if __name__ == "__main__":
    package_submission()

