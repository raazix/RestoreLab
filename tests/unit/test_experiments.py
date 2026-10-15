"""Unit tests for controlled failure experiment scenarios."""

from pathlib import Path
import pytest
from restorelab.config import RestoreLabSettings
from restorelab.experiments.runner import ExperimentRunner
from restorelab.experiments.scenarios import ALL_SCENARIOS


def test_scenario_definitions():
    """Ensure all required failure scenarios are registered."""
    expected_ids = [
        "EXP_MISSING_SOURCE",
        "EXP_INVALID_REPO",
        "EXP_WRONG_CREDENTIALS",
        "EXP_COMMAND_ERROR",
        "EXP_TAMPERED_FIXTURE",
        "EXP_UNSAFE_RESTORE",
        "EXP_TIMEOUT",
        "EXP_INTEGRITY_CHECK_FAILURE",
    ]
    registered = [s.scenario_id for s in ALL_SCENARIOS]
    for eid in expected_ids:
        assert eid in registered


def test_exp_missing_source(temp_lab_env: RestoreLabSettings):
    runner = ExperimentRunner(temp_lab_env)
    res = runner.run_experiment("EXP_MISSING_SOURCE")
    assert res.passed is True
    assert any(f.rule_id == "RULE_SOURCE_DIR_MISSING" for f in res.diagnostic_findings)


def test_exp_invalid_repo(temp_lab_env: RestoreLabSettings):
    runner = ExperimentRunner(temp_lab_env)
    res = runner.run_experiment("EXP_INVALID_REPO")
    assert res.passed is True
    assert any(f.rule_id == "RULE_REPO_NOT_INITIALIZED" for f in res.diagnostic_findings)


def test_exp_tampered_fixture(temp_lab_env: RestoreLabSettings):
    runner = ExperimentRunner(temp_lab_env)
    res = runner.run_experiment("EXP_TAMPERED_FIXTURE")
    assert res.passed is True
    assert any(f.rule_id == "RULE_MANIFEST_SILENT_CORRUPTION" for f in res.diagnostic_findings)


def test_exp_unsafe_restore(temp_lab_env: RestoreLabSettings):
    runner = ExperimentRunner(temp_lab_env)
    res = runner.run_experiment("EXP_UNSAFE_RESTORE")
    assert res.passed is True
    assert any(f.rule_id == "RULE_RESTORE_SAFETY_VIOLATION" for f in res.diagnostic_findings)


def test_exp_timeout(temp_lab_env: RestoreLabSettings):
    runner = ExperimentRunner(temp_lab_env)
    res = runner.run_experiment("EXP_TIMEOUT")
    assert res.passed is True
    assert any(f.rule_id == "RULE_COMMAND_TIMEOUT" for f in res.diagnostic_findings)
