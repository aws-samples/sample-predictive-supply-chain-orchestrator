import { useState } from 'react'

type Diagram = 'conceptual' | 'technical' | 'dataflow'

const BOX = (label: string, sub: string, color: string, opts?: { width?: string; mono?: boolean }) => (
  <div style={{
    padding: '10px 14px', borderRadius: '8px', border: `2px solid ${color}`,
    background: `${color}10`, textAlign: 'center', width: opts?.width || 'auto',
  }}>
    <div style={{ fontSize: '12px', fontWeight: 700, color }}>{label}</div>
    <div style={{ fontSize: '10px', color: '#64748b', fontFamily: opts?.mono ? 'monospace' : 'inherit' }}>{sub}</div>
  </div>
)

const ARROW = ({ direction = 'down', label = '' }: { direction?: 'down' | 'right' | 'left'; label?: string }) => (
  <div style={{
    display: 'flex', flexDirection: direction === 'down' ? 'column' : 'row',
    alignItems: 'center', gap: '2px', padding: direction === 'down' ? '4px 0' : '0 4px',
  }}>
    {label && <span style={{ fontSize: '9px', color: '#94a3b8', fontStyle: 'italic' }}>{label}</span>}
    <span style={{ fontSize: '14px', color: '#94a3b8' }}>
      {direction === 'down' ? '▼' : direction === 'right' ? '▶' : '◀'}
    </span>
  </div>
)

export default function ArchitecturePage() {
  const [diagram, setDiagram] = useState<Diagram>('conceptual')

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{ width: '220px', flexShrink: 0, background: '#f8fafc', borderRight: '1px solid #e2e8f0', padding: '20px 0' }}>
        <div style={{ padding: '0 16px 16px', fontSize: '16px', fontWeight: 700, color: '#1e293b' }}>
          Architecture
        </div>
        {([
          { key: 'conceptual' as Diagram, label: 'Conceptual Overview' },
          { key: 'technical' as Diagram, label: 'Technical Stack' },
          { key: 'dataflow' as Diagram, label: 'Data Flow' },
        ]).map(item => (
          <button key={item.key} onClick={() => setDiagram(item.key)} style={{
            display: 'block', width: '100%', padding: '10px 16px', border: 'none',
            textAlign: 'left', cursor: 'pointer', fontSize: '13px', fontWeight: 500,
            background: diagram === item.key ? '#fff' : 'transparent',
            color: diagram === item.key ? '#1e293b' : '#64748b',
            borderLeft: diagram === item.key ? '3px solid #3b82f6' : '3px solid transparent',
          }}>
            {item.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '28px 36px', background: '#fff' }}>

        {/* ── CONCEPTUAL ── */}
        {diagram === 'conceptual' && (
          <>
            <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>Conceptual Overview</h2>
            <p style={{ margin: '0 0 24px', fontSize: '13px', color: '#64748b' }}>How the procurement optimization agent works at a high level</p>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0' }}>
              {/* User */}
              {BOX('Procurement Team', 'VoltCycle e-bike manufacturing', '#3b82f6', { width: '280px' })}

              {/* Two paths */}
              <div style={{ display: 'flex', gap: '40px', margin: '8px 0', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <ARROW direction="down" label="button click" />
                  <div style={{
                    padding: '10px 16px', borderRadius: '10px', border: '2px solid #10b981',
                    background: '#10b98110', textAlign: 'center', width: '180px',
                  }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#10b981' }}>Direct API</div>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>Flask Lambda → Tools</div>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <ARROW direction="down" label="natural language" />
                  {BOX('Orchestrator (Nova Lite)', 'Intent classification → routes to specialist', '#f59e0b', { width: '280px' })}
                  <ARROW direction="down" label="routes to" />
                  <div style={{ display: 'flex', gap: '10px' }}>
                    {BOX('Procurement Agent', 'Optimization, Pareto, PRs', '#3b82f6')}
                    {BOX('Demand Forecast Agent', 'Chronos-2 predictions', '#22c55e')}
                    {BOX('Supplier Intelligence Agent', 'Risk simulation, performance', '#ef4444')}
                  </div>
                </div>
              </div>

              <ARROW direction="down" label="both paths invoke" />

              {/* Tools */}
              <div style={{
                padding: '16px 20px', borderRadius: '12px', border: '2px solid #f59e0b',
                background: '#f59e0b08', width: '500px', textAlign: 'center',
              }}>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#f59e0b', marginBottom: '8px' }}>Lambda Tools (shared)</div>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '12px' }}>Shared across all agents via MCP Gateway</div>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  {BOX('Optimize', 'Pareto frontier', '#10b981')}
                  {BOX('Query', 'Neptune graph', '#f59e0b')}
                  {BOX('Explain', 'Business context', '#06b6d4')}
                  {BOX('Create PRs', 'SAP integration', '#ef4444')}
                  {BOX('Forecast', 'Chronos-2 SageMaker', '#ec4899')}
                </div>
              </div>
              <ARROW direction="down" label="tool invocations" />

              {/* Data Layer */}
              <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                <div style={{ padding: '14px 18px', borderRadius: '10px', border: '2px solid #10b981', background: '#10b98110', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#10b981' }}>Supply Network Graph</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>15 suppliers, 16 materials</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Amazon Neptune</div>
                </div>
                <div style={{ padding: '14px 18px', borderRadius: '10px', border: '2px solid #f59e0b', background: '#f59e0b10', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#f59e0b' }}>Optimization Engine</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Multi-objective (scipy)</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Cost, Risk, Quality, Lead Time</div>
                </div>
                <div style={{ padding: '14px 18px', borderRadius: '10px', border: '2px solid #8b5cf6', background: '#8b5cf610', textAlign: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#8b5cf6' }}>AgentCore Enterprise</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Memory, Policy, Evaluators</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>MCP Gateway</div>
                </div>
              </div>
              <ARROW direction="down" label="decisions" />

              {/* Outputs */}
              <div style={{ display: 'flex', gap: '12px' }}>
                {BOX('Pareto Solutions', 'Cost-Optimized / Balanced / Risk-Diversified', '#3b82f6')}
                {BOX('Purchase Requisitions', 'SAP-ready PRs by supplier', '#ef4444')}
                {BOX('Supplier Insights', 'Risk analysis + alternatives', '#10b981')}
              </div>
            </div>
          </>
        )}

        {/* ── TECHNICAL ── */}
        {diagram === 'technical' && (
          <>
            <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>Technical Stack</h2>
            <p style={{ margin: '0 0 24px', fontSize: '13px', color: '#64748b' }}>AWS services and 14 CDK stacks powering the application</p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Frontend tier */}
              <TierBox title="Presentation Tier" color="#3b82f6" items={[
                { name: 'CloudFront', detail: 'CDN distribution with OAI' },
                { name: 'S3', detail: 'Static React 19 / Vite / TypeScript app' },
                { name: 'Cognito', detail: '3 user personas (Analyst, Manager, Admin)' },
              ]} />

              {/* API tier */}
              <TierBox title="API Tier" color="#8b5cf6" items={[
                { name: 'API Gateway', detail: 'REST proxy + Cognito authorizer + CORS' },
                { name: 'Lambda (Flask)', detail: 'API handler via Mangum (VPC, 29s timeout)' },
              ]} />

              {/* Agent tier */}
              <TierBox title="Multi-Agent Orchestration" color="#f59e0b" items={[
                { name: 'Orchestrator', detail: 'Amazon Nova Lite — intent classification router' },
                { name: 'Procurement Agent', detail: 'Claude Sonnet 4 — optimization, Pareto strategies, PRs' },
                { name: 'Forecast Agent', detail: 'Claude Sonnet 4 — SageMaker Chronos-2 demand predictions' },
                { name: 'Intelligence Agent', detail: 'Claude Sonnet 4 — risk simulation, performance monitoring' },
              ]} />

              {/* AgentCore tier */}
              <TierBox title="AgentCore Enterprise" color="#8b5cf6" items={[
                { name: 'MCP Gateway', detail: '4 Lambda targets, JWT + IAM auth' },
                { name: 'Policy Engine', detail: 'Cedar RBAC — 3 roles, deny rules (LOG_ONLY mode)' },
                { name: 'Memory', detail: 'Semantic + Preference + Summarization (90-day TTL)' },
                { name: 'Evaluators', detail: '7 built-in + 2 custom LLM-as-Judge (100% sampling)' },
                { name: 'Guardrails', detail: 'Bedrock Guardrail — PII detection, content safety' },
              ]} />

              {/* ML tier */}
              <TierBox title="ML / Forecasting" color="#ec4899" items={[
                { name: 'SageMaker Endpoint', detail: 'Chronos-2 (120M params) on ml.g5.2xlarge GPU' },
                { name: 'JumpStart Model', detail: 'Probabilistic time-series: P10/P50/P90 quantiles' },
              ]} />

              {/* Compute tier */}
              <TierBox title="Tool Tier (Lambda)" color="#10b981" items={[
                { name: 'Optimization Tool', detail: '2048MB, scipy SLSQP engine, 60s timeout' },
                { name: 'Data Access Tool', detail: 'Neptune HTTP + S3 CSV (VPC private subnet)' },
                { name: 'Explainability Tool', detail: 'Business context generation via Bedrock' },
                { name: 'Shared Layer', detail: 'scipy, numpy, gremlin_python, pydantic, structlog' },
              ]} />

              {/* Data tier */}
              <TierBox title="Data Tier" color="#ef4444" items={[
                { name: 'Neptune', detail: 'Graph DB — 33 nodes, 41 edges (Gremlin + HTTP)' },
                { name: 'S3', detail: 'CSV data, PR storage, agent bundles, forecast data' },
                { name: 'VPC', detail: 'Private subnets + NAT Gateway for Neptune/SageMaker' },
              ]} />

              {/* Observability */}
              <TierBox title="Observability" color="#64748b" items={[
                { name: 'OTEL (auto-instrumented)', detail: 'AWS Distro for OpenTelemetry — traces + logs' },
                { name: 'CloudWatch', detail: 'Dashboards, alarms, structured JSON logs' },
                { name: 'AgentCore Evaluations', detail: 'Online eval results in CloudWatch log group' },
                { name: 'SNS', detail: 'Alert notifications for error thresholds' },
              ]} />
            </div>
          </>
        )}

        {/* ── DATA FLOW — User Workflow Journey ── */}
        {diagram === 'dataflow' && (
          <>
            <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 800, color: '#0f172a' }}>Procurement Workflow</h2>
            <p style={{ margin: '0 0 24px', fontSize: '13px', color: '#64748b' }}>End-to-end journey from demand forecasting to purchase requisitions</p>

            {/* Workflow steps */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0' }}>

              <FlowStep num={1} title="Demand & Forecast" detail="Review stock on hand for 18 BOM materials. Run SageMaker Chronos-2 (120M params) to generate P10/P50/P90 probabilistic demand forecasts over 60-90 days. Select confidence level — P90 for conservative procurement planning." color="#3b82f6" width="600px" />
              <ARROW direction="down" label="forecast quantities feed into optimizer" />

              <FlowStep num={2} title="Multi-Objective Optimization" detail="SLSQP solver minimizes weighted sum of Cost, Risk, and Lead Time. Generates 3 Pareto strategies: Cost-Optimized (lowest TCO, 60% max concentration), Balanced (recommended tradeoff, 40% max), Risk-Diversified (max resilience, 25% max). Considers volume discounts, regional freight, carrying cost, carbon pricing, and MOQ constraints." color="#10b981" width="600px" />
              <ARROW direction="down" label="3 Pareto-optimal solutions" />

              <FlowStep num={3} title="Analysis & Comparison" detail="Compare solutions on Pareto frontier chart. Adjust weights with interactive sliders to create custom strategies. Executive dashboard shows KPIs, cost comparison, and spend distribution. AI Reasoning panel explains trade-offs, risks to monitor, and volume discount opportunities." color="#8b5cf6" width="600px" />
              <ARROW direction="down" label="select preferred strategy" />

              <div style={{ display: 'flex', gap: '16px', width: '600px' }}>
                <div style={{ flex: 1 }}>
                  <FlowStep num={4} title="Supplier Exploration" detail="Risk Map: Leaflet map with 15 suppliers across 10 countries, color-coded by geopolitical risk. Graph Explorer: Neptune network showing supplier-material relationships, centrality, and alternative sourcing paths. Defect Tracker: quality history feeding into dynamic risk scores." color="#f59e0b" width="100%" />
                </div>
                <div style={{ flex: 1 }}>
                  <FlowStep num={5} title="Risk Simulation" detail="5 geopolitical scenarios: Strait of Hormuz blockade, Suez Canal disruption, Taiwan Strait crisis, US-China tariff escalation, European port strikes. Models freight cost increases, lead time delays, and tariff impacts per affected supplier." color="#ef4444" width="100%" />
                </div>
              </div>
              <ARROW direction="down" label="approve solution" />

              <FlowStep num={6} title="Purchase Requisitions" detail="Generate SAP ME51N-format PRs from the approved Pareto strategy. Grouped by supplier with material line items, quantities, unit prices, delivery dates, and payment terms. DRAFT status for review, then 'Send to ERP' for approval workflow." color="#06b6d4" width="600px" />
            </div>

            {/* Two access patterns */}
            <div style={{
              marginTop: '24px', padding: '16px 20px', borderRadius: '10px',
              background: '#f8fafc', border: '1px solid #e2e8f0',
            }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', marginBottom: '10px' }}>Two Access Patterns — Same Tools</div>
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', background: '#10b98108', border: '1px solid #10b98130' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#10b981', marginBottom: '4px' }}>Direct UI</div>
                  <div style={{ fontSize: '11px', color: '#64748b', lineHeight: '1.5' }}>
                    Button clicks → API Gateway → Flask Lambda → Tool Lambdas. Fast, deterministic, no LLM overhead. Best for structured workflows.
                  </div>
                </div>
                <div style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', background: '#8b5cf608', border: '1px solid #8b5cf630' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#8b5cf6', marginBottom: '4px' }}>Agent Chat</div>
                  <div style={{ fontSize: '11px', color: '#64748b', lineHeight: '1.5' }}>
                    Natural language → AgentCore Runtime → Orchestrator → Specialist Agent → MCP Gateway → Tool Lambdas. Adds reasoning, memory, and multi-turn context.
                  </div>
                </div>
              </div>
            </div>

            {/* Shared infra footer */}
            <div style={{
              marginTop: '12px', padding: '14px 20px', borderRadius: '10px',
              background: '#f8fafc', border: '1px solid #e2e8f0',
            }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', marginBottom: '8px' }}>Shared Infrastructure</div>
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}><strong style={{ color: '#64748b' }}>Neptune</strong> — Supplier network graph (15 suppliers, 18 materials)</div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}><strong style={{ color: '#64748b' }}>SageMaker</strong> — Chronos-2 120M param forecast (ml.g5.2xlarge GPU)</div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}><strong style={{ color: '#64748b' }}>AgentCore</strong> — Memory, MCP Gateway, Evaluators, Cedar Policies</div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}><strong style={{ color: '#64748b' }}>Guardrails</strong> — PII detection, content safety</div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function TierBox({ title, color, items }: { title: string; color: string; items: { name: string; detail: string }[] }) {
  return (
    <div style={{ borderRadius: '10px', border: `1px solid ${color}30`, overflow: 'hidden' }}>
      <div style={{ padding: '8px 14px', background: `${color}10`, fontSize: '12px', fontWeight: 700, color, borderBottom: `1px solid ${color}30` }}>
        {title}
      </div>
      <div style={{ display: 'flex', gap: '0', flexWrap: 'wrap' }}>
        {items.map(item => (
          <div key={item.name} style={{ flex: '1 1 200px', padding: '10px 14px', borderRight: '1px solid #f1f5f9' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{item.name}</div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{item.detail}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FlowStep({ num, title, detail, color, width }: { num: number; title: string; detail: string; color: string; width?: string }) {
  return (
    <div style={{
      display: 'flex', gap: '10px', alignItems: 'flex-start', padding: '12px 16px',
      borderRadius: '10px', border: `1px solid ${color}40`, background: `${color}08`,
      width: width || '600px',
    }}>
      <div style={{
        width: '24px', height: '24px', borderRadius: '50%', background: color,
        color: '#fff', fontSize: '12px', fontWeight: 800, display: 'flex',
        alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>{num}</div>
      <div>
        <div style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{title}</div>
        <div style={{ fontSize: '11px', color: '#64748b', lineHeight: '1.4' }}>{detail}</div>
      </div>
    </div>
  )
}
