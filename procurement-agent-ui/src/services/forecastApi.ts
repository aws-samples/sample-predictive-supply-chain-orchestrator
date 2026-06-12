/**
 * Forecast API service — connects to the demand forecasting backend.
 *
 * In production, uses VITE_API_URL to reach the Flask Lambda via API Gateway.
 * In local dev, falls back to the Vite proxy at /forecast-api.
 *
 * API endpoint: POST {baseUrl}/api/forecast
 *
 * Request:  { material_id: string, prediction_length: number }
 * Response: { summary: { total_p10, total_p50, total_p90, avg_daily_p50 }, forecast: [...] }
 *
 * The p90 value is used as the demand figure (safety buffer) for procurement gap analysis.
 */

import { getIdToken } from '../auth/CognitoAuth'

const FORECAST_BASE_URL = (import.meta.env.VITE_API_URL || '/forecast-api').replace(/\/+$/, '')

export interface ForecastSummary {
  total_p10: number
  total_p50: number
  total_p90: number
  avg_daily_p50: number
}

export interface ForecastPoint {
  date: string
  p10: number
  p50: number
  p90: number
}

export interface MaterialForecast {
  material_id: string
  summary: ForecastSummary
  forecast?: ForecastPoint[]
  error?: string
}

/**
 * Fetch forecast for a single material.
 * @param materialId - Material ID (e.g., MAT-BAT-001)
 * @param predictionLength - Number of days to forecast (default: 90 for quarterly)
 */
export async function fetchMaterialForecast(
  materialId: string,
  predictionLength = 90
): Promise<MaterialForecast> {
  try {
    const token = await getIdToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = token;
    const res = await fetch(`${FORECAST_BASE_URL}/api/demand/forecast`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ material_id: materialId, prediction_length: predictionLength }),
      signal: AbortSignal.timeout(45000),
    })
    if (!res.ok) {
      return { material_id: materialId, summary: { total_p10: 0, total_p50: 0, total_p90: 0, avg_daily_p50: 0 }, error: res.statusText }
    }
    const data = await res.json()
    return { material_id: materialId, summary: data.summary, forecast: data.forecast }
  } catch (e: any) {
    return { material_id: materialId, summary: { total_p10: 0, total_p50: 0, total_p90: 0, avg_daily_p50: 0 }, error: e.message }
  }
}

/**
 * Fetch forecasts for all materials in batches to avoid overwhelming the server.
 * @param materialIds - Array of material IDs to forecast
 * @param predictionLength - Number of days to forecast (default: 60)
 */
export async function fetchAllForecasts(
  materialIds: string[],
  predictionLength = 60
): Promise<MaterialForecast[]> {
  const BATCH_SIZE = 3
  const results: MaterialForecast[] = []
  for (let i = 0; i < materialIds.length; i += BATCH_SIZE) {
    const batch = materialIds.slice(i, i + BATCH_SIZE)
    const batchResults = await Promise.all(
      batch.map(id => fetchMaterialForecast(id, predictionLength))
    )
    results.push(...batchResults)
  }
  return results
}
