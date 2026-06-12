import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { suppliers, materials } from '../data/realData'

export default function DashboardCapabilities() {
  const [expandedSection, setExpandedSection] = useState<'tools' | 'suppliers' | 'materials' | null>(null)

  const tools = [
    { id: 1, name: 'Optimize Supplier Mix', desc: 'Generates Pareto-optimal solutions balancing cost, risk, and lead time' },
    { id: 2, name: 'Explain Recommendation', desc: 'Provides natural language explanations for optimization decisions' },
    { id: 3, name: 'Get Supplier Network', desc: 'Queries Neptune graph for supplier relationships and alternatives' },
    { id: 4, name: 'Get Pricing Data', desc: 'Retrieves pricing with volume tiers and discounts' },
    { id: 5, name: 'Get Demand Forecast', desc: 'Calls SageMaker for demand predictions' },
    { id: 6, name: 'Get Real-Time Alerts', desc: 'Fetches geopolitical risks, weather, port closures, and supply disruptions' }
  ]

  const toggleSection = (section: 'tools' | 'suppliers' | 'materials') => {
    setExpandedSection(expandedSection === section ? null : section)
  }

  return (
    <div className="viz-card" style={{ marginBottom: '24px' }}>
      <h3>🤖 Agent Capabilities</h3>
      
      {/* Capability Badges - Interactive */}
      <div className="agent-capabilities-compact" style={{ justifyContent: 'flex-start', gap: '16px', padding: '20px 0' }}>
        <button
          onClick={() => toggleSection('tools')}
          style={{
            padding: '12px 16px',
            backgroundColor: expandedSection === 'tools' ? '#8b5cf6' : '#e9d5ff',
            color: expandedSection === 'tools' ? 'white' : '#6b21a8',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s'
          }}
        >
          <span style={{ fontSize: '18px' }}>6</span>
          <span>Tools</span>
          {expandedSection === 'tools' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        <button
          onClick={() => toggleSection('suppliers')}
          style={{
            padding: '12px 16px',
            backgroundColor: expandedSection === 'suppliers' ? '#8b5cf6' : '#e9d5ff',
            color: expandedSection === 'suppliers' ? 'white' : '#6b21a8',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s'
          }}
        >
          <span style={{ fontSize: '18px' }}>15</span>
          <span>Suppliers</span>
          {expandedSection === 'suppliers' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        <button
          onClick={() => toggleSection('materials')}
          style={{
            padding: '12px 16px',
            backgroundColor: expandedSection === 'materials' ? '#8b5cf6' : '#e9d5ff',
            color: expandedSection === 'materials' ? 'white' : '#6b21a8',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s'
          }}
        >
          <span style={{ fontSize: '18px' }}>16</span>
          <span>Materials</span>
          {expandedSection === 'materials' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      <p style={{ color: '#64748b', marginTop: '16px', lineHeight: '1.6' }}>
        The Procurement Optimization Agent uses multi-objective optimization to balance cost, risk, and lead time across your supplier network. 
        It analyzes 15 qualified suppliers and 16 materials to generate Pareto-optimal solutions for your production needs.
      </p>

      {/* Expanded Sections */}
      {expandedSection === 'tools' && (
        <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #e2e8f0' }}>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#1e293b' }}>Agent Tools:</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {tools.map((tool) => (
              <div key={tool.id} style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '6px', borderLeft: '3px solid #8b5cf6' }}>
                <div style={{ fontWeight: '600', fontSize: '13px', color: '#1e293b' }}>{tool.id}. {tool.name}</div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{tool.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {expandedSection === 'suppliers' && (
        <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #e2e8f0' }}>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#1e293b' }}>Qualified Suppliers:</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', maxHeight: '400px', overflowY: 'auto' }}>
            {suppliers.map((supplier) => (
              <div key={supplier.id} style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                <div style={{ fontWeight: '600', fontSize: '13px', color: '#1e293b' }}>{supplier.name}</div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                  📍 {supplier.location} | ⭐ {supplier.rating}/5 | ⏱️ {supplier.leadTimeDays}d
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {expandedSection === 'materials' && (
        <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #e2e8f0' }}>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#1e293b' }}>BOM Materials (16 items):</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', maxHeight: '400px', overflowY: 'auto' }}>
            {materials.map((material) => (
              <div key={material.id} style={{ padding: '12px', backgroundColor: '#f8fafc', borderRadius: '6px', borderLeft: '3px solid #3b82f6' }}>
                <div style={{ fontWeight: '600', fontSize: '13px', color: '#1e293b' }}>{material.name}</div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                  {material.category} | {material.criticalityLevel}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
