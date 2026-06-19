/**
 * API service for Procurement Optimization Agent backend.
 *
 * Connects React UI to Flask backend via Vite proxy (see vite.config.ts).
 * In dev mode, /api/* is proxied to localhost:5001 by Vite.
 * Falls back to hardcoded data if backend is unavailable.
 */

import { getAccessToken, getIdToken } from '../auth/CognitoAuth';

// Use relative URLs — Vite proxy handles routing to the correct backend
export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '');
const USE_FALLBACK = import.meta.env.VITE_USE_FALLBACK !== 'false';

// AgentCore Runtime — frontend calls directly with user's JWT
const AGENTCORE_REGION = import.meta.env.VITE_AGENTCORE_REGION || 'us-east-1';
const AGENTCORE_RUNTIME_ARN = import.meta.env.VITE_AGENTCORE_RUNTIME_ARN || '';

/** Build headers with Cognito ID token for API Gateway calls. */
export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getIdToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
  try {
    const accessToken = await getAccessToken();
    if (accessToken) headers['X-Access-Token'] = accessToken;
  } catch { /* access token optional */ }
  return headers;
}

export interface MaterialDemand {
  material_id: string;
  quantity: number;
  required_by?: string;
}

export interface OptimizationConstraints {
  max_supplier_concentration: number;
  excluded_suppliers?: string[];
  max_lead_time_days: number;
  budget_max: number;
  budget_min: number;
  prefer_contracted_suppliers?: boolean;
}

export interface ObjectiveWeights {
  cost: number;
  risk: number;
  lead_time: number;
}

export interface OptimizationRequest {
  materials: MaterialDemand[];
  constraints?: OptimizationConstraints;
  objectives?: ObjectiveWeights;
}

export interface SupplierAllocation {
  supplier_id: string;
  supplier_name: string;
  material_id: string;
  material_name: string;
  quantity: number;
  unit_price: number;
  total_cost: number;
  lead_time_days: number;
  quality_score: number;
  freight_cost?: number;
  carrying_cost?: number;
  carbon_cost?: number;
  tco?: number;
}

export interface SupplierMix {
  name: string;
  total_cost: number;
  risk_score: number;
  quality_score: number;
  lead_time_days: number;
  max_supplier_concentration: number;
  allocations: SupplierAllocation[];
  reasoning?: string;
  demand_buffer_pct?: number | null;
}

export interface OptimizationResponse {
  solutions: SupplierMix[];
  request_id: string;
  computation_time_ms: number;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  environment: string;
}

/**
 * Check backend health status.
 */
export async function checkHealth(): Promise<HealthCheckResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      signal: AbortSignal.timeout(8000),
    });

    if (!response.ok) {
      console.warn('Backend health check failed:', response.statusText);
      return null;
    }

    return response.json();
  } catch (error) {
    console.warn('Backend not available:', error);
    return null;
  }
}

/**
 * Optimize supplier selection.
 */
export async function optimizeSuppliers(
  request: OptimizationRequest,
  useFallback: boolean = USE_FALLBACK
): Promise<OptimizationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/optimize`, {
      method: 'POST',
      headers: await authHeaders(),
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Optimization failed: ${response.statusText}`);
    }

    const data = await response.json();
    // console.log('✅ Backend API response received:', data.solutions?.length, 'solutions');
    return data;

  } catch (error) {
    console.warn('⚠️ Backend API failed:', error);

    if (useFallback) {
      // console.log('📦 Using fallback hardcoded data');
      return getFallbackOptimization();
    }

    throw error;
  }
}

/**
 * Get fallback hardcoded optimization data.
 */
function getFallbackOptimization(): OptimizationResponse {
  return {
    solutions: [
      {
        name: 'Cost-Optimized',
        total_cost: 650000,
        risk_score: 7.5,
        quality_score: 6.5,
        lead_time_days: 55,
        max_supplier_concentration: 0.32,
        allocations: [
          {
            supplier_id: 'SUP-001', supplier_name: 'BatteryTech Solutions',
            material_id: 'MAT-BAT-001', material_name: 'Lithium-ion Battery Pack',
            quantity: 500, unit_price: 280.0, total_cost: 140000,
            lead_time_days: 55, quality_score: 6.5,
          },
        ],
        reasoning: 'Lowest cost option with acceptable risk for budget-conscious procurement. (Fallback data)',
      },
      {
        name: 'Balanced',
        total_cost: 875000,
        risk_score: 3.5,
        quality_score: 8.2,
        lead_time_days: 42,
        max_supplier_concentration: 0.28,
        allocations: [
          {
            supplier_id: 'SUP-002', supplier_name: 'PowerCell Industries',
            material_id: 'MAT-BAT-001', material_name: 'Lithium-ion Battery Pack',
            quantity: 500, unit_price: 320.0, total_cost: 160000,
            lead_time_days: 42, quality_score: 8.2,
          },
        ],
        reasoning: 'Optimal balance of cost, quality, and risk. Recommended for most scenarios. (Fallback data)',
      },
      {
        name: 'Risk-Diversified',
        total_cost: 1200000,
        risk_score: 1.5,
        quality_score: 9.5,
        lead_time_days: 35,
        max_supplier_concentration: 0.22,
        allocations: [
          {
            supplier_id: 'SUP-003', supplier_name: 'BrakeSafe Systems',
            material_id: 'MAT-BRK-001', material_name: 'Hydraulic Disc Brake',
            quantity: 1000, unit_price: 45.0, total_cost: 45000,
            lead_time_days: 35, quality_score: 9.5,
          },
        ],
        reasoning: 'Highest quality and lowest risk. Supply chain insurance for critical production. (Fallback data)',
      },
    ],
    request_id: 'fallback-' + Date.now(),
    computation_time_ms: 0,
  };
}

/**
 * Optimize for 500 Urban E-Bikes with full BOM.
 */
export async function optimizeUrbanEBikes(
  excludedSuppliers?: string[],
  useFallback: boolean = USE_FALLBACK,
): Promise<OptimizationResponse> {
  // Full BOM for Q2 production: Urban (500) + Mountain (400)
  // Shared materials need 900, product-specific materials need their product qty
  return optimizeSuppliers({
    materials: [
      // Battery System (shared — 900)
      { material_id: 'MAT-BAT-001', quantity: 900 },
      { material_id: 'MAT-BAT-002', quantity: 900 },
      { material_id: 'MAT-BAT-003', quantity: 900 },
      // Drive System
      { material_id: 'MAT-MOT-001', quantity: 500 },  // Urban-only: Mid-Drive 750W
      { material_id: 'MAT-MOT-002', quantity: 400 },  // Mountain-only: Mid-Drive 500W
      { material_id: 'MAT-MOT-003', quantity: 900 },  // Shared: Motor Controller
      { material_id: 'MAT-MOT-004', quantity: 900 },  // Shared: Torque Sensor
      // Frame
      { material_id: 'MAT-FRM-001', quantity: 500 },  // Urban-only: Aluminum Frame
      { material_id: 'MAT-FRM-002', quantity: 400 },  // Mountain-only: Carbon Fiber Frame
      { material_id: 'MAT-FRM-003', quantity: 900 },  // Shared: Suspension Fork
      { material_id: 'MAT-FRM-004', quantity: 900 },  // Shared: Handlebar Assembly
      // Electronics (shared — 900)
      { material_id: 'MAT-ELC-001', quantity: 900 },
      { material_id: 'MAT-ELC-002', quantity: 900 },
      { material_id: 'MAT-ELC-003', quantity: 900 },
      // Standard Components (shared — 900)
      { material_id: 'MAT-STD-001', quantity: 900 },
      { material_id: 'MAT-STD-002', quantity: 900 },
      { material_id: 'MAT-STD-003', quantity: 900 },
      { material_id: 'MAT-STD-004', quantity: 900 },
    ],
    constraints: {
      max_supplier_concentration: 0.60,
      excluded_suppliers: excludedSuppliers || [],
      max_lead_time_days: 60,
      budget_max: 5_000_000,
      budget_min: 0,
      prefer_contracted_suppliers: true,
    },
  }, useFallback);
}

/**
 * Check if backend is available.
 */
export async function isBackendAvailable(): Promise<boolean> {
  const health = await checkHealth();
  return health !== null && health.status === 'healthy';
}

// --- Live data endpoints ---

export interface BackendSupplier {
  supplier_id: string;
  name: string;
  location: string;
  rating: number;
  lead_time_days: number;
  payment_terms: string;
  financial_stability_score: number;
  geopolitical_risk_score: number;
  active_status: boolean;
  contact_email: string;
  contact_phone: string;
}

export interface BackendPerformance {
  performance_id: string;
  supplier_id: string;
  measurement_period: string;
  on_time_delivery_rate: number;
  quality_score: number;
  defect_rate: number;
  cost_variance: number;
  response_time_hours: number;
}

export interface BackendMaterial {
  material_id: string;
  name: string;
  category: string;
  unit_of_measure: string;
  standard_cost: number;
  criticality_level: string;
  weight_kg: number;
}

/**
 * Fetch suppliers from backend.
 */
export async function fetchSuppliers(): Promise<BackendSupplier[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suppliers`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.suppliers || [];
  } catch {
    console.warn('Failed to fetch suppliers from backend');
    return [];
  }
}

/**
 * Fetch materials from backend.
 */
export async function fetchMaterials(): Promise<BackendMaterial[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/materials`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.materials || [];
  } catch {
    console.warn('Failed to fetch materials from backend');
    return [];
  }
}

/**
 * Fetch supplier performance from backend.
 */
export async function fetchSupplierPerformance(): Promise<BackendPerformance[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/supplier-performance`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.performance || [];
  } catch {
    console.warn('Failed to fetch supplier performance from backend');
    return [];
  }
}

// --- Chat endpoint ---

export interface ChatResponse {
  response: string;
  source: string;
  timestamp: string;
}

/**
 * Send a message to the procurement agent chat.
 */
// Persistent session ID per browser tab for memory continuity
const SESSION_ID = crypto.randomUUID();

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const token = await getAccessToken();

  // Authenticated: call AgentCore Runtime directly (no API Gateway 29s limit)
  if (token && AGENTCORE_RUNTIME_ARN) {
    const dp = `https://bedrock-agentcore.${AGENTCORE_REGION}.amazonaws.com`;
    const arn = encodeURIComponent(AGENTCORE_RUNTIME_ARN);
    const url = `${dp}/runtimes/${arn}/invocations?qualifier=DEFAULT`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': SESSION_ID,
      },
      body: JSON.stringify({ prompt: message, actor_id: 'demo-user' }),
      signal: AbortSignal.timeout(90000),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      throw new Error(`Agent error (${response.status}): ${errorText}`);
    }

    let text = await response.text();
    // AgentCore returns response as JSON-encoded string — unescape
    if (text.startsWith('"') && text.endsWith('"')) {
      try { text = JSON.parse(text); } catch { /* use as-is */ }
    }
    return { response: text, source: 'agentcore', timestamp: new Date().toISOString() };
  }

  // Fallback: API Lambda (unauthenticated)
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({ message, session_id: SESSION_ID, user_id: 'demo-user' }),
    signal: AbortSignal.timeout(60000),
  });

  if (!response.ok) {
    if (response.status === 504) {
      throw new Error('Agent is still processing — try a simpler question or retry in a moment.')
    }
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || `Chat failed: ${response.statusText}`);
  }

  return response.json();
}

// --- Purchase Requisition endpoints ---

export interface PurchaseRequisitionRequest {
  solution_name: string;
  allocations: Array<{
    supplier_id: string;
    material_id: string;
    quantity: number;
    unit_price: number;
  }>;
  requester: string;
  notes?: string;
}

export interface PurchaseRequisitionResponse {
  pr_ids: string[];
  total_prs: number;
  total_value: number;
  status: string;
  solution_name: string;
  requester: string;
  created_at: string;
}

/**
 * Create purchase requisitions from a solution.
 */
export async function createPurchaseRequisitions(
  req: PurchaseRequisitionRequest
): Promise<PurchaseRequisitionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/purchase-requisitions`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(req),
    signal: AbortSignal.timeout(10000),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || `PR creation failed: ${response.statusText}`);
  }

  return response.json();
}

export interface SAPExportRequest {
  solution_name: string
  allocations: Array<{
    supplier_id: string
    supplier_name: string
    material_id: string
    material_name: string
    quantity: number
    unit_price: number
    lead_time_days: number
  }>
  requester?: string
}

export interface SAPExportResponse {
  export_id: string
  solution_name: string
  total_documents: number
  s3_prefix: string
  s3_keys: string[]
  odata_documents: any[]
  created_at: string
}

/**
 * Export purchase requisitions as SAP OData JSON to S3.
 */
export async function exportSAPOData(req: SAPExportRequest): Promise<SAPExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/purchase-requisitions/export-sap`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(req),
    signal: AbortSignal.timeout(15000),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.error || `SAP export failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Optimize with custom weights. Returns a single custom solution.
 */
export async function optimizeWithWeights(
  weights: { cost: number; risk: number; lead_time: number },
  materials?: { material_id: string; quantity: number }[],
): Promise<{
  solution: SupplierMix; weights: typeof weights; computation_time_ms: number;
}> {
  const body: Record<string, unknown> = { weights }
  if (materials && materials.length > 0) {
    body.materials = materials
  }
  const response = await fetch(`${API_BASE_URL}/api/optimize-custom`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Custom optimization failed: ${response.statusText}`);
  return response.json();
}

// --- Neptune Graph endpoints ---

export interface GraphNode {
  id: string; label: string; type: 'supplier' | 'material';
  risk?: number; rating?: number; location?: string;
  category?: string; criticality?: string;
}
export interface GraphLink { source: string; target: string; price: number; lead_time: number; }
export interface GraphNetwork { nodes: GraphNode[]; links: GraphLink[]; degree: Record<string, number>; source: string; }

export async function fetchGraphNetwork(): Promise<GraphNetwork> {
  try {
    const r = await fetch(`${API_BASE_URL}/api/graph/network`, { headers: await authHeaders(), signal: AbortSignal.timeout(10000) });
    if (!r.ok) return { nodes: [], links: [], degree: {}, source: 'error' };
    return r.json();
  } catch { return { nodes: [], links: [], degree: {}, source: 'error' }; }
}

export async function fetchAlternativeSuppliers(materialId: string): Promise<{ suppliers: any[] }> {
  try {
    const r = await fetch(`${API_BASE_URL}/api/graph/alternatives/${materialId}`, { headers: await authHeaders(), signal: AbortSignal.timeout(10000) });
    if (!r.ok) return { suppliers: [] };
    return r.json();
  } catch { return { suppliers: [] }; }
}

export async function fetchSupplierMaterialsGraph(supplierId: string): Promise<{ materials: any[] }> {
  try {
    const r = await fetch(`${API_BASE_URL}/api/graph/supplier-materials/${supplierId}`, { headers: await authHeaders(), signal: AbortSignal.timeout(10000) });
    if (!r.ok) return { materials: [] };
    return r.json();
  } catch { return { materials: [] }; }
}

/**
 * List purchase requisitions.
 */
export async function listPurchaseRequisitions(): Promise<{ purchase_requisitions: any[]; total: number }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/purchase-requisitions`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return { purchase_requisitions: [], total: 0 };
    return response.json();
  } catch {
    return { purchase_requisitions: [], total: 0 };
  }
}

// --- Defect Tracking endpoints ---

export interface DefectRecord {
  defect_id: string;
  supplier_id: string;
  supplier_name: string;
  material_id: string;
  material_name: string;
  defect_date: string;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
  category: string;
  quantity_affected: number;
  batch_id: string;
  description: string;
  root_cause: string;
  status: 'OPEN' | 'RESOLVED' | 'CLOSED';
  recall_initiated: boolean;
  resolution_date: string | null;
  corrective_action: string;
}

export interface DefectSummary {
  overview: {
    total_defects: number;
    open_defects: number;
    resolved_defects: number;
    recalls_initiated: number;
    critical_defects: number;
    total_units_affected: number;
  };
  by_severity: Record<string, { count: number; quantity_affected: number }>;
  by_supplier: Record<string, {
    supplier_name: string;
    total_defects: number;
    open_defects: number;
    critical_defects: number;
    recalls: number;
    quantity_affected: number;
    defect_score: number;
  }>;
  by_material: Record<string, {
    material_name: string;
    total_defects: number;
    critical_defects: number;
    quantity_affected: number;
    suppliers_affected: string[];
  }>;
  by_category: Record<string, number>;
}

export interface DefectReport {
  report: {
    total_defects: number;
    avg_resolution_days: number | null;
    monthly_trend: Record<string, { total: number; critical: number; quantity: number }>;
    top_root_causes: Array<{ cause: string; count: number }>;
    recall_rate: number;
    open_rate: number;
  };
}

export async function fetchDefects(filters?: {
  supplier_id?: string; material_id?: string; severity?: string; status?: string;
}): Promise<{ defects: DefectRecord[]; total: number }> {
  try {
    const params = new URLSearchParams();
    if (filters?.supplier_id) params.set('supplier_id', filters.supplier_id);
    if (filters?.material_id) params.set('material_id', filters.material_id);
    if (filters?.severity) params.set('severity', filters.severity);
    if (filters?.status) params.set('status', filters.status);
    const qs = params.toString();
    const response = await fetch(`${API_BASE_URL}/api/defects${qs ? '?' + qs : ''}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return { defects: [], total: 0 };
    return response.json();
  } catch {
    return { defects: [], total: 0 };
  }
}

export async function fetchDefectSummary(): Promise<DefectSummary | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/defects/summary`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchDefectReport(supplierId?: string): Promise<DefectReport | null> {
  try {
    const qs = supplierId ? `?supplier_id=${supplierId}` : '';
    const response = await fetch(`${API_BASE_URL}/api/defects/report${qs}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function initiateRecall(defectId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/defects/${defectId}/recall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`Recall failed: ${response.statusText}`);
  return response.json();
}
