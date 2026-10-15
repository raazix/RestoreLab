"""
RestoreLab Recovery Verification Orchestrator
Executes isolated restores and cryptographically verifies recovered data
against pre-backup baseline manifests.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field

from restorelab.backup.base import BackupEngine, CommandExecutionResult
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.verification.manifest import (
    Manifest,
    ManifestComparisonResult,
    compare_manifests,
    generate_manifest,
)

logger = setup_logging()

VerificationStatus = Literal["PASSED", "FAILED", "WARNING", "INCONCLUSIVE", "NOT_RUN"]


class RecoveryVerificationReport(BaseModel):
    """Full cryptographic verification report for a recovery test."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    snapshot_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: VerificationStatus
    original_manifest_id: str
    restored_manifest_id: Optional[str] = None
    restore_target_path: str
    resolved_content_path: str
    restore_duration_seconds: float = 0.0
    verification_duration_seconds: float = 0.0
    comparison_result: Optional[ManifestComparisonResult] = None
    command_result: Optional[CommandExecutionResult] = None
    diagnostics_summary: str = ""


def locate_restored_content_root(
    restore_target: Path,
    original_source: Path,
) -> Path:
    """
    Locates the actual root of the restored content inside the isolated restore target.
    
    Restic recreates the path structure under the restore target:
    - On Windows: target / drive_letter / path_components
      (e.g., C:\\data\\src -> target\\C\\data\\src)
    - On POSIX: target / path_components (e.g., /data/src -> target/data/src)
    """
    target = restore_target.resolve()
    orig = original_source.resolve()

    # Strategy 1: Check Windows drive layout
    if orig.drive:
        drive_letter = orig.drive.rstrip(":")
        rel_parts = orig.parts[1:]  # Skip drive anchor
        candidate = target.joinpath(drive_letter, *rel_parts)
        if candidate.is_dir():
            return candidate

    # Strategy 2: Check POSIX / standard relative parts
    if orig.is_absolute():
        rel_parts = [p for p in orig.parts if p not in (orig.anchor, "/", "\\")]
        candidate = target.joinpath(*rel_parts)
        if candidate.is_dir():
            return candidate

    # Strategy 3: Check immediate subdirectories or target itself
    subdirs = [d for d in target.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and subdirs[0].name.lower() in ("c", "d", "e", "f", "data", orig.name.lower()):
        # Walk down single-child directories
        curr = target
        while True:
            children = [c for c in curr.iterdir() if c.is_dir()]
            if len(children) == 1 and not list(curr.glob("*.*")):
                curr = children[0]
            else:
                break
        return curr

    return target


def verify_recovery(
    engine: BackupEngine,
    snapshot_id: str,
    original_manifest: Manifest,
    target_dir: Optional[Path | str] = None,
    settings: Optional[RestoreLabSettings] = None,
) -> RecoveryVerificationReport:
    """
    Perform an end-to-end recovery verification test:
    1. Allocate a timestamped isolated restore sandbox.
    2. Enforce strict destination safety checks.
    3. Execute restore using the backup engine.
    4. Locate the restored content tree.
    5. Generate a fresh cryptographic manifest for the restored files.
    6. Compare restored manifest against pre-backup original manifest.
    7. Synthesize an evidence-backed verification report.
    """
    conf = settings or get_settings()
    t0 = time.perf_counter()

    # Generate timestamped destination sandbox if not provided
    if target_dir:
        dest_path = Path(target_dir).resolve()
    else:
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest_path = conf.resolved_restore_dir / f"verify_{snapshot_id[:8]}_{timestamp_slug}"

    # Verify safety before doing anything
    is_safe, reason = conf.is_safe_restore_target(dest_path)
    if not is_safe:
        return RecoveryVerificationReport(
            snapshot_id=snapshot_id,
            status="FAILED",
            original_manifest_id=original_manifest.manifest_id,
            restore_target_path=str(dest_path),
            resolved_content_path="",
            restore_duration_seconds=0.0,
            verification_duration_seconds=round(time.perf_counter() - t0, 3),
            diagnostics_summary=f"Safety boundary rejection: {reason}",
        )

    # 1. Execute restore
    t_restore_start = time.perf_counter()
    orig_source_path = Path(original_manifest.root_path).resolve()
    if orig_source_path.drive:
        drive_clean = orig_source_path.drive.rstrip(":")
        subfolder_spec = f"/{drive_clean}/{'/'.join(orig_source_path.parts[1:])}"
    else:
        subfolder_spec = orig_source_path.as_posix()

    try:
        restore_result = engine.restore_snapshot(
            snapshot_id,
            dest_path,
            subfolder=subfolder_spec,
        )
        restore_duration = round(time.perf_counter() - t_restore_start, 3)
    except Exception as e:
        restore_duration = round(time.perf_counter() - t_restore_start, 3)
        return RecoveryVerificationReport(
            snapshot_id=snapshot_id,
            status="FAILED",
            original_manifest_id=original_manifest.manifest_id,
            restore_target_path=str(dest_path),
            resolved_content_path="",
            restore_duration_seconds=restore_duration,
            verification_duration_seconds=round(time.perf_counter() - t0, 3),
            diagnostics_summary=f"Restore execution failed: {type(e).__name__}: {str(e)}",
        )

    if not restore_result.execution_result.success:
        return RecoveryVerificationReport(
            snapshot_id=snapshot_id,
            status="FAILED",
            original_manifest_id=original_manifest.manifest_id,
            restore_target_path=str(dest_path),
            resolved_content_path="",
            restore_duration_seconds=restore_duration,
            verification_duration_seconds=round(time.perf_counter() - t0, 3),
            command_result=restore_result.execution_result,
            diagnostics_summary=(
                f"Restore command failed with exit code {restore_result.execution_result.exit_code}: "
                f"{restore_result.execution_result.stderr.strip()}"
            ),
        )

    # 2. Locate restored content root
    orig_source_path = Path(original_manifest.root_path)
    content_root = locate_restored_content_root(dest_path, orig_source_path)

    # 3. Generate restored manifest
    t_verify_start = time.perf_counter()
    try:
        restored_manifest = generate_manifest(
            content_root,
            max_bytes=conf.max_source_scan_mb * 1024 * 1024,
            max_files=conf.max_manifest_files,
        )
    except Exception as e:
        verify_duration = round(time.perf_counter() - t_verify_start, 3)
        return RecoveryVerificationReport(
            snapshot_id=snapshot_id,
            status="INCONCLUSIVE",
            original_manifest_id=original_manifest.manifest_id,
            restore_target_path=str(dest_path),
            resolved_content_path=str(content_root),
            restore_duration_seconds=restore_duration,
            verification_duration_seconds=verify_duration,
            command_result=restore_result.execution_result,
            diagnostics_summary=f"Failed to scan restored files for manifest generation: {str(e)}",
        )

    # 4. Compare manifests byte-for-byte
    comparison = compare_manifests(original_manifest, restored_manifest)
    verify_duration = round(time.perf_counter() - t_verify_start, 3)

    final_status: VerificationStatus = (
        "PASSED" if comparison.is_perfect_match else "FAILED"
    )

    return RecoveryVerificationReport(
        snapshot_id=snapshot_id,
        status=final_status,
        original_manifest_id=original_manifest.manifest_id,
        restored_manifest_id=restored_manifest.manifest_id,
        restore_target_path=str(dest_path),
        resolved_content_path=str(content_root),
        restore_duration_seconds=restore_duration,
        verification_duration_seconds=verify_duration,
        comparison_result=comparison,
        command_result=restore_result.execution_result,
        diagnostics_summary=comparison.summary,
    )
