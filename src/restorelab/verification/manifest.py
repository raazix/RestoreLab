"""
RestoreLab Cryptographic Manifest Engine
Generates deterministic SHA-256 manifests of file trees and performs strict,
byte-level comparison between pre-backup sources and isolated restored trees.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

DiffStatus = Literal["matched", "missing", "extra", "corrupted", "size_mismatch"]


class FileEntry(BaseModel):
    """Metadata and cryptographic fingerprint for a single file."""

    path: str = Field(description="Normalized relative path with forward slashes")
    size_bytes: int = Field(ge=0, description="Exact file size in bytes")
    sha256: str = Field(description="Lowercase hex-encoded SHA-256 digest")
    modified_at: str = Field(description="ISO 8601 modification timestamp")


class Manifest(BaseModel):
    """Complete cryptographically bound manifest for a directory snapshot."""

    manifest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    root_path: str = Field(description="Original root path at time of generation")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_files: int = 0
    total_bytes: int = 0
    entries: Dict[str, FileEntry] = Field(default_factory=dict)
    manifest_hash: str = Field(
        default="",
        description="SHA-256 digest over canonical sorted manifest content",
    )

    def calculate_manifest_hash(self) -> str:
        """Compute deterministic SHA-256 hash of all sorted entries."""
        hasher = hashlib.sha256()
        for path in sorted(self.entries.keys()):
            entry = self.entries[path]
            line = f"{entry.path}|{entry.size_bytes}|{entry.sha256}\n"
            hasher.update(line.encode("utf-8"))
        return hasher.hexdigest()

    def finalize(self) -> "Manifest":
        """Update counts and manifest hash."""
        self.total_files = len(self.entries)
        self.total_bytes = sum(e.size_bytes for e in self.entries.values())
        self.manifest_hash = self.calculate_manifest_hash()
        return self


class FileDiff(BaseModel):
    """Detailed differential report for a single file."""

    path: str
    status: DiffStatus
    expected_size: Optional[int] = None
    actual_size: Optional[int] = None
    expected_sha256: Optional[str] = None
    actual_sha256: Optional[str] = None
    details: str = ""


class ManifestComparisonResult(BaseModel):
    """Result of comparing expected pre-backup manifest with restored manifest."""

    source_manifest_id: str
    restored_manifest_id: str
    is_perfect_match: bool
    total_expected: int
    total_actual: int
    matched_count: int = 0
    missing_count: int = 0
    extra_count: int = 0
    corrupted_count: int = 0
    size_mismatch_count: int = 0
    diffs: List[FileDiff] = Field(default_factory=list)
    summary: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)


def compute_file_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute hex SHA-256 digest of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_rel_path(path: Path | str) -> str:
    """Convert path to normalized relative POSIX string (e.g. 'docs/report.txt')."""
    p_str = str(path).replace("\\", "/")
    p_str = p_str.lstrip("/")
    return p_str


def generate_manifest(
    directory: Path | str,
    max_bytes: int = 500 * 1024 * 1024,
    max_files: int = 10000,
    exclude_patterns: Optional[List[str]] = None,
) -> Manifest:
    """
    Scan a directory tree and construct a deterministic SHA-256 manifest.
    
    Safety controls:
    - Normalizes paths to relative POSIX.
    - Prevents symlink path traversal outside root.
    - Throws ValueError if file count or byte volume exceeds safety bounds.
    - Omits temporary files matching exclude_patterns.
    """
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError(f"Manifest source directory does not exist: {root}")

    excludes = exclude_patterns or [
        ".git",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "Thumbs.db",
    ]

    manifest = Manifest(root_path=str(root))
    scanned_bytes = 0
    scanned_files = 0

    # Sort directory tree traversal for determinism
    all_paths: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        # Exclude directories in-place
        dirnames[:] = [
            d for d in sorted(dirnames)
            if not any(d == ex.strip("/") for ex in excludes)
        ]
        for fname in sorted(filenames):
            if any(fname == ex or fname.endswith(ex.replace("*", "")) for ex in excludes):
                continue
            all_paths.append(Path(dirpath) / fname)

    all_paths.sort()

    for file_path in all_paths:
        # Check safety limits
        scanned_files += 1
        if scanned_files > max_files:
            raise ValueError(
                f"File limit exceeded: {scanned_files} files exceeds safety limit {max_files}"
            )

        # Symlink security check
        if file_path.is_symlink():
            resolved = file_path.resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                # Symlink points outside root: skip for safety
                continue

        try:
            stat = file_path.stat()
            size = stat.st_size
            scanned_bytes += size
            if scanned_bytes > max_bytes:
                raise ValueError(
                    f"Byte volume limit exceeded: {scanned_bytes} bytes exceeds safety limit {max_bytes}"
                )

            rel_path = normalize_rel_path(file_path.relative_to(root))
            sha = compute_file_sha256(file_path)
            mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

            manifest.entries[rel_path] = FileEntry(
                path=rel_path,
                size_bytes=size,
                sha256=sha,
                modified_at=mod_time,
            )
        except (PermissionError, FileNotFoundError, OSError) as e:
            # Record failed file reads gracefully
            rel_path = normalize_rel_path(file_path.relative_to(root))
            manifest.entries[rel_path] = FileEntry(
                path=rel_path,
                size_bytes=0,
                sha256=f"ERROR:{type(e).__name__}",
                modified_at=datetime.now(timezone.utc).isoformat(),
            )

    return manifest.finalize()


def compare_manifests(
    expected: Manifest,
    actual: Manifest,
) -> ManifestComparisonResult:
    """
    Compare pre-backup expected manifest against restored actual manifest.
    
    Detects:
    - Matched files (identical path, size, and hash)
    - Missing files (present in expected, absent in actual)
    - Extra unexpected files (present in actual, absent in expected)
    - Content corruption (present in both, identical or differing size, different hash)
    - Size mismatches
    """
    diffs: List[FileDiff] = []
    matched = 0
    missing = 0
    extra = 0
    corrupted = 0
    size_mismatch = 0

    expected_paths = set(expected.entries.keys())
    actual_paths = set(actual.entries.keys())

    # 1. Compare all expected files
    for path in sorted(expected_paths):
        exp_entry = expected.entries[path]
        if path not in actual_paths:
            missing += 1
            diffs.append(
                FileDiff(
                    path=path,
                    status="missing",
                    expected_size=exp_entry.size_bytes,
                    expected_sha256=exp_entry.sha256,
                    details="File expected from original manifest is missing from restored tree",
                )
            )
        else:
            act_entry = actual.entries[path]
            size_ok = exp_entry.size_bytes == act_entry.size_bytes
            hash_ok = exp_entry.sha256 == act_entry.sha256

            if size_ok and hash_ok:
                matched += 1
                diffs.append(
                    FileDiff(
                        path=path,
                        status="matched",
                        expected_size=exp_entry.size_bytes,
                        actual_size=act_entry.size_bytes,
                        expected_sha256=exp_entry.sha256,
                        actual_sha256=act_entry.sha256,
                        details="Cryptographic hash and byte size match perfectly",
                    )
                )
            elif not size_ok and not hash_ok:
                corrupted += 1
                size_mismatch += 1
                diffs.append(
                    FileDiff(
                        path=path,
                        status="corrupted",
                        expected_size=exp_entry.size_bytes,
                        actual_size=act_entry.size_bytes,
                        expected_sha256=exp_entry.sha256,
                        actual_sha256=act_entry.sha256,
                        details=f"Content and size mismatch: expected {exp_entry.size_bytes}B, found {act_entry.size_bytes}B",
                    )
                )
            elif not hash_ok:
                corrupted += 1
                diffs.append(
                    FileDiff(
                        path=path,
                        status="corrupted",
                        expected_size=exp_entry.size_bytes,
                        actual_size=act_entry.size_bytes,
                        expected_sha256=exp_entry.sha256,
                        actual_sha256=act_entry.sha256,
                        details="Silent data corruption: byte size matches but SHA-256 hash differs",
                    )
                )
            else:
                size_mismatch += 1
                diffs.append(
                    FileDiff(
                        path=path,
                        status="size_mismatch",
                        expected_size=exp_entry.size_bytes,
                        actual_size=act_entry.size_bytes,
                        expected_sha256=exp_entry.sha256,
                        actual_sha256=act_entry.sha256,
                        details=f"Size mismatch: expected {exp_entry.size_bytes}B, found {act_entry.size_bytes}B",
                    )
                )

    # 2. Check for unexpected extra files
    for path in sorted(actual_paths - expected_paths):
        act_entry = actual.entries[path]
        extra += 1
        diffs.append(
            FileDiff(
                path=path,
                status="extra",
                actual_size=act_entry.size_bytes,
                actual_sha256=act_entry.sha256,
                details="Unexpected file present in restore target not in pre-backup manifest",
            )
        )

    is_perfect = (
        matched == len(expected_paths)
        and missing == 0
        and extra == 0
        and corrupted == 0
        and size_mismatch == 0
    )

    if is_perfect:
        summary = f"PASSED: 100% byte-level recovery verified across {matched} files ({expected.total_bytes:,} bytes)."
    else:
        failures = []
        if missing > 0:
            failures.append(f"{missing} missing")
        if corrupted > 0:
            failures.append(f"{corrupted} corrupted")
        if size_mismatch > 0:
            failures.append(f"{size_mismatch} size mismatches")
        if extra > 0:
            failures.append(f"{extra} unexpected extra")
        summary = f"FAILED: Verification failed with {', '.join(failures)} out of {len(expected_paths)} expected files."

    evidence = {
        "expected_manifest_hash": expected.manifest_hash,
        "actual_manifest_hash": actual.manifest_hash,
        "expected_file_count": len(expected_paths),
        "actual_file_count": len(actual_paths),
        "matched_count": matched,
        "missing_count": missing,
        "extra_count": extra,
        "corrupted_count": corrupted,
        "size_mismatch_count": size_mismatch,
    }

    return ManifestComparisonResult(
        source_manifest_id=expected.manifest_id,
        restored_manifest_id=actual.manifest_id,
        is_perfect_match=is_perfect,
        total_expected=len(expected_paths),
        total_actual=len(actual_paths),
        matched_count=matched,
        missing_count=missing,
        extra_count=extra,
        corrupted_count=corrupted,
        size_mismatch_count=size_mismatch,
        diffs=diffs,
        summary=summary,
        evidence=evidence,
    )
