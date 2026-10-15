"""
Unit tests for RestoreLab Recovery Drill Engine
Verifies isolated sandbox restores, RTO calculation, and safe artifact cleanup.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from restorelab.backup.base import CommandExecutionResult, SnapshotInfo
from restorelab.config import RestoreLabSettings
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.incidents.models import RecoveryDrillRecord
from restorelab.incidents.repository import IncidentRepository
from restorelab.verification.drills import RecoveryDrillRunner
from restorelab.verification.manifest import Manifest
from restorelab.verification.restore import RecoveryVerificationReport


@pytest.fixture
def temp_env(tmp_path: Path):
    db_path = tmp_path / "test.db"
    repo = IncidentRepository(db_path=db_path)
    repo.init_database()

    settings = RestoreLabSettings(
        repository_path=tmp_path / "repo",
        database_path=str(db_path),
        lab_source=tmp_path / "source",
        lab_restore=tmp_path / "restore",
        lab_experiments=tmp_path / "experiments",
        restic_password="test-password",
    )

    settings.ensure_directories()
    return repo, settings


def test_recovery_drill_success(temp_env):
    repo, settings = temp_env

    mock_engine = MagicMock()
    mock_engine.list_snapshots.return_value = [
        SnapshotInfo(
            id="snap12345678",
            full_id="snap12345678abcdef0123456789abcdef0123456789",
            time="2026-10-15T12:00:00Z",
            paths=["/lab/source"],
            tags=["lab"],
        )

    ]

    mock_report = RecoveryVerificationReport(
        snapshot_id="snap12345678",
        timestamp="2026-10-15T12:05:00Z",
        status="PASSED",
        original_manifest_id="MAN-001",

        restored_manifest_id="MAN-002",
        restore_target_path=str(settings.resolved_restore_dir / "drill_test"),
        resolved_content_path=str(settings.resolved_restore_dir / "drill_test"),
        restore_duration_seconds=3.5,
        diagnostics_summary="Byte-for-byte SHA-256 match",
    )



    with patch("restorelab.verification.drills.verify_recovery", return_value=mock_report):
        runner = RecoveryDrillRunner(
            engine=mock_engine,
            repository=repo,
            settings=settings,
            diagnostic_engine=DiagnosticEngine(),
        )

        drill = runner.run_drill(
            snapshot_id="snap12345678",
            rto_target_seconds=10.0,
            drill_type="manual",
            cleanup_after=True,
        )

        assert drill.drill_id.startswith("DRILL-")
        assert drill.snapshot_id == "snap12345678"
        assert drill.status == "SUCCESS"
        assert drill.rto_compliant is True
        assert drill.sandbox_cleaned is True

        # Verify persisted in database
        persisted = repo.list_recovery_drills()
        assert len(persisted) == 1
        assert persisted[0].drill_id == drill.drill_id


def test_recovery_drill_rto_breached(temp_env):
    repo, settings = temp_env

    mock_engine = MagicMock()
    mock_engine.list_snapshots.return_value = [
        SnapshotInfo(
            id="snap99999999",
            full_id="snap99999999abcdef0123456789abcdef0123456789",
            time="2026-10-15T12:00:00Z",
            paths=["/lab/source"],
            tags=["lab"],
        )
    ]

    mock_report = RecoveryVerificationReport(
        snapshot_id="snap99999999",
        timestamp="2026-10-15T12:05:00Z",
        status="PASSED",
        original_manifest_id="MAN-001",
        restored_manifest_id="MAN-002",

        restore_target_path=str(settings.resolved_restore_dir / "drill_test2"),
        resolved_content_path=str(settings.resolved_restore_dir / "drill_test2"),
        restore_duration_seconds=15.0,
        diagnostics_summary="Restore took 15 seconds",
    )



    with patch("restorelab.verification.drills.verify_recovery", return_value=mock_report):
        runner = RecoveryDrillRunner(
            engine=mock_engine,
            repository=repo,
            settings=settings,
        )

        drill = runner.run_drill(
            snapshot_id="snap99999999",
            rto_target_seconds=5.0,  # 5s target vs 15s restore
            drill_type="scheduled",
            cleanup_after=True,
        )

        assert drill.rto_compliant is False
        assert drill.status == "SUCCESS"
        assert "SLA target exceeded" in drill.evidence_summary
