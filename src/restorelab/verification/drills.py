"""
RestoreLab Automated Recovery Drill Engine
Executes manual and automated recovery drill exercises into isolated sandboxes,
verifies cryptographic data recovery, evaluates RTO compliance, and safely purges drill fixtures.
"""

from __future__ import annotations

import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from restorelab.backup.base import BackupEngine
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.incidents.models import RecoveryDrillRecord
from restorelab.incidents.repository import IncidentRepository
from restorelab.verification.restore import verify_recovery

logger = setup_logging()


class RecoveryDrillRunner:
    """Orchestrates isolated recovery drills with RTO compliance validation."""

    def __init__(
        self,
        engine: BackupEngine,
        repository: IncidentRepository,
        settings: Optional[RestoreLabSettings] = None,
        diagnostic_engine: Optional[DiagnosticEngine] = None,
    ) -> None:
        self.engine = engine
        self.repository = repository
        self.settings = settings or get_settings()
        self.diagnostic_engine = diagnostic_engine or DiagnosticEngine()

    def run_drill(
        self,
        snapshot_id: Optional[str] = None,
        subfolder: Optional[str] = None,
        rto_target_seconds: float = 60.0,
        drill_type: Literal["manual", "scheduled"] = "manual",
        cleanup_after: bool = True,
    ) -> RecoveryDrillRecord:
        """
        Execute a single recovery drill against a snapshot.
        If snapshot_id is not specified, selects the latest available snapshot.
        """
        # 1. Resolve snapshot
        if not snapshot_id:
            snapshots = self.engine.list_snapshots()
            if not snapshots:
                raise ValueError("No snapshots found in repository to execute recovery drill.")
            snapshot_id = snapshots[0].id

        drill_id = f"DRILL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        start_time = time.monotonic()

        # 2. Allocate isolated sandbox path within lab restore bounds
        sandbox_target = self.settings.resolved_restore_dir / f"drill_{drill_id}"
        sandbox_target.mkdir(parents=True, exist_ok=True)

        status: Literal["SUCCESS", "FAILED", "INCONCLUSIVE"] = "SUCCESS"
        matched = 0
        corrupted = 0
        missing = 0
        extra = 0
        evidence_summary = ""

        try:
            report = verify_recovery(
                engine=self.engine,
                repository=self.repository,
                snapshot_id=snapshot_id,
                subfolder=subfolder,
                diagnostic_engine=self.diagnostic_engine,
            )

            if report.status == "PASSED":
                status = "SUCCESS"
                evidence_summary = "100% byte-level recovery verified against baseline manifest."
            elif report.status == "FAILED":
                status = "FAILED"
                evidence_summary = f"Recovery integrity check failed: {report.diagnostics_summary}"
            else:
                status = "INCONCLUSIVE"
                evidence_summary = f"Verification inconclusive: {report.diagnostics_summary}"

            if report.comparison_result:
                matched = report.comparison_result.matched_count
                corrupted = report.comparison_result.corrupted_count
                missing = report.comparison_result.missing_count
                extra = report.comparison_result.extra_count

        except Exception as e:
            logger.error(f"Recovery drill {drill_id} exception: {e}")
            status = "FAILED"
            evidence_summary = f"Drill error: {str(e)}"

        wall_duration = time.monotonic() - start_time
        reported_duration = 0.0
        if report:
            reported_duration = getattr(report, "restore_duration_seconds", 0.0) or getattr(report, "duration_seconds", 0.0)
        duration = max(wall_duration, reported_duration)
        rto_compliant = duration <= rto_target_seconds
        if not rto_compliant:
            evidence_summary = (
                f"{evidence_summary} [RTO SLA target exceeded: {duration:.2f}s > {rto_target_seconds:.1f}s]".strip()
            )


        # 3. Safe sandbox cleanup
        sandbox_cleaned = False
        if cleanup_after and sandbox_target.exists():
            try:
                shutil.rmtree(sandbox_target, ignore_errors=True)
                sandbox_cleaned = True
            except Exception as e:
                logger.warning(f"Failed to purge drill sandbox {sandbox_target}: {e}")

        # 4. Construct drill record
        drill_record = RecoveryDrillRecord(
            drill_id=drill_id,
            snapshot_id=snapshot_id,
            status=status,
            drill_type=drill_type,
            restore_target_path=str(sandbox_target),
            duration_seconds=round(duration, 2),
            rto_target_seconds=rto_target_seconds,
            rto_compliant=rto_compliant,
            matched_files=matched,
            corrupted_files=corrupted,
            missing_files=missing,
            extra_files=extra,
            evidence_summary=evidence_summary,
            sandbox_cleaned=sandbox_cleaned,
        )

        self.repository.record_recovery_drill(drill_record)
        return drill_record

    def run_all_drills(
        self,
        rto_target_seconds: float = 60.0,
    ) -> List[RecoveryDrillRecord]:
        """Execute automated recovery drills against all snapshots in repository."""
        snapshots = self.engine.list_snapshots()
        records: List[RecoveryDrillRecord] = []
        for s in snapshots:
            rec = self.run_drill(
                snapshot_id=s.id,
                rto_target_seconds=rto_target_seconds,
                drill_type="scheduled",
                cleanup_after=True,
            )
            records.append(rec)
        return records
