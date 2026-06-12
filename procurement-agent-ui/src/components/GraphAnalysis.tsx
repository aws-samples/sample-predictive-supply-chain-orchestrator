import { useState, useEffect, useMemo } from 'react'
import { Search, Loader2, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { API_BASE_URL, authHeaders, sendChatMessage } from '../services/api'

// ── Data types ──────────────────────────────────────────────────────────────

interface SupplierData {
  id: string; name: string; location: string; risk: number; rating: number;
  // Neptune-enriched fields (optional — present when backend returns them)
  on_time_delivery_rate?: number;
  quality_score?: number;
  defect_rate?: number;
  response_time_hours?: number;
  contract_type?: string;
  payment_terms?: string;
  annual_value?: number;
  contract_status?: string;
}
interface MaterialData {
  id: string; name: string; category: string; criticality: string;
  // Neptune-enriched inventory fields
  current_stock?: number;
  reorder_point?: number;
  safety_stock?: number;
}
interface EdgeData { from: string; to: string; }

const SUPPLIERS_DATA: SupplierData[] = [
  { id: 'SUP-001', name: 'Shenzhen LiPower', location: 'China', risk: 3.2, rating: 4.25 },
  { id: 'SUP-002', name: 'Samsung SDI', location: 'South Korea', risk: 2.1, rating: 4.5 },
  { id: 'SUP-003', name: 'Panasonic Energy', location: 'USA', risk: 1.5, rating: 4.3 },
  { id: 'SUP-004', name: 'Bafang Electric', location: 'Germany', risk: 1.8, rating: 4.6 },
  { id: 'SUP-005', name: 'Shimano Components', location: 'Taiwan', risk: 2.8, rating: 4.1 },
  { id: 'SUP-006', name: 'Bosch eBike', location: 'USA', risk: 1.5, rating: 4.0 },
  { id: 'SUP-007', name: 'Giant Mfg', location: 'USA', risk: 1.5, rating: 4.4 },
  { id: 'SUP-008', name: 'Merida Industry', location: 'Japan', risk: 2.0, rating: 4.7 },
  { id: 'SUP-009', name: 'Reynolds Tech', location: 'UK', risk: 2.2, rating: 4.3 },
  { id: 'SUP-010', name: 'Garmin Display', location: 'India', risk: 3.5, rating: 3.75 },
  { id: 'SUP-011', name: 'Continental Elec', location: 'USA', risk: 1.5, rating: 4.2 },
  { id: 'SUP-012', name: 'Sigma Sport', location: 'China', risk: 3.2, rating: 3.8 },
  { id: 'SUP-013', name: 'DT Swiss', location: 'Netherlands', risk: 1.7, rating: 4.5 },
  { id: 'SUP-014', name: 'Mavic SAS', location: 'USA', risk: 1.5, rating: 4.0 },
  { id: 'SUP-015', name: 'SRAM Corp', location: 'Germany', risk: 1.8, rating: 4.7 },
]

const MATERIALS_DATA: MaterialData[] = [
  { id: 'MAT-BAT-001', name: 'Li-ion Battery Pack', category: 'BATTERY_SYSTEM', criticality: 'CRITICAL' },
  { id: 'MAT-BAT-002', name: 'Battery Mgmt System', category: 'BATTERY_SYSTEM', criticality: 'CRITICAL' },
  { id: 'MAT-BAT-003', name: 'Charging Port', category: 'BATTERY_SYSTEM', criticality: 'HIGH' },
  { id: 'MAT-MOT-001', name: 'Mid-Drive Motor', category: 'DRIVE_SYSTEM', criticality: 'CRITICAL' },
  { id: 'MAT-MOT-002', name: 'Hub Motor', category: 'DRIVE_SYSTEM', criticality: 'CRITICAL' },
  { id: 'MAT-MOT-003', name: 'Motor Controller', category: 'DRIVE_SYSTEM', criticality: 'CRITICAL' },
  { id: 'MAT-MOT-004', name: 'Torque Sensor', category: 'DRIVE_SYSTEM', criticality: 'HIGH' },
  { id: 'MAT-FRM-001', name: 'Aluminum Frame', category: 'FRAME_COMPONENT', criticality: 'CRITICAL' },
  { id: 'MAT-FRM-002', name: 'Carbon Fiber Frame', category: 'FRAME_COMPONENT', criticality: 'HIGH' },
  { id: 'MAT-FRM-003', name: 'Suspension Fork', category: 'FRAME_COMPONENT', criticality: 'MEDIUM' },
  { id: 'MAT-FRM-004', name: 'Handlebar Assembly', category: 'FRAME_COMPONENT', criticality: 'MEDIUM' },
  { id: 'MAT-ELC-001', name: 'LCD Display', category: 'ELECTRONICS', criticality: 'HIGH' },
  { id: 'MAT-ELC-002', name: 'Wiring Harness', category: 'ELECTRONICS', criticality: 'HIGH' },
  { id: 'MAT-ELC-003', name: 'Speed Sensor', category: 'ELECTRONICS', criticality: 'MEDIUM' },
  { id: 'MAT-STD-001', name: 'Wheel Set', category: 'STANDARD_PARTS', criticality: 'HIGH' },
  { id: 'MAT-STD-002', name: 'Hydraulic Brakes', category: 'STANDARD_PARTS', criticality: 'HIGH' },
  { id: 'MAT-STD-003', name: 'Gear System', category: 'STANDARD_PARTS', criticality: 'MEDIUM' },
  { id: 'MAT-STD-004', name: 'Pedal Set', category: 'STANDARD_PARTS', criticality: 'LOW' },
]

const EDGES_DATA: EdgeData[] = [
  { from: 'SUP-001', to: 'MAT-BAT-001' }, { from: 'SUP-001', to: 'MAT-BAT-002' }, { from: 'SUP-001', to: 'MAT-BAT-003' },
  { from: 'SUP-002', to: 'MAT-BAT-001' }, { from: 'SUP-002', to: 'MAT-BAT-002' }, { from: 'SUP-002', to: 'MAT-BAT-003' },
  { from: 'SUP-003', to: 'MAT-BAT-001' }, { from: 'SUP-003', to: 'MAT-BAT-002' }, { from: 'SUP-003', to: 'MAT-BAT-003' },
  { from: 'SUP-004', to: 'MAT-MOT-001' }, { from: 'SUP-004', to: 'MAT-MOT-002' }, { from: 'SUP-004', to: 'MAT-MOT-003' }, { from: 'SUP-004', to: 'MAT-MOT-004' },
  { from: 'SUP-005', to: 'MAT-MOT-001' }, { from: 'SUP-005', to: 'MAT-MOT-002' }, { from: 'SUP-005', to: 'MAT-MOT-003' }, { from: 'SUP-005', to: 'MAT-MOT-004' },
  { from: 'SUP-006', to: 'MAT-MOT-001' }, { from: 'SUP-006', to: 'MAT-MOT-002' },
  { from: 'SUP-007', to: 'MAT-FRM-001' }, { from: 'SUP-007', to: 'MAT-FRM-003' }, { from: 'SUP-007', to: 'MAT-FRM-004' },
  { from: 'SUP-008', to: 'MAT-FRM-002' },
  { from: 'SUP-009', to: 'MAT-FRM-001' }, { from: 'SUP-009', to: 'MAT-FRM-002' }, { from: 'SUP-009', to: 'MAT-FRM-003' }, { from: 'SUP-009', to: 'MAT-FRM-004' },
  { from: 'SUP-010', to: 'MAT-ELC-001' }, { from: 'SUP-010', to: 'MAT-ELC-002' }, { from: 'SUP-010', to: 'MAT-ELC-003' },
  { from: 'SUP-011', to: 'MAT-ELC-001' }, { from: 'SUP-011', to: 'MAT-ELC-002' }, { from: 'SUP-011', to: 'MAT-ELC-003' },
  { from: 'SUP-012', to: 'MAT-ELC-001' },
  { from: 'SUP-013', to: 'MAT-STD-001' }, { from: 'SUP-013', to: 'MAT-STD-003' }, { from: 'SUP-013', to: 'MAT-STD-004' },
  { from: 'SUP-014', to: 'MAT-STD-001' }, { from: 'SUP-014', to: 'MAT-STD-002' }, { from: 'SUP-014', to: 'MAT-STD-003' }, { from: 'SUP-014', to: 'MAT-STD-004' },
  { from: 'SUP-015', to: 'MAT-STD-002' },
]

// ── Color & display helpers ─────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  BATTERY_SYSTEM: '#3b82f6',
  DRIVE_SYSTEM: '#8b5cf6',
  FRAME_COMPONENT: '#f59e0b',
  ELECTRONICS: '#22c55e',
  STANDARD_PARTS: '#94a3b8',
}

const CATEGORY_LABELS: Record<string, string> = {
  BATTERY_SYSTEM: 'Battery System',
  DRIVE_SYSTEM: 'Drive System',
  FRAME_COMPONENT: 'Frame Components',
  ELECTRONICS: 'Electronics',
  STANDARD_PARTS: 'Standard Parts',
}

const CRITICALITY_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f59e0b',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
}

const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS)

const REGION_FLAGS: Record<string, string> = {
  'China': '🇨🇳', 'Shenzhen China': '🇨🇳', 'Guangzhou China': '🇨🇳',
  'South Korea': '🇰🇷', 'Seoul South Korea': '🇰🇷',
  'Japan': '🇯🇵', 'Nagoya Japan': '🇯🇵',
  'Taiwan': '🇹🇼', 'Taipei Taiwan': '🇹🇼',
  'USA': '🇺🇸', 'San Jose USA': '🇺🇸', 'Detroit USA': '🇺🇸', 'Portland USA': '🇺🇸', 'Austin USA': '🇺🇸', 'Chicago USA': '🇺🇸',
  'Germany': '🇩🇪', 'Munich Germany': '🇩🇪', 'Stuttgart Germany': '🇩🇪',
  'UK': '🇬🇧', 'Manchester UK': '🇬🇧',
  'India': '🇮🇳', 'Bangalore India': '🇮🇳',
  'Netherlands': '🇳🇱', 'Amsterdam Netherlands': '🇳🇱',
  'France': '🇫🇷',
}

function riskColor(risk: number): string {
  if (risk < 2.5) return '#22c55e'
  if (risk < 3.5) return '#f59e0b'
  return '#ef4444'
}

function otdColor(rate: number): string {
  if (rate >= 95) return '#22c55e'
  if (rate >= 90) return '#f59e0b'
  return '#ef4444'
}

function defectColor(rate: number): string {
  if (rate < 1) return '#22c55e'
  if (rate < 2) return '#f59e0b'
  return '#ef4444'
}

function qualityColor(score: number): string {
  if (score >= 8) return '#22c55e'
  if (score >= 6) return '#f59e0b'
  return '#ef4444'
}

function inventoryStatus(stock?: number, reorder?: number, safety?: number): { label: string; color: string } {
  if (stock == null || reorder == null || safety == null) return { label: 'N/A', color: '#94a3b8' }
  if (stock < safety) return { label: 'CRITICAL', color: '#ef4444' }
  if (stock < reorder) return { label: 'LOW', color: '#f59e0b' }
  return { label: 'OK', color: '#22c55e' }
}

function renderStars(rating: number): string {
  const full = Math.floor(rating)
  const half = rating - full >= 0.25
  let s = ''
  for (let i = 0; i < full; i++) s += '\u2605'
  if (half) s += '\u00BD'
  return s
}

function lightenHex(hex: string, amount: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const nr = Math.min(255, Math.round(r + (255 - r) * amount))
  const ng = Math.min(255, Math.round(g + (255 - g) * amount))
  const nb = Math.min(255, Math.round(b + (255 - b) * amount))
  return `#${nr.toString(16).padStart(2, '0')}${ng.toString(16).padStart(2, '0')}${nb.toString(16).padStart(2, '0')}`
}

// ── Sankey layout types ─────────────────────────────────────────────────────

interface BarPos {
  x: number; y: number; w: number; h: number;
}

interface SankeyBand {
  key: string;
  sourceBar: BarPos;
  targetBar: BarPos;
  sourceSlotY: number;
  targetSlotY: number;
  bandWidth: number;
  color: string;
  opacity: number;
  categoryKey: string;
  materialId: string;
  supplierId: string;
}

type SelectionType =
  | { type: 'category'; key: string }
  | { type: 'material'; id: string }
  | { type: 'supplier'; id: string }

// ── Component ───────────────────────────────────────────────────────────────

export default function GraphAnalysis() {
  const [suppliers, setSuppliers] = useState<SupplierData[]>([])
  const [materials, setMaterials] = useState<MaterialData[]>([])
  const [edges, setEdges] = useState<EdgeData[]>([])
  const [loading, setLoading] = useState(true)

  const [hovered, setHovered] = useState<SelectionType | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [perfFilters, setPerfFilters] = useState<Set<string>>(new Set()) // additive: 'otd' | 'quality' | 'defect' | 'risk' | 'contract'
  const [selected, setSelected] = useState<SelectionType | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [agentResponse, setAgentResponse] = useState<string | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)

  // Performance data from /api/supplier-performance (keyed by supplier_id)
  const [perfData, setPerfData] = useState<Record<string, {
    on_time_delivery_rate?: number; quality_score?: number;
    defect_rate?: number; response_time_hours?: number;
    measurement_period?: string;
  }>>({})

  // ── Data fetching ─────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      let sups: SupplierData[] = []
      let mats: MaterialData[] = []
      let edgeList: EdgeData[] = []

      try {
        const headers = await authHeaders()

        const [supRes, netRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/suppliers`, { headers, signal: AbortSignal.timeout(5000) }),
          fetch(`${API_BASE_URL}/api/graph/network`, { headers, signal: AbortSignal.timeout(5000) }),
        ])

        if (supRes.ok && netRes.ok) {
          const supData = await supRes.json()
          const netData = await netRes.json()

          const backendSuppliers = (supData.suppliers || []) as Array<{
            supplier_id: string; name: string; location: string;
            geopolitical_risk_score?: number; rating?: number;
            on_time_delivery_rate?: number; quality_score?: number;
            defect_rate?: number; response_time_hours?: number;
            contract_type?: string; payment_terms?: string;
            annual_value?: number; contract_status?: string;
          }>
          if (backendSuppliers.length > 0) {
            sups = backendSuppliers.map(s => ({
              id: s.supplier_id,
              name: s.name,
              location: s.location,
              risk: s.geopolitical_risk_score ?? 2.0,
              rating: s.rating ?? 4.0,
              on_time_delivery_rate: s.on_time_delivery_rate,
              quality_score: s.quality_score,
              defect_rate: s.defect_rate,
              response_time_hours: s.response_time_hours,
              contract_type: s.contract_type,
              payment_terms: s.payment_terms,
              annual_value: s.annual_value,
              contract_status: s.contract_status,
            }))
          }

          const netNodes = (netData.nodes || []) as Array<{
            id: string; label: string; type: string;
            category?: string; criticality?: string;
            current_stock?: number; reorder_point?: number; safety_stock?: number;
          }>
          const netMaterials = netNodes.filter(n => n.type === 'material')
          if (netMaterials.length > 0) {
            mats = netMaterials.map(m => ({
              id: m.id,
              name: m.label,
              category: m.category || 'STANDARD_PARTS',
              criticality: m.criticality || 'MEDIUM',
              current_stock: m.current_stock,
              reorder_point: m.reorder_point,
              safety_stock: m.safety_stock,
            }))
          }

          const netLinks = (netData.links || []) as Array<{ source: string; target: string }>
          if (netLinks.length > 0) {
            edgeList = netLinks.map(l => ({ from: l.source, to: l.target }))
          }
        }
      } catch {
        // API unavailable -- fall through to fallback
      }

      if (sups.length === 0) sups = SUPPLIERS_DATA
      if (mats.length === 0) mats = MATERIALS_DATA
      if (edgeList.length === 0) edgeList = EDGES_DATA

      if (cancelled) return

      setSuppliers(sups)
      setMaterials(mats)
      setEdges(edgeList)
      setLoading(false)
    }

    loadData()
    return () => { cancelled = true }
  }, [])

  // ── Fetch performance data ────────────────────────────────────────────────

  useEffect(() => {
    authHeaders().then(headers => {
      fetch(`${API_BASE_URL}/api/supplier-performance`, { headers, signal: AbortSignal.timeout(5000) })
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (d?.performance) {
            const map: Record<string, any> = {}
            for (const p of d.performance as Array<{
              supplier_id: string; measurement_period?: string;
              on_time_delivery_rate?: number; quality_score?: number;
              defect_rate?: number; response_time_hours?: number;
            }>) {
              if (!map[p.supplier_id] || (p.measurement_period && p.measurement_period > (map[p.supplier_id].measurement_period || ''))) {
                map[p.supplier_id] = p
              }
            }
            setPerfData(map)
          }
        })
        .catch(() => { /* performance data unavailable */ })
    })
  }, [])

  // ── Derived lookups ───────────────────────────────────────────────────────

  const materialsByCategory = useMemo(() => {
    const map: Record<string, MaterialData[]> = {}
    CATEGORY_KEYS.forEach(k => { map[k] = [] })
    materials.forEach(m => {
      if (map[m.category]) map[m.category].push(m)
    })
    return map
  }, [materials])

  const suppliersForMaterial = useMemo(() => {
    const map: Record<string, SupplierData[]> = {}
    materials.forEach(m => {
      const supIds = edges.filter(e => e.to === m.id).map(e => e.from)
      map[m.id] = suppliers.filter(s => supIds.includes(s.id))
    })
    return map
  }, [materials, suppliers, edges])

  const materialsForSupplier = useMemo(() => {
    const map: Record<string, MaterialData[]> = {}
    suppliers.forEach(s => {
      const matIds = edges.filter(e => e.from === s.id).map(e => e.to)
      map[s.id] = materials.filter(m => matIds.includes(m.id))
    })
    return map
  }, [materials, suppliers, edges])

  // ── Sankey layout computation ─────────────────────────────────────────────

  const layout = useMemo(() => {
    const padTop = 45
    const availableHeight = 650
    const catGap = 6
    const matBarH = 28
    const matGapInner = 2
    const matGapGroup = 8
    const supGap = 3

    // Column x ranges
    const catX = 20
    const catW = 150
    const matX = 320
    const matW = 230
    const supX = 710
    const supW = 190

    // --- Category bars ---
    const totalMaterials = materials.length || 1
    const totalCatGaps = (CATEGORY_KEYS.length - 1) * catGap
    const catAvailH = availableHeight - totalCatGaps

    const catBars: Record<string, BarPos> = {}
    let catYCursor = padTop

    CATEGORY_KEYS.forEach(catKey => {
      const count = (materialsByCategory[catKey] || []).length
      const h = Math.max(30, (count / totalMaterials) * catAvailH)
      catBars[catKey] = { x: catX, y: catYCursor, w: catW, h }
      catYCursor += h + catGap
    })

    // --- Material bars ---
    const matBars: Record<string, BarPos & { catKey: string }> = {}
    let matYCursor = padTop

    CATEGORY_KEYS.forEach((catKey, catIdx) => {
      if (catIdx > 0) matYCursor += matGapGroup
      const catMats = materialsByCategory[catKey] || []
      catMats.forEach((mat, i) => {
        if (i > 0) matYCursor += matGapInner
        matBars[mat.id] = { x: matX, y: matYCursor, w: matW, h: matBarH, catKey }
        matYCursor += matBarH
      })
    })

    // --- Supplier bars (grouped by region, then sorted by connections) ---
    const regionOrder = ['Americas', 'Europe', 'Asia-Pacific']
    const supRegion = (loc: string) => {
      if (/USA|San Jose|Detroit|Portland|Austin|Chicago/.test(loc)) return 'Americas'
      if (/Germany|Munich|Stuttgart|UK|Manchester|Netherlands|Amsterdam|France/.test(loc)) return 'Europe'
      return 'Asia-Pacific'
    }
    const sortedSuppliers = [...suppliers].sort((a, b) => {
      const ra = regionOrder.indexOf(supRegion(a.location))
      const rb = regionOrder.indexOf(supRegion(b.location))
      if (ra !== rb) return ra - rb
      const aCnt = (materialsForSupplier[a.id] || []).length
      const bCnt = (materialsForSupplier[b.id] || []).length
      return bCnt - aCnt
    })

    const supBars: Record<string, BarPos> = {}
    const regionHeaderYs: Record<string, number> = {}
    let supYCursor = padTop
    let lastRegion = ''

    sortedSuppliers.forEach(sup => {
      const region = supRegion(sup.location)
      if (region !== lastRegion) {
        regionHeaderYs[region] = supYCursor
        supYCursor += 14 // space for header
        lastRegion = region
      }
      const connections = (materialsForSupplier[sup.id] || []).length
      const h = Math.max(28, connections * 10)
      supBars[sup.id] = { x: supX, y: supYCursor, w: supW, h }
      supYCursor += h + supGap
    })

    // --- Bands: Category -> Material ---
    // Track slot usage for each bar edge
    const catRightSlots: Record<string, number> = {}
    const matLeftSlots: Record<string, number> = {}
    const matRightSlots: Record<string, number> = {}
    const supLeftSlots: Record<string, number> = {}

    CATEGORY_KEYS.forEach(k => { catRightSlots[k] = 0 })
    materials.forEach(m => { matLeftSlots[m.id] = 0; matRightSlots[m.id] = 0 })
    suppliers.forEach(s => { supLeftSlots[s.id] = 0 })

    const bandWidth = 6

    const catMatBands: SankeyBand[] = []

    CATEGORY_KEYS.forEach(catKey => {
      const catMats = materialsByCategory[catKey] || []
      const catBar = catBars[catKey]
      const totalBands = catMats.length
      const totalBandH = totalBands * bandWidth
      const catStartY = catBar.y + (catBar.h - totalBandH) / 2

      catMats.forEach((mat, i) => {
        const mBar = matBars[mat.id]
        if (!mBar) return

        const sourceSlotY = catStartY + i * bandWidth + bandWidth / 2
        const targetSlotY = mBar.y + mBar.h / 2

        catMatBands.push({
          key: `cm-${catKey}-${mat.id}`,
          sourceBar: catBar,
          targetBar: mBar,
          sourceSlotY,
          targetSlotY,
          bandWidth,
          color: CATEGORY_COLORS[catKey],
          opacity: 0.15,
          categoryKey: catKey,
          materialId: mat.id,
          supplierId: '',
        })

        catRightSlots[catKey] += bandWidth
        matLeftSlots[mat.id] += bandWidth
      })
    })

    // --- Bands: Material -> Supplier ---
    const matSupBands: SankeyBand[] = []

    // Precompute how many bands connect to each supplier so we can distribute slots
    const supBandCounts: Record<string, number> = {}
    suppliers.forEach(s => { supBandCounts[s.id] = 0 })
    materials.forEach(mat => {
      const matSups = suppliersForMaterial[mat.id] || []
      matSups.forEach(s => { supBandCounts[s.id]++ })
    })

    // Compute starting Y for each supplier's left-side slots
    const supSlotStartY: Record<string, number> = {}
    suppliers.forEach(s => {
      const bar = supBars[s.id]
      if (!bar) return
      const totalH = supBandCounts[s.id] * bandWidth
      supSlotStartY[s.id] = bar.y + (bar.h - totalH) / 2
    })

    const supSlotCursor: Record<string, number> = {}
    suppliers.forEach(s => { supSlotCursor[s.id] = 0 })

    materials.forEach(mat => {
      const mBar = matBars[mat.id]
      if (!mBar) return
      const matSups = suppliersForMaterial[mat.id] || []
      const totalBands = matSups.length
      const totalBandH = totalBands * bandWidth
      const matStartY = mBar.y + (mBar.h - totalBandH) / 2

      matSups.forEach((sup, i) => {
        const sBar = supBars[sup.id]
        if (!sBar) return

        const sourceSlotY = matStartY + i * bandWidth + bandWidth / 2
        const targetSlotY = (supSlotStartY[sup.id] || sBar.y) + supSlotCursor[sup.id] * bandWidth + bandWidth / 2
        supSlotCursor[sup.id]++

        matSupBands.push({
          key: `ms-${mat.id}-${sup.id}`,
          sourceBar: mBar,
          targetBar: sBar,
          sourceSlotY,
          targetSlotY,
          bandWidth,
          color: CATEGORY_COLORS[mBar.catKey],
          opacity: 0.12,
          categoryKey: mBar.catKey,
          materialId: mat.id,
          supplierId: sup.id,
        })
      })
    })

    return {
      catBars,
      matBars,
      supBars,
      sortedSuppliers,
      catMatBands,
      matSupBands,
      regionHeaderYs,
    }
  }, [materials, suppliers, edges, materialsByCategory, suppliersForMaterial, materialsForSupplier])

  // ── Highlight logic ───────────────────────────────────────────────────────

  const activeNode = hovered || selected

  const highlightedBandKeys = useMemo(() => {
    if (!activeNode) return null
    const keys = new Set<string>()

    if (activeNode.type === 'category') {
      const catKey = activeNode.key
      layout.catMatBands.forEach(b => { if (b.categoryKey === catKey) keys.add(b.key) })
      layout.matSupBands.forEach(b => { if (b.categoryKey === catKey) keys.add(b.key) })
    } else if (activeNode.type === 'material') {
      const matId = activeNode.id
      layout.catMatBands.forEach(b => { if (b.materialId === matId) keys.add(b.key) })
      layout.matSupBands.forEach(b => { if (b.materialId === matId) keys.add(b.key) })
    } else if (activeNode.type === 'supplier') {
      const supId = activeNode.id
      layout.matSupBands.forEach(b => {
        if (b.supplierId === supId) {
          keys.add(b.key)
          // Also highlight the cat->mat band for connected materials
          layout.catMatBands.forEach(cb => { if (cb.materialId === b.materialId) keys.add(cb.key) })
        }
      })
    } else if ((activeNode as any).type === 'edge') {
      const h = activeNode as any
      layout.matSupBands.forEach(b => {
        if (b.materialId === h.materialId && b.supplierId === h.supplierId) keys.add(b.key)
      })
      layout.catMatBands.forEach(b => {
        if (b.materialId === h.materialId) keys.add(b.key)
      })
    }

    return keys
  }, [activeNode, layout])

  // ── Bezier path builder ───────────────────────────────────────────────────

  function bandPath(band: SankeyBand): string {
    const x1 = band.sourceBar.x + band.sourceBar.w
    const y1 = band.sourceSlotY
    const x2 = band.targetBar.x
    const y2 = band.targetSlotY
    const cpx = (x1 + x2) / 2
    return `M ${x1},${y1 - band.bandWidth / 2}
            C ${cpx},${y1 - band.bandWidth / 2} ${cpx},${y2 - band.bandWidth / 2} ${x2},${y2 - band.bandWidth / 2}
            L ${x2},${y2 + band.bandWidth / 2}
            C ${cpx},${y2 + band.bandWidth / 2} ${cpx},${y1 + band.bandWidth / 2} ${x1},${y1 + band.bandWidth / 2}
            Z`
  }

  function bandOpacity(band: SankeyBand): number {
    if (!highlightedBandKeys) return band.opacity
    return highlightedBandKeys.has(band.key) ? 0.45 : 0.05
  }

  // ── Interaction ───────────────────────────────────────────────────────────

  function handleBarClick(node: SelectionType) {
    setSelected(prev => {
      if (prev && prev.type === node.type) {
        const prevId = prev.type === 'category' ? prev.key : prev.id
        const nodeId = node.type === 'category' ? node.key : node.id
        if (prevId === nodeId) return null
      }
      return node
    })
  }

  // ── Agent search ──────────────────────────────────────────────────────────

  async function handleSearchWithQuery(query: string) {
    if (!query.trim()) return
    setAgentLoading(true)
    setAgentResponse(null)
    try {
      const result = await sendChatMessage(`Using the supply network graph: ${query}`)
      setAgentResponse(result.response)
    } catch (err) {
      setAgentResponse(`Error: ${err instanceof Error ? err.message : 'Failed'}`)
    } finally {
      setAgentLoading(false)
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return
    setAgentLoading(true)
    setAgentResponse(null)
    try {
      const result = await sendChatMessage(`Using the supply network graph: ${searchQuery}`)
      setAgentResponse(result.response)
    } catch (err) {
      setAgentResponse(`Error: ${err instanceof Error ? err.message : 'Failed to get response'}`)
    } finally {
      setAgentLoading(false)
    }
  }

  // ── Detail panel data ─────────────────────────────────────────────────────

  const detailData = useMemo(() => {
    if (!selected) return null

    if (selected.type === 'category') {
      const catKey = selected.key
      const catMats = materialsByCategory[catKey] || []
      const allSups = new Set<string>()
      let totalRisk = 0
      let riskCount = 0
      catMats.forEach(m => {
        const sups = suppliersForMaterial[m.id] || []
        sups.forEach(s => {
          allSups.add(s.id)
          totalRisk += s.risk
          riskCount++
        })
      })
      return {
        type: 'category' as const,
        label: CATEGORY_LABELS[catKey] || catKey,
        color: CATEGORY_COLORS[catKey],
        materials: catMats,
        supplierCount: allSups.size,
        avgRisk: riskCount > 0 ? totalRisk / riskCount : 0,
      }
    }

    if (selected.type === 'material') {
      const mat = materials.find(m => m.id === selected.id)
      if (!mat) return null
      const sups = suppliersForMaterial[mat.id] || []
      return {
        type: 'material' as const,
        label: mat.name,
        color: CATEGORY_COLORS[mat.category],
        category: CATEGORY_LABELS[mat.category] || mat.category,
        criticality: mat.criticality,
        suppliers: sups,
        current_stock: mat.current_stock,
        reorder_point: mat.reorder_point,
        safety_stock: mat.safety_stock,
      }
    }

    if (selected.type === 'supplier') {
      const sup = suppliers.find(s => s.id === selected.id)
      if (!sup) return null
      const mats = materialsForSupplier[sup.id] || []
      // Merge performance data from API with Neptune vertex properties
      const perf = perfData[sup.id]
      const otd = sup.on_time_delivery_rate ?? perf?.on_time_delivery_rate
      const qs = sup.quality_score ?? perf?.quality_score
      const dr = sup.defect_rate ?? perf?.defect_rate
      const rt = sup.response_time_hours ?? perf?.response_time_hours
      return {
        type: 'supplier' as const,
        label: sup.name,
        color: riskColor(sup.risk),
        location: sup.location,
        rating: sup.rating,
        risk: sup.risk,
        materials: mats,
        on_time_delivery_rate: otd,
        quality_score_val: qs,
        defect_rate: dr,
        response_time_hours: rt,
        contract_type: sup.contract_type,
        payment_terms: sup.payment_terms,
        annual_value: sup.annual_value,
        contract_status: sup.contract_status,
        supplierId: sup.id,
      }
    }

    return null
  }, [selected, materials, suppliers, materialsByCategory, suppliersForMaterial, materialsForSupplier, perfData])

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
        background: '#f8fafc',
      }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: '#3b82f6' }} />
        <span style={{ fontSize: 13, fontWeight: 500, color: '#64748b' }}>Loading supply network...</span>
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', width: '100%', height: '100%',
      overflow: 'hidden', position: 'relative',
      background: '#ffffff',
    }}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes slideInPanel { from { transform: translateX(100%); } to { transform: translateX(0); } }
        .sankey-band { transition: opacity 0.25s ease; }
        .sankey-bar { transition: opacity 0.2s ease, filter 0.2s ease; cursor: pointer; }
        .sankey-bar:hover { filter: brightness(1.06); }
      `}</style>

      {/* ── Header ── */}
      <div style={{
        padding: '10px 20px', borderBottom: '1px solid #e2e8f0',
        background: '#fff', flexShrink: 0,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: 16, fontWeight: 700, color: '#1e293b' }}>Supply Network</span>
          <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 12 }}>
            {suppliers.length} suppliers · {materials.length} materials · {edges.length} relationships
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: '#94a3b8', marginRight: 4 }}>Highlight by:</span>
          {[
            { id: 'otd', label: 'On-Time Delivery', icon: '🚚', bounds: '🟢 >95% 🟡 >90% ⬜ <90%' },
            { id: 'quality', label: 'Quality', icon: '⭐', bounds: '🟢 >8.5 🟡 >7.0 ⬜ <7.0' },
            { id: 'defect', label: 'Defect Rate', icon: '⚠️', bounds: '🟢 <0.5% 🟡 <2% ⬜ >2%' },
            { id: 'risk', label: 'Risk', icon: '🛡️', bounds: '🟢 <2.5 🟡 <3.5 ⬜ >3.5' },
            { id: 'contract', label: 'Contracts', icon: '📋', bounds: '🟢 Active ⬜ None' },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setPerfFilters(prev => {
                const next = new Set(prev)
                if (next.has(f.id)) next.delete(f.id); else next.add(f.id)
                return next
              })}
              style={{
                padding: '4px 10px', borderRadius: 16, fontSize: 11, fontWeight: 600,
                border: perfFilters.has(f.id) ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                background: perfFilters.has(f.id) ? '#eff6ff' : '#fff',
                color: perfFilters.has(f.id) ? '#1d4ed8' : '#64748b',
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}
            >
              {f.icon} {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active filter criteria bar */}
      {perfFilters.size > 0 && (
        <div style={{
          padding: '6px 20px', background: '#f0f9ff', borderBottom: '1px solid #bae6fd',
          display: 'flex', gap: 16, fontSize: 11, color: '#0369a1', flexShrink: 0, flexWrap: 'wrap',
        }}>
          <span style={{ fontWeight: 600 }}>Active filters:</span>
          {[
            { id: 'otd', label: 'On-Time Delivery', bounds: '🟢 ≥95%  🟡 ≥90%  ⬜ <90%' },
            { id: 'quality', label: 'Quality Score', bounds: '🟢 ≥8.5  🟡 ≥7.0  ⬜ <7.0' },
            { id: 'defect', label: 'Defect Rate', bounds: '🟢 <0.5%  🟡 <2%  ⬜ ≥2%' },
            { id: 'risk', label: 'Risk Score', bounds: '🟢 <2.5  🟡 <3.5  ⬜ ≥3.5' },
            { id: 'contract', label: 'Contract', bounds: '🟢 Active  ⬜ None' },
          ].filter(f => perfFilters.has(f.id)).map(f => (
            <span key={f.id} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <strong>{f.label}:</strong> {f.bounds}
            </span>
          ))}
        </div>
      )}

      {/* ── Sankey + Detail panel ──────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>

        {/* ── SVG Sankey ─────────────────────────────────────────────── */}
        <div
          style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: 0 }}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect()
            setTooltipPos({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 10 })
          }}
        >
          <svg
            viewBox="0 0 920 740"
            width="100%"
            height="100%"
            preserveAspectRatio="xMidYMid meet"
            style={{ display: 'block', background: '#ffffff' }}
          >
            {/* Column headers */}
            <text x={95} y={30} textAnchor="middle" fontSize={13} fontWeight={700} fill="#1e293b">Categories</text>
            <text x={460} y={30} textAnchor="middle" fontSize={13} fontWeight={700} fill="#1e293b">Parts / Materials</text>
            <text x={815} y={30} textAnchor="middle" fontSize={13} fontWeight={700} fill="#1e293b">Suppliers</text>

            {/* ── Bands: Category -> Material ────────────────────────── */}
            {layout.catMatBands.map(band => (
              <path
                key={band.key}
                className="sankey-band"
                d={bandPath(band)}
                fill={band.color}
                opacity={bandOpacity(band)}
                onMouseEnter={() => setHovered({ type: 'category', key: band.categoryKey })}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              />
            ))}

            {/* ── Bands: Material -> Supplier ────────────────────────── */}
            {layout.matSupBands.map(band => (
              <path
                key={band.key}
                className="sankey-band"
                d={bandPath(band)}
                fill={band.color}
                opacity={bandOpacity(band)}
                onMouseEnter={(e) => {
                  setHovered({ type: 'edge', materialId: band.materialId, supplierId: band.supplierId } as any)
                }}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              />
            ))}

            {/* ── Category bars (left) ───────────────────────────────── */}
            {CATEGORY_KEYS.map(catKey => {
              const bar = layout.catBars[catKey]
              if (!bar) return null
              const color = CATEGORY_COLORS[catKey]
              const label = CATEGORY_LABELS[catKey]
              const count = (materialsByCategory[catKey] || []).length
              const isActive = activeNode?.type === 'category' && activeNode.key === catKey
              const dimmed = highlightedBandKeys && !isActive

              return (
                <g
                  key={catKey}
                  className="sankey-bar"
                  opacity={dimmed ? 0.4 : 1}
                  onMouseEnter={() => setHovered({ type: 'category', key: catKey })}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => handleBarClick({ type: 'category', key: catKey })}
                >
                  <rect
                    x={bar.x} y={bar.y} width={bar.w} height={bar.h}
                    rx={4} fill={color}
                    stroke={isActive ? '#1e293b' : 'none'}
                    strokeWidth={isActive ? 2 : 0}
                  />
                  <text
                    x={bar.x + bar.w / 2}
                    y={bar.y + bar.h / 2 - 7}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={13} fontWeight={700} fill="#fff"
                    style={{ pointerEvents: 'none' }}
                  >
                    {label}
                  </text>
                  <text
                    x={bar.x + bar.w / 2}
                    y={bar.y + bar.h / 2 + 8}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={11} fill="#fff" opacity={0.85}
                    style={{ pointerEvents: 'none' }}
                  >
                    {count} materials
                  </text>
                </g>
              )
            })}

            {/* ── Material bars (middle) ─────────────────────────────── */}
            {materials.map(mat => {
              const bar = layout.matBars[mat.id]
              if (!bar) return null
              const catColor = CATEGORY_COLORS[mat.category] || '#94a3b8'
              const fillColor = lightenHex(catColor, 0.25)
              const isActive = activeNode?.type === 'material' && activeNode.id === mat.id
              const isConnected = highlightedBandKeys
                ? layout.catMatBands.some(b => b.materialId === mat.id && highlightedBandKeys.has(b.key))
                  || layout.matSupBands.some(b => b.materialId === mat.id && highlightedBandKeys.has(b.key))
                : false
              const dimmed = highlightedBandKeys && !isActive && !isConnected

              return (
                <g
                  key={mat.id}
                  className="sankey-bar"
                  opacity={dimmed ? 0.3 : 1}
                  onMouseEnter={() => setHovered({ type: 'material', id: mat.id })}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => handleBarClick({ type: 'material', id: mat.id })}
                >
                  <rect
                    x={bar.x} y={bar.y} width={bar.w} height={bar.h}
                    rx={3} fill={fillColor}
                    stroke={isActive ? '#1e40af' : catColor}
                    strokeWidth={isActive ? 2 : 0.5}
                  />
                  {/* Criticality dot inside bar (left) */}
                  <circle
                    cx={bar.x + 10}
                    cy={bar.y + bar.h / 2}
                    r={4}
                    fill="#fff" opacity={0.9}
                    stroke={CRITICALITY_COLORS[mat.criticality] || '#94a3b8'}
                    strokeWidth={2}
                    style={{ pointerEvents: 'none' }}
                  />
                  {/* Label inside bar */}
                  <text
                    x={bar.x + 20}
                    y={bar.y + bar.h / 2}
                    textAnchor="start" dominantBaseline="middle"
                    fontSize={10} fontWeight={600} fill="#fff"
                    style={{ pointerEvents: 'none' }}
                  >
                    {mat.name}
                  </text>
                </g>
              )
            })}

            {/* ── Supplier region headers ──────────────────────────── */}
            {Object.entries(layout.regionHeaderYs).map(([region, y]) => (
              <text key={`rh-${region}`}
                x={layout.supBars[layout.sortedSuppliers[0]?.id]?.x || 700}
                y={y + 10}
                fontSize={10} fontWeight={700} fill="#64748b"
                style={{ pointerEvents: 'none', letterSpacing: '1.5px' }}
              >{region.toUpperCase()}</text>
            ))}
            {layout.sortedSuppliers.map(sup => {
              const bar = layout.supBars[sup.id]
              if (!bar) return null
              const perf = perfData[sup.id]
              const otdVal = sup.on_time_delivery_rate ?? perf?.on_time_delivery_rate
              const qsVal = sup.quality_score ?? perf?.quality_score
              const drVal = sup.defect_rate ?? perf?.defect_rate

              // Additive filters: supplier must pass ALL active filters
              let color = riskColor(sup.risk)
              let filterDimmed = false

              if (perfFilters.size > 0) {
                let passes = true
                let bestColor = '#22c55e'

                if (perfFilters.has('otd')) {
                  if (otdVal == null || otdVal < 90) passes = false
                  else if (otdVal < 95) bestColor = '#f59e0b'
                }
                if (perfFilters.has('quality')) {
                  if (qsVal == null || qsVal < 7) passes = false
                  else if (qsVal < 8.5) bestColor = '#f59e0b'
                }
                if (perfFilters.has('defect')) {
                  if (drVal == null || drVal > 2) passes = false
                  else if (drVal > 1) bestColor = '#f59e0b'
                }
                if (perfFilters.has('risk')) {
                  if (sup.risk > 3.5) passes = false
                  else if (sup.risk > 2.5) bestColor = '#f59e0b'
                }
                if (perfFilters.has('contract')) {
                  if (sup.contract_status !== 'Active') passes = false
                }

                if (passes) {
                  color = bestColor
                } else {
                  color = '#cbd5e1' // medium gray — clearly different from active
                  filterDimmed = true
                }
              }

              const isActive = activeNode?.type === 'supplier' && activeNode.id === sup.id
              const isConnected = highlightedBandKeys
                ? layout.matSupBands.some(b => b.supplierId === sup.id && highlightedBandKeys.has(b.key))
                : false
              const dimmed = (highlightedBandKeys && !isActive && !isConnected) || filterDimmed

              // Override bar opacity for filtered-out suppliers
              const barOpacity = filterDimmed ? 0.4 : (dimmed ? 0.3 : 0.85)

              return (
                <g
                  key={sup.id}
                  className="sankey-bar"
                  opacity={dimmed ? 0.3 : 1}
                  onMouseEnter={() => setHovered({ type: 'supplier', id: sup.id })}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => handleBarClick({ type: 'supplier', id: sup.id })}
                >
                  <rect
                    x={bar.x} y={bar.y} width={bar.w} height={bar.h}
                    rx={3} fill={color}
                    stroke={isActive ? '#1e293b' : filterDimmed ? '#94a3b8' : 'none'}
                    strokeWidth={isActive ? 2 : filterDimmed ? 1 : 0}
                    strokeDasharray={filterDimmed ? '4,3' : 'none'}
                    opacity={barOpacity}
                  />
                  {/* Label inside bar */}
                  <text
                    x={bar.x + 6}
                    y={bar.y + bar.h / 2 + (bar.h > 30 ? -5 : 0)}
                    textAnchor="start" dominantBaseline="middle"
                    fontSize={bar.h > 25 ? 11 : 9} fontWeight={600} fill={filterDimmed ? '#64748b' : '#fff'}
                    style={{ pointerEvents: 'none' }}
                  >
                    {REGION_FLAGS[sup.location] || ''} {sup.name.split(' ').slice(0, 2).join(' ')}
                  </text>
                  {bar.h > 30 && (
                    <text
                      x={bar.x + 6}
                      y={bar.y + bar.h / 2 + 9}
                      textAnchor="start" dominantBaseline="middle"
                      fontSize={9} fill="rgba(255,255,255,0.7)"
                      style={{ pointerEvents: 'none' }}
                    >
                      {sup.location}
                    </text>
                  )}
                  {/* Contract & defect indicators */}
                  {sup.contract_status?.toLowerCase() === 'active' && (
                    <circle
                      cx={bar.x + bar.w - 12}
                      cy={bar.y + bar.h / 2 - (sup.defect_rate != null && sup.defect_rate > 1.5 ? 5 : 0)}
                      r={4}
                      fill="#22c55e"
                      stroke="#fff" strokeWidth={1}
                      style={{ pointerEvents: 'none' }}
                    />
                  )}
                  {sup.defect_rate != null && sup.defect_rate > 1.5 && (
                    <text
                      x={bar.x + bar.w - 12}
                      y={bar.y + bar.h / 2 + (sup.contract_status?.toLowerCase() === 'active' ? 7 : 0)}
                      textAnchor="middle" dominantBaseline="middle"
                      fontSize={10} fill="#ef4444"
                      style={{ pointerEvents: 'none' }}
                    >
                      ⚠
                    </text>
                  )}
                </g>
              )
            })}
          </svg>

          {/* Hover tooltip */}
          {hovered && !selected && (
            <div style={{
              position: 'absolute', left: tooltipPos.x, top: tooltipPos.y - 40,
              background: '#0f172a', color: '#f1f5f9', padding: '10px 16px',
              borderRadius: 10, fontSize: 13, fontWeight: 500, pointerEvents: 'none',
              zIndex: 100, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
              maxWidth: 400, border: '1px solid #334155',
            }}>
              {(() => {
                if ((hovered as any).type === 'edge') {
                  const h = hovered as any
                  const mat = materials.find(m => m.id === h.materialId)
                  const sup = suppliers.find(s => s.id === h.supplierId)
                  const edge = edges.find(e => e.from === h.supplierId && e.to === h.materialId)
                  if (!mat || !sup) return null
                  return (
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>{sup.name} → {mat.name}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 12 }}>
                        <span style={{ color: '#94a3b8' }}>Category</span>
                        <span>{CATEGORY_LABELS[mat.category] || mat.category}</span>
                        <span style={{ color: '#94a3b8' }}>Criticality</span>
                        <span style={{ color: CRITICALITY_COLORS[mat.criticality], fontWeight: 600 }}>{mat.criticality}</span>
                        <span style={{ color: '#94a3b8' }}>Supplier Risk</span>
                        <span style={{ color: riskColor(sup.risk), fontWeight: 600 }}>{sup.risk.toFixed(1)}/10</span>
                        <span style={{ color: '#94a3b8' }}>Location</span>
                        <span>{sup.location}</span>
                      </div>
                    </div>
                  )
                }
                if (hovered.type === 'supplier') {
                  const sup = suppliers.find(s => s.id === hovered.id)
                  if (!sup) return null
                  const p = perfData[sup.id]
                  const otd = sup.on_time_delivery_rate ?? p?.on_time_delivery_rate
                  const qs = sup.quality_score ?? p?.quality_score
                  return (
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 6, fontSize: 14 }}>{sup.name}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 12 }}>
                        <span style={{ color: '#94a3b8' }}>Location</span>
                        <span>{sup.location}</span>
                        <span style={{ color: '#94a3b8' }}>Risk</span>
                        <span style={{ color: riskColor(sup.risk), fontWeight: 600 }}>{sup.risk.toFixed(1)}/10</span>
                        {otd != null && <>
                          <span style={{ color: '#94a3b8' }}>On-Time Delivery</span>
                          <span style={{ color: otdColor(otd), fontWeight: 600 }}>{otd.toFixed(1)}%</span>
                        </>}
                        {qs != null && <>
                          <span style={{ color: '#94a3b8' }}>Quality</span>
                          <span style={{ color: qualityColor(qs), fontWeight: 600 }}>{qs.toFixed(1)}/10</span>
                        </>}
                        {sup.contract_status && <>
                          <span style={{ color: '#94a3b8' }}>Contract</span>
                          <span style={{ color: '#22c55e', fontWeight: 600 }}>{sup.contract_type || 'Active'}</span>
                        </>}
                        <span style={{ color: '#94a3b8' }}>Materials</span>
                        <span>{(materialsForSupplier[sup.id] || []).length}</span>
                      </div>
                    </div>
                  )
                }
                if (hovered.type === 'material') {
                  const mat = materials.find(m => m.id === hovered.id)
                  if (!mat) return null
                  const inv = inventoryStatus(mat.current_stock, mat.reorder_point, mat.safety_stock)
                  return (
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 6, fontSize: 14 }}>{mat.name}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 12 }}>
                        <span style={{ color: '#94a3b8' }}>Category</span>
                        <span>{CATEGORY_LABELS[mat.category]}</span>
                        <span style={{ color: '#94a3b8' }}>Criticality</span>
                        <span style={{ color: CRITICALITY_COLORS[mat.criticality], fontWeight: 600 }}>{mat.criticality}</span>
                        {mat.current_stock != null && <>
                          <span style={{ color: '#94a3b8' }}>Stock</span>
                          <span style={{ color: inv.color, fontWeight: 600 }}>{mat.current_stock} ({inv.label})</span>
                        </>}
                        <span style={{ color: '#94a3b8' }}>Suppliers</span>
                        <span>{(suppliersForMaterial[mat.id] || []).length}</span>
                      </div>
                    </div>
                  )
                }
                if (hovered.type === 'category') {
                  const mats = materialsByCategory[hovered.key] || []
                  return (
                    <span>
                      <strong>{CATEGORY_LABELS[hovered.key]}</strong>
                      <span style={{ color: '#94a3b8' }}> · {mats.length} materials</span>
                    </span>
                  )
                }
                return null
              })()}
            </div>
          )}

          {/* Legend */}
          <div style={{
            position: 'absolute', bottom: 12, left: 16,
            display: 'flex', gap: 16, fontSize: 11, color: '#64748b',
            background: 'rgba(255,255,255,0.95)', padding: '6px 14px',
            borderRadius: 8, border: '1px solid #e2e8f0',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontWeight: 600 }}>Risk:</span>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />Low
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', display: 'inline-block', marginLeft: 4 }} />Medium
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block', marginLeft: 4 }} />High
            </span>
            <span style={{ color: '#cbd5e1' }}>|</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontWeight: 600 }}>Criticality:</span>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} />Critical
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', display: 'inline-block', marginLeft: 4 }} />High
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#eab308', display: 'inline-block', marginLeft: 4 }} />Med
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block', marginLeft: 4 }} />Low
            </span>
          </div>
        </div>

        {/* ── Detail panel ────────────────────────────────────────────── */}
        {detailData && (
          <div style={{
            width: 280, flexShrink: 0,
            background: '#fff',
            borderLeft: '1px solid #e2e8f0',
            boxShadow: '-4px 0 20px rgba(0,0,0,0.06)',
            animation: 'slideInPanel 0.2s ease-out',
            display: 'flex', flexDirection: 'column',
            overflow: 'hidden',
          }}>
            {/* Panel header */}
            <div style={{
              padding: '14px 16px', flexShrink: 0,
              background: detailData.color,
              color: '#fff',
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: 6,
              }}>
                <span style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px', opacity: 0.8 }}>
                  {detailData.type}
                </span>
                <button
                  onClick={() => setSelected(null)}
                  style={{
                    background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: 4,
                    color: '#fff', fontSize: 16, cursor: 'pointer', padding: '2px 8px',
                    lineHeight: 1,
                  }}
                >
                  {'\u00d7'}
                </button>
              </div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>
                {detailData.label}
              </div>
            </div>

            {/* Panel body */}
            <div style={{ flex: 1, overflow: 'auto', padding: '14px 16px' }}>

              {/* Category detail */}
              {detailData.type === 'category' && (() => {
                const d = detailData as { type: 'category'; materials: MaterialData[]; supplierCount: number; avgRisk: number }
                return (
                  <>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                      <DetailRow label="Materials" value={String(d.materials.length)} />
                      <DetailRow label="Suppliers" value={String(d.supplierCount)} />
                      <DetailRow
                        label="Avg Risk"
                        value={d.avgRisk.toFixed(1)}
                        valueColor={riskColor(d.avgRisk)}
                      />
                    </div>
                    <div style={{
                      fontSize: 11, fontWeight: 700, color: '#1e293b',
                      marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                    }}>
                      Materials ({d.materials.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {d.materials.map(m => (
                        <button
                          key={m.id}
                          onClick={() => setSelected({ type: 'material', id: m.id })}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '7px 10px', borderRadius: 6, textAlign: 'left',
                            border: '1px solid #f1f5f9', background: '#fafbfc',
                            cursor: 'pointer', width: '100%',
                          }}
                        >
                          <div style={{
                            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                            background: CRITICALITY_COLORS[m.criticality] || '#94a3b8',
                          }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{m.name}</div>
                            <div style={{ fontSize: 10, color: '#94a3b8' }}>
                              <span style={{ color: CRITICALITY_COLORS[m.criticality], fontWeight: 600 }}>{m.criticality}</span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </>
                )
              })()}

              {/* Material detail */}
              {detailData.type === 'material' && (() => {
                const d = detailData as {
                  type: 'material'; category: string; criticality: string; suppliers: SupplierData[];
                  current_stock?: number; reorder_point?: number; safety_stock?: number;
                }
                const hasInventory = d.current_stock != null || d.reorder_point != null || d.safety_stock != null
                const invStatus = inventoryStatus(d.current_stock, d.reorder_point, d.safety_stock)
                // For the stock bar, compute proportions relative to max of (stock, reorder * 1.5)
                const barMax = Math.max(d.current_stock ?? 0, (d.reorder_point ?? 0) * 1.5, (d.safety_stock ?? 0) * 2)
                return (
                  <>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                      <DetailRow label="Category" value={d.category} />
                      <DetailRow
                        label="Criticality"
                        value={d.criticality}
                        valueColor={CRITICALITY_COLORS[d.criticality]}
                      />
                      <DetailRow label="Suppliers" value={String(d.suppliers.length)} />
                    </div>

                    {/* Inventory section */}
                    {hasInventory && (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{
                          fontSize: 11, fontWeight: 700, color: '#1e293b',
                          marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                        }}>
                          Inventory
                        </div>
                        <div style={{
                          background: '#f8fafc', border: '1px solid #e2e8f0',
                          borderRadius: 8, padding: '10px 12px',
                          display: 'flex', flexDirection: 'column', gap: 8,
                        }}>
                          {d.current_stock != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Current Stock</span>
                              <span style={{ fontWeight: 700, color: '#1e293b' }}>{d.current_stock} units</span>
                            </div>
                          )}
                          {d.reorder_point != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Reorder Point</span>
                              <span style={{ fontWeight: 600, color: '#64748b' }}>{d.reorder_point} units</span>
                            </div>
                          )}
                          {d.safety_stock != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Safety Stock</span>
                              <span style={{ fontWeight: 600, color: '#64748b' }}>{d.safety_stock} units</span>
                            </div>
                          )}
                          {/* Stock level bar */}
                          {barMax > 0 && (
                            <div style={{ position: 'relative', height: 16, background: '#e2e8f0', borderRadius: 4, marginTop: 2 }}>
                              {/* Safety stock zone (red line) */}
                              {d.safety_stock != null && (
                                <div style={{
                                  position: 'absolute', left: `${(d.safety_stock / barMax) * 100}%`,
                                  top: 0, bottom: 0, width: 2, background: '#ef4444', borderRadius: 1, zIndex: 2,
                                }} />
                              )}
                              {/* Reorder point (yellow line) */}
                              {d.reorder_point != null && (
                                <div style={{
                                  position: 'absolute', left: `${(d.reorder_point / barMax) * 100}%`,
                                  top: 0, bottom: 0, width: 2, background: '#f59e0b', borderRadius: 1, zIndex: 2,
                                }} />
                              )}
                              {/* Current stock fill */}
                              {d.current_stock != null && (
                                <div style={{
                                  height: '100%', borderRadius: 4,
                                  width: `${Math.min(100, (d.current_stock / barMax) * 100)}%`,
                                  background: invStatus.color, opacity: 0.6,
                                }} />
                              )}
                            </div>
                          )}
                          {/* Status badge */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                            <span style={{ color: '#64748b' }}>Status</span>
                            <span style={{
                              fontWeight: 700, fontSize: 10,
                              padding: '2px 8px', borderRadius: 10,
                              background: invStatus.color === '#22c55e' ? '#dcfce7' : invStatus.color === '#f59e0b' ? '#fef3c7' : '#fee2e2',
                              color: invStatus.color,
                            }}>
                              {invStatus.label}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div style={{
                      fontSize: 11, fontWeight: 700, color: '#1e293b',
                      marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                    }}>
                      Suppliers ({d.suppliers.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {d.suppliers.map(s => (
                        <button
                          key={s.id}
                          onClick={() => setSelected({ type: 'supplier', id: s.id })}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '7px 10px', borderRadius: 6, textAlign: 'left',
                            border: '1px solid #f1f5f9', background: '#fafbfc',
                            cursor: 'pointer', width: '100%',
                          }}
                        >
                          <div style={{
                            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                            background: riskColor(s.risk),
                          }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{s.name}</div>
                            <div style={{ fontSize: 10, color: '#94a3b8' }}>
                              {s.location}
                              {' \u2022 '}
                              <span style={{ color: riskColor(s.risk) }}>Risk {s.risk.toFixed(1)}</span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </>
                )
              })()}

              {/* Supplier detail */}
              {detailData.type === 'supplier' && (() => {
                const d = detailData as {
                  type: 'supplier'; location: string; rating: number; risk: number;
                  materials: MaterialData[]; supplierId: string;
                  on_time_delivery_rate?: number; quality_score_val?: number;
                  defect_rate?: number; response_time_hours?: number;
                  contract_type?: string; payment_terms?: string;
                  annual_value?: number; contract_status?: string;
                }
                const hasPerf = d.on_time_delivery_rate != null || d.quality_score_val != null
                const hasContract = d.contract_type != null || d.payment_terms != null || d.annual_value != null
                return (
                  <>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                      <DetailRow label="Location" value={d.location} />
                      <DetailRow
                        label="Rating"
                        value={`${renderStars(d.rating)} (${d.rating.toFixed(1)})`}
                      />
                      <DetailRow
                        label="Risk Score"
                        value={d.risk.toFixed(1)}
                        valueColor={riskColor(d.risk)}
                      />
                    </div>

                    {/* Performance section */}
                    {hasPerf && (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{
                          fontSize: 11, fontWeight: 700, color: '#1e293b',
                          marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                        }}>
                          Performance
                        </div>
                        <div style={{
                          background: '#f8fafc', border: '1px solid #e2e8f0',
                          borderRadius: 8, padding: '10px 12px',
                          display: 'flex', flexDirection: 'column', gap: 10,
                        }}>
                          {d.on_time_delivery_rate != null && (
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                                <span style={{ color: '#64748b' }}>On-Time Delivery</span>
                                <span style={{ fontWeight: 700, color: otdColor(d.on_time_delivery_rate) }}>
                                  {d.on_time_delivery_rate.toFixed(1)}%
                                </span>
                              </div>
                              <div style={{ height: 6, background: '#e2e8f0', borderRadius: 3 }}>
                                <div style={{
                                  height: '100%', borderRadius: 3, width: `${Math.min(100, d.on_time_delivery_rate)}%`,
                                  background: otdColor(d.on_time_delivery_rate),
                                }} />
                              </div>
                            </div>
                          )}
                          {d.quality_score_val != null && (
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                                <span style={{ color: '#64748b' }}>Quality Score</span>
                                <span style={{ fontWeight: 700, color: qualityColor(d.quality_score_val) }}>
                                  {d.quality_score_val.toFixed(1)}/10
                                </span>
                              </div>
                              <div style={{ height: 6, background: '#e2e8f0', borderRadius: 3 }}>
                                <div style={{
                                  height: '100%', borderRadius: 3, width: `${d.quality_score_val * 10}%`,
                                  background: qualityColor(d.quality_score_val),
                                }} />
                              </div>
                            </div>
                          )}
                          {d.defect_rate != null && (
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                                <span style={{ color: '#64748b' }}>Defect Rate</span>
                                <span style={{ fontWeight: 700, color: defectColor(d.defect_rate) }}>
                                  {d.defect_rate.toFixed(2)}%
                                </span>
                              </div>
                              <div style={{ height: 6, background: '#e2e8f0', borderRadius: 3 }}>
                                <div style={{
                                  height: '100%', borderRadius: 3, width: `${Math.min(100, d.defect_rate * 20)}%`,
                                  background: defectColor(d.defect_rate),
                                }} />
                              </div>
                            </div>
                          )}
                          {d.response_time_hours != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Response Time</span>
                              <span style={{ fontWeight: 700, color: '#1e293b' }}>{d.response_time_hours}h</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Contract section */}
                    {hasContract && (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{
                          fontSize: 11, fontWeight: 700, color: '#1e293b',
                          marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                        }}>
                          Contract
                        </div>
                        <div style={{
                          background: '#f8fafc', border: '1px solid #e2e8f0',
                          borderRadius: 8, padding: '10px 12px',
                          display: 'flex', flexDirection: 'column', gap: 6,
                        }}>
                          {d.contract_type != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Type</span>
                              <span style={{ fontWeight: 600, color: '#1e293b' }}>{d.contract_type}</span>
                            </div>
                          )}
                          {d.payment_terms != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Payment Terms</span>
                              <span style={{ fontWeight: 600, color: '#1e293b' }}>{d.payment_terms}</span>
                            </div>
                          )}
                          {d.annual_value != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                              <span style={{ color: '#64748b' }}>Annual Value</span>
                              <span style={{ fontWeight: 600, color: '#1e293b' }}>
                                ${d.annual_value >= 1_000_000 ? `${(d.annual_value / 1_000_000).toFixed(1)}M` : `${(d.annual_value / 1_000).toFixed(0)}K`}
                              </span>
                            </div>
                          )}
                          {d.contract_status != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, alignItems: 'center' }}>
                              <span style={{ color: '#64748b' }}>Status</span>
                              <span style={{
                                fontWeight: 700, fontSize: 10,
                                padding: '2px 8px', borderRadius: 10,
                                background: d.contract_status.toLowerCase() === 'active' ? '#dcfce7' : '#fee2e2',
                                color: d.contract_status.toLowerCase() === 'active' ? '#16a34a' : '#dc2626',
                              }}>
                                {d.contract_status}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    <div style={{
                      fontSize: 11, fontWeight: 700, color: '#1e293b',
                      marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.3px',
                    }}>
                      Materials Supplied ({d.materials.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {d.materials.map(m => (
                        <button
                          key={m.id}
                          onClick={() => setSelected({ type: 'material', id: m.id })}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '7px 10px', borderRadius: 6, textAlign: 'left',
                            border: '1px solid #f1f5f9', background: '#fafbfc',
                            cursor: 'pointer', width: '100%',
                          }}
                        >
                          <div style={{
                            width: 8, height: 8, borderRadius: 2, flexShrink: 0,
                            background: CATEGORY_COLORS[m.category] || '#94a3b8',
                          }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{m.name}</div>
                            <div style={{ fontSize: 10, color: '#94a3b8' }}>
                              {CATEGORY_LABELS[m.category] || m.category}
                              {' \u2022 '}
                              <span style={{ color: CRITICALITY_COLORS[m.criticality], fontWeight: 600 }}>{m.criticality}</span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </>
                )
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function DetailRow({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{
      padding: '6px 10px', borderRadius: 6,
      background: '#f8fafc', border: '1px solid #f1f5f9',
    }}>
      <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 1 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 700, color: valueColor || '#1e293b' }}>{value}</div>
    </div>
  )
}
