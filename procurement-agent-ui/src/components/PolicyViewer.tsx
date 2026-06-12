import { useState, useEffect } from 'react'
import { Shield, ShieldCheck, ShieldX, Users, Lock } from 'lucide-react'
import { fetchPolicies, type CedarPolicy, type PolicyRole } from '../services/adminApi'

type Tab = 'roles' | 'policies'

export default function PolicyViewer() {
  const [tab, setTab] = useState<Tab>('roles')
  const [policies, setPolicies] = useState<CedarPolicy[]>([])
  const [roles, setRoles] = useState<PolicyRole[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedPolicy, setExpandedPolicy] = useState<string | null>(null)

  useEffect(() => {
    fetchPolicies().then(data => {
      setPolicies(data.policies)
      setRoles(data.roles)
      setLoading(false)
    })
  }, [])

  const permitCount = policies.filter(p => p.effect === 'permit').length
  const forbidCount = policies.filter(p => p.effect === 'forbid').length

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: '#1e293b' }}>Cedar Policies</h2>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
          AgentCore PolicyEngine with Cedar RBAC and guardrails
        </p>
      </div>

      {/* Live policy engine info */}
      <div style={{
        display: 'flex', gap: '10px', marginBottom: '16px', padding: '10px 14px',
        background: '#faf5ff', borderRadius: '8px', border: '1px solid #d8b4fe', fontSize: '12px',
      }}>
        <span style={{ color: '#7c3aed', fontWeight: 600 }}>Policy Engine:</span>
        <span style={{ fontFamily: 'monospace', color: '#6d28d9' }}>ProcurementPolicyEngine</span>
        <span style={{ color: '#d8b4fe' }}>|</span>
        <span style={{ color: '#7c3aed' }}>Mode: LOG_ONLY (evaluates without blocking)</span>
        <span style={{ color: '#d8b4fe' }}>|</span>
        <span style={{ color: '#16a34a', fontWeight: 600 }}>ACTIVE</span>
      </div>

      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
        <StatCard icon={Shield} label="Total Policies" value={policies.length} color="#3b82f6" />
        <StatCard icon={ShieldCheck} label="Permit" value={permitCount} color="#10b981" />
        <StatCard icon={ShieldX} label="Forbid (Guardrails)" value={forbidCount} color="#ef4444" />
        <StatCard icon={Users} label="Roles" value={roles.length} color="#8b5cf6" />
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '2px', marginBottom: '20px', background: '#f1f5f9', borderRadius: '8px', padding: '3px' }}>
        {([['roles', 'Roles & Permissions', Users], ['policies', 'Cedar Policies', Shield]] as const).map(([key, label, Icon]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            padding: '8px', borderRadius: '6px', border: 'none', cursor: 'pointer',
            fontSize: '13px', fontWeight: 600,
            background: tab === key ? '#fff' : 'transparent',
            color: tab === key ? '#1e293b' : '#94a3b8',
            boxShadow: tab === key ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
          }}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Loading...</div>
      ) : tab === 'roles' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {roles.map(role => (
            <div key={role.name} style={{
              background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0',
              padding: '16px 20px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{
                    width: '32px', height: '32px', borderRadius: '8px', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    background: role.name === 'Admin' ? '#fef3c7' : role.name === 'ProcurementManager' ? '#eff6ff' : '#f0fdf4',
                  }}>
                    {role.name === 'Admin' ? <Lock size={16} style={{ color: '#f59e0b' }} />
                      : <Users size={16} style={{ color: role.name === 'ProcurementManager' ? '#3b82f6' : '#10b981' }} />}
                  </div>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{role.name}</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>{role.description}</div>
                  </div>
                </div>
                {role.max_budget_authority > 0 && (
                  <span style={{
                    padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
                    background: '#fef3c7', color: '#92400e',
                  }}>
                    Budget: ${(role.max_budget_authority / 1000000).toFixed(0)}M
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>Tools</div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {role.allowed_tools.map(t => (
                      <span key={t} style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                        background: '#eff6ff', color: '#3b82f6', fontWeight: 500,
                      }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>Actions</div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {role.allowed_actions.map(a => (
                      <span key={a} style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                        background: '#f0fdf4', color: '#16a34a', fontWeight: 500,
                      }}>
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Cedar policy list */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {policies.map(policy => (
            <div key={policy.name} style={{
              background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0',
              overflow: 'hidden',
            }}>
              <div
                onClick={() => setExpandedPolicy(expandedPolicy === policy.name ? null : policy.name)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '12px 16px', cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {policy.effect === 'permit'
                    ? <ShieldCheck size={14} style={{ color: '#10b981' }} />
                    : <ShieldX size={14} style={{ color: '#ef4444' }} />}
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                    {policy.name.replace(/_/g, ' ')}
                  </span>
                  {policy.role && (
                    <span style={{
                      padding: '1px 6px', borderRadius: '4px', fontSize: '10px',
                      background: '#f1f5f9', color: '#64748b',
                    }}>
                      {policy.role}
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>{policy.description}</span>
              </div>
              {expandedPolicy === policy.name && (
                <div style={{ padding: '0 16px 12px' }}>
                  <pre style={{
                    margin: 0, padding: '12px', borderRadius: '8px',
                    background: '#0f172a', color: '#e2e8f0', fontSize: '12px',
                    fontFamily: 'monospace', overflow: 'auto', lineHeight: '1.5',
                  }}>
                    {policy.statement}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: { icon: typeof Shield; label: string; value: number; color: string }) {
  return (
    <div style={{ padding: '14px', borderRadius: '12px', background: '#fff', border: '1px solid #e2e8f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
        <Icon size={13} style={{ color }} />
        <span style={{ fontSize: '11px', fontWeight: 500, color: '#94a3b8' }}>{label}</span>
      </div>
      <div style={{ fontSize: '22px', fontWeight: 700, color }}>{value}</div>
    </div>
  )
}
