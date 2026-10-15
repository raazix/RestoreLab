"""
RestoreLab SQLite Persistence and Audit Repository
Manages atomic transactions, FTS5 full-text indexing, audit trails, and curated knowledge base.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from pydantic import BaseModel

from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.experiments.runner import ExperimentResult
from restorelab.incidents.models import (
    BackupRunRecord,
    IncidentRecord,
    IntegrityCheckRecord,
    KnowledgeArticle,
    RestoreAttemptRecord,
)
from restorelab.verification.manifest import Manifest

logger = setup_logging()


class IncidentRepository:
    """SQLite data access layer providing ACID persistence and full-text search."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path:
            self.db_path = Path(db_path).resolve()
        else:
            self.db_path = get_settings().resolved_database_path
        self._fts5_available = True
        self.init_database()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding SQLite connection with transaction management."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self) -> None:
        """Create database tables, indexes, and initial knowledge-base seeds."""
        with self._connection() as conn:
            # 1. Incidents Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    operation_id TEXT,
                    symptoms_json TEXT,
                    raw_evidence_json TEXT,
                    findings_json TEXT,
                    verified_resolution TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    notes_json TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at);")

            # 2. Backup Runs Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    snapshot_id TEXT,
                    status TEXT NOT NULL,
                    manifest_id TEXT,
                    total_files INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    raw_output TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_backup_time ON backup_runs(timestamp);")

            # 3. Restore Attempts Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS restore_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    original_manifest_id TEXT,
                    restored_manifest_id TEXT,
                    matched_files INTEGER NOT NULL,
                    corrupted_files INTEGER NOT NULL,
                    missing_files INTEGER NOT NULL,
                    extra_files INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    details TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_restore_time ON restore_attempts(timestamp);")

            # 4. Integrity Checks Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS integrity_checks (
                    check_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    exit_code INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    raw_output TEXT
                );
                """
            )

            # 5. Manifests Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS manifests (
                    manifest_id TEXT PRIMARY KEY,
                    root_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    manifest_hash TEXT NOT NULL,
                    manifest_json TEXT NOT NULL
                );
                """
            )

            # 6. Experiments Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    scenario_title TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    expected_outcome TEXT,
                    actual_observations TEXT,
                    sanitized_output TEXT,
                    checks_json TEXT,
                    findings_json TEXT,
                    cleanup_status TEXT,
                    evidence_json TEXT
                );
                """
            )

            # 7. Knowledge Articles Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_articles (
                    article_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    problem_symptoms TEXT NOT NULL,
                    preconditions TEXT,
                    diagnostic_checks TEXT,
                    verified_cause TEXT,
                    resolution_steps TEXT,
                    verification_procedure TEXT,
                    known_limitations TEXT,
                    related_incidents_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 8. FTS5 Virtual Table for Knowledge Search
            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                        article_id UNINDEXED,
                        title,
                        category,
                        problem_symptoms,
                        verified_cause,
                        resolution_steps,
                        tokenize = 'porter unicode61'
                    );
                    """
                )
                self._fts5_available = True
            except sqlite3.OperationalError as e:
                logger.warning(f"FTS5 virtual table initialization failed: {e}. Falling back to LIKE.")
                self._fts5_available = False

        self._seed_default_knowledge_base()

    def _seed_default_knowledge_base(self) -> None:
        """Seed verified troubleshooting articles if repository is empty."""
        articles = [
            KnowledgeArticle(
                article_id="KB-RESTIC-001",
                title="Restic Authentication & Keystore Password Failure",
                category="authentication",
                problem_symptoms="Backup or snapshot query fails with 'Fatal: wrong password or no key found' or exit code 12.",
                preconditions="Encrypted repository accessed with incorrect RESTIC_PASSWORD environment variable or keystore corruption.",
                diagnostic_checks="1. Inspect RESTIC_PASSWORD in .env.\n2. Attempt reading keys via 'restic key list'.\n3. Check for trailing newline or encoding issues in password.",
                verified_cause="Mismatch between supplied repository password and PBKDF2/scrypt derived key in repository config.",
                resolution_steps="Update RESTIC_PASSWORD in .env to the correct value or initialize a secondary key using 'restic key add'.",
                verification_procedure="Execute 'restic snapshots' to confirm authenticated access.",
                known_limitations="Lost passwords cannot be recovered without a valid key file.",
            ),
            KnowledgeArticle(
                article_id="KB-RESTIC-002",
                title="Uninitialized Repository / Missing Config File",
                category="repository",
                problem_symptoms="Engine commands fail with exit code 10 and 'Fatal: config file not found. Is there a repository at the following location?'.",
                preconditions="Repository directory was created or moved without running 'restic init'.",
                diagnostic_checks="Check whether repository directory contains a 'config' file and 'data/', 'index/', 'snapshots/' subfolders.",
                verified_cause="Target path exists as a bare filesystem directory without Restic repository metadata.",
                resolution_steps="Run 'restic init' via the Backup Lab or CLI to establish repository structures and encryption keys.",
                verification_procedure="Confirm engine.get_status() reports initialized=True.",
                known_limitations="Running init on an existing repository will fail. Use only for new repositories.",
            ),
            KnowledgeArticle(
                article_id="KB-CORRUPT-001",
                title="Silent Data Corruption in Recovered Payload",
                category="integrity",
                problem_symptoms="Restored file sizes match expected counts, but cryptographic SHA-256 hashes differ.",
                preconditions="Storage bit rot, filesystem corruption, or silent network bit flips occurred during data storage or retrieval.",
                diagnostic_checks="1. Run 'restic check --read-data' to verify repository pack integrity.\n2. Check host filesystem SMART metrics.\n3. Compare SHA-256 hashes across successive snapshots.",
                verified_cause="Data block alteration occurring beneath the file system layer without updating inode file length metadata.",
                resolution_steps="Isolate corrupted snapshot. Identify affected files from manifest diff. Restore from the most recent verified healthy snapshot.",
                verification_procedure="Run verify_recovery against earlier snapshots until 100% manifest match is achieved.",
                known_limitations="Once data chunks in the repository are overwritten or corrupted without redundancy, recovery depends on independent replica stores.",
            ),
            KnowledgeArticle(
                article_id="KB-SEC-001",
                title="Restore Target Containment & Overwrite Violation",
                category="security",
                problem_symptoms="Restore attempt blocked before execution with 'Unsafe restore destination rejected'.",
                preconditions="Restore target path points to live source directory, system root volume (C:\\), or outside approved lab bounds.",
                diagnostic_checks="Inspect requested target path against LAB_RESTORE_DIR and LAB_SOURCE_DIR configuration settings.",
                verified_cause="Safety containment guard intentionally halted execution to prevent overwriting active production data.",
                resolution_steps="Specify a destination directory strictly within ./data/lab_restore or ./data/lab_experiments.",
                verification_procedure="Confirm target path is inside configured restore sandbox bounds.",
                known_limitations="Overwriting live source data in-place is permanently disabled for safety.",
            ),
            KnowledgeArticle(
                article_id="KB-LOCK-001",
                title="Stale Repository Locks & Concurrency Conflicts",
                category="concurrency",
                problem_symptoms="Commands fail with 'Fatal: unable to create lock in repo: repository is already locked' (exit code 11).",
                preconditions="A previous backup command was killed ungracefully (power cut, SIGKILL, Task Manager termination).",
                diagnostic_checks="Verify no other active restic processes are running on the system using Task Manager or psutil.",
                verified_cause="Orphaned lock file persisted in repository 'locks/' folder following abnormal process termination.",
                resolution_steps="After confirming no active backup processes exist, execute 'restic unlock' to remove stale locks.",
                verification_procedure="Run 'restic snapshots' to confirm lock release.",
                known_limitations="Unlocking an actively running backup process can corrupt repository operations.",
            ),
            KnowledgeArticle(
                article_id="KB-FS-001",
                title="Missing Source Directory or Inaccessible Inodes",
                category="filesystem",
                problem_symptoms="Backup command fails immediately with 'cannot find the path specified' or FileNotFoundError.",
                preconditions="Configured source directory path was renamed, deleted, or unmounted.",
                diagnostic_checks="Check if path exists via os.path.exists() and verify current user read permissions.",
                verified_cause="Backup engine targeted a path that does not exist in the host filesystem.",
                resolution_steps="Restore or create the source directory and re-populate test files via 'Generate Sample Dataset'.",
                verification_procedure="Re-run pre-backup manifest scan.",
                known_limitations="Non-existent paths cannot be backed up.",
            ),
        ]

        with self._connection() as conn:
            for art in articles:
                # Check if exists
                cur = conn.execute("SELECT 1 FROM knowledge_articles WHERE article_id = ?", (art.article_id,))
                if not cur.fetchone():
                    self.save_knowledge_article(art)

    # -------------------------------------------------------------------------
    # Incident CRUD
    # -------------------------------------------------------------------------

    def save_incident(self, record: IncidentRecord) -> None:
        """Persist or update an incident record."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO incidents (
                    incident_id, created_at, title, status, severity, category,
                    operation_type, operation_id, symptoms_json, raw_evidence_json,
                    findings_json, verified_resolution, resolved_by, resolved_at, notes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    title=excluded.title,
                    status=excluded.status,
                    severity=excluded.severity,
                    category=excluded.category,
                    symptoms_json=excluded.symptoms_json,
                    raw_evidence_json=excluded.raw_evidence_json,
                    findings_json=excluded.findings_json,
                    verified_resolution=excluded.verified_resolution,
                    resolved_by=excluded.resolved_by,
                    resolved_at=excluded.resolved_at,
                    notes_json=excluded.notes_json;
                """,
                (
                    record.incident_id,
                    record.created_at,
                    record.title,
                    record.status,
                    record.severity,
                    record.category,
                    record.operation_type,
                    record.operation_id,
                    json.dumps(record.symptoms),
                    json.dumps(record.raw_evidence),
                    json.dumps([f.model_dump() for f in record.findings]),
                    record.verified_resolution,
                    record.resolved_by,
                    record.resolved_at,
                    json.dumps(record.notes),
                ),
            )

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        """Fetch incident by unique identifier."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_incident(row)

    def list_incidents(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[IncidentRecord]:
        """List incidents with optional status filter."""
        with self._connection() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_incident(r) for r in cur.fetchall()]

    def _row_to_incident(self, row: sqlite3.Row) -> IncidentRecord:
        return IncidentRecord(
            incident_id=row["incident_id"],
            created_at=row["created_at"],
            title=row["title"],
            status=row["status"],
            severity=row["severity"],
            category=row["category"],
            operation_type=row["operation_type"],
            operation_id=row["operation_id"],
            symptoms=json.loads(row["symptoms_json"] or "[]"),
            raw_evidence=json.loads(row["raw_evidence_json"] or "{}"),
            findings=json.loads(row["findings_json"] or "[]"),
            verified_resolution=row["verified_resolution"],
            resolved_by=row["resolved_by"],
            resolved_at=row["resolved_at"],
            notes=json.loads(row["notes_json"] or "[]"),
        )

    # -------------------------------------------------------------------------
    # Backup Run Records
    # -------------------------------------------------------------------------

    def save_backup_run(self, record: BackupRunRecord) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO backup_runs (
                    run_id, timestamp, source_path, snapshot_id, status,
                    manifest_id, total_files, total_bytes, duration_seconds, raw_output
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.run_id,
                    record.timestamp,
                    record.source_path,
                    record.snapshot_id,
                    record.status,
                    record.manifest_id,
                    record.total_files,
                    record.total_bytes,
                    record.duration_seconds,
                    record.raw_output,
                ),
            )

    def list_backup_runs(self, limit: int = 50) -> List[BackupRunRecord]:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM backup_runs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                BackupRunRecord(
                    run_id=r["run_id"],
                    timestamp=r["timestamp"],
                    source_path=r["source_path"],
                    snapshot_id=r["snapshot_id"],
                    status=r["status"],
                    manifest_id=r["manifest_id"],
                    total_files=r["total_files"],
                    total_bytes=r["total_bytes"],
                    duration_seconds=r["duration_seconds"],
                    raw_output=r["raw_output"] or "",
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Restore Attempts
    # -------------------------------------------------------------------------

    def save_restore_attempt(self, record: RestoreAttemptRecord) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO restore_attempts (
                    attempt_id, timestamp, snapshot_id, target_path, status,
                    original_manifest_id, restored_manifest_id, matched_files,
                    corrupted_files, missing_files, extra_files, duration_seconds, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.attempt_id,
                    record.timestamp,
                    record.snapshot_id,
                    record.target_path,
                    record.status,
                    record.original_manifest_id,
                    record.restored_manifest_id,
                    record.matched_files,
                    record.corrupted_files,
                    record.missing_files,
                    record.extra_files,
                    record.duration_seconds,
                    record.details,
                ),
            )

    def list_restore_attempts(self, limit: int = 50) -> List[RestoreAttemptRecord]:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM restore_attempts ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                RestoreAttemptRecord(
                    attempt_id=r["attempt_id"],
                    timestamp=r["timestamp"],
                    snapshot_id=r["snapshot_id"],
                    target_path=r["target_path"],
                    status=r["status"],
                    original_manifest_id=r["original_manifest_id"],
                    restored_manifest_id=r["restored_manifest_id"],
                    matched_files=r["matched_files"],
                    corrupted_files=r["corrupted_files"],
                    missing_files=r["missing_files"],
                    extra_files=r["extra_files"],
                    duration_seconds=r["duration_seconds"],
                    details=r["details"] or "",
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Integrity Check Records
    # -------------------------------------------------------------------------

    def save_integrity_check(self, record: IntegrityCheckRecord) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO integrity_checks (
                    check_id, timestamp, check_type, passed, exit_code, duration_seconds, raw_output
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.check_id,
                    record.timestamp,
                    record.check_type,
                    1 if record.passed else 0,
                    record.exit_code,
                    record.duration_seconds,
                    record.raw_output,
                ),
            )

    def list_integrity_checks(self, limit: int = 50) -> List[IntegrityCheckRecord]:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM integrity_checks ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                IntegrityCheckRecord(
                    check_id=r["check_id"],
                    timestamp=r["timestamp"],
                    check_type=r["check_type"],
                    passed=bool(r["passed"]),
                    exit_code=r["exit_code"],
                    duration_seconds=r["duration_seconds"],
                    raw_output=r["raw_output"] or "",
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Manifest Records
    # -------------------------------------------------------------------------

    def save_manifest(self, manifest: Manifest) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manifests (
                    manifest_id, root_path, created_at, total_files, total_bytes, manifest_hash, manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    manifest.manifest_id,
                    manifest.root_path,
                    manifest.created_at,
                    manifest.total_files,
                    manifest.total_bytes,
                    manifest.manifest_hash,
                    manifest.model_dump_json(),
                ),
            )

    def get_manifest(self, manifest_id: str) -> Optional[Manifest]:
        with self._connection() as conn:
            cur = conn.execute("SELECT manifest_json FROM manifests WHERE manifest_id = ?", (manifest_id,))
            row = cur.fetchone()
            if not row:
                return None
            return Manifest.model_validate_json(row["manifest_json"])

    # -------------------------------------------------------------------------
    # Experiment Records
    # -------------------------------------------------------------------------

    def save_experiment(self, result: ExperimentResult) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO experiments (
                    experiment_id, scenario_id, scenario_title, executed_at, passed,
                    expected_outcome, actual_observations, sanitized_output,
                    checks_json, findings_json, cleanup_status, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    result.experiment_id,
                    result.scenario_id,
                    result.scenario_title,
                    result.executed_at,
                    1 if result.passed else 0,
                    result.expected_outcome,
                    result.actual_observations,
                    result.sanitized_output,
                    json.dumps(result.checks_performed),
                    json.dumps([f.model_dump() for f in result.diagnostic_findings]),
                    result.cleanup_status,
                    json.dumps(result.evidence),
                ),
            )

    def list_experiments(self, limit: int = 50) -> List[ExperimentResult]:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM experiments ORDER BY executed_at DESC LIMIT ?",
                (limit,),
            )
            results = []
            for r in cur.fetchall():
                findings_data = json.loads(r["findings_json"] or "[]")
                results.append(
                    ExperimentResult(
                        experiment_id=r["experiment_id"],
                        scenario_id=r["scenario_id"],
                        scenario_title=r["scenario_title"],
                        executed_at=r["executed_at"],
                        passed=bool(r["passed"]),
                        expected_outcome=r["expected_outcome"] or "",
                        actual_observations=r["actual_observations"] or "",
                        sanitized_output=r["sanitized_output"] or "",
                        checks_performed=json.loads(r["checks_json"] or "[]"),
                        diagnostic_findings=findings_data,
                        cleanup_status=r["cleanup_status"] or "",
                        evidence=json.loads(r["evidence_json"] or "{}"),
                    )
                )
            return results

    # -------------------------------------------------------------------------
    # Knowledge Base CRUD and Search
    # -------------------------------------------------------------------------

    def save_knowledge_article(self, article: KnowledgeArticle) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_articles (
                    article_id, title, category, problem_symptoms, preconditions,
                    diagnostic_checks, verified_cause, resolution_steps,
                    verification_procedure, known_limitations, related_incidents_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    problem_symptoms=excluded.problem_symptoms,
                    preconditions=excluded.preconditions,
                    diagnostic_checks=excluded.diagnostic_checks,
                    verified_cause=excluded.verified_cause,
                    resolution_steps=excluded.resolution_steps,
                    verification_procedure=excluded.verification_procedure,
                    known_limitations=excluded.known_limitations,
                    related_incidents_json=excluded.related_incidents_json,
                    updated_at=excluded.updated_at;
                """,
                (
                    article.article_id,
                    article.title,
                    article.category,
                    article.problem_symptoms,
                    article.preconditions,
                    article.diagnostic_checks,
                    article.verified_cause,
                    article.resolution_steps,
                    article.verification_procedure,
                    article.known_limitations,
                    json.dumps(article.related_incident_ids),
                    article.created_at,
                    article.updated_at,
                ),
            )

            if self._fts5_available:
                try:
                    conn.execute("DELETE FROM knowledge_fts WHERE article_id = ?", (article.article_id,))
                    conn.execute(
                        """
                        INSERT INTO knowledge_fts (
                            article_id, title, category, problem_symptoms, verified_cause, resolution_steps
                        ) VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            article.article_id,
                            article.title,
                            article.category,
                            article.problem_symptoms,
                            article.verified_cause,
                            article.resolution_steps,
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Error updating FTS5 index: {e}")

    def get_knowledge_article(self, article_id: str) -> Optional[KnowledgeArticle]:
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM knowledge_articles WHERE article_id = ?", (article_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_article(row)

    def list_knowledge_articles(self, category: Optional[str] = None) -> List[KnowledgeArticle]:
        with self._connection() as conn:
            if category:
                cur = conn.execute(
                    "SELECT * FROM knowledge_articles WHERE category = ? ORDER BY article_id ASC",
                    (category,),
                )
            else:
                cur = conn.execute("SELECT * FROM knowledge_articles ORDER BY article_id ASC")
            return [self._row_to_article(r) for r in cur.fetchall()]

    def search_knowledge_base(self, query: str) -> List[KnowledgeArticle]:
        """
        Search knowledge base using SQLite FTS5 if available, with LIKE fallback.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return self.list_knowledge_articles()

        results: List[KnowledgeArticle] = []

        if self._fts5_available:
            try:
                # Sanitize query for FTS5 (escape special chars)
                fts_query = "".join(c for c in cleaned_query if c.isalnum() or c.isspace()).strip()
                if fts_query:
                    # Token-level OR search
                    fts_tokens = [f'"{tok}"*' for tok in fts_query.split() if tok]
                    match_expr = " OR ".join(fts_tokens)
                    with self._connection() as conn:
                        cur = conn.execute(
                            """
                            SELECT a.* FROM knowledge_articles a
                            JOIN knowledge_fts f ON a.article_id = f.article_id
                            WHERE knowledge_fts MATCH ?
                            ORDER BY rank
                            LIMIT 20;
                            """,
                            (match_expr,),
                        )
                        results = [self._row_to_article(r) for r in cur.fetchall()]
                        if results:
                            return results
            except Exception as e:
                logger.warning(f"FTS5 query failed: {e}. Falling back to substring search.")

        # Fallback substring search across key fields
        like_expr = f"%{cleaned_query}%"
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM knowledge_articles
                WHERE title LIKE ?
                   OR problem_symptoms LIKE ?
                   OR verified_cause LIKE ?
                   OR resolution_steps LIKE ?
                   OR category LIKE ?
                ORDER BY article_id ASC
                LIMIT 20;
                """,
                (like_expr, like_expr, like_expr, like_expr, like_expr),
            )
            return [self._row_to_article(r) for r in cur.fetchall()]

    def _row_to_article(self, row: sqlite3.Row) -> KnowledgeArticle:
        return KnowledgeArticle(
            article_id=row["article_id"],
            title=row["title"],
            category=row["category"],
            problem_symptoms=row["problem_symptoms"],
            preconditions=row["preconditions"] or "",
            diagnostic_checks=row["diagnostic_checks"] or "",
            verified_cause=row["verified_cause"] or "",
            resolution_steps=row["resolution_steps"] or "",
            verification_procedure=row["verification_procedure"] or "",
            known_limitations=row["known_limitations"] or "",
            related_incident_ids=json.loads(row["related_incidents_json"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
