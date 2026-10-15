"""
Unit tests for RestoreLab Disaster Recovery Readiness Analytics Engine.
Validates multi-factor score calculation, tier classification, and metric limitations.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from restorelab.incidents.models import RecoveryDrillRecord
from restorelab.incidents.repository import IncidentRepository


@pytest.fixture
def repo(tmp_path: Path):
    db_file = tmp_path / "readiness.db"
    r = IncidentRepository(db_path=db_file)
    r.init_database()
    return r


def test_empty_repository_readiness(repo):
    # With no drills and no backups
    assessment = repo.get_recovery_readiness()
    assert assessment.score >= 0
    assert assessment.readiness_tier in ("OPTIMAL", "ACCEPTABLE", "DEGRADED", "AT_RISK")
    assert len(assessment.metric_limitations) >= 3


def test_readiness_with_successful_drills(repo):
    # Add 3 successful drills with fast RTO
    for i in range(3):
        drill = RecoveryDrillRecord(
            drill_id=f"DRILL-SUCC-{i}",
            snapshot_id=f"snap-{i}",
            status="SUCCESS",
            duration_seconds=5.0,
            rto_target_seconds=30.0,
            rto_compliant=True,
            restore_target_path="/tmp/test",
        )
        repo.record_recovery_drill(drill)

    assessment = repo.get_recovery_readiness()
    assert assessment.successful_drills_count == 3
    assert assessment.failed_drills_count == 0
    assert assessment.rto_compliance_rate == 100.0
    assert assessment.average_restore_seconds == 5.0
    assert assessment.score >= 70


def test_readiness_with_failed_drills(repo):
    # Add 2 failed drills with duration exceeding RTO target
    for i in range(2):
        drill = RecoveryDrillRecord(
            drill_id=f"DRILL-FAIL-{i}",
            snapshot_id=f"snap-{i}",
            status="FAILED",
            duration_seconds=95.0,
            rto_target_seconds=60.0,
            rto_compliant=False,
            restore_target_path="/tmp/test",
            corrupted_files=3,
        )
        repo.record_recovery_drill(drill)

    assessment = repo.get_recovery_readiness(rto_target_seconds=60.0)
    assert assessment.failed_drills_count == 2
    assert assessment.rto_compliance_rate == 0.0
    assert assessment.readiness_tier in ("DEGRADED", "AT_RISK")

