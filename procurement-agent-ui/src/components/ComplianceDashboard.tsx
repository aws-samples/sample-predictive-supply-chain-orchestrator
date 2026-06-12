import { CheckCircle, AlertTriangle } from 'lucide-react'
import { supplierContracts, paretoSolutions } from '../data/realData'

interface ComplianceDashboardProps {
  selectedSolution: string | null
}

export default function ComplianceDashboard({ selectedSolution }: ComplianceDashboardProps) {
  const solution = paretoSolutions.find(s => s.id === selectedSolution) || paretoSolutions[1]
  
  // Get unique suppliers in this solution
  const solutionSupplierIds = new Set(solution.allocations.map(a => a.supplierId))
  const solutionContracts = supplierContracts.filter(c => solutionSupplierIds.has(c.supplierId))
  
  // Count contracts with sustainability clauses
  const sustainabilityContracts = solutionContracts.filter(c => 
    c.sustainabilityClause && c.sustainabilityClause !== 'None'
  )

  const compliance = {
    supplierConcentration: { 
      value: solution.supplierConcentration[0].percentage, 
      limit: 40, 
      status: 'pass' 
    },
    approvedSuppliers: { 
      value: solutionSupplierIds.size, 
      total: solutionSupplierIds.size, 
      status: 'pass' 
    },
    minSuppliersPerCategory: { 
      status: 'pass', 
      details: 'Battery: 2, Motor: 1, Frame: 2' 
    },
    leadTime: { 
      value: solution.maxLeadTimeDays, 
      target: 30, 
      status: solution.maxLeadTimeDays > 30 ? 'warning' : 'pass'
    },
    sustainability: {
      value: sustainabilityContracts.length,
      total: solutionContracts.length,
      percentage: Math.round((sustainabilityContracts.length / solutionContracts.length) * 100)
    }
  }

  return (
    <div className="compliance-panel">
      <div className="compliance-header">
        <h4>✓ Policy Compliance</h4>
      </div>
      <div className="compliance-items">
        <div className="compliance-item compliance-pass">
          <CheckCircle size={16} color="#10b981" />
          <div className="compliance-text">
            <div className="compliance-label">Max supplier concentration: {compliance.supplierConcentration.value}%</div>
            <div className="compliance-sublabel">Policy: &lt;{compliance.supplierConcentration.limit}%</div>
          </div>
        </div>

        <div className="compliance-item compliance-pass">
          <CheckCircle size={16} color="#10b981" />
          <div className="compliance-text">
            <div className="compliance-label">Approved suppliers only</div>
            <div className="compliance-sublabel">All {compliance.approvedSuppliers.value} suppliers pre-approved</div>
          </div>
        </div>

        <div className="compliance-item compliance-pass">
          <CheckCircle size={16} color="#10b981" />
          <div className="compliance-text">
            <div className="compliance-label">Minimum 2 suppliers per category</div>
            <div className="compliance-sublabel">{compliance.minSuppliersPerCategory.details}</div>
          </div>
        </div>

        <div className="compliance-item compliance-pass">
          <CheckCircle size={16} color="#10b981" />
          <div className="compliance-text">
            <div className="compliance-label">Sustainability clauses: {compliance.sustainability.percentage}%</div>
            <div className="compliance-sublabel">{compliance.sustainability.value} of {compliance.sustainability.total} contracts include sustainability requirements</div>
          </div>
        </div>

        <div className={`compliance-item ${compliance.leadTime.status === 'pass' ? 'compliance-pass' : 'compliance-warning'}`}>
          {compliance.leadTime.status === 'pass' ? (
            <CheckCircle size={16} color="#10b981" />
          ) : (
            <AlertTriangle size={16} color="#f59e0b" />
          )}
          <div className="compliance-text">
            <div className="compliance-label">
              {compliance.leadTime.status === 'pass' ? 'Lead time within target' : 'Lead time exceeds target'}
            </div>
            <div className="compliance-sublabel">{compliance.leadTime.value} days (Target: {compliance.leadTime.target} days)</div>
          </div>
        </div>
      </div>
      
      {/* Contract Details */}
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
        <h5 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px' }}>
          Active Contracts ({solutionContracts.length})
        </h5>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
          {solutionContracts.map(contract => (
            <div key={contract.contractId} style={{ 
              padding: '10px', 
              backgroundColor: '#f8fafc',
              borderRadius: '6px',
              fontSize: '12px'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                {contract.contractType}
              </div>
              <div style={{ color: '#64748b', fontSize: '11px' }}>
                {contract.sustainabilityClause !== 'None' && (
                  <div>🌱 {contract.sustainabilityClause}</div>
                )}
                <div>💰 {contract.paymentTerms} | {contract.priceAdjustmentClause}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

