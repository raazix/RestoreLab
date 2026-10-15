# RestoreLab — Threat Model & Operational Safety Guide

This document defines the security boundaries, threat vectors, and architectural mitigations incorporated into **RestoreLab**.

---

## 1. System Trust Boundaries & Assets

### Protected Assets
1. **Host Filesystem Integrity:** Protecting live operating system volumes, system binaries, and user profile data from inadvertent overwrite or deletion.
2. **Repository Cryptographic Keys:** Ensuring encryption passwords are never exposed in plaintext across logs, shell commands, process listings, or error reports.
3. **Data Authenticity:** Preserving verifiable audit records and manifests against unauthorized tampering.

### Threat Actors Considered
- **Inadvertent Operator Error:** Accidental selection of live directories (e.g., `C:\`, `C:\Users\username`) as restore targets.
- **Malicious Symlink Traversal:** Malicious archives containing symlinks designed to write files outside approved restore sandboxes.
- **Process Memory & Log Sniffing:** Local processes observing command-line arguments to steal repository credentials.
- **Data Exfiltration via Cloud Extensions:** Accidental transmission of confidential local telemetry to external AI services.

---

## 2. Threat Analysis & Architectural Mitigations

| Threat ID | Threat Vector | Impact | Architectural Mitigation in RestoreLab |
| :--- | :--- | :--- | :--- |
| **THREAT-01** | In-place restore overwriting active source or host root | Data loss, system unbootable | **Strict Destination Containment Guard (`is_safe_restore_target`):** Rejects any restore destination that overlaps the live source directory, repository directory, root volume (`C:\`), or user profile root. |
| **THREAT-02** | Credential leakage via process argument inspection | Unauthorized repository decryption | **Environment Variable Credential Injection:** Passwords are never passed via CLI flags (`--password` or `--password-file`). Subprocesses inherit credentials strictly via isolated memory environment dictionaries (`RESTIC_PASSWORD`). |
| **THREAT-03** | Passwords leaking into logs, terminal traces, and database | Credential disclosure | **Deterministic Text Sanitizer (`sanitize_text`):** Intercepts all standard error, standard output, and exception strings before persisting or rendering, redacting passwords, API keys, and private tokens. |
| **THREAT-04** | Symlink traversal outside approved boundaries | Arbitrary file read/write | **Symlink Containment Validation:** Manifest scanning resolves symlink destinations (`Path.resolve()`). Links pointing outside the approved root directory are strictly skipped. |
| **THREAT-05** | Unauthorized telemetry transmission to remote AI services | Data leakage / privacy violation | **Opt-In Client-Side Privacy Pipeline:** Supermemory adapter is disabled by default (`SUPERMEMORY_ENABLED=false`). When active, payload preview enforces path redaction and credential stripping before HTTP dispatch. |
| **THREAT-06** | Accidental corruption of active repository during testing | Loss of lab backups | **Disposable Fixture Sandboxing:** All destructive tests and controlled experiments run exclusively inside disposable scratchpad directories (`data/lab_experiments/run_*`), leaving the active repository untouched. |

---

## 3. Operational Safety Checklist for Administrators

1. **Least Privilege Operation:** Always run RestoreLab under a standard, non-privileged user account. The application does not require and must not run with Administrator privileges.
2. **Review Environment Settings:** Ensure `.env` is excluded from version control and set file permissions to `0600` (read/write by owner only).
3. **Verify Sandbox Cleanliness:** Periodically inspect `data/lab_restore` and `data/lab_experiments` to confirm sandbox isolation.
