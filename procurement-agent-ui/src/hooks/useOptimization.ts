/**
 * React hook for optimization API with automatic fallback.
 *
 * Fetches real optimization from backend, transforms API response
 * to match the frontend OptimizationSolution interface, and falls
 * back to hardcoded data if backend is unavailable.
 */

import { useState, useEffect } from 'react';
import { optimizeUrbanEBikes, optimizeSuppliers, isBackendAvailable, type SupplierMix } from '../services/api';
import type { OptimizationSolution } from '../data/realData';

interface UseOptimizationResult {
  solutions: OptimizationSolution[] | null;
  loading: boolean;
  error: string | null;
  backendStatus: 'connected' | 'fallback' | 'checking';
  requestId: string | null;
  computationTimeMs: number | null;
  hasRun: boolean;
  refetch: (forecastMaterials?: { material_id: string; quantity: number }[], excludedSuppliers?: string[]) => Promise<void>;
}

const SOLUTION_IDS: Record<string, string> = {
  'Cost-Optimized': 'SOL-A',
  'Balanced': 'SOL-B',
  'Risk-Diversified': 'SOL-C',
};

/**
 * Transform a backend SupplierMix into the frontend OptimizationSolution format.
 */
function transformSolution(mix: SupplierMix): OptimizationSolution {
  const id = SOLUTION_IDS[mix.name] || `SOL-${mix.name.charAt(0).toUpperCase()}`;

  // Build supplier concentration from allocations
  const supplierCosts: Record<string, { name: string; cost: number }> = {};
  for (const alloc of mix.allocations) {
    const key = alloc.supplier_id;
    if (!supplierCosts[key]) {
      supplierCosts[key] = { name: alloc.supplier_name, cost: 0 };
    }
    supplierCosts[key].cost += alloc.total_cost;
  }
  const totalCost = mix.total_cost || Object.values(supplierCosts).reduce((sum, s) => sum + s.cost, 0);
  const supplierConcentration = Object.entries(supplierCosts).map(([supplierId, info]) => ({
    supplierId,
    supplierName: info.name,
    percentage: Math.round((info.cost / totalCost) * 100),
  })).sort((a, b) => b.percentage - a.percentage);

  // Build allocations in frontend format
  const allocations = mix.allocations.map(a => ({
    supplierId: a.supplier_id,
    supplierName: a.supplier_name,
    materialId: a.material_id,
    materialName: a.material_name,
    quantity: a.quantity,
    unitPrice: a.unit_price,
    totalCost: a.total_cost,
    leadTimeDays: a.lead_time_days,
    freightCost: a.freight_cost || 0,
    carryingCost: a.carrying_cost || 0,
    carbonCost: a.carbon_cost || 0,
    tco: a.tco || a.total_cost,
  }));

  // Generate reasoning structure
  const keyFactors: string[] = [
    `Total Cost of Ownership: $${totalCost.toLocaleString()} (includes freight, carrying, carbon costs)`,
    `Quality Score: ${mix.quality_score.toFixed(1)}/10`,
    `Risk Score: ${mix.risk_score.toFixed(1)}/10 (trend-weighted dynamic scoring)`,
    `Max Lead Time: ${mix.lead_time_days} days`,
    `Supplier Concentration: ${Math.round(mix.max_supplier_concentration * 100)}%`,
  ];

  if (mix.demand_buffer_pct) {
    keyFactors.push(`Demand Buffer: +${mix.demand_buffer_pct}% above base forecast`);
  }

  const tradeOffs: string[] = [];
  if (mix.name === 'Cost-Optimized') {
    tradeOffs.push('Lowest TCO → May accept higher risk suppliers');
    tradeOffs.push('Cost savings from volume consolidation and favorable payment terms');
  } else if (mix.name === 'Balanced') {
    tradeOffs.push('Moderate cost with good quality and risk balance');
    tradeOffs.push('Leverages contracted suppliers for reliability');
  } else if (mix.name === 'Risk-Diversified') {
    tradeOffs.push('Highest quality and lowest risk → Higher TCO');
    tradeOffs.push('Trend-verified suppliers with best performance history');
  }

  const risks: string[] = [];
  if (mix.risk_score > 5) risks.push('Elevated supply chain risk — consider diversification');
  if (mix.max_supplier_concentration > 0.5) risks.push(`High supplier concentration (${Math.round(mix.max_supplier_concentration * 100)}%) — single point of failure risk`);
  if (mix.lead_time_days > 45) risks.push(`Extended lead time (${mix.lead_time_days}d) — plan for buffer stock`);

  // TCO breakdown for volume discounts display
  const totalFreight = mix.allocations.reduce((s, a) => s + (a.freight_cost || 0), 0);
  const totalCarbon = mix.allocations.reduce((s, a) => s + (a.carbon_cost || 0), 0);
  const totalCarrying = mix.allocations.reduce((s, a) => s + (a.carrying_cost || 0), 0);

  const volumeDiscounts = [];
  if (totalFreight > 0) volumeDiscounts.push({ description: 'Freight costs (region-based)', savings: -totalFreight });
  if (totalCarbon > 0) volumeDiscounts.push({ description: 'Carbon impact ($50/ton CO₂)', savings: -totalCarbon });
  if (totalCarrying > 0) volumeDiscounts.push({ description: 'Carrying costs (safety stock)', savings: -totalCarrying });

  return {
    id,
    name: mix.name,
    totalCost: totalCost,
    riskScore: mix.risk_score,
    qualityScore: mix.quality_score,
    maxLeadTimeDays: mix.lead_time_days,
    allocations,
    explanation: mix.reasoning || '',
    supplierConcentration,
    reasoning: {
      summary: mix.reasoning || '',
      keyFactors,
      tradeOffs,
      risks,
      volumeDiscounts: volumeDiscounts.length > 0 ? volumeDiscounts : undefined,
    },
    demandBufferPct: mix.demand_buffer_pct ?? undefined,
  };
}

export function useOptimization(): UseOptimizationResult {
  const [solutions, setSolutions] = useState<OptimizationSolution[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'connected' | 'fallback' | 'checking'>('checking');
  const [hasRun, setHasRun] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [computationTimeMs, setComputationTimeMs] = useState<number | null>(null);

  const fetchOptimization = async (forecastMaterials?: { material_id: string; quantity: number }[], excludedSuppliers?: string[]) => {
    try {
      setLoading(true);
      setError(null);
      setBackendStatus('checking');

      const available = await isBackendAvailable();
      const response = forecastMaterials && forecastMaterials.length > 0
        ? await optimizeSuppliers({
            materials: forecastMaterials,
            constraints: {
              max_supplier_concentration: 0.60,
              excluded_suppliers: excludedSuppliers || [],
              max_lead_time_days: 60,
              budget_max: 5_000_000,
              budget_min: 0,
              prefer_contracted_suppliers: true,
            },
          })
        : await optimizeUrbanEBikes(excludedSuppliers);

      // Transform API solutions to frontend format
      const transformed = response.solutions.map(transformSolution);
      setSolutions(transformed);
      setRequestId(response.request_id);
      setComputationTimeMs(response.computation_time_ms);
      setHasRun(true);

      if (available && response.computation_time_ms > 0) {
        setBackendStatus('connected');
        // console.log('✅ Using backend API -', transformed.length, 'solutions');
      } else {
        setBackendStatus('fallback');
        // console.log('📦 Using fallback data');
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setBackendStatus('fallback');
      // console.error('❌ Optimization failed:', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Check backend availability — retry after short delay for Cognito session to load
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      // First try immediately
      let available = await isBackendAvailable();
      if (!available && !cancelled) {
        // Retry after 2s (Cognito session may still be loading)
        await new Promise(r => setTimeout(r, 2000));
        if (!cancelled) available = await isBackendAvailable();
      }
      if (!cancelled) {
        setBackendStatus(available ? 'connected' : 'fallback');
        setLoading(false);
      }
    };
    check();
    return () => { cancelled = true; };
  }, []);

  return {
    solutions,
    loading,
    error,
    backendStatus,
    requestId,
    computationTimeMs,
    hasRun,
    refetch: fetchOptimization,
  };
}
