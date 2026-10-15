"""
RestoreLab Sample Lab Dataset Generator
Generates realistic, verifiable test datasets including nested directories,
configuration files, binary blobs, and Unicode filenames for backup resilience testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple


def generate_lab_dataset(target_dir: Path | str) -> Tuple[int, int]:
    """
    Populate target directory with a standard reliability engineering dataset.
    Returns (file_count, total_bytes).
    """
    root = Path(target_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    files_created = 0
    total_bytes = 0

    def write_f(rel_path: str, content: str | bytes) -> None:
        nonlocal files_created, total_bytes
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = content
        p.write_bytes(data)
        files_created += 1
        total_bytes += len(data)

    # 1. Root configuration files
    app_config = {
        "service_name": "payment-gateway-relay",
        "environment": "production-us-east-1",
        "port": 8443,
        "tls_enabled": True,
        "workers": 8,
        "timeout_ms": 3000,
        "database": {
            "host": "db-cluster.internal.net",
            "port": 5432,
            "max_connections": 100,
        },
    }
    write_f("configs/app_config.json", json.dumps(app_config, indent=2))

    nginx_conf = """# Reverse proxy configuration
events { worker_connections 1024; }
http {
    upstream backend {
        server 127.0.0.1:8080 max_fails=3 fail_timeout=30s;
    }
    server {
        listen 80;
        server_name relay.restorelab.local;
        location /healthz {
            return 200 'healthy';
        }
    }
}
"""
    write_f("configs/nginx.conf", nginx_conf)

    # 2. Operational runbooks and docs
    runbook_md = """# Disaster Recovery Runbook: RestoreLab Tier-1 Services

## Objective
Verify RPO (< 1 hour) and RTO (< 15 minutes) for content-addressable storage repositories.

## Verification Steps
1. Take pre-ingest deterministic SHA-256 tree manifest.
2. Trigger incremental chunk deduplication backup.
3. Validate repository index with 'restic check'.
4. Perform sandbox restore into isolated container.
5. Execute byte-level differential audit comparing pre and post hashes.
"""
    write_f("docs/recovery_runbook.md", runbook_md)

    specs_md = """# System Architecture Specifications
- Deduplication: Rabin CDC (Chunk-Defined Chunking)
- Cipher: ChaCha20-Poly1305 AEAD authenticated encryption
- Manifest Digest: SHA-256 tree hash
"""
    write_f("docs/architecture_specs.md", specs_md)

    # 3. Tabular metrics and telemetry
    telemetry_csv = "timestamp,cpu_pct,memory_mb,io_wait_ms,status\n"
    for i in range(1, 51):
        telemetry_csv += f"2026-10-15T12:{i:02d}:00Z,{15 + (i % 10)},{512 + i * 2},{1.2 + (i % 3) * 0.4},nominal\n"
    write_f("data/telemetry_export.csv", telemetry_csv)

    # 4. Binary asset
    # Pseudorandom reproducible binary pattern
    binary_data = bytes([(x * 37 + 13) % 256 for x in range(4096)])
    write_f("data/firmware_signature.bin", binary_data)

    # 5. Unicode resilience test file (proves Windows filesystem UTF-8 handling)
    unicode_content = (
        "Unicode File System Verification / 测试文件 / файл_проверки / テストファイル\n"
        "Accented characters: é, è, ê, ë, ñ, ü, ö, ä, ß, ç, ø, å\n"
    )
    write_f("docs/i18n_unicode_üñîçødé.txt", unicode_content)

    return files_created, total_bytes
