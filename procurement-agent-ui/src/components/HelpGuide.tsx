import { useState } from 'react'
import { MessageSquare, Package, Map, GitBranch, BarChart3, FileCheck, Settings2, ChevronRight, Zap, Target, Shield, Brain, Radio } from 'lucide-react'

type Section = 'overview' | 'tabs' | 'agentcore' | 'tips'

const TAB_GUIDES = [
  { icon: Package, name: 'Demand & Inventory', color: '#3b82f6', description: 'Starting point. Shows production schedule for 500 e-bikes/quarter, inventory gaps across 16 BOM materials, and demand forecasts.', steps: ['Review the production schedule and inventory status', 'Identify materials with supply gaps (highlighted in red)', 'Click "Optimize Procurement" to run the multi-objective optimizer'] },
  { icon: MessageSquare, name: 'Procurement Agent', color: '#8b5cf6', description: 'Chat with the AI procurement analyst. Ask questions, run optimizations, and get explanations in natural language.', steps: ['Ask "Optimize for 500 battery packs" to trigger optimization', 'Ask "Explain the Balanced solution" for trade-off analysis', 'Ask "Find alternative suppliers for motors" for graph queries', 'The right panel shows Pareto frontier and solution details'] },
  { icon: Map, name: 'Supplier Risk Map', color: '#10b981', description: 'Interactive Leaflet map showing supplier locations with risk heatmaps. Click suppliers to see performance history.', steps: ['Colored circles indicate geopolitical risk level', 'Blue-bordered suppliers are in the current solution', 'Click a supplier for detailed performance metrics (OTD, quality, defects)', 'Switch between solutions to see allocation changes on the map'] },
  { icon: GitBranch, name: 'Graph Explorer', color: '#f59e0b', description: 'Neptune graph database visualization. Explore supplier-material relationships, centrality, and network topology.', steps: ['View supplier centrality rankings (most connected suppliers)', 'Browse materials by category (Battery, Motor, Frame, Electronics)', 'Data comes from Amazon Neptune graph database', 'Shows real supply network relationships'] },
  { icon: BarChart3, name: 'Analysis', color: '#ef4444', description: 'Deep dive into optimization results. Compare solutions, adjust weights, view BOM details, and read AI reasoning.', steps: ['Select solutions from the Pareto frontier buttons at top', 'Use Weight Sliders to create custom optimizations (drag Cost/Risk/Lead Time)', 'Executive Dashboard shows KPIs, cost comparison, spend distribution', 'BOM table shows per-material supplier allocations and costs', 'AI Reasoning panel explains why each solution was chosen'] },
  { icon: FileCheck, name: 'Approve PRs', color: '#06b6d4', description: 'Generate and review SAP-style Purchase Requisitions from the selected optimization solution.', steps: ['Select a solution first (from Agent or Analysis tab)', 'PRs are grouped by supplier with line items', 'Review quantities, unit prices, and total costs', 'Each PR includes delivery dates and payment terms'] },
  { icon: Settings2, name: 'Defect Tracker', color: '#ef4444', description: 'Track supplier quality issues by severity (Critical/Major/Minor), manage recalls, and view corrective actions. Defect history feeds into the dynamic risk scoring model.', steps: ['Browse defects by supplier and material with severity classification', 'View root cause analysis and corrective actions taken', 'Track recall status (initiated, resolved, open)', 'Defect scores are automatically integrated into the optimization risk model'] },
  { icon: Shield, name: 'Risk Simulation', color: '#f59e0b', description: 'Model 5 geopolitical scenarios and see impact on your supply chain — freight costs, lead times, tariffs, and affected suppliers.', steps: ['Select a scenario: Strait of Hormuz, Suez Canal, Taiwan Strait, US-China Tariffs, or European Port Strike', 'View affected vs unaffected suppliers with cost and lead time impact', 'See per-supplier freight increase percentages and delivery delays', 'Get recommended actions for each scenario'] },
  { icon: Settings2, name: 'Operations', color: '#64748b', description: 'AgentCore enterprise features dashboard. Monitor Gateway, agents, Memory, Evaluators, and Cedar Policies.', steps: ['MCP Gateway: View 4 agents (Orchestrator + 3 specialists), 4 registered MCP tools, and connection details', 'Evaluations: See 9 deployed evaluators (7 built-in + 2 custom LLM-as-Judge), traces with latency and tool usage, runtime config', 'Cedar Policies: Review RBAC roles (Analyst/Manager/Admin) and guardrails', 'Agent Memory: View memory strategies (Semantic, Preferences, Summarization) and stored insights'] },
]

export default function HelpGuide() {
  const [section, setSection] = useState<Section>('overview')

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{ width: '220px', flexShrink: 0, background: '#f8fafc', borderRight: '1px solid #e2e8f0', padding: '20px 0' }}>
        <div style={{ padding: '0 16px 16px', fontSize: '16px', fontWeight: 700, color: '#1e293b' }}>
          User Guide
        </div>
        {([
          { key: 'overview' as Section, label: 'Overview' },
          { key: 'tabs' as Section, label: 'Feature Walkthrough' },
          { key: 'agentcore' as Section, label: 'AgentCore Features' },
          { key: 'tips' as Section, label: 'Tips & Shortcuts' },
        ]).map(item => (
          <button key={item.key} onClick={() => setSection(item.key)} style={{
            display: 'block', width: '100%', padding: '10px 16px', border: 'none',
            textAlign: 'left', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
            background: section === item.key ? '#fff' : 'transparent',
            color: section === item.key ? '#1e293b' : '#64748b',
            borderLeft: section === item.key ? '3px solid #3b82f6' : '3px solid transparent',
          }}>
            {item.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '28px 36px', background: '#fff' }}>
        {section === 'overview' && (
          <>
            <h1 style={{ margin: '0 0 8px', fontSize: '28px', fontWeight: 800, color: '#0f172a' }}>VoltCycle Procurement Agent</h1>
            <p style={{ margin: '0 0 24px', fontSize: '15px', color: '#64748b', lineHeight: '1.6' }}>
              AI-powered procurement optimization for e-bike manufacturing. This application uses a multi-agent orchestrator
              with 3 specialist agents, multi-objective optimization, Neptune graph database, and Amazon Bedrock AgentCore enterprise features.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '28px' }}>
              {[
                { icon: Zap, title: 'Optimize', desc: 'Pareto-optimal supplier selection across cost, risk, quality, and lead time', color: '#3b82f6' },
                { icon: Target, title: 'Analyze', desc: '16-material BOM analysis with 15 suppliers across USA, Europe, and Asia', color: '#10b981' },
                { icon: Shield, title: 'Govern', desc: 'Cedar policies, memory persistence, evaluators, and MCP Gateway', color: '#8b5cf6' },
              ].map(c => (
                <div key={c.title} style={{ padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <c.icon size={24} style={{ color: c.color, marginBottom: '8px' }} />
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#1e293b', marginBottom: '4px' }}>{c.title}</div>
                  <div style={{ fontSize: '13px', color: '#64748b', lineHeight: '1.4' }}>{c.desc}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#1e293b', marginBottom: '12px' }}>Quick Start</h3>
            <ol style={{ margin: 0, padding: '0 0 0 20px', fontSize: '14px', color: '#475569', lineHeight: '2' }}>
              <li>Go to <strong>Demand & Inventory</strong> to see production context and inventory gaps</li>
              <li>Click <strong>Optimize Procurement</strong> to run the multi-objective optimizer</li>
              <li>Switch to <strong>Analysis</strong> to compare Cost-Optimized, Balanced, and Risk-Diversified solutions</li>
              <li>Use <strong>Procurement Agent</strong> chat for natural language queries and explanations</li>
              <li>Check <strong>Operations</strong> to see AgentCore Gateway, Memory, and Evaluators</li>
            </ol>
          </>
        )}

        {section === 'tabs' && (
          <>
            <h2 style={{ margin: '0 0 20px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>Feature Walkthrough</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {TAB_GUIDES.map(tab => (
                <div key={tab.name} style={{ borderRadius: '12px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 18px', background: '#f8fafc' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${tab.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <tab.icon size={16} style={{ color: tab.color }} />
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#1e293b' }}>{tab.name}</div>
                  </div>
                  <div style={{ padding: '14px 18px' }}>
                    <p style={{ margin: '0 0 10px', fontSize: '13px', color: '#475569', lineHeight: '1.5' }}>{tab.description}</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {tab.steps.map((step, i) => (
                        <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '13px', color: '#334155' }}>
                          <ChevronRight size={14} style={{ color: tab.color, flexShrink: 0, marginTop: '2px' }} />
                          {step}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {section === 'agentcore' && (
          <>
            <h2 style={{ margin: '0 0 20px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>AgentCore Enterprise Features</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {[
                { icon: Radio, title: 'MCP Gateway', id: 'READY — 4 tools, 4 agents', desc: 'Exposes 4 Lambda tools (optimize_suppliers, query_supplier_data, explain_solution, create_purchase_requisitions) via Model Context Protocol. 4 agents: Orchestrator (Nova Lite router) + 3 specialists (Procurement, Forecast, Intelligence on Claude Sonnet 4). All agents share tools via JWT auth.', color: '#3b82f6' },
                { icon: Brain, title: 'AgentCore Memory', id: 'ACTIVE — 3 strategies', desc: '3 strategies: SEMANTIC (supplier insights, top_k=5), USER_PREFERENCE (optimization preferences, top_k=3), SUMMARIZATION (session summaries). Events auto-expire after 90 days. Persists context across sessions per actor_id.', color: '#10b981' },
                { icon: Shield, title: 'Policy Engine + Cedar', id: 'ACTIVE — LOG_ONLY', desc: 'Cedar-based authorization controlling who can invoke which tools. RBAC roles: Analyst (read-only data + explanations), ProcurementManager (optimize + PRs up to $5M), Admin (full access). 9 Cedar policies deployed including deny rules for excessive quantities (>100K) and budgets (>$10M).', color: '#8b5cf6' },
                { icon: Target, title: 'Evaluators', id: '9 evaluators — 100% sampling', desc: '7 built-in evaluators (GoalSuccessRate, Correctness, ToolSelectionAccuracy, ToolParameterAccuracy, Helpfulness, Faithfulness, Harmfulness) + 2 custom LLM-as-Judge: ProcurementToolAccuracy (TOOL_CALL level, 1-5 scale for optimization correctness) and ProcurementQuality (SESSION level, 1-5 scale for overall procurement guidance). All run at 100% sampling via online eval config.', color: '#f59e0b' },
              ].map(f => (
                <div key={f.title} style={{ padding: '18px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <f.icon size={20} style={{ color: f.color }} />
                    <span style={{ fontSize: '16px', fontWeight: 700, color: '#1e293b' }}>{f.title}</span>
                    <span style={{ padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontFamily: 'monospace', background: '#f1f5f9', color: '#64748b' }}>{f.id}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '13px', color: '#475569', lineHeight: '1.5' }}>{f.desc}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {section === 'tips' && (
          <>
            <h2 style={{ margin: '0 0 20px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>Tips & Shortcuts</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px', color: '#334155' }}>
              {[
                'Type "optimize" in the chat to trigger a full Pareto frontier optimization',
                'Click solution cards in the Agent tab to see detailed supplier allocations',
                'Use Weight Sliders in Analysis to create custom Cost/Risk/Lead Time trade-offs',
                'The Supplier Risk Map highlights suppliers in the current solution with blue borders',
                'The Graph Explorer shows Neptune-sourced supplier centrality and network topology',
                'All data is real — 15 suppliers, 16 materials, with actual pricing and risk scores',
                'The Operations tab shows live AgentCore resource status queried from AWS APIs',
                'Memory strategies extract insights automatically from every conversation',
                'Cedar policies are in LOG_ONLY mode — switch to ENFORCE for production',
                'The MCP Gateway URL can be used by any MCP-compatible agent to access tools',
              ].map((tip, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', padding: '10px 14px', borderRadius: '8px', background: i % 2 === 0 ? '#f8fafc' : '#fff' }}>
                  <span style={{ color: '#3b82f6', fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                  {tip}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
