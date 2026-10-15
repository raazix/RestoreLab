"""
RestoreLab Backup Engine Base Abstraction
Defines the contract and structured result types for backup engines,
ensuring loose coupling, testability, and deterministic failure reporting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class CommandExecutionResult(BaseModel):
    """Raw, sanitized outcome of a subprocess execution."""

    command: List[str] = Field(description="Sanitized argument list")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(default="", description="Sanitized stdout text")
    stderr: str = Field(default="", description="Sanitized stderr text")
    duration_seconds: float = Field(default=0.0, ge=0.0)
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class SnapshotInfo(BaseModel):
    """Normalized snapshot representation."""

    id: str = Field(description="Short snapshot ID (e.g. 8 characters)")
    full_id: str = Field(description="Complete snapshot hex ID")
    time: str = Field(description="ISO timestamp of snapshot creation")
    paths: List[str] = Field(default_factory=list, description="Original source paths")
    hostname: str = Field(default="", description="Host identifier")
    username: str = Field(default="", description="Backup user identifier")
    tags: List[str] = Field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None


class RepositoryStatus(BaseModel):
    """State of repository connectivity and accessibility."""

    initialized: bool
    accessible: bool
    error_message: Optional[str] = None
    raw_output: str = ""


class IntegrityCheckResult(BaseModel):
    """Outcome of repository integrity verification."""

    check_type: Literal["index_only", "full_read_data"]
    passed: bool
    exit_code: int
    details: str
    duration_seconds: float
    raw_output: str


class BackupResult(BaseModel):
    """Structured report of a backup run."""

    snapshot_id: Optional[str] = None
    files_new: int = 0
    files_changed: int = 0
    files_unmodified: int = 0
    bytes_added: int = 0
    total_files_processed: int = 0
    total_bytes_processed: int = 0
    duration_seconds: float = 0.0
    execution_result: CommandExecutionResult
    raw_json: Optional[Dict[str, Any]] = None


class RestoreResult(BaseModel):
    """Structured report of a restore operation."""

    snapshot_id: str
    target_dir: str
    duration_seconds: float = 0.0
    execution_result: CommandExecutionResult


class BackupEngine(ABC):
    """Abstract interface defining the backup engine contract."""

    @abstractmethod
    def get_status(self) -> RepositoryStatus:
        """Inspect repository status without altering state."""
        pass

    @abstractmethod
    def init_repository(self) -> CommandExecutionResult:
        """Initialize a new repository at the configured target."""
        pass

    @abstractmethod
    def check_repository(self, read_data: bool = False) -> IntegrityCheckResult:
        """Execute repository-level integrity validation."""
        pass

    @abstractmethod
    def create_backup(
        self,
        source_dir: Path | str,
        tags: Optional[List[str]] = None,
    ) -> BackupResult:
        """Create a new backup snapshot from the approved source directory."""
        pass

    @abstractmethod
    def list_snapshots(self) -> List[SnapshotInfo]:
        """Enumerate all available snapshots in the repository."""
        pass

    @abstractmethod
    def restore_snapshot(
        self,
        snapshot_id: str,
        target_dir: Path | str,
        include_paths: Optional[List[str]] = None,
        subfolder: Optional[str] = None,
    ) -> RestoreResult:
        """Restore a snapshot into an isolated destination directory."""
        pass
