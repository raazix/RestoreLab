"""
Unit tests for RestoreLab Snapshot Drift and Volumetric Anomaly Engine.
Verifies file-level diffing, volumetric calculations, and explainable forensic flags.
"""

from __future__ import annotations

import pytest

from restorelab.verification.drift import SnapshotDriftAnalyzer
from restorelab.verification.manifest import FileEntry, Manifest


@pytest.fixture
def mock_analyzer():
    return SnapshotDriftAnalyzer(repository=None)


def test_drift_identical_manifests(mock_analyzer):
    entry1 = FileEntry(path="docs/a.txt", size_bytes=100, sha256="abc1", modified_at="2026-10-15T00:00:00Z")
    entry2 = FileEntry(path="docs/b.txt", size_bytes=200, sha256="abc2", modified_at="2026-10-15T00:00:00Z")

    m1 = Manifest(root_path="/lab", total_files=2, total_bytes=300, entries={"docs/a.txt": entry1, "docs/b.txt": entry2})
    m2 = Manifest(root_path="/lab", total_files=2, total_bytes=300, entries={"docs/a.txt": entry1, "docs/b.txt": entry2})

    report = mock_analyzer.analyze_drift(m1, m2, "snap-1", "snap-2")
    assert len(report.added_files) == 0
    assert len(report.removed_files) == 0
    assert len(report.modified_files) == 0
    assert len(report.unchanged_files) == 2
    assert report.size_change_bytes == 0
    assert report.percent_size_change == 0.0
    assert len(report.anomaly_flags) == 0


def test_drift_mass_deletion_anomaly(mock_analyzer):
    entries1 = {
        f"file_{i}.txt": FileEntry(path=f"file_{i}.txt", size_bytes=1000, sha256=f"hash_{i}", modified_at="2026-10-15T00:00:00Z")
        for i in range(10)
    }
    # Only 5 files left (50% deleted)
    entries2 = {
        f"file_{i}.txt": FileEntry(path=f"file_{i}.txt", size_bytes=1000, sha256=f"hash_{i}", modified_at="2026-10-15T00:00:00Z")
        for i in range(5)
    }

    m1 = Manifest(root_path="/lab", total_files=10, total_bytes=10000, entries=entries1)
    m2 = Manifest(root_path="/lab", total_files=5, total_bytes=5000, entries=entries2)

    report = mock_analyzer.analyze_drift(m1, m2, "snap-base", "snap-target")
    assert len(report.removed_files) == 5
    assert "ANOMALY_MASS_DELETION" in report.anomaly_flags


def test_drift_mass_modification_anomaly(mock_analyzer):
    entries1 = {
        f"doc_{i}.txt": FileEntry(path=f"doc_{i}.txt", size_bytes=2000, sha256=f"hash_old_{i}", modified_at="2026-10-15T00:00:00Z")
        for i in range(10)
    }
    # 8 of 10 files modified (80%)
    entries2 = {
        f"doc_{i}.txt": FileEntry(
            path=f"doc_{i}.txt",
            size_bytes=2000,
            sha256=f"hash_new_{i}" if i < 8 else f"hash_old_{i}",
            modified_at="2026-10-15T01:00:00Z",
        )
        for i in range(10)
    }

    m1 = Manifest(root_path="/lab", total_files=10, total_bytes=20000, entries=entries1)
    m2 = Manifest(root_path="/lab", total_files=10, total_bytes=20000, entries=entries2)

    report = mock_analyzer.analyze_drift(m1, m2, "snap-base", "snap-target")
    assert len(report.modified_files) == 8
    assert "ANOMALY_MASS_MODIFICATION" in report.anomaly_flags


def test_drift_suspicious_extension_flag(mock_analyzer):
    entries1 = {
        "readme.txt": FileEntry(path="readme.txt", size_bytes=500, sha256="abc", modified_at="2026-10-15T00:00:00Z")
    }
    entries2 = {
        "readme.txt": FileEntry(path="readme.txt", size_bytes=500, sha256="abc", modified_at="2026-10-15T00:00:00Z"),
        "payload.crypto": FileEntry(path="payload.crypto", size_bytes=1000, sha256="xyz", modified_at="2026-10-15T01:00:00Z"),
    }

    m1 = Manifest(root_path="/lab", total_files=1, total_bytes=500, entries=entries1)
    m2 = Manifest(root_path="/lab", total_files=2, total_bytes=1500, entries=entries2)

    report = mock_analyzer.analyze_drift(m1, m2, "snap-base", "snap-target")
    assert "ANOMALY_SUSPICIOUS_EXTENSION" in report.anomaly_flags
    assert any("atypical extensions" in exp for exp in report.anomaly_explanations)
