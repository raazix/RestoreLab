"""Integration tests for genuine Restic backup, restore, and cryptographic verification."""

from pathlib import Path
import pytest

from restorelab.backup.restic import ResticBackupEngine
from restorelab.config import RestoreLabSettings, get_settings
from restorelab.verification.manifest import generate_manifest
from restorelab.verification.restore import verify_recovery


@pytest.mark.integration
def test_full_backup_and_recovery_verification(sample_dataset: Path, tmp_path: Path):
    """
    End-to-end integration test:
    1. Initialize a real Restic repository in a temp directory.
    2. Generate pre-backup SHA-256 manifest.
    3. Execute genuine Restic backup.
    4. Verify repository health via check.
    5. Enumerate snapshots.
    6. Perform isolated restore into sandbox.
    7. Cryptographically verify recovered content matches 100%.
    """
    binary = get_settings().find_restic_binary()
    if not binary:
        pytest.skip("Restic binary not available on system")

    repo_dir = tmp_path / "integration_repo"
    restore_dir = tmp_path / "integration_restore"
    restore_dir.mkdir(parents=True)

    settings = RestoreLabSettings(
        restic_binary_path=str(binary),
        restic_repository=str(repo_dir),
        restic_password="integration-test-passphrase-2026",
        lab_source_dir=str(sample_dataset),
        lab_restore_dir=str(restore_dir),
    )

    engine = ResticBackupEngine(settings)

    # 1. Initialize repository
    init_res = engine.init_repository()
    assert init_res.success, f"Init failed: {init_res.stderr}"

    # 2. Check repository status
    status = engine.get_status()
    assert status.initialized is True
    assert status.accessible is True

    # 3. Generate pre-backup manifest
    pre_manifest = generate_manifest(sample_dataset)
    assert pre_manifest.total_files == 3

    # 4. Create backup
    backup_res = engine.create_backup(sample_dataset, tags=["e2e-test"])
    assert backup_res.execution_result.success
    assert backup_res.snapshot_id is not None

    # 5. List snapshots
    snapshots = engine.list_snapshots()
    assert len(snapshots) >= 1
    assert any(s.id in backup_res.snapshot_id or backup_res.snapshot_id.startswith(s.id) for s in snapshots)

    # 6. Repository integrity check (fast index check)
    check_res = engine.check_repository(read_data=False)
    assert check_res.passed is True

    # 7. Isolated restore and full byte-level recovery verification
    report = verify_recovery(
        engine=engine,
        snapshot_id=backup_res.snapshot_id,
        original_manifest=pre_manifest,
        settings=settings,
    )

    assert report.status == "PASSED"
    assert report.comparison_result is not None
    assert report.comparison_result.is_perfect_match is True
    assert report.comparison_result.matched_count == 3
    assert report.comparison_result.missing_count == 0
    assert report.comparison_result.corrupted_count == 0
    assert report.comparison_result.extra_count == 0
