import { useState, useEffect, useRef } from 'react'
import { fetchMaterialForecast, type MaterialForecast } from '../services/forecastApi'
import ForecastChart from './ForecastChart'

const PRODUCTION_SCHEDULE = [
  { product: 'Urban Commuter E-Bike', q1: 520, q2: 500, q3: 580, q4: 450, status: 'Planned', priority: 'High' },
  { product: 'Mountain Trail E-Bike', q1: 430, q2: 400, q3: 480, q4: 350, status: 'Planned', priority: 'Medium' },
]

const INVENTORY = [
  // Shared materials (Urban 500 + Mountain 400 = 900 units needed)
  { id: 'MAT-BAT-001', name: 'Li-ion Battery Pack', cat: 'Battery', stock: 250, reorder: 200, safety: 150, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-BAT-002', name: 'Battery Mgmt System', cat: 'Battery', stock: 480, reorder: 300, safety: 200, status: 'Surplus', defaultQty: 900, product: 'Both' },
  { id: 'MAT-BAT-003', name: 'Charging Port', cat: 'Battery', stock: 720, reorder: 500, safety: 350, status: 'Surplus', defaultQty: 900, product: 'Both' },
  { id: 'MAT-MOT-003', name: 'Motor Controller', cat: 'Motor', stock: 380, reorder: 250, safety: 180, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-MOT-004', name: 'Torque Sensor', cat: 'Motor', stock: 520, reorder: 350, safety: 250, status: 'Surplus', defaultQty: 900, product: 'Both' },
  { id: 'MAT-FRM-003', name: 'Suspension Fork', cat: 'Frame', stock: 95, reorder: 80, safety: 50, status: 'Critical', defaultQty: 900, product: 'Both' },
  { id: 'MAT-FRM-004', name: 'Handlebar Assembly', cat: 'Frame', stock: 420, reorder: 300, safety: 200, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-ELC-001', name: 'LCD Display', cat: 'Electronics', stock: 290, reorder: 200, safety: 150, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-ELC-002', name: 'Wiring Harness', cat: 'Electronics', stock: 610, reorder: 400, safety: 300, status: 'Surplus', defaultQty: 900, product: 'Both' },
  { id: 'MAT-ELC-003', name: 'Speed Sensor', cat: 'Electronics', stock: 540, reorder: 350, safety: 250, status: 'Surplus', defaultQty: 900, product: 'Both' },
  { id: 'MAT-STD-001', name: 'Wheel Set', cat: 'Standard', stock: 150, reorder: 200, safety: 120, status: 'Below Reorder', defaultQty: 900, product: 'Both' },
  { id: 'MAT-STD-002', name: 'Hydraulic Brakes', cat: 'Standard', stock: 320, reorder: 250, safety: 180, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-STD-003', name: 'Gear System', cat: 'Standard', stock: 280, reorder: 200, safety: 150, status: 'OK', defaultQty: 900, product: 'Both' },
  { id: 'MAT-STD-004', name: 'Pedal Set', cat: 'Standard', stock: 450, reorder: 300, safety: 200, status: 'Surplus', defaultQty: 900, product: 'Both' },
  // Urban-only (500 units)
  { id: 'MAT-MOT-001', name: 'Mid-Drive Motor 750W', cat: 'Motor', stock: 180, reorder: 150, safety: 100, status: 'Low', defaultQty: 500, product: 'Urban' },
  { id: 'MAT-FRM-001', name: 'Aluminum Frame', cat: 'Frame', stock: 310, reorder: 250, safety: 180, status: 'OK', defaultQty: 500, product: 'Urban' },
  // Mountain-only (400 units)
  { id: 'MAT-MOT-002', name: 'Mid-Drive Motor 500W', cat: 'Motor', stock: 200, reorder: 150, safety: 100, status: 'OK', defaultQty: 400, product: 'Mountain' },
  { id: 'MAT-FRM-002', name: 'Carbon Fiber Frame', cat: 'Frame', stock: 120, reorder: 100, safety: 80, status: 'Low', defaultQty: 400, product: 'Mountain' },
]

const statusStyle: Record<string, { bg: string; text: string; dot: string }> = {
  'Surplus':        { bg: '#dcfce7', text: '#16a34a', dot: '#22c55e' },
  'OK':             { bg: '#dbeafe', text: '#2563eb', dot: '#3b82f6' },
  'Low':            { bg: '#fef3c7', text: '#d97706', dot: '#f59e0b' },
  'Critical':       { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444' },
  'Below Reorder':  { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444' },
  'In Stock':       { bg: '#dcfce7', text: '#16a34a', dot: '#22c55e' },
}

export type ConfidenceLevel = 'p90' | 'p50' | 'p10'

interface DemandContextProps {
  quantity?: number
  onOptimize?: (materials?: { material_id: string; quantity: number }[]) => void
  forecasts?: Record<string, MaterialForecast>
  setForecasts?: (f: Record<string, MaterialForecast>) => void
  useForecast?: boolean
  setUseForecast?: (v: boolean) => void
  confidenceLevel?: ConfidenceLevel
  setConfidenceLevel?: (v: ConfidenceLevel) => void
  externalLoading?: boolean
  setExternalLoading?: (v: boolean) => void
}

const CONFIDENCE_LABELS: Record<ConfidenceLevel, { label: string; desc: string }> = {
  p90: { label: 'P90', desc: 'Conservative' },
  p50: { label: 'P50', desc: 'Median' },
  p10: { label: 'P10', desc: 'Optimistic' },
}

export default function DemandContext({
  quantity = 500,
  onOptimize,
  forecasts: externalForecasts,
  setForecasts: externalSetForecasts,
  useForecast: externalUseForecast,
  setUseForecast: externalSetUseForecast,
  confidenceLevel: externalConfidenceLevel,
  setConfidenceLevel: externalSetConfidenceLevel,
  externalLoading,
  setExternalLoading,
}: DemandContextProps) {
  // Use external state if provided (lifted to App), otherwise local
  const [localForecasts, localSetForecasts] = useState<Record<string, MaterialForecast>>({})
  const [localUseForecast, localSetUseForecast] = useState(false)
  const [localConfidenceLevel, localSetConfidenceLevel] = useState<ConfidenceLevel>('p90')

  const forecasts = externalForecasts ?? localForecasts
  const setForecasts = externalSetForecasts ?? localSetForecasts
  const useForecast = externalUseForecast ?? localUseForecast
  const setUseForecast = externalSetUseForecast ?? localSetUseForecast
  const confidenceLevel = externalConfidenceLevel ?? localConfidenceLevel
  const setConfidenceLevel = externalSetConfidenceLevel ?? localSetConfidenceLevel

  const [localLoading, setLocalLoading] = useState(false)
  const forecastLoading = externalLoading || localLoading
  const setForecastLoading = (v: boolean) => { setLocalLoading(v); setExternalLoading?.(v) }
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [forecastElapsed, setForecastElapsed] = useState(0)
  const [showAll, setShowAll] = useState(true)
  const startTimeRef = useRef(0)

  // Elapsed timer during forecasting
  useEffect(() => {
    if (!forecastLoading) return
    startTimeRef.current = Date.now()
    const iv = setInterval(() => setForecastElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000)), 1000)
    return () => clearInterval(iv)
  }, [forecastLoading])

  const handleFetchForecasts = async () => {
    setForecastLoading(true)
    setForecastError(null)
    setForecastElapsed(0)
    try {
      const ids = INVENTORY.map(i => i.id)
      const BATCH = 3
      for (let i = 0; i < ids.length; i += BATCH) {
        const batch = ids.slice(i, i + BATCH)
        const results = await Promise.all(batch.map(id => fetchMaterialForecast(id, 60)))
        // Update state incrementally so progress bar updates
        setForecasts(prev => {
          const next = { ...prev }
          for (const r of results) next[r.material_id] = r
          return next
        })
      }
      setUseForecast(true)
    } catch (e: any) {
      setForecastError(e.message || 'Forecast fetch failed')
    } finally {
      setForecastLoading(false)
    }
  }

  const needToProcure = INVENTORY.map(item => {
    const fc = forecasts[item.id]
    const forecastValue = fc && !fc.error
      ? confidenceLevel === 'p90' ? fc.summary.total_p90
        : confidenceLevel === 'p50' ? fc.summary.total_p50
        : fc.summary.total_p10
      : 0
    // AI forecast replaces BOM — the whole point is data-driven procurement
    const needed = useForecast && forecastValue > 0 ? Math.ceil(forecastValue) : item.defaultQty
    const gap = Math.max(0, needed - item.stock)
    const p10 = fc?.summary.total_p10
    const p50 = fc?.summary.total_p50
    const p90 = fc?.summary.total_p90
    return { ...item, needed, gap, hasSurplus: item.stock >= needed, p10, p50, p90, forecastValue: forecastValue > 0 ? Math.ceil(forecastValue) : undefined }
  })

  const totalGap = needToProcure.reduce((sum, i) => sum + i.gap, 0)
  const criticalItems = needToProcure.filter(i => i.gap > 0).length
  const surplusItems = needToProcure.filter(i => i.gap === 0).length

  const handleOptimize = () => {
    if (!onOptimize) return
    if (useForecast) {
      // Only send materials with a procurement gap (need > stock)
      const materials = needToProcure
        .filter(i => i.gap > 0)
        .map(i => ({ material_id: i.id, quantity: i.needed }))
      onOptimize(materials)
    } else {
      onOptimize()
    }
  }

  // Exception items sorted by gap descending (worst first)
  const exceptions = needToProcure.filter(i => i.gap > 0).sort((a, b) => b.gap - a.gap)
  // Full list sorted by severity for "show all" table
  const severityOrder: Record<string, number> = { 'Critical': 0, 'Below Reorder': 1, 'Low': 2, 'OK': 3, 'Surplus': 4 }
  const sortedAll = [...needToProcure].sort((a, b) => {
    const aS = a.hasSurplus ? 'Surplus' : a.status
    const bS = b.hasSurplus ? 'Surplus' : b.status
    return (severityOrder[aS] ?? 5) - (severityOrder[bS] ?? 5)
  })

  // Status counts for health strip
  const statusCounts = {
    stocked: surplusItems,
    short: needToProcure.filter(i => !i.hasSurplus && (i.status === 'OK' || i.status === 'Surplus')).length,
    low: needToProcure.filter(i => !i.hasSurplus && i.status === 'Low').length,
    critical: needToProcure.filter(i => !i.hasSurplus && (i.status === 'Critical' || i.status === 'Below Reorder')).length,
  }

  const categories = [...new Set(INVENTORY.map(i => i.cat))]
  const q2Total = PRODUCTION_SCHEDULE.reduce((s, p) => s + p.q2, 0)

  return (
    <div>
      {/* ── Hero banner (info only, no buttons) ── */}
      <div style={{
        padding: '20px 24px', borderRadius: 'var(--radius-lg)', marginBottom: 16,
        background: 'linear-gradient(135deg, var(--color-nav-bg) 0%, #334155 100%)', color: '#fff',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.6, marginBottom: 4 }}>Q2 2026 Production Plan</div>
            <div style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>{q2Total} Units</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, opacity: 0.5, marginBottom: 4 }}>{INVENTORY.length} materials · {categories.length} categories</div>
            <div style={{ display: 'flex', gap: 14, fontSize: 13, opacity: 0.85 }}>
              {PRODUCTION_SCHEDULE.map(p => (
                <span key={p.product}>
                  {p.product}: <span style={{ fontWeight: 700 }}>{p.q2}</span>
                  <span style={{
                    marginLeft: 6, padding: '1px 6px', borderRadius: 8, fontSize: 10, fontWeight: 600,
                    background: p.priority === 'High' ? 'rgba(239,68,68,0.25)' : 'rgba(245,158,11,0.25)',
                  }}>{p.priority}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Forecast progress bar ── */}
      {forecastLoading && (
        <div style={{
          padding: '12px 16px', borderRadius: 'var(--radius-lg)', marginBottom: 12,
          border: '1px solid var(--color-primary)', background: 'rgba(59,130,246,0.04)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-primary)' }}>
              Forecasting materials with Chronos-2...
            </span>
            <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              <strong style={{ color: 'var(--color-primary)' }}>{Object.keys(forecasts).length}/{INVENTORY.length}</strong>
              {forecastElapsed > 0 && <span style={{ marginLeft: 8 }}>{forecastElapsed}s</span>}
            </span>
          </div>
          <div style={{ height: 6, borderRadius: 3, background: 'var(--color-border)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 3, background: 'var(--color-primary)',
              width: `${(Object.keys(forecasts).length / INVENTORY.length) * 100}%`,
              transition: 'width 0.5s ease',
            }} />
          </div>
        </div>
      )}

      {/* ── Action bar: compact inline steps ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
        borderRadius: 'var(--radius-lg)', marginBottom: 16,
        border: '1px solid var(--color-border)', background: 'var(--color-surface)',
      }}>
        {/* Step 1 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 20, height: 20, borderRadius: '50%', fontSize: 10, fontWeight: 700,
            background: useForecast ? '#22c55e' : 'var(--color-primary)', color: '#fff', flexShrink: 0,
          }}>{useForecast ? '✓' : '1'}</span>
          {!useForecast ? (
            <button onClick={handleFetchForecasts} disabled={forecastLoading} style={{
              padding: '6px 14px', borderRadius: 'var(--radius-sm)', border: 'none',
              background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: 12,
              cursor: forecastLoading ? 'wait' : 'pointer', whiteSpace: 'nowrap',
            }}>
              {forecastLoading ? '⏳ Loading...' : '📊 Run Forecast'}
            </button>
          ) : (
            <span style={{ fontSize: 12, fontWeight: 600, color: '#22c55e', whiteSpace: 'nowrap' }}>Forecast Active</span>
          )}
        </div>

        {/* Confidence selector (appears after forecast) */}
        {useForecast && (
          <div style={{ display: 'flex', borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--color-border)' }}>
            {(['p90', 'p50', 'p10'] as ConfidenceLevel[]).map(level => (
              <button key={level} onClick={() => setConfidenceLevel(level)} style={{
                padding: '4px 10px', border: 'none', fontSize: 10, fontWeight: 600, cursor: 'pointer',
                background: confidenceLevel === level ? 'var(--color-primary)' : 'transparent',
                color: confidenceLevel === level ? '#fff' : 'var(--color-text-muted)',
                transition: 'all 0.15s', whiteSpace: 'nowrap',
              }}>
                {CONFIDENCE_LABELS[level].label} <span style={{ fontWeight: 400, opacity: 0.7 }}>{CONFIDENCE_LABELS[level].desc}</span>
              </button>
            ))}
          </div>
        )}

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: 'var(--color-border)', flexShrink: 0 }} />

        {/* Step 2 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 20, height: 20, borderRadius: '50%', fontSize: 10, fontWeight: 700,
            background: useForecast ? 'var(--color-primary)' : 'var(--color-text-muted)', color: '#fff', flexShrink: 0,
            opacity: useForecast ? 1 : 0.5,
          }}>2</span>
          {onOptimize && (
            <button onClick={handleOptimize} style={{
              padding: '6px 14px', borderRadius: 'var(--radius-sm)', border: 'none',
              background: useForecast ? '#3b82f6' : 'var(--color-text-muted)',
              color: '#fff', fontWeight: 600, fontSize: 12, cursor: 'pointer',
              opacity: useForecast ? 1 : 0.5, transition: 'all 0.2s', whiteSpace: 'nowrap',
            }}>
              Optimize →
            </button>
          )}
        </div>

        {/* Source info (right-aligned) */}
        <div style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--color-text-muted)', textAlign: 'right', whiteSpace: 'nowrap' }}>
          {useForecast
            ? `Chronos-2 ${CONFIDENCE_LABELS[confidenceLevel].label} · AI-driven procurement · ${criticalItems} gaps`
            : 'BOM × production schedule (500 Urban + 400 Mountain)'}
        </div>

        {forecastError && (
          <div style={{ fontSize: 10, color: 'var(--color-danger)', whiteSpace: 'nowrap' }}>⚠️ {forecastError}</div>
        )}
      </div>

      {/* ── KPI cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Materials Tracked', value: `${INVENTORY.length}`, sub: `${categories.length} categories`, color: 'var(--color-primary)' },
          { label: 'Need Procurement', value: `${criticalItems}`, sub: criticalItems > 3 ? 'Action required' : 'Manageable', color: criticalItems > 3 ? 'var(--color-danger)' : 'var(--color-warning)' },
          { label: 'Total Gap', value: totalGap.toLocaleString(), sub: 'units short', color: 'var(--color-danger)' },
          { label: 'Fully Stocked', value: `${surplusItems}`, sub: `${Math.round(surplusItems / INVENTORY.length * 100)}% coverage`, color: 'var(--color-success)' },
        ].map(kpi => (
          <div key={kpi.label} style={{
            padding: '14px 16px', borderRadius: 'var(--radius-lg)', background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
          }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</div>
            <div style={{ fontSize: 26, fontWeight: 800, color: kpi.color, marginTop: 4, lineHeight: 1 }}>{kpi.value}</div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 6 }}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Single Inventory Status section ── */}
      <div style={{
        border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)',
        background: 'var(--color-surface)', marginBottom: 20, overflow: 'hidden',
      }}>
        {/* Header with health strip */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text)' }}>Inventory Status</div>
            <button onClick={() => setShowAll(!showAll)} style={{
              padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: 11, fontWeight: 600, cursor: 'pointer',
              border: '1px solid var(--color-border)', background: showAll ? 'var(--color-primary-light)' : 'var(--color-surface)',
              color: showAll ? 'var(--color-primary)' : 'var(--color-text-muted)',
            }}>
              {showAll ? `Showing all ${INVENTORY.length}` : `Exceptions only (${exceptions.length})`}
            </button>
          </div>
          {/* Health strip */}
          <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: 'var(--color-border)' }}>
            {statusCounts.stocked > 0 && <div style={{ width: `${(statusCounts.stocked / INVENTORY.length) * 100}%`, background: '#22c55e' }} />}
            {statusCounts.short > 0 && <div style={{ width: `${(statusCounts.short / INVENTORY.length) * 100}%`, background: '#3b82f6' }} />}
            {statusCounts.low > 0 && <div style={{ width: `${(statusCounts.low / INVENTORY.length) * 100}%`, background: '#f59e0b' }} />}
            {statusCounts.critical > 0 && <div style={{ width: `${(statusCounts.critical / INVENTORY.length) * 100}%`, background: '#ef4444' }} />}
          </div>
          <div style={{ display: 'flex', gap: 14, marginTop: 6, fontSize: 11 }}>
            {[
              { label: 'Stocked', color: '#22c55e', count: statusCounts.stocked },
              { label: 'Short', color: '#3b82f6', count: statusCounts.short },
              { label: 'Low', color: '#f59e0b', count: statusCounts.low },
              { label: 'Critical', color: '#ef4444', count: statusCounts.critical },
            ].filter(l => l.count > 0).map(l => (
              <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: l.color, flexShrink: 0 }} />
                {l.label} ({l.count})
              </div>
            ))}
          </div>
        </div>

        {/* Exception list (default) or full table (show all) */}
        {!showAll ? (
          <div style={{ padding: exceptions.length > 0 ? '2px 0' : '24px 18px' }}>
            {exceptions.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--color-success)' }}>
                <div style={{ fontSize: 20, marginBottom: 4 }}>✅</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>All materials fully stocked</div>
              </div>
            )}
            {exceptions.map(item => {
              const pct = Math.round((item.stock / item.needed) * 100)
              const isCritical = item.status === 'Critical' || item.status === 'Below Reorder'
              const isLow = item.status === 'Low'
              const barColor = isCritical ? '#ef4444' : isLow ? '#f59e0b' : pct < 50 ? '#f59e0b' : '#3b82f6'
              const dotColor = isCritical ? '#ef4444' : isLow ? '#f59e0b' : '#3b82f6'
              return (
                <div key={item.id} style={{
                  display: 'grid', gridTemplateColumns: '6px 2fr 1fr 80px',
                  alignItems: 'center', gap: 12, padding: '9px 18px 9px 12px',
                  borderBottom: '1px solid var(--color-border-light)',
                }}>
                  {/* Severity dot */}
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor }} />
                  {/* Name + category */}
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)' }}>{item.name}</span>
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginLeft: 8 }}>{item.cat}</span>
                  </div>
                  {/* Fill bar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--color-border)' }}>
                      <div style={{ height: '100%', borderRadius: 2, width: `${pct}%`, background: barColor, transition: 'width 0.3s' }} />
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', width: 28, textAlign: 'right' }}>{pct}%</span>
                  </div>
                  {/* Gap */}
                  <div style={{ textAlign: 'right', fontSize: 12, fontWeight: 700, color: isCritical ? '#dc2626' : isLow ? '#d97706' : 'var(--color-text-secondary)' }}>
                    −{item.gap}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          /* Full table — simplified pre-forecast, expanded post-forecast */
          <div>
            <div style={{
              display: 'grid', gridTemplateColumns: useForecast ? '2fr 0.7fr 0.7fr 0.7fr 0.7fr 1fr' : '2fr 0.7fr 0.7fr 0.8fr 1fr',
              padding: '8px 18px', background: 'var(--color-bg)', fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)',
              textTransform: 'uppercase', letterSpacing: '0.04em',
            }}>
              <div>Material</div><div>Stock</div>
              {!useForecast && <div title="BOM × Production Schedule (500 Urban + 400 Mountain)">Q2 Need (BOM)</div>}
              {useForecast && <div title="BOM × Production Schedule">BOM Plan</div>}
              {useForecast && <div title="Chronos-2 AI forecast (60-day demand)">AI Forecast ({CONFIDENCE_LABELS[confidenceLevel].label})</div>}
              {useForecast && <div>Gap</div>}
              <div>Status</div>
            </div>
            {sortedAll.map(item => {
              const displayStatus = item.hasSurplus ? 'In Stock' : item.status
              const sc = statusStyle[displayStatus] || statusStyle['OK']
              return (
                <div key={item.id} style={{
                  display: 'grid', gridTemplateColumns: useForecast ? '2fr 0.7fr 0.7fr 0.7fr 0.7fr 1fr' : '2fr 0.7fr 0.7fr 0.8fr 1fr',
                  padding: '8px 18px', fontSize: 12, borderTop: '1px solid var(--color-border-light)',
                  transition: 'background 0.1s ease',
                }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--color-bg)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
                >
                  <div style={{ fontWeight: 500, color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    {forecastLoading && (
                      forecasts[item.id] && !forecasts[item.id].error
                        ? <span style={{ width: 14, height: 14, borderRadius: '50%', background: '#dcfce7', color: '#22c55e', fontSize: 8, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✓</span>
                        : forecasts[item.id]?.error
                          ? <span style={{ width: 14, height: 14, borderRadius: '50%', background: '#fee2e2', color: '#ef4444', fontSize: 8, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✗</span>
                          : <span style={{ width: 12, height: 12, borderRadius: '50%', border: '2px solid #e2e8f0', borderTopColor: '#3b82f6', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
                    )}
                    {item.name}
                    <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{item.cat}</span>
                  </div>
                  <div style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>{item.stock}</div>
                  {!useForecast && <div style={{ color: 'var(--color-text-secondary)', fontWeight: 500, fontSize: 11 }}>
                    {item.defaultQty}
                    <span style={{ fontSize: 9, marginLeft: 4, color: 'var(--color-text-muted)' }}>
                      {(item as any).product === 'Urban' ? 'Urban' : (item as any).product === 'Mountain' ? 'Mtn' : 'Both'}
                    </span>
                  </div>}
                  {useForecast && <div style={{ color: 'var(--color-text-muted)', fontSize: 11 }}>
                    {item.defaultQty}
                    <span style={{ fontSize: 9, marginLeft: 4, opacity: 0.6 }}>
                      {(item as any).product === 'Urban' ? 'Urban' : (item as any).product === 'Mountain' ? 'Mtn' : ''}
                    </span>
                  </div>}
                  {useForecast && <div style={{ color: '#6366f1', fontWeight: 700 }}>{item.forecastValue ?? '—'}</div>}
                  {useForecast && (
                    <div style={{ fontWeight: item.gap > 0 ? 700 : 400, color: item.gap > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                      {item.gap > 0 ? `-${item.gap}` : 'OK'}
                    </div>
                  )}
                  <div>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600, background: sc.bg, color: sc.text }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: sc.dot }} />
                      {displayStatus}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Forecast time series chart ── */}
      {useForecast && Object.keys(forecasts).length > 0 && (
        <ForecastChart
          forecasts={forecasts}
          materials={INVENTORY.map(i => ({ id: i.id, name: i.name }))}
        />
      )}

      {/* ── Production schedule (collapsible) ── */}
      <details style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', background: 'var(--color-surface)' }}>
        <summary style={{ padding: '12px 18px', fontSize: 13, fontWeight: 600, color: 'var(--color-text)', cursor: 'pointer', userSelect: 'none' }}>
          Production Schedule
          <span style={{ fontWeight: 400, color: 'var(--color-text-muted)', marginLeft: 6, fontSize: 12 }}>
            ({q2Total} units Q2)
          </span>
        </summary>
        <div style={{ padding: '0 18px 14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr repeat(4, 0.7fr) 0.7fr', gap: 0 }}>
            {['Product', 'Q1', 'Q2', 'Q3', 'Q4', 'Priority'].map(h => (
              <div key={h} style={{ padding: '8px 0', fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--color-border)' }}>{h}</div>
            ))}
            {PRODUCTION_SCHEDULE.map(p => (
              [p.product, p.q1, p.q2, p.q3, p.q4, p.priority].map((val, ci) => (
                <div key={`${p.product}-${ci}`} style={{
                  padding: '10px 0', fontSize: 13, borderBottom: '1px solid var(--color-border-light)',
                  fontWeight: ci === 0 ? 500 : ci === 2 ? 700 : 400,
                  color: ci === 2 ? 'var(--color-primary)' : ci === 0 ? 'var(--color-text)' : 'var(--color-text-secondary)',
                }}>
                  {ci === 5 ? (
                    <span style={{
                      padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600,
                      background: val === 'High' ? 'var(--color-danger-light)' : 'var(--color-warning-light)',
                      color: val === 'High' ? 'var(--color-danger)' : 'var(--color-warning)',
                    }}>{val}</span>
                  ) : val}
                </div>
              ))
            ))}
          </div>
        </div>
      </details>
    </div>
  )
}
