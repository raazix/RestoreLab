"""
RestoreLab REST API Backend
Exposes endpoints for the Linear-inspired React reliability workbench.
"""

from __future__ import annotations

import hashlib
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project src is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from restorelab.backup.base import CommandExecutionResult
from restorelab.backup.restic import ResticBackupEngine
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.diagnostics.rules import DiagnosticFinding
from restorelab.experiments.runner import ExperimentResult, ExperimentRunner
from restorelab.experiments.scenarios import ALL_SCENARIOS, get_scenario_by_id
from restorelab.incidents.models import (
    BackupRunRecord,
    IncidentRecord,
    IncidentSeverity,
    IncidentStatus,
    IntegrityCheckRecord,
    KnowledgeArticle,
    RestoreAttemptRecord,
)
from restorelab.incidents.repository import IncidentRepository
from restorelab.knowledge.provider import SearchResult
from restorelab.knowledge.sqlite_search import SQLiteKnowledgeProvider
from restorelab.knowledge.supermemory_adapter import SupermemoryAdapter
from restorelab.reporting.exports import (
    export_incident_markdown,
    export_verification_markdown,
)
from restorelab.verification.manifest import (
    Manifest,
    ManifestComparisonResult,
    compare_manifests,
    generate_manifest,
)
from restorelab.verification.restore import (
    RecoveryVerificationReport,
    verify_recovery,
)
from restorelab.verification.sample_data import generate_lab_dataset

logger = setup_logging()

# ==============================================================================
# Global Application State Container
# ==============================================================================
class AppContext:
    def __init__(self) -> None:
        self.settings: RestoreLabSettings = get_settings()
        self.settings.ensure_directories()
        self.repo: IncidentRepository = IncidentRepository()
        self.engine: ResticBackupEngine = ResticBackupEngine(self.settings)
        self.diag_engine: DiagnosticEngine = DiagnosticEngine()
        self.exp_runner: ExperimentRunner = ExperimentRunner(self.settings, self.diag_engine)
        self.kb_provider: SQLiteKnowledgeProvider = SQLiteKnowledgeProvider(self.repo)
        self.supermemory: SupermemoryAdapter = SupermemoryAdapter(
            self.settings, fallback_provider=self.kb_provider
        )


app_ctx = AppContext()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure lab directories and database tables exist
    app_ctx.settings.ensure_directories()
    app_ctx.repo.init_database()
    logger.info("RestoreLab REST API initialized successfully.")
    yield


app = FastAPI(
    title="RestoreLab API",
    description="REST backend for RestoreLab Backup Integrity & Recovery Verification Workbench",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Request/Response Schemas
# ==============================================================================
class BackupRequest(BaseModel):
    tags: List[str] = Field(default_factory=lambda: ["manual", "lab"])


class IntegrityCheckRequest(BaseModel):
    read_data: bool = False


class RestoreVerifyRequest(BaseModel):
    snapshot_id: str
    subfolder: Optional[str] = None


class IncidentUpdateRequest(BaseModel):
    status: IncidentStatus
    resolution: Optional[str] = None
    note: Optional[str] = None


class SupermemorySyncRequest(BaseModel):
    consent: bool


class SupermemoryTestResponse(BaseModel):
    success: bool
    message: str
    namespace: str
    api_url: str


# ==============================================================================
# System & Health Endpoints
# ==============================================================================
@app.get("/api/system/status")
def get_system_status():
    """Retrieve runtime environment, binary detection, and path status."""
    binary_status = app_ctx.settings.find_restic_binary()
    return {
        "restic_installed": binary_status is not None,
        "restic_binary_path": str(binary_status) if binary_status else None,
        "repository_path": str(app_ctx.settings.resolved_repository),
        "database_path": str(app_ctx.settings.resolved_database_path),
        "lab_source": str(app_ctx.settings.resolved_source_dir),
        "lab_restore": str(app_ctx.settings.resolved_restore_dir),
        "lab_experiments": str(app_ctx.settings.resolved_experiments_dir),
        "supermemory_enabled": app_ctx.settings.supermemory_enabled,
        "supermemory_namespace": app_ctx.settings.supermemory_namespace,
        "command_timeout_seconds": app_ctx.settings.command_timeout_seconds,
        "max_source_scan_mb": app_ctx.settings.max_source_scan_mb,
    }


@app.get("/api/dashboard")
def get_dashboard_metrics():
    """Retrieve operational reliability metrics and recent activity."""
    backup_runs = app_ctx.repo.list_backup_runs(limit=100)
    restore_attempts = app_ctx.repo.list_restore_attempts(limit=100)
    open_incidents = app_ctx.repo.list_incidents(status="open")
    checks = app_ctx.repo.list_integrity_checks(limit=10)

    total_backups = len(backup_runs)
    total_restores = len(restore_attempts)
    passed_restores = sum(1 for r in restore_attempts if r.status == "PASSED")
    verification_ratio = (
        round((passed_restores / total_restores) * 100, 1) if total_restores > 0 else 0.0
    )

    last_check_status = checks[0].passed if checks else None

    return {
        "total_backups": total_backups,
        "total_restores": total_restores,
        "passed_restores": passed_restores,
        "verification_ratio": verification_ratio,
        "open_incidents_count": len(open_incidents),
        "last_integrity_check_passed": last_check_status,
        "recent_backup_runs": [run.model_dump() for run in backup_runs[:5]],
        "recent_restore_attempts": [att.model_dump() for att in restore_attempts[:5]],
        "open_incidents": [inc.model_dump() for inc in open_incidents[:5]],
    }


# ==============================================================================
# Backup Operations
# ==============================================================================
@app.get("/api/backups")
def list_backups(limit: int = 50):
    """List historical backup run audit logs."""
    runs = app_ctx.repo.list_backup_runs(limit=limit)
    return [run.model_dump() for run in runs]


@app.post("/api/backups/generate-sample")
def generate_sample_data():
    """Populate lab source directory with realistic multi-type test data."""
    try:
        source_dir = app_ctx.settings.resolved_source_dir
        file_count, total_bytes = generate_lab_dataset(source_dir)
        files = [
            str(p.relative_to(source_dir))
            for p in source_dir.rglob("*")
            if p.is_file()
        ]
        return {
            "success": True,
            "message": f"Generated {file_count} test files ({total_bytes} bytes)",
            "file_count": file_count,
            "total_bytes": total_bytes,
            "files": files,
        }
    except Exception as e:
        logger.error(f"Failed to generate sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backups/manifest")
def generate_source_manifest():
    """Compute deterministic SHA-256 baseline manifest for source directory."""
    source_dir = app_ctx.settings.resolved_source_dir
    if not source_dir.exists():
        raise HTTPException(status_code=400, detail=f"Source directory does not exist: {source_dir}")

    try:
        manifest = generate_manifest(
            source_dir,
            max_files=app_ctx.settings.max_manifest_files,
            max_total_bytes=app_ctx.settings.max_source_scan_mb * 1024 * 1024,
        )
        app_ctx.repo.save_manifest(manifest)
        return manifest.model_dump()
    except Exception as e:
        logger.error(f"Manifest generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backups/init-repo")
def initialize_repository():
    """Initialize encrypted local Restic repository."""
    result = app_ctx.engine.init_repository()
    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_seconds": result.duration_seconds,
    }


@app.post("/api/backups/run")
def execute_backup(req: BackupRequest):
    """Execute genuine Restic backup subprocess and record audit trail."""
    source_dir = app_ctx.settings.resolved_source_dir
    if not source_dir.exists():
        raise HTTPException(status_code=400, detail="Source directory does not exist")

    result = app_ctx.engine.backup(source_dir, tags=req.tags)

    # Compute pre-manifest if possible
    manifest_id = None
    try:
        manifest = generate_manifest(
            source_dir,
            max_files=app_ctx.settings.max_manifest_files,
            max_total_bytes=app_ctx.settings.max_source_scan_mb * 1024 * 1024,
        )
        app_ctx.repo.save_manifest(manifest)
        manifest_id = manifest.id
    except Exception:
        pass

    # Record in SQLite
    run_record = BackupRunRecord(
        source_path=str(source_dir),
        snapshot_id=result.metadata.get("snapshot_id") if result.metadata else None,
        status="success" if result.success else "failed",
        manifest_id=manifest_id,
        total_files=result.metadata.get("files_new", 0) + result.metadata.get("files_changed", 0) if result.metadata else 0,
        total_bytes=result.metadata.get("data_added", 0) if result.metadata else 0,
        duration_seconds=result.duration_seconds,
        raw_output=result.stdout if result.success else result.stderr,
    )
    app_ctx.repo.record_backup_run(run_record)

    return {
        "success": result.success,
        "snapshot_id": run_record.snapshot_id,
        "duration_seconds": result.duration_seconds,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "run_record": run_record.model_dump(),
    }


@app.post("/api/backups/check")
def check_repository_integrity(req: IntegrityCheckRequest):
    """Run fast index check or deep data block verification."""
    result = app_ctx.engine.check(read_data=req.read_data)

    check_record = IntegrityCheckRecord(
        check_type="full_read_data" if req.read_data else "index_only",
        passed=result.success,
        exit_code=result.exit_code,
        duration_seconds=result.duration_seconds,
        raw_output=result.stdout if result.success else result.stderr,
    )
    app_ctx.repo.record_integrity_check(check_record)

    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "check_record": check_record.model_dump(),
    }


# ==============================================================================
# Snapshots & Recovery Verification
# ==============================================================================
@app.get("/api/snapshots")
def list_snapshots():
    """Retrieve all available snapshots from the Restic repository."""
    snapshots = app_ctx.engine.list_snapshots()
    return snapshots


@app.post("/api/restore/verify")
def verify_snapshot_recovery(req: RestoreVerifyRequest):
    """Execute isolated sandbox restore and cryptographically verify recovery."""
    try:
        report = verify_recovery(
            engine=app_ctx.engine,
            repository=app_ctx.repo,
            snapshot_id=req.snapshot_id,
            subfolder=req.subfolder,
            diagnostic_engine=app_ctx.diag_engine,
        )
        return report.model_dump()
    except Exception as e:
        logger.error(f"Recovery verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Incident Explorer & Triage
# ==============================================================================
@app.get("/api/incidents")
def list_incidents(status: Optional[str] = None, limit: int = 50):
    """List operational incident records with optional status filter."""
    incidents = app_ctx.repo.list_incidents(status=status, limit=limit)
    return [inc.model_dump() for inc in incidents]


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    """Retrieve a specific incident record with full diagnostic details."""
    incident = app_ctx.repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@app.patch("/api/incidents/{incident_id}")
def update_incident(incident_id: str, req: IncidentUpdateRequest):
    """Update incident lifecycle status and resolution notes."""
    incident = app_ctx.repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = req.status
    if req.resolution:
        incident.verified_resolution = req.resolution
        incident.resolved_at = datetime.now(timezone.utc).isoformat()
        incident.resolved_by = "Engineer"
    if req.note:
        incident.notes.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {req.note}")

    app_ctx.repo.update_incident(incident)
    return incident.model_dump()


@app.post("/api/incidents/{incident_id}/preview-sanitized")
def preview_sanitized_telemetry(incident_id: str):
    """Preview the exact scrubbed JSON payload before Supermemory transmission."""
    incident = app_ctx.repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    payload = app_ctx.supermemory.preview_sanitized_payload(incident)
    return payload


@app.post("/api/incidents/{incident_id}/sync-supermemory")
def sync_incident_to_supermemory(incident_id: str, req: SupermemorySyncRequest):
    """Sync sanitized incident knowledge into Supermemory v5 with explicit consent."""
    if not req.consent:
        raise HTTPException(
            status_code=400,
            detail="Explicit operator consent required before sending incident telemetry remotely.",
        )

    incident = app_ctx.repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    result = app_ctx.supermemory.index_incident(incident)
    return {
        "success": result.success,
        "memory_id": result.memory_id,
        "message": result.message,
        "fallback_used": result.fallback_used,
    }


# ==============================================================================
# Knowledge Base & Search
# ==============================================================================
@app.get("/api/knowledge/search")
def search_knowledge(query: str, use_supermemory: bool = False, limit: int = 10):
    """Search troubleshooting articles and historical incidents."""
    if not query.strip():
        return []

    if use_supermemory and app_ctx.settings.supermemory_enabled:
        results = app_ctx.supermemory.search(query, limit=limit)
    else:
        results = app_ctx.kb_provider.search(query, limit=limit)

    return [r.model_dump() for r in results]


@app.get("/api/knowledge/articles")
def list_knowledge_articles():
    """List curated troubleshooting articles."""
    articles = app_ctx.repo.list_knowledge_articles()
    return [art.model_dump() for art in articles]


# ==============================================================================
# Controlled Failure Experiments
# ==============================================================================
@app.get("/api/experiments")
def list_experiments():
    """List all available controlled failure scenarios with safety invariants."""
    return [
        {
            "id": s.scenario_id,
            "title": s.title,
            "description": s.description,
            "expected_outcome": s.expected_outcome,
            "target_rule_id": s.target_rule_id,
            "deterministic_rule": s.target_rule_id,
            "preconditions": s.preconditions,
        }
        for s in ALL_SCENARIOS
    ]


@app.post("/api/experiments/{scenario_id}/run")
def run_experiment_scenario(scenario_id: str):
    """Execute a controlled failure scenario in an isolated disposable scratchpad."""
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = app_ctx.exp_runner.run_scenario(scenario)
    return result.model_dump()


# ==============================================================================
# Post-Mortems & Verification Reports
# ==============================================================================
@app.get("/api/reports/incident/{incident_id}")
def export_incident_report(incident_id: str):
    """Generate Markdown post-mortem with cryptographic SHA-256 fingerprint."""
    incident = app_ctx.repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    markdown_text = export_incident_markdown(incident)
    fingerprint = hashlib.sha256(markdown_text.encode("utf-8")).hexdigest()
    return {
        "incident_id": incident.incident_id,
        "title": incident.title,
        "sha256_fingerprint": fingerprint,
        "markdown": markdown_text,
    }


@app.get("/api/reports/restore/{attempt_id}")
def export_restore_report(attempt_id: str):
    """Generate Markdown verification report for a restore attempt."""
    attempts = app_ctx.repo.list_restore_attempts(limit=100)
    matched = next((a for a in attempts if a.attempt_id == attempt_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail="Restore attempt not found")

    report = RecoveryVerificationReport(
        snapshot_id=matched.snapshot_id,
        timestamp=matched.timestamp,
        status=matched.status,
        original_manifest_id=matched.original_manifest_id or "NONE",
        restored_manifest_id=matched.restored_manifest_id,
        restore_target_path=matched.target_path,
        resolved_content_path=matched.target_path,
        duration_seconds=matched.duration_seconds,
        diagnostics_summary=matched.details,
    )
    markdown_text = export_verification_markdown(report)
    fingerprint = hashlib.sha256(markdown_text.encode("utf-8")).hexdigest()
    return {
        "attempt_id": matched.attempt_id,
        "snapshot_id": matched.snapshot_id,
        "status": matched.status,
        "sha256_fingerprint": fingerprint,
        "markdown": markdown_text,
    }


# ==============================================================================
# Settings & Configuration
# ==============================================================================
@app.get("/api/settings")
def get_settings_view():
    """Retrieve verified active configuration with credentials redacted."""
    s = app_ctx.settings
    return {
        "restic_binary_path": str(s.find_restic_binary() or s.restic_binary_path),
        "repository_path": str(s.resolved_repository),
        "database_path": str(s.resolved_database_path),
        "lab_source": str(s.resolved_source_dir),
        "lab_restore": str(s.resolved_restore_dir),
        "lab_experiments": str(s.resolved_experiments_dir),
        "command_timeout_seconds": s.command_timeout_seconds,
        "max_source_scan_mb": s.max_source_scan_mb,
        "max_manifest_files": s.max_manifest_files,
        "log_level": s.log_level,
        "supermemory_enabled": s.supermemory_enabled,
        "supermemory_api_url": s.supermemory_api_url,
        "supermemory_namespace": s.supermemory_namespace,
        "supermemory_key_configured": bool(s.supermemory_api_key),
    }


@app.post("/api/settings/test-supermemory", response_model=SupermemoryTestResponse)
def test_supermemory():
    """Probe the Supermemory API connection non-destructively."""
    result = app_ctx.supermemory.test_connection()
    return SupermemoryTestResponse(
        success=result.success,
        message=result.message,
        namespace=app_ctx.settings.supermemory_namespace,
        api_url=app_ctx.settings.supermemory_api_url,
    )


# ==============================================================================
# Static Files (Production Frontend Build)
# ==============================================================================
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
