import { productionSchedule } from '../data/realData'

export default function ProductionContextPanel() {
  // Filter for Urban Commuter E-Bike
  const urbanSchedule = productionSchedule.filter(ps => 
    ps.productName.includes('Urban Commuter')
  )

  const totalPlanned = urbanSchedule.reduce((sum, ps) => sum + ps.plannedQuantity, 0)

  return (
    <div className="viz-card" style={{ marginBottom: '24px' }}>
      <h3>🏭 Production Schedule Context</h3>
      <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '16px' }}>
        Why we're optimizing for 500 Urban E-Bikes
      </p>
      
      <div style={{ 
        padding: '16px', 
        backgroundColor: '#eff6ff', 
        borderRadius: '8px',
        borderLeft: '4px solid #3b82f6',
        marginBottom: '16px'
      }}>
        <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
          Q2 2026 Production Plan
        </div>
        <div style={{ fontSize: '24px', fontWeight: '700', color: '#1e293b', marginBottom: '4px' }}>
          {totalPlanned} bikes
        </div>
        <div style={{ fontSize: '12px', color: '#64748b' }}>
          Total Urban Commuter E-Bikes planned across {urbanSchedule.length} batches
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {urbanSchedule.map(schedule => (
          <div key={schedule.scheduleId} style={{ 
            padding: '12px', 
            backgroundColor: '#f8fafc',
            borderRadius: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
                {schedule.notes}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                {schedule.startDate} to {schedule.endDate}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '18px', fontWeight: '700', color: '#1e293b' }}>
                {schedule.plannedQuantity}
              </div>
              <div style={{ 
                fontSize: '10px',
                fontWeight: '600',
                color: schedule.priority === 'High' ? '#ef4444' : '#f59e0b',
                textTransform: 'uppercase'
              }}>
                {schedule.priority}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
