"""Unit tests for the cryptographic manifest generation and comparison engine."""

from pathlib import Path
import pytest
from restorelab.verification.manifest import (
    compare_manifests,
    compute_file_sha256,
    generate_manifest,
)


def test_manifest_generation(sample_dataset: Path):
    """Verify deterministic manifest creation across directory hierarchy."""
    manifest = generate_manifest(sample_dataset)

    assert manifest.total_files == 3
    assert manifest.manifest_hash != ""
    assert "system.conf" in manifest.entries
    assert "docs/readme.md" in manifest.entries
    assert "data/sample.bin" in manifest.entries

    # Check forward-slash normalization
    assert not any("\\" in k for k in manifest.entries.keys())

    # SHA256 of system.conf
    conf_file = sample_dataset / "system.conf"
    expected_sha = compute_file_sha256(conf_file)
    assert manifest.entries["system.conf"].sha256 == expected_sha
    assert manifest.entries["system.conf"].size_bytes == conf_file.stat().st_size


def test_manifest_perfect_match(sample_dataset: Path, tmp_path: Path):
    """Verify that an exact copy results in a perfect match."""
    import shutil

    copy_dir = tmp_path / "exact_copy"
    shutil.copytree(sample_dataset, copy_dir)

    m1 = generate_manifest(sample_dataset)
    m2 = generate_manifest(copy_dir)

    res = compare_manifests(m1, m2)
    assert res.is_perfect_match is True
    assert res.matched_count == 3
    assert res.missing_count == 0
    assert res.extra_count == 0
    assert res.corrupted_count == 0
    assert "PASSED: 100% byte-level recovery verified" in res.summary


def test_manifest_silent_corruption_detected(sample_dataset: Path, tmp_path: Path):
    """Verify that byte tampering is flagged as corruption (same size, different hash)."""
    import shutil

    tampered_dir = tmp_path / "tampered"
    shutil.copytree(sample_dataset, tampered_dir)

    # Tamper with 1 byte in sample.bin (same size)
    bin_file = tampered_dir / "data" / "sample.bin"
    data = bytearray(bin_file.read_bytes())
    data[10] = (data[10] + 1) % 256
    bin_file.write_bytes(bytes(data))

    m1 = generate_manifest(sample_dataset)
    m2 = generate_manifest(tampered_dir)

    res = compare_manifests(m1, m2)
    assert res.is_perfect_match is False
    assert res.matched_count == 2
    assert res.corrupted_count == 1
    assert any(d.status == "corrupted" and d.path == "data/sample.bin" for d in res.diffs)


def test_manifest_missing_and_extra_files(sample_dataset: Path, tmp_path: Path):
    """Verify detection of missing files and unexpected extra files."""
    import shutil

    modified_dir = tmp_path / "modified"
    shutil.copytree(sample_dataset, modified_dir)

    # Delete docs/readme.md
    (modified_dir / "docs" / "readme.md").unlink()

    # Add an unexpected extra file
    (modified_dir / "unauthorized.txt").write_text("extra", encoding="utf-8")

    m1 = generate_manifest(sample_dataset)
    m2 = generate_manifest(modified_dir)

    res = compare_manifests(m1, m2)
    assert res.is_perfect_match is False
    assert res.missing_count == 1
    assert res.extra_count == 1
    assert any(d.status == "missing" and d.path == "docs/readme.md" for d in res.diffs)
    assert any(d.status == "extra" and d.path == "unauthorized.txt" for d in res.diffs)


def test_manifest_safety_limits(sample_dataset: Path):
    """Verify that exceeding safety limits raises ValueError."""
    with pytest.raises(ValueError, match="File limit exceeded"):
        generate_manifest(sample_dataset, max_files=2)

    with pytest.raises(ValueError, match="Byte volume limit exceeded"):
        generate_manifest(sample_dataset, max_bytes=10)
