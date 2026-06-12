import { getMaterialsAtOrBelowReorderPoint } from '../data/realData'

export default function InventoryStatusPanel() {
  const lowStockMaterials = getMaterialsAtOrBelowReorderPoint()

  return (
    <div className="viz-card" style={{ marginBottom: '24px' }}>
      <h3>📦 Inventory Status</h3>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>
          Materials at or below reorder point
        </p>
        <span style={{ 
          backgroundColor: '#fef3c7', 
          color: '#92400e',
          padding: '4px 12px',
          borderRadius: '12px',
          fontSize: '13px',
          fontWeight: '600'
        }}>
          {lowStockMaterials.length} items need attention
        </span>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
        {lowStockMaterials.map(({ material, inventory }) => {
          const stockPercentage = (inventory.currentStock / inventory.reorderPoint) * 100
          const isCritical = inventory.currentStock <= inventory.safetyStock
          
          return (
            <div key={material.id} style={{ 
              padding: '14px', 
              backgroundColor: isCritical ? '#fef2f2' : '#fffbeb',
              borderRadius: '8px',
              borderLeft: `4px solid ${isCritical ? '#ef4444' : '#f59e0b'}`
            }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '8px'
              }}>
                <div style={{ fontWeight: '600', fontSize: '13px', flex: 1 }}>
                  {material.name.split(' ').slice(0, 3).join(' ')}
                </div>
                <span style={{ 
                  fontSize: '11px',
                  fontWeight: '600',
                  color: isCritical ? '#dc2626' : '#d97706'
                }}>
                  {isCritical ? '🔴 CRITICAL' : '⚠️ LOW'}
                </span>
              </div>
              
              <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '6px' }}>
                <div>Current: <strong>{inventory.currentStock}</strong> units</div>
                <div>Reorder at: {inventory.reorderPoint} units</div>
                <div>Safety stock: {inventory.safetyStock} units</div>
              </div>
              
              {/* Progress bar */}
              <div style={{ 
                width: '100%', 
                height: '6px', 
                backgroundColor: '#e5e7eb',
                borderRadius: '3px',
                overflow: 'hidden'
              }}>
                <div style={{ 
                  width: `${Math.min(stockPercentage, 100)}%`,
                  height: '100%',
                  backgroundColor: isCritical ? '#ef4444' : '#f59e0b',
                  transition: 'width 0.3s'
                }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
