import { useState } from 'react'
import { optimizeWithWeights } from '../services/api'
import type { SupplierMix } from '../services/api'

interface WeightSlidersProps {
  onCustomSolution?: (solution: SupplierMix) => void
  materials?: { material_id: string; quantity: number }[]
}

export default function WeightSliders({ onCustomSolution, materials }: WeightSlidersProps) {
  const [cost, setCost] = useState(40)
  const [risk, setRisk] = useState(35)
  const [leadTime, setLeadTime] = useState(25)
  const [loading, setLoading] = useState(false)
  const [lastRun, setLastRun] = useState<string | null>(null)

  const total = cost + risk + leadTime
  const normalized = {
    cost: total > 0 ? cost / total : 0.33,
    risk: total > 0 ? risk / total : 0.33,
    lead_time: total > 0 ? leadTime / total : 0.34,
  }

  const runCustom = async () => {
    setLoading(true)
    try {
      const resp = await optimizeWithWeights(normalized, materials)
      const sol = resp.solution
      setLastRun(`$${Math.round(sol.total_cost / 1000)}K | Risk ${sol.risk_score.toFixed(1)} | ${resp.computation_time_ms}ms`)
      onCustomSolution?.(sol)
    } catch {
      setLastRun('Failed')
    }
    setLoading(false)
  }

  const presets = [
    { label: 'Cost Focus', c: 80, r: 10, l: 10 },
    { label: 'Balanced', c: 35, r: 35, l: 30 },
    { label: 'Risk Averse', c: 10, r: 70, l: 20 },
    { label: 'Fast Delivery', c: 15, r: 15, l: 70 },
  ]

  return (
    <div style={{ padding: '12px 14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>Custom Weights</h4>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {lastRun && <span style={{ fontSize: '11px', color: '#10b981' }}>{lastRun}</span>}
          <button onClick={runCustom} disabled={loading} style={{
            padding: '5px 14px', borderRadius: '6px', border: 'none',
            background: loading ? '#94a3b8' : '#3b82f6', color: '#fff',
            fontWeight: 600, fontSize: '12px', cursor: loading ? 'default' : 'pointer',
          }}>
            {loading ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
        {presets.map(p => (
          <button key={p.label} onClick={() => { setCost(p.c); setRisk(p.r); setLeadTime(p.l) }} style={{
            flex: 1, padding: '3px', borderRadius: '4px', fontSize: '10px', cursor: 'pointer',
            border: '1px solid #e2e8f0', background: '#fff', color: '#475569', fontWeight: 500,
          }}>{p.label}</button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        {[
          { label: 'Cost', value: cost, set: setCost, color: '#10b981', pct: normalized.cost },
          { label: 'Risk', value: risk, set: setRisk, color: '#8b5cf6', pct: normalized.risk },
          { label: 'Lead Time', value: leadTime, set: setLeadTime, color: '#f59e0b', pct: normalized.lead_time },
        ].map(s => (
          <div key={s.label} style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '2px' }}>
              <span style={{ fontWeight: 500 }}>{s.label}</span>
              <span style={{ fontWeight: 700, color: s.color }}>{Math.round(s.pct * 100)}%</span>
            </div>
            <input type="range" min={0} max={100} value={s.value}
              onChange={e => s.set(Number(e.target.value))}
              style={{ width: '100%', accentColor: s.color, height: '4px' }} />
          </div>
        ))}
      </div>
    </div>
  )
}
