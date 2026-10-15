"""Unit tests for knowledge retrieval and Supermemory adapter privacy safeguards."""

from pathlib import Path
import pytest
from restorelab.config import RestoreLabSettings
from restorelab.incidents.models import IncidentRecord
from restorelab.incidents.repository import IncidentRepository
from restorelab.knowledge.sqlite_search import SQLiteKnowledgeProvider
from restorelab.knowledge.supermemory_adapter import SupermemoryAdapter


def test_sqlite_knowledge_search(tmp_path: Path):
    db_file = tmp_path / "test_kb.db"
    repo = IncidentRepository(db_path=db_file)
    provider = SQLiteKnowledgeProvider(repo)

    # Search for password failure keywords
    results = provider.search("password keystore auth")
    assert len(results) >= 1
    top = results[0]
    assert "KB-RESTIC-001" in top.item_id or "Password" in top.title
    assert "Matched" in top.match_reason


def test_sqlite_corruption_search(tmp_path: Path):
    db_file = tmp_path / "test_kb2.db"
    repo = IncidentRepository(db_path=db_file)
    provider = SQLiteKnowledgeProvider(repo)

    # Search for corruption keywords
    results = provider.search("silent corruption hash mismatch")
    assert len(results) >= 1
    assert any("KB-CORRUPT-001" == r.item_id for r in results)


def test_supermemory_disabled_by_default(tmp_path: Path):
    settings = RestoreLabSettings(
        supermemory_enabled=False,
        database_path=str(tmp_path / "test.db"),
    )
    adapter = SupermemoryAdapter(settings)
    assert adapter.is_available() is False
    assert "Disabled" in adapter.get_provider_name()

    # Search falls back gracefully without error
    results = adapter.search("password")
    assert len(results) >= 1


def test_supermemory_privacy_sanitization():
    settings = RestoreLabSettings(
        restic_password="SecretPassphrase99!",
    )
    adapter = SupermemoryAdapter(settings)

    inc = IncidentRecord(
        title="Failed backup of C:\\Users\\Administrator\\Documents\\payroll.xlsx",
        symptoms=["Auth failed with password SecretPassphrase99!"],
        category="security",
    )

    preview = adapter.preview_sanitized_payload(inc)

    # Validate credential scrubbing
    assert "SecretPassphrase99!" not in str(preview)
    assert "[REDACTED_PASSWORD]" in str(preview)
    # Validate local path scrubbing
    assert "C:\\Users\\Administrator" not in str(preview)
    assert "[LOCAL_PATH]" in str(preview)
