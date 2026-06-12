import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell, Label, ReferenceLine, LabelList } from 'recharts'
import type { OptimizationSolution } from '../data/realData'

interface ParetoChartProps {
  solutions: OptimizationSolution[]
  selectedSolution: string | null
  onSelectSolution: (id: string) => void
}

const STRATEGY_COLORS: Record<string, string> = {
  'Cost-Optimized': '#22c55e',
  'Balanced': '#3b82f6',
  'Risk-Diversified': '#a855f7',
}

export default function ParetoChart({ solutions, selectedSolution, onSelectSolution }: ParetoChartProps) {
  const chartData = solutions.map(sol => ({
    name: sol.name,
    cost: Math.round(sol.totalCost / 1000),
    risk: Math.round(sol.riskScore * 10) / 10,
    quality: Math.round(sol.qualityScore * 10) / 10,
    leadTime: sol.maxLeadTimeDays,
    id: sol.id,
    isSelected: sol.id === selectedSolution,
    isRecommended: sol.name === 'Balanced',
    color: STRATEGY_COLORS[sol.name] || '#94a3b8',
  }))

  const costs = chartData.map(d => d.cost)
  const risks = chartData.map(d => d.risk)
  const costMin = Math.floor(Math.min(...costs) * 0.85 / 50) * 50
  const costMax = Math.ceil(Math.max(...costs) * 1.15 / 50) * 50
  const riskMin = Math.max(0, Math.floor(Math.min(...risks) - 1))
  const riskMax = Math.ceil(Math.max(...risks) + 2)

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div style={{
          background: '#1e293b', padding: '12px 16px', borderRadius: '10px',
          border: `2px solid ${data.color}`, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: data.color, marginBottom: '8px' }}>
            {data.name} {data.isRecommended ? '  Recommended' : ''}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: '12px' }}>
            <span style={{ color: '#94a3b8' }}>Total Cost</span>
            <span style={{ color: '#f1f5f9', fontWeight: 600 }}>${data.cost}K</span>
            <span style={{ color: '#94a3b8' }}>Risk Score</span>
            <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{data.risk}/10</span>
            <span style={{ color: '#94a3b8' }}>Quality</span>
            <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{data.quality}/10</span>
            <span style={{ color: '#94a3b8' }}>Lead Time</span>
            <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{data.leadTime} days</span>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="pareto-chart-container">
      <ResponsiveContainer width="100%" height={380}>
        <ScatterChart margin={{ top: 30, right: 40, bottom: 35, left: 35 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />

          <XAxis type="number" dataKey="cost" domain={[costMin, costMax]}
            tickFormatter={(v: number) => `$${v}K`} tick={{ fontSize: 12, fill: '#64748b' }}>
            <Label value="Total Cost (lower is better)" position="bottom" offset={10}
              style={{ fontSize: 13, fill: '#94a3b8', fontWeight: 500 }} />
          </XAxis>

          <YAxis type="number" dataKey="risk" domain={[riskMin, riskMax]}
            tickFormatter={(v: number) => v.toFixed(1)} tick={{ fontSize: 12, fill: '#64748b' }}>
            <Label value="Risk Score (lower is better)" angle={-90} position="left" offset={10}
              style={{ fontSize: 13, fill: '#94a3b8', fontWeight: 500 }} />
          </YAxis>

          <ReferenceLine y={2.0} stroke="#f59e0b" strokeDasharray="6 4" strokeOpacity={0.25} />
          <ReferenceLine x={costs.length > 0 ? Math.round((costMin + costMax) / 2) : 700} stroke="#f59e0b" strokeDasharray="6 4" strokeOpacity={0.15} />

          <ZAxis type="number" dataKey="quality" range={[300, 700]} name="Quality" />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#94a3b8' }} />

          <Scatter data={chartData} onClick={(data) => onSelectSolution(data.id)} cursor="pointer">
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.isSelected ? '#2563eb' : entry.color}
                stroke={entry.isSelected ? '#fff' : entry.color}
                strokeWidth={entry.isSelected ? 3 : 1.5}
                opacity={entry.isSelected ? 1 : 0.85}
              />
            ))}
            <LabelList dataKey="name" position="top" offset={12}
              style={{ fontSize: 11, fontWeight: 600, fill: '#475569' }} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginTop: '4px', flexWrap: 'wrap' }}>
        {Object.entries(STRATEGY_COLORS).map(([name, color]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>
              {name}{name === 'Balanced' ? ' (recommended)' : ''}
            </span>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
        Bubble size = quality score. Bottom-left = ideal (low cost, low risk). Click to select.
      </div>
    </div>
  )
}
