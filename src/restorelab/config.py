"""
RestoreLab Configuration and Safety Governance Module
Provides validated environment settings, strict filesystem isolation guards,
and credential redaction for operational safety.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class RestoreLabSettings(BaseSettings):
    """Strongly typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Restic Engine Configuration
    restic_binary_path: str = Field(
        default="bin/restic.exe",
        description="Path to restic binary or executable name on system PATH",
    )
    restic_repository: str = Field(
        default="./data/lab_repo",
        description="Local repository path for lab backups",
    )
    restic_password: str = Field(
        default="restorelab-lab-secret-passphrase-change-in-prod",
        description="Restic repository encryption password",
    )
    restic_cache_dir: Optional[str] = Field(
        default="./data/restic_cache",
        description="Local cache directory for restic metadata",
    )

    # Lab Boundary Paths
    lab_source_dir: str = Field(
        default="./data/lab_source",
        description="Approved local source data directory for lab backups",
    )
    lab_restore_dir: str = Field(
        default="./data/lab_restore",
        description="Isolated sandbox directory for recovery operations",
    )
    lab_experiments_dir: str = Field(
        default="./data/lab_experiments",
        description="Disposable scratch directory for failure experiments",
    )

    # Database
    database_path: str = Field(
        default="./data/restorelab.db",
        description="SQLite database path for incidents, manifests, and audit trails",
    )

    # Operational Controls
    log_level: str = Field(default="INFO", description="Logging verbosity")
    command_timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=1800,
        description="Subprocess execution timeout in seconds",
    )
    max_source_scan_mb: int = Field(
        default=500,
        ge=1,
        le=10000,
        description="Safety threshold for lab source scans in megabytes",
    )
    max_manifest_files: int = Field(
        default=10000,
        ge=10,
        le=500000,
        description="Maximum file count permitted in a single manifest scan",
    )

    # Optional Supermemory Extension
    supermemory_enabled: bool = Field(
        default=False,
        description="Whether remote Supermemory incident memory adapter is active",
    )
    supermemory_api_key: Optional[str] = Field(
        default=None,
        description="API key for Supermemory integration",
    )
    supermemory_namespace: str = Field(
        default="restorelab-incidents",
        description="Supermemory v5 namespace for scoped incident isolation",
    )
    supermemory_workspace_id: Optional[str] = Field(
        default=None,
        description="Supermemory workspace ID",
    )
    supermemory_api_url: str = Field(
        default="https://api.supermemory.ai",
        description="Supermemory API base URL",
    )

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    def resolve_path(self, relative_or_abs: str | Path) -> Path:
        """Resolve a path relative to PROJECT_ROOT if not already absolute."""
        p = Path(relative_or_abs)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        else:
            p = p.resolve()
        return p

    @property
    def resolved_repository(self) -> Path:
        return self.resolve_path(self.restic_repository)

    @property
    def resolved_source_dir(self) -> Path:
        return self.resolve_path(self.lab_source_dir)

    @property
    def resolved_restore_dir(self) -> Path:
        return self.resolve_path(self.lab_restore_dir)

    @property
    def resolved_experiments_dir(self) -> Path:
        return self.resolve_path(self.lab_experiments_dir)

    @property
    def resolved_database_path(self) -> Path:
        return self.resolve_path(self.database_path)

    @property
    def resolved_cache_dir(self) -> Optional[Path]:
        if self.restic_cache_dir:
            return self.resolve_path(self.restic_cache_dir)
        return None

    def find_restic_binary(self) -> Optional[Path]:
        """
        Locates the restic executable.
        Checks:
        1. Configured path (resolved against PROJECT_ROOT if relative)
        2. bin/restic.exe in PROJECT_ROOT
        3. bin/restic in PROJECT_ROOT
        4. System PATH via shutil.which('restic')
        """
        # 1. Configured path
        candidate = self.resolve_path(self.restic_binary_path)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

        # 2. Project bin/restic.exe or bin/restic
        for default_name in ("restic.exe", "restic", "restic_0.19.1_windows_amd64.exe"):
            p = PROJECT_ROOT / "bin" / default_name
            if p.is_file():
                return p.resolve()

        # 3. System PATH
        which_path = shutil.which("restic")
        if which_path:
            return Path(which_path).resolve()

        return None

    def ensure_directories(self) -> None:
        """Create lab directories and database parent directories safely."""
        self.resolved_source_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_restore_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_experiments_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_repository.parent.mkdir(parents=True, exist_ok=True)
        self.resolved_database_path.parent.mkdir(parents=True, exist_ok=True)
        if self.resolved_cache_dir:
            self.resolved_cache_dir.mkdir(parents=True, exist_ok=True)

    def is_safe_restore_target(self, target_path: Path | str) -> Tuple[bool, str]:
        """
        Verify that a restore target path complies with safety boundaries.
        Rules:
        - Target must resolve to an absolute path.
        - Target must be contained within lab_restore_dir OR lab_experiments_dir.
        - Target must NEVER be equal to or a parent of lab_source_dir (prevent in-place overwrite).
        - Target must NEVER be inside or equal to restic_repository.
        - Target must NEVER be root drive or user profile root.
        """
        target = self.resolve_path(target_path)
        restore_root = self.resolved_restore_dir
        exp_root = self.resolved_experiments_dir
        source_root = self.resolved_source_dir
        repo_root = self.resolved_repository

        # Check root drive
        if target == target.anchor or str(target) in ("/", "\\", "C:\\", "C:/"):
            return False, "Target cannot be a root drive"

        # Check home directory safety
        home = Path.home().resolve()
        if target == home:
            return False, "Target cannot be the user home root directory"

        # Check repository overlap
        try:
            target.relative_to(repo_root)
            return False, f"Target is inside the repository directory: {repo_root}"
        except ValueError:
            pass
        if target == repo_root:
            return False, "Target cannot be the repository directory"

        # Check source overlap (strictly forbidden to overwrite source)
        if target == source_root:
            return False, "Target cannot be the source directory (in-place restore forbidden)"
        try:
            source_root.relative_to(target)
            return False, "Target is an ancestor of the source directory"
        except ValueError:
            pass

        # Target must be contained within approved isolation roots
        inside_restore = False
        try:
            target.relative_to(restore_root)
            inside_restore = True
        except ValueError:
            pass

        inside_exp = False
        try:
            target.relative_to(exp_root)
            inside_exp = True
        except ValueError:
            pass

        if not (inside_restore or inside_exp):
            return (
                False,
                f"Target path '{target}' is not within approved restore sandbox ({restore_root}) or experiment root ({exp_root})",
            )

        return True, "Path is within approved isolation bounds"

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize raw output, terminal logs, or exceptions.
        Redacts passwords, sensitive tokens, and user home paths.
        """
        if not text:
            return ""

        sanitized = text

        # Redact configured restic password if present
        if self.restic_password and len(self.restic_password) > 3:
            sanitized = sanitized.replace(self.restic_password, "[REDACTED_PASSWORD]")

        # Redact supermemory API key if configured
        if self.supermemory_api_key and len(self.supermemory_api_key) > 4:
            sanitized = sanitized.replace(self.supermemory_api_key, "[REDACTED_API_KEY]")

        # Redact common password command patterns
        sanitized = re.sub(
            r"(--password-file|--password-command|RESTIC_PASSWORD)=([^\s]+)",
            r"\1=[REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Redact bearer tokens
        sanitized = re.sub(
            r"Bearer\s+[A-Za-z0-9_\-\.]{10,}",
            "Bearer [REDACTED_TOKEN]",
            sanitized,
        )

        # Redact any supermemory key pattern
        sanitized = re.sub(
            r"sm_[A-Za-z0-9_-]{20,}",
            "[REDACTED_SUPERMEMORY_KEY]",
            sanitized,
        )

        return sanitized


# Global singleton settings instance
_settings: Optional[RestoreLabSettings] = None


def get_settings() -> RestoreLabSettings:
    """Return cached singleton configuration instance."""
    global _settings
    if _settings is None:
        _settings = RestoreLabSettings()
    return _settings


def setup_logging(level_name: Optional[str] = None) -> logging.Logger:
    """Configure structured logging for RestoreLab."""
    settings = get_settings()
    level = getattr(logging, (level_name or settings.log_level).upper(), logging.INFO)

    logger = logging.getLogger("restorelab")
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(module)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
