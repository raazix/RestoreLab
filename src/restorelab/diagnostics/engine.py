"""
RestoreLab Diagnostic Engine
Executes deterministic rule sets across observable command outputs,
manifest differentials, and repository health states.
"""

from __future__ import annotations

from typing import List, Optional
from restorelab.diagnostics.rules import (
    BaseDiagnosticRule,
    DiagnosticContext,
    DiagnosticFinding,
    get_default_diagnostic_rules,
)
from restorelab.config import setup_logging

logger = setup_logging()


class DiagnosticEngine:
    """
    Deterministic rule evaluation engine for backup and recovery troubleshooting.
    Zero hallucination risk: every finding is bound to observable evidence.
    """

    def __init__(self, rules: Optional[List[BaseDiagnosticRule]] = None) -> None:
        self.rules: List[BaseDiagnosticRule] = rules or get_default_diagnostic_rules()

    def register_rule(self, rule: BaseDiagnosticRule) -> None:
        """Register a new diagnostic rule dynamically."""
        self.rules.append(rule)

    def diagnose(self, context: DiagnosticContext) -> List[DiagnosticFinding]:
        """
        Evaluate context against all registered rules.
        Returns matching findings sorted by certainty ('confirmed' > 'likely' > 'unknown').
        """
        findings: List[DiagnosticFinding] = []

        for rule in self.rules:
            try:
                finding = rule.evaluate(context)
                if finding:
                    findings.append(finding)
            except Exception as e:
                logger.error(f"Rule evaluation error in {rule.rule_id}: {e}")

        # If an error occurred but no rule fired, provide an unknown fallback finding
        cmd = context.command_result
        if not findings and cmd and not cmd.success:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_UNCLASSIFIED_FAILURE",
                    rule_name="Unclassified Execution Failure",
                    version="1.0",
                    certainty="unknown",
                    root_cause=f"Process exited with non-zero exit code {cmd.exit_code} without matching known diagnostic signatures.",
                    supporting_evidence=[
                        f"Command: {' '.join(cmd.command)}",
                        f"Exit code: {cmd.exit_code}",
                        f"Stderr: {cmd.stderr.strip()[:200] or 'none'}",
                    ],
                    recommended_checks=[
                        "Inspect raw terminal logs for non-standard error codes.",
                        "Check system event logs or filesystem permissions.",
                    ],
                    suggested_remediation="Review the raw error output in the Incident Explorer and submit an incident report.",
                    kb_reference_id=None,
                )
            )

        # Sort: confirmed first, then likely, then unknown
        certainty_rank = {"confirmed": 0, "likely": 1, "unknown": 2}
        findings.sort(key=lambda f: certainty_rank.get(f.certainty, 3))

        return findings
