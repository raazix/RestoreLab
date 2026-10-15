"""
Unit tests for RestoreLab HTML & JSON Report Export Engine.
Validates report generation, cryptographic SHA-256 signatures, and format integrity.
"""

from __future__ import annotations

import hashlib
import json
import pytest

from restorelab.incidents.models import ReadinessAssessment, RecoveryDrillRecord
from restorelab.reporting.html_export import (
    export_drill_html,
    export_drill_json,
    export_readiness_html,
    export_readiness_json,
    export_verification_html,
)
from restorelab.verification.restore import RecoveryVerificationReport


def test_export_drill_html_signature():
    drill = RecoveryDrillRecord(
        drill_id="DRILL-20261015-TEST01",
        snapshot_id="abcdef123456",
        status="SUCCESS",
        drill_type="manual",
        restore_target_path="/lab/restore/drill_test",
        duration_seconds=2.45,
        rto_target_seconds=30.0,
        rto_compliant=True,
        matched_files=42,
        corrupted_files=0,
        missing_files=0,
        extra_files=0,
        evidence_summary="Perfect SHA-256 cryptographic match",
        sandbox_cleaned=True,
    )

    report = export_drill_html(drill)
    assert report.content_format == "html"
    assert "<!DOCTYPE html>" in report.content
    assert "RestoreLab / Recovery Drill Audit" in report.content
    assert drill.drill_id in report.content
    assert report.sha256_fingerprint is not None
    assert len(report.sha256_fingerprint) == 64


def test_export_drill_json():
    drill = RecoveryDrillRecord(
        drill_id="DRILL-JSON-TEST",
        snapshot_id="fedcba654321",
        status="SUCCESS",
        restore_target_path="/lab/restore/target",
        duration_seconds=1.2,
    )
    report = export_drill_json(drill)
    assert report.content_format == "json"
    parsed = json.loads(report.content)
    assert parsed["drill_id"] == "DRILL-JSON-TEST"
    assert parsed["snapshot_id"] == "fedcba654321"

    # Verify cryptographic signature matches payload
    expected_hash = hashlib.sha256(report.content.encode("utf-8")).hexdigest()
    assert report.sha256_fingerprint == expected_hash


def test_export_readiness_html():
    readiness = ReadinessAssessment(
        assessment_id="RDY-20261015-EX01",
        score=88,
        readiness_tier="OPTIMAL",
        coverage_ratio=0.75,
        tested_snapshots_count=3,
        total_eligible_snapshots=4,
        latest_snapshot_age_hours=2.5,
        rto_compliance_rate=1.0,
        average_restore_seconds=4.2,
        unresolved_incidents_count=0,
        successful_drills_count=3,
        failed_drills_count=0,
        metric_limitations=["Metrics reflect synthetic lab tests"],
    )

    report = export_readiness_html(readiness)
    assert report.content_format == "html"
    assert "Disaster Recovery Readiness Audit" in report.content
    assert "88 / 100" in report.content
    assert "75.0%" in report.content
    assert "Metrics reflect synthetic lab tests" in report.content


def test_export_verification_html():
    ver_report = RecoveryVerificationReport(
        snapshot_id="snap-test-verification",
        timestamp="2026-10-15T10:00:00Z",
        status="PASSED",
        original_manifest_id="MAN-ORIG",
        restored_manifest_id="MAN-REST",

        restore_target_path="/lab/restore/target",
        resolved_content_path="/lab/restore/target",
        duration_seconds=3.1,
        diagnostics_summary="Verification succeeded without checksum divergences",
    )
    report = export_verification_html(ver_report)
    assert report.content_format == "html"
    assert "Cryptographic Verification Audit Certificate" in report.content
    assert "snap-test-verification" in report.content
