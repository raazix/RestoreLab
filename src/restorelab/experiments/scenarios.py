"""
RestoreLab Controlled Failure Experiment Scenarios
Pre-defined, reproducible failure scenarios exercising realistic backup and recovery defects
against disposable fixtures without risking active repositories.
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class ExperimentScenario(BaseModel):
    """Metadata and definition of a reproducible failure experiment."""

    scenario_id: str
    title: str
    description: str
    preconditions: List[str] = Field(default_factory=list)
    expected_outcome: str
    target_rule_id: str


ALL_SCENARIOS: List[ExperimentScenario] = [
    ExperimentScenario(
        scenario_id="EXP_MISSING_SOURCE",
        title="Missing Source Directory",
        description="Attempts to execute a backup operation against a non-existent or moved source folder.",
        preconditions=[
            "Configure backup source path to a non-existent filesystem directory.",
            "Confirm directory does not exist prior to invocation.",
        ],
        expected_outcome="Backup engine aborts and reports missing source path.",
        target_rule_id="RULE_SOURCE_DIR_MISSING",
    ),
    ExperimentScenario(
        scenario_id="EXP_INVALID_REPO",
        title="Uninitialized / Invalid Repository Path",
        description="Attempts repository operations against an uninitialized directory lacking restic metadata.",
        preconditions=[
            "Allocate a fresh, empty directory without running 'restic init'.",
            "Configure backup engine to target this empty directory.",
        ],
        expected_outcome="Operation fails with exit code 10 and 'config file not found' / repository inquiry.",
        target_rule_id="RULE_REPO_NOT_INITIALIZED",
    ),
    ExperimentScenario(
        scenario_id="EXP_WRONG_CREDENTIALS",
        title="Incorrect Repository Passphrase",
        description="Attempts to access a valid encrypted repository using an invalid decryption key.",
        preconditions=[
            "Initialize an isolated disposable repository with a known passphrase.",
            "Attempt snapshot interrogation using an intentionally incorrect passphrase.",
        ],
        expected_outcome="Operation rejected with authentication failure (exit code 12 / wrong password).",
        target_rule_id="RULE_RESTIC_AUTH_FAILED",
    ),
    ExperimentScenario(
        scenario_id="EXP_COMMAND_ERROR",
        title="Backup Command Error on Unreadable Files",
        description="Exercises backup error handling when encountering inaccessible or locked items.",
        preconditions=[
            "Create a test fixture with locked or restricted attributes.",
            "Attempt backup scan.",
        ],
        expected_outcome="Engine captures non-zero return code and surfaces diagnostic logs.",
        target_rule_id="RULE_SOURCE_DIR_MISSING",
    ),
    ExperimentScenario(
        scenario_id="EXP_TAMPERED_FIXTURE",
        title="Silent Data Corruption in Restored Content",
        description="Simulates bit rot in recovered files where file size remains unchanged but SHA-256 changes.",
        preconditions=[
            "Generate pre-backup test dataset and compute deterministic SHA-256 manifest.",
            "Create an isolated restore target containing 1 tampered byte in data payload.",
        ],
        expected_outcome="Manifest comparison flags corruption: identical byte size, differing cryptographic hash.",
        target_rule_id="RULE_MANIFEST_SILENT_CORRUPTION",
    ),
    ExperimentScenario(
        scenario_id="EXP_UNSAFE_RESTORE",
        title="Restoration Safety Boundary Violation",
        description="Attempts to execute a restore targeting an unauthorized path (e.g. source directory or drive root).",
        preconditions=[
            "Specify a restore target that overlaps the live source directory.",
        ],
        expected_outcome="Pre-execution safety guard strictly rejects target before executing subprocess.",
        target_rule_id="RULE_RESTORE_SAFETY_VIOLATION",
    ),
    ExperimentScenario(
        scenario_id="EXP_TIMEOUT",
        title="Subprocess Execution Timeout",
        description="Tests graceful process termination and state capture when an operation exceeds its time budget.",
        preconditions=[
            "Configure a tight execution timeout limit.",
            "Invoke a command that exceeds the timeout limit.",
        ],
        expected_outcome="Subprocess terminates with timed_out=True and exit code 124.",
        target_rule_id="RULE_COMMAND_TIMEOUT",
    ),
    ExperimentScenario(
        scenario_id="EXP_INTEGRITY_CHECK_FAILURE",
        title="Repository Integrity Check Failure",
        description="Validates detection of physical pack corruption in a disposable lab repository.",
        preconditions=[
            "Initialize a disposable temporary repository and back up sample data.",
            "In the disposable repository only, tamper with 1 byte of a pack file.",
            "Execute 'restic check'.",
        ],
        expected_outcome="Repository check returns failure, exposing corrupted pack hash.",
        target_rule_id="RULE_INTEGRITY_CHECK_FAILED",
    ),
]


def get_scenario_by_id(scenario_id: str) -> Optional[ExperimentScenario]:
    """Retrieve scenario definition by ID."""
    for s in ALL_SCENARIOS:
        if s.scenario_id == scenario_id:
            return s
    return None
