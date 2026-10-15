"""
RestoreLab Data Models for Incidents, Audit Trails, and Knowledge Base
Defines persistent entities with strict typing, JSON serialization, and audit metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from restorelab.diagnostics.rules import DiagnosticFinding

IncidentStatus = Literal["open", "investigating", "mitigated", "resolved", "closed"]
IncidentSeverity = Literal["critical", "high", "medium", "low"]
OperationType = Literal["backup", "restore", "check", "experiment", "manifest_scan"]


class IncidentRecord(BaseModel):
    """Structured operational incident record with diagnostic history."""

    incident_id: str = Field(
        default_factory=lambda: f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    title: str
    status: IncidentStatus = "open"
    severity: IncidentSeverity = "medium"
    category: str = "general"
    operation_type: OperationType = "backup"
    operation_id: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)
    findings: List[DiagnosticFinding] = Field(default_factory=list)
    verified_resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class BackupRunRecord(BaseModel):
    """Audit log entry for an executed backup operation."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_path: str
    snapshot_id: Optional[str] = None
    status: Literal["success", "failed", "warning"] = "success"
    manifest_id: Optional[str] = None
    total_files: int = 0
    total_bytes: int = 0
    duration_seconds: float = 0.0
    raw_output: str = ""


class RestoreAttemptRecord(BaseModel):
    """Audit log entry for a recovery verification or restore attempt."""

    attempt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    snapshot_id: str
    target_path: str
    status: Literal["PASSED", "FAILED", "WARNING", "INCONCLUSIVE"] = "PASSED"
    original_manifest_id: Optional[str] = None
    restored_manifest_id: Optional[str] = None
    matched_files: int = 0
    corrupted_files: int = 0
    missing_files: int = 0
    extra_files: int = 0
    duration_seconds: float = 0.0
    details: str = ""


class IntegrityCheckRecord(BaseModel):
    """Audit log entry for a repository-level integrity validation."""

    check_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    check_type: Literal["index_only", "full_read_data"] = "index_only"
    passed: bool = True
    exit_code: int = 0
    duration_seconds: float = 0.0
    raw_output: str = ""


class KnowledgeArticle(BaseModel):
    """Curated troubleshooting article with verified post-mortem data."""

    article_id: str
    title: str
    category: str
    problem_symptoms: str
    preconditions: str = ""
    diagnostic_checks: str = ""
    verified_cause: str = ""
    resolution_steps: str = ""
    verification_procedure: str = ""
    known_limitations: str = ""
    related_incident_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
