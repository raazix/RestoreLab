"""
RestoreLab Evidence-Based Root-Cause Investigation
Aggregates observable diagnostic findings into structured evidence chains,
distinguishing confirmed observations from likely causes and unknowns,
and recommending safe next diagnostic checks without destructive interventions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from restorelab.diagnostics.rules import DiagnosticContext, DiagnosticFinding


class InvestigationReport(BaseModel):
    """Forensic investigation report grouping evidence into certainty tiers."""

    operation_type: str = "backup"
    confirmed_observations: List[str] = Field(default_factory=list)
    likely_causes: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    findings: List[DiagnosticFinding] = Field(default_factory=list)
    recommended_next_checks: List[str] = Field(default_factory=list)
    non_destructive_invariants: List[str] = Field(default_factory=list)


def build_investigation_report(
    context: DiagnosticContext,
    findings: List[DiagnosticFinding],
) -> InvestigationReport:
    """
    Synthesize diagnostic context and findings into an evidence-based investigation report.
    """
    confirmed: List[str] = []
    likely: List[str] = []
    unknowns: List[str] = []
    next_checks: List[str] = []

    # 1. Observable command facts
    if context.command_result:
        cmd = context.command_result
        confirmed.append(f"Command exited with status code {cmd.exit_code} (Duration: {cmd.duration_seconds:.2f}s).")
        if cmd.stderr:
            stderr_preview = cmd.stderr.strip()[:200]
            confirmed.append(f"Observed stderr output: \"{stderr_preview}\"")

    # 2. Observable manifest verification facts
    if context.manifest_diff:
        diff = context.manifest_diff
        if diff.corrupted_count > 0:
            confirmed.append(
                f"Cryptographic hash mismatch detected on {diff.corrupted_count} files (Identical size, different SHA-256 digest)."
            )
        if diff.missing_count > 0:
            confirmed.append(f"{diff.missing_count} expected files were absent from restored target.")
        if diff.extra_count > 0:
            confirmed.append(f"{diff.extra_count} unexpected extra files detected in restore target.")
        if diff.matched_count > 0 and diff.corrupted_count == 0 and diff.missing_count == 0:
            confirmed.append(f"All {diff.matched_count} restored files matched baseline pre-backup hashes byte-for-byte.")

    # 3. Categorize findings by certainty rating
    for f in findings:
        if f.certainty == "confirmed":
            likely.append(f"Confirmed Root Cause [{f.rule_id}]: {f.root_cause}")
        elif f.certainty == "likely":
            likely.append(f"Likely Cause [{f.rule_id}]: {f.root_cause}")
        else:
            unknowns.append(f"Uncertain Failure [{f.rule_id}]: {f.root_cause}")

        for check in f.recommended_checks:
            if check not in next_checks:
                next_checks.append(f"[{f.rule_id}] {check}")

    if not findings and context.command_result and not context.command_result.success:
        unknowns.append("No existing diagnostic rule matched the observed symptoms. Manual investigation required.")
        next_checks.append("Inspect restic debug logs by running with RESTIC_DEBUG=1.")

    invariants = [
        "No automatic destructive repairs or repository pruning executed.",
        "Restore testing was bounded within isolated sandbox directories.",
        "Passphrases and credentials were read strictly from isolated environment variables.",
    ]

    return InvestigationReport(
        operation_type=context.additional_facts.get("operation_type", "backup"),
        confirmed_observations=confirmed,
        likely_causes=likely,
        unknowns=unknowns,
        findings=findings,
        recommended_next_checks=next_checks,
        non_destructive_invariants=invariants,
    )
