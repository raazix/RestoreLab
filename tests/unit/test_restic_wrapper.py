"""Unit tests for Restic CLI wrapper and safety boundaries."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from restorelab.backup.restic import ResticBackupEngine
from restorelab.config import RestoreLabSettings


def test_missing_binary_handling(tmp_path: Path):
    """Verify engine returns exit code 127 when binary is absent."""
    non_existent = tmp_path / "bin" / "does_not_exist_restic.exe"
    settings = RestoreLabSettings(
        restic_binary_path=str(non_existent),
        restic_repository=str(tmp_path / "repo"),
    )
    engine = ResticBackupEngine(settings, custom_binary_path=non_existent)
    res = engine.init_repository()

    assert res.exit_code == 127
    assert "Restic binary not found" in res.stderr
    assert not res.success


def test_safe_restore_target_rejection(tmp_path: Path):
    """Verify that unsafe destination targets are rejected before subprocess execution."""
    repo = tmp_path / "repo"
    source = tmp_path / "source"
    restore_sandbox = tmp_path / "restore"
    settings = RestoreLabSettings(
        restic_repository=str(repo),
        lab_source_dir=str(source),
        lab_restore_dir=str(restore_sandbox),
    )
    engine = ResticBackupEngine(settings)

    # Attempting to restore directly over the source directory
    with pytest.raises(ValueError, match="Unsafe restore destination rejected"):
        engine.restore_snapshot("dummy_snap", source)

    # Attempting to restore directly into the repository directory
    with pytest.raises(ValueError, match="Unsafe restore destination rejected"):
        engine.restore_snapshot("dummy_snap", repo)


def test_credential_sanitization():
    """Verify passwords are scrubbed from outputs."""
    settings = RestoreLabSettings(
        restic_password="SuperSecretPassword99!",
    )
    engine = ResticBackupEngine(settings)

    raw_text = "Error: password SuperSecretPassword99! is invalid."
    sanitized = settings.sanitize_text(raw_text)

    assert "SuperSecretPassword99!" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
