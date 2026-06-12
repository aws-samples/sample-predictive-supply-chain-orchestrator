import { CheckCircle, RefreshCw, Settings } from 'lucide-react'

export default function ERPIntegrationPanel() {
  return (
    <div className="erp-panel">
      <div className="erp-header">
        <h4>🔗 ERP Integration</h4>
        <span className="status-badge-success">Connected</span>
      </div>
      <div className="erp-system">
        <div className="erp-system-name">SAP S/4HANA</div>
        <div className="erp-last-sync">Last sync: 2 minutes ago</div>
      </div>
      <div className="erp-data-sources">
        <div className="erp-data-item">
          <CheckCircle size={14} color="#10b981" />
          <span>Supplier Master: 15 suppliers</span>
        </div>
        <div className="erp-data-item">
          <CheckCircle size={14} color="#10b981" />
          <span>Pricing: Updated daily</span>
        </div>
        <div className="erp-data-item">
          <CheckCircle size={14} color="#10b981" />
          <span>Contracts: 12 active</span>
        </div>
        <div className="erp-data-item">
          <CheckCircle size={14} color="#10b981" />
          <span>Inventory: Real-time</span>
        </div>
      </div>
      <div className="erp-actions">
        <button className="erp-btn-secondary">
          <RefreshCw size={14} />
          Sync Now
        </button>
        <button className="erp-btn-secondary">
          <Settings size={14} />
          Configure
        </button>
      </div>
    </div>
  )
}
