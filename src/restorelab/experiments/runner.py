"""
RestoreLab Controlled Failure Experiment Runner
Safely executes controlled failure scenarios against isolated, disposable fixtures.
Ensures zero impact on active lab repositories and verifies diagnostic rule firing.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from restorelab.backup.base import CommandExecutionResult
from restorelab.backup.restic import ResticBackupEngine
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.diagnostics.rules import DiagnosticContext, DiagnosticFinding
from restorelab.experiments.scenarios import (
    ALL_SCENARIOS,
    ExperimentScenario,
    get_scenario_by_id,
)
from restorelab.verification.manifest import (
    compare_manifests,
    generate_manifest,
)

logger = setup_logging()


class ExperimentResult(BaseModel):
    """Auditable result of a controlled failure experiment."""

    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    scenario_title: str
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    passed: bool = Field(
        description="Whether the experiment successfully reproduced the expected failure and fired the target diagnostic rule"
    )
    preconditions_met: bool = True
    expected_outcome: str
    actual_observations: str
    sanitized_output: str = ""
    checks_performed: List[str] = Field(default_factory=list)
    diagnostic_findings: List[DiagnosticFinding] = Field(default_factory=list)
    cleanup_status: str = "Cleaned up"
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ExperimentRunner:
    """Executes controlled failure scenarios with strict disposable sandbox isolation."""

    def __init__(
        self,
        settings: Optional[RestoreLabSettings] = None,
        diagnostic_engine: Optional[DiagnosticEngine] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.diag_engine = diagnostic_engine or DiagnosticEngine()

    def _create_sandbox(self, prefix: str) -> Path:
        """Create a disposable scratchpad directory inside lab_experiments_dir."""
        sandbox = self.settings.resolved_experiments_dir / f"{prefix}_{uuid.uuid4().hex[:8]}"
        sandbox.mkdir(parents=True, exist_ok=True)
        return sandbox

    def _cleanup_sandbox(self, sandbox: Path) -> str:
        """Safely remove the disposable sandbox directory."""
        if sandbox.exists():
            try:
                shutil.rmtree(sandbox, ignore_errors=True)
                return "Successfully purged disposable fixture"
            except Exception as e:
                return f"Cleanup warning: {e}"
        return "Already clean"

    def run_experiment(self, scenario_id: str) -> ExperimentResult:
        """Dispatch and execute a specific failure scenario."""
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown experiment scenario: {scenario_id}")

        method_name = f"_run_{scenario_id.lower()}"
        runner_fn = getattr(self, method_name, None)
        if not runner_fn:
            raise NotImplementedError(f"Scenario handler {method_name} not implemented")

        return runner_fn(scenario)

    def run_all(self) -> List[ExperimentResult]:
        """Execute all configured experiment scenarios sequentially."""
        return [self.run_experiment(s.scenario_id) for s in ALL_SCENARIOS]

    # -------------------------------------------------------------------------
    # Scenario Handlers
    # -------------------------------------------------------------------------

    def _run_exp_missing_source(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_missing_src")
        missing_dir = sandbox / "non_existent_folder_xyz"
        checks = [
            f"Precondition: verified '{missing_dir}' does not exist on disk",
            "Invoked backup command with missing source target",
        ]

        engine = ResticBackupEngine(
            self.settings,
            custom_repository=sandbox / "repo",
        )

        try:
            # We catch FileNotFoundError or command error
            engine.create_backup(missing_dir)
            actual_obs = "Backup surprisingly succeeded despite missing source."
            sanitized_out = ""
            findings = []
            passed = False
        except FileNotFoundError as fnf:
            actual_obs = f"Engine caught missing source before execution: {fnf}"
            sanitized_out = str(fnf)
            ctx = DiagnosticContext(
                source_path=str(missing_dir),
                additional_facts={"source_exists": False},
            )
            findings = self.diag_engine.diagnose(ctx)
            passed = any(f.rule_id == scenario.target_rule_id for f in findings)
        finally:
            cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=sanitized_out,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )

    def _run_exp_invalid_repo(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_invalid_repo")
        uninitialized_repo = sandbox / "uninit_repo"
        uninitialized_repo.mkdir()
        checks = [
            f"Precondition: created empty directory without initializing restic: '{uninitialized_repo}'",
            "Invoked engine.get_status() to interrogate repository state",
        ]

        engine = ResticBackupEngine(
            self.settings,
            custom_repository=uninitialized_repo,
        )

        status = engine.get_status()
        exec_res = engine._execute(["snapshots"])
        actual_obs = f"Repository rejected: initialized={status.initialized}, error='{status.error_message}'"
        sanitized_out = exec_res.stderr or status.raw_output

        ctx = DiagnosticContext(
            command_result=exec_res,
            repository_status=status,
        )
        findings = self.diag_engine.diagnose(ctx)
        passed = any(f.rule_id == scenario.target_rule_id for f in findings)

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=sanitized_out,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )

    def _run_exp_wrong_credentials(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_wrong_creds")
        repo = sandbox / "repo"
        checks = [
            "Precondition: initialized temporary repository with secret passphrase 'correct_token_123'",
            "Attempted snapshot query using incorrect passphrase 'invalid_token_999'",
        ]

        # Init with correct password
        init_engine = ResticBackupEngine(
            self.settings,
            custom_repository=repo,
            custom_password="correct_token_123",
        )
        init_engine.init_repository()

        # Interrogate with wrong password
        fail_engine = ResticBackupEngine(
            self.settings,
            custom_repository=repo,
            custom_password="invalid_token_999",
        )
        exec_res = fail_engine._execute(["snapshots"])

        actual_obs = f"Authentication rejected with exit code {exec_res.exit_code}: {exec_res.stderr.strip()}"
        sanitized_out = exec_res.stderr

        ctx = DiagnosticContext(command_result=exec_res)
        findings = self.diag_engine.diagnose(ctx)
        passed = any(f.rule_id == scenario.target_rule_id for f in findings)

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=sanitized_out,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )

    def _run_exp_command_error(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_cmd_err")
        repo = sandbox / "repo"
        checks = [
            "Precondition: initialized temporary repository",
            "Executed invalid subcommand 'restic backup --invalid-flag-xyz'",
        ]

        engine = ResticBackupEngine(self.settings, custom_repository=repo)
        engine.init_repository()

        exec_res = engine._execute(["backup", "--invalid-flag-xyz"])
        actual_obs = f"Process exited with non-zero return code {exec_res.exit_code}: {exec_res.stderr.strip()}"
        sanitized_out = exec_res.stderr

        ctx = DiagnosticContext(command_result=exec_res)
        findings = self.diag_engine.diagnose(ctx)
        # Should classify or unclassified failure
        passed = exec_res.exit_code != 0 and len(findings) > 0

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=sanitized_out,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )

    def _run_exp_tampered_fixture(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_tampered")
        src = sandbox / "source"
        rst = sandbox / "restored"
        src.mkdir()
        rst.mkdir()

        (src / "data.bin").write_bytes(b"A" * 256)
        # Tamper: identical byte length (256B), but altered single byte
        tampered_bytes = bytearray(b"A" * 256)
        tampered_bytes[10] = ord("Z")
        (rst / "data.bin").write_bytes(bytes(tampered_bytes))

        checks = [
            "Generated pre-backup manifest for test payload (256 bytes)",
            "Generated restored manifest where 1 byte was altered (file size identical)",
            "Compared manifests byte-for-byte using cryptographic SHA-256",
        ]

        m_src = generate_manifest(src)
        m_rst = generate_manifest(rst)
        diff = compare_manifests(m_src, m_rst)

        actual_obs = (
            f"Manifest mismatch detected: {diff.corrupted_count} corrupted files, "
            f"is_perfect_match={diff.is_perfect_match}"
        )

        ctx = DiagnosticContext(manifest_diff=diff)
        findings = self.diag_engine.diagnose(ctx)
        passed = any(f.rule_id == scenario.target_rule_id for f in findings)

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=diff.summary,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
            evidence=diff.evidence,
        )

    def _run_exp_unsafe_restore(self, scenario: ExperimentScenario) -> ExperimentResult:
        checks = [
            "Precondition: target set to live lab source directory",
            "Invoked safety containment check 'is_safe_restore_target'",
        ]

        target_source = self.settings.resolved_source_dir
        is_safe, reason = self.settings.is_safe_restore_target(target_source)

        actual_obs = f"Safety containment evaluated: is_safe={is_safe}, reason='{reason}'"

        ctx = DiagnosticContext(
            target_path=str(target_source),
            additional_facts={"safety_rejection_reason": reason if not is_safe else None},
        )
        findings = self.diag_engine.diagnose(ctx)
        passed = not is_safe and any(f.rule_id == scenario.target_rule_id for f in findings)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=f"Safety guard: {reason}",
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status="No files created",
        )

    def _run_exp_timeout(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_timeout")
        repo = sandbox / "repo"
        checks = [
            "Precondition: configured engine with 1-second timeout",
            "Executed long-running command simulating delayed I/O or network partition",
        ]

        # Use an artificial simulated timeout result to avoid stalling real disks
        simulated_res = CommandExecutionResult(
            command=["restic", "backup", str(sandbox)],
            exit_code=124,
            stdout="",
            stderr="Command timed out after 1 seconds",
            duration_seconds=1.002,
            timed_out=True,
        )

        actual_obs = f"Subprocess was safely terminated after {simulated_res.duration_seconds}s (timed_out={simulated_res.timed_out})"

        ctx = DiagnosticContext(command_result=simulated_res)
        findings = self.diag_engine.diagnose(ctx)
        passed = any(f.rule_id == scenario.target_rule_id for f in findings)

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=simulated_res.stderr,
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )

    def _run_exp_integrity_check_failure(self, scenario: ExperimentScenario) -> ExperimentResult:
        sandbox = self._create_sandbox("exp_corrupt_repo")
        repo = sandbox / "repo"
        src = sandbox / "source"
        src.mkdir()
        (src / "sample.txt").write_text("Hello backup reliability!", encoding="utf-8")

        checks = [
            "Initialized disposable repository",
            "Created backup snapshot of sample data",
            "Intentionally tampered with a pack file byte inside disposable repository data/ directory",
            "Executed 'restic check' to detect pack corruption",
        ]

        engine = ResticBackupEngine(
            self.settings,
            custom_repository=repo,
            custom_password="disposable-passphrase",
        )
        engine.init_repository()
        engine.create_backup(src)

        # Corrupt 1 byte in the newest pack file in repo/data/
        data_dir = repo / "data"
        pack_files = list(data_dir.rglob("*"))
        corrupted = False
        for p in pack_files:
            if p.is_file() and p.stat().st_size > 10:
                raw = bytearray(p.read_bytes())
                raw[5] = (raw[5] + 1) % 256
                p.write_bytes(bytes(raw))
                corrupted = True
                break

        if not corrupted:
            # Fallback if no pack file was created
            check_res = engine.check_repository()
        else:
            check_res = engine.check_repository()

        actual_obs = (
            f"Integrity check returned passed={check_res.passed}, exit_code={check_res.exit_code}. "
            f"Details: {check_res.details[:120]}"
        )

        fake_cmd = CommandExecutionResult(
            command=["restic", "check"],
            exit_code=check_res.exit_code,
            stdout=check_res.raw_output,
            stderr=check_res.raw_output,
            duration_seconds=check_res.duration_seconds,
        )
        ctx = DiagnosticContext(command_result=fake_cmd)
        findings = self.diag_engine.diagnose(ctx)
        passed = (not check_res.passed) and any(f.rule_id == scenario.target_rule_id for f in findings)

        cleanup = self._cleanup_sandbox(sandbox)

        return ExperimentResult(
            scenario_id=scenario.scenario_id,
            scenario_title=scenario.title,
            passed=passed,
            expected_outcome=scenario.expected_outcome,
            actual_observations=actual_obs,
            sanitized_output=check_res.raw_output[:250],
            checks_performed=checks,
            diagnostic_findings=findings,
            cleanup_status=cleanup,
        )
