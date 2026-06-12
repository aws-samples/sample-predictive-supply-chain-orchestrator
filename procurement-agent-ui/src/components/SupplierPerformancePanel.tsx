import { useState, useEffect } from 'react'
import { fetchSupplierPerformance, fetchSuppliers, type BackendPerformance, type BackendSupplier } from '../services/api'

export default function SupplierPerformancePanel() {
  const [livePerformance, setLivePerformance] = useState<BackendPerformance[]>([])
  const [liveSuppliers, setLiveSuppliers] = useState<BackendSupplier[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchSupplierPerformance(), fetchSuppliers()])
      .then(([perf, sups]) => {
        setLivePerformance(perf)
        setLiveSuppliers(sups)
      })
      .finally(() => setLoading(false))
  }, [])

  const getSupplierName = (supplierId: string): string => {
    const s = liveSuppliers.find(s => s.supplier_id === supplierId)
    if (s) return s.name.split(' ')[0]
    return supplierId
  }

  // Build latest performance per supplier
  type PerfRecord = { supplierId: string; onTimeDeliveryRate: number; qualityScore: number; defectRate: number; responseTimeHours: number; performanceId: string }

  const latestMap = new Map<string, BackendPerformance>()
  for (const perf of livePerformance) {
    const existing = latestMap.get(perf.supplier_id)
    if (!existing || perf.measurement_period > existing.measurement_period) {
      latestMap.set(perf.supplier_id, perf)
    }
  }
  const sortedSuppliers: PerfRecord[] = Array.from(latestMap.values())
    .sort((a, b) => b.on_time_delivery_rate - a.on_time_delivery_rate)
    .map(p => ({
      supplierId: p.supplier_id,
      onTimeDeliveryRate: p.on_time_delivery_rate,
      qualityScore: p.quality_score,
      defectRate: p.defect_rate,
      responseTimeHours: p.response_time_hours,
      performanceId: p.performance_id,
    }))

  if (loading) {
    return (
      <div className="viz-card" style={{ marginBottom: '24px' }}>
        <h3>Supplier Performance (Latest Period)</h3>
        <p style={{ color: '#64748b', fontSize: '14px' }}>Loading performance data from Neptune...</p>
      </div>
    )
  }

  if (sortedSuppliers.length === 0) {
    return (
      <div className="viz-card" style={{ marginBottom: '24px' }}>
        <h3>Supplier Performance (Latest Period)</h3>
        <p style={{ color: '#64748b', fontSize: '14px' }}>No performance data available. Check backend connection.</p>
      </div>
    )
  }

  return (
    <div className="viz-card" style={{ marginBottom: '24px' }}>
      <h3>Supplier Performance (Latest Period) - Live</h3>
      <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '16px' }}>
        Performance metrics for {sortedSuppliers.length} suppliers from Neptune
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', maxHeight: '600px', overflowY: 'auto' }}>
        {sortedSuppliers.map(perf => {
          const isTopPerformer = perf.onTimeDeliveryRate >= 97 && perf.qualityScore >= 9

          return (
            <div key={perf.performanceId} style={{
              padding: '14px',
              backgroundColor: isTopPerformer ? '#f0fdf4' : '#f8fafc',
              borderRadius: '8px',
              borderLeft: `4px solid ${isTopPerformer ? '#10b981' : '#64748b'}`
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px'
              }}>
                <div style={{ fontWeight: '600', fontSize: '13px' }}>
                  {getSupplierName(perf.supplierId)}
                </div>
                {isTopPerformer && (
                  <span style={{ fontSize: '11px', color: '#10b981' }}>Top</span>
                )}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                fontSize: '12px'
              }}>
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px' }}>On-Time</div>
                  <div style={{ fontWeight: '600', color: '#1e293b' }}>
                    {perf.onTimeDeliveryRate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px' }}>Quality</div>
                  <div style={{ fontWeight: '600', color: '#1e293b' }}>
                    {perf.qualityScore.toFixed(1)}/10
                  </div>
                </div>
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px' }}>Defect Rate</div>
                  <div style={{
                    fontWeight: '600',
                    color: perf.defectRate < 1 ? '#10b981' : perf.defectRate < 2 ? '#f59e0b' : '#ef4444'
                  }}>
                    {perf.defectRate.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px' }}>Response</div>
                  <div style={{ fontWeight: '600', color: '#1e293b' }}>
                    {perf.responseTimeHours}h
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
