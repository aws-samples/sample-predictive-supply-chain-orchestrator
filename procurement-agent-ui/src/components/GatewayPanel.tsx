import { useState, useEffect } from 'react'
import { Radio, Plug, Shield, CheckCircle, Activity, Brain, Cpu, GitBranch, ChevronDown, ChevronRight, Zap } from 'lucide-react'
import { fetchGatewayStatus, type GatewayStatus, type AgentInfo } from '../services/adminApi'

export default function GatewayPanel() {
  const [gateway, setGateway] = useState<GatewayStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  useEffect(() => {
    fetchGatewayStatus().then(data => {
      setGateway(data)
      setLoading(false)
    })
  }, [])

  if (loading || !gateway) {
    return <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading...</div>
  }

  const orchestrator = gateway.agents?.find(a => a.role === 'router')
  const specialists = gateway.agents?.filter(a => a.role === 'specialist') || []

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: 'var(--color-text)' }}>MCP Gateway</h2>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-text-muted)' }}>
          AgentCore Gateway exposing tools via Model Context Protocol
        </p>
      </div>

      {/* Gateway info card */}
      <div style={{
        background: 'var(--color-surface)', borderRadius: '12px', border: '1px solid var(--color-border)',
        padding: '20px', marginBottom: '24px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Radio size={18} style={{ color: 'var(--color-primary)' }} />
              <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text)' }}>{gateway.name}</span>
              <span style={{
                padding: '2px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
                background: gateway.status === 'ACTIVE' || gateway.status === 'READY' ? 'var(--color-success-light)' : 'var(--color-warning-light)',
                color: gateway.status === 'ACTIVE' || gateway.status === 'READY' ? 'var(--color-success)' : 'var(--color-warning)',
              }}>
                {gateway.status}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>ID: {gateway.gateway_id}</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '24px', marginTop: '16px' }}>
          <InfoChip icon={Plug} label="Protocol" value={gateway.protocol} />
          <InfoChip icon={Shield} label="Auth" value={gateway.auth_type} />
          <InfoChip icon={Activity} label="Tools" value={`${gateway.tools.length} registered`} />
          <InfoChip icon={Brain} label="Agents" value={`${gateway.agents?.length || 0} active`} />
        </div>
      </div>

      {/* Multi-Agent Architecture */}
      {gateway.agents && gateway.agents.length > 0 && (
        <>
          <div style={{ marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--color-text)' }}>Multi-Agent Orchestration</h3>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--color-text-muted)' }}>
              Intent classification routes to specialist agents via lightweight router
            </p>
          </div>

          {/* Orchestrator card */}
          {orchestrator && (
            <div style={{
              background: 'var(--color-nav-bg)', borderRadius: '12px', padding: '16px 20px',
              marginBottom: '8px', color: '#fff',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '32px', height: '32px', borderRadius: '8px',
                    background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <GitBranch size={16} style={{ color: '#fff' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700 }}>{orchestrator.name}</div>
                    <div style={{ fontSize: '11px', opacity: 0.7 }}>{orchestrator.description}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '8px', background: 'rgba(255,255,255,0.15)', fontWeight: 600 }}>
                    {orchestrator.model.split('/').pop()?.split(':')[0] || orchestrator.model}
                  </span>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: '3px',
                    padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 600,
                    background: 'rgba(34,197,94,0.2)', color: '#4ade80',
                  }}>
                    <CheckCircle size={9} /> active
                  </span>
                </div>
              </div>
              {/* Routing arrows */}
              <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                {specialists.map(agent => (
                  <div key={agent.name} style={{ textAlign: 'center', fontSize: '10px', opacity: 0.7 }}>
                    <div style={{ marginBottom: '2px' }}>|</div>
                    <div>{agent.name.replace(' Agent', '')}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Specialist agents */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
            {specialists.map(agent => (
              <AgentCard
                key={agent.name}
                agent={agent}
                expanded={expandedAgent === agent.name}
                onToggle={() => setExpandedAgent(expandedAgent === agent.name ? null : agent.name)}
              />
            ))}
          </div>
        </>
      )}

      {/* MCP Tools */}
      <div style={{ marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--color-text)' }}>Registered MCP Tools</h3>
        <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          All agents share tools via JWT-authenticated Gateway
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {gateway.tools.map(tool => (
          <div key={tool.name} style={{
            background: 'var(--color-surface)', borderRadius: '12px', border: '1px solid var(--color-border)',
            padding: '16px 20px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '6px',
                  background: 'var(--color-primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Plug size={14} style={{ color: 'var(--color-primary)' }} />
                </div>
                <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {tool.name}
                </span>
              </div>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '4px',
                padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                background: tool.status === 'active' ? 'var(--color-success-light)' : 'var(--color-danger-light)',
                color: tool.status === 'active' ? 'var(--color-success)' : 'var(--color-danger)',
              }}>
                <CheckCircle size={10} /> {tool.status}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.5', marginBottom: '8px' }}>
              {tool.description}
            </div>
            <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
              <span>Target: <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)' }}>{tool.target_name}</span></span>
              {gateway.agents && (
                <span>Used by: <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                  {gateway.agents.filter(a => a.tools_used.includes(tool.name)).map(a => a.name.replace(' Agent', '')).join(', ') || 'All'}
                </span></span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* MCP Protocol info */}
      <div style={{
        marginTop: '20px', padding: '16px 20px', background: 'var(--color-surface)',
        borderRadius: '12px', border: '1px solid var(--color-border)',
      }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '8px' }}>MCP Connection</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Protocol: </span>
            Model Context Protocol (MCP) over HTTPS
          </div>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Auth: </span>
            AWS IAM Signature V4 (no anonymous access)
          </div>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Access: </span>
            IAM-authenticated agents only
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Sub-components ── */

function AgentCard({ agent, expanded, onToggle }: { agent: AgentInfo; expanded: boolean; onToggle: () => void }) {
  const colorMap: Record<string, string> = {
    'Procurement Agent': 'var(--color-primary)',
    'Demand Forecast Agent': '#8b5cf6',
    'Supplier Intelligence Agent': '#f59e0b',
  }
  const color = colorMap[agent.name] || 'var(--color-primary)'

  return (
    <div style={{
      background: 'var(--color-surface)', borderRadius: '12px', border: '1px solid var(--color-border)',
      overflow: 'hidden',
    }}>
      <div onClick={onToggle} style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '14px 20px', cursor: 'pointer',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          <div style={{
            width: '28px', height: '28px', borderRadius: '6px',
            background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Brain size={14} style={{ color }} />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text)' }}>{agent.name}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '1px' }}>{agent.description}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 600,
            background: 'var(--color-success-light)', color: 'var(--color-success)',
          }}>
            <CheckCircle size={9} /> {agent.status}
          </span>
        </div>
      </div>
      {expanded && (
        <div style={{ padding: '0 20px 16px', borderTop: '1px solid var(--color-border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '14px' }}>
            <div>
              <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>Model</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Cpu size={11} style={{ color: 'var(--color-text-muted)' }} />
                <span style={{ fontSize: '12px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--color-text-secondary)' }}>
                  {agent.model.split('/').pop()?.split(':')[0] || agent.model}
                </span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>Tools</div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {agent.tools_used.map(tool => (
                  <span key={tool} style={{
                    display: 'inline-flex', alignItems: 'center', gap: '3px',
                    padding: '2px 8px', borderRadius: '8px', fontSize: '10px', fontWeight: 600,
                    background: color + '15', color,
                  }}>
                    <Zap size={8} /> {tool}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoChip({ icon: Icon, label, value }: { icon: typeof Plug; label: string; value: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <Icon size={14} style={{ color: 'var(--color-text-muted)' }} />
      <div>
        <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>{label}</div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)' }}>{value}</div>
      </div>
    </div>
  )
}
