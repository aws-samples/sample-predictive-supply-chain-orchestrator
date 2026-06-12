import { useState } from 'react'
import { Play, TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react'

export default function WhatIfScenarios() {
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set())
  const [analysisResult, setAnalysisResult] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const scenarios = [
    {
      id: 1,
      label: 'China supplier unavailable',
      impact: '+$41K cost, -15% risk',
      icon: <AlertTriangle size={14} color="#ef4444" />,
      result: 'Removing Chinese suppliers shifts allocation to South Korea and Germany. TCO increases $41K but geopolitical risk drops 15%. Lead time extends 5 days.'
    },
    {
      id: 2,
      label: 'Rush order (15 day lead time)',
      impact: '+$78K cost, -17 days',
      icon: <TrendingUp size={14} color="#f59e0b" />,
      result: 'Constraining to 15-day lead time eliminates 60% of suppliers. Remaining options cost $78K more due to premium shipping and limited volume discounts.'
    },
    {
      id: 3,
      label: '10% budget cut',
      impact: '-$97K cost, +0.7 risk',
      icon: <TrendingDown size={14} color="#10b981" />,
      result: 'Budget reduction forces lower-tier suppliers. Quality drops 0.8 points, risk increases 0.7 points. Recommend monitoring defect rates closely.'
    },
    {
      id: 4,
      label: 'Prioritize sustainability',
      impact: '+$52K cost, -30% carbon',
      icon: <TrendingUp size={14} color="#10b981" />,
      result: 'Prioritizing low-carbon suppliers reduces CO₂ by 30% at $52K premium. Suppliers with ISO 14001 certification preferred. 3 suppliers qualify.'
    },
    {
      id: 5,
      label: 'Single-source elimination',
      impact: '+$23K cost, -25% risk',
      icon: <AlertTriangle size={14} color="#f59e0b" />,
      result: 'Capping supplier concentration at 25% requires splitting orders across more suppliers. Cost increases $23K but concentration risk drops significantly.'
    }
  ]

  const toggleScenario = (id: number) => {
    setCheckedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    setAnalysisResult(null)
  }

  const runAnalysis = async () => {
    if (checkedIds.size === 0) return
    setIsRunning(true)
    setAnalysisResult(null)

    // Simulate analysis (in production, this calls the optimization engine with modified constraints)
    await new Promise(r => setTimeout(r, 1200))

    const selectedScenarios = scenarios.filter(s => checkedIds.has(s.id))
    const results = selectedScenarios.map(s => `• ${s.label}: ${s.result}`).join('\n\n')
    setAnalysisResult(results)
    setIsRunning(false)
  }

  return (
    <div className="whatif-panel">
      <div className="whatif-header">
        <h4>🔮 What-If Scenarios</h4>
      </div>
      <div className="whatif-description">
        Explore alternative scenarios:
      </div>
      <div className="whatif-scenarios">
        {scenarios.map(scenario => (
          <label key={scenario.id} className="whatif-checkbox-enhanced">
            <div className="whatif-checkbox-row">
              <input
                type="checkbox"
                checked={checkedIds.has(scenario.id)}
                onChange={() => toggleScenario(scenario.id)}
              />
              <span className="whatif-label">{scenario.label}</span>
            </div>
            <div className="whatif-impact">
              {scenario.icon}
              <span>{scenario.impact}</span>
            </div>
          </label>
        ))}
      </div>
      <button
        className="whatif-run-btn"
        onClick={runAnalysis}
        disabled={checkedIds.size === 0 || isRunning}
        style={{ opacity: checkedIds.size === 0 ? 0.5 : 1 }}
      >
        {isRunning ? (
          <>⏳ Analyzing...</>
        ) : (
          <>
            <Play size={14} />
            Run Scenario Analysis ({checkedIds.size} selected)
          </>
        )}
      </button>

      {analysisResult && (
        <div style={{
          marginTop: '12px', padding: '12px', background: '#f0fdf4',
          borderRadius: '8px', border: '1px solid #bbf7d0', fontSize: '13px',
          lineHeight: '1.6', whiteSpace: 'pre-line', color: '#15803d'
        }}>
          <div style={{ fontWeight: 600, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle size={14} /> Analysis Complete
          </div>
          {analysisResult}
        </div>
      )}

      <div className="whatif-note">
        💡 Select one or more scenarios to compare against baseline
      </div>
    </div>
  )
}
