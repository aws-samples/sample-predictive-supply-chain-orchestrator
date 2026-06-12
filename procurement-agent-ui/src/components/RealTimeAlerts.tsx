import { AlertTriangle, TrendingDown } from 'lucide-react'

export default function RealTimeAlerts() {
  const alerts = [
    {
      id: 1,
      severity: 'high',
      icon: '🔴',
      title: 'Strait of Hormuz Closure',
      impact: '+14 days from Asia',
      affected: '3 suppliers',
      action: 'View Alternatives'
    },
    {
      id: 2,
      severity: 'medium',
      icon: '🟡',
      title: 'Typhoon Season Active',
      impact: 'Possible port delays',
      affected: '2 suppliers',
      action: 'Monitor'
    },
    {
      id: 3,
      severity: 'opportunity',
      icon: '🟢',
      title: 'Price Drop: Aluminum -8%',
      impact: '$12K savings opportunity',
      affected: 'Frame suppliers',
      action: 'Re-optimize'
    }
  ]

  return (
    <div className="alerts-panel">
      <div className="alerts-header">
        <h4>🔔 Real-Time Alerts</h4>
        <span className="alerts-count">{alerts.length}</span>
      </div>
      <div className="alerts-list">
        {alerts.map(alert => (
          <div key={alert.id} className={`alert-item alert-${alert.severity}`}>
            <div className="alert-icon">{alert.icon}</div>
            <div className="alert-content">
              <div className="alert-title">{alert.title}</div>
              <div className="alert-impact">{alert.impact}</div>
              <div className="alert-affected">Affected: {alert.affected}</div>
            </div>
            <button className="alert-action-btn">{alert.action}</button>
          </div>
        ))}
      </div>
    </div>
  )
}
