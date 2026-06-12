import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import type { OptimizationSolution } from '../data/realData'

interface ExecutiveDashboardProps {
  solutions: OptimizationSolution[]
  selectedSolution: string | null
}

const SOLUTION_COLORS: Record<string, string> = {
  'Cost-Optimized': '#22c55e',
  'Balanced': '#3b82f6',
  'Risk-Diversified': '#a855f7',
}

const PIE_COLORS = [
  '#3b82f6',
  '#22c55e',
  '#a855f7',
  '#f97316',
  '#ef4444',
  '#14b8a6',
  '#eab308',
  '#ec4899',
  '#6366f1',
  '#64748b',
]

const CATEGORY_LABELS: Record<string, string> = {
  BAT: 'Battery',
  MOT: 'Motor',
  FRM: 'Frame',
  ELC: 'Electronics',
  STD: 'Standard',
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
  return `$${value.toFixed(0)}`
}

function getCategoryFromMaterialId(materialId: string): string {
  const match = materialId.match(/^MAT-(\w{3})/)
  return match ? match[1] : 'OTHER'
}

export default function ExecutiveDashboard({
  solutions,
  selectedSolution,
}: ExecutiveDashboardProps) {
  const selected =
    solutions.find((s) => s.id === selectedSolution) ?? solutions[0]
  if (!selected || solutions.length === 0) return null

  const costOptimizedSolution = solutions.find((s) => s.name === 'Cost-Optimized')
  const riskDiversifiedSolution = solutions.find((s) => s.name === 'Risk-Diversified')

  // KPI calculations
  const totalProcurementValue = selected.totalCost
  const savingsVsRiskDiversified =
    costOptimizedSolution && riskDiversifiedSolution
      ? riskDiversifiedSolution.totalCost - costOptimizedSolution.totalCost
      : 0
  const avgRiskScore =
    solutions.reduce((sum, s) => sum + s.riskScore, 0) / solutions.length
  const avgLeadTime =
    selected.allocations.reduce((sum, a) => sum + a.leadTimeDays, 0) /
    selected.allocations.length

  // Cost comparison data
  const costComparisonData = solutions.map((s) => ({
    name: s.name,
    cost: s.totalCost,
    fill: SOLUTION_COLORS[s.name] ?? '#64748b',
  }))

  // Supplier spend distribution for selected solution
  const supplierSpendMap = new Map<string, number>()
  selected.allocations.forEach((a) => {
    const current = supplierSpendMap.get(a.supplierName) ?? 0
    supplierSpendMap.set(a.supplierName, current + a.totalCost)
  })
  const supplierSpendData = Array.from(supplierSpendMap.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  // Material cost breakdown by category
  const categorySpendMap = new Map<string, number>()
  selected.allocations.forEach((a) => {
    const catKey = getCategoryFromMaterialId(a.materialId)
    const label = CATEGORY_LABELS[catKey] ?? catKey
    const current = categorySpendMap.get(label) ?? 0
    categorySpendMap.set(label, current + a.totalCost)
  })
  const materialCostData = Array.from(categorySpendMap.entries())
    .map(([category, cost]) => ({ category, cost }))
    .sort((a, b) => b.cost - a.cost)

  const kpis = [
    {
      label: 'Total Procurement Value',
      value: formatCurrency(totalProcurementValue),
      sub: `${selected.name} solution`,
    },
    {
      label: 'Savings vs Risk-Diversified',
      value: formatCurrency(savingsVsRiskDiversified),
      sub: 'Cost-Optimized to Risk-Diversified spread',
    },
    {
      label: 'Avg Supplier Risk Score',
      value: avgRiskScore.toFixed(1),
      sub: `Across ${solutions.length} solutions`,
    },
    {
      label: 'Avg Lead Time',
      value: `${Math.round(avgLeadTime)} days`,
      sub: `${selected.name} allocations`,
    },
  ]

  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#1e293b' }}>Executive Summary</div>
        <button onClick={() => window.print()} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 8, border: '1px solid #e2e8f0',
          background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: '#475569',
        }}>
          <span style={{ fontSize: 14 }}>🖨</span> Export PDF
        </button>
      </div>

      {/* KPI Cards */}
      <div style={styles.kpiRow}>
        {kpis.map((kpi) => (
          <div key={kpi.label} style={styles.kpiCard}>
            <div style={styles.kpiLabel}>{kpi.label}</div>
            <div style={styles.kpiValue}>{kpi.value}</div>
            <div style={styles.kpiSub}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={styles.chartsRow}>
        {/* Cost Comparison Bar Chart */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Cost Comparison by Solution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={costComparisonData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
            >
              <XAxis
                type="number"
                tickFormatter={(v: number) => formatCurrency(v)}
                tick={{ fontSize: 11, fill: '#475569' }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12, fill: '#1e293b' }}
                width={70}
              />
              <Tooltip
                formatter={(value: number) => [
                  `$${value.toLocaleString()}`,
                  'Total Cost',
                ]}
                contentStyle={styles.tooltipContent}
              />
              <Bar dataKey="cost" radius={[0, 4, 4, 0]} barSize={28}>
                {costComparisonData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Supplier Spend Distribution Pie */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>
            Supplier Spend Distribution ({selected.name})
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={supplierSpendData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                innerRadius={40}
                paddingAngle={2}
                label={({ name, percent }: { name: string; percent: number }) =>
                  `${name.split(' ')[0]} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={{ stroke: '#94a3b8', strokeWidth: 1 }}
              >
                {supplierSpendData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [
                  `$${value.toLocaleString()}`,
                  'Spend',
                ]}
                contentStyle={styles.tooltipContent}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Material Cost Breakdown */}
      <div style={{ ...styles.chartCard, marginTop: 16 }}>
        <h3 style={styles.chartTitle}>
          Material Cost Breakdown ({selected.name})
        </h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={materialCostData}
            margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
          >
            <XAxis
              dataKey="category"
              tick={{ fontSize: 12, fill: '#1e293b' }}
            />
            <YAxis
              tickFormatter={(v: number) => formatCurrency(v)}
              tick={{ fontSize: 11, fill: '#475569' }}
            />
            <Tooltip
              formatter={(value: number) => [
                `$${value.toLocaleString()}`,
                'Cost',
              ]}
              contentStyle={styles.tooltipContent}
            />
            <Bar dataKey="cost" radius={[4, 4, 0, 0]} barSize={48}>
              {materialCostData.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: 24,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: '#1e293b',
    maxWidth: 1100,
  },
  heading: {
    fontSize: 20,
    fontWeight: 600,
    marginBottom: 16,
    color: '#0f172a',
    letterSpacing: '-0.02em',
  },
  kpiRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 12,
    marginBottom: 20,
  },
  kpiCard: {
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: '14px 16px',
    background: '#ffffff',
  },
  kpiLabel: {
    fontSize: 11,
    fontWeight: 500,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.04em',
    color: '#64748b',
    marginBottom: 4,
  },
  kpiValue: {
    fontSize: 22,
    fontWeight: 700,
    color: '#0f172a',
    lineHeight: 1.2,
  },
  kpiSub: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  chartsRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 16,
  },
  chartCard: {
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: 16,
    background: '#ffffff',
  },
  chartTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#334155',
    marginBottom: 8,
    marginTop: 0,
  },
  tooltipContent: {
    fontSize: 12,
    borderRadius: 6,
    border: '1px solid #e2e8f0',
  },
}
