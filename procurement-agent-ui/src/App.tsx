import { useState, useEffect } from 'react'
import { LogOut, MessageSquare, Map as MapIcon, BarChart3, FileCheck, GitBranch, Package, Settings2, HelpCircle, Layers, PanelRightOpen, PanelRightClose, ChevronLeft, ChevronRight, X, AlertTriangle, Zap, Shield } from 'lucide-react'
import ChatInterface, { type Message } from './components/ChatInterface'
import ParetoChart from './components/ParetoChart'
import SolutionCards from './components/SolutionCards'
import SupplierMap from './components/SupplierMap'
import PurchaseRequisitionPreview from './components/PurchaseRequisitionPreview'
import GraphAnalysis from './components/GraphAnalysis'
import ExecutiveDashboard from './components/ExecutiveDashboard'
import DemandContext, { type ConfidenceLevel } from './components/DemandContext'
import WeightSliders from './components/WeightSliders'
import BackendStatus from './components/BackendStatus'
import EvaluationsPanel from './components/EvaluationsPanel'
import MemoryExplorer from './components/MemoryExplorer'
import PolicyViewer from './components/PolicyViewer'
import GatewayPanel from './components/GatewayPanel'
import HelpGuide from './components/HelpGuide'
import ArchitecturePage from './components/ArchitecturePage'
import RiskSimulation from './components/RiskSimulation'
import DefectTracker from './components/DefectTracker'
import WorkflowStepper from './components/WorkflowStepper'
import ConfirmModal from './components/ConfirmModal'
import { useOptimization } from './hooks/useOptimization'
import { useAuth } from './auth/CognitoAuth'
import { fetchSuppliers, fetchSupplierPerformance, type BackendSupplier, type BackendPerformance, type SupplierMix } from './services/api'
import { paretoSolutions as fallbackSolutions } from './data/realData'
import './App.css'
import './components/BackendStatus.css'

type MaterialForecast = { material_id: string; summary: { total_p10: number; total_p50: number; total_p90: number; avg_daily_p50: number }; forecast?: any[]; error?: string }
type View = 'demand' | 'results' | 'map' | 'graph' | 'analysis' | 'approve' | 'defects' | 'risk' | 'ops' | 'architecture' | 'help'
type OpsTab = 'gateway' | 'evaluations' | 'policies' | 'memory'

interface NavGroup { label: string; items: { key: View; label: string; icon: typeof MessageSquare }[] }

const NAV_GROUPS: NavGroup[] = [
  { label: 'Plan', items: [
    { key: 'demand', label: 'Demand & Inventory', icon: Package },
    { key: 'graph', label: 'Supply Network', icon: GitBranch },
  ]},
  { label: 'Simulate', items: [
    { key: 'map', label: 'Global Risk Map', icon: MapIcon },
    { key: 'risk', label: 'Risk Simulation', icon: Shield },
    { key: 'defects', label: 'Defect Tracker', icon: AlertTriangle },
  ]},
  { label: 'Optimize', items: [
    { key: 'results' as View, label: 'Results', icon: Zap },
    { key: 'analysis', label: 'Analysis', icon: BarChart3 },
  ]},
  { label: 'Execute', items: [
    { key: 'approve', label: 'Requisitions', icon: FileCheck },
  ]},
  { label: 'Admin', items: [
    { key: 'ops', label: 'Operations', icon: Settings2 },
    { key: 'architecture', label: 'Architecture', icon: Layers },
    { key: 'help', label: 'Guide', icon: HelpCircle },
  ]},
]

function getInitialView(): View {
  const hash = window.location.hash.replace('#', '') as View
  const validViews: View[] = ['demand', 'results', 'map', 'graph', 'analysis', 'approve', 'defects', 'risk', 'ops', 'architecture', 'help']
  if (validViews.includes(hash)) return hash
  const stored = sessionStorage.getItem('activeView') as View | null
  if (stored && validViews.includes(stored)) return stored
  return 'demand'
}

function App() {
  const [selectedSolution, setSelectedSolution] = useState<string | null>('SOL-B')
  const [activeView, setActiveViewRaw] = useState<View>(getInitialView)
  const [selectedSupplier, setSelectedSupplier] = useState<string | null>(null)
  const [customSolution, setCustomSolution] = useState<any>(null)
  const [opsTab, setOpsTab] = useState<OpsTab>('gateway')
  const [liveSuppliers, setLiveSuppliers] = useState<BackendSupplier[]>([])
  const [livePerformance, setLivePerformance] = useState<BackendPerformance[]>([])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [agentOpen, setAgentOpen] = useState(false)
  const [agentPanelWidth, setAgentPanelWidth] = useState(480)
  const [activityMessages, setActivityMessages] = useState<Message[]>([])
  const [pendingAgentMessage, setPendingAgentMessage] = useState<string | null>(null)
  const [strategyExpanded, setStrategyExpanded] = useState(false)
  const [showPRConfirm, setShowPRConfirm] = useState(false)
  const [prsSubmitted, setPrsSubmitted] = useState(false)
  const [demandForecasts, setDemandForecasts] = useState<Record<string, MaterialForecast>>({})
  const [demandUseForecast, setDemandUseForecast] = useState(false)
  const [demandConfidenceLevel, setDemandConfidenceLevel] = useState<ConfidenceLevel>('p90')
  const [forecastMaterials, setForecastMaterials] = useState<{ material_id: string; quantity: number }[] | undefined>(undefined)
  const [forecastLoading, setForecastLoading] = useState(false)

  // Forecast loading tracked at App level for persistence
  const { user, logout } = useAuth()

  // Sync activeView → URL hash + sessionStorage
  const setActiveView = (view: View) => {
    setActiveViewRaw(view)
    window.location.hash = view
    sessionStorage.setItem('activeView', view)
  }

  // Listen for browser back/forward
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace('#', '') as View
      const validViews: View[] = ['demand', 'results', 'map', 'graph', 'analysis', 'approve', 'defects', 'risk', 'ops', 'architecture', 'help']
      if (validViews.includes(hash)) setActiveViewRaw(hash)
    }
    window.addEventListener('hashchange', onHashChange)
    // Set initial hash if not present
    if (!window.location.hash) window.location.hash = activeView
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    Promise.all([fetchSuppliers(), fetchSupplierPerformance()]).then(([sups, perf]) => {
      setLiveSuppliers(sups)
      setLivePerformance(perf)
    })
  }, [])

  const { solutions: liveSolutions, loading, backendStatus, computationTimeMs, hasRun, refetch } = useOptimization()
  const baseSolutions = liveSolutions && liveSolutions.length > 0 ? liveSolutions : (hasRun ? fallbackSolutions : [])
  const paretoSolutions = customSolution ? [...baseSolutions.filter((s: any) => s.id !== 'SOL-CUSTOM'), customSolution] : baseSolutions

  useEffect(() => {
    if (paretoSolutions.length > 0 && !selectedSolution) {
      setSelectedSolution(paretoSolutions.find((s: any) => s.name === 'Balanced')?.id || paretoSolutions[0].id)
    }
  }, [paretoSolutions.length])

  const messages: Message[] = []
  const currentSolution = paretoSolutions.find((s: any) => s.id === selectedSolution) || paretoSolutions[1]

  const noResultsNudge = (pageName: string) => (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, background: 'var(--color-bg)' }}>
      <div style={{ textAlign: 'center', maxWidth: 420 }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text)', marginBottom: 8 }}>No optimization results yet</div>
        <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
          {pageName} requires optimization results. Run optimization to generate Pareto-optimal procurement strategies.
        </div>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button onClick={() => { refetch(); setActiveView('results') }} style={{
            padding: '10px 24px', borderRadius: 'var(--radius-sm)', border: 'none',
            background: 'var(--color-primary)', color: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer',
          }}>
            Run Optimization
          </button>
          <button onClick={() => setActiveView('demand')} style={{
            padding: '10px 24px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)',
            background: 'var(--color-surface)', color: 'var(--color-text)', fontWeight: 600, fontSize: 13, cursor: 'pointer',
          }}>
            Plan Demand First
          </button>
        </div>
      </div>
    </div>
  )

  const handleOptimize = (materials?: { material_id: string; quantity: number }[]) => {
    setForecastMaterials(materials)
    setActivityMessages(prev => [...prev, {
      role: 'system' as const,
      content: materials && materials.length > 0
        ? `⚡ Optimization triggered with ${materials.length} forecast-driven materials`
        : '⚡ Optimization triggered from Demand & Inventory page',
      timestamp: new Date(),
    }])
    refetch(materials).then(() => {
      setActivityMessages(prev => [...prev, {
        role: 'system' as const,
        content: `✅ Optimization complete — ${paretoSolutions.length || 'multiple'} Pareto solutions generated`,
        timestamp: new Date(),
      }])
    })
    setActiveView('results')
  }
  const sideW = sidebarCollapsed ? 56 : 220

  /** Build a structured prompt for the agent to analyze a selected solution */
  function requestAgentAnalysis(solution: any) {
    const topAllocs = [...solution.allocations]
      .sort((a: any, b: any) => b.totalCost - a.totalCost)
      .slice(0, 5)
      .map((a: any) => `- ${a.materialName}: ${a.supplierName}, ${a.quantity} units @ $${a.unitPrice} = $${Math.round(a.totalCost / 1000)}K`)
      .join('\n')

    const supplierConc = (solution.supplierConcentration || [])
      .slice(0, 5)
      .map((sc: any) => `${sc.supplierName} ${sc.percentage}%`)
      .join(', ')

    const prompt = `Analyze the "${solution.name}" procurement strategy for our Q2 e-bike production:

- Total Cost: $${Math.round(solution.totalCost).toLocaleString()}
- Risk Score: ${solution.riskScore.toFixed(1)}/10
- Quality Score: ${solution.qualityScore.toFixed(1)}/10
- Max Lead Time: ${solution.maxLeadTimeDays} days
- ${solution.allocations.length} material allocations across ${new Set(solution.allocations.map((a: any) => a.supplierId)).size} suppliers
- Top supplier concentration: ${supplierConc}

Top 5 allocations by cost:
${topAllocs}

Provide your analysis: key factors, trade-offs compared to other strategies, risks to monitor, and your recommendation.`

    setPendingAgentMessage(prompt)
    setAgentOpen(true)
  }

  /* ──────────────────────── RENDER ──────────────────────── */
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ═══ LEFT SIDEBAR ═══ */}
      <aside style={{
        width: sideW, flexShrink: 0, display: 'flex', flexDirection: 'column',
        background: 'var(--color-nav-bg)', transition: 'width 0.2s ease', overflow: 'hidden',
      }}>
        <div onClick={() => setActiveView('demand')} style={{ height: 52, display: 'flex', alignItems: 'center', padding: '0 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0, gap: 10, cursor: 'pointer' }}>
          <img src="/vite.svg" alt="VoltCycle" style={{ width: 28, height: 28, flexShrink: 0 }} />
          {!sidebarCollapsed && (
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 14, color: '#fff', whiteSpace: 'nowrap', letterSpacing: '-0.01em' }}>VoltCycle</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', whiteSpace: 'nowrap', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.05em' }}>SUPPLY CHAIN OPS</div>
            </div>
          )}
        </div>
        <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {NAV_GROUPS.map((group, gi) => (
            <div key={group.label || `group-${gi}`} style={{ marginBottom: 4 }}>
              {!sidebarCollapsed && group.label && <div style={{ padding: '8px 16px 4px', fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{group.label}</div>}
              {group.items.map(item => {
                const active = activeView === item.key
                return (
                  <button key={item.key} onClick={() => setActiveView(item.key)} title={sidebarCollapsed ? item.label : undefined} style={{
                    display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                    padding: sidebarCollapsed ? '8px 0' : '7px 16px',
                    justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                    border: 'none', borderRadius: 0, cursor: 'pointer', fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    background: active ? 'rgba(255,255,255,0.08)' : 'transparent',
                    color: active ? '#fff' : 'rgba(255,255,255,0.5)',
                    borderLeft: active ? '3px solid var(--color-nav-indicator)' : '3px solid transparent',
                    transition: 'all 0.12s ease',
                  }}>
                    <item.icon size={16} strokeWidth={active ? 2.2 : 1.6} />
                    {!sidebarCollapsed && <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>}
                  </button>
                )
              })}
            </div>
          ))}
        </nav>
        <div style={{ padding: sidebarCollapsed ? '8px 0' : '8px 12px', borderTop: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <BackendStatus compact={sidebarCollapsed} />
        </div>
        <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: 10,
          border: 'none', borderTop: '1px solid rgba(255,255,255,0.06)', background: 'transparent',
          color: 'rgba(255,255,255,0.3)', cursor: 'pointer', fontSize: 11,
        }}>
          {sidebarCollapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /><span>Collapse</span></>}
        </button>
      </aside>

      {/* ═══ MAIN AREA (top bar + content + agent panel) ═══ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* ─ Top bar ─ */}
        <header style={{ height: 42, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 16px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {currentSolution && hasRun && (
              <span style={{ padding: '2px 10px', borderRadius: 10, fontSize: 11, fontWeight: 500, background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
                {currentSolution.name}: ${Math.round(currentSolution.totalCost / 1000)}K
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={() => setAgentOpen(!agentOpen)} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              border: agentOpen ? '1px solid var(--color-primary)' : '1px solid var(--border-color)',
              background: agentOpen ? 'var(--color-primary)' : 'var(--color-primary-light)',
              color: agentOpen ? '#fff' : 'var(--color-primary)',
              boxShadow: agentOpen ? 'none' : '0 0 0 3px rgba(37, 99, 235, 0.1)',
            }}>
              <MessageSquare size={14} /> AI Agent {agentOpen ? <PanelRightClose size={13} /> : <PanelRightOpen size={13} />}
            </button>
            {user && <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{user}</span>}
            <button onClick={logout} style={{ display: 'flex', alignItems: 'center', padding: '4px 6px', border: '1px solid var(--color-border)', borderRadius: 4, background: 'transparent', cursor: 'pointer', color: 'var(--color-text-muted)' }}><LogOut size={12} /></button>
          </div>
        </header>

        {/* ─ Workflow Stepper (hidden on full-screen pages) ─ */}
        {!['graph', 'map', 'risk', 'ops', 'architecture', 'help', 'defects'].includes(activeView) && (
          <WorkflowStepper
            activeView={activeView}
            onNavigate={(view) => {
              const validViews: View[] = ['demand', 'results', 'map', 'graph', 'analysis', 'approve', 'defects', 'risk', 'ops', 'architecture', 'help']
              if (validViews.includes(view as View)) setActiveView(view as View)
            }}
            completedSteps={new Set([
              ...(demandUseForecast ? ['forecast'] : []),
              ...(hasRun ? ['optimize', 'analyze'] : []),
              ...(prsSubmitted ? ['execute'] : []),
            ])}
            loadingStep={forecastLoading ? 'forecast' : undefined}
          />
        )}

        {/* ─ Content + Agent ─ */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Page content */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>

            {activeView === 'demand' && (
              <div style={{ flex: 1, overflow: 'auto', padding: 24, background: 'var(--color-bg)' }}>
                <div style={{ maxWidth: 1000, margin: '0 auto' }}>
                  <DemandContext
                    quantity={500}
                    onOptimize={handleOptimize}
                    forecasts={demandForecasts}
                    setForecasts={setDemandForecasts}
                    useForecast={demandUseForecast}
                    setUseForecast={setDemandUseForecast}
                    confidenceLevel={demandConfidenceLevel}
                    setConfidenceLevel={setDemandConfidenceLevel}
                    externalLoading={forecastLoading}
                    setExternalLoading={setForecastLoading}
                  />
                </div>
              </div>
            )}

            {activeView === 'results' && (
              <div style={{ flex: 1, overflow: 'auto', padding: 24, background: 'var(--color-bg)' }}>
                <div style={{ maxWidth: 1100, margin: '0 auto' }}>
                  {/* Back link */}
                  <button onClick={() => setActiveView('demand')} style={{
                    display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0', border: 'none',
                    background: 'transparent', cursor: 'pointer', fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 16,
                  }}>← Back to Demand & Inventory</button>

                  {loading && (
                    <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      <div style={{ fontSize: 14 }}>Running optimization...</div>
                    </div>
                  )}

                  {!loading && paretoSolutions.length > 0 && (
                    <>
                      {/* KPI summary row */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
                        {[
                          { label: 'Solutions Found', value: String(paretoSolutions.length), sub: 'Pareto optimal' },
                          { label: 'Best Cost', value: `$${Math.round(Math.min(...paretoSolutions.map((s: any) => s.totalCost)) / 1000)}K`, sub: 'Cost-Optimized option' },
                          { label: 'Lowest Risk', value: `${Math.min(...paretoSolutions.map((s: any) => s.riskScore)).toFixed(1)}/10`, sub: 'Risk-Diversified option' },
                          { label: 'Computation', value: computationTimeMs ? `${computationTimeMs}ms` : '—', sub: backendStatus === 'connected' ? 'Live backend' : 'Fallback data' },
                        ].map(kpi => (
                          <div key={kpi.label} style={{ padding: '14px 16px', borderRadius: 'var(--radius-lg)', background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
                            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</div>
                            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginTop: 2 }}>{kpi.value}</div>
                            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>{kpi.sub}</div>
                          </div>
                        ))}
                      </div>

                      {/* Pareto chart */}
                      <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: 20, marginBottom: 20 }}>
                        <h3 style={{ fontSize: 15, margin: '0 0 12px', fontWeight: 600 }}>Pareto Frontier</h3>
                        <ParetoChart solutions={paretoSolutions} selectedSolution={selectedSolution} onSelectSolution={setSelectedSolution} />
                      </div>

                      {/* Solution cards grid */}
                      <SolutionCards solutions={paretoSolutions} selectedSolution={selectedSolution} onSelectSolution={setSelectedSolution} onViewAnalysis={() => setActiveView('analysis')} onApprovePRs={() => setShowPRConfirm(true)} />
                    </>
                  )}

                  {!loading && paretoSolutions.length === 0 && (
                    <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)', marginBottom: 6 }}>No results yet</div>
                      <div style={{ fontSize: 12 }}>Optimization is running or hasn't been triggered.</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeView === 'map' && (hasRun ? (
              <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
                <SupplierMap
                  selectedSolution={selectedSolution}
                  solutionSupplierIds={currentSolution ? [...new Set(currentSolution.allocations.map((a: any) => a.supplierId))] as string[] : []}
                  solutions={paretoSolutions.map((s: any) => ({ id: s.id, name: s.name }))}
                  onSelectSolution={setSelectedSolution}
                  onSupplierClick={setSelectedSupplier}
                  activeSupplier={selectedSupplier}
                  onRiskOptimize={(msg) => {
                    setAgentOpen(true)
                    setActivityMessages(prev => [...prev, {
                      role: 'system' as const,
                      content: '⚡ Risk analysis triggered from Supplier Map',
                      timestamp: new Date(),
                    }])
                    setPendingAgentMessage(msg)
                  }}
                  onNavigate={(view) => {
                    const validViews: View[] = ['demand', 'results', 'map', 'graph', 'analysis', 'approve', 'defects', 'risk', 'ops', 'architecture', 'help']
                    if (validViews.includes(view as View)) setActiveView(view as View)
                  }}
                  onRefetchOptimization={(excludedSuppliers) => refetch(forecastMaterials || undefined, excludedSuppliers)}
                />
                {selectedSupplier && (
                  <div style={{
                    position: 'absolute', top: 0, right: 0, width: 340, height: '100%',
                    background: 'var(--color-surface)', borderLeft: '1px solid var(--color-border)',
                    boxShadow: '-4px 0 20px rgba(0,0,0,0.08)', overflow: 'auto', zIndex: 1001,
                  }}>
                    {renderSupplierPanel()}
                  </div>
                )}
              </div>
            ) : noResultsNudge('Supplier Risk Map'))}

            {activeView === 'graph' && <GraphAnalysis />}
            {activeView === 'analysis' && (hasRun ? renderAnalysisView() : noResultsNudge('Analysis'))}
            {activeView === 'approve' && (hasRun ? <div style={{ flex: 1, overflow: 'auto', padding: 24, background: 'var(--color-bg)' }}><PurchaseRequisitionPreview solution={currentSolution || null} onAllSubmitted={() => setPrsSubmitted(true)} /></div> : noResultsNudge('Purchase Requisitions'))}
            {activeView === 'defects' && <DefectTracker />}
            {activeView === 'risk' && <RiskSimulation />}
            {activeView === 'ops' && renderOpsView()}
            {activeView === 'architecture' && <ArchitecturePage />}
            {activeView === 'help' && <HelpGuide />}
          </div>

          {/* ═══ FLOATING AGENT PANEL ═══ */}
          {agentOpen && renderAgentPanel()}
        </div>
      </div>

      {/* ═══ CONFIRM MODAL ═══ */}
      {showPRConfirm && currentSolution && (
        <ConfirmModal
          title="Create Purchase Requisitions"
          message={`Create ${new Set(currentSolution.allocations.map((a: any) => a.supplierId)).size} requisitions (${currentSolution.allocations.length} line items) for the ${currentSolution.name} strategy ($${Math.round(currentSolution.totalCost / 1000)}K total)?\n\nThese will be routed through your approval workflow.`}
          confirmLabel="Create PRs"
          cancelLabel="Cancel"
          onConfirm={() => { setShowPRConfirm(false); setActiveView('approve') }}
          onCancel={() => setShowPRConfirm(false)}
        />
      )}
    </div>
  )

  /* ──────── Supplier panel (map view right side) ──────── */
  function renderSupplierPanel() {
    const sup = selectedSupplier ? liveSuppliers.find(s => s.supplier_id === selectedSupplier) : null
    const supPerf = selectedSupplier ? livePerformance.filter(p => p.supplier_id === selectedSupplier).sort((a, b) => b.measurement_period.localeCompare(a.measurement_period)) : []
    const latestPerf = supPerf[0]
    const solutionSupIds = currentSolution ? new Set(currentSolution.allocations.map((a: any) => a.supplierId)) : new Set<string>()

    if (!sup) return (
      <div style={{ padding: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--color-text)' }}>Suppliers {currentSolution ? `(${currentSolution.name})` : ''}</div>
        <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 12 }}>{solutionSupIds.size > 0 ? `${solutionSupIds.size} in solution` : 'Select a supplier'}</div>
        {liveSuppliers.sort((a, b) => (solutionSupIds.has(b.supplier_id) ? 1 : 0) - (solutionSupIds.has(a.supplier_id) ? 1 : 0)).map(s => {
          const inSol = solutionSupIds.has(s.supplier_id)
          return (
            <button key={s.supplier_id} onClick={() => setSelectedSupplier(s.supplier_id)} style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '8px 10px', marginBottom: 3,
              borderRadius: 'var(--radius-md)', cursor: 'pointer', textAlign: 'left',
              border: inSol ? '1px solid var(--color-primary)' : '1px solid var(--color-border-light)',
              background: inSol ? 'var(--color-primary-light)' : 'var(--color-surface)',
              opacity: solutionSupIds.size > 0 && !inSol ? 0.5 : 1,
            }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0, background: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 14 }}>{s.name.charAt(0)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</div>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{s.location}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                <div style={{ padding: '1px 6px', borderRadius: 8, fontSize: 10, fontWeight: 600, background: s.geopolitical_risk_score < 2.5 ? 'var(--color-success-light)' : s.geopolitical_risk_score < 3.5 ? 'var(--color-warning-light)' : 'var(--color-danger-light)', color: s.geopolitical_risk_score < 2.5 ? 'var(--color-success)' : s.geopolitical_risk_score < 3.5 ? 'var(--color-warning)' : 'var(--color-danger)' }}>Risk {s.geopolitical_risk_score.toFixed(1)}</div>
                {inSol && <div style={{ fontSize: 10, color: 'var(--color-primary)', fontWeight: 600 }}>In Solution</div>}
              </div>
            </button>
          )
        })}
      </div>
    )

    return (
      <div style={{ padding: 20 }}>
        <button onClick={() => setSelectedSupplier(null)} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', cursor: 'pointer', fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 16 }}>← All Suppliers</button>
        <div style={{ padding: 16, borderRadius: 'var(--radius-lg)', marginBottom: 16, background: 'var(--color-nav-bg)', color: '#fff' }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{sup.name}</div>
          <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>{sup.location} | {sup.supplier_id}</div>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 13 }}>
            {[{ l: 'Rating', v: `${sup.rating}/5` }, { l: 'Risk', v: `${sup.geopolitical_risk_score}/10` }, { l: 'Stability', v: `${sup.financial_stability_score}/10` }, { l: 'Lead Time', v: `${sup.lead_time_days}d` }].map(m => (
              <div key={m.l}><div style={{ opacity: 0.7, fontSize: 11 }}>{m.l}</div><div style={{ fontWeight: 700 }}>{m.v}</div></div>
            ))}
          </div>
        </div>
        {latestPerf && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Latest Performance</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { label: 'On-Time Delivery', value: `${latestPerf.on_time_delivery_rate.toFixed(1)}%`, good: latestPerf.on_time_delivery_rate > 95 },
                { label: 'Quality Score', value: `${latestPerf.quality_score.toFixed(1)}/10`, good: latestPerf.quality_score > 8 },
                { label: 'Defect Rate', value: `${latestPerf.defect_rate.toFixed(2)}%`, good: latestPerf.defect_rate < 1.5 },
                { label: 'Response Time', value: `${latestPerf.response_time_hours}h`, good: latestPerf.response_time_hours < 24 },
              ].map(m => (
                <div key={m.label} style={{ padding: 12, borderRadius: 8, background: 'var(--color-bg)', borderLeft: `3px solid ${m.good ? 'var(--color-success)' : 'var(--color-warning)'}` }}>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{m.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text)' }}>{m.value}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {supPerf.length > 1 && (
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>History ({supPerf.length} periods)</h4>
            <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 0.8fr 0.8fr 0.8fr', padding: '8px 12px', background: 'var(--color-bg)', fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)' }}><div>Period</div><div>OTD</div><div>Quality</div><div>Defects</div></div>
              {supPerf.slice(0, 5).map(p => (
                <div key={p.performance_id} style={{ display: 'grid', gridTemplateColumns: '1fr 0.8fr 0.8fr 0.8fr', padding: '8px 12px', fontSize: 12, borderTop: '1px solid var(--color-border-light)' }}>
                  <div>{p.measurement_period}</div><div>{p.on_time_delivery_rate.toFixed(1)}%</div><div>{p.quality_score.toFixed(1)}</div><div>{p.defect_rate.toFixed(2)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {currentSolution && (() => {
          const allocs = currentSolution.allocations.filter((a: any) => a.supplierId === sup.supplier_id)
          return (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>In {currentSolution.name} Solution?</h4>
              {allocs.length === 0
                ? <div style={{ padding: 12, borderRadius: 8, background: 'var(--color-warning-light)', fontSize: 13, color: 'var(--color-warning)' }}>Not selected in current solution</div>
                : allocs.map((a: any, i: number) => (
                  <div key={i} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--color-success-light)', marginBottom: 4, fontSize: 13 }}>
                    <div style={{ fontWeight: 600, color: 'var(--color-success)' }}>{a.materialName}</div>
                    <div style={{ color: '#15803d' }}>{a.quantity} units @ ${a.unitPrice.toFixed(2)} = ${a.totalCost.toLocaleString()}</div>
                  </div>
                ))
              }
            </div>
          )
        })()}
      </div>
    )
  }

  /* ──────── Analysis view ──────── */
  function renderAnalysisView() {
    return (
      <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ marginBottom: 12 }}>
          <button onClick={() => setActiveView('results')} style={{
            background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer',
            fontSize: 13, fontWeight: 500, padding: 0, display: 'flex', alignItems: 'center', gap: 4,
          }}>
            ← Back to Results
          </button>
        </div>
        {/* Solution selector + strategy summary bar */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          {paretoSolutions.map((s: any) => (
            <button key={s.id} onClick={() => { setSelectedSolution(s.id); setStrategyExpanded(false) }} style={{
              padding: '6px 14px', borderRadius: 16, fontSize: 13, cursor: 'pointer',
              border: s.id === selectedSolution ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
              background: s.id === selectedSolution ? 'var(--color-primary-light)' : 'var(--color-surface)',
              color: s.id === selectedSolution ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              fontWeight: s.id === selectedSolution ? 600 : 400,
            }}>{s.name} - ${Math.round(s.totalCost / 1000)}K | Risk {s.riskScore.toFixed(1)}</button>
          ))}
        </div>

        {/* Compact strategy KPI bar */}
        {currentSolution && (() => {
          const [expanded, setExpanded] = [strategyExpanded, setStrategyExpanded]
          return (
            <div style={{ marginBottom: 16, borderRadius: 8, background: 'var(--color-nav-bg)', color: '#fff', overflow: 'hidden' }}>
              <div style={{ display: 'flex', gap: 12, padding: '10px 16px', alignItems: 'center', cursor: 'pointer', flexWrap: 'wrap' }} onClick={() => setExpanded(!expanded)}>
                <div style={{ fontSize: 16, fontWeight: 700, marginRight: 4 }}>{currentSolution.name}</div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  {[
                    { l: 'Cost', v: `$${Math.round(currentSolution.totalCost / 1000)}K` },
                    { l: 'Risk', v: `${currentSolution.riskScore.toFixed(1)}/10` },
                    { l: 'Quality', v: `${currentSolution.qualityScore.toFixed(1)}/10` },
                    { l: 'Lead', v: `${currentSolution.maxLeadTimeDays}d` },
                    { l: 'Suppliers', v: `${new Set(currentSolution.allocations.map((a: any) => a.supplierId)).size}` },
                  ].map(k => (
                    <div key={k.l} style={{ display: 'flex', gap: 4, alignItems: 'baseline', fontSize: 13 }}>
                      <span style={{ opacity: 0.6, fontSize: 10 }}>{k.l}</span>
                      <span style={{ fontWeight: 700 }}>{k.v}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button onClick={(e) => {
                    e.stopPropagation()
                    setShowPRConfirm(true)
                  }} style={{
                    padding: '6px 16px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.3)',
                    background: 'rgba(255,255,255,0.15)', color: '#fff', fontWeight: 600,
                    fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    whiteSpace: 'nowrap',
                  }}>
                    📋 Approve & Create PRs
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); requestAgentAnalysis(currentSolution) }} style={{
                    padding: '6px 16px', borderRadius: 6, border: '2px solid rgba(255,255,255,0.5)',
                    background: 'rgba(59,130,246,0.8)', color: '#fff', fontWeight: 700,
                    fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    whiteSpace: 'nowrap', letterSpacing: '0.02em',
                    boxShadow: '0 0 8px rgba(59,130,246,0.4)',
                  }}>
                    🤖 Analyze with AI
                  </button>
                  <span style={{ fontSize: 11, opacity: 0.6, cursor: 'pointer' }}>
                    {expanded ? '▲' : '▼'}
                  </span>
                </div>
              </div>
              {expanded && (
                <div style={{ padding: '0 16px 14px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  {/* Expanded KPI grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, padding: '12px 0' }}>
                    {[
                      { l: 'Total Cost', v: `$${currentSolution.totalCost.toLocaleString()}` },
                      { l: 'Risk Score', v: `${currentSolution.riskScore.toFixed(1)} / 10` },
                      { l: 'Quality Score', v: `${currentSolution.qualityScore.toFixed(1)} / 10` },
                      { l: 'Max Lead Time', v: `${currentSolution.maxLeadTimeDays} days` },
                      { l: 'Materials', v: `${new Set(currentSolution.allocations.map((a: any) => a.materialId)).size}` },
                    ].map(k => (
                      <div key={k.l} style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 10, opacity: 0.5, marginBottom: 2 }}>{k.l}</div>
                        <div style={{ fontSize: 18, fontWeight: 700 }}>{k.v}</div>
                      </div>
                    ))}
                  </div>
                  {/* Full supplier concentration */}
                  {currentSolution.supplierConcentration?.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 11, opacity: 0.5, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Supplier Concentration</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '6px 16px' }}>
                        {currentSolution.supplierConcentration.map((sc: any) => (
                          <div key={sc.supplierId} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                            <div style={{ width: 40, textAlign: 'right', fontWeight: 600 }}>{sc.percentage}%</div>
                            <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.15)' }}>
                              <div style={{ height: '100%', borderRadius: 2, width: `${sc.percentage}%`, background: sc.percentage > 50 ? '#ef4444' : sc.percentage > 30 ? '#f59e0b' : '#22c55e' }} />
                            </div>
                            <div style={{ opacity: 0.8, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sc.supplierName}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Explanation if available */}
                  {currentSolution.explanation && (
                    <div style={{ marginTop: 12, fontSize: 12, opacity: 0.7, lineHeight: 1.5 }}>
                      {currentSolution.explanation}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })()}

        {/* Custom weights */}
        <div style={{ marginBottom: 16 }}>
          <WeightSliders materials={forecastMaterials} onCustomSolution={(sol: SupplierMix) => {
            const allocs = sol.allocations.map((a: any) => ({ supplierId: a.supplier_id, supplierName: a.supplier_name, materialId: a.material_id, materialName: a.material_name, quantity: a.quantity, unitPrice: a.unit_price, totalCost: a.total_cost, leadTimeDays: a.lead_time_days }))
            const supplierNames: string[] = [...new Set(allocs.map((a: any) => a.supplierName))]
            const totalCost = sol.total_cost
            setCustomSolution({
              id: 'SOL-CUSTOM', name: 'Custom', totalCost, riskScore: sol.risk_score, qualityScore: sol.quality_score, maxLeadTimeDays: sol.lead_time_days,
              explanation: `Custom-weighted solution with ${supplierNames.length} suppliers.`,
              supplierConcentration: Object.entries(allocs.reduce((acc: Record<string, { name: string; cost: number }>, a: any) => { if (!acc[a.supplierId]) acc[a.supplierId] = { name: a.supplierName, cost: 0 }; acc[a.supplierId].cost += a.totalCost; return acc }, {})).map(([id, info]: any) => ({ supplierId: id, supplierName: info.name, percentage: Math.round((info.cost / totalCost) * 100) })).sort((a: any, b: any) => b.percentage - a.percentage),
              allocations: allocs,
              reasoning: { summary: `Custom: ${supplierNames.length} suppliers, ${Math.round(totalCost / 1000)}K.`, keyFactors: [`TCO: ${Math.round(totalCost).toLocaleString()}`], tradeOffs: ['User-defined weights'], risks: sol.risk_score > 2 ? ['Elevated risk'] : ['Low risk'] },
            })
            setSelectedSolution('SOL-CUSTOM')
          }} />
        </div>

        {/* Executive dashboard */}
        <ExecutiveDashboard solutions={paretoSolutions} selectedSolution={selectedSolution} />

        {/* Pareto Frontier */}
        <div style={{ marginTop: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Pareto Frontier</h3>
          <ParetoChart solutions={paretoSolutions} selectedSolution={selectedSolution} onSelectSolution={setSelectedSolution} />
        </div>

        {/* BOM table */}
        {currentSolution && (
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>BOM: {currentSolution.name} ({new Set(currentSolution.allocations.map((a: any) => a.materialId)).size} materials, {currentSolution.allocations.length} orders)</h3>
            <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 0.7fr 1fr 1fr', padding: '8px 12px', background: 'var(--color-bg)', fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)' }}><div>Material</div><div>Supplier</div><div>Qty</div><div>Unit</div><div style={{ textAlign: 'right' }}>Total</div></div>
              {currentSolution.allocations.map((a: any, i: number) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 0.7fr 1fr 1fr', padding: '7px 12px', fontSize: 12, borderTop: '1px solid var(--color-border-light)' }}>
                  <div style={{ fontWeight: 500 }}>{a.materialName}</div><div style={{ color: 'var(--color-text-secondary)' }}>{a.supplierName}</div><div>{a.quantity}</div><div>${a.unitPrice.toFixed(0)}</div><div style={{ textAlign: 'right', fontWeight: 500 }}>${Math.round(a.totalCost / 1000)}K</div>
                </div>
              ))}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 0.7fr 1fr 1fr', padding: '10px 12px', background: 'var(--color-bg)', fontWeight: 700, fontSize: 13, borderTop: '1px solid var(--color-border)' }}><div>Total TCO</div><div /><div /><div /><div style={{ textAlign: 'right' }}>${Math.round(currentSolution.totalCost / 1000)}K</div></div>
            </div>
          </div>
        )}
        </div>
      </div>
    )
  }

  /* ──────── Operations view ──────── */
  function renderOpsView() {
    return (
      <div style={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>
        <div style={{ width: 200, flexShrink: 0, background: 'var(--color-surface)', borderRight: '1px solid var(--color-border)', padding: '16px 0' }}>
          <div style={{ padding: '0 16px 12px', fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>AgentCore</div>
          {([{ key: 'gateway' as OpsTab, label: 'MCP Gateway' }, { key: 'evaluations' as OpsTab, label: 'Evaluations' }, { key: 'policies' as OpsTab, label: 'Cedar Policies' }, { key: 'memory' as OpsTab, label: 'Agent Memory' }]).map(item => (
            <button key={item.key} onClick={() => setOpsTab(item.key)} style={{
              display: 'block', width: '100%', padding: '8px 16px', border: 'none', textAlign: 'left', cursor: 'pointer', fontSize: 13, fontWeight: 500,
              background: opsTab === item.key ? 'var(--color-primary-light)' : 'transparent',
              color: opsTab === item.key ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              borderLeft: opsTab === item.key ? '3px solid var(--color-primary)' : '3px solid transparent', borderRadius: 0,
            }}>{item.label}</button>
          ))}
        </div>
        <div style={{ flex: 1, overflow: 'auto', background: 'var(--color-bg)' }}>
          {opsTab === 'gateway' && <GatewayPanel />}
          {opsTab === 'evaluations' && <EvaluationsPanel />}
          {opsTab === 'policies' && <PolicyViewer />}
          {opsTab === 'memory' && <MemoryExplorer />}
        </div>
      </div>
    )
  }

  /* ──────── Floating agent panel (chat only) ──────── */
  function renderAgentPanel() {
    return (
      <>
        {/* Drag handle for resizing */}
        <div
          style={{
            width: 4, cursor: 'col-resize', background: 'transparent',
            flexShrink: 0, position: 'relative', zIndex: 10,
          }}
          onMouseDown={(e) => {
            e.preventDefault()
            const startX = e.clientX
            const startWidth = agentPanelWidth
            const onMove = (ev: MouseEvent) => {
              const delta = startX - ev.clientX
              setAgentPanelWidth(Math.max(320, Math.min(800, startWidth + delta)))
            }
            const onUp = () => {
              document.removeEventListener('mousemove', onMove)
              document.removeEventListener('mouseup', onUp)
            }
            document.addEventListener('mousemove', onMove)
            document.addEventListener('mouseup', onUp)
          }}
          onMouseEnter={(e) => { (e.target as HTMLElement).style.background = 'var(--color-primary)' }}
          onMouseLeave={(e) => { (e.target as HTMLElement).style.background = 'transparent' }}
        />
        <div style={{ width: agentPanelWidth, flexShrink: 0, display: 'flex', flexDirection: 'column', borderLeft: '1px solid var(--color-border)', background: 'var(--color-surface)', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)' }}>Procurement Agent</div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Powered by Claude on Bedrock</div>
            </div>
            <button onClick={() => setAgentOpen(false)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, borderRadius: 6, border: '1px solid var(--color-border)', background: 'var(--color-surface)', cursor: 'pointer', color: 'var(--color-text-muted)', padding: 0 }}><X size={14} /></button>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <ChatInterface messages={messages} activityMessages={activityMessages} onOptimizationTriggered={() => refetch(forecastMaterials)} pendingMessage={pendingAgentMessage} onPendingMessageConsumed={() => setPendingAgentMessage(null)} />
          </div>
        </div>
      </>
    )
  }
}

export default App
