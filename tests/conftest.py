"""Pytest fixtures for RestoreLab test suite."""

import os
import sys
from pathlib import Path
import pytest

# Ensure src is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from restorelab.config import RestoreLabSettings, get_settings


@pytest.fixture
def temp_lab_env(tmp_path: Path):
    """Provides an isolated environment for testing with custom temp directories."""
    repo_dir = tmp_path / "repo"
    source_dir = tmp_path / "source"
    restore_dir = tmp_path / "restore"
    exp_dir = tmp_path / "experiments"
    db_file = tmp_path / "test.db"

    repo_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    restore_dir.mkdir(parents=True)
    exp_dir.mkdir(parents=True)

    settings = RestoreLabSettings(
        restic_repository=str(repo_dir),
        restic_password="test-secret-password-12345",
        lab_source_dir=str(source_dir),
        lab_restore_dir=str(restore_dir),
        lab_experiments_dir=str(exp_dir),
        database_path=str(db_file),
        command_timeout_seconds=30,
        max_source_scan_mb=50,
        max_manifest_files=500,
    )
    return settings


@pytest.fixture
def sample_dataset(tmp_path: Path):
    """Creates a sample nested dataset for backup and manifest tests."""
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True)

    # File 1: Top-level text
    (dataset_dir / "system.conf").write_text("server_port=8080\nthreads=4\n", encoding="utf-8")

    # File 2: Nested markdown
    docs_dir = dataset_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "readme.md").write_text("# Test Docs\nOperational recovery notes.\n", encoding="utf-8")

    # File 3: Binary-like data
    data_dir = dataset_dir / "data"
    data_dir.mkdir()
    (data_dir / "sample.bin").write_bytes(bytes([i % 256 for i in range(1024)]))

    return dataset_dir
