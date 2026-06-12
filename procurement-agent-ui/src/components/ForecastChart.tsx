import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { MaterialForecast } from '../services/forecastApi'

interface ForecastChartProps {
  forecasts: Record<string, MaterialForecast>
  materials: { id: string; name: string }[]
}

export default function ForecastChart({ forecasts, materials }: ForecastChartProps) {
  const materialsWithForecast = materials.filter(
    m => forecasts[m.id]?.forecast && forecasts[m.id].forecast!.length > 0
  )

  const [selectedMaterial, setSelectedMaterial] = useState<string>(
    materialsWithForecast[0]?.id ?? ''
  )

  if (materialsWithForecast.length === 0) return null

  const fc = forecasts[selectedMaterial]
  const data = fc?.forecast ?? []

  // Format date labels for the X axis
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  return (
    <div style={{
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      background: 'var(--color-surface)',
      marginBottom: 20,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text)' }}>
          Demand Forecast
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 14, fontSize: 11 }}>
            {[
              { label: 'P10 (Optimistic)', color: '#22c55e' },
              { label: 'P50 (Median)', color: '#3b82f6' },
              { label: 'P90 (Conservative)', color: '#ef4444' },
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-muted)' }}>
                <span style={{ width: 10, height: 3, borderRadius: 1, background: item.color, flexShrink: 0 }} />
                {item.label}
              </div>
            ))}
          </div>
          {/* Material selector */}
          <select
            value={selectedMaterial}
            onChange={e => setSelectedMaterial(e.target.value)}
            style={{
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              background: 'var(--color-bg)',
              color: 'var(--color-text)',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {materialsWithForecast.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart */}
      <div style={{ padding: '16px 18px 12px' }}>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
              width={45}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                fontSize: 12,
              }}
              labelFormatter={(label: string) => `Date: ${label}`}
              formatter={(value: number, name: string) => {
                const labels: Record<string, string> = {
                  p90: 'P90 (Conservative)',
                  p50: 'P50 (Median)',
                  p10: 'P10 (Optimistic)',
                }
                return [Math.round(value), labels[name] ?? name]
              }}
            />
            <Area
              dataKey="p90"
              stroke="#ef4444"
              fill="#ef444415"
              strokeWidth={1}
              dot={false}
              activeDot={false}
            />
            <Area
              dataKey="p50"
              stroke="#3b82f6"
              fill="none"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, fill: '#3b82f6' }}
            />
            <Area
              dataKey="p10"
              stroke="#22c55e"
              fill="#22c55e15"
              strokeWidth={1}
              dot={false}
              activeDot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
