"""
RestoreLab Reporting and Export Engine
Produces structured, verifiable Markdown and JSON post-mortem reports with
cryptographic SHA-256 report signatures for auditability.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from restorelab.incidents.models import IncidentRecord
from restorelab.verification.restore import RecoveryVerificationReport


class ExportedReport(BaseModel):
    """Cryptographically signed export manifest."""

    report_id: str
    report_type: str
    generated_at: str
    content_format: str
    content: str
    sha256_fingerprint: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def export_incident_markdown(incident: IncidentRecord) -> ExportedReport:
    """Format an incident into an industry-standard reliability post-mortem report."""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# RestoreLab Post-Mortem Incident Report: {incident.incident_id}",
        "",
        f"- **Title:** {incident.title}",
        f"- **Generated At:** {now}",
        f"- **Created At:** {incident.created_at}",
        f"- **Status:** {incident.status.upper()}",
        f"- **Severity:** {incident.severity.upper()}",
        f"- **Category:** {incident.category}",
        f"- **Operation Type:** {incident.operation_type}",
        f"- **Operation ID:** {incident.operation_id or 'N/A'}",
        "",
        "## 1. Executive Summary",
        incident.title,
        "",
        "## 2. Observable Symptoms & Evidence",
    ]

    if incident.symptoms:
        for s in incident.symptoms:
            lines.append(f"- {s}")
    else:
        lines.append("- No initial symptoms cataloged.")

    lines.extend([
        "",
        "## 3. Diagnostic Findings & Root Cause Analysis",
    ])

    if incident.findings:
        for idx, f in enumerate(incident.findings, 1):
            lines.extend([
                f"### Finding {idx}: {f.rule_name} (`{f.rule_id}`)",
                f"- **Certainty:** {f.certainty.upper()}",
                f"- **Root Cause:** {f.root_cause}",
                f"- **Suggested Remediation:** {f.suggested_remediation}",
            ])
            if f.supporting_evidence:
                lines.append("- **Supporting Evidence:**")
                for ev in f.supporting_evidence:
                    lines.append(f"  - {ev}")
            if f.recommended_checks:
                lines.append("- **Recommended Operational Checks:**")
                for chk in f.recommended_checks:
                    lines.append(f"  - {chk}")
            lines.append("")
    else:
        lines.append("- No deterministic findings recorded.")

    lines.extend([
        "## 4. Verified Resolution & Preventative Action",
        f"- **Resolution:** {incident.verified_resolution or 'Pending verification'}",
        f"- **Resolved By:** {incident.resolved_by or 'Unassigned'}",
        f"- **Resolved At:** {incident.resolved_at or 'Open'}",
        "",
        "## 5. Timeline & Operational Notes",
    ])

    if incident.notes:
        for n in incident.notes:
            lines.append(f"- {n}")
    else:
        lines.append("- No additional operator notes.")

    md_text = "\n".join(lines)
    fingerprint = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    return ExportedReport(
        report_id=f"REP-{incident.incident_id}",
        report_type="incident_postmortem",
        generated_at=now,
        content_format="markdown",
        content=md_text,
        sha256_fingerprint=fingerprint,
        metadata={"incident_id": incident.incident_id, "status": incident.status},
    )


def export_verification_markdown(report: RecoveryVerificationReport) -> ExportedReport:
    """Format a recovery verification test into a cryptographic compliance audit report."""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# RestoreLab Cryptographic Recovery Verification Audit: {report.id}",
        "",
        f"- **Snapshot ID:** `{report.snapshot_id}`",
        f"- **Audit Status:** **{report.status}**",
        f"- **Generated At:** {now}",
        f"- **Source Manifest ID:** `{report.original_manifest_id}`",
        f"- **Restored Manifest ID:** `{report.restored_manifest_id or 'N/A'}`",
        f"- **Restore Duration:** {report.restore_duration_seconds}s",
        f"- **Verification Duration:** {report.verification_duration_seconds}s",
        f"- **Destination Target:** `{report.restore_target_path}`",
        "",
        "## 1. Verification Outcome & Integrity Assessment",
        f"> **{report.diagnostics_summary}**",
        "",
    ]

    if report.comparison_result:
        comp = report.comparison_result
        lines.extend([
            "## 2. File-by-File Cryptographic Breakdown",
            f"- **Expected Files:** {comp.total_expected}",
            f"- **Actual Restored Files:** {comp.total_actual}",
            f"- **Matched (100% SHA-256 & Size):** {comp.matched_count}",
            f"- **Silent Data Corruptions:** {comp.corrupted_count}",
            f"- **Missing Files:** {comp.missing_count}",
            f"- **Unexpected Extra Files:** {comp.extra_count}",
            "",
            "### Differential Sample Table",
            "| Relative Path | Status | Expected SHA-256 | Actual SHA-256 | Notes |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        for d in comp.diffs[:20]:
            exp_s = (d.expected_sha256 or "N/A")[:12] + "..." if d.expected_sha256 else "-"
            act_s = (d.actual_sha256 or "N/A")[:12] + "..." if d.actual_sha256 else "-"
            lines.append(f"| `{d.path}` | **{d.status.upper()}** | `{exp_s}` | `{act_s}` | {d.details} |")

        if len(comp.diffs) > 20:
            lines.append(f"\n*(Showing 20 of {len(comp.diffs)} total file records)*")

    md_text = "\n".join(lines)
    fingerprint = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    return ExportedReport(
        report_id=f"AUDIT-{report.snapshot_id[:8]}",
        report_type="recovery_verification_audit",
        generated_at=now,
        content_format="markdown",
        content=md_text,
        sha256_fingerprint=fingerprint,
        metadata={"snapshot_id": report.snapshot_id, "status": report.status},
    )
