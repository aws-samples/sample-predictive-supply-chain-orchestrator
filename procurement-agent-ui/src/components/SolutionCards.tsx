import { useState } from 'react'
import { Check, TrendingDown, Shield, Clock, Package } from 'lucide-react'
import type { OptimizationSolution } from '../data/realData'

interface SolutionCardsProps {
  solutions: OptimizationSolution[]
  selectedSolution: string | null
  onSelectSolution: (id: string) => void
  onViewAnalysis?: () => void
  onApprovePRs?: () => void
}

export default function SolutionCards({ solutions, selectedSolution, onSelectSolution, onViewAnalysis, onApprovePRs }: SolutionCardsProps) {
  const [confirmingPR, setConfirmingPR] = useState<string | null>(null)

  const getRiskColor = (risk: number) => {
    if (risk < 3) return '#10b981' // green
    if (risk < 6) return '#f59e0b' // yellow
    return '#ef4444' // red
  }

  const getRiskLabel = (risk: number) => {
    if (risk < 3) return 'Low Risk'
    if (risk < 6) return 'Medium Risk'
    return 'High Risk'
  }

  return (
    <div className="solution-cards-container">
      {solutions.map((solution) => {
        const isSelected = solution.id === selectedSolution
        const riskColor = getRiskColor(solution.riskScore)

        return (
          <div 
            key={solution.id}
            className={`solution-card ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelectSolution(solution.id)}
          >
            <div className="card-header">
              <h4>{solution.name}</h4>
              {isSelected && <Check className="check-icon" size={20} />}
            </div>

            <div className="card-metrics">
              <div className="metric">
                <TrendingDown size={18} color="#10b981" />
                <div>
                  <div className="metric-label">Total Cost</div>
                  <div className="metric-value">${(solution.totalCost / 1000).toFixed(1)}k</div>
                </div>
              </div>

              <div className="metric">
                <Shield size={18} color={riskColor} />
                <div>
                  <div className="metric-label">Risk Score</div>
                  <div className="metric-value" style={{ color: riskColor }}>
                    {solution.riskScore.toFixed(1)}/10
                  </div>
                  <div className="metric-sublabel">{getRiskLabel(solution.riskScore)}</div>
                </div>
              </div>

              <div className="metric">
                <Clock size={18} color="#3b82f6" />
                <div>
                  <div className="metric-label">Lead Time</div>
                  <div className="metric-value">{solution.maxLeadTimeDays} days</div>
                </div>
              </div>
            </div>

            <div className="card-explanation">
              {solution.explanation}
              {solution.demandBufferPct && (
                <div style={{ marginTop: '8px', padding: '4px 8px', background: '#fef3c7', borderRadius: '4px', fontSize: '12px', color: '#92400e' }}>
                  📦 +{solution.demandBufferPct}% demand buffer for supply resilience
                </div>
              )}
            </div>

            <div className="card-suppliers">
              <div className="suppliers-label">
                <Package size={16} />
                <span>{new Set(solution.allocations.map((a: any) => a.materialId)).size} Materials | {solution.supplierConcentration.length} Suppliers | {solution.allocations.length} Orders</span>
              </div>
              <div className="supplier-concentration">
                {solution.supplierConcentration.slice(0, 5).map((conc, idx) => (
                  <div key={idx} className="concentration-item">
                    <span className="supplier-name">{conc.supplierName}</span>
                    <div className="concentration-bar">
                      <div 
                        className="concentration-fill" 
                        style={{ 
                          width: `${conc.percentage}%`,
                          backgroundColor: conc.percentage > 40 ? '#ef4444' : '#10b981'
                        }}
                      />
                    </div>
                    <span className="concentration-pct">{conc.percentage}%</span>
                  </div>
                ))}
                {solution.supplierConcentration.length > 5 && (
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    +{solution.supplierConcentration.length - 5} more suppliers
                  </div>
                )}
              </div>
            </div>

            <button className={`approve-button ${isSelected ? 'selected' : ''}`}>
              {isSelected ? '✓ Selected' : 'Select Solution'}
            </button>

            {isSelected && (
              <button 
                className="create-pr-button"
                onClick={(e) => {
                  e.stopPropagation()
                  onApprovePRs?.()
                }}
              >
                📋 Approve & Create PRs
              </button>
            )}
            {isSelected && onViewAnalysis && (
              <button
                className="view-analysis-button"
                onClick={(e) => {
                  e.stopPropagation()
                  onViewAnalysis()
                }}
              >
                📊 View Analysis →
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
