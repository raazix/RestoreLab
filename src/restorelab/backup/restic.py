"""
RestoreLab Restic Backup Engine Implementation
Wraps the official Restic CLI via safe, hardened subprocess execution,
environment-injected credentials, JSON output parsing, and structured diagnostics.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from restorelab.backup.base import (
    BackupEngine,
    BackupResult,
    CommandExecutionResult,
    IntegrityCheckResult,
    RepositoryStatus,
    RestoreResult,
    SnapshotInfo,
)
from restorelab.config import RestoreLabSettings, get_settings, setup_logging

logger = setup_logging()


class ResticBackupEngine(BackupEngine):
    """
    Production-grade Restic wrapper.
    Ensures safe execution, credential isolation via subprocess env,
    path containment validation, and structured telemetry.
    """

    def __init__(
        self,
        settings: Optional[RestoreLabSettings] = None,
        custom_binary_path: Optional[Path | str] = None,
        custom_repository: Optional[Path | str] = None,
        custom_password: Optional[str] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._custom_binary_path = (
            Path(custom_binary_path).resolve() if custom_binary_path else None
        )
        self._custom_repository = (
            Path(custom_repository).resolve() if custom_repository else None
        )
        self._custom_password = custom_password

    @property
    def binary_path(self) -> Optional[Path]:
        if self._custom_binary_path:
            return self._custom_binary_path
        return self.settings.find_restic_binary()

    @property
    def repository_path(self) -> Path:
        if self._custom_repository:
            return self._custom_repository
        return self.settings.resolved_repository

    @property
    def password(self) -> str:
        if self._custom_password is not None:
            return self._custom_password
        return self.settings.restic_password

    def _build_env(self) -> Dict[str, str]:
        """Construct isolated subprocess environment with credentials injected."""
        env = os.environ.copy()
        env["RESTIC_PASSWORD"] = self.password
        env["RESTIC_REPOSITORY"] = str(self.repository_path)
        if self.settings.resolved_cache_dir:
            env["RESTIC_CACHE_DIR"] = str(self.settings.resolved_cache_dir)
        return env

    def _execute(
        self,
        subcommand_args: List[str],
        timeout_seconds: Optional[int] = None,
    ) -> CommandExecutionResult:
        """
        Execute restic CLI safely with argument lists.
        Handles missing binary, timeouts, sanitization, and timing.
        """
        binary = self.binary_path
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()

        if not binary or not binary.is_file():
            ended_at = datetime.now(timezone.utc).isoformat()
            duration = time.perf_counter() - t0
            msg = (
                f"Restic binary not found at '{binary or 'None'}'. "
                f"Verify RESTIC_BINARY_PATH in .env or run scripts/download_restic.ps1."
            )
            logger.error(msg)
            return CommandExecutionResult(
                command=["restic"] + subcommand_args,
                exit_code=127,
                stdout="",
                stderr=msg,
                duration_seconds=round(duration, 3),
                started_at=started_at,
                ended_at=ended_at,
                timed_out=False,
            )

        cmd = [str(binary)] + subcommand_args
        timeout = timeout_seconds or self.settings.command_timeout_seconds

        try:
            proc = subprocess.run(
                cmd,
                env=self._build_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            duration = time.perf_counter() - t0
            ended_at = datetime.now(timezone.utc).isoformat()

            sanitized_stdout = self.settings.sanitize_text(proc.stdout)
            sanitized_stderr = self.settings.sanitize_text(proc.stderr)

            # Sanitize command representation (remove passwords if any sneaked in)
            sanitized_cmd = [self.settings.sanitize_text(c) for c in cmd]

            return CommandExecutionResult(
                command=sanitized_cmd,
                exit_code=proc.returncode,
                stdout=sanitized_stdout,
                stderr=sanitized_stderr,
                duration_seconds=round(duration, 3),
                started_at=started_at,
                ended_at=ended_at,
                timed_out=False,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - t0
            ended_at = datetime.now(timezone.utc).isoformat()
            raw_err = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else str(exc.stderr or "")
            )
            err_msg = f"Command timed out after {timeout} seconds: {raw_err}"
            logger.warning(err_msg)
            return CommandExecutionResult(
                command=[str(binary)] + subcommand_args,
                exit_code=124,
                stdout="",
                stderr=self.settings.sanitize_text(err_msg),
                duration_seconds=round(duration, 3),
                started_at=started_at,
                ended_at=ended_at,
                timed_out=True,
            )
        except Exception as e:
            duration = time.perf_counter() - t0
            ended_at = datetime.now(timezone.utc).isoformat()
            err_msg = f"Unexpected execution failure: {type(e).__name__}: {str(e)}"
            logger.error(err_msg)
            return CommandExecutionResult(
                command=[str(binary)] + subcommand_args,
                exit_code=1,
                stdout="",
                stderr=self.settings.sanitize_text(err_msg),
                duration_seconds=round(duration, 3),
                started_at=started_at,
                ended_at=ended_at,
                timed_out=False,
            )

    def get_status(self) -> RepositoryStatus:
        """
        Check if the configured repository exists and is accessible.
        Uses `restic snapshots --json --latest 1`.
        """
        if not self.repository_path.exists():
            return RepositoryStatus(
                initialized=False,
                accessible=False,
                error_message=f"Repository path does not exist: {self.repository_path}",
                raw_output="",
            )

        res = self._execute(["snapshots", "--json", "--latest", "1"])
        if res.exit_code == 0:
            return RepositoryStatus(
                initialized=True,
                accessible=True,
                error_message=None,
                raw_output=res.stdout,
            )

        # Diagnose known repository errors
        stderr_lower = res.stderr.lower()
        if "is there a repository at the following location" in stderr_lower or "config file not found" in stderr_lower:
            return RepositoryStatus(
                initialized=False,
                accessible=False,
                error_message="Repository exists on filesystem but has not been initialized with 'restic init'.",
                raw_output=res.stderr,
            )
        elif "wrong password" in stderr_lower or "keystore" in stderr_lower:
            return RepositoryStatus(
                initialized=True,
                accessible=False,
                error_message="Authentication failed: incorrect repository password.",
                raw_output=res.stderr,
            )

        return RepositoryStatus(
            initialized=False,
            accessible=False,
            error_message=f"Repository check failed with exit code {res.exit_code}: {res.stderr.strip()}",
            raw_output=res.stderr,
        )

    def init_repository(self) -> CommandExecutionResult:
        """Initialize a new Restic repository."""
        self.repository_path.parent.mkdir(parents=True, exist_ok=True)
        return self._execute(["init"])

    def check_repository(self, read_data: bool = False) -> IntegrityCheckResult:
        """
        Validate repository integrity.
        read_data=False: checks index, pack headers, and snapshot trees (fast).
        read_data=True: reads and verifies all data chunks byte-for-byte (deep).
        """
        args = ["check"]
        if read_data:
            args.append("--read-data")

        res = self._execute(args)
        passed = res.exit_code == 0
        details = (
            "Repository integrity verified successfully."
            if passed
            else f"Integrity check failed: {res.stderr.strip() or res.stdout.strip()}"
        )

        return IntegrityCheckResult(
            check_type="full_read_data" if read_data else "index_only",
            passed=passed,
            exit_code=res.exit_code,
            details=details,
            duration_seconds=res.duration_seconds,
            raw_output=f"{res.stdout}\n{res.stderr}".strip(),
        )

    def create_backup(
        self,
        source_dir: Path | str,
        tags: Optional[List[str]] = None,
    ) -> BackupResult:
        """
        Execute backup against an approved directory using JSON telemetry.
        """
        source = Path(source_dir).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Source directory does not exist: {source}")

        args = ["backup", "--json", str(source)]
        if tags:
            for tag in tags:
                args.extend(["--tag", tag])

        exec_res = self._execute(args)

        # Parse NDJSON output from restic
        summary_data: Dict[str, Any] = {}
        snapshot_id: Optional[str] = None

        for line in exec_res.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
                if msg.get("message_type") == "summary":
                    summary_data = msg
                    snapshot_id = msg.get("snapshot_id")
                elif msg.get("message_type") == "status":
                    pass
            except json.JSONDecodeError:
                continue

        # If summary wasn't in stdout, try to extract snapshot ID from regular output
        if not snapshot_id and exec_res.exit_code == 0:
            for line in exec_res.stdout.splitlines():
                if "snapshot" in line.lower() and "saved" in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        snapshot_id = parts[1].strip()

        return BackupResult(
            snapshot_id=snapshot_id,
            files_new=summary_data.get("files_new", 0),
            files_changed=summary_data.get("files_changed", 0),
            files_unmodified=summary_data.get("files_unmodified", 0),
            bytes_added=summary_data.get("data_added", 0),
            total_files_processed=summary_data.get("total_files_processed", 0),
            total_bytes_processed=summary_data.get("total_bytes_processed", 0),
            duration_seconds=exec_res.duration_seconds,
            execution_result=exec_res,
            raw_json=summary_data or None,
        )

    def list_snapshots(self) -> List[SnapshotInfo]:
        """Query repository and return structured list of all snapshots."""
        res = self._execute(["snapshots", "--json"])
        if res.exit_code != 0:
            logger.warning(f"Failed to list snapshots: {res.stderr}")
            return []

        try:
            raw_list = json.loads(res.stdout)
            snapshots: List[SnapshotInfo] = []
            for item in raw_list:
                snap = SnapshotInfo(
                    id=item.get("short_id", item.get("id", "")[:8]),
                    full_id=item.get("id", ""),
                    time=item.get("time", ""),
                    paths=item.get("paths", []),
                    hostname=item.get("hostname", ""),
                    username=item.get("username", ""),
                    tags=item.get("tags", []) or [],
                    summary=item.get("summary"),
                )
                snapshots.append(snap)
            # Sort newest first
            snapshots.sort(key=lambda s: s.time, reverse=True)
            return snapshots
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing snapshots JSON: {e}")
            return []

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_dir: Path | str,
        include_paths: Optional[List[str]] = None,
        subfolder: Optional[str] = None,
    ) -> RestoreResult:
        """
        Restore a snapshot into an isolated target directory.
        Strictly validates destination safety before command execution.
        Supports snapshotID:subfolder syntax for direct non-privileged Windows restores.
        """
        target = Path(target_dir).resolve()

        # Enforce destination safety boundary
        is_safe, reason = self.settings.is_safe_restore_target(target)
        if not is_safe:
            raise ValueError(f"Unsafe restore destination rejected: {reason}")

        target.mkdir(parents=True, exist_ok=True)

        spec = snapshot_id
        if subfolder:
            clean_subfolder = subfolder.replace("\\", "/").replace(":", "")
            if not clean_subfolder.startswith("/"):
                clean_subfolder = "/" + clean_subfolder
            spec = f"{snapshot_id}:{clean_subfolder}"

        args = ["restore", spec, "--target", str(target)]
        if include_paths:
            for p in include_paths:
                args.extend(["--include", p])

        exec_res = self._execute(args)

        return RestoreResult(
            snapshot_id=snapshot_id,
            target_dir=str(target),
            duration_seconds=exec_res.duration_seconds,
            execution_result=exec_res,
        )
