/**
 * Defect Tracking dashboard component.
 *
 * Displays defect records, summary stats, recall management,
 * and defect reports with filtering and drill-down.
 * Uses the project design tokens from index.css.
 */

import { useState, useEffect } from 'react'
import { AlertTriangle, Shield, RotateCcw, FileText, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import {
  fetchDefects, fetchDefectSummary, fetchDefectReport, initiateRecall,
  type DefectRecord, type DefectSummary, type DefectReport,
} from '../services/api'
import './DefectTracker.css'

type Tab = 'overview' | 'defects' | 'report'

export default function DefectTracker() {
  const [tab, setTab] = useState<Tab>('overview')
  const [defects, setDefects] = useState<DefectRecord[]>([])
  const [summary, setSummary] = useState<DefectSummary | null>(null)
  const [report, setReport] = useState<DefectReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterSeverity, setFilterSeverity] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterSupplier, setFilterSupplier] = useState<string>('')
  const [expandedDefect, setExpandedDefect] = useState<string | null>(null)
  const [recallStatus, setRecallStatus] = useState<Record<string, string>>({})

  useEffect(() => {
    loadData()
  }, [filterSeverity, filterStatus, filterSupplier])

  async function loadData() {
    setLoading(true)
    const filters: Record<string, string> = {}
    if (filterSeverity) filters.severity = filterSeverity
    if (filterStatus) filters.status = filterStatus
    if (filterSupplier) filters.supplier_id = filterSupplier

    const [defData, sumData, repData] = await Promise.all([
      fetchDefects(filters),
      fetchDefectSummary(),
      fetchDefectReport(filterSupplier || undefined),
    ])
    setDefects(defData.defects)
    setSummary(sumData)
    setReport(repData)
    setLoading(false)
  }

  async function handleRecall(defectId: string) {
    try {
      setRecallStatus(prev => ({ ...prev, [defectId]: 'initiating...' }))
      const result = await initiateRecall(defectId)
      setRecallStatus(prev => ({ ...prev, [defectId]: `✓ ${result.recall_id}` }))
    } catch {
      setRecallStatus(prev => ({ ...prev, [defectId]: 'Failed' }))
    }
  }

  const severityClass = (s: string) =>
    s === 'CRITICAL' ? 'critical' : s === 'MAJOR' ? 'major' : 'minor'
  const severityColor = (s: string) =>
    s === 'CRITICAL' ? 'var(--color-danger)' : s === 'MAJOR' ? 'var(--color-warning)' : 'var(--color-text-secondary)'

  const tabs: { key: Tab; label: string; icon: typeof AlertTriangle }[] = [
    { key: 'overview', label: 'Dashboard', icon: Shield },
    { key: 'defects', label: 'Defect Log', icon: AlertTriangle },
    { key: 'report', label: 'Reports', icon: FileText },
  ]

  return (
    <div className="defect-tracker">
      {/* Left sidebar */}
      <div className="defect-sidebar">
        <div className="defect-sidebar-title">Defect Tracking</div>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`defect-tab-btn ${tab === t.key ? 'active' : ''}`}>
            <t.icon size={14} />
            {t.label}
          </button>
        ))}

        {/* Filters */}
        <div className="defect-filters">
          <div className="defect-filters-label">
            <Filter size={11} /> FILTERS
          </div>
          <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
            className="defect-filter-select" aria-label="Filter by severity">
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="MAJOR">Major</option>
            <option value="MINOR">Minor</option>
          </select>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            className="defect-filter-select" aria-label="Filter by status">
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          {summary && (
            <select value={filterSupplier} onChange={e => setFilterSupplier(e.target.value)}
              className="defect-filter-select" aria-label="Filter by supplier">
              <option value="">All Suppliers</option>
              {Object.entries(summary.by_supplier).map(([id, s]) => (
                <option key={id} value={id}>{s.supplier_name}</option>
              ))}
            </select>
          )}
          {(filterSeverity || filterStatus || filterSupplier) && (
            <button onClick={() => { setFilterSeverity(''); setFilterStatus(''); setFilterSupplier(''); }}
              className="defect-clear-btn">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="defect-main">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--color-text-muted)' }}>Loading defect data...</div>
        ) : (
          <>
            {/* ─── DASHBOARD TAB ─── */}
            {tab === 'overview' && summary && (
              <div>
                {/* KPI cards */}
                <div className="defect-kpi-grid">
                  {[
                    { label: 'Total Defects', value: summary.overview.total_defects, color: 'var(--color-primary)' },
                    { label: 'Open', value: summary.overview.open_defects, color: 'var(--color-danger)' },
                    { label: 'Resolved', value: summary.overview.resolved_defects, color: 'var(--color-success)' },
                    { label: 'Critical', value: summary.overview.critical_defects, color: 'var(--color-warning)' },
                    { label: 'Recalls', value: summary.overview.recalls_initiated, color: '#8b5cf6' },
                    { label: 'Units Affected', value: summary.overview.total_units_affected, color: '#06b6d4' },
                  ].map(kpi => (
                    <div key={kpi.label} className="defect-kpi-card" style={{ borderLeft: `4px solid ${kpi.color}` }}>
                      <div className="defect-kpi-label">{kpi.label}</div>
                      <div className="defect-kpi-value">{kpi.value}</div>
                    </div>
                  ))}
                </div>

                {/* Severity + Category breakdown */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
                  <div className="defect-panel">
                    <h3>By Severity</h3>
                    {Object.entries(summary.by_severity).map(([sev, data]) => (
                      <div key={sev} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                        <span className={`severity-badge ${severityClass(sev)}`}>{sev}</span>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontWeight: 600, fontSize: 'var(--text-base)' }}>{data.count}</span>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginLeft: '8px' }}>{data.quantity_affected} units</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="defect-panel">
                    <h3>By Category</h3>
                    {Object.entries(summary.by_category).sort((a, b) => b[1] - a[1]).map(([cat, count]) => {
                      const maxCount = Math.max(...Object.values(summary.by_category))
                      return (
                        <div key={cat} style={{ marginBottom: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '3px' }}>
                            <span style={{ color: 'var(--color-text)' }}>{cat}</span>
                            <span style={{ fontWeight: 600 }}>{count}</span>
                          </div>
                          <div className="score-bar-track">
                            <div className="score-bar-fill" style={{ width: `${(count / maxCount) * 100}%`, background: 'var(--color-primary)' }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Supplier defect scores */}
                <div className="defect-panel">
                  <h3>Supplier Defect Risk Scores</h3>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '0 0 12px' }}>
                    These scores feed into the optimization engine's risk calculation — suppliers with higher defect scores are penalized during forecasting.
                  </p>
                  <div className="defect-table">
                    <div className="defect-table-header" style={{ gridTemplateColumns: '2fr 0.8fr 0.8fr 0.8fr 0.8fr 1.2fr' }}>
                      <div>Supplier</div><div>Defects</div><div>Open</div><div>Critical</div><div>Recalls</div><div>Risk Score</div>
                    </div>
                    {Object.entries(summary.by_supplier)
                      .sort((a, b) => b[1].defect_score - a[1].defect_score)
                      .map(([id, s]) => (
                        <div key={id} className="defect-table-row"
                          style={{
                            gridTemplateColumns: '2fr 0.8fr 0.8fr 0.8fr 0.8fr 1.2fr',
                            background: filterSupplier === id ? 'var(--color-primary-light)' : undefined,
                          }}
                          onClick={() => { setFilterSupplier(id); setTab('defects'); }}>
                          <div>
                            <div style={{ fontWeight: 500 }}>{s.supplier_name}</div>
                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>{id}</div>
                          </div>
                          <div>{s.total_defects}</div>
                          <div style={{ color: s.open_defects > 0 ? 'var(--color-danger)' : 'var(--color-success)', fontWeight: 600 }}>{s.open_defects}</div>
                          <div style={{ color: s.critical_defects > 0 ? 'var(--color-danger)' : 'var(--color-text-secondary)' }}>{s.critical_defects}</div>
                          <div>{s.recalls}</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div className="score-bar-track">
                              <div className="score-bar-fill" style={{
                                width: `${Math.min(100, s.defect_score * 10)}%`,
                                background: s.defect_score > 6 ? 'var(--color-danger)' : s.defect_score > 3 ? 'var(--color-warning)' : 'var(--color-success)',
                              }} />
                            </div>
                            <span style={{ fontWeight: 600, fontSize: 'var(--text-xs)', minWidth: '28px' }}>{s.defect_score}</span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            )}

            {/* ─── DEFECT LOG TAB ─── */}
            {tab === 'defects' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                  <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: 0, color: 'var(--color-text)' }}>
                    Defect Log ({defects.length} records)
                  </h2>
                  <button onClick={loadData} style={{
                    display: 'flex', alignItems: 'center', gap: '4px', padding: '6px 12px',
                    borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)',
                    background: 'var(--color-surface)', cursor: 'pointer', fontSize: '12px',
                    color: 'var(--color-text-secondary)',
                  }}>
                    <RotateCcw size={12} /> Refresh
                  </button>
                </div>

                {defects.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-muted)' }}>
                    No defects match the current filters.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {defects.map(d => {
                      const isExpanded = expandedDefect === d.defect_id
                      return (
                        <div key={d.defect_id} className="defect-card"
                          style={{ borderLeft: `4px solid ${severityColor(d.severity)}` }}>
                          {/* Header row */}
                          <div className="defect-card-header"
                            onClick={() => setExpandedDefect(isExpanded ? null : d.defect_id)}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                              <span className={`severity-badge ${severityClass(d.severity)}`}>{d.severity}</span>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--color-text)' }}>
                                  {d.defect_id}: {d.description.slice(0, 60)}{d.description.length > 60 ? '...' : ''}
                                </div>
                                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                                  {d.supplier_name} → {d.material_name} | {d.defect_date} | Batch {d.batch_id}
                                </div>
                              </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span className={`status-badge-defect ${d.status === 'OPEN' ? 'open' : 'resolved'}`}>{d.status}</span>
                              {d.recall_initiated && <span className="recall-badge">RECALL</span>}
                              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>{d.quantity_affected} units</span>
                              {isExpanded ? <ChevronUp size={14} color="var(--color-text-muted)" /> : <ChevronDown size={14} color="var(--color-text-muted)" />}
                            </div>
                          </div>

                          {/* Expanded detail */}
                          {isExpanded && (
                            <div className="defect-card-detail">
                              <div className="defect-detail-grid">
                                <div>
                                  <div className="defect-detail-label">Category</div>
                                  <div className="defect-detail-value">{d.category}</div>
                                </div>
                                <div>
                                  <div className="defect-detail-label">Resolution Date</div>
                                  <div className="defect-detail-value">{d.resolution_date || 'Pending'}</div>
                                </div>
                                <div style={{ gridColumn: '1 / -1' }}>
                                  <div className="defect-detail-label">Root Cause</div>
                                  <div className="defect-root-cause">{d.root_cause}</div>
                                </div>
                                {d.corrective_action && (
                                  <div style={{ gridColumn: '1 / -1' }}>
                                    <div className="defect-detail-label">Corrective Action</div>
                                    <div className="defect-corrective-action">{d.corrective_action}</div>
                                  </div>
                                )}
                              </div>

                              {/* Recall button */}
                              {d.status === 'OPEN' && !d.recall_initiated && (
                                <div style={{ marginTop: 'var(--space-3)' }}>
                                  {recallStatus[d.defect_id] ? (
                                    <span style={{
                                      fontSize: '12px', fontWeight: 600,
                                      color: recallStatus[d.defect_id].startsWith('✓') ? 'var(--color-success)' : 'var(--color-danger)',
                                    }}>
                                      {recallStatus[d.defect_id]}
                                    </span>
                                  ) : (
                                    <button onClick={() => handleRecall(d.defect_id)} className="recall-button">
                                      <AlertTriangle size={13} /> Initiate Recall
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ─── REPORT TAB ─── */}
            {tab === 'report' && report && report.report && (
              <div>
                <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: '0 0 var(--space-4)', color: 'var(--color-text)' }}>
                  Defect Analysis Report {filterSupplier ? `— ${summary?.by_supplier[filterSupplier]?.supplier_name || filterSupplier}` : '— All Suppliers'}
                </h2>

                {/* Report KPIs */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-6)' }}>
                  {[
                    { label: 'Total Defects', value: report.report.total_defects },
                    { label: 'Avg Resolution', value: report.report.avg_resolution_days ? `${report.report.avg_resolution_days}d` : 'N/A' },
                    { label: 'Recall Rate', value: `${report.report.recall_rate}%` },
                    { label: 'Open Rate', value: `${report.report.open_rate}%` },
                  ].map(kpi => (
                    <div key={kpi.label} className="defect-kpi-card" style={{ textAlign: 'center' }}>
                      <div className="defect-kpi-label">{kpi.label}</div>
                      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text)' }}>{kpi.value}</div>
                    </div>
                  ))}
                </div>

                {/* Monthly trend */}
                <div className="defect-panel" style={{ marginBottom: 'var(--space-4)' }}>
                  <h3>Monthly Trend</h3>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', height: '120px' }}>
                    {Object.entries(report.report.monthly_trend).map(([month, data]) => {
                      const maxTotal = Math.max(...Object.values(report.report.monthly_trend).map(d => d.total))
                      const height = maxTotal > 0 ? (data.total / maxTotal) * 100 : 0
                      return (
                        <div key={month} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)' }}>{data.total}</div>
                          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1px' }}>
                            {data.critical > 0 && (
                              <div style={{
                                height: `${(data.critical / data.total) * height}px`,
                                background: 'var(--color-danger)', borderRadius: '3px 3px 0 0', minHeight: '4px',
                              }} />
                            )}
                            <div style={{
                              height: `${height - (data.critical > 0 ? (data.critical / data.total) * height : 0)}px`,
                              background: 'var(--color-primary)', borderRadius: data.critical > 0 ? '0 0 3px 3px' : '3px',
                              minHeight: '4px',
                            }} />
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>{month}</div>
                        </div>
                      )
                    })}
                  </div>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px', justifyContent: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--color-text-secondary)' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--color-danger)' }} /> Critical
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--color-text-secondary)' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--color-primary)' }} /> Other
                    </div>
                  </div>
                </div>

                {/* Top root causes */}
                <div className="defect-panel" style={{ marginBottom: 'var(--space-4)' }}>
                  <h3>Top Root Causes</h3>
                  {report.report.top_root_causes.map((rc, i) => (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '8px 0', borderBottom: '1px solid var(--color-border-light)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          width: '20px', height: '20px', borderRadius: '50%', display: 'flex',
                          alignItems: 'center', justifyContent: 'center', fontSize: '10px',
                          fontWeight: 700, background: 'var(--color-border-light)', color: 'var(--color-text-secondary)',
                        }}>{i + 1}</span>
                        <span style={{ fontSize: '12px', color: 'var(--color-text)' }}>{rc.cause}</span>
                      </div>
                      <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{rc.count}</span>
                    </div>
                  ))}
                </div>

                {/* Impact on optimization note */}
                <div className="defect-info-banner">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <Shield size={14} color="#2563eb" />
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: '#1e40af' }}>Impact on Supplier Selection</span>
                  </div>
                  <p>
                    Defect history is factored into the optimization engine's risk scoring. Suppliers with higher defect scores
                    (especially open critical defects and recalls) receive a higher risk penalty, making the system prefer
                    suppliers with cleaner defect records during procurement optimization.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
