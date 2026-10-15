# RestoreLab — Testing Strategy & Verification Guide

This document details the test architecture, automated suites, failure injection scenarios, and evaluation methodology for **RestoreLab**.

---

## 1. Test Architecture & Pytest Suite

The automated test suite is divided into fast unit tests and genuine integration tests:

```
tests/
├── conftest.py                   # Shared pytest fixtures (isolated lab envs, sample datasets)
├── unit/
│   ├── test_manifest.py          # Deterministic SHA-256 manifests, silent corruption detection
│   ├── test_diagnostics.py       # Deterministic diagnostic rules & unclassified fallbacks
│   ├── test_repository.py        # SQLite persistence, ACID operations, FTS5 search
│   ├── test_knowledge.py         # Case-based reasoning & Supermemory privacy redaction
│   ├── test_experiments.py       # Safe execution of failure scenarios in disposable sandboxes
│   └── test_restic_wrapper.py    # Subprocess execution, credential sanitization, timeout handling
└── integration/
    └── test_backup_restore_e2e.py # Genuine end-to-end Restic backup & recovery verification
```

---

## 2. Test Execution Commands

### Run Fast Unit Tests (< 1 second)
```powershell
python -m pytest tests/unit -v
```

### Run Full Test Suite (Unit + Genuine Restic Integration)
```powershell
python -m pytest tests/unit tests/integration -v
```

### Run with Duration Profiling
```powershell
.\scripts\run_tests.ps1
```

---

## 3. Evaluated Reliability Metrics

| Test Domain | Target Invariant | Measured Test Result | Status |
| :--- | :--- | :--- | :--- |
| **Manifest Integrity** | Deterministic SHA-256 generation across nested trees and Unicode files | Verified across 75+ files with zero non-determinism | ✅ Passed |
| **Silent Corruption Detection** | Detection of 1-byte data tampering where file size remains unchanged | 100% detection rate (`corrupted_count > 0`, `is_perfect_match = False`) | ✅ Passed |
| **Restore Safety Boundaries** | In-place restore over live source or system root strictly rejected | `ValueError` raised before subprocess dispatch | ✅ Passed |
| **Credential Scrubbing** | Passwords scrubbed from logs, errors, and JSON exports | Validated against string search for `RESTIC_PASSWORD` | ✅ Passed |
| **End-to-End Recovery Verification** | Genuine Restic backup, restore into sandbox, 100% manifest verification | Complete byte-level match across real local backup | ✅ Passed |
| **Subprocess Timeout Guard** | Hanging commands safely terminated | Subprocess aborted with `timed_out = True` (exit code 124) | ✅ Passed |
| **Diagnostic Accuracy** | Deterministic rules fire accurately on known symptom signatures | Evaluated across all 8 failure scenarios | ✅ Passed |

---

## 4. Controlled Failure Scenarios Tested

1. **`EXP_MISSING_SOURCE`:** Non-existent source path handled before subprocess.
2. **`EXP_INVALID_REPO`:** Uninitialized directory detected (exit code 10).
3. **`EXP_WRONG_CREDENTIALS`:** Invalid passphrase caught without leaking secret.
4. **`EXP_COMMAND_ERROR`:** Subprocess exit code and standard error captured.
5. **`EXP_TAMPERED_FIXTURE`:** Silent data corruption flagged byte-for-byte.
6. **`EXP_UNSAFE_RESTORE`:** Dangerous destination rejected before execution.
7. **`EXP_TIMEOUT`:** Overdue commands terminated cleanly.
8. **`EXP_INTEGRITY_CHECK_FAILURE`:** Physical pack corruption detected via `restic check`.
