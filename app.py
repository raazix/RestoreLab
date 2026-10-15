"""
RestoreLab — Backup Integrity & Recovery Verification Tool
Main Streamlit Application
A reliability-engineering workbench for investigating backup failures,
testing data recovery, verifying restored content, and learning from incidents.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st

# Ensure src is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from restorelab.backup.base import CommandExecutionResult
from restorelab.backup.restic import ResticBackupEngine
from restorelab.config import RestoreLabSettings, get_settings, setup_logging
from restorelab.diagnostics.engine import DiagnosticEngine
from restorelab.diagnostics.rules import DiagnosticContext
from restorelab.experiments.runner import ExperimentRunner
from restorelab.experiments.scenarios import ALL_SCENARIOS, get_scenario_by_id
from restorelab.incidents.models import (
    BackupRunRecord,
    IncidentRecord,
    IntegrityCheckRecord,
    KnowledgeArticle,
    RestoreAttemptRecord,
)
from restorelab.incidents.repository import IncidentRepository
from restorelab.knowledge.sqlite_search import SQLiteKnowledgeProvider
from restorelab.knowledge.supermemory_adapter import SupermemoryAdapter
from restorelab.reporting.exports import (
    export_incident_markdown,
    export_verification_markdown,
)
from restorelab.reporting.html_export import (
    export_drill_html,
    export_readiness_html,
    export_verification_html,
)
from restorelab.verification.drills import RecoveryDrillRunner
from restorelab.verification.drift import SnapshotDriftAnalyzer
from restorelab.verification.manifest import (
    compare_manifests,
    generate_manifest,
)
from restorelab.verification.restore import verify_recovery
from restorelab.verification.sample_data import generate_lab_dataset

logger = setup_logging()


# ==============================================================================
# Page Configuration & Styling
# ==============================================================================
st.set_page_config(
    page_title="RestoreLab — Backup Integrity Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Reliability Engineering CSS
st.markdown(
    """
    <style>
    /* Global Typography & Palette */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Header Card */
    .workbench-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        color: #f8fafc;
    }
    .workbench-title {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: #38bdf8;
    }
    .workbench-subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin-top: 6px;
        margin-bottom: 0;
    }

    /* Metric Cards */
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        text-align: left;
    }
    .metric-title {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .badge-passed {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid #059669;
    }
    .badge-failed {
        background: rgba(244, 63, 94, 0.15);
        color: #f43f5e;
        border: 1px solid #e11d48;
    }
    .badge-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid #d97706;
    }
    .badge-not-run {
        background: rgba(100, 116, 139, 0.15);
        color: #94a3b8;
        border: 1px solid #475569;
    }
    .badge-inconclusive {
        background: rgba(168, 85, 247, 0.15);
        color: #a855f7;
        border: 1px solid #9333ea;
    }
    
    /* Audit Finding Card */
    .finding-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .finding-card-critical {
        border-left-color: #f43f5e;
    }
    .finding-card-warning {
        border-left-color: #f59e0b;
    }
    
    /* Footer */
    .lab-footer {
        text-align: center;
        font-size: 12px;
        color: #64748b;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_app_components():
    """Initialize singleton repository, settings, and engines."""
    settings = get_settings()
    settings.ensure_directories()
    repo = IncidentRepository()
    engine = ResticBackupEngine(settings)
    diag_engine = DiagnosticEngine()
    exp_runner = ExperimentRunner(settings, diag_engine)
    kb_provider = SQLiteKnowledgeProvider(repo)
    supermemory = SupermemoryAdapter(settings, fallback_provider=kb_provider)
    drill_runner = RecoveryDrillRunner(engine, repo, settings, diag_engine)
    drift_analyzer = SnapshotDriftAnalyzer(repo, engine, settings)
    return settings, repo, engine, diag_engine, exp_runner, kb_provider, supermemory, drill_runner, drift_analyzer


settings, repo, engine, diag_engine, exp_runner, kb_provider, supermemory, drill_runner, drift_analyzer = get_app_components()


# ==============================================================================
# Navigation Sidebar
# ==============================================================================
with st.sidebar:
    st.markdown("### 🛡️ **RestoreLab**")
    st.caption("Backup Integrity & Recovery Verification")

    binary_status = settings.find_restic_binary()
    if binary_status:
        st.success(f"Engine: Restic (`{binary_status.name}`)", icon="✅")
    else:
        st.error("Restic executable missing", icon="❌")

    st.markdown("---")
    menu = st.radio(
        "Navigation",
        [
            "Overview",
            "Backup Lab",
            "Recovery Verification",
            "Recovery Drills & Readiness",
            "Incident Explorer",
            "Knowledge Base",
            "Experiments",
            "Reports",
            "Settings",
        ],
        index=0,
    )

    st.markdown("---")
    st.caption("Environment: **Windows / Local-first**")
    st.caption(f"Database: `{settings.resolved_database_path.name}`")
    st.caption(f"Lab Repo: `{settings.resolved_repository.name}`")


# ==============================================================================
# Page 1: OVERVIEW
# ==============================================================================
if menu == "Overview":
    st.markdown(
        """
        <div class="workbench-header">
            <h1 class="workbench-title">Reliability Engineering Workbench</h1>
            <p class="workbench-subtitle">
                Continuous backup validation, silent data corruption detection, and evidence-grounded recovery verification.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Key Operational Metrics
    backup_runs = repo.list_backup_runs(limit=100)
    restore_attempts = repo.list_restore_attempts(limit=100)
    open_incidents = repo.list_incidents(status="open")
    checks = repo.list_integrity_checks(limit=10)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Total Backup Runs</div>
                <div class="metric-value">{len(backup_runs)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        passed_restores = sum(1 for r in restore_attempts if r.status == "PASSED")
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Verified Restores</div>
                <div class="metric-value">{passed_restores} / {len(restore_attempts)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Open Incidents</div>
                <div class="metric-value">{len(open_incidents)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        last_check_status = (
            '<span class="badge badge-passed">Passed</span>'
            if checks and checks[0].passed
            else (
                '<span class="badge badge-failed">Failed</span>'
                if checks
                else '<span class="badge badge-not-run">Not Run</span>'
            )
        )
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Repository Integrity</div>
                <div class="metric-value" style="font-size:18px; margin-top:8px;">{last_check_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📋 Recent Operational Activity")
    tab_backups, tab_restores, tab_incidents = st.tabs(
        ["Recent Backups", "Recovery Audits", "Unresolved Incidents"]
    )

    with tab_backups:
        if not backup_runs:
            st.info("No backup runs recorded yet. Head to **Backup Lab** to initialize and perform your first backup.")
        else:
            table_data = [
                {
                    "Run ID": r.run_id[:8],
                    "Timestamp": r.timestamp[:19].replace("T", " "),
                    "Snapshot": r.snapshot_id[:8] if r.snapshot_id else "N/A",
                    "Status": r.status.upper(),
                    "Files": r.total_files,
                    "Volume": f"{r.total_bytes / 1024:.1f} KB",
                    "Duration": f"{r.duration_seconds}s",
                }
                for r in backup_runs[:10]
            ]
            st.dataframe(table_data, use_container_width=True)

    with tab_restores:
        if not restore_attempts:
            st.info("No recovery verification attempts executed yet. Visit **Recovery Verification** to test a snapshot restore.")
        else:
            table_data = [
                {
                    "Attempt ID": r.attempt_id[:8],
                    "Timestamp": r.timestamp[:19].replace("T", " "),
                    "Snapshot": r.snapshot_id[:8],
                    "Result": r.status,
                    "Matched": r.matched_files,
                    "Corrupted": r.corrupted_files,
                    "Missing": r.missing_files,
                    "Duration": f"{r.duration_seconds}s",
                }
                for r in restore_attempts[:10]
            ]
            st.dataframe(table_data, use_container_width=True)

    with tab_incidents:
        if not open_incidents:
            st.success("No active open incidents. System state is nominal.")
        else:
            for inc in open_incidents:
                st.markdown(
                    f"""
                    <div class="finding-card finding-card-critical">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>{inc.title}</strong>
                            <span class="badge badge-failed">{inc.severity}</span>
                        </div>
                        <div style="font-size:13px; color:#cbd5e1; margin-top:6px;">
                            ID: <code>{inc.incident_id}</code> | Category: <code>{inc.category}</code> | Created: {inc.created_at[:19]}
                        </div>
                        <div style="font-size:13px; color:#94a3b8; margin-top:4px;">
                            Symptoms: {'; '.join(inc.symptoms[:2])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ==============================================================================
# Page 2: BACKUP LAB
# ==============================================================================
elif menu == "Backup Lab":
    st.markdown("## 💾 Backup Lab Operations")
    st.caption("Configure, execute, and inspect real cryptographic backups against user-approved lab directories.")

    # Status Bar
    repo_status = engine.get_status()
    col_stat1, col_stat2 = st.columns([3, 1])
    with col_stat1:
        if repo_status.initialized and repo_status.accessible:
            st.success(f"Repository Connected: `{settings.resolved_repository}`", icon="✅")
        elif not repo_status.initialized:
            st.warning(f"Repository Uninitialized: `{settings.resolved_repository}`", icon="⚠️")
        else:
            st.error(f"Repository Inaccessible: {repo_status.error_message}", icon="❌")
    with col_stat2:
        if st.button("Initialize Repository", use_container_width=True):
            with st.spinner("Initializing repository..."):
                res = engine.init_repository()
                if res.success:
                    st.success("Repository initialized successfully!")
                    st.rerun()
                else:
                    st.error(f"Initialization failed: {res.stderr}")
                    # Log incident
                    diag = diag_engine.diagnose(DiagnosticContext(command_result=res))
                    inc = IncidentRecord(
                        title=f"Repository Init Failure: {res.stderr[:80]}",
                        severity="high",
                        category="repository",
                        operation_type="backup",
                        symptoms=[res.stderr.strip()],
                        findings=diag,
                    )
                    repo.save_incident(inc)

    st.markdown("---")
    st.markdown("### 1. Lab Source Dataset")
    c_src1, c_src2 = st.columns([3, 1])
    with c_src1:
        st.text_input(
            "Approved Source Directory",
            value=str(settings.resolved_source_dir),
            disabled=True,
            help="Configured in .env as LAB_SOURCE_DIR to isolate backup tests",
        )
    with c_src2:
        if st.button("Generate Sample Dataset", use_container_width=True):
            f_count, b_count = generate_lab_dataset(settings.resolved_source_dir)
            st.success(f"Created {f_count} files ({b_count / 1024:.1f} KB) including Unicode & binary fixtures!")
            st.rerun()

    # Pre-Backup Manifest Scan
    st.markdown("### 2. Pre-Backup Manifest & Ingestion")
    source_exists = settings.resolved_source_dir.exists() and any(settings.resolved_source_dir.iterdir())
    if not source_exists:
        st.info("Source directory is empty. Click **Generate Sample Dataset** above to populate test fixtures.")

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        scan_manifest = st.button("Generate Pre-Backup Manifest", disabled=not source_exists, use_container_width=True)
    with col_btn2:
        run_backup = st.button("Execute Real Backup (Restic)", disabled=not source_exists or not repo_status.initialized, use_container_width=True)

    if scan_manifest:
        with st.spinner("Scanning source tree and calculating SHA-256 digests..."):
            try:
                manifest = generate_manifest(
                    settings.resolved_source_dir,
                    max_bytes=settings.max_source_scan_mb * 1024 * 1024,
                    max_files=settings.max_manifest_files,
                )
                repo.save_manifest(manifest)
                st.session_state["latest_manifest"] = manifest
                st.success(
                    f"Generated Deterministic Manifest `{manifest.manifest_id[:8]}`: "
                    f"{manifest.total_files} files ({manifest.total_bytes / 1024:.1f} KB). "
                    f"Digest: `{manifest.manifest_hash[:16]}...`"
                )
                # Show entries
                table_files = [
                    {"Path": e.path, "Size (Bytes)": e.size_bytes, "SHA-256": e.sha256[:16] + "..."}
                    for e in list(manifest.entries.values())[:10]
                ]
                st.dataframe(table_files, use_container_width=True)
            except Exception as e:
                st.error(f"Manifest scan failed: {e}")

    if run_backup:
        with st.spinner("Executing cryptographic restic backup..."):
            # 1. Automatically generate pre-manifest if absent
            try:
                pre_m = generate_manifest(settings.resolved_source_dir)
                repo.save_manifest(pre_m)
            except Exception as e:
                st.error(f"Failed pre-backup manifest generation: {e}")
                st.stop()

            # 2. Run backup
            b_res = engine.create_backup(settings.resolved_source_dir, tags=["lab-run"])
            
            # 3. Persist run record
            run_rec = BackupRunRecord(
                source_path=str(settings.resolved_source_dir),
                snapshot_id=b_res.snapshot_id,
                status="success" if b_res.execution_result.success else "failed",
                manifest_id=pre_m.manifest_id,
                total_files=b_res.total_files_processed,
                total_bytes=b_res.total_bytes_processed,
                duration_seconds=b_res.duration_seconds,
                raw_output=f"{b_res.execution_result.stdout}\n{b_res.execution_result.stderr}",
            )
            repo.save_backup_run(run_rec)

            if b_res.execution_result.success:
                st.success(
                    f"Backup Succeeded! Snapshot ID: `{b_res.snapshot_id[:8]}` "
                    f"({b_res.files_new} new, {b_res.files_changed} changed, {b_res.bytes_added / 1024:.1f} KB added) "
                    f"in {b_res.duration_seconds}s"
                )
            else:
                st.error(f"Backup Failed with exit code {b_res.execution_result.exit_code}")
                st.code(b_res.execution_result.stderr)
                # Live diagnostic triage
                diag_findings = diag_engine.diagnose(DiagnosticContext(command_result=b_res.execution_result))
                inc = IncidentRecord(
                    title=f"Backup Failure on {settings.resolved_source_dir.name}",
                    severity="high",
                    category="backup",
                    operation_type="backup",
                    symptoms=[b_res.execution_result.stderr.strip()[:200]],
                    findings=diag_findings,
                )
                repo.save_incident(inc)
                st.warning("Incident logged automatically in Incident Explorer.")

    st.markdown("---")
    st.markdown("### 3. Repository Health & Integrity Validation")
    st.caption("Perform physical index checks or deep cryptographic payload scans.")
    col_chk1, col_chk2 = st.columns([1, 1])
    with col_chk1:
        if st.button("Run Fast Index Check (`restic check`)", use_container_width=True):
            with st.spinner("Checking index integrity..."):
                chk = engine.check_repository(read_data=False)
                repo.save_integrity_check(
                    IntegrityCheckRecord(
                        check_type=chk.check_type,
                        passed=chk.passed,
                        exit_code=chk.exit_code,
                        duration_seconds=chk.duration_seconds,
                        raw_output=chk.raw_output,
                    )
                )
                if chk.passed:
                    st.success(f"PASSED: Index structures intact ({chk.duration_seconds}s).")
                else:
                    st.error(f"FAILED: {chk.details}")
    with col_chk2:
        if st.button("Run Deep Data Check (`--read-data`)", use_container_width=True):
            with st.spinner("Verifying all stored data pack blocks..."):
                chk = engine.check_repository(read_data=True)
                repo.save_integrity_check(
                    IntegrityCheckRecord(
                        check_type=chk.check_type,
                        passed=chk.passed,
                        exit_code=chk.exit_code,
                        duration_seconds=chk.duration_seconds,
                        raw_output=chk.raw_output,
                    )
                )
                if chk.passed:
                    st.success(f"PASSED: 100% of repository chunks validated byte-for-byte ({chk.duration_seconds}s).")
                else:
                    st.error(f"FAILED: Corrupted chunks found: {chk.details}")


# ==============================================================================
# Page 3: RECOVERY VERIFICATION
# ==============================================================================
elif menu == "Recovery Verification":
    st.markdown("## 🔍 Cryptographic Recovery Verification")
    st.caption("Restore snapshots into strictly isolated sandboxes and verify restored files against pre-backup manifests.")

    snapshots = engine.list_snapshots()
    if not snapshots:
        st.warning("No snapshots found in repository. Create a backup in Backup Lab first.")
        st.stop()

    # Snapshot Selector
    snap_options = {
        f"Snapshot {s.id} ({s.time[:19].replace('T', ' ')}) - {s.paths}": s
        for s in snapshots
    }
    selected_label = st.selectbox("Select Target Snapshot to Verify", list(snap_options.keys()))
    selected_snap = snap_options[selected_label]

    # Find matching pre-backup runs or manifests
    all_runs = repo.list_backup_runs(limit=100)
    matching_manifest_id = None
    for r in all_runs:
        if r.snapshot_id and (r.snapshot_id == selected_snap.id or r.snapshot_id.startswith(selected_snap.id)):
            matching_manifest_id = r.manifest_id
            break

    manifest_obj: Optional[Any] = None
    if matching_manifest_id:
        manifest_obj = repo.get_manifest(matching_manifest_id)

    st.markdown("### Destination Sandbox Configuration")
    col_dest1, col_dest2 = st.columns([3, 1])
    with col_dest1:
        default_target = settings.resolved_restore_dir / f"verify_{selected_snap.id}_{datetime.now().strftime('%H%M%S')}"
        target_input = st.text_input("Isolated Restore Destination Sandbox", value=str(default_target))
    with col_dest2:
        is_safe, reason = settings.is_safe_restore_target(target_input)
        if is_safe:
            st.success("Target: Isolated Sandbox", icon="🛡️")
        else:
            st.error(f"Unsafe: {reason}", icon="🚫")

    # If manifest not automatically bound, allow baseline generation from current source
    if not manifest_obj:
        st.info("No pre-backup manifest was bound to this snapshot. You can use the current source tree as baseline manifest.")
        if st.button("Generate Baseline Manifest from Approved Source"):
            manifest_obj = generate_manifest(settings.resolved_source_dir)
            repo.save_manifest(manifest_obj)
            st.session_state["baseline_manifest"] = manifest_obj
            st.success("Baseline manifest generated!")

    if "baseline_manifest" in st.session_state and not manifest_obj:
        manifest_obj = st.session_state["baseline_manifest"]

    # Execute Recovery Verification Button
    if st.button("Execute Restore & Verify Content Integrity", disabled=not is_safe or not manifest_obj, type="primary"):
        with st.spinner("Restoring into isolated sandbox and performing byte-for-byte verification..."):
            report = verify_recovery(
                engine=engine,
                snapshot_id=selected_snap.id,
                original_manifest=manifest_obj,
                target_dir=target_input,
                settings=settings,
            )

            # Persist attempt record
            matched = report.comparison_result.matched_count if report.comparison_result else 0
            corrupted = report.comparison_result.corrupted_count if report.comparison_result else 0
            missing = report.comparison_result.missing_count if report.comparison_result else 0
            extra = report.comparison_result.extra_count if report.comparison_result else 0

            rec = RestoreAttemptRecord(
                snapshot_id=selected_snap.id,
                target_path=report.restore_target_path,
                status=report.status,
                original_manifest_id=report.original_manifest_id,
                restored_manifest_id=report.restored_manifest_id,
                matched_files=matched,
                corrupted_files=corrupted,
                missing_files=missing,
                extra_files=extra,
                duration_seconds=report.restore_duration_seconds + report.verification_duration_seconds,
                details=report.diagnostics_summary,
            )
            repo.save_restore_attempt(rec)

            st.session_state["last_verification_report"] = report

    # Render Report
    if "last_verification_report" in st.session_state:
        rep = st.session_state["last_verification_report"]
        st.markdown("---")
        badge_class = {
            "PASSED": "badge-passed",
            "FAILED": "badge-failed",
            "WARNING": "badge-warning",
            "INCONCLUSIVE": "badge-inconclusive",
            "NOT_RUN": "badge-not-run",
        }.get(rep.status, "badge-not-run")

        st.markdown(
            f"""
            <div class="workbench-header" style="margin-top:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#f8fafc;">Verification Result: Snapshot {rep.snapshot_id}</h3>
                    <span class="badge {badge_class}" style="font-size:14px;">{rep.status}</span>
                </div>
                <p style="margin-top:8px; color:#cbd5e1;">{rep.diagnostics_summary}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if rep.comparison_result:
            comp = rep.comparison_result
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("100% Matched Files", comp.matched_count)
            col_m2.metric("Silent Corruptions", comp.corrupted_count)
            col_m3.metric("Missing Files", comp.missing_count)
            col_m4.metric("Extra Files", comp.extra_count)

            st.markdown("#### File-by-File Integrity Details")
            diff_table = [
                {
                    "Relative Path": d.path,
                    "Status": d.status.upper(),
                    "Expected Bytes": d.expected_size if d.expected_size is not None else "-",
                    "Actual Bytes": d.actual_size if d.actual_size is not None else "-",
                    "Verification Details": d.details,
                }
                for d in comp.diffs
            ]
            st.dataframe(diff_table, use_container_width=True)

            # Export Button
            audit_export = export_verification_markdown(rep)
            st.download_button(
                "Export Cryptographic Audit Report (.md)",
                data=audit_export.content,
                file_name=f"audit_report_{rep.snapshot_id[:8]}.md",
                mime="text/markdown",
            )


# ==============================================================================
# Page: RECOVERY DRILLS & READINESS ANALYTICS
# ==============================================================================
elif menu == "Recovery Drills & Readiness":
    st.markdown("## 🎯 Automated Recovery Drills & DR Readiness")
    st.caption("Measure actual restore durations against RTO SLAs, audit historical recovery drills in isolated sandboxes, and detect snapshot drift.")

    # Section 1: DR Readiness Analytics
    st.markdown("### 1. Disaster Recovery Readiness Scorecard")
    readiness = repo.get_recovery_readiness()

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.metric("Readiness Score", f"{readiness.score} / 100", f"Tier: {readiness.readiness_tier}")
    with col_r2:
        st.metric("Snapshot Coverage", f"{readiness.coverage_ratio:.1f}%", f"{readiness.tested_snapshots_count}/{readiness.total_eligible_snapshots} Tested")
    with col_r3:
        st.metric("RTO SLA Compliance", f"{readiness.rto_compliance_rate:.1f}%", f"Avg {readiness.average_restore_seconds:.2f}s")
    with col_r4:
        snap_age_str = f"{readiness.latest_snapshot_age_hours:.1f}h" if readiness.latest_snapshot_age_hours is not None else "N/A"
        st.metric("Latest Snapshot Age (RPO)", snap_age_str, f"{readiness.successful_drills_count} Passes")

    readiness_html = export_readiness_html(readiness)
    st.download_button(
        "Download Signed Readiness Audit (.html)",
        data=readiness_html.content,
        file_name=f"DR_Readiness_{readiness.assessment_id}.html",
        mime="text/html",
    )

    with st.expander("Review Documented Metric Limitations & Assumptions"):
        for lim in readiness.metric_limitations:
            st.markdown(f"- {lim}")

    st.markdown("---")

    # Section 2: Automated Recovery Drill Runner
    st.markdown("### 2. Execute Disaster Recovery Drill")
    st.caption("Restores snapshot into disposable sandbox, audits SHA-256 byte parity, and checks RTO compliance.")

    col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
    snapshots = engine.list_snapshots()
    snap_lookup = {s.id: s for s in snapshots}
    with col_d1:
        snap_choices = ["Latest Available Snapshot"] + [f"{s.id} ({s.time[:10]})" for s in snapshots]
        chosen_snap = st.selectbox("Drill Snapshot Target", snap_choices)
    with col_d2:
        drill_rto = st.number_input("RTO Target (seconds)", min_value=5, max_value=600, value=60)
    with col_d3:
        auto_clean = st.checkbox("Auto-purge Sandbox", value=True)

    if st.button("Launch Recovery Drill", type="primary", disabled=len(snapshots) == 0):
        target_sid = None if chosen_snap == "Latest Available Snapshot" else chosen_snap.split()[0]
        with st.spinner("Executing isolated recovery drill and measuring recovery time..."):
            try:
                drill_result = drill_runner.run_drill(
                    snapshot_id=target_sid,
                    rto_target_seconds=float(drill_rto),
                    cleanup_after=auto_clean,
                )
                if drill_result.status == "SUCCESS":
                    st.success(f"DRILL PASSED: Recovered in {drill_result.duration_seconds:.2f}s (RTO Target: {drill_result.rto_target_seconds}s)")
                else:
                    st.error(f"DRILL FAILED: {drill_result.evidence_summary}")
                st.session_state["last_drill_report"] = drill_result
            except Exception as e:
                st.error(f"Drill failed: {e}")

    # Drill history
    past_drills = repo.list_recovery_drills(limit=20)
    if past_drills:
        st.markdown("#### Historical Recovery Drills")
        drill_data = [
            {
                "Drill ID": d.drill_id,
                "Snapshot": d.snapshot_id[:8],
                "Status": d.status,
                "Duration (s)": round(d.duration_seconds, 2),
                "Target RTO (s)": d.rto_target_seconds,
                "RTO Compliant": "YES" if d.rto_compliant else "NO",
                "Matched Files": d.matched_files,
                "Corrupted": d.corrupted_files,
                "Created At": d.created_at[:19],
            }
            for d in past_drills
        ]
        st.dataframe(drill_data, use_container_width=True)

    st.markdown("---")

    # Section 3: Snapshot Drift & Volumetric Anomaly Analysis
    st.markdown("### 3. Snapshot Drift & Volumetric Anomaly Analysis")
    st.caption("Compare snapshots or inspect current live dataset to detect volumetric swings and explainable forensic anomalies.")

    if len(snapshots) > 0:
        col_dr1, col_dr2 = st.columns(2)
        with col_dr1:
            base_s = st.selectbox("Baseline Snapshot", [s.id for s in snapshots], key="drift_base")
        with col_dr2:
            target_options = ["current (Live Source Tree)"] + [s.id for s in snapshots]
            target_s = st.selectbox("Target Comparison", target_options, key="drift_target")

        if st.button("Run Drift Analysis"):
            target_key = "current" if target_s.startswith("current") else target_s
            with st.spinner("Comparing manifests and evaluating volumetric trends..."):
                try:
                    drift_rep = drift_analyzer.compare_snapshots(base_s, target_key)
                    st.session_state["last_drift_rep"] = drift_rep
                except Exception as e:
                    st.error(f"Drift analysis error: {e}")

        if "last_drift_rep" in st.session_state:
            d_rep = st.session_state["last_drift_rep"]
            st.markdown("#### Drift Findings")
            c_a, c_m, c_r, c_v = st.columns(4)
            c_a.metric("Added Files", len(d_rep.added_files))
            c_m.metric("Modified Files", len(d_rep.modified_files))
            c_r.metric("Removed Files", len(d_rep.removed_files))
            c_v.metric("Volumetric Swing", f"{d_rep.percent_size_change}%", f"{d_rep.size_change_bytes / 1024:.1f} KB")

            if d_rep.anomaly_flags:
                st.warning("Forensic Anomaly Indicators Raised (Deviations from Baseline):")
                for exp in d_rep.anomaly_explanations:
                    st.markdown(f"- **{exp}**")
                st.caption("Note: Flags indicate statistical deviations; they do not represent definitive claims of malware.")
            else:
                st.success("No volumetric or modification anomalies detected. Normal operational drift.")


# ==============================================================================
# Page 4: INCIDENT EXPLORER
# ==============================================================================
elif menu == "Incident Explorer":
    st.markdown("## 🚨 Incident Explorer & Audit Log")
    st.caption("Investigate backup failures, review deterministic diagnostic findings, and log verified resolutions.")


    # Status Filters
    c_f1, c_f2 = st.columns([2, 1])
    with c_f1:
        status_filter = st.selectbox("Filter by Status", ["All", "open", "investigating", "mitigated", "resolved", "closed"])
    with c_f2:
        incidents = repo.list_incidents(status=None if status_filter == "All" else status_filter)
        st.metric("Total Filtered Incidents", len(incidents))

    if not incidents:
        st.info("No incidents found matching current filters.")

    for inc in incidents:
        with st.expander(f"[{inc.severity.upper()}] {inc.title} ({inc.status.upper()}) — {inc.incident_id}"):
            st.markdown(f"**Created At:** `{inc.created_at}` | **Category:** `{inc.category}` | **Operation:** `{inc.operation_type}`")

            st.markdown("#### Observable Symptoms")
            for s in inc.symptoms:
                st.markdown(f"- `{s}`")

            if inc.findings:
                st.markdown("#### Deterministic Diagnostic Findings")
                for f in inc.findings:
                    st.markdown(
                        f"""
                        <div class="finding-card">
                            <strong>{f.rule_name}</strong> (Rule: <code>{f.rule_id}</code> | Certainty: <strong>{f.certainty.upper()}</strong>)
                            <div style="margin-top:4px; color:#cbd5e1;">Root Cause: {f.root_cause}</div>
                            <div style="margin-top:4px; color:#38bdf8;">Suggested Remediation: {f.suggested_remediation}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if f.kb_reference_id:
                        st.caption(f"Linked Knowledge Base Article: `{f.kb_reference_id}`")

            st.markdown("#### Verified Resolution Workflow")
            new_res = st.text_area(
                "Resolution Steps Applied",
                value=inc.verified_resolution or "",
                key=f"res_{inc.incident_id}",
            )
            col_act1, col_act2, col_act3 = st.columns(3)
            with col_act1:
                new_status = st.selectbox("Update Status", ["open", "investigating", "mitigated", "resolved", "closed"], index=["open", "investigating", "mitigated", "resolved", "closed"].index(inc.status), key=f"st_{inc.incident_id}")
            with col_act2:
                if st.button("Save Incident Updates", key=f"btn_{inc.incident_id}"):
                    inc.status = new_status
                    inc.verified_resolution = new_res
                    if new_status in ("resolved", "closed") and not inc.resolved_at:
                        inc.resolved_at = datetime.now(timezone.utc).isoformat()
                        inc.resolved_by = "Reliability Engineer"
                    repo.save_incident(inc)
                    st.success("Incident updated!")
                    st.rerun()
            with col_act3:
                export_doc = export_incident_markdown(inc)
                st.download_button(
                    "Export Post-Mortem (.md)",
                    data=export_doc.content,
                    file_name=f"postmortem_{inc.incident_id}.md",
                    mime="text/markdown",
                    key=f"dl_{inc.incident_id}",
                )

            if settings.supermemory_enabled:
                st.markdown("---")
                st.markdown("##### 🌐 Supermemory Integration (Cloud Incident Memory)")
                if st.checkbox("🔍 Review Sanitized Telemetry Payload (Privacy Audit)", key=f"preview_chk_{inc.incident_id}"):
                    st.caption("Inspect the exact payload that will be transmitted. All passwords and paths are scrubbed.")
                    sanitized_payload = supermemory.preview_sanitized_payload(inc)
                    st.json(sanitized_payload)

                col_sync1, col_sync2 = st.columns([3, 1])
                with col_sync1:
                    consent = st.checkbox(
                        f"I give explicit consent to transmit this sanitized incident summary to namespace '{supermemory.namespace}'",
                        key=f"consent_{inc.incident_id}",
                    )
                with col_sync2:
                    if st.button("Sync to Supermemory", disabled=not consent, key=f"sync_btn_{inc.incident_id}", use_container_width=True):
                        with st.spinner(f"Synchronizing to Supermemory namespace '{supermemory.namespace}'..."):
                            supermemory.index_incident(inc)
                            st.success(f"Incident synchronized to namespace '{supermemory.namespace}'!")


# ==============================================================================
# Page 5: KNOWLEDGE BASE
# ==============================================================================
elif menu == "Knowledge Base":
    st.markdown("## 📚 Operational Reliability Knowledge Base")
    st.caption("Offline case-based reasoning powered by SQLite FTS5. Matches failure signatures to verified resolutions.")

    search_q = st.text_input("Search Symptoms, Error Messages, or Root Causes", placeholder="e.g. wrong password, silent corruption, lock, missing file")
    
    col_kb1, col_kb2 = st.columns([3, 1])
    with col_kb1:
        cat_filter = st.selectbox("Category Filter", ["All", "authentication", "repository", "integrity", "security", "concurrency", "filesystem"])
    active_search_provider = supermemory if settings.supermemory_enabled else kb_provider
    with col_kb2:
        st.caption(f"Provider: **{active_search_provider.get_provider_name()}**")

    results = active_search_provider.search(
        query=search_q,
        category=None if cat_filter == "All" else cat_filter,
        limit=10,
    )

    st.markdown(f"### Found {len(results)} Matching Articles / Incidents")
    for r in results:
        with st.expander(f"[{r.item_type.upper()}] {r.title} ({r.category})"):
            st.info(f"💡 **Relevance Reason:** {r.match_reason}")
            st.markdown(f"**Symptoms & Problem Statement:**\n{r.snippet}")
            if r.verified_resolution:
                st.success(f"**Verified Resolution Steps:**\n{r.verified_resolution}")
            if r.metadata.get("diagnostic_checks"):
                st.markdown(f"**Diagnostic Checks:**\n{r.metadata.get('diagnostic_checks')}")
            if r.metadata.get("verification_procedure"):
                st.markdown(f"**Verification Procedure:**\n{r.metadata.get('verification_procedure')}")
            if r.metadata.get("known_limitations"):
                st.warning(f"**Known Limitations:**\n{r.metadata.get('known_limitations')}")


# ==============================================================================
# Page 6: EXPERIMENTS
# ==============================================================================
elif menu == "Experiments":
    st.markdown("## 🧪 Controlled Failure Experiments")
    st.caption("Safely reproduce realistic failure scenarios in disposable sandboxes without risking active repositories.")

    col_exp1, col_exp2 = st.columns([3, 1])
    with col_exp1:
        scenario_opts = {f"{s.scenario_id}: {s.title}": s.scenario_id for s in ALL_SCENARIOS}
        selected_scen_label = st.selectbox("Select Experiment Scenario", list(scenario_opts.keys()))
        selected_scen_id = scenario_opts[selected_scen_label]
        scenario_def = get_scenario_by_id(selected_scen_id)
    with col_exp2:
        st.write("")
        st.write("")
        run_single = st.button("Run Single Experiment", type="primary", use_container_width=True)

    if scenario_def:
        st.markdown(f"> **Description:** {scenario_def.description}")
        st.markdown(f"- **Expected Outcome:** {scenario_def.expected_outcome}")
        st.markdown(f"- **Target Diagnostic Rule:** `{scenario_def.target_rule_id}`")

    if run_single:
        with st.spinner(f"Executing {selected_scen_id} in disposable sandbox..."):
            res = exp_runner.run_experiment(selected_scen_id)
            repo.save_experiment(res)
            st.session_state["last_experiment_result"] = res

    # Run All Button
    if st.button("Run Entire Controlled Failure Suite (8 Scenarios)", use_container_width=True):
        with st.spinner("Executing all 8 failure experiments safely..."):
            results = exp_runner.run_all()
            for r in results:
                repo.save_experiment(r)
            st.session_state["all_experiment_results"] = results
            st.success(f"Executed {len(results)} experiments! {sum(1 for r in results if r.passed)} passed verification.")

    if "last_experiment_result" in st.session_state:
        exp_res = st.session_state["last_experiment_result"]
        st.markdown("---")
        status_badge = '<span class="badge badge-passed">Passed</span>' if exp_res.passed else '<span class="badge badge-failed">Failed</span>'
        st.markdown(
            f"""
            <div class="workbench-header">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#f8fafc;">Result: {exp_res.scenario_title}</h3>
                    {status_badge}
                </div>
                <div style="margin-top:8px; color:#cbd5e1;">Actual Observation: {exp_res.actual_observations}</div>
                <div style="margin-top:4px; font-size:12px; color:#94a3b8;">Cleanup Status: {exp_res.cleanup_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Checks Performed")
        for chk in exp_res.checks_performed:
            st.markdown(f"- {chk}")

        if exp_res.diagnostic_findings:
            st.markdown("#### Diagnostic Findings Fired")
            for f in exp_res.diagnostic_findings:
                st.markdown(
                    f"""
                    <div class="finding-card">
                        <strong>{f.rule_name}</strong> (<code>{f.rule_id}</code>)
                        <div>Root Cause: {f.root_cause}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if exp_res.sanitized_output:
            st.markdown("#### Sanitized Subprocess Output")
            st.code(exp_res.sanitized_output)


# ==============================================================================
# Page 7: REPORTS
# ==============================================================================
elif menu == "Reports":
    st.markdown("## 📋 Reliability & Audit Reports")
    st.caption("Generate and download audit reports with cryptographic SHA-256 signatures.")

    tab_rep_inc, tab_rep_rec = st.tabs(["Incident Post-Mortems", "Recovery Verification Audits"])

    with tab_rep_inc:
        inc_list = repo.list_incidents(limit=20)
        if not inc_list:
            st.info("No incidents logged.")
        else:
            for inc in inc_list:
                rep_doc = export_incident_markdown(inc)
                with st.expander(f"{inc.incident_id}: {inc.title}"):
                    st.caption(f"SHA-256 Report Fingerprint: `{rep_doc.sha256_fingerprint}`")
                    st.code(rep_doc.content, language="markdown")
                    st.download_button(
                        f"Download {inc.incident_id}.md",
                        data=rep_doc.content,
                        file_name=f"{inc.incident_id}.md",
                        mime="text/markdown",
                        key=f"dl_rep_{inc.incident_id}",
                    )

    with tab_rep_rec:
        rec_list = repo.list_restore_attempts(limit=20)
        if not rec_list:
            st.info("No recovery verification attempts executed.")
        else:
            for rec in rec_list:
                with st.expander(f"Audit {rec.attempt_id[:8]} — Snapshot {rec.snapshot_id[:8]} ({rec.status})"):
                    st.markdown(f"- **Target:** `{rec.target_path}`")
                    st.markdown(f"- **Result:** {rec.status}")
                    st.markdown(f"- **Matched:** {rec.matched_files} | **Corrupted:** {rec.corrupted_files} | **Missing:** {rec.missing_files}")
                    st.markdown(f"- **Details:** {rec.details}")


# ==============================================================================
# Page 8: SETTINGS
# ==============================================================================
elif menu == "Settings":
    st.markdown("## ⚙️ Settings & Configuration")
    st.caption("Review system paths, safety limits, logging, and external adapters.")

    st.markdown("### 1. Active Lab Paths")
    st.text_input("Restic Binary Path", value=str(settings.find_restic_binary() or "Not Found"), disabled=True)
    st.text_input("Lab Repository Path", value=str(settings.resolved_repository), disabled=True)
    st.text_input("Lab Source Directory", value=str(settings.resolved_source_dir), disabled=True)
    st.text_input("Lab Restore Sandbox Directory", value=str(settings.resolved_restore_dir), disabled=True)
    st.text_input("Lab Experiments Scratchpad", value=str(settings.resolved_experiments_dir), disabled=True)
    st.text_input("SQLite Database Path", value=str(settings.resolved_database_path), disabled=True)

    st.markdown("---")
    st.markdown("### 2. Operational Safety Limits")
    c_s1, c_s2, c_s3 = st.columns(3)
    c_s1.metric("Command Timeout", f"{settings.command_timeout_seconds}s")
    c_s2.metric("Max Source Scan", f"{settings.max_source_scan_mb} MB")
    c_s3.metric("Max Manifest Files", f"{settings.max_manifest_files:,}")

    st.markdown("---")
    st.markdown("### 3. Optional Supermemory Extension")
    st.caption("Requires explicit user consent and configuration. When disabled, RestoreLab operates 100% offline.")
    
    col_sm1, col_sm2 = st.columns([3, 1])
    with col_sm1:
        st.write(f"Provider: **{supermemory.get_provider_name()}**")
        st.caption(f"Active v5 Namespace: `{supermemory.namespace}`")
    with col_sm2:
        st.checkbox("Supermemory Enabled", value=settings.supermemory_enabled, disabled=True)

    if settings.supermemory_enabled:
        if st.button("Test Supermemory API Connection", use_container_width=True):
            with st.spinner("Probing Supermemory API v5 endpoint..."):
                ok, msg = supermemory.test_connection()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    st.markdown("#### Client-Side Privacy Sanitization Preview")
    st.caption("Verifies that passwords, API keys, and local filesystem paths are scrubbed before any remote transmission.")
    sample_incident = IncidentRecord(
        title="Failed backup of C:\\Users\\Administrator\\Payroll\\october.xlsx",
        symptoms=[f"Auth failure with password {settings.restic_password}"],
        category="security",
    )
    st.json(supermemory.preview_sanitized_payload(sample_incident))

st.markdown(
    """
    <div class="lab-footer">
        RestoreLab &mdash; Independent Backup Integrity & Recovery Verification Tool &bull; Local-First Reliability Engineering
    </div>
    """,
    unsafe_allow_html=True,
)
