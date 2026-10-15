# RestoreLab — Operational Troubleshooting Guide

This guide provides actionable remediation steps for common operational errors encountered during backup, recovery, and integrity verification.

---

## 1. Common Restic Exit Codes

| Exit Code | Meaning | Probable Cause | Recommended Remediation |
| :---: | :--- | :--- | :--- |
| **0** | Success | Command completed normally. | Note: Exit code 0 does not prove content recoverability. Execute recovery verification in RestoreLab. |
| **1** | General Error | Subcommand failure, syntax issue, or path error. | Inspect standard error in Incident Explorer. Check file paths and read/write permissions. |
| **10** | Repository Not Found | Directory exists without `config` file. | Execute `restic init` or click **Initialize Repository** in Backup Lab. |
| **11** | Repository Locked | Previous operation crashed or is currently running. | Ensure no other backup tasks are running, then run `restic unlock`. |
| **12** | Authentication Error | Incorrect password supplied. | Verify `RESTIC_PASSWORD` in `.env`. Ensure no leading/trailing spaces exist. |
| **124** | Command Timeout | Subprocess exceeded time limit. | Increase `COMMAND_TIMEOUT_SECONDS` in Settings or `.env`. Check for disk bottleneck. |
| **127** | Executable Missing | `restic.exe` not found on PATH or in `bin/`. | Run `powershell .\scripts\download_restic.ps1` to download official binary. |

---

## 2. Troubleshooting Manifest & Verification Failures

### Symptom: Verification Status "FAILED" with Corrupted Files
- **Cause:** Restored files have matching byte sizes but differing SHA-256 digests (silent bit rot or file tampering).
- **Diagnosis:**
  1. Inspect the Differential Sample Table in Recovery Verification to identify affected paths.
  2. Run **Deep Data Check (`--read-data`)** in Backup Lab to see if repository pack chunks are damaged.
  3. Check host disk health (SMART metrics).
- **Remediation:** Restore from an earlier verified snapshot. Isolate corrupted storage volumes.

### Symptom: Unsafe Restore Destination Rejected
- **Cause:** Safety containment guard detected an attempt to restore over the live source directory or system root.
- **Remediation:** In Recovery Verification, ensure the restore destination is inside `./data/lab_restore` or `./data/lab_experiments`.

---

## 3. SQLite Database & Search Troubleshooting

### Symptom: FTS5 Virtual Table Operational Error
- **Cause:** SQLite library compiled without FTS5 module.
- **Mitigation in RestoreLab:** The persistence layer automatically detects missing FTS5 and falls back seamlessly to multi-column `LIKE` substring search.
- **Verification:** Run `python -m pytest tests/unit/test_repository.py` to confirm fallback operability.
