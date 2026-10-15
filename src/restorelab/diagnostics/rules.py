"""
RestoreLab Deterministic Diagnostic Rules
Versioned, rule-based diagnostic engine providing auditable root-cause analysis,
observable evidence mapping, and prescriptive remediation steps.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from restorelab.backup.base import (
    CommandExecutionResult,
    RepositoryStatus,
)
from restorelab.verification.manifest import ManifestComparisonResult

Certainty = Literal["confirmed", "likely", "unknown"]


class DiagnosticFinding(BaseModel):
    """Structured, explainable diagnostic finding."""

    rule_id: str
    rule_name: str
    version: str = "1.0"
    certainty: Certainty
    root_cause: str
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    recommended_checks: List[str] = Field(default_factory=list)
    suggested_remediation: str
    kb_reference_id: Optional[str] = None


class DiagnosticContext(BaseModel):
    """Observable facts and telemetry passed to the diagnostic rules engine."""

    command_result: Optional[CommandExecutionResult] = None
    manifest_diff: Optional[ManifestComparisonResult] = None
    repository_status: Optional[RepositoryStatus] = None
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    additional_facts: Dict[str, Any] = Field(default_factory=dict)


class BaseDiagnosticRule(ABC):
    """Contract for deterministic diagnostic rules."""

    rule_id: str
    rule_name: str
    version: str = "1.0"
    category: str

    @abstractmethod
    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        """Evaluate evidence against rule criteria."""
        pass


class ResticAuthFailedRule(BaseDiagnosticRule):
    rule_id = "RULE_RESTIC_AUTH_FAILED"
    rule_name = "Restic Authentication Failure"
    category = "authentication"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res or res.success:
            return None

        stderr_lower = res.stderr.lower()
        if (
            res.exit_code == 12
            or "wrong password" in stderr_lower
            or "keystore" in stderr_lower
            or "unable to open repository: password incorrect" in stderr_lower
        ):
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause="Invalid repository encryption credentials.",
                supporting_evidence=[
                    f"Command exit code: {res.exit_code}",
                    f"Standard error output contains credential rejection pattern: {res.stderr.strip()[:180]}",
                ],
                recommended_checks=[
                    "Inspect RESTIC_PASSWORD in .env configuration.",
                    "Verify if repository was initialized with a different passphrase.",
                ],
                suggested_remediation="Configure the correct RESTIC_PASSWORD in the .env file or environment settings.",
                kb_reference_id="KB-RESTIC-001",
            )
        return None


class RepoNotInitializedRule(BaseDiagnosticRule):
    rule_id = "RULE_REPO_NOT_INITIALIZED"
    rule_name = "Repository Uninitialized"
    category = "repository"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res or res.success:
            return None

        stderr_lower = res.stderr.lower()
        if (
            res.exit_code == 10
            or "is there a repository at the following location" in stderr_lower
            or "config file not found" in stderr_lower
        ):
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause="Restic repository directory exists but contains no initialized configuration file.",
                supporting_evidence=[
                    f"Restic exited with code {res.exit_code}",
                    "Detected missing config signature: 'config file not found' / repository inquiry",
                ],
                recommended_checks=[
                    "Check if 'restic init' has ever been run on this path.",
                    "Verify whether repository path points to the intended location.",
                ],
                suggested_remediation="Initialize the repository via 'Initialize Repository' in the Backup Lab or run 'restic init'.",
                kb_reference_id="KB-RESTIC-002",
            )
        return None


class SourceDirMissingRule(BaseDiagnosticRule):
    rule_id = "RULE_SOURCE_DIR_MISSING"
    rule_name = "Source Directory Missing"
    category = "filesystem"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        # Check explicit source path check
        if ctx.source_path and ctx.additional_facts.get("source_exists") is False:
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause=f"Specified backup source directory does not exist on disk: {ctx.source_path}",
                supporting_evidence=[
                    f"Target source path '{ctx.source_path}' does not resolve to an existing filesystem directory.",
                ],
                recommended_checks=[
                    "Confirm the configured source directory path in Settings.",
                    "Generate test lab data using 'Generate Sample Dataset'.",
                ],
                suggested_remediation="Create the source directory and populate it with lab data before initiating backup.",
                kb_reference_id="KB-FS-001",
            )

        res = ctx.command_result
        if res and not res.success:
            stderr_lower = res.stderr.lower()
            if "cannot find the path specified" in stderr_lower or "no such file or directory" in stderr_lower:
                return DiagnosticFinding(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    version=self.version,
                    certainty="likely",
                    root_cause="Backup source directory or an included path could not be located by the engine.",
                    supporting_evidence=[
                        f"Command error output: {res.stderr.strip()[:180]}",
                    ],
                    recommended_checks=["Verify path existence and filesystem permissions."],
                    suggested_remediation="Ensure the source directory exists and has read permissions.",
                    kb_reference_id="KB-FS-001",
                )
        return None


class RestoreSafetyViolationRule(BaseDiagnosticRule):
    rule_id = "RULE_RESTORE_SAFETY_VIOLATION"
    rule_name = "Restore Safety Containment Violation"
    category = "security"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        # Check additional facts or error message
        rejection_reason = ctx.additional_facts.get("safety_rejection_reason")
        if rejection_reason:
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause=f"Restore operation aborted: safety guard rejected destination path ({rejection_reason}).",
                supporting_evidence=[
                    f"Destination validation failure: {rejection_reason}",
                    f"Requested target path: {ctx.target_path or 'unspecified'}",
                ],
                recommended_checks=[
                    "Check configured lab restore boundaries (LAB_RESTORE_DIR).",
                    "Verify target path does not overlap live source data or root volume.",
                ],
                suggested_remediation="Direct recovery restores exclusively to an approved sandbox under ./data/lab_restore.",
                kb_reference_id="KB-SEC-001",
            )
        return None


class ManifestSilentCorruptionRule(BaseDiagnosticRule):
    rule_id = "RULE_MANIFEST_SILENT_CORRUPTION"
    rule_name = "Silent Data Corruption Detected"
    category = "integrity"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        diff = ctx.manifest_diff
        if not diff:
            return None

        if diff.corrupted_count > 0:
            corrupted_samples = [
                d.path for d in diff.diffs if d.status == "corrupted"
            ][:5]
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause=(
                    f"Silent data corruption confirmed across {diff.corrupted_count} restored files. "
                    "File bytes have been modified without size change, violating cryptographic SHA-256 integrity."
                ),
                supporting_evidence=[
                    f"Total corrupted files: {diff.corrupted_count}",
                    f"Sample corrupted files: {', '.join(corrupted_samples)}",
                    f"Pre-backup manifest hash: {diff.evidence.get('expected_manifest_hash')}",
                    f"Restored manifest hash: {diff.evidence.get('actual_manifest_hash')}",
                ],
                recommended_checks=[
                    "Execute deep repository payload check: 'restic check --read-data'.",
                    "Inspect storage medium for latent sector errors or file tampering.",
                ],
                suggested_remediation="Isolate corrupted snapshots and restore from the most recent verified healthy snapshot.",
                kb_reference_id="KB-CORRUPT-001",
            )
        return None


class ManifestMissingFilesRule(BaseDiagnosticRule):
    rule_id = "RULE_MANIFEST_MISSING_FILES"
    rule_name = "Incomplete Recovery — Missing Files"
    category = "integrity"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        diff = ctx.manifest_diff
        if not diff:
            return None

        if diff.missing_count > 0:
            missing_samples = [d.path for d in diff.diffs if d.status == "missing"][:5]
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause=f"Recovery verification incomplete: {diff.missing_count} files present in original manifest are missing from restore.",
                supporting_evidence=[
                    f"Missing file count: {diff.missing_count}",
                    f"Sample missing files: {', '.join(missing_samples)}",
                ],
                recommended_checks=[
                    "Check if exclusions or pattern filters omitted files during backup or restore.",
                    "Verify whether source files were locked by open processes during backup creation.",
                ],
                suggested_remediation="Check backup logs for skipped open files and verify snapshot contents via 'restic ls'.",
                kb_reference_id="KB-RECOVERY-001",
            )
        return None


class ManifestExtraFilesRule(BaseDiagnosticRule):
    rule_id = "RULE_MANIFEST_EXTRA_FILES"
    rule_name = "Unexpected Extra Files in Sandbox"
    category = "integrity"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        diff = ctx.manifest_diff
        if not diff:
            return None

        if diff.extra_count > 0:
            extra_samples = [d.path for d in diff.diffs if d.status == "extra"][:5]
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="likely",
                root_cause=f"Restored sandbox contains {diff.extra_count} files not present in the pre-backup manifest.",
                supporting_evidence=[
                    f"Extra file count: {diff.extra_count}",
                    f"Sample extra files: {', '.join(extra_samples)}",
                ],
                recommended_checks=[
                    "Verify whether restore destination directory was empty prior to restore.",
                    "Check if temporary OS or editor files were generated in the sandbox directory.",
                ],
                suggested_remediation="Ensure restore operations use a clean, empty target directory.",
                kb_reference_id="KB-RECOVERY-002",
            )
        return None


class ResticLockedRule(BaseDiagnosticRule):
    rule_id = "RULE_RESTIC_LOCKED"
    rule_name = "Repository Locked"
    category = "concurrency"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res or res.success:
            return None

        stderr_lower = res.stderr.lower()
        if res.exit_code == 11 or "unable to create lock" in stderr_lower or "repository is already locked" in stderr_lower:
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause="Repository is locked by another running operation or a previously crashed process left a stale lock.",
                supporting_evidence=[
                    f"Restic exit code: {res.exit_code}",
                    f"Stderr: {res.stderr.strip()[:180]}",
                ],
                recommended_checks=[
                    "Check for running restic processes in Task Manager.",
                    "Confirm whether a prior backup operation was forcefully terminated.",
                ],
                suggested_remediation="If no other backup operations are active, release the lock by running 'restic unlock'.",
                kb_reference_id="KB-LOCK-001",
            )
        return None


class CommandTimeoutRule(BaseDiagnosticRule):
    rule_id = "RULE_COMMAND_TIMEOUT"
    rule_name = "Operation Execution Timeout"
    category = "performance"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res:
            return None

        if res.timed_out or res.exit_code == 124:
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause=f"Subprocess exceeded allotted time budget ({res.duration_seconds}s).",
                supporting_evidence=[
                    f"Timed out flag: {res.timed_out}",
                    f"Duration before termination: {res.duration_seconds}s",
                ],
                recommended_checks=[
                    "Inspect disk I/O performance and network latency.",
                    "Verify whether source volume contains massive files exceeding expected throughput.",
                ],
                suggested_remediation="Increase COMMAND_TIMEOUT_SECONDS in settings or verify storage throughput.",
                kb_reference_id="KB-PERF-001",
            )
        return None


class MissingBinaryRule(BaseDiagnosticRule):
    rule_id = "RULE_MISSING_BINARY"
    rule_name = "Missing Backup Engine Executable"
    category = "environment"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res:
            return None

        if res.exit_code == 127 or "restic binary not found" in res.stderr.lower():
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause="Restic executable is not installed or not accessible at configured path.",
                supporting_evidence=[
                    f"Exit code: {res.exit_code}",
                    f"Stderr message: {res.stderr.strip()[:180]}",
                ],
                recommended_checks=[
                    "Check RESTIC_BINARY_PATH in .env or Settings.",
                    "Check if bin/restic.exe exists in the project workspace.",
                ],
                suggested_remediation="Run 'powershell scripts/download_restic.ps1' or configure RESTIC_BINARY_PATH.",
                kb_reference_id="KB-BIN-001",
            )
        return None


class IntegrityCheckFailedRule(BaseDiagnosticRule):
    rule_id = "RULE_INTEGRITY_CHECK_FAILED"
    rule_name = "Repository Integrity Check Failed"
    category = "integrity"

    def evaluate(self, ctx: DiagnosticContext) -> Optional[DiagnosticFinding]:
        res = ctx.command_result
        if not res or res.success:
            return None

        # Check if the command executed was 'check'
        if any("check" in c for c in res.command):
            return DiagnosticFinding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                version=self.version,
                certainty="confirmed",
                root_cause="Restic repository integrity check failed: detected corruption in index, snapshots, or packs.",
                supporting_evidence=[
                    f"Integrity check exit code: {res.exit_code}",
                    f"Error output: {res.stderr.strip()[:180]}",
                ],
                recommended_checks=[
                    "Run 'restic check --read-data' to isolate specific corrupted pack files.",
                    "Attempt index repair via 'restic rebuild-index'.",
                ],
                suggested_remediation="Rebuild the repository index or restore from an uncorrupted secondary backup repository.",
                kb_reference_id="KB-REPO-001",
            )
        return None


def get_default_diagnostic_rules() -> List[BaseDiagnosticRule]:
    """Instantiate standard suite of deterministic diagnostic rules."""
    return [
        MissingBinaryRule(),
        ResticAuthFailedRule(),
        RepoNotInitializedRule(),
        SourceDirMissingRule(),
        RestoreSafetyViolationRule(),
        ResticLockedRule(),
        CommandTimeoutRule(),
        ManifestSilentCorruptionRule(),
        ManifestMissingFilesRule(),
        ManifestExtraFilesRule(),
        IntegrityCheckFailedRule(),
    ]
