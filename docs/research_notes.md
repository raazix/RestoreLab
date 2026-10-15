# RestoreLab — Research Notes & Empirical Foundations

This document records the research citations, empirical findings, and industry reliability standards that inform the architectural and operational design of **RestoreLab**.

---

## 1. Silent Data Corruption & The Fallacy of Command Success

### Research Question
Does an exit code of `0` from a backup utility guarantee that backed up data is recoverable and uncorrupted?

### Sources
1. **Bairavasundaram, L. N., Goodson, G. R., Pasupathy, S., & Schindler, J. (2008).**  
   *An Analysis of Data Corruption in the Storage Stack.*  
   Proceedings of the 6th USENIX Conference on File and Storage Technologies (FAST '08), 223–238.  
   URL: https://www.usenix.org/legacy/event/fast08/tech/bairavasundaram.html
2. **Krevat, E., Tucek, J., & Ganger, G. R. (2007).**  
   *Disks Are From Mars, Apps Are From Venus: Storage System Fallacies.*  
   USENIX HotStorage '07.

### Relevant Findings
- Across a sample of 1.53 million enterprise and nearline disk drives over 41 months, silent data corruption developed across diverse hardware platforms without generating disk controller or bus errors.
- Checksums computed solely at write-time can validate write completion without catching latent sector errors or file-level transformations that occur post-backup.
- File system metadata operations may succeed while data blocks retain corrupted or truncated states.

### Limitations
- The FAST '08 study examined block-level and parity-level storage in storage arrays rather than content-addressable deduplicating backup engines like Restic.

### Design Decisions Informed
- **Mandatory Content-Level Verification:** A backup command returning exit code `0` is treated strictly as an *operational confirmation*, never as proof of data recoverability.
- **Independent Cryptographic Manifests:** Pre-backup deterministic SHA-256 manifests (`path`, `size`, `sha256`) are generated prior to ingest and independently verified against restored trees byte-for-byte.
- **Distinction Between Repository and Content Integrity:** Restic index checks (`restic check`) verify index and pack header integrity, while RestoreLab verification explicitly validates the reconstituted filesystem payload.

---

## 2. Content-Addressable Storage and Deduplication in Backup Engines

### Research Question
How does content-addressable chunking (Restic) affect restore speed, metadata integrity, and verification cost?

### Sources
1. **Restic Design Specification & Architecture.**  
   *Design: Data structures, encryption, and deduplication.*  
   Official Documentation: https://restic.readthedocs.io/en/stable/100_references.html  
2. **Quinlan, S., & Dorward, S. (2002).**  
   *Venti: A New Approach to Archival Data Storage.*  
   USENIX FAST '02.
3. **Zhu, B., Li, K., & Patterson, H. (2008).**  
   *Avoiding the Disk Bottleneck in the Data Domain Deduplication File System.*  
   USENIX FAST '08.

### Relevant Findings
- Restic uses Rabin-based content-defined chunking (CDC) with ChaCha20-Poly1305 authenticated encryption and SHA-256 identification.
- Repository corruption can occur in two distinct zones:
  1. *Metadata zone*: Snapshots and index files. Detectable via index traverse (`restic check` without `--read-data`).
  2. *Data pack zone*: Actual chunk payloads. Detectable only via full payload validation (`restic check --read-data`) or through snapshot restore and file hash comparison.

### Limitations
- Full payload reads across large repositories introduce substantial I/O overhead and cannot be run synchronously on every incremental operation.

### Design Decisions Informed
- **Tiered Verification Levels:**
  - *Level 1 (Fast)*: Snapshot metadata and index structure validation.
  - *Level 2 (Deep)*: Isolated sandbox restore followed by end-to-end manifest comparison.
  - *Level 3 (Full Data Read)*: Optional repository-wide payload validation (`--read-data`).
- **Explicit Recording of Untested States:** The UI strictly displays "Not Run" for checks omitted rather than assuming success.

---

## 3. Case-Based Reasoning (CBR) and Deterministic Diagnostic Rules

### Research Question
How should automated diagnostic systems for IT operational failures balance explainability, determinism, and similarity retrieval?

### Sources
1. **Aamodt, A., & Plaza, E. (1994).**  
   *Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches.*  
   AI Communications, 7(1), 39–59.
2. **Chen, M., et al. (2004).**  
   *Path-Based Failure and Evolution Management in Large-Scale Internet Systems.*  
   ACM Transactions on Computer Systems (TOCS).
3. **Nygard, M. T. (2018).**  
   *Release It!: Design and Deploy Production-Ready Software.* Pragmatic Bookshelf (2nd Edition).

### Relevant Findings
- Black-box probabilistic models and ungrounded LLMs produce hallucinated remediations and false confidence during outage recovery.
- Deterministic rule chains based on observable symptoms (return codes, standard error patterns, missing inodes, path containment violations) provide reproducible, auditable root causes.
- Case-Based Reasoning (Retrieve, Reuse, Revise, Retain) allows historical incident knowledge to be retrieved effectively using structured symptom signatures and full-text search.

### Limitations
- Rule sets require deliberate curation and do not automatically generalize to entirely novel runtime failures outside their pattern vocabulary.

### Design Decisions Informed
- **Dual-Layer Diagnostics:**
  1. *Deterministic Rules Engine:* Evaluates facts (`exit_code`, `stderr_snippets`, `manifest_diffs`, `path_status`) against versioned rules. Returns `confirmed`, `likely`, or `unknown`.
  2. *Local Incident Knowledge Base:* SQLite FTS5-powered case-based retrieval matching error signatures against verified post-mortems.
- **Evidence-First Presentation:** Every diagnostic finding references observable raw output and states any contradicting observations.

---

## 4. Cyber-Resilience and Isolated Recovery Sandboxing

### Research Question
What architectural controls are required to prevent backup restore operations from overwriting production source directories or propagating untrusted artifacts?

### Sources
1. **NIST Special Publication 800-209 (2020).**  
   *Security Guideline for Storage Infrastructure.*  
   National Institute of Standards and Technology.  
   DOI: https://doi.org/10.6028/NIST.SP.800-209
2. **NIST SP 800-160 Vol. 2 Rev. 1 (2021).**  
   *Developing Cyber-Resilient Systems: A Systems Security Engineering Approach.*

### Relevant Findings
- Restoration procedures frequently introduce catastrophic secondary failures when destinations overlap with live workloads.
- Secure recovery demands "Clean Room" or sandbox isolation: designated isolated volumes with strict path containment checks and privilege non-escalation.

### Limitations
- Local sandbox restores require sufficient free scratch storage and strict path sanitization.

### Design Decisions Informed
- **Containment Invariant:** Restore destination paths are strictly validated to ensure they reside within the designated lab boundaries and never overlap with the source directory or repository directory.
- **No In-Place Overwrites:** Restores default to timestamped subdirectories within the isolated restore directory.
- **Path Traversal Guards:** Resolves canonical absolute paths (`Path.resolve()`) to prevent traversal tricks (`../`).

---

## 5. Privacy and Offline-First Local Diagnostics

### Research Question
Under what conditions may incident telemetry and diagnostics be transmitted to external services?

### Sources
1. **Saltzer, J. H., & Schroeder, M. D. (1975).**  
   *The Protection of Information in Computer Systems.*  
   Proceedings of the IEEE, 63(9), 1278–1308.
2. **ISO/IEC 27040:2024.**  
   *Information technology — Security techniques — Storage security.*

### Relevant Findings
- Backup logs, file manifests, and terminal standard errors routinely leak authentication tokens, local usernames, absolute paths, database credentials, and customer personal data.
- Cloud-dependent diagnostic tools fail during network partition events—precisely when disaster recovery verification is needed most.

### Limitations
- Purely local models are constrained to pre-indexed incident articles and deterministic matching.

### Design Decisions Informed
- **Default Offline Operation:** The entire application operates 100% offline with SQLite and local Python processing.
- **Sanitization Pipeline:** Redacts passwords, API keys, private tokens, and local user home paths from logs and database records.
- **Opt-In Remote Adapter:** Supermemory is implemented strictly behind a provider interface, requiring explicit user activation, showing a preview of sanitized data before transmission.
