# RestoreLab — System Architecture & Design Specification

RestoreLab is an independent, vendor-neutral reliability engineering workbench designed to investigate backup failures, test data recovery, verify restored content cryptographically, and extract lessons from operational incidents.

---

## 1. High-Level Architectural Overview

RestoreLab separates operational concerns into distinct, loosely-coupled modules connected via deterministic data contracts:

```
+--------------------------------------------------------------------------------+
|                             Presentation Tier                                  |
|            Streamlit Reliability Workbench (8 Specialized Pages)               |
+--------------------------------------------------------------------------------+
                                       |
+--------------------------------------------------------------------------------+
|                             Application Tier                                   |
|                                                                                |
|  +--------------------+  +--------------------+  +--------------------------+  |
|  |   Backup Engine    |  |  Verification &    |  |   Deterministic Rules    |  |
|  |     (Restic)       |  |  Manifest Engine   |  |     Diagnostic Engine    |  |
|  +--------------------+  +--------------------+  +--------------------------+  |
|            |                       |                           |               |
|  +--------------------+  +--------------------+  +--------------------------+  |
|  |  Experiments       |  |  Incident & Audit  |  |  Knowledge Base &        |  |
|  |  (Failure Sandbox) |  |  Repository        |  |  Case-Based Retrieval    |  |
|  +--------------------+  +--------------------+  +--------------------------+  |
+--------------------------------------------------------------------------------+
                                       |
+--------------------------------------------------------------------------------+
|                             Storage & Host Tier                                |
|   - SQLite (ACID Audit Logs, Metadata, FTS5 Search)                            |
|   - Restic Repository (Content-Addressable Chunk Store, ChaCha20-Poly1305)     |
|   - Local Filesystem Sandboxes (Strict Path Isolation)                         |
+--------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Components

### 2.1 Backup Engine Abstraction (`restorelab.backup`)
- **Contract:** Defined by `BackupEngine` abstract base class.
- **Restic Implementation (`ResticBackupEngine`):**
  - Invokes CLI binaries via safe parameter lists (`subprocess.run`), avoiding shell interpolation vulnerabilities.
  - Credential isolation: Passwords and repository locations are injected via subprocess environment variables (`RESTIC_PASSWORD`), preventing secrets from appearing in system process lists.
  - Subprocess timeouts: Configurable timeout enforcement prevents stalled operations from hanging workers.
  - Sanitization: All standard error and standard output streams are scrubbed for passwords, API keys, and private tokens before persistence or presentation.

### 2.2 Cryptographic Manifest & Recovery Verification (`restorelab.verification`)
- **Pre-Ingest Manifest:** Generates a deterministic SHA-256 fingerprint of the source directory prior to backup.
  $$\text{Manifest} = \{ \text{normalized\_rel\_path} \to (\text{size}, \text{sha256}, \text{mtime}) \}$$
- **Canonical Hash:** Computes a SHA-256 digest over the lexicographically sorted entries, binding the entire tree state cryptographically.
- **Isolated Sandbox Restore:** Restores snapshots into timestamped, dedicated sandbox paths strictly bounded within `LAB_RESTORE_DIR`.
- **Differential Verification Engine:** Compares pre-backup expected manifests with restored actual manifests. Detects:
  - 100% byte matches
  - Silent data corruption (identical size, differing hash)
  - Missing files
  - Unexpected extra files
  - Size discrepancies

### 2.3 Deterministic Diagnostic Engine (`restorelab.diagnostics`)
- **Design Philosophy:** Zero hallucination risk. Rules evaluate observable facts (`exit_code`, `stderr_snippets`, `manifest_diffs`, `path_status`).
- **Explainability:** Each fired rule specifies:
  - Rule identifier & version
  - Certainty rating (`confirmed`, `likely`, `unknown`)
  - Supported evidence and observed facts
  - Recommended checks and prescriptive remediations
  - Direct links to Knowledge Base articles (`kb_reference_id`)

### 2.4 Controlled Failure Experiments (`restorelab.experiments`)
- **Disposable Fixture Sandboxing:** Experiments execute within isolated scratchpads inside `data/lab_experiments/`.
- **Active Repository Safety Invariant:** Experiments never alter, truncate, or corrupt active lab repositories. All destructive failure tests operate on disposable, temporary repositories and purge all artifacts upon completion.

### 2.5 Persistence & Case-Based Knowledge Base (`restorelab.incidents`, `restorelab.knowledge`)
- **SQLite Engine (Authoritative Source of Truth):** ACID transactions, WAL mode, foreign key enforcement. All incidents, backup runs, and recovery audits reside authoritatively in local SQLite.
- **Full-Text Retrieval (FTS5):** Indexes troubleshooting articles, symptoms, root causes, and verified resolutions.
- **Case-Based Reasoning (CBR):** Matches real-time incident symptoms against historical post-mortems and provides deterministic relevance explanations.
- **Provider Interface (`MemoryProvider`):** Loose coupling allowing local SQLite offline search or opt-in remote adapters (`SupermemoryAdapter`).
- **Supermemory v5 Integration (`SupermemoryAdapter`):**
  - Uses official `supermemory>=5.0.0` SDK.
  - Strict namespace isolation via `SUPERMEMORY_NAMESPACE` (`/ns/{namespace}/...`).
  - Pre-transmission privacy scrubber replacing Windows/POSIX filesystem paths (`[LOCAL_PATH]`) and redacting secrets, bearer tokens, and API keys.
  - Requires explicit user review of sanitized JSON payload and UI checkbox consent before remote ingestion.
  - Zero secret leakage in logs or exception traces.
  - Transparent fallback to SQLite FTS5 when Supermemory is unconfigured, disabled, or offline.

---

## 3. Data Flow Pipelines

### 3.1 Backup & Manifest Pipeline
```
1. Approved Source Scan  -->  Compute SHA-256 Manifest  -->  Persist Manifest
                                                                     |
2. Subprocess Trigger    -->  Restic Backup (--json)     -->  Capture Exit Code
                                                                     |
3. Snapshot Capture      -->  Parse NDJSON Telemetry     -->  Record BackupRun
```

### 3.2 Recovery Verification Pipeline
```
1. Select Snapshot       -->  Validate Dest Sandbox Path  -->  Execute Isolated Restore
                                                                     |
2. Locate Restored Root  -->  Generate Restored Manifest -->  Byte-Level Diff
                                                                     |
3. Evaluate Rules        -->  Generate Audit Report       -->  Record RestoreAttempt
```

---

## 4. Filesystem Directory Layout

```
data/
├── lab_repo/         # Official encrypted Restic repository
├── lab_source/       # Approved user test dataset
├── lab_restore/      # Isolated recovery sandboxes
├── lab_experiments/  # Disposable scratchpad for failure scenarios
└── restorelab.db     # SQLite persistence with FTS5 search index
```
