import { useState } from 'react'
import { AlertTriangle, Shield, TrendingUp, Clock, DollarSign, Package, CheckCircle, Loader2 } from 'lucide-react'
import { API_BASE_URL, authHeaders } from '../services/api'

const MATERIAL_NAMES: Record<string, string> = {
  'MAT-BAT-001': 'Battery Pack 48V', 'MAT-BAT-002': 'Battery Mgmt System', 'MAT-BAT-003': 'Charging Port',
  'MAT-MOT-001': 'Mid-Drive Motor 750W', 'MAT-MOT-002': 'Mid-Drive Motor 500W', 'MAT-MOT-003': 'Motor Controller', 'MAT-MOT-004': 'Torque Sensor',
  'MAT-FRM-001': 'Aluminum Frame', 'MAT-FRM-002': 'Carbon Fiber Frame', 'MAT-FRM-003': 'Suspension Fork', 'MAT-FRM-004': 'Handlebar Assembly',
  'MAT-ELC-001': 'LCD Display', 'MAT-ELC-002': 'Wiring Harness', 'MAT-ELC-003': 'Speed Sensor',
  'MAT-STD-001': 'Wheel Set', 'MAT-STD-002': 'Hydraulic Brakes', 'MAT-STD-003': 'Gear System', 'MAT-STD-004': 'Pedal Set',
}

// ── Types ──────────────────────────────────────────────

interface Scenario {
  id: string
  name: string
  description: string
  status: 'ACTIVE' | 'Ongoing' | 'Monitoring'
  statusColor: string
  statusBg: string
  probability: string
}

interface AffectedSupplier {
  supplier_id: string
  name: string
  location: string
  materials_at_risk: string[]
  materials_count: number
  freight_increase_pct: number
  tariff_increase_pct: number
  lead_time_increase_days: number
  estimated_cost_impact_pct: number
}

interface UnaffectedSupplier {
  supplier_id: string
  name: string
  location: string
  materials_supplied: string[]
  status: string
}

interface SimulationResult {
  scenario: {
    id: string
    name: string
    description: string
    probability: string
    current_status: string
    freight_increase_pct: number
    lead_time_increase_days: number
    tariff_increase_pct: number
  }
  affected_suppliers: AffectedSupplier[]
  unaffected_suppliers: UnaffectedSupplier[]
  summary: {
    affected_supplier_count: number
    unaffected_supplier_count: number
    total_materials_at_risk: number
    avg_cost_impact_pct: number
    max_lead_time_increase_days: number
  }
  recommended_actions: string[]
}

// ── Predefined scenarios ───────────────────────────────

const SCENARIOS: Scenario[] = [
  {
    id: 'strait_of_hormuz',
    name: 'Strait of Hormuz Blockade',
    description: 'Major shipping chokepoint disruption affecting Middle East oil and cargo routes. Impacts freight costs and delivery times for suppliers in the region.',
    status: 'ACTIVE',
    statusColor: '#ef4444',
    statusBg: 'rgba(239, 68, 68, 0.12)',
    probability: 'High',
  },
  {
    id: 'suez_canal',
    name: 'Suez Canal Disruption',
    description: 'Partial or full closure of the Suez Canal forcing rerouting via Cape of Good Hope. Significant lead time and cost increases for Europe-Asia trade.',
    status: 'Ongoing',
    statusColor: '#f59e0b',
    statusBg: 'rgba(245, 158, 11, 0.12)',
    probability: 'Medium',
  },
  {
    id: 'taiwan_strait',
    name: 'Taiwan Strait Crisis',
    description: 'Escalation of tensions in the Taiwan Strait affecting semiconductor and electronics supply chains across East Asia.',
    status: 'Monitoring',
    statusColor: '#eab308',
    statusBg: 'rgba(234, 179, 8, 0.12)',
    probability: 'Low',
  },
  {
    id: 'us_china_tariff',
    name: 'US-China Tariff Escalation',
    description: 'Increased tariffs on Chinese imports including raw materials, battery components, and electronics used in e-bike manufacturing.',
    status: 'ACTIVE',
    statusColor: '#ef4444',
    statusBg: 'rgba(239, 68, 68, 0.12)',
    probability: 'High',
  },
  {
    id: 'european_port_strike',
    name: 'European Port Strike',
    description: 'Coordinated labor action across major European ports (Rotterdam, Hamburg, Antwerp) causing weeks-long delays in cargo handling.',
    status: 'Monitoring',
    statusColor: '#eab308',
    statusBg: 'rgba(234, 179, 8, 0.12)',
    probability: 'Low',
  },
]

// ── Component ──────────────────────────────────────────

export default function RiskSimulation() {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function runSimulation(scenarioId: string) {
    setSelectedScenario(scenarioId)
    setResult(null)
    setError(null)
    setLoading(true)

    try {
      const headers = await authHeaders()
      const response = await fetch(`${API_BASE_URL}/api/risk-simulation`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ scenario_id: scenarioId }),
        signal: AbortSignal.timeout(15000),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: response.statusText }))
        throw new Error(errData.error || `Simulation failed: ${response.statusText}`)
      }

      const data: SimulationResult = await response.json()
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Failed to run risk simulation. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const activeScenario = SCENARIOS.find(s => s.id === selectedScenario)

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: 24, background: 'var(--color-bg)' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <AlertTriangle size={22} color="#ef4444" />
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>
              Geopolitical Risk Simulation
            </h2>
          </div>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0, lineHeight: 1.5 }}>
            Select a risk scenario to simulate its impact on your supply chain. The simulation identifies affected suppliers, estimates cost and lead time impacts, and recommends mitigation actions.
          </p>
        </div>

        {/* Scenario cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12, marginBottom: 28 }}>
          {SCENARIOS.map(scenario => {
            const isSelected = selectedScenario === scenario.id
            return (
              <button
                key={scenario.id}
                onClick={() => runSimulation(scenario.id)}
                disabled={loading}
                style={{
                  textAlign: 'left',
                  padding: 16,
                  borderRadius: 'var(--radius-lg)',
                  border: isSelected ? `2px solid ${scenario.statusColor}` : '1px solid var(--color-border)',
                  background: isSelected ? scenario.statusBg : 'var(--color-surface)',
                  cursor: loading ? 'wait' : 'pointer',
                  opacity: loading && !isSelected ? 0.6 : 1,
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)', lineHeight: 1.3, flex: 1, marginRight: 8 }}>
                    {scenario.name}
                  </div>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 10,
                    fontSize: 10,
                    fontWeight: 700,
                    color: scenario.statusColor,
                    background: scenario.statusBg,
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}>
                    {scenario.status}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                  {scenario.description}
                </div>
              </button>
            )
          })}
        </div>

        {/* Loading state */}
        {loading && (
          <div style={{
            padding: '48px 20px',
            textAlign: 'center',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
          }}>
            <Loader2 size={28} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)', marginTop: 12 }}>
              Running simulation...
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>
              Analyzing impact of {activeScenario?.name || 'scenario'} on your supply chain
            </div>
            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div style={{
            padding: 20,
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <AlertTriangle size={16} color="#ef4444" />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#ef4444' }}>Simulation Error</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
              {error}
            </div>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div>
            {/* Scenario header */}
            <div style={{
              padding: '16px 20px',
              background: 'var(--color-nav-bg)',
              color: '#fff',
              borderRadius: 'var(--radius-lg)',
              marginBottom: 16,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{result.scenario.name}</div>
                  <div style={{ fontSize: 13, opacity: 0.8, marginTop: 4 }}>{result.scenario.description}</div>
                  <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>{result.scenario.current_status}</div>
                </div>
                <span style={{
                  padding: '4px 12px',
                  borderRadius: 12,
                  fontSize: 12,
                  fontWeight: 700,
                  background: result.scenario.probability === 'HIGH' ? 'rgba(239,68,68,0.2)' : result.scenario.probability === 'MEDIUM' ? 'rgba(245,158,11,0.2)' : 'rgba(234,179,8,0.2)',
                  color: result.scenario.probability === 'HIGH' ? '#fca5a5' : result.scenario.probability === 'MEDIUM' ? '#fcd34d' : '#fde68a',
                }}>
                  {result.scenario.probability} Probability
                </span>
              </div>
            </div>

            {/* Impact Summary KPI cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
              {[
                {
                  label: 'Avg Cost Impact',
                  value: `+${result.summary.avg_cost_impact_pct}%`,
                  icon: DollarSign,
                  color: '#ef4444',
                  bg: 'rgba(239, 68, 68, 0.08)',
                },
                {
                  label: 'Materials at Risk',
                  value: String(result.summary.total_materials_at_risk),
                  icon: Package,
                  color: '#f59e0b',
                  bg: 'rgba(245, 158, 11, 0.08)',
                },
                {
                  label: 'Max Lead Time Increase',
                  value: `+${result.summary.max_lead_time_increase_days} days`,
                  icon: Clock,
                  color: '#f59e0b',
                  bg: 'rgba(245, 158, 11, 0.08)',
                },
              ].map(kpi => (
                <div key={kpi.label} style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: kpi.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <kpi.icon size={16} color={kpi.color} />
                    </div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {kpi.label}
                    </div>
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--color-text)' }}>
                    {kpi.value}
                  </div>
                </div>
              ))}
            </div>

            {/* Affected Suppliers table */}
            {result.affected_suppliers.length > 0 && (
              <div style={{
                marginBottom: 20,
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
              }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertTriangle size={16} color="#ef4444" />
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>
                    Affected Suppliers ({result.affected_suppliers.length})
                  </h3>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: 'var(--color-bg)' }}>
                        {['Supplier', 'Location', 'Materials', 'Freight Impact', 'Lead Time Increase'].map(h => (
                          <th key={h} style={{
                            padding: '10px 16px',
                            textAlign: 'left',
                            fontSize: 11,
                            fontWeight: 600,
                            color: 'var(--color-text-muted)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                            whiteSpace: 'nowrap',
                          }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.affected_suppliers.map((sup, i) => (
                        <tr key={i} style={{ borderTop: '1px solid var(--color-border-light, var(--color-border))' }}>
                          <td style={{ padding: '10px 16px', fontWeight: 500, color: 'var(--color-text)' }}>
                            {sup.name}
                          </td>
                          <td style={{ padding: '10px 16px', color: 'var(--color-text-secondary)' }}>
                            {sup.location}
                          </td>
                          <td style={{ padding: '10px 16px', color: 'var(--color-text-secondary)' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                              {sup.materials_at_risk.map(m => (
                                <span key={m} style={{
                                  padding: '1px 8px',
                                  borderRadius: 8,
                                  fontSize: 11,
                                  background: 'rgba(239, 68, 68, 0.08)',
                                  color: '#ef4444',
                                  fontWeight: 500,
                                }}>
                                  {MATERIAL_NAMES[m] || m}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td style={{ padding: '10px 16px' }}>
                            <span style={{
                              color: sup.freight_increase_pct > 30 ? '#ef4444' : sup.freight_increase_pct > 15 ? '#f59e0b' : '#eab308',
                              fontWeight: 600,
                            }}>
                              +{sup.freight_increase_pct}%
                            </span>
                          </td>
                          <td style={{ padding: '10px 16px' }}>
                            <span style={{
                              color: sup.lead_time_increase_days > 14 ? '#ef4444' : sup.lead_time_increase_days > 7 ? '#f59e0b' : '#eab308',
                              fontWeight: 600,
                            }}>
                              +{sup.lead_time_increase_days} days
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Unaffected Suppliers */}
            {result.unaffected_suppliers.length > 0 && (
              <div style={{
                marginBottom: 20,
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
              }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Shield size={16} color="#22c55e" />
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>
                    Unaffected Suppliers ({result.unaffected_suppliers.length})
                  </h3>
                </div>
                <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                  {result.unaffected_suppliers.map((sup, i) => (
                    <div key={i} style={{
                      padding: '12px 16px',
                      borderRadius: 'var(--radius-md, 8px)',
                      background: 'rgba(34, 197, 94, 0.06)',
                      border: '1px solid rgba(34, 197, 94, 0.15)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                        <CheckCircle size={14} color="#22c55e" />
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>{sup.name}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 4 }}>{sup.location}</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {sup.materials_supplied.map(m => (
                          <span key={m} style={{
                            padding: '1px 8px',
                            borderRadius: 8,
                            fontSize: 11,
                            background: 'rgba(34, 197, 94, 0.1)',
                            color: '#22c55e',
                            fontWeight: 500,
                          }}>
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommended Actions */}
            {result.recommended_actions.length > 0 && (
              <div style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
              }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <TrendingUp size={16} color="var(--color-primary)" />
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>
                    Recommended Actions
                  </h3>
                </div>
                <ul style={{ padding: '16px 20px 16px 36px', margin: 0, listStyleType: 'disc' }}>
                  {result.recommended_actions.map((action, i) => (
                    <li key={i} style={{
                      fontSize: 13,
                      color: 'var(--color-text-secondary)',
                      lineHeight: 1.6,
                      marginBottom: i < result.recommended_actions.length - 1 ? 6 : 0,
                    }}>
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
