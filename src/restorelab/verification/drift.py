"""
RestoreLab Snapshot Integrity & Drift Analysis Engine
Compares snapshot states and baseline manifests to detect drift, volumetric anomalies,
and unusual modification surges with explainable forensic flags.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from restorelab.backup.base import BackupEngine
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.incidents.models import SnapshotDriftReport
from restorelab.incidents.repository import IncidentRepository
from restorelab.verification.manifest import FileEntry, Manifest

logger = setup_logging()


class SnapshotDriftAnalyzer:
    """Forensic engine analyzing content drift and volumetric swings between backup states."""

    def __init__(
        self,
        repository: IncidentRepository,
        engine: Optional[BackupEngine] = None,
        settings: Optional[RestoreLabSettings] = None,
    ) -> None:
        self.repository = repository
        self.engine = engine
        self.settings = settings or get_settings()

    def analyze_drift(
        self,
        base_manifest: Manifest,
        target_manifest: Manifest,
        base_snapshot_id: str = "baseline",
        target_snapshot_id: str = "target",
    ) -> SnapshotDriftReport:
        """
        Compare two manifests (or snapshots) and evaluate explainable anomaly flags.
        """
        base_entries = base_manifest.entries or {}
        target_entries = target_manifest.entries or {}

        added_files: List[str] = []
        removed_files: List[str] = []
        modified_files: List[str] = []
        unchanged_files: List[str] = []

        # Check all files in target vs base
        for path, target_entry in target_entries.items():
            if path not in base_entries:
                added_files.append(path)
            else:
                base_entry = base_entries[path]
                if (
                    base_entry.sha256 != target_entry.sha256
                    or base_entry.size_bytes != target_entry.size_bytes
                ):
                    modified_files.append(path)
                else:
                    unchanged_files.append(path)


        # Check files removed
        for path in base_entries:
            if path not in target_entries:
                removed_files.append(path)

        total_base_files = len(base_entries)
        total_target_files = len(target_entries)

        base_bytes = base_manifest.total_bytes
        target_bytes = target_manifest.total_bytes
        size_change_bytes = target_bytes - base_bytes
        percent_size_change = (
            round((size_change_bytes / base_bytes) * 100.0, 1) if base_bytes > 0 else 0.0
        )

        # Evaluate Anomaly Flags (Evidence-based, strictly avoiding false claims of definitive malware)
        anomaly_flags: List[str] = []
        anomaly_explanations: List[str] = []

        # 1. Mass Deletion Anomaly
        if total_base_files >= 5:
            deletion_ratio = len(removed_files) / total_base_files
            if deletion_ratio >= 0.40:
                flag = "ANOMALY_MASS_DELETION"
                anomaly_flags.append(flag)
                anomaly_explanations.append(
                    f"{flag}: {len(removed_files)} of {total_base_files} files ({round(deletion_ratio * 100, 1)}%) were removed between snapshots."
                )

        # 2. Rapid Mass Modification Anomaly
        if total_base_files >= 5:
            mod_ratio = len(modified_files) / total_base_files
            if mod_ratio >= 0.60:
                flag = "ANOMALY_MASS_MODIFICATION"
                anomaly_flags.append(flag)
                anomaly_explanations.append(
                    f"{flag}: {len(modified_files)} of {total_base_files} files ({round(mod_ratio * 100, 1)}%) were modified in a single interval."
                )

        # 3. Volumetric Swings
        if base_bytes > 1024 * 10:  # > 10 KB
            if percent_size_change >= 100.0:
                flag = "ANOMALY_VOLUMETRIC_SPIKE"
                anomaly_flags.append(flag)
                anomaly_explanations.append(
                    f"{flag}: Total dataset size expanded by {percent_size_change}% ({size_change_bytes} bytes added)."
                )
            elif percent_size_change <= -50.0:
                flag = "ANOMALY_VOLUMETRIC_COLLAPSE"
                anomaly_flags.append(flag)
                anomaly_explanations.append(
                    f"{flag}: Total dataset size dropped by {abs(percent_size_change)}% ({abs(size_change_bytes)} bytes reduced)."
                )

        # 4. Suspicious Extensions Check
        suspicious_extensions = {".locked", ".encrypted", ".crypto", ".pay", ".crypt"}
        flagged_exts = [p for p in added_files if Path(p).suffix.lower() in suspicious_extensions]
        if flagged_exts:
            flag = "ANOMALY_SUSPICIOUS_EXTENSION"
            anomaly_flags.append(flag)
            anomaly_explanations.append(
                f"{flag}: {len(flagged_exts)} new files with atypical extensions detected ({', '.join(flagged_exts[:3])}). Recommend manual offline triage."
            )

        return SnapshotDriftReport(
            base_snapshot_id=base_snapshot_id,
            target_snapshot_id=target_snapshot_id,
            added_files=added_files,
            removed_files=removed_files,
            modified_files=modified_files,
            unchanged_files=unchanged_files,
            size_change_bytes=size_change_bytes,
            percent_size_change=percent_size_change,
            total_base_files=total_base_files,
            total_target_files=total_target_files,
            anomaly_flags=anomaly_flags,
            anomaly_explanations=anomaly_explanations,
        )

    def compare_snapshots(
        self,
        base_snapshot_id: str,
        target_snapshot_id: str,
    ) -> SnapshotDriftReport:
        """Compare two snapshots using stored manifests or live source."""
        # 1. Resolve base manifest
        base_manifest = self.repository.get_manifest_for_snapshot(base_snapshot_id)
        if not base_manifest:
            base_manifest = self.repository.get_manifest(base_snapshot_id)

        # 2. Resolve target manifest
        if target_snapshot_id in ("current", "live", "source"):
            from restorelab.verification.manifest import generate_manifest
            target_manifest = generate_manifest(self.settings.resolved_source_dir)
        else:
            target_manifest = self.repository.get_manifest_for_snapshot(target_snapshot_id)
            if not target_manifest:
                target_manifest = self.repository.get_manifest(target_snapshot_id)

        if not base_manifest:
            raise ValueError(f"No manifest found for base snapshot/manifest: '{base_snapshot_id}'")
        if not target_manifest:
            raise ValueError(f"No manifest found for target snapshot/manifest: '{target_snapshot_id}'")

        return self.analyze_drift(
            base_manifest=base_manifest,
            target_manifest=target_manifest,
            base_snapshot_id=base_snapshot_id,
            target_snapshot_id=target_snapshot_id,
        )

