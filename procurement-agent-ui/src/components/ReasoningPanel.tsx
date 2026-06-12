import type { OptimizationSolution } from '../data/realData'

interface ReasoningPanelProps {
  solution: OptimizationSolution | null
}

export default function ReasoningPanel({ solution }: ReasoningPanelProps) {
  if (!solution || !solution.reasoning) {
    return (
      <div style={{ 
        padding: '24px', 
        background: 'white', 
        borderRadius: '8px', 
        border: '1px solid #e2e8f0',
        textAlign: 'center',
        color: '#94a3b8'
      }}>
        Select a solution to see AI reasoning
      </div>
    )
  }

  const { reasoning } = solution

  return (
    <div style={{ 
      padding: '24px', 
      background: 'white', 
      borderRadius: '8px', 
      border: '1px solid #e2e8f0'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <span style={{ fontSize: '20px' }}>🤖</span>
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>
            Agent Reasoning
          </h3>
        </div>
        <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
          {reasoning.summary}
        </p>
      </div>

      {/* Key Factors */}
      <div style={{ marginBottom: '20px' }}>
        <h4 style={{ 
          fontSize: '14px', 
          fontWeight: '600', 
          color: '#334155', 
          marginBottom: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          Key Factors
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {reasoning.keyFactors.map((factor, idx) => (
            <div key={idx} style={{ 
              display: 'flex', 
              gap: '8px', 
              fontSize: '14px',
              color: '#475569'
            }}>
              <span style={{ color: '#10b981', fontWeight: '600' }}>✓</span>
              <span>{factor}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trade-offs */}
      <div style={{ marginBottom: '20px' }}>
        <h4 style={{ 
          fontSize: '14px', 
          fontWeight: '600', 
          color: '#334155', 
          marginBottom: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          Trade-offs
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {reasoning.tradeOffs.map((tradeoff, idx) => (
            <div key={idx} style={{ 
              display: 'flex', 
              gap: '8px', 
              fontSize: '14px',
              color: '#475569'
            }}>
              <span style={{ color: '#f59e0b', fontWeight: '600' }}>⚖️</span>
              <span>{tradeoff}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risks */}
      <div style={{ marginBottom: '20px' }}>
        <h4 style={{ 
          fontSize: '14px', 
          fontWeight: '600', 
          color: '#334155', 
          marginBottom: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          Risks to Monitor
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {reasoning.risks.map((risk, idx) => (
            <div key={idx} style={{ 
              display: 'flex', 
              gap: '8px', 
              fontSize: '14px',
              color: '#475569'
            }}>
              <span style={{ color: '#ef4444', fontWeight: '600' }}>⚠️</span>
              <span>{risk}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Volume Discounts */}
      {reasoning.volumeDiscounts && reasoning.volumeDiscounts.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ 
            fontSize: '14px', 
            fontWeight: '600', 
            color: '#334155', 
            marginBottom: '12px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            Volume Discount Opportunities
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {reasoning.volumeDiscounts.map((discount, idx) => (
              <div key={idx} style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px',
                background: '#f0fdf4',
                borderRadius: '6px',
                border: '1px solid #bbf7d0'
              }}>
                <span style={{ fontSize: '14px', color: '#166534' }}>
                  {discount.description}
                </span>
                <span style={{ 
                  fontSize: '14px', 
                  fontWeight: '600', 
                  color: '#15803d'
                }}>
                  ${(discount.savings / 1000).toFixed(0)}K
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contract Compliance */}
      {reasoning.contractCompliance && reasoning.contractCompliance.length > 0 && (
        <div>
          <h4 style={{ 
            fontSize: '14px', 
            fontWeight: '600', 
            color: '#334155', 
            marginBottom: '12px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            Contract Compliance
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {reasoning.contractCompliance.map((contract, idx) => (
              <div key={idx} style={{ 
                display: 'flex', 
                flexDirection: 'column',
                gap: '4px',
                padding: '12px',
                background: '#f8fafc',
                borderRadius: '6px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: '600', 
                  color: '#334155'
                }}>
                  {contract.supplier}
                </div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>
                  {contract.commitment}
                </div>
                <div style={{ 
                  fontSize: '13px', 
                  color: '#10b981',
                  fontWeight: '500'
                }}>
                  {contract.status}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
