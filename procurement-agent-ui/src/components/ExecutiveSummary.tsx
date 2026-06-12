import { TrendingDown, Shield, Clock, Users } from 'lucide-react'
import { paretoSolutions } from '../data/realData'

interface ExecutiveSummaryProps {
  selectedSolution: string | null
}

export default function ExecutiveSummary({ selectedSolution }: ExecutiveSummaryProps) {
  const solution = paretoSolutions.find(s => s.id === selectedSolution) || paretoSolutions[1]
  const baseline = paretoSolutions[0] // Cost-optimized as baseline
  const savings = baseline.totalCost - solution.totalCost
  const savingsPercent = ((savings / baseline.totalCost) * 100).toFixed(1)

  return (
    <div className="executive-summary">
      <div className="exec-header">
        <h4>📊 Executive Summary</h4>
        <span className="exec-recommendation">Recommended</span>
      </div>
      
      <div className="exec-solution-name">{solution.name} Solution</div>
      
      <div className="exec-metrics">
        <div className="exec-metric-primary">
          <div className="exec-metric-label">Total Cost</div>
          <div className="exec-metric-value">${(solution.totalCost / 1000).toFixed(0)}K</div>
        </div>
        
        <div className="exec-metric-secondary">
          <TrendingDown size={16} color="#10b981" />
          <div>
            <div className="exec-metric-label">Savings vs Baseline</div>
            <div className="exec-metric-value-small">${Math.abs(savings).toLocaleString()} ({Math.abs(parseFloat(savingsPercent))}%)</div>
          </div>
        </div>
      </div>

      <div className="exec-kpis">
        <div className="exec-kpi">
          <Shield size={18} color="#3b82f6" />
          <div>
            <div className="exec-kpi-label">Risk Score</div>
            <div className="exec-kpi-value">{solution.riskScore}/10</div>
            <div className="exec-kpi-status">Low Risk</div>
          </div>
        </div>

        <div className="exec-kpi">
          <Clock size={18} color="#3b82f6" />
          <div>
            <div className="exec-kpi-label">Lead Time</div>
            <div className="exec-kpi-value">{solution.maxLeadTimeDays} days</div>
            <div className="exec-kpi-status">Acceptable</div>
          </div>
        </div>

        <div className="exec-kpi">
          <Users size={18} color="#3b82f6" />
          <div>
            <div className="exec-kpi-label">Diversification</div>
            <div className="exec-kpi-value">{solution.supplierConcentration.length} suppliers</div>
            <div className="exec-kpi-status">Excellent</div>
          </div>
        </div>
      </div>

      <div className="exec-actions">
        <button className="exec-btn-primary">
          Approve & Send to ERP
        </button>
        <button className="exec-btn-secondary">
          Export PDF Report
        </button>
      </div>
    </div>
  )
}
