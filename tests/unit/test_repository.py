"""Unit tests for the SQLite persistence layer and audit history."""

from pathlib import Path
import pytest
from restorelab.incidents.models import (
    BackupRunRecord,
    IncidentRecord,
    RestoreAttemptRecord,
)
from restorelab.incidents.repository import IncidentRepository
from restorelab.verification.manifest import generate_manifest


def test_repository_initialization(tmp_path: Path):
    db_file = tmp_path / "test_repo.db"
    repo = IncidentRepository(db_path=db_file)

    # Check that default seeded knowledge articles are present
    articles = repo.list_knowledge_articles()
    assert len(articles) >= 5
    assert any(a.article_id == "KB-RESTIC-001" for a in articles)
    assert any(a.article_id == "KB-CORRUPT-001" for a in articles)


def test_incident_persistence(tmp_path: Path):
    db_file = tmp_path / "test_inc.db"
    repo = IncidentRepository(db_path=db_file)

    inc = IncidentRecord(
        title="Test Outage: Missing Source Directory",
        status="open",
        severity="high",
        category="filesystem",
        symptoms=["Source path C:/missing not found", "Subprocess exit code 1"],
        raw_evidence={"exit_code": 1},
    )
    repo.save_incident(inc)

    retrieved = repo.get_incident(inc.incident_id)
    assert retrieved is not None
    assert retrieved.title == inc.title
    assert retrieved.status == "open"
    assert "Source path C:/missing not found" in retrieved.symptoms

    # Update resolution
    retrieved.status = "resolved"
    retrieved.verified_resolution = "Source path recreated and verified."
    repo.save_incident(retrieved)

    updated = repo.get_incident(inc.incident_id)
    assert updated.status == "resolved"
    assert updated.verified_resolution == "Source path recreated and verified."


def test_backup_and_restore_audit_persistence(tmp_path: Path):
    db_file = tmp_path / "test_audit.db"
    repo = IncidentRepository(db_path=db_file)

    b_run = BackupRunRecord(
        source_path="C:/data/source",
        snapshot_id="snap1234",
        status="success",
        total_files=42,
        total_bytes=10240,
        duration_seconds=1.25,
    )
    repo.save_backup_run(b_run)

    r_attempt = RestoreAttemptRecord(
        snapshot_id="snap1234",
        target_path="C:/data/restore",
        status="PASSED",
        matched_files=42,
        corrupted_files=0,
        missing_files=0,
        extra_files=0,
        duration_seconds=0.88,
    )
    repo.save_restore_attempt(r_attempt)

    runs = repo.list_backup_runs()
    attempts = repo.list_restore_attempts()

    assert len(runs) == 1
    assert runs[0].snapshot_id == "snap1234"
    assert len(attempts) == 1
    assert attempts[0].status == "PASSED"


def test_manifest_persistence(sample_dataset: Path, tmp_path: Path):
    db_file = tmp_path / "test_manifest.db"
    repo = IncidentRepository(db_path=db_file)

    manifest = generate_manifest(sample_dataset)
    repo.save_manifest(manifest)

    loaded = repo.get_manifest(manifest.manifest_id)
    assert loaded is not None
    assert loaded.manifest_hash == manifest.manifest_hash
    assert loaded.total_files == manifest.total_files
