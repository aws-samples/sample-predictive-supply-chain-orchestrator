import { TrendingUp, Shield, Zap, BarChart3, FileCheck, ChevronRight } from 'lucide-react'

interface WorkflowStep {
  key: string
  label: string
  view: string
  icon: typeof TrendingUp
  description: string
  optional?: boolean
}

const STEPS: WorkflowStep[] = [
  { key: 'forecast', label: 'Forecast', view: 'demand', icon: TrendingUp, description: 'Predict demand with Chronos-2' },
  { key: 'risk', label: 'Assess Risk', view: 'map', icon: Shield, description: 'Geopolitical scenarios', optional: true },
  { key: 'optimize', label: 'Optimize', view: 'results', icon: Zap, description: '3 Pareto strategies' },
  { key: 'analyze', label: 'Analyze', view: 'analysis', icon: BarChart3, description: 'Supplier deep-dive' },
  { key: 'execute', label: 'Execute', view: 'approve', icon: FileCheck, description: 'Purchase requisitions' },
]

interface WorkflowStepperProps {
  activeView: string
  onNavigate: (view: string) => void
  completedSteps: Set<string>
  loadingStep?: string
}

export default function WorkflowStepper({ activeView, onNavigate, completedSteps, loadingStep }: WorkflowStepperProps) {
  const activeStep = STEPS.find(s => s.view === activeView)?.key || ''

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 0,
      padding: '8px 16px',
      background: 'var(--color-surface)',
      borderBottom: '1px solid var(--color-border)',
      overflowX: 'auto',
      flexShrink: 0,
    }}>
      {STEPS.map((step, idx) => {
        const isActive = step.key === activeStep
        const isCompleted = completedSteps.has(step.key)
        const isLoadingStep = loadingStep === step.key
        const isPast = STEPS.findIndex(s => s.key === activeStep) > idx

        return (
          <div key={step.key} style={{ display: 'flex', alignItems: 'center' }}>
            <button
              onClick={() => onNavigate(step.view)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 14px', borderRadius: 8, border: 'none',
                background: isActive ? 'var(--color-primary)' : isLoadingStep ? 'rgba(59,130,246,0.08)' : isCompleted || isPast ? 'rgba(34,197,94,0.08)' : 'transparent',
                cursor: 'pointer', transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {/* Step number/check */}
              <div style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700,
                background: isActive ? '#fff' : isCompleted ? '#22c55e' : 'var(--color-border)',
                color: isActive ? 'var(--color-primary)' : isCompleted ? '#fff' : 'var(--color-text-muted)',
              }}>
                {isLoadingStep ? '⏳' : isCompleted ? '✓' : idx + 1}
              </div>

              {/* Label */}
              <div style={{ textAlign: 'left' }}>
                <div style={{
                  fontSize: 12, fontWeight: 600,
                  color: isActive ? '#fff' : isCompleted ? '#22c55e' : 'var(--color-text-secondary)',
                }}>
                  {step.label}
                </div>
                <div style={{
                  fontSize: 9,
                  color: isActive ? 'rgba(255,255,255,0.7)' : 'var(--color-text-muted)',
                  marginTop: 1,
                }}>
                  {step.description}{step.optional ? ' (optional)' : ''}
                </div>
              </div>
            </button>

            {/* Connector arrow */}
            {idx < STEPS.length - 1 && (
              <ChevronRight
                size={14}
                style={{
                  color: isPast || isCompleted ? '#22c55e' : 'var(--color-border)',
                  flexShrink: 0, margin: '0 2px',
                }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
