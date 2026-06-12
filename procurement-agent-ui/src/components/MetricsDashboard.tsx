import { useState, useEffect } from 'react'
import { TrendingDown, Package, AlertTriangle, Clock } from 'lucide-react'
import { suppliers as fallbackSuppliers } from '../data/realData'
import { fetchSuppliers, type BackendSupplier } from '../services/api'

export default function MetricsDashboard() {
  const [liveSuppliers, setLiveSuppliers] = useState<BackendSupplier[] | null>(null)

  useEffect(() => {
    fetchSuppliers().then(sups => {
      if (sups.length > 0) setLiveSuppliers(sups)
    })
  }, [])

  // Compute metrics from live data or fallback
  let avgRisk: string
  let avgLeadTime: number

  if (liveSuppliers && liveSuppliers.length > 0) {
    avgRisk = (liveSuppliers.reduce((sum, s) => sum + s.geopolitical_risk_score, 0) / liveSuppliers.length).toFixed(1)
    avgLeadTime = Math.round(liveSuppliers.reduce((sum, s) => sum + s.lead_time_days, 0) / liveSuppliers.length)
  } else {
    avgRisk = (fallbackSuppliers.reduce((sum, s) => sum + s.geopoliticalRisk, 0) / fallbackSuppliers.length).toFixed(1)
    avgLeadTime = Math.round(fallbackSuppliers.reduce((sum, s) => sum + s.leadTimeDays, 0) / fallbackSuppliers.length)
  }

  const getRiskLevel = (risk: number) => {
    if (risk < 2.5) return 'Low'
    if (risk < 3.5) return 'Medium'
    return 'High'
  }

  return (
    <div className="metrics-dashboard">
      <div className="metric-card">
        <div className="metric-icon" style={{ backgroundColor: '#dcfce7' }}>
          <TrendingDown size={24} color="#10b981" />
        </div>
        <div className="metric-info">
          <div className="metric-label">Cost Savings</div>
          <div className="metric-value">35%</div>
          <div className="metric-change positive">vs baseline</div>
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-icon" style={{ backgroundColor: '#dbeafe' }}>
          <Package size={24} color="#3b82f6" />
        </div>
        <div className="metric-info">
          <div className="metric-label">Material Availability</div>
          <div className="metric-value">98%</div>
          <div className="metric-change positive">from 85%</div>
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-icon" style={{ backgroundColor: '#fef3c7' }}>
          <AlertTriangle size={24} color="#f59e0b" />
        </div>
        <div className="metric-info">
          <div className="metric-label">Supplier Risk</div>
          <div className="metric-value">{avgRisk}/10</div>
          <div className="metric-change neutral">{getRiskLevel(parseFloat(avgRisk))}</div>
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-icon" style={{ backgroundColor: '#e0e7ff' }}>
          <Clock size={24} color="#6366f1" />
        </div>
        <div className="metric-info">
          <div className="metric-label">Avg Lead Time</div>
          <div className="metric-value">{avgLeadTime} days</div>
          <div className="metric-change positive">Network average</div>
        </div>
      </div>
    </div>
  )
}
