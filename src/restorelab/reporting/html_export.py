"""
RestoreLab HTML & JSON Report Generation Engine
Renders self-contained, publication-ready audit reports for recovery drills,
cryptographic verification audits, readiness assessments, and incident post-mortems.
Includes cryptographic SHA-256 integrity signatures for verifiable record keeping.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional

from restorelab.incidents.models import (
    IncidentRecord,
    ReadinessAssessment,
    RecoveryDrillRecord,
)
from restorelab.reporting.exports import ExportedReport
from restorelab.verification.restore import RecoveryVerificationReport

# Self-contained CSS for high-fidelity dark-mode engineering audit reports
HTML_REPORT_CSS = """
:root {
  --bg-primary: #0a0b0d;
  --bg-secondary: #12151a;
  --bg-card: #181c24;
  --border: #262b35;
  --text-main: #f1f3f7;
  --text-muted: #8b949e;
  --accent: #5e6ad2;
  --success: #10b981;
  --danger: #ef4444;
  --warning: #f59e0b;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg-primary: #f8fafc;
    --bg-secondary: #f1f5f9;
    --bg-card: #ffffff;
    --border: #e2e8f0;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --accent: #4f46e5;
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: var(--font-sans);
  line-height: 1.5;
  padding: 2.5rem 1rem;
}
.report-container {
  max-width: 960px;
  margin: 0 auto;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
}
.report-header {
  padding: 2rem;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(94, 106, 210, 0.05) 0%, transparent 100%);
}
.report-brand {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.brand-title {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
}
.signature-badge {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  background: var(--bg-card);
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--border);
  color: var(--text-muted);
}
h1 {
  font-size: 1.6rem;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 0.5rem;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
}
.meta-item {
  display: flex;
  flex-direction: column;
}
.meta-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}
.meta-val {
  font-size: 0.92rem;
  font-weight: 500;
  font-family: var(--font-mono);
}
.status-pill {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.status-pill.success { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }
.status-pill.danger { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); }
.status-pill.warning { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.3); }
.report-body {
  padding: 2rem;
}
.section {
  margin-bottom: 2rem;
}
.section:last-child {
  margin-bottom: 0;
}
h2 {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 0.85rem;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.stat-card {
  background: var(--bg-card);
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid var(--border);
}
.stat-num {
  font-size: 1.4rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-main);
}
.stat-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}
.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}
.audit-table th, .audit-table td {
  padding: 0.65rem 0.85rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.audit-table th {
  background: var(--bg-card);
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.audit-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}
.code-block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  padding: 1rem;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  overflow-x: auto;
  white-space: pre-wrap;
  color: var(--text-main);
}
.bullet-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.bullet-list li {
  font-size: 0.88rem;
  color: var(--text-main);
  padding-left: 1.25rem;
  position: relative;
}
.bullet-list li::before {
  content: "•";
  position: absolute;
  left: 0.25rem;
  color: var(--accent);
  font-weight: bold;
}
.alert-box {
  background: rgba(94, 106, 210, 0.08);
  border-left: 3px solid var(--accent);
  padding: 0.85rem 1.15rem;
  border-radius: 0 4px 4px 0;
  font-size: 0.88rem;
  margin-bottom: 1rem;
}
.report-footer {
  padding: 1.5rem 2rem;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  color: var(--text-muted);
}
"""


def _wrap_html_document(title: str, body_html: str, fingerprint: str) -> str:
    """Surround rendered sections with modern, secure standalone HTML5 scaffolding."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="generator" content="RestoreLab Audit Reporter">
  <meta name="x-audit-signature" content="{escape(fingerprint)}">
  <style>{HTML_REPORT_CSS}</style>
</head>
<body>
  <div class="report-container">
    {body_html}
    <div class="report-footer">
      <div>Generated by <strong>RestoreLab Engineering Workbench</strong></div>
      <div style="font-family: var(--font-mono);">SHA-256 Digest: {escape(fingerprint[:16])}...</div>
    </div>
  </div>
</body>
</html>"""


def export_drill_html(drill: RecoveryDrillRecord) -> ExportedReport:
    """Format an automated/manual recovery drill into a verified HTML compliance report."""
    now = datetime.now(timezone.utc).isoformat()
    status_class = (
        "success" if drill.status == "SUCCESS"
        else "danger" if drill.status == "FAILED"
        else "warning"
    )
    rto_status_class = "success" if drill.rto_compliant else "danger"

    body_html = f"""
    <div class="report-header">
      <div class="report-brand">
        <span class="brand-title">RestoreLab / Recovery Drill Audit</span>
        <span class="signature-badge">{escape(drill.drill_id)}</span>
      </div>
      <h1>Recovery Drill Audit Record</h1>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        Automated sandbox verification of backup snapshot restoration and cryptographic integrity.
      </p>
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Audit Status</span>
          <div><span class="status-pill {status_class}">{escape(drill.status)}</span></div>
        </div>
        <div class="meta-item">
          <span class="meta-label">Snapshot ID</span>
          <span class="meta-val">{escape(drill.snapshot_id[:12])}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Execution Type</span>
          <span class="meta-val" style="text-transform: capitalize;">{escape(drill.drill_type)}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Timestamp (UTC)</span>
          <span class="meta-val">{escape(drill.created_at[:19])}</span>
        </div>
      </div>
    </div>

    <div class="report-body">
      <div class="section">
        <h2>1. Recovery Time Objective (RTO) Metrics</h2>
        <div class="stat-cards">
          <div class="stat-card">
            <div class="stat-num">{drill.duration_seconds:.2f}s</div>
            <div class="stat-desc">Actual Recovery Time</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{drill.rto_target_seconds:.1f}s</div>
            <div class="stat-desc">Target RTO Limit</div>
          </div>
          <div class="stat-card">
            <div class="stat-num"><span class="status-pill {rto_status_class}">{"Compliant" if drill.rto_compliant else "Breached"}</span></div>
            <div class="stat-desc">RTO SLA Status</div>
          </div>
        </div>
      </div>

      <div class="section">
        <h2>2. Cryptographic SHA-256 Verification Summary</h2>
        <div class="stat-cards">
          <div class="stat-card">
            <div class="stat-num" style="color: var(--success);">{drill.matched_files}</div>
            <div class="stat-desc">Verified 100% Matches</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" style="color: var(--danger);">{drill.corrupted_files}</div>
            <div class="stat-desc">Hash Corruptions</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" style="color: var(--warning);">{drill.missing_files}</div>
            <div class="stat-desc">Missing Files</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{drill.extra_files}</div>
            <div class="stat-desc">Unexpected Extra Files</div>
          </div>
        </div>
      </div>

      <div class="section">
        <h2>3. Forensic Sandbox Findings & Audit Trace</h2>
        <div class="alert-box">
          <strong>Outcome Finding:</strong> {escape(drill.evidence_summary or "Drill completed within designated parameters.")}
        </div>
        <table class="audit-table">
          <thead>
            <tr>
              <th>Property</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Restore Target Sandbox</td>
              <td><code>{escape(drill.restore_target_path)}</code></td>
            </tr>
            <tr>
              <td>Sandbox Auto-Cleaned</td>
              <td>{"Yes (Storage recycled safely)" if drill.sandbox_cleaned else "No (Retained for forensics)"}</td>
            </tr>
            <tr>
              <td>Drill ID</td>
              <td><code>{escape(drill.drill_id)}</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """

    # Pre-compute fingerprint on unadorned template, then re-wrap with signature
    temp_html = _wrap_html_document(f"Recovery Drill {drill.drill_id}", body_html, "PENDING")
    fingerprint = hashlib.sha256(temp_html.encode("utf-8")).hexdigest()
    final_html = _wrap_html_document(f"Recovery Drill {drill.drill_id}", body_html, fingerprint)

    return ExportedReport(
        report_id=drill.drill_id,
        report_type="recovery_drill_report",
        generated_at=now,
        content_format="html",
        content=final_html,
        sha256_fingerprint=fingerprint,
        metadata={
            "drill_id": drill.drill_id,
            "snapshot_id": drill.snapshot_id,
            "status": drill.status,
            "duration_seconds": drill.duration_seconds,
            "rto_compliant": drill.rto_compliant,
        },
    )


def export_verification_html(report: RecoveryVerificationReport) -> ExportedReport:
    """Format a recovery verification test into a standalone HTML audit certificate."""
    now = datetime.now(timezone.utc).isoformat()
    status_class = (
        "success" if report.status == "SUCCESS"
        else "danger" if report.status == "FAILED"
        else "warning"
    )

    diff_rows_html = ""
    if report.comparison_result and report.comparison_result.diffs:
        for d in report.comparison_result.diffs[:25]:
            d_class = "success" if d.status == "MATCH" else "danger" if d.status == "CORRUPTED" else "warning"
            exp_sha = (d.expected_sha256 or "N/A")[:12] + "..." if d.expected_sha256 else "-"
            act_sha = (d.actual_sha256 or "N/A")[:12] + "..." if d.actual_sha256 else "-"
            diff_rows_html += f"""
            <tr>
              <td><code>{escape(d.path)}</code></td>
              <td><span class="status-pill {d_class}">{escape(d.status)}</span></td>
              <td><code>{escape(exp_sha)}</code></td>
              <td><code>{escape(act_sha)}</code></td>
              <td>{escape(d.details)}</td>
            </tr>
            """

    body_html = f"""
    <div class="report-header">
      <div class="report-brand">
        <span class="brand-title">RestoreLab / Cryptographic Recovery Audit</span>
        <span class="signature-badge">{escape(report.id)}</span>
      </div>
      <h1>Cryptographic Verification Audit Certificate</h1>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        Deterministic byte-for-byte SHA-256 verification against original baseline manifest.
      </p>
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Audit Outcome</span>
          <div><span class="status-pill {status_class}">{escape(report.status)}</span></div>
        </div>
        <div class="meta-item">
          <span class="meta-label">Snapshot ID</span>
          <span class="meta-val">{escape(report.snapshot_id[:12])}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Restore Duration</span>
          <span class="meta-val">{report.restore_duration_seconds:.2f}s</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Audit Timestamp</span>
          <span class="meta-val">{escape(report.timestamp[:19])}</span>
        </div>
      </div>
    </div>

    <div class="report-body">
      <div class="section">
        <h2>1. Verification Outcome & Diagnostics</h2>
        <div class="alert-box">
          <strong>Diagnostics:</strong> {escape(report.diagnostics_summary)}
        </div>
      </div>

      <div class="section">
        <h2>2. Manifest & Content Verification Details</h2>
        <table class="audit-table">
          <tbody>
            <tr>
              <td>Source Baseline Manifest ID</td>
              <td><code>{escape(report.original_manifest_id)}</code></td>
            </tr>
            <tr>
              <td>Restored Directory Manifest ID</td>
              <td><code>{escape(report.restored_manifest_id or "N/A")}</code></td>
            </tr>
            <tr>
              <td>Restore Sandbox Target</td>
              <td><code>{escape(report.restore_target_path)}</code></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section">
        <h2>3. File-by-File Cryptographic Breakdown</h2>
        <table class="audit-table">
          <thead>
            <tr>
              <th>Relative File Path</th>
              <th>Status</th>
              <th>Expected Digest</th>
              <th>Restored Digest</th>
              <th>Forensic Detail</th>
            </tr>
          </thead>
          <tbody>
            {diff_rows_html or '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No diffs cataloged.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
    """

    temp_html = _wrap_html_document(f"Verification Audit {report.snapshot_id}", body_html, "PENDING")
    fingerprint = hashlib.sha256(temp_html.encode("utf-8")).hexdigest()
    final_html = _wrap_html_document(f"Verification Audit {report.snapshot_id}", body_html, fingerprint)

    return ExportedReport(
        report_id=report.id,
        report_type="recovery_verification_audit",
        generated_at=now,
        content_format="html",
        content=final_html,
        sha256_fingerprint=fingerprint,
        metadata={
            "report_id": report.id,
            "snapshot_id": report.snapshot_id,
            "status": report.status,
            "duration": report.restore_duration_seconds,
        },
    )


def export_readiness_html(readiness: ReadinessAssessment) -> ExportedReport:
    """Format disaster recovery readiness analytics into a clean executive audit."""
    now = datetime.now(timezone.utc).isoformat()
    tier_class = (
        "success" if readiness.readiness_tier == "OPTIMAL"
        else "warning" if readiness.readiness_tier == "ACCEPTABLE"
        else "danger"
    )

    limitations_html = "".join(f"<li>{escape(lim)}</li>" for lim in readiness.metric_limitations)

    body_html = f"""
    <div class="report-header">
      <div class="report-brand">
        <span class="brand-title">RestoreLab / Disaster Recovery Analytics</span>
        <span class="signature-badge">{escape(readiness.assessment_id)}</span>
      </div>
      <h1>Disaster Recovery Readiness Audit</h1>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        Objective readiness scoring derived strictly from persisted recovery drill history and snapshot coverage.
      </p>
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Readiness Score</span>
          <span class="meta-val" style="font-size: 1.5rem; color: var(--accent);">{readiness.score} / 100</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Readiness Tier</span>
          <div><span class="status-pill {tier_class}">{escape(readiness.readiness_tier)}</span></div>
        </div>
        <div class="meta-item">
          <span class="meta-label">Tested Snapshot Coverage</span>
          <span class="meta-val">{readiness.coverage_ratio * 100:.1f}% ({readiness.tested_snapshots_count}/{readiness.total_eligible_snapshots})</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">RTO SLA Compliance</span>
          <span class="meta-val">{readiness.rto_compliance_rate * 100:.1f}%</span>
        </div>
      </div>
    </div>

    <div class="report-body">
      <div class="section">
        <h2>1. Historical Recovery Drill Statistics</h2>
        <div class="stat-cards">
          <div class="stat-card">
            <div class="stat-num" style="color: var(--success);">{readiness.successful_drills_count}</div>
            <div class="stat-desc">Successful Drills</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" style="color: var(--danger);">{readiness.failed_drills_count}</div>
            <div class="stat-desc">Failed Drills</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{readiness.average_restore_seconds:.2f}s</div>
            <div class="stat-desc">Avg Restoration Time</div>
          </div>
          <div class="stat-card">
            <div class="stat-num" style="color: {'var(--danger)' if readiness.unresolved_incidents_count > 0 else 'var(--text-muted)'};">{readiness.unresolved_incidents_count}</div>
            <div class="stat-desc">Active Unresolved Incidents</div>
          </div>
        </div>
      </div>

      <div class="section">
        <h2>2. Data Freshness & Snapshot Age (RPO)</h2>
        <div class="alert-box">
          <strong>Latest Snapshot Age:</strong> {f"{readiness.latest_snapshot_age_hours:.1f} hours" if readiness.latest_snapshot_age_hours is not None else "No snapshots cataloged"}
        </div>
      </div>

      <div class="section">
        <h2>3. Documented Metric Limitations & Assumptions</h2>
        <ul class="bullet-list">
          {limitations_html}
        </ul>
      </div>
    </div>
    """

    temp_html = _wrap_html_document(f"DR Readiness Assessment {readiness.assessment_id}", body_html, "PENDING")
    fingerprint = hashlib.sha256(temp_html.encode("utf-8")).hexdigest()
    final_html = _wrap_html_document(f"DR Readiness Assessment {readiness.assessment_id}", body_html, fingerprint)

    return ExportedReport(
        report_id=readiness.assessment_id,
        report_type="readiness_assessment_report",
        generated_at=now,
        content_format="html",
        content=final_html,
        sha256_fingerprint=fingerprint,
        metadata={
            "assessment_id": readiness.assessment_id,
            "score": readiness.score,
            "tier": readiness.readiness_tier,
            "coverage_ratio": readiness.coverage_ratio,
        },
    )


def export_drill_json(drill: RecoveryDrillRecord) -> ExportedReport:
    """Format recovery drill record as structured, fingerprint-verified JSON."""
    now = datetime.now(timezone.utc).isoformat()
    raw_dict = drill.model_dump()
    raw_dict["_export_generated_at"] = now
    json_str = json.dumps(raw_dict, indent=2)
    fingerprint = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    return ExportedReport(
        report_id=drill.drill_id,
        report_type="recovery_drill_json",
        generated_at=now,
        content_format="json",
        content=json_str,
        sha256_fingerprint=fingerprint,
        metadata={"drill_id": drill.drill_id, "snapshot_id": drill.snapshot_id},
    )


def export_readiness_json(readiness: ReadinessAssessment) -> ExportedReport:
    """Format disaster recovery readiness assessment as structured JSON."""
    now = datetime.now(timezone.utc).isoformat()
    raw_dict = readiness.model_dump()
    raw_dict["_export_generated_at"] = now
    json_str = json.dumps(raw_dict, indent=2)
    fingerprint = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    return ExportedReport(
        report_id=readiness.assessment_id,
        report_type="readiness_assessment_json",
        generated_at=now,
        content_format="json",
        content=json_str,
        sha256_fingerprint=fingerprint,
        metadata={"assessment_id": readiness.assessment_id, "score": readiness.score},
    )
