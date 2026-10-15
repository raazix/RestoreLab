import React, { useEffect, useState } from 'react'
import {
  FlaskConical,
  Play,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Terminal,
  Layers,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, ExperimentResult, ExperimentScenario, SystemStatus } from '@/lib/api'

interface ExperimentsViewProps {
  systemStatus: SystemStatus | null
  onRefreshMetrics: () => void
}

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({
  systemStatus,
  onRefreshMetrics,
}) => {
  const [scenarios, setScenarios] = useState<ExperimentScenario[]>([])
  const [loadingScenarios, setLoadingScenarios] = useState(false)
  const [runningScenarioId, setRunningScenarioId] = useState<string | null>(null)
  const [experimentResult, setExperimentResult] = useState<ExperimentResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const fetchScenarios = async () => {
    setLoadingScenarios(true)
    try {
      const data = await api.getExperiments()
      setScenarios(data)
    } catch (err: any) {
      setErrorMsg(`Failed to load scenarios: ${err.message}`)
    } finally {
      setLoadingScenarios(false)
    }
  }

  useEffect(() => {
    fetchScenarios()
  }, [])

  const handleRunExperiment = async (scenarioId: string) => {
    setRunningScenarioId(scenarioId)
    setExperimentResult(null)
    setErrorMsg(null)

    try {
      const result = await api.runExperiment(scenarioId)
      setExperimentResult(result)
      onRefreshMetrics()
    } catch (err: any) {
      setErrorMsg(`Experiment failed: ${err.message}`)
    } finally {
      setRunningScenarioId(null)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Controlled Failure Experiments
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Safely simulate real-world failure scenarios against disposable fixtures.
          Active repositories are never altered; scratchpads are automatically purged after evaluation.
        </p>
      </div>

      {/* Disposable Safety Guarantee Banner */}
      <div className="p-3.5 rounded-xl bg-surface-2 border border-border-subtle flex items-center justify-between text-xs">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-zinc-300">
            <strong>Active Repository Invariant:</strong> All destructive tests execute strictly inside disposable scratchpad directories.
          </span>
        </div>
        <Badge variant="emerald" dot>
          Safety Active
        </Badge>
      </div>

      {/* Result Card (If run) */}
      {experimentResult && (
        <Card className="space-y-4 border-indigo-500/30 bg-surface-2">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-indigo-400" />
              <CardTitle>
                Diagnostic Evaluation: <span className="font-mono text-cyan-400">{experimentResult.scenario_id}</span>
              </CardTitle>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px]">
              <span className="text-zinc-400">Duration: {experimentResult.duration_seconds.toFixed(2)}s</span>
              {experimentResult.scratchpad_purged && (
                <Badge variant="emerald" dot>
                  Scratchpad Purged
                </Badge>
              )}
            </div>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-3 rounded bg-surface-1 font-mono text-zinc-300 border border-border-subtle">
              <strong className="text-zinc-400">Observed Symptom:</strong> {experimentResult.symptom_observed}
            </div>

            {experimentResult.findings && experimentResult.findings.length > 0 ? (
              <div className="space-y-2 pt-2">
                <span className="text-zinc-400 uppercase tracking-wider text-[10px] font-bold">
                  Deterministic Rule Engine Match
                </span>
                {experimentResult.findings.map((f, i) => (
                  <div key={i} className="p-3 rounded bg-surface-3 border border-border-muted space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-cyan-400">{f.rule_id}</span>
                      <Badge variant="emerald">Certainty: {f.certainty.toUpperCase()}</Badge>
                    </div>
                    <div className="text-zinc-200">
                      <strong>Root Cause:</strong> {f.root_cause}
                    </div>
                    {f.prescriptive_remediations && (
                      <div className="text-zinc-400 text-[11px]">
                        <strong>Prescriptive Remediation:</strong> {f.prescriptive_remediations.join('; ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-zinc-500 text-xs">No specific diagnostic rules matched.</div>
            )}
          </div>
        </Card>
      )}

      {/* Grid of Scenarios */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {scenarios.map((scenario) => {
          const isRunning = runningScenarioId === scenario.id

          return (
            <Card key={scenario.id} className="flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Badge variant="cyan" className="font-mono text-[10px]">
                    {scenario.id}
                  </Badge>
                  <span className="font-mono text-[10px] text-zinc-500">
                    Rule: {scenario.target_rule_id}
                  </span>
                </div>

                <h3 className="text-xs font-bold text-zinc-100">{scenario.title}</h3>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {scenario.description}
                </p>

                <div className="p-2 rounded bg-surface-2 text-[11px] font-mono text-zinc-400 border border-border-subtle">
                  <span className="text-zinc-500">Expected:</span> {scenario.expected_outcome}
                </div>
              </div>

              <Button
                size="sm"
                variant="secondary"
                isLoading={isRunning}
                onClick={() => handleRunExperiment(scenario.id)}
                leftIcon={<Play className="w-3.5 h-3.5 text-indigo-400" />}
              >
                Run Experiment in Scratchpad
              </Button>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
