/**
 * Admin API service for Operations panel.
 *
 * Provides access to evaluations, memory, policies, and gateway status.
 * Falls back to demo data when backend is unavailable.
 */

import { getIdToken } from '../auth/CognitoAuth';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5001').replace(/\/+$/, '');

/** Build headers with Cognito ID token for API Gateway calls. */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getIdToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
  return headers;
}

// ── Types ──────────────────────────────────────────────────────────

export interface EvalCheck {
  [key: string]: boolean;
}

export interface EvalCaseResult {
  case: string;
  passed: boolean;
  score: number;
  duration_ms: number;
  tools_invoked: string[];
  checks: EvalCheck;
  error?: string;
}

export interface EvalSummary {
  total_cases: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
  total_duration_ms: number;
  results: EvalCaseResult[];
}

export interface SessionTurn {
  session_id: string;
  turn_id: number;
  user_id: string;
  role: string;
  content: string;
  tools_used: string[];
  created_at: number;
}

export interface MemoryEntry {
  user_id: string;
  memory_key: string;
  content: Record<string, unknown>;
  category: string;
  created_at: number;
  updated_at: number;
}

export interface MemoryRecord {
  record_id: string;
  strategy: string;
  strategy_type: string;
  namespace: string;
  content: string;
  created_at: string;
  updated_at: string;
  score: number | null;
}

export interface CedarPolicy {
  name: string;
  description: string;
  statement: string;
  effect: 'permit' | 'forbid';
  role?: string;
}

export interface PolicyRole {
  name: string;
  description: string;
  allowed_tools: string[];
  allowed_actions: string[];
  max_budget_authority: number;
}

export interface GatewayTool {
  name: string;
  description: string;
  target_name: string;
  lambda_arn?: string;
  status: 'active' | 'inactive';
}

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  model: string;
  tools_used: string[];
  status: 'active' | 'inactive';
}

export interface GatewayStatus {
  gateway_id: string;
  name: string;
  protocol: string;
  auth_type: string;
  status: string;
  tools: GatewayTool[];
  agents: AgentInfo[];
}

// ── API Functions ──────────────────────────────────────────────────

export async function fetchEvaluations(tags?: string[]): Promise<EvalSummary> {
  try {
    const params = tags ? `?tags=${tags.join(',')}` : '';
    const res = await fetch(`${API_BASE_URL}/api/admin/evaluations${params}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(60000),
    });
    if (res.ok) {
      const data = await res.json();
      // Live API returns {evaluators: [...]} — transform to EvalSummary format
      if (data.evaluators && !data.results) {
        return {
          total_cases: data.evaluators.length,
          passed: data.evaluators.filter((e: Record<string, string>) => e.status === 'ACTIVE').length,
          failed: data.evaluators.filter((e: Record<string, string>) => e.status !== 'ACTIVE').length,
          pass_rate: 1.0,
          avg_score: 1.0,
          total_duration_ms: 0,
          results: data.evaluators.map((ev: Record<string, string>) => ({
            case: ev.name || ev.evaluator_id,
            passed: ev.status === 'ACTIVE',
            score: ev.status === 'ACTIVE' ? 1.0 : 0.0,
            duration_ms: 0,
            tools_invoked: [ev.level || 'SESSION'],
            checks: { deployed: ev.status === 'ACTIVE', level: true },
            error: ev.status !== 'ACTIVE' ? `Status: ${ev.status}` : undefined,
          })),
        };
      }
      return data;
    }
  } catch { /* fallback */ }
  return getFallbackEvaluations();
}

// Types for live memory API response
interface LiveMemoryResponse {
  memory_id: string;
  name: string;
  status: string;
  event_expiry_days: number;
  strategies: Array<{
    strategy_id: string;
    name: string;
    type: string;
    status: string;
    namespaces: string[];
  }>;
  records: unknown[];
}

export async function fetchSessions(userId?: string): Promise<SessionTurn[]> {
  try {
    const params = userId ? `?user_id=${userId}` : '';
    const res = await fetch(`${API_BASE_URL}/api/admin/memory/sessions${params}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(25000),
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length === 0) return getFallbackSessions();
      return data;
    }
  } catch { /* fallback */ }
  return getFallbackSessions();
}

let _cachedMemoryInfo: LiveMemoryResponse | null = null;

export async function fetchMemoryInfo(): Promise<LiveMemoryResponse | null> {
  if (_cachedMemoryInfo) return _cachedMemoryInfo;
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memory/entries`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      _cachedMemoryInfo = await res.json();
      return _cachedMemoryInfo;
    }
  } catch { /* ignore */ }
  return null;
}

export async function fetchMemories(userId?: string): Promise<MemoryEntry[]> {
  try {
    const params = userId ? `?user_id=${userId}` : '';
    const res = await fetch(`${API_BASE_URL}/api/admin/memory/entries${params}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      const data = await res.json() as LiveMemoryResponse;
      _cachedMemoryInfo = data;
      // Transform strategies into MemoryEntry format for display
      if (data.strategies && data.strategies.length > 0) {
        const now = Date.now() / 1000;
        return data.strategies.map(s => ({
          user_id: 'system',
          memory_key: s.strategy_id,
          content: {
            type: s.type,
            status: s.status,
            namespaces: s.namespaces,
          } as Record<string, unknown>,
          category: s.type.toLowerCase(),
          created_at: now,
          updated_at: now,
        }));
      }
      return [];
    }
  } catch { /* fallback */ }
  return getFallbackMemories();
}

export async function fetchPolicies(): Promise<{ policies: CedarPolicy[]; roles: PolicyRole[] }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/policies`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) return await res.json();
  } catch { /* fallback */ }
  return getFallbackPolicies();
}

export async function fetchGatewayStatus(): Promise<GatewayStatus> {
  const fallback = getFallbackGatewayStatus();
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/gateway`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      const live = await res.json();
      // Merge: replace live tools with enriched fallback versions (matched by target_name),
      // then append any fallback tools not present in live data
      const liveTargets = new Set((live.tools || []).map((t: GatewayTool) => t.target_name));
      return {
        ...live,
        tools: live.tools?.length > 0
          ? live.tools.map((t: GatewayTool) => {
              const enriched = fallback.tools.find(ft => ft.target_name === t.target_name);
              return enriched || t;
            }).concat(fallback.tools.filter((ft: GatewayTool) => !liveTargets.has(ft.target_name)))
          : fallback.tools,
        agents: live.agents?.length > 0 ? live.agents : fallback.agents,
      };
    }
  } catch { /* fallback */ }
  return fallback;
}

export async function fetchMemoryRecords(actorId?: string): Promise<MemoryRecord[]> {
  try {
    const params = actorId ? `?actor_id=${actorId}` : '';
    const res = await fetch(`${API_BASE_URL}/api/admin/memory/records${params}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(15000),
    });
    if (res.ok) {
      const data = await res.json();
      return data.records || [];
    }
  } catch { /* fallback */ }
  return [];
}

export async function searchMemory(query: string, actorId?: string): Promise<MemoryRecord[]> {
  try {
    const params = new URLSearchParams({ q: query });
    if (actorId) params.set('actor_id', actorId);
    const res = await fetch(`${API_BASE_URL}/api/admin/memory/search?${params}`, {
      headers: await authHeaders(),
      signal: AbortSignal.timeout(15000),
    });
    if (res.ok) {
      const data = await res.json();
      return data.records || [];
    }
  } catch { /* fallback */ }
  return [];
}

// ── Fallback Data ──────────────────────────────────────────────────

function getFallbackEvaluations(): EvalSummary {
  return {
    total_cases: 10,
    passed: 9,
    failed: 1,
    pass_rate: 0.9,
    avg_score: 0.92,
    total_duration_ms: 14500,
    results: [
      { case: 'basic_optimization', passed: true, score: 1.0, duration_ms: 1200, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, has_solutions: true, has_allocations: true, cost_positive: true } },
      { case: 'multi_material_optimization', passed: true, score: 1.0, duration_ms: 1800, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, has_solutions: true, has_allocations: true, budget_respected: true } },
      { case: 'supplier_query', passed: true, score: 1.0, duration_ms: 800, tools_invoked: ['query_supplier_data'], checks: { correct_tools: true, has_suppliers: true } },
      { case: 'solution_explanation', passed: true, score: 1.0, duration_ms: 2100, tools_invoked: ['optimize_suppliers', 'explain_solution'], checks: { correct_tools: true, has_explanation: true } },
      { case: 'concentration_constraint', passed: true, score: 1.0, duration_ms: 1400, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, has_solutions: true, concentration_respected: true } },
      { case: 'lead_time_constraint', passed: true, score: 1.0, duration_ms: 1100, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, has_solutions: true, lead_time_respected: true } },
      { case: 'actionable_recommendation', passed: true, score: 1.0, duration_ms: 1500, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, has_recommendation: true, has_reasoning: true } },
      { case: 'unknown_material_handling', passed: true, score: 1.0, duration_ms: 900, tools_invoked: ['optimize_suppliers'], checks: { correct_tools: true, handles_error_gracefully: true } },
      { case: 'optimize_and_create_prs', passed: true, score: 1.0, duration_ms: 2800, tools_invoked: ['optimize_suppliers', 'create_purchase_requisitions'], checks: { correct_tools: true, has_solutions: true, has_prs: true } },
      { case: 'supplier_network_query', passed: false, score: 0.5, duration_ms: 900, tools_invoked: ['query_supplier_data'], checks: { correct_tools: true, has_network_data: false }, error: 'Neptune graph traversal returned partial results' },
    ],
  };
}

function getFallbackSessions(): SessionTurn[] {
  const now = Date.now() / 1000;
  return [
    { session_id: 'sess-001', turn_id: 1, user_id: 'demo@voltcycle.com', role: 'user', content: 'Optimize procurement for 500 battery packs', tools_used: [], created_at: now - 3600 },
    { session_id: 'sess-001', turn_id: 2, user_id: 'demo@voltcycle.com', role: 'assistant', content: 'I found 4 optimal solutions on the Pareto frontier...', tools_used: ['optimize_suppliers'], created_at: now - 3595 },
    { session_id: 'sess-001', turn_id: 3, user_id: 'demo@voltcycle.com', role: 'user', content: 'Explain the Balanced solution', tools_used: [], created_at: now - 3500 },
    { session_id: 'sess-001', turn_id: 4, user_id: 'demo@voltcycle.com', role: 'assistant', content: 'The Balanced solution distributes orders across 3 suppliers...', tools_used: ['explain_solution'], created_at: now - 3490 },
    { session_id: 'sess-002', turn_id: 1, user_id: 'procurement@voltcycle.com', role: 'user', content: 'Find alternative suppliers for motor assemblies', tools_used: [], created_at: now - 7200 },
    { session_id: 'sess-002', turn_id: 2, user_id: 'procurement@voltcycle.com', role: 'assistant', content: 'I found 5 alternative suppliers within 2 hops in the supply network...', tools_used: ['query_supplier_data'], created_at: now - 7190 },
  ];
}

function getFallbackMemories(): MemoryEntry[] {
  const now = Date.now() / 1000;
  return [
    { user_id: 'demo@voltcycle.com', memory_key: 'preferred_strategy', content: { strategy: 'Balanced', reason: 'Best trade-off for Q2 production' }, category: 'preferences', created_at: now - 86400, updated_at: now - 3600 },
    { user_id: 'demo@voltcycle.com', memory_key: 'supplier_note_SUP-003', content: { note: 'Quality issues in Jan batch, monitor closely', supplier: 'SUP-003' }, category: 'supplier_insights', created_at: now - 172800, updated_at: now - 172800 },
    { user_id: 'demo@voltcycle.com', memory_key: 'budget_q2_2026', content: { budget_max: 950000, approved_by: 'CFO', period: 'Q2 2026' }, category: 'constraints', created_at: now - 259200, updated_at: now - 86400 },
    { user_id: 'procurement@voltcycle.com', memory_key: 'preferred_suppliers', content: { preferred: ['SUP-001', 'SUP-005', 'SUP-008'], reason: 'Contract terms favorable' }, category: 'preferences', created_at: now - 345600, updated_at: now - 172800 },
  ];
}

function getFallbackPolicies(): { policies: CedarPolicy[]; roles: PolicyRole[] } {
  return {
    policies: [
      { name: 'analyst_read_data', description: 'Analyst can query supplier data', statement: 'permit (principal in Role::"Analyst", action == Action::"ReadData", resource in Tool::"query_supplier_data");', effect: 'permit', role: 'Analyst' },
      { name: 'analyst_explain', description: 'Analyst can view explanations', statement: 'permit (principal in Role::"Analyst", action == Action::"ReadData", resource in Tool::"explain_solution");', effect: 'permit', role: 'Analyst' },
      { name: 'manager_optimize', description: 'Manager can run optimization within budget authority', statement: 'permit (principal in Role::"ProcurementManager", action == Action::"InvokeTool", resource in Tool::"optimize_suppliers") when { context.budget_max <= principal.max_budget_authority };', effect: 'permit', role: 'ProcurementManager' },
      { name: 'manager_data_access', description: 'Manager can query supplier data', statement: 'permit (principal in Role::"ProcurementManager", action == Action::"ReadData", resource in Tool::"query_supplier_data");', effect: 'permit', role: 'ProcurementManager' },
      { name: 'manager_explain', description: 'Manager can view explanations', statement: 'permit (principal in Role::"ProcurementManager", action == Action::"ReadData", resource in Tool::"explain_solution");', effect: 'permit', role: 'ProcurementManager' },
      { name: 'manager_create_pr', description: 'Manager can create PRs with quantity limit', statement: 'permit (principal in Role::"ProcurementManager", action == Action::"CreatePR", resource in Tool::"create_purchase_requisitions") when { context.total_quantity <= 10000 };', effect: 'permit', role: 'ProcurementManager' },
      { name: 'admin_full_access', description: 'Admin has unrestricted access', statement: 'permit (principal in Role::"Admin", action, resource);', effect: 'permit', role: 'Admin' },
      { name: 'deny_excessive_quantity', description: 'Block optimization with >100K total quantity', statement: 'forbid (principal, action == Action::"InvokeTool", resource in Tool::"optimize_suppliers") when { context.total_quantity > 100000 };', effect: 'forbid' },
      { name: 'deny_excessive_budget', description: 'Block optimization with >$10M budget', statement: 'forbid (principal, action == Action::"InvokeTool", resource in Tool::"optimize_suppliers") when { context.budget_max > 10000000 };', effect: 'forbid' },
    ],
    roles: [
      { name: 'Analyst', description: 'Read-only access to supplier data and solution explanations', allowed_tools: ['query_supplier_data', 'explain_solution'], allowed_actions: ['ReadData'], max_budget_authority: 0 },
      { name: 'ProcurementManager', description: 'Full optimization, data access, and PR creation', allowed_tools: ['optimize_suppliers', 'query_supplier_data', 'explain_solution', 'create_purchase_requisitions'], allowed_actions: ['InvokeTool', 'ReadData', 'CreatePR'], max_budget_authority: 5000000 },
      { name: 'Admin', description: 'Unrestricted access to all tools and configuration', allowed_tools: ['*'], allowed_actions: ['*'], max_budget_authority: 10000000 },
    ],
  };
}

function getFallbackGatewayStatus(): GatewayStatus {
  return {
    gateway_id: 'procurement-optimization-gw-kedoqwtok1',
    name: 'procurement-optimization-gw',
    protocol: 'MCP',
    auth_type: 'AWS_IAM',
    status: 'READY',
    tools: [
      { name: 'optimize_suppliers', description: 'SLSQP multi-objective optimization — returns 3 Pareto strategies (Cost-Optimized, Balanced, Risk-Diversified) with TCO, risk scores, and supplier allocations', target_name: 'optimize-suppliers', status: 'active' },
      { name: 'query_supplier_data', description: 'Multi-purpose data access — supports query_types: get_all_suppliers, get_sourcing_summary, find_alternative_suppliers, get_supplier_performance, forecast_demand (Chronos-2), simulate_risk, list_risk_scenarios', target_name: 'query-supplier-data', status: 'active' },
      { name: 'explain_solution', description: 'Generate business explanations with trade-off analysis, key factors, risks to monitor, and volume discount opportunities for a selected Pareto strategy', target_name: 'explain-solution', status: 'active' },
      { name: 'create_purchase_requisitions', description: 'Generate SAP ME51N-format purchase requisitions from approved optimization solutions — groups by supplier, writes to S3', target_name: 'create-purchase-requisitions', status: 'active' },
    ],
    agents: [
      {
        name: 'Orchestrator',
        role: 'router',
        description: 'Intent classification router — classifies user queries and delegates to specialist agents. Uses lightweight model for fast routing.',
        model: 'us.amazon.nova-lite-v1:0',
        tools_used: [],
        status: 'active',
      },
      {
        name: 'Procurement Agent',
        role: 'specialist',
        description: 'Supplier selection, multi-objective optimization, Pareto frontier analysis, and purchase requisition generation.',
        model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
        tools_used: ['optimize_suppliers', 'query_supplier_data', 'explain_solution', 'create_purchase_requisitions'],
        status: 'active',
      },
      {
        name: 'Demand Forecast Agent',
        role: 'specialist',
        description: 'Chronos-2 time-series predictions (120M params) with P10/P50/P90 confidence intervals, gap analysis, and inventory planning.',
        model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
        tools_used: ['query_supplier_data'],
        status: 'active',
      },
      {
        name: 'Supplier Intelligence Agent',
        role: 'specialist',
        description: 'Geopolitical risk simulation (5 scenarios), supplier performance monitoring, single-source risk detection, and sourcing resilience analysis.',
        model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
        tools_used: ['query_supplier_data'],
        status: 'active',
      },
    ],
  };
}
