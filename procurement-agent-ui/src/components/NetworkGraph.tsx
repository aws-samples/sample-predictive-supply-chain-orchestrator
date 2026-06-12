interface NetworkGraphProps {
  networkData: {
    nodes: Array<{ id: string; label: string; type: string; size: number; risk?: number }>
    links: Array<{ source: string; target: string; value: number; price: number }>
  }
}

export default function NetworkGraph({ networkData }: NetworkGraphProps) {
  const { nodes, links } = networkData

  // Simple force-directed layout simulation (simplified for demo)
  const width = 600
  const height = 450
  const centerX = width / 2
  const centerY = height / 2

  // Position materials in center cluster, suppliers in circle around them
  const materialNodes = nodes.filter(n => n.type === 'material')
  const supplierNodes = nodes.filter(n => n.type === 'supplier')

  const angleStep = (2 * Math.PI) / supplierNodes.length
  const radius = 180

  // Arrange materials in a grid in the center
  const materialsPerRow = 4
  const materialSpacing = 40
  
  // Get material category icon
  const getMaterialIcon = (materialId: string) => {
    if (materialId.includes('BAT')) return '🔋'
    if (materialId.includes('MOT')) return '⚙️'
    if (materialId.includes('FRM')) return '🔧'
    if (materialId.includes('ELC')) return '💡'
    if (materialId.includes('STD')) return '🛞'
    return '📦'
  }
  
  // Get country flag emoji
  const getCountryFlag = (supplierId: string) => {
    const supplier = supplierNodes.find(n => n.id === supplierId)
    if (!supplier) return '🏭'
    
    // Map supplier to country flag based on risk and name patterns
    if (supplier.label.includes('Battery') || supplier.label.includes('Display')) return '🇨🇳'
    if (supplier.label.includes('PowerCell')) return '🇰🇷'
    if (supplier.label.includes('EcoEnergy') || supplier.label.includes('ElectroVision') || 
        supplier.label.includes('AlumaTech') || supplier.label.includes('RollerTech')) return '🇺🇸'
    if (supplier.label.includes('DriveMotor') || supplier.label.includes('BrakeSafe')) return '🇩🇪'
    if (supplier.label.includes('TorqueTech')) return '🇹🇼'
    if (supplier.label.includes('CarbonFiber')) return '🇯🇵'
    if (supplier.label.includes('FrameWorks')) return '🇬🇧'
    if (supplier.label.includes('WheelCraft')) return '🇳🇱'
    if (supplier.label.includes('SmartDisplay')) return '🇮🇳'
    return '🏭'
  }

  return (
    <div className="network-graph-container">
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        {/* Links */}
        {links.map((link, idx) => {
          const supplierIdx = supplierNodes.findIndex(n => n.id === link.source)
          const materialIdx = materialNodes.findIndex(n => n.id === link.target)
          
          if (supplierIdx === -1 || materialIdx === -1) return null
          
          const sourceX = centerX + radius * Math.cos(supplierIdx * angleStep)
          const sourceY = centerY + radius * Math.sin(supplierIdx * angleStep)
          
          const row = Math.floor(materialIdx / materialsPerRow)
          const col = materialIdx % materialsPerRow
          const targetX = centerX - (materialsPerRow * materialSpacing) / 2 + col * materialSpacing
          const targetY = centerY - 60 + row * 30

          return (
            <line
              key={idx}
              x1={sourceX}
              y1={sourceY}
              x2={targetX}
              y2={targetY}
              stroke="#cbd5e1"
              strokeWidth={1}
              opacity={0.4}
            />
          )
        })}

        {/* Material Nodes (center cluster) */}
        {materialNodes.map((node, idx) => {
          const row = Math.floor(idx / materialsPerRow)
          const col = idx % materialsPerRow
          const x = centerX - (materialsPerRow * materialSpacing) / 2 + col * materialSpacing
          const y = centerY - 60 + row * 30

          return (
            <g key={node.id}>
              <circle
                cx={x}
                cy={y}
                r={12}
                fill="#3b82f6"
                stroke="#1e40af"
                strokeWidth={2}
                opacity={0.9}
              />
              <text
                x={x}
                y={y + 1}
                textAnchor="middle"
                fontSize="14"
                fill="white"
              >
                {getMaterialIcon(node.id)}
              </text>
              <title>{node.label}</title>
            </g>
          )
        })}

        {/* Supplier Nodes (circle) */}
        {supplierNodes.map((node, idx) => {
          const x = centerX + radius * Math.cos(idx * angleStep)
          const y = centerY + radius * Math.sin(idx * angleStep)
          const riskColor = (node.risk ?? 5) < 2.5 ? '#10b981' : (node.risk ?? 5) < 3.5 ? '#f59e0b' : '#ef4444'

          return (
            <g key={node.id}>
              <circle
                cx={x}
                cy={y}
                r={node.size / 1.5}
                fill={riskColor}
                stroke="#fff"
                strokeWidth={2.5}
                opacity={0.95}
              />
              <text
                x={x}
                y={y + 2}
                textAnchor="middle"
                fontSize="16"
                fill="white"
              >
                {getCountryFlag(node.id)}
              </text>
              <text
                x={x}
                y={y + node.size / 1.5 + 14}
                textAnchor="middle"
                fontSize="11"
                fill="#1e293b"
                fontWeight="600"
              >
                {node.label}
              </text>
              <text
                x={x}
                y={y + node.size / 1.5 + 26}
                textAnchor="middle"
                fontSize="9"
                fill="#64748b"
              >
                Risk: {node.risk?.toFixed(1)}
              </text>
            </g>
          )
        })}
        
        {/* Center label */}
        <text
          x={centerX}
          y={centerY + 100}
          textAnchor="middle"
          fontSize="12"
          fill="#64748b"
          fontWeight="600"
        >
          16 Materials
        </text>
      </svg>

      <div className="network-legend">
        <div className="legend-section">
          <div className="legend-title">Materials</div>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-icon">🔋</span>
              <span>Battery</span>
            </div>
            <div className="legend-item">
              <span className="legend-icon">⚙️</span>
              <span>Motor</span>
            </div>
            <div className="legend-item">
              <span className="legend-icon">🔧</span>
              <span>Frame</span>
            </div>
            <div className="legend-item">
              <span className="legend-icon">💡</span>
              <span>Electronics</span>
            </div>
            <div className="legend-item">
              <span className="legend-icon">🛞</span>
              <span>Wheels/Parts</span>
            </div>
          </div>
        </div>
        
        <div className="legend-section">
          <div className="legend-title">Supplier Risk</div>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: '#10b981' }}></span>
              <span>Low (&lt;2.5)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }}></span>
              <span>Medium (2.5-3.5)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: '#ef4444' }}></span>
              <span>High (&gt;3.5)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
