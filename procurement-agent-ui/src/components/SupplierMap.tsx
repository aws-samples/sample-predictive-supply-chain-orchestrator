import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Circle, Polyline, useMap, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchSuppliers, API_BASE_URL, authHeaders } from '../services/api'

import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'
const DefaultIcon = L.icon({ iconUrl: icon, shadowUrl: iconShadow, iconSize: [25, 41], iconAnchor: [12, 41] })
L.Marker.prototype.options.icon = DefaultIcon

interface SupplierMapProps {
  selectedSolution: string | null
  solutionSupplierIds?: string[]
  solutions?: { id: string; name: string }[]
  onSelectSolution?: (id: string) => void
  onSupplierClick?: (supplierId: string | null) => void
  activeSupplier?: string | null
  onRiskOptimize?: (message: string) => void
  onNavigate?: (view: string) => void
  onRefetchOptimization?: (excludedSuppliers?: string[]) => Promise<void>
}

function MapController({ flyTo }: { flyTo: { lat: number; lng: number; zoom: number } | null }) {
  const map = useMap()
  useEffect(() => { if (flyTo) map.flyTo([flyTo.lat, flyTo.lng], flyTo.zoom, { duration: 1.2 }) }, [flyTo, map])
  // Invalidate size when container resizes (e.g. agent panel open/close)
  useEffect(() => {
    const container = map.getContainer()
    const ro = new ResizeObserver(() => { map.invalidateSize() })
    ro.observe(container)
    return () => ro.disconnect()
  }, [map])
  return null
}

const FACTORY = { name: 'VoltCycle Factory', city: 'Denver, CO', lat: 39.7392, lng: -104.9903 }

const SUPPLIERS = [
  { id: 'SUP-001', name: 'Shenzhen LiPower', country: 'China', city: 'Shenzhen', region: 'Asia-Pacific', lat: 22.5431, lng: 114.0579, risk: 3.2, leadTime: 35, distance: '6,900 mi' },
  { id: 'SUP-002', name: 'Samsung SDI', country: 'South Korea', city: 'Seoul', region: 'Asia-Pacific', lat: 37.5665, lng: 126.9780, risk: 2.1, leadTime: 38, distance: '6,400 mi' },
  { id: 'SUP-003', name: 'Panasonic Energy', country: 'USA', city: 'San Jose', region: 'Americas', lat: 37.3382, lng: -121.8863, risk: 1.5, leadTime: 3, distance: '950 mi' },
  { id: 'SUP-004', name: 'Bafang Electric', country: 'Germany', city: 'Munich', region: 'Europe', lat: 48.1351, lng: 11.5820, risk: 1.8, leadTime: 18, distance: '5,200 mi' },
  { id: 'SUP-005', name: 'Shimano Components', country: 'Taiwan', city: 'Taipei', region: 'Asia-Pacific', lat: 25.0330, lng: 121.5654, risk: 2.8, leadTime: 32, distance: '6,800 mi' },
  { id: 'SUP-006', name: 'Bosch eBike Systems', country: 'USA', city: 'Detroit', region: 'Americas', lat: 42.3314, lng: -83.0458, risk: 1.5, leadTime: 3, distance: '1,200 mi' },
  { id: 'SUP-007', name: 'Giant Mfg', country: 'USA', city: 'Portland', region: 'Americas', lat: 45.5152, lng: -122.6784, risk: 1.5, leadTime: 2, distance: '1,000 mi' },
  { id: 'SUP-008', name: 'Merida Industry', country: 'Japan', city: 'Nagoya', region: 'Asia-Pacific', lat: 35.1815, lng: 136.9066, risk: 2.0, leadTime: 30, distance: '5,800 mi' },
  { id: 'SUP-009', name: 'Reynolds Tech', country: 'UK', city: 'Manchester', region: 'Europe', lat: 53.4808, lng: -2.2426, risk: 2.2, leadTime: 16, distance: '4,700 mi' },
  { id: 'SUP-010', name: 'Garmin Display Systems', country: 'India', city: 'Bangalore', region: 'Asia-Pacific', lat: 12.9716, lng: 77.5946, risk: 3.5, leadTime: 28, distance: '8,500 mi' },
  { id: 'SUP-011', name: 'Continental Elec', country: 'USA', city: 'Austin', region: 'Americas', lat: 30.2672, lng: -97.7431, risk: 1.5, leadTime: 2, distance: '800 mi' },
  { id: 'SUP-012', name: 'Sigma Sport', country: 'China', city: 'Guangzhou', region: 'Asia-Pacific', lat: 23.1291, lng: 113.2644, risk: 3.2, leadTime: 34, distance: '7,100 mi' },
  { id: 'SUP-013', name: 'DT Swiss', country: 'Netherlands', city: 'Amsterdam', region: 'Europe', lat: 52.3676, lng: 4.9041, risk: 1.7, leadTime: 17, distance: '4,900 mi' },
  { id: 'SUP-014', name: 'Mavic SAS', country: 'USA', city: 'Chicago', region: 'Americas', lat: 41.8781, lng: -87.6298, risk: 1.5, leadTime: 2, distance: '900 mi' },
  { id: 'SUP-015', name: 'SRAM Corp', country: 'Germany', city: 'Stuttgart', region: 'Europe', lat: 48.7758, lng: 9.1829, risk: 1.8, leadTime: 18, distance: '5,300 mi' },
]

const RISK_ZONES = [
  { id: 'rz1', title: 'Strait of Hormuz', severity: 'HIGH' as const, impact: '+14d shipping delay', lat: 26.5, lng: 56.3, radius: 500000 },
  { id: 'rz2', title: 'US-China Tariffs', severity: 'MEDIUM' as const, impact: '+20% tariffs', lat: 35, lng: 110, radius: 800000 },
  { id: 'rz3', title: 'Typhoon Season', severity: 'MEDIUM' as const, impact: 'Port closures 3-7d', lat: 20, lng: 130, radius: 700000 },
]

const RISK_SCENARIO_OPTIONS = [
  { id: '', label: 'No Scenario' },
  { id: 'strait_of_hormuz', label: '🔴 Strait of Hormuz' },
  { id: 'suez_canal', label: '🟠 Suez Canal' },
  { id: 'taiwan_strait', label: '🟡 Taiwan Strait' },
  { id: 'us_china_tariff', label: '🔴 US-China Tariff' },
  { id: 'european_port_strike', label: '🟡 EU Port Strike' },
]

interface RiskResult {
  scenario: { name: string; probability: string; current_status: string; freight_increase_pct: number; lead_time_increase_days: number }
  affected_suppliers: { supplier_id: string; name: string; materials_count: number; freight_increase_pct: number; lead_time_increase_days: number }[]
  unaffected_suppliers: { supplier_id: string; name: string }[]
  summary: { affected_supplier_count: number; total_materials_at_risk: number; avg_cost_impact_pct: number; max_lead_time_increase_days: number }
  recommended_actions: string[]
}

export default function SupplierMap({ selectedSolution, solutionSupplierIds, solutions, onSelectSolution, onSupplierClick, activeSupplier, onRiskOptimize, onNavigate, onRefetchOptimization }: SupplierMapProps) {
  const [showRisks, setShowRisks] = useState(true)
  const [flyTo, setFlyTo] = useState<{ lat: number; lng: number; zoom: number } | null>(null)
  const [showList, setShowList] = useState(false)
  const [riskScenario, setRiskScenario] = useState('')
  const [riskResult, setRiskResult] = useState<RiskResult | null>(null)
  const [riskLoading, setRiskLoading] = useState(false)

  const affectedIds = new Set(riskResult?.affected_suppliers.map(s => s.supplier_id) || [])

  const handleRiskChange = async (scenarioId: string) => {
    setRiskScenario(scenarioId)
    if (!scenarioId) { setRiskResult(null); return }
    setRiskLoading(true)
    try {
      const headers = await authHeaders()
      const res = await fetch(`${API_BASE_URL}/api/risk-simulation`, {
        method: 'POST', headers,
        body: JSON.stringify({ scenario_id: scenarioId }),
        signal: AbortSignal.timeout(10000),
      })
      if (res.ok) setRiskResult(await res.json())
    } catch (err) { console.error('Risk simulation failed') }
    setRiskLoading(false)
  }

  const inSolution = (id: string) => !solutionSupplierIds || solutionSupplierIds.length === 0 || solutionSupplierIds.includes(id)

  const createIcon = (risk: number, name: string, active: boolean, selected: boolean, supplierId?: string) => {
    const isAffected = supplierId ? affectedIds.has(supplierId) : false
    const color = isAffected ? '#ef4444' : riskScenario && !isAffected && supplierId && affectedIds.size > 0 ? '#22c55e' : risk < 2.5 ? '#10b981' : risk < 3.5 ? '#f59e0b' : '#ef4444'
    const size = selected ? 32 : active ? 26 : 20
    const border = selected ? '3px solid #3b82f6' : '2px solid #fff'
    const opacity = active ? 1 : 0.4
    const shadow = selected ? '0 0 0 4px rgba(59,130,246,0.3), 0 2px 8px rgba(0,0,0,0.3)' : '0 2px 6px rgba(0,0,0,0.25)'
    return L.divIcon({
      className: 'custom-supplier-marker',
      // nosemgrep: html-in-template-string -- interpolated values are computed numerics/booleans and a single char from a controlled supplier name; no user input
      html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:${border};box-shadow:${shadow};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:${size * 0.42}px;opacity:${opacity};font-family:Inter,system-ui,sans-serif;cursor:pointer;transition:all 0.15s;">${name.charAt(0)}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
  }

  const factoryIcon = L.divIcon({
    className: 'custom-factory-marker',
    html: `<div style="background:#3b82f6;width:32px;height:32px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 10px rgba(59,130,246,0.4);display:flex;align-items:center;justify-content:center;font-size:15px;">🏭</div>`,
    iconSize: [32, 32], iconAnchor: [16, 16],
  })

  const handleMarkerClick = (sup: typeof SUPPLIERS[0]) => {
    setFlyTo({ lat: sup.lat, lng: sup.lng, zoom: 5 })
    onSupplierClick?.(sup.id)
  }

  // Stats for floating summary
  const avgRisk = (SUPPLIERS.reduce((s, sup) => s + sup.risk, 0) / SUPPLIERS.length).toFixed(1)
  const regions = [...new Set(SUPPLIERS.map(s => s.region))]
  const regionCounts = regions.map(r => ({ region: r, count: SUPPLIERS.filter(s => s.region === r).length }))

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      {/* ── Map ── */}
      <MapContainer
        center={[30, -10]}
        zoom={2}
        minZoom={2}
        maxBoundsViscosity={0.5}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        worldCopyJump={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <MapController flyTo={flyTo} />

        {/* Risk zones */}
        {showRisks && RISK_ZONES.map(z => (
          <Circle key={z.id} center={[z.lat, z.lng]} radius={z.radius} pathOptions={{
            color: z.severity === 'HIGH' ? '#ef4444' : '#f59e0b',
            fillColor: z.severity === 'HIGH' ? '#ef4444' : '#f59e0b',
            fillOpacity: 0.12, weight: 1.5, opacity: 0.5,
          }}>
            <Tooltip direction="top" opacity={0.95} sticky>
              <div style={{ fontSize: 12 }}><strong>{z.title}</strong><br />{z.impact}</div>
            </Tooltip>
          </Circle>
        ))}

        {/* Shipping routes — highlighted when risk scenario active */}
        {SUPPLIERS.map(sup => {
          const isAffected = affectedIds.has(sup.id)
          const hasScenario = riskScenario && affectedIds.size > 0
          const isActive = sup.id === activeSupplier

          let color = sup.risk < 2.5 ? '#10b981' : sup.risk < 3.5 ? '#f59e0b' : '#ef4444'
          let weight = 1.2
          let opacity = 0.25
          let dashArray = '6, 8'

          if (isActive) {
            color = '#3b82f6'; weight = 3; opacity = 0.8; dashArray = ''
          } else if (hasScenario && isAffected) {
            color = '#ef4444'; weight = 2.5; opacity = 0.7; dashArray = ''
          } else if (hasScenario && !isAffected) {
            color = '#22c55e'; weight = 1.5; opacity = 0.5; dashArray = '6, 8'
          }

          return (
            <Polyline key={`r-${sup.id}`} positions={[[sup.lat, sup.lng], [FACTORY.lat, FACTORY.lng]]} pathOptions={{
              color, weight, opacity, dashArray,
            }} />
          )
        })}

        {/* Factory */}
        <Marker position={[FACTORY.lat, FACTORY.lng]} icon={factoryIcon}>
          <Tooltip direction="top" offset={[0, -16]} opacity={0.9}>
            <strong>🏭 {FACTORY.name}</strong><br /><span style={{ fontSize: 11 }}>{FACTORY.city}</span>
          </Tooltip>
        </Marker>

        {/* Supplier markers */}
        {SUPPLIERS.map(sup => (
          <Marker
            key={sup.id}
            position={[sup.lat, sup.lng]}
            icon={createIcon(sup.risk, sup.name, inSolution(sup.id), sup.id === activeSupplier, sup.id)}
            eventHandlers={{ click: () => handleMarkerClick(sup) }}
          >
            <Tooltip direction="top" offset={[0, -12]} opacity={0.95}>
              <div style={{ fontSize: 12 }}>
                <strong>{sup.name}</strong>
                <div style={{ color: '#64748b', marginTop: 2 }}>{sup.city}, {sup.country} · {sup.leadTime}d · Risk {sup.risk}</div>
              </div>
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>

      {/* ── Floating controls (top-left) ── */}
      <div style={{
        position: 'absolute', top: 12, left: 12, zIndex: 1000,
        display: 'flex', gap: 6,
      }}>
        <button onClick={() => { setFlyTo({ lat: 30, lng: -10, zoom: 2 }); onSupplierClick?.(null) }} style={{
          padding: '6px 12px', borderRadius: 8, border: '1px solid #e2e8f0',
          background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#3b82f6',
          boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        }}>🌍 Reset</button>
        <button onClick={() => setShowRisks(!showRisks)} style={{
          padding: '6px 12px', borderRadius: 8, border: '1px solid #e2e8f0',
          background: showRisks ? '#fef3c7' : '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500,
          color: showRisks ? '#92400e' : '#64748b', boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        }}>{showRisks ? '⚠️ Risks On' : '⚠️ Risks Off'}</button>
        <select
          value={riskScenario}
          onChange={(e) => handleRiskChange(e.target.value)}
          style={{
            padding: '6px 10px', borderRadius: 8, border: '1px solid #e2e8f0',
            background: riskScenario ? '#fef2f2' : '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600,
            color: riskScenario ? '#dc2626' : '#64748b', boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
          }}
        >
          {RISK_SCENARIO_OPTIONS.map(opt => (
            <option key={opt.id} value={opt.id}>{opt.label}</option>
          ))}
        </select>
        {solutions && solutions.length > 0 && solutions.map(s => (
          <button key={s.id} onClick={() => onSelectSolution?.(s.id)} style={{
            padding: '6px 10px', borderRadius: 8, fontSize: 11, fontWeight: 500, cursor: 'pointer',
            border: selectedSolution === s.id ? '2px solid #3b82f6' : '1px solid #e2e8f0',
            background: selectedSolution === s.id ? '#eff6ff' : '#fff',
            color: selectedSolution === s.id ? '#1d4ed8' : '#64748b',
            boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
          }}>{s.name}</button>
        ))}
      </div>

      {/* ── Supplier list toggle (top-right) ── */}
      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 1000 }}>
        <button onClick={() => setShowList(!showList)} style={{
          padding: '6px 14px', borderRadius: 8, border: showList ? '2px solid #3b82f6' : '1px solid #e2e8f0',
          background: showList ? '#eff6ff' : '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600,
          color: showList ? '#1d4ed8' : '#475569', boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        }}>📋 Suppliers ({SUPPLIERS.length})</button>
      </div>

      {/* ── Floating supplier list (right side) ── */}
      {showList && !activeSupplier && (
        <div style={{
          position: 'absolute', top: 48, right: 12, bottom: 12, width: 280, zIndex: 1000,
          background: '#fff', borderRadius: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
          border: '1px solid #e2e8f0', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '12px 14px', borderBottom: '1px solid #f1f5f9', fontSize: 13, fontWeight: 700, color: '#1e293b' }}>
            All Suppliers
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
            {regions.map(region => {
              const regionSups = SUPPLIERS.filter(s => s.region === region)
              return (
                <div key={region}>
                  <div style={{ padding: '8px 14px 4px', fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {region} ({regionSups.length})
                  </div>
                  {regionSups.map(sup => {
                    const riskColor = sup.risk < 2.5 ? '#10b981' : sup.risk < 3.5 ? '#f59e0b' : '#ef4444'
                    const active = inSolution(sup.id)
                    return (
                      <button key={sup.id} onClick={() => handleMarkerClick(sup)} style={{
                        display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '7px 14px',
                        border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left',
                        opacity: active ? 1 : 0.5,
                      }}>
                        <span style={{
                          width: 24, height: 24, borderRadius: '50%', background: riskColor, flexShrink: 0,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: '#fff', fontSize: 11, fontWeight: 700,
                        }}>{sup.name.charAt(0)}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 500, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sup.name}</div>
                          <div style={{ fontSize: 10, color: '#94a3b8' }}>{sup.city} · {sup.leadTime}d</div>
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 600, color: riskColor }}>{sup.risk}</span>
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Risk Impact Panel (bottom-right) ── */}
      {riskResult && !riskLoading && (
        <div style={{
          position: 'absolute', bottom: 12, right: 12, zIndex: 1000, width: 320,
          background: '#fff', borderRadius: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          border: '2px solid #ef4444', overflow: 'hidden', maxHeight: '60%', display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '12px 16px', background: '#fef2f2', borderBottom: '1px solid #fecaca' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#dc2626' }}>{riskResult.scenario.name}</div>
            <div style={{ fontSize: 11, color: '#991b1b', marginTop: 2 }}>{riskResult.scenario.current_status}</div>
          </div>
          <div style={{ padding: '12px 16px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#ef4444' }}>{riskResult.summary.affected_supplier_count}</div>
              <div style={{ fontSize: 9, color: '#94a3b8', textTransform: 'uppercase' }}>Suppliers Hit</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#f59e0b' }}>{riskResult.summary.total_materials_at_risk}</div>
              <div style={{ fontSize: 9, color: '#94a3b8', textTransform: 'uppercase' }}>Materials</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#f59e0b' }}>+{riskResult.summary.max_lead_time_increase_days}d</div>
              <div style={{ fontSize: 9, color: '#94a3b8', textTransform: 'uppercase' }}>Lead Time</div>
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 8px', fontSize: 12 }}>
            <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: 6 }}>Affected:</div>
            {riskResult.affected_suppliers.map(s => (
              <div key={s.supplier_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid #f8fafc' }}>
                <span style={{ color: '#ef4444', fontWeight: 500 }}>{s.name}</span>
                <span style={{ color: '#94a3b8' }}>+{s.freight_increase_pct}% freight</span>
              </div>
            ))}
            <div style={{ fontWeight: 600, color: '#1e293b', marginTop: 10, marginBottom: 6 }}>Safe alternatives:</div>
            {riskResult.unaffected_suppliers.slice(0, 4).map(s => (
              <div key={s.supplier_id} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 0' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
                <span style={{ color: '#22c55e', fontWeight: 500 }}>{s.name}</span>
              </div>
            ))}
          </div>
          <div style={{ padding: '10px 16px', borderTop: '1px solid #fecaca', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button
              onClick={async () => {
                const affectedIds = riskResult.affected_suppliers.map(s => s.supplier_id)
                if (onRefetchOptimization) await onRefetchOptimization(affectedIds)
                if (onNavigate) onNavigate('results')
              }}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: 8, border: 'none',
                background: '#dc2626', color: '#fff', fontSize: 12, fontWeight: 700,
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              ⚡ Re-Optimize Excluding {riskResult.affected_suppliers.length} Affected Suppliers
            </button>
            <button
              onClick={() => {
                const safeNames = riskResult.unaffected_suppliers.map(s => s.name).join(', ')
                const msg = `Analyze the impact of ${riskResult.scenario.name} on our supply chain. ${riskResult.summary.affected_supplier_count} suppliers affected with +${riskResult.scenario.freight_increase_pct}% freight. Safe alternatives: ${safeNames}. Recommend a mitigation strategy.`
                if (onRiskOptimize) onRiskOptimize(msg)
              }}
              style={{
                width: '100%', padding: '6px 12px', borderRadius: 8, border: '1px solid #fecaca',
                background: 'transparent', color: '#dc2626', fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}
            >
              💬 Ask Agent for Analysis
            </button>
          </div>
        </div>
      )}
      {riskLoading && (
        <div style={{
          position: 'absolute', bottom: 12, right: 12, zIndex: 1000,
          background: '#fff', borderRadius: 12, padding: '20px 24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.12)', border: '1px solid #e2e8f0',
          fontSize: 13, color: '#64748b',
        }}>
          Simulating risk scenario...
        </div>
      )}

      {/* ── Floating summary (bottom-left) ── */}
      <div style={{
        position: 'absolute', bottom: 32, left: 12, zIndex: 1000,
        background: '#fff', borderRadius: 12, padding: '14px 18px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.12)', border: '1px solid #e2e8f0',
        minWidth: 220,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', marginBottom: 8 }}>Supply Network</div>
        <div style={{ display: 'flex', gap: 16, fontSize: 12, marginBottom: 10 }}>
          <div><span style={{ fontWeight: 700, color: '#1e293b', fontSize: 18 }}>{SUPPLIERS.length}</span><div style={{ color: '#94a3b8', fontSize: 10, marginTop: 1 }}>Suppliers</div></div>
          <div><span style={{ fontWeight: 700, color: parseFloat(avgRisk) > 2.5 ? '#f59e0b' : '#10b981', fontSize: 18 }}>{avgRisk}</span><div style={{ color: '#94a3b8', fontSize: 10, marginTop: 1 }}>Avg Risk</div></div>
          <div><span style={{ fontWeight: 700, color: '#1e293b', fontSize: 18 }}>{regions.length}</span><div style={{ color: '#94a3b8', fontSize: 10, marginTop: 1 }}>Regions</div></div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {regionCounts.map(r => (
            <span key={r.region} style={{
              padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600,
              background: '#f1f5f9', color: '#475569',
            }}>{r.region} ({r.count})</span>
          ))}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: 10, marginTop: 10, paddingTop: 8, borderTop: '1px solid #f1f5f9' }}>
          {[{ l: 'Low', c: '#10b981' }, { l: 'Medium', c: '#f59e0b' }, { l: 'High', c: '#ef4444' }].map(x => (
            <div key={x.l} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#94a3b8' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: x.c }} />{x.l}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
