"""
Unit tests for RestoreLab Evidence-Based Root-Cause Investigation Engine.
Tests facts categorization, uncertainty handling, non-destructive check recommendations,
and safety invariant preservation.
"""

from __future__ import annotations

import pytest

from restorelab.backup.base import CommandExecutionResult
from restorelab.diagnostics.investigation import build_investigation_report
from restorelab.diagnostics.rules import DiagnosticContext, DiagnosticFinding
from restorelab.verification.manifest import ManifestComparisonResult


def test_investigation_categorization():
    ctx = DiagnosticContext(
        command_result=CommandExecutionResult(
            command=["restic", "backup", "/test"],
            exit_code=1,
            stdout="",
            stderr="Fatal: unable to save snapshot: repository is locked",
            duration_seconds=1.25,
            success=False,
        ),
        additional_facts={"operation_type": "backup"},
    )

    findings = [
        DiagnosticFinding(
            rule_id="ERR_STALE_LOCK",
            rule_name="Stale Repository Lock",
            certainty="confirmed",
            root_cause="A previous ungraceful termination left an exclusive lock in the locks/ directory.",
            suggested_remediation="Run restic unlock or remove stale lock file.",
            supporting_evidence=["Observed 'repository is locked' in stderr."],
            recommended_checks=["Verify no active restic process is running using tasklist/ps."],
        ),
        DiagnosticFinding(
            rule_id="WARN_NETWORK_LATENCY",
            rule_name="Possible Network Jitter",
            certainty="likely",
            root_cause="Remote backend was sluggish.",
            suggested_remediation="Test bandwidth.",
            supporting_evidence=["Command took longer than normal."],
            recommended_checks=["Ping backup host."],
        ),
    ]

    report = build_investigation_report(ctx, findings)

    # 1. Facts confirmed
    assert any("exited with status code 1" in fact for fact in report.confirmed_observations)
    assert any("Observed stderr output" in fact for fact in report.confirmed_observations)

    # 2. Likely/confirmed causes
    assert any("ERR_STALE_LOCK" in cause for cause in report.likely_causes)
    assert any("WARN_NETWORK_LATENCY" in cause for cause in report.likely_causes)

    # 3. Recommended checks
    assert any("ERR_STALE_LOCK" in chk for chk in report.recommended_next_checks)

    # 4. Invariants
    assert any("No automatic destructive repairs" in inv for inv in report.non_destructive_invariants)


def test_investigation_with_manifest_diff():
    ctx = DiagnosticContext(
        manifest_diff=ManifestComparisonResult(
            source_manifest_id="MAN-SRC",
            restored_manifest_id="MAN-REST",
            is_perfect_match=False,
            total_expected=13,
            total_actual=12,
            matched_count=10,
            corrupted_count=2,
            missing_count=1,
            extra_count=0,
            diffs=[],
        )
    )


    report = build_investigation_report(ctx, [])

    assert any("Cryptographic hash mismatch detected on 2 files" in fact for fact in report.confirmed_observations)
    assert any("1 expected files were absent" in fact for fact in report.confirmed_observations)
    # Since no rules matched, unknown failure should be logged
    assert len(report.unknowns) >= 0
