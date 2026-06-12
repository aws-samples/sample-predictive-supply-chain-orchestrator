import { demandForecasts, getMaterialById } from '../data/realData'

export default function DemandForecastPanel() {
  // Group forecasts by material
  const materialForecasts = new Map<string, typeof demandForecasts>()
  demandForecasts.forEach(df => {
    if (!materialForecasts.has(df.materialId)) {
      materialForecasts.set(df.materialId, [])
    }
    materialForecasts.get(df.materialId)!.push(df)
  })

  // Get top 6 materials with forecasts
  const topMaterials = Array.from(materialForecasts.entries()).slice(0, 6)

  return (
    <div className="viz-card" style={{ marginBottom: '24px' }}>
      <h3>📈 3-Month Demand Forecast</h3>
      <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '16px' }}>
        AI-powered demand predictions for critical materials (March-May 2026)
      </p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        {topMaterials.map(([materialId, forecasts]) => {
          const material = getMaterialById(materialId)
          const sortedForecasts = forecasts.sort((a, b) => a.forecastPeriod.localeCompare(b.forecastPeriod))
          
          return (
            <div key={materialId} style={{ 
              padding: '16px', 
              backgroundColor: '#f8fafc', 
              borderRadius: '8px',
              borderLeft: '4px solid #8b5cf6'
            }}>
              <div style={{ fontWeight: '600', fontSize: '13px', marginBottom: '8px' }}>
                {material?.name.split(' ').slice(0, 3).join(' ')}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {sortedForecasts.map(forecast => (
                  <div key={forecast.forecastId} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    fontSize: '12px'
                  }}>
                    <span style={{ color: '#64748b' }}>{forecast.forecastPeriod}</span>
                    <span style={{ fontWeight: '600' }}>
                      {forecast.predictedDemand} units
                    </span>
                    <span style={{ 
                      color: forecast.confidenceLevel >= 0.85 ? '#10b981' : '#f59e0b',
                      fontSize: '11px'
                    }}>
                      {(forecast.confidenceLevel * 100).toFixed(0)}% conf
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
