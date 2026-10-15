"""Unit tests for the deterministic diagnostic engine and rules."""

import pytest
from restorelab.backup.base import CommandExecutionResult
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.diagnostics.rules import (
    DiagnosticContext,
    ResticAuthFailedRule,
    RepoNotInitializedRule,
    SourceDirMissingRule,
    RestoreSafetyViolationRule,
    ManifestSilentCorruptionRule,
    ManifestMissingFilesRule,
    CommandTimeoutRule,
    MissingBinaryRule,
)
from restorelab.verification.manifest import (
    FileDiff,
    ManifestComparisonResult,
)


def test_auth_failed_rule():
    rule = ResticAuthFailedRule()
    ctx = DiagnosticContext(
        command_result=CommandExecutionResult(
            command=["restic", "snapshots"],
            exit_code=12,
            stderr="Fatal: wrong password or no key found",
        )
    )
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_RESTIC_AUTH_FAILED"
    assert finding.kb_reference_id == "KB-RESTIC-001"


def test_repo_not_initialized_rule():
    rule = RepoNotInitializedRule()
    ctx = DiagnosticContext(
        command_result=CommandExecutionResult(
            command=["restic", "snapshots"],
            exit_code=10,
            stderr="Fatal: config file not found. Is there a repository at the following location?",
        )
    )
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_REPO_NOT_INITIALIZED"


def test_source_missing_rule():
    rule = SourceDirMissingRule()
    ctx = DiagnosticContext(
        source_path="C:/non_existent/data",
        additional_facts={"source_exists": False},
    )
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_SOURCE_DIR_MISSING"


def test_restore_safety_rule():
    rule = RestoreSafetyViolationRule()
    ctx = DiagnosticContext(
        target_path="C:/",
        additional_facts={"safety_rejection_reason": "Target cannot be a root drive"},
    )
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_RESTORE_SAFETY_VIOLATION"


def test_manifest_silent_corruption_rule():
    rule = ManifestSilentCorruptionRule()
    diff = ManifestComparisonResult(
        source_manifest_id="src_1",
        restored_manifest_id="rst_1",
        is_perfect_match=False,
        total_expected=1,
        total_actual=1,
        corrupted_count=1,
        diffs=[
            FileDiff(
                path="database.bin",
                status="corrupted",
                expected_sha256="aaa",
                actual_sha256="bbb",
            )
        ],
    )
    ctx = DiagnosticContext(manifest_diff=diff)
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_MANIFEST_SILENT_CORRUPTION"
    assert "Silent data corruption confirmed" in finding.root_cause


def test_command_timeout_rule():
    rule = CommandTimeoutRule()
    ctx = DiagnosticContext(
        command_result=CommandExecutionResult(
            command=["restic", "check"],
            exit_code=124,
            timed_out=True,
            duration_seconds=30.0,
        )
    )
    finding = rule.evaluate(ctx)
    assert finding is not None
    assert finding.certainty == "confirmed"
    assert finding.rule_id == "RULE_COMMAND_TIMEOUT"


def test_diagnostic_engine_unclassified_fallback():
    engine = DiagnosticEngine()
    ctx = DiagnosticContext(
        command_result=CommandExecutionResult(
            command=["restic", "unknown-cmd"],
            exit_code=99,
            stderr="Unusual internal engine panic line 42",
        )
    )
    findings = engine.diagnose(ctx)
    assert len(findings) == 1
    assert findings[0].certainty == "unknown"
    assert findings[0].rule_id == "RULE_UNCLASSIFIED_FAILURE"
