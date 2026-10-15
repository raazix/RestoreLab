# 🛡️ RestoreLab — Backup Integrity & Recovery Verification Tool

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Engine: Restic](https://img.shields.io/badge/engine-Restic%200.19.1-cyan.svg)](https://restic.net/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6.svg)](https://microsoft.com)
[![Tests: 39 Passed](https://img.shields.io/badge/tests-39%20passed-success.svg)](tests/)

> **Evidence before conclusions. Recovery over appearance. Safety by default.**

**RestoreLab** is an independent, vendor-neutral reliability engineering workbench designed to investigate backup failures, test data recovery, verify restored content cryptographically, and learn from previous incidents.

Unlike traditional backup utilities that stop at reporting exit codes, RestoreLab proves whether data can actually be reconstituted and verified byte-for-byte. It pairs real Restic backup operations with deterministic SHA-256 manifest auditing, a deterministic diagnostic rule engine, an ACID incident repository with FTS5 search, and controlled failure experiments.

---

## 🌟 Key Capabilities

- **Real Local Restic Engine:** Hardened wrapper executing genuine backups, snapshot listings, index checks, and isolated restores without shell injection risks.
- **Cryptographic File-Level Verification:** Pre-backup and post-restore SHA-256 manifests comparing byte counts, relative POSIX paths, and cryptographic digests to catch silent data corruption.
- **Strict Destination Safety Guards:** Rejects in-place overwrites of source directories, repository roots, or system volumes before subprocess dispatch.
- **Deterministic Diagnostic Engine:** 11 versioned, auditable rules mapping observable symptoms (exit codes, stderr patterns, manifest diffs) to confirmed root causes and remediations without generative AI hallucinations.
- **Repeatable Failure Experiments:** 8 safe, automated failure injection scenarios (missing source, uninitialized repo, wrong password, silent bit rot, safety violations, timeouts, pack corruption) run in disposable scratchpads.
- **ACID Persistence & Full-Text Retrieval:** SQLite database tracking backup runs, restore attempts, audit manifests, incidents, and a curated troubleshooting knowledge base powered by SQLite FTS5.
- **Hashed Audit & Post-Mortem Exports:** Generate signed Markdown post-mortems and cryptographic verification reports with SHA-256 fingerprints.
- **Windows-First, Local-First:** Runs 100% locally on Windows 10/11 without Docker, cloud credentials, or external API dependencies. Includes an optional, privacy-sanitized Supermemory extension.

---

## 🚀 Quick Start (Windows PowerShell)

### 1. Prerequisites
- **Python 3.11+** installed and available on PATH (`python --version`).
- **PowerShell 5.1+ / 7+**.

### 2. Automated One-Click Setup
Clone or navigate to the repository directory and run the automated lab bootstrap:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_lab.ps1
```

The setup script will automatically:
1. Generate `.env` from `.env.example`.
2. Create dedicated, isolated lab directories (`data/lab_repo`, `data/lab_source`, `data/lab_restore`, `data/lab_experiments`).
3. Download and verify the official Windows Restic binary into `bin/restic.exe`.
4. Generate the sample reliability dataset (configs, markdown, binary, Unicode).
5. Initialize the local encrypted Restic lab repository.

### 3. Launch the Workbench
```powershell
.\scripts\run_app.ps1
```
Open your browser to: **`http://localhost:8501`**

---

## 🧭 Workbench Navigation & Workflows

RestoreLab features 8 specialized workbench views:

| Page | Description | Core Capabilities |
| :--- | :--- | :--- |
| **📊 Overview** | High-level reliability dashboard | System status, recent backup runs, verified restore ratio, repository health, open incidents. |
| **💾 Backup Lab** | Backup execution and repository management | Initialize repository, generate test datasets, pre-scan SHA-256 manifests, execute backups, run fast or deep integrity checks (`--read-data`). |
| **🔍 Recovery Verification** | Snapshot restore & cryptographic diff | Browse snapshots, perform isolated sandbox restores, compare pre/post manifests, detect silent corruption. |
| **🚨 Incident Explorer** | Triage and post-mortem workbench | Investigate failures, view observable evidence and diagnostic findings, record verified remediations, update lifecycle status. |
| **📚 Knowledge Base** | Case-based reasoning search | Search troubleshooting articles and past post-mortems using SQLite FTS5 with explainable match reasons. |
| **🧪 Experiments** | Controlled failure injection | Execute 8 failure scenarios against disposable fixtures with automatic sandbox cleanup. |
| **📋 Reports** | Audit report generator | View and download Markdown post-mortems and cryptographic recovery audit reports with SHA-256 fingerprints. |
| **⚙️ Settings** | Configuration & safety governance | Inspect active paths, safety limits, binary paths, and preview Supermemory client-side privacy sanitization. |

---

## 🧪 Reproducible Technical Interview Demo Walkthrough

Follow this 5-minute walkthrough to demonstrate end-to-end reliability engineering in an interview:

### Step 1: Environment & Dataset Preparation
1. Open the **Backup Lab** page.
2. Confirm the repository status indicator is green (`Repository Connected`).
3. Click **Generate Sample Dataset** to populate `data/lab_source/` with configs, markdown, binary assets, and a Unicode test file (`üñîçødé.txt`).
4. Click **Generate Pre-Backup Manifest** to calculate pre-ingest SHA-256 digests.

### Step 2: Genuine Backup Execution
1. Click **Execute Real Backup (Restic)**.
2. Observe duration, added bytes, and the generated snapshot hex ID (e.g. `3a4f89b1`).
3. Click **Run Fast Index Check (`restic check`)** to confirm index structure validity.

### Step 3: Isolated Recovery & Cryptographic Verification
1. Navigate to **Recovery Verification**.
2. Select your newly created snapshot.
3. Observe the destination safety badge: `Target: Isolated Sandbox` (verified inside `data/lab_restore/`).
4. Click **Execute Restore & Verify Content Integrity**.
5. Inspect the file-by-file verification table: **`PASSED: 100% byte-level recovery verified`** with matching SHA-256 hashes across all files.

### Step 4: Controlled Failure & Silent Corruption Detection
1. Navigate to **Experiments**.
2. Select **`EXP_TAMPERED_FIXTURE: Silent Data Corruption in Restored Content`**.
3. Click **Run Single Experiment**.
4. Observe the result: The engine detects a 1-byte alteration where file size was identical, triggering deterministic rule **`RULE_MANIFEST_SILENT_CORRUPTION`**.
5. Observe that the disposable experiment sandbox was automatically purged upon completion.

### Step 5: Incident Investigation & Knowledge Base Search
1. Navigate to **Knowledge Base**.
2. Type `silent corruption` into the search box.
3. Review article **`KB-CORRUPT-001`**, noting the explainable match reason and verified resolution steps.
4. Navigate to **Reports** to inspect and export the cryptographically hashed post-mortem report.

---

## 🏗️ Architecture & Project Structure

```
RestoreLab/
├── app.py                         # Streamlit Reliability Workbench
├── src/
│   └── restorelab/
│       ├── __init__.py
│       ├── config.py              # Validated settings, path containment, credential sanitization
│       ├── backup/
│       │   ├── base.py            # BackupEngine contract & result models
│       │   └── restic.py          # Safe Restic CLI subprocess wrapper
│       ├── verification/
│       │   ├── manifest.py        # Deterministic SHA-256 manifest engine & diffing
│       │   ├── restore.py         # Isolated restore orchestrator & verification
│       │   └── sample_data.py     # Realistic test dataset generator
│       ├── diagnostics/
│       │   ├── engine.py          # Deterministic diagnostic evaluation engine
│       │   └── rules.py           # 11 versioned diagnostic rules
│       ├── incidents/
│       │   ├── models.py          # Data models for incidents, runs, audits, and KB
│       │   └── repository.py      # SQLite ACID persistence & FTS5 search
│       ├── knowledge/
│       │   ├── provider.py        # MemoryProvider interface & SearchResult
│       │   ├── sqlite_search.py   # Local offline FTS5 case-based retrieval
│       │   └── supermemory_adapter.py # Optional remote memory adapter with privacy redaction
│       ├── experiments/
│       │   ├── scenarios.py       # 8 failure scenario specifications
│       │   └── runner.py          # Safe disposable experiment execution runner
│       └── reporting/
│           └── exports.py         # Markdown/JSON post-mortems with SHA-256 fingerprints
├── tests/
│   ├── conftest.py                # Isolated test fixtures
│   ├── unit/                      # 29 fast unit tests (< 1 sec)
│   └── integration/               # End-to-end Restic integration tests
├── scripts/
│   ├── download_restic.ps1        # Restic binary downloader
│   ├── setup_lab.ps1              # Full environment setup
│   ├── run_app.ps1                # App launcher
│   ├── run_tests.ps1              # Automated test runner
│   └── generate_sample_data.py    # CLI sample data generator
├── docs/
│   ├── architecture.md            # System design & component models
│   ├── research_notes.md          # Peer-reviewed research citations & design rationale
│   ├── testing.md                 # Test plan, metrics, and failure scenarios
│   ├── threat_model.md            # Security boundaries & safety guide
│   └── troubleshooting.md         # Operational error codes & remediations
├── .env.example                   # Documented configuration template
├── requirements.txt               # Constrained dependencies
└── README.md
```

---

## 🔬 Research Foundations

RestoreLab's architectural design is grounded in peer-reviewed systems and storage literature (detailed in [`docs/research_notes.md`](docs/research_notes.md)):

1. **Silent Data Corruption:** Bairavasundaram et al. (*USENIX FAST '08*) established that exit code `0` from write operations fails to catch silent data corruption, motivating RestoreLab's independent SHA-256 manifest audit requirement.
2. **Content-Addressable Chunking:** Restic architecture specification and Quinlan & Dorward (*USENIX FAST '02*) inform our multi-tier verification distinguishing fast index checks from payload reading (`--read-data`).
3. **Case-Based Reasoning (CBR):** Aamodt & Plaza (*AI Communications '94*) and Nygard (*Release It!*) inform our deterministic diagnostic engine and offline symptom-matching retrieval.
4. **Clean Room Recovery:** NIST SP 800-209 and SP 800-160 inform our strict destination containment checks (`is_safe_restore_target`) preventing in-place overwrites.

---

## 🧠 Supermemory v5 Knowledge Integration (Optional)

RestoreLab integrates with the official **Supermemory API v5** (`supermemory>=5.0.0`) for cross-incident case-based reasoning and semantic retrieval, while guaranteeing complete local privacy:

- **Isolated Namespace:** All incident knowledge is strictly scoped to `SUPERMEMORY_NAMESPACE` (default: `restorelab-incidents`) via the URL endpoint path `/ns/{namespace}/...`.
- **Client-Side Privacy Sanitization:** Previews and redacts all local Windows/POSIX paths (`[LOCAL_PATH]`), passwords, bearer tokens, and API keys before transmission. Raw file contents and credentials are **never** transmitted.
- **Explicit User Consent:** Before syncing an incident to Supermemory, the workbench provides a real-time expandable preview of the exact sanitized JSON payload and requires an explicit opt-in confirmation checkbox.
- **Zero Secret Leaks:** API keys and credentials are read strictly from `.env` and are scrubbed from log output and error stack traces.
- **SQLite Source of Truth & Safe Fallback:** SQLite remains the authoritative ACID incident database. If Supermemory is disabled, offline, or throttled, queries seamlessly fall back to local SQLite FTS5 search without user interruption.

---

## 🧪 Automated Testing Suite

RestoreLab includes 39 unit and integration tests using `pytest`:

```powershell
# Run the complete test suite (all 39 tests)
python -m pytest tests/ -v

# Run fast offline unit tests with mocked API (no keys or network required)
python -m pytest tests/unit/ -v

# Run live Supermemory v5 integration tests (uses SUPERMEMORY_API_KEY from .env)
python -m pytest tests/integration/test_supermemory_live.py -v
```

All 39 tests pass cleanly:
- **Offline Supermemory Mocks (7 tests):** Verified config loading, client-side regex path/secret redaction, mocked connection check, mocked document ingestion, mocked hybrid retrieval, offline fallback, and API key redaction in error messages.
- **Live Integration Tests (2 tests):** Verified live connection to `https://api.supermemory.ai` and live ingestion/search roundtrip against namespace `restorelab-incidents`.
- **Deterministic Manifest Engine (5 tests):** Size limits, Unicode paths, and byte-for-byte SHA-256 verification.
- **Diagnostic Engine & Failure Scenarios (13 tests):** 11 deterministic rules and 8 failure scenarios including silent bit rot, missing repo, and timeouts.
- **ACID Persistence & SQLite Search (4 tests):** Backup runs, restore audits, incident records, and FTS5 full-text queries.
- **Hardened Subprocess Wrapper (3 tests):** Missing binary safety (127), safe restore target verification, and environment credential containment.
- **End-to-End Restic Cycle (1 test):** Genuine Restic backup, snapshot discovery, restore, and 100% cryptographic verification.

---

## 🔒 Security & Safety Controls

- **No Administrator Privileges Required:** Operates strictly within non-privileged user space.
- **Isolated Lab Bounds:** Backups, restores, and scratchpads are strictly confined to `./data/`.
- **Zero Command-Line Secret Leaks:** Subprocess passwords are never passed as arguments.
- **Privacy-First Telemetry:** The optional Supermemory adapter is disabled by default and scrubs all credentials, usernames, and local paths before transmission.

---

## 📄 License

RestoreLab is open-source software licensed under the [MIT License](LICENSE).
