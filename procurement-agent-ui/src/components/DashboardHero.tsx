import { TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { getMaterialsAtOrBelowReorderPoint, productionSchedule } from '../data/realData'

export default function DashboardHero() {
  const lowStockCount = getMaterialsAtOrBelowReorderPoint().length
  const urbanSchedule = productionSchedule.filter(ps => ps.productName.includes('Urban Commuter'))
  const totalQ2Production = urbanSchedule.reduce((sum, ps) => sum + ps.plannedQuantity, 0)

  return (
    <div style={{ marginBottom: '32px' }}>
      {/* Hero Section - The Problem */}
      <div style={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '12px',
        padding: '32px',
        color: 'white',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '14px', fontWeight: '600', opacity: 0.9, marginBottom: '8px' }}>
          PROCUREMENT CHALLENGE
        </div>
        <h2 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '16px', color: 'white' }}>
          Optimize Materials for 500 Urban E-Bikes
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(4, 1fr)', 
          gap: '24px',
          marginTop: '24px'
        }}>
          <div>
            <div style={{ fontSize: '13px', opacity: 0.9, marginBottom: '4px' }}>Cost Range</div>
            <div style={{ fontSize: '24px', fontWeight: '700' }}>$650K-$1.2M</div>
          </div>
          <div>
            <div style={{ fontSize: '13px', opacity: 0.9, marginBottom: '4px' }}>Materials</div>
            <div style={{ fontSize: '24px', fontWeight: '700' }}>16 items</div>
          </div>
          <div>
            <div style={{ fontSize: '13px', opacity: 0.9, marginBottom: '4px' }}>Suppliers</div>
            <div style={{ fontSize: '24px', fontWeight: '700' }}>15 qualified</div>
          </div>
          <div>
            <div style={{ fontSize: '13px', opacity: 0.9, marginBottom: '4px' }}>Lead Time</div>
            <div style={{ fontSize: '24px', fontWeight: '700' }}>42-45 days</div>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Solution + Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* AI Agent Solution */}
        <div className="viz-card" style={{ 
          borderLeft: '4px solid #8b5cf6',
          backgroundColor: '#faf5ff'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <CheckCircle size={24} color="#8b5cf6" />
            <h3 style={{ margin: 0 }}>🤖 AI Agent Solution</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ 
                width: '6px', 
                height: '6px', 
                borderRadius: '50%', 
                backgroundColor: '#8b5cf6',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Generates Pareto-optimal solutions</div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>3 solutions balancing cost, risk, and lead time</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ 
                width: '6px', 
                height: '6px', 
                borderRadius: '50%', 
                backgroundColor: '#8b5cf6',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Ensures policy compliance</div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>Max 40% supplier concentration, sustainability requirements</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ 
                width: '6px', 
                height: '6px', 
                borderRadius: '50%', 
                backgroundColor: '#8b5cf6',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Optimizes in under 30 seconds</div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>Real-time analysis of 15 suppliers × 16 materials</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ 
                width: '6px', 
                height: '6px', 
                borderRadius: '50%', 
                backgroundColor: '#8b5cf6',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Integrates with existing ERP</div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>Creates purchase requisitions for SAP/Oracle approval</div>
              </div>
            </div>
          </div>
        </div>

        {/* Current Alerts */}
        <div className="viz-card" style={{ 
          borderLeft: '4px solid #f59e0b',
          backgroundColor: '#fffbeb'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <AlertCircle size={24} color="#f59e0b" />
            <h3 style={{ margin: 0 }}>⚠️ Current Alerts</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Alert 1: Low Stock */}
            <div style={{ 
              padding: '14px', 
              backgroundColor: 'white',
              borderRadius: '8px',
              border: '1px solid #fde68a'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Materials Need Reordering</div>
                <span style={{ 
                  backgroundColor: '#fef3c7', 
                  color: '#92400e',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {lowStockCount} items
                </span>
              </div>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                Critical: Carbon Fiber Frame, Mid-Drive Motor, Hub Motor
              </div>
            </div>

            {/* Alert 2: Demand Trend */}
            <div style={{ 
              padding: '14px', 
              backgroundColor: 'white',
              borderRadius: '8px',
              border: '1px solid #fde68a'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Demand Trending Up</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <TrendingUp size={16} color="#f59e0b" />
                  <span style={{ fontWeight: '700', color: '#f59e0b' }}>+29%</span>
                </div>
              </div>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                March: 450 units → May: 580 units (3-month forecast)
              </div>
            </div>

            {/* Alert 3: Production Context */}
            <div style={{ 
              padding: '14px', 
              backgroundColor: 'white',
              borderRadius: '8px',
              border: '1px solid #fde68a'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <div style={{ fontWeight: '600', fontSize: '14px' }}>Q2 Production Plan</div>
                <span style={{ fontWeight: '700', color: '#1e293b' }}>{totalQ2Production} bikes</span>
              </div>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                Current optimization: 500 bikes (33% of Q2 total)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
