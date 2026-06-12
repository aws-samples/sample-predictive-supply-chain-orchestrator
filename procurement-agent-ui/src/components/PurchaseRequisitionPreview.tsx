import { useState } from 'react'
import type { OptimizationSolution } from '../data/realData'
import { downloadSinglePR, downloadAllPRs } from '../utils/prPdfExport'
import { generateODataDocuments, type SAPODataDocument } from '../utils/sapODataExport'
import { exportSAPOData } from '../services/api'

interface PurchaseRequisitionPreviewProps {
  solution: OptimizationSolution | null
  onAllSubmitted?: () => void
}

const STATUS_STEPS = ['Draft', 'Submitted', 'Approved', 'PO Created'] as const

const headerCellStyle: React.CSSProperties = {
  padding: '6px 8px',
  fontSize: '11px',
  fontWeight: 600,
  color: '#354a5f',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.03em',
  borderBottom: '2px solid #354a5f',
  whiteSpace: 'nowrap',
}

const cellStyle: React.CSSProperties = {
  padding: '7px 8px',
  fontSize: '12px',
  color: '#32363a',
  borderBottom: '1px solid #e5e5e5',
}

const labelStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#6a6d70',
  marginBottom: '2px',
  fontWeight: 500,
}

const valueStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#32363a',
  fontWeight: 600,
}

function formatCurrency(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
}

function generateMaterialNumber(materialId: string, idx: number): string {
  const num = parseInt(materialId.replace(/\D/g, ''), 10) || (idx + 1)
  return `3000${String(num).padStart(4, '0')}`
}

function getUoM(materialName: string): string {
  const lower = materialName.toLowerCase()
  if (lower.includes('cell') || lower.includes('module') || lower.includes('pack') || lower.includes('bms') || lower.includes('connector') || lower.includes('sensor')) return 'EA'
  if (lower.includes('electrolyte') || lower.includes('slurry') || lower.includes('solvent')) return 'L'
  if (lower.includes('foil') || lower.includes('sheet') || lower.includes('film')) return 'M2'
  if (lower.includes('powder') || lower.includes('cathode') || lower.includes('anode') || lower.includes('lithium') || lower.includes('cobalt') || lower.includes('nickel') || lower.includes('manganese') || lower.includes('graphite')) return 'KG'
  return 'EA'
}

function getAcctAssignment(materialName: string): string {
  const lower = materialName.toLowerCase()
  if (lower.includes('cell') || lower.includes('cathode') || lower.includes('anode') || lower.includes('electrolyte')) return 'K - Cost Center'
  if (lower.includes('pack') || lower.includes('module')) return 'A - Asset'
  return 'K - Cost Center'
}

export default function PurchaseRequisitionPreview({ solution, onAllSubmitted }: PurchaseRequisitionPreviewProps) {
  const [submittedAll, setSubmittedAll] = useState(false)
  const [submittedPRs, setSubmittedPRs] = useState<Set<string>>(new Set())
  const [sapExportResult, setSapExportResult] = useState<{ exportSuccess: boolean; exportPath?: string } | null>(null)
  const [sapExporting, setSapExporting] = useState(false)
  const [sapPreviewDocs, setSapPreviewDocs] = useState<SAPODataDocument[] | null>(null)
  const [sapExportedAll, setSapExportedAll] = useState(false)
  const [sapExportedPRs, setSapExportedPRs] = useState<Set<string>>(new Set())

  if (!solution) {
    return (
      <div style={{
        padding: '40px 24px',
        background: '#ffffff',
        borderRadius: '4px',
        border: '1px solid #d9d9d9',
        textAlign: 'center',
        color: '#6a6d70',
        fontFamily: '\'72\', Arial, Helvetica, sans-serif',
      }}>
        Select a solution to preview purchase requisitions
      </div>
    )
  }

  // Group allocations by supplier
  const prsBySupplier = solution.allocations.reduce((acc, alloc) => {
    if (!acc[alloc.supplierId]) {
      acc[alloc.supplierId] = {
        supplierName: alloc.supplierName,
        items: []
      }
    }
    acc[alloc.supplierId].items.push(alloc)
    return acc
  }, {} as Record<string, { supplierName: string; items: typeof solution.allocations }>)

  const prList = Object.entries(prsBySupplier).map(([supplierId, data], idx) => {
    const totalCost = data.items.reduce((sum, item) => sum + item.totalCost, 0)
    const prNumber = 10020000 + idx + 1
    const freightEstimate = data.items.reduce((sum, item) => sum + (item.freightCost || item.totalCost * 0.025), 0)
    const taxEstimate = totalCost * 0.075

    return {
      prNumber: String(prNumber),
      supplierId,
      supplierName: data.supplierName,
      items: data.items,
      subtotal: totalCost,
      freightEstimate,
      taxEstimate,
      grandTotal: totalCost + freightEstimate + taxEstimate,
    }
  })

  const overallSubtotal = prList.reduce((s, pr) => s + pr.subtotal, 0)
  const overallFreight = prList.reduce((s, pr) => s + pr.freightEstimate, 0)
  const overallTax = prList.reduce((s, pr) => s + pr.taxEstimate, 0)
  const overallTotal = overallSubtotal + overallFreight + overallTax

  const creationDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })

  const handleSAPExport = async (singlePR?: typeof prList[0]) => {
    // 1. Generate OData JSON client-side (always works)
    const allocsForOData = singlePR
      ? singlePR.items.map(item => ({
          supplierId: singlePR.supplierId,
          supplierName: singlePR.supplierName,
          materialId: item.materialId,
          materialName: item.materialName,
          quantity: item.quantity,
          unitPrice: item.unitPrice,
          leadTimeDays: item.leadTimeDays,
        }))
      : solution.allocations.map(a => ({
          supplierId: a.supplierId,
          supplierName: a.supplierName,
          materialId: a.materialId,
          materialName: a.materialName,
          quantity: a.quantity,
          unitPrice: a.unitPrice,
          leadTimeDays: a.leadTimeDays,
        }))

    const docs = generateODataDocuments(solution.name, allocsForOData)
    setSapPreviewDocs(docs)

    // 2. Try export in background (may fail if backend unavailable)
    setSapExporting(true)
    try {
      const result = await exportSAPOData({
        solution_name: solution.name,
        allocations: allocsForOData.map(a => ({
          supplier_id: a.supplierId,
          supplier_name: a.supplierName,
          material_id: a.materialId,
          material_name: a.materialName,
          quantity: a.quantity,
          unit_price: a.unitPrice,
          lead_time_days: a.leadTimeDays,
        })),
        requester: 'procurement@voltcycle.com',
      })
      setSapExportResult({ exportSuccess: true, exportPath: result.export_id })
      if (singlePR) {
        setSapExportedPRs(prev => new Set(prev).add(singlePR.prNumber))
      } else {
        setSapExportedAll(true)
      }
    } catch {
      setSapExportResult({ exportSuccess: false })
    } finally {
      setSapExporting(false)
    }
  }

  return (
    <div style={{
      fontFamily: '\'72\', Arial, Helvetica, sans-serif',
      background: '#f7f7f7',
      borderRadius: '4px',
      border: '1px solid #d9d9d9',
    }}>
      {/* ---- SAP-style Title Bar ---- */}
      <div style={{
        background: '#354a5f',
        padding: '12px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderRadius: '4px 4px 0 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ color: '#ffffff', fontSize: '15px', fontWeight: 700 }}>
            Create Purchase Requisition: ME51N
          </span>
          <span style={{
            background: '#e8f5e1',
            color: '#256f3a',
            fontSize: '11px',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '3px',
          }}>
            {prList.length} Document{prList.length !== 1 ? 's' : ''}
          </span>
        </div>
        <span style={{ color: '#a9b4be', fontSize: '11px' }}>
          Transaction: ME51N | Client 100
        </span>
      </div>

      {/* ---- Bulk Action Bar ---- */}
      <div style={{
        padding: '10px 20px',
        background: '#edf2f7',
        borderBottom: '1px solid #d9d9d9',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ fontSize: '12px', color: '#354a5f', fontWeight: 600 }}>
          {prList.length} requisition{prList.length !== 1 ? 's' : ''} · {solution.name} · {formatCurrency(overallTotal)} total
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => downloadAllPRs(prList, solution.name)}
            style={{
              padding: '6px 14px', background: '#0a6ed1', border: '1px solid #0854a0',
              borderRadius: '4px', fontSize: '11px', fontWeight: 600, color: '#ffffff', cursor: 'pointer',
            }}
          >
            ⬇ Download All PDF
          </button>
          <button
            onClick={() => handleSAPExport()}
            disabled={sapExporting}
            style={{
              padding: '6px 14px',
              background: sapExportedAll ? '#f0fdf4' : '#ffffff',
              border: sapExportedAll ? '1px solid #16a34a' : '1px solid #0a6ed1',
              borderRadius: '4px', fontSize: '11px', fontWeight: 600,
              color: sapExportedAll ? '#16a34a' : sapExporting ? '#89919a' : '#0a6ed1',
              cursor: sapExporting ? 'wait' : 'pointer',
            }}
          >
            {sapExportedAll ? '✓ Exported to SAP' : sapExporting ? '⏳ Exporting...' : '📤 Export All to SAP'}
          </button>
          <button
            onClick={() => { setSubmittedAll(true); onAllSubmitted?.() }}
            disabled={submittedAll}
            style={{
              padding: '6px 14px', background: submittedAll ? '#e8f5e1' : '#ffffff',
              border: submittedAll ? '1px solid #256f3a' : '1px solid #89919a',
              borderRadius: '4px', fontSize: '11px', fontWeight: 600,
              color: submittedAll ? '#256f3a' : '#32363a',
              cursor: submittedAll ? 'default' : 'pointer',
            }}
          >
            {submittedAll ? '✓ All Submitted' : '✓ Submit All for Approval'}
          </button>
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {prList.map((pr, prIdx) => {
          const lineItems = pr.items

          return (
            <div key={pr.prNumber} style={{
              background: '#ffffff',
              border: '1px solid #d9d9d9',
              borderRadius: '4px',
              marginBottom: prIdx < prList.length - 1 ? '20px' : '0',
            }}>
              {/* ---- Document Header ---- */}
              <div style={{
                borderBottom: '1px solid #d9d9d9',
                padding: '16px 20px 12px',
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '14px',
                }}>
                  <div>
                    <div style={{ fontSize: '11px', color: '#6a6d70', marginBottom: '2px' }}>
                      Purchase Requisition
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#32363a' }}>
                      {pr.prNumber}
                    </div>
                  </div>
                  {(() => {
                    const isSubmitted = submittedAll || submittedPRs.has(pr.prNumber)
                    return (
                      <div style={{
                        padding: '4px 10px',
                        background: isSubmitted ? '#e8f5e1' : '#fff3cd',
                        border: isSubmitted ? '1px solid #256f3a' : '1px solid #e6c200',
                        borderRadius: '3px',
                        fontSize: '11px',
                        fontWeight: 700,
                        color: isSubmitted ? '#256f3a' : '#8a6d00',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}>
                        {isSubmitted ? '✓ Submitted' : 'Draft'}
                      </div>
                    )
                  })()}
                </div>

                {/* Header fields grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                  gap: '12px 24px',
                }}>
                  <div>
                    <div style={labelStyle}>Document Type</div>
                    <div style={valueStyle}>NB - Standard</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Created By</div>
                    <div style={valueStyle}>VOLTCYCLE_PROC</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Creation Date</div>
                    <div style={valueStyle}>{creationDate}</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Purchase Org.</div>
                    <div style={valueStyle}>1000 - VoltCycle NA</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Plant</div>
                    <div style={valueStyle}>1100 - Denver</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Company Code</div>
                    <div style={valueStyle}>1000</div>
                  </div>
                </div>
              </div>

              {/* ---- Status Workflow Stepper ---- */}
              <div style={{
                padding: '14px 20px',
                borderBottom: '1px solid #d9d9d9',
                background: '#fafafa',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0',
                }}>
                  {STATUS_STEPS.map((step, idx) => {
                    const prStep = (submittedAll || submittedPRs.has(pr.prNumber)) ? 1 : 0
                    const isActive = idx === prStep
                    const isCompleted = idx < prStep
                    const isLast = idx === STATUS_STEPS.length - 1

                    return (
                      <div key={step} style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '90px' }}>
                          <div style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '11px',
                            fontWeight: 700,
                            background: isActive ? '#0a6ed1' : isCompleted ? '#256f3a' : '#d9d9d9',
                            color: isActive || isCompleted ? '#ffffff' : '#6a6d70',
                            marginBottom: '4px',
                          }}>
                            {isCompleted ? '\u2713' : idx + 1}
                          </div>
                          <div style={{
                            fontSize: '10px',
                            fontWeight: isActive ? 700 : 500,
                            color: isActive ? '#0a6ed1' : isCompleted ? '#256f3a' : '#6a6d70',
                          }}>
                            {step}
                          </div>
                        </div>
                        {!isLast && (
                          <div style={{
                            width: '48px',
                            height: '2px',
                            background: isCompleted ? '#256f3a' : '#d9d9d9',
                            marginBottom: '16px',
                          }} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* ---- Line Items Table ---- */}
              <div style={{ padding: '16px 20px' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#32363a', marginBottom: '10px' }}>
                  Line Items
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '900px' }}>
                    <thead>
                      <tr>
                        <th style={{ ...headerCellStyle, textAlign: 'center', width: '40px' }}>Item</th>
                        <th style={{ ...headerCellStyle, textAlign: 'left' }}>Material</th>
                        <th style={{ ...headerCellStyle, textAlign: 'left', minWidth: '160px' }}>Short Text</th>
                        <th style={{ ...headerCellStyle, textAlign: 'right', width: '60px' }}>Qty</th>
                        <th style={{ ...headerCellStyle, textAlign: 'center', width: '40px' }}>UoM</th>
                        <th style={{ ...headerCellStyle, textAlign: 'center', width: '90px' }}>Delivery Date</th>
                        <th style={{ ...headerCellStyle, textAlign: 'right', width: '90px' }}>Price</th>
                        <th style={{ ...headerCellStyle, textAlign: 'right', width: '100px' }}>Net Value</th>
                        <th style={{ ...headerCellStyle, textAlign: 'left', minWidth: '120px' }}>Supplier</th>
                        <th style={{ ...headerCellStyle, textAlign: 'left', minWidth: '110px' }}>Acct Assignment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineItems.map((item, idx) => {
                        const deliveryDate = new Date(Date.now() + item.leadTimeDays * 86400000)
                          .toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })
                        const itemNumber = (idx + 1) * 10
                        const isEvenRow = idx % 2 === 0

                        return (
                          <tr key={idx} style={{ background: isEvenRow ? '#ffffff' : '#f7f7f7' }}>
                            <td style={{ ...cellStyle, textAlign: 'center', fontWeight: 600 }}>
                              {String(itemNumber).padStart(4, '0')}
                            </td>
                            <td style={{ ...cellStyle, fontFamily: 'monospace', fontSize: '11px' }}>
                              {generateMaterialNumber(item.materialId, idx)}
                            </td>
                            <td style={cellStyle}>{item.materialName}</td>
                            <td style={{ ...cellStyle, textAlign: 'right', fontWeight: 600 }}>
                              {item.quantity.toLocaleString()}
                            </td>
                            <td style={{ ...cellStyle, textAlign: 'center' }}>{getUoM(item.materialName)}</td>
                            <td style={{ ...cellStyle, textAlign: 'center', fontSize: '11px' }}>{deliveryDate}</td>
                            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatCurrency(item.unitPrice)}</td>
                            <td style={{ ...cellStyle, textAlign: 'right', fontWeight: 600 }}>
                              {formatCurrency(item.totalCost)}
                            </td>
                            <td style={{ ...cellStyle, fontSize: '11px' }}>{item.supplierName}</td>
                            <td style={{ ...cellStyle, fontSize: '11px' }}>{getAcctAssignment(item.materialName)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* ---- Totals Section ---- */}
              <div style={{
                padding: '12px 20px 16px',
                borderTop: '1px solid #d9d9d9',
                background: '#fafafa',
              }}>
                <div style={{ maxWidth: '320px', marginLeft: 'auto' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                    <span>Subtotal</span>
                    <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(pr.subtotal)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                    <span>Freight Estimate</span>
                    <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(pr.freightEstimate)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                    <span>Tax Estimate (7.5%)</span>
                    <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(pr.taxEstimate)}</span>
                  </div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '8px 0 0',
                    marginTop: '6px',
                    borderTop: '2px solid #354a5f',
                    fontSize: '14px',
                    fontWeight: 700,
                    color: '#32363a',
                  }}>
                    <span>Total</span>
                    <span>{formatCurrency(pr.grandTotal)}</span>
                  </div>
                </div>
              </div>

              {/* ---- Action Buttons ---- */}
              <div style={{
                padding: '12px 20px',
                borderTop: '1px solid #d9d9d9',
                display: 'flex',
                gap: '8px',
                justifyContent: 'flex-end',
                background: '#ffffff',
                borderRadius: '0 0 4px 4px',
              }}>
                <button
                  onClick={() => setSubmittedPRs(prev => new Set(prev).add(pr.prNumber))}
                  disabled={submittedAll || submittedPRs.has(pr.prNumber)}
                  style={{
                    padding: '7px 16px',
                    background: (submittedAll || submittedPRs.has(pr.prNumber)) ? '#e8f5e1' : '#0a6ed1',
                    border: (submittedAll || submittedPRs.has(pr.prNumber)) ? '1px solid #256f3a' : '1px solid #0854a0',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: (submittedAll || submittedPRs.has(pr.prNumber)) ? '#256f3a' : '#ffffff',
                    cursor: (submittedAll || submittedPRs.has(pr.prNumber)) ? 'default' : 'pointer',
                  }}
                >
                  {(submittedAll || submittedPRs.has(pr.prNumber)) ? '✓ Submitted' : 'Submit for Approval'}
                </button>
                <button
                  onClick={() => handleSAPExport(pr)}
                  disabled={sapExporting}
                  style={{
                    padding: '7px 16px',
                    background: (sapExportedAll || sapExportedPRs.has(pr.prNumber)) ? '#f0fdf4' : '#ffffff',
                    border: (sapExportedAll || sapExportedPRs.has(pr.prNumber)) ? '1px solid #16a34a' : '1px solid #0a6ed1',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: (sapExportedAll || sapExportedPRs.has(pr.prNumber)) ? '#16a34a' : sapExporting ? '#89919a' : '#0a6ed1',
                    cursor: sapExporting ? 'wait' : 'pointer',
                  }}
                >
                  {(sapExportedAll || sapExportedPRs.has(pr.prNumber)) ? '✓ Exported' : sapExporting ? 'Exporting...' : 'Export to SAP'}
                </button>
                <button
                  onClick={() => downloadSinglePR(pr, solution.name)}
                  style={{
                    padding: '7px 16px',
                    background: '#ffffff',
                    border: '1px solid #89919a',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#32363a',
                    cursor: 'pointer',
                  }}
                >
                  Download PDF
                </button>
              </div>
            </div>
          )
        })}

        {/* ---- Overall Summary ---- */}
        {prList.length > 1 && (
          <div style={{
            marginTop: '20px',
            background: '#ffffff',
            border: '1px solid #d9d9d9',
            borderRadius: '4px',
            padding: '16px 20px',
          }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#32363a', marginBottom: '10px' }}>
              Requisition Summary -- {prList.length} Documents
            </div>
            <div style={{ maxWidth: '320px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                <span>Subtotal</span>
                <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(overallSubtotal)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                <span>Freight Estimate</span>
                <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(overallFreight)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '12px', color: '#6a6d70' }}>
                <span>Tax Estimate</span>
                <span style={{ color: '#32363a', fontWeight: 500 }}>{formatCurrency(overallTax)}</span>
              </div>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 0 0',
                marginTop: '6px',
                borderTop: '2px solid #354a5f',
                fontSize: '14px',
                fontWeight: 700,
                color: '#32363a',
              }}>
                <span>Grand Total</span>
                <span>{formatCurrency(overallTotal)}</span>
              </div>
            </div>
          </div>
        )}

        {/* ---- Footer ---- */}
        <div style={{
          marginTop: '16px',
          padding: '10px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '10px',
          color: '#89919a',
        }}>
          <span>Integration: SAP S/4HANA via OData | Purchase Org 1000 | Company Code 1000</span>
          <span style={{
            fontWeight: 700,
            fontSize: '11px',
            color: '#354a5f',
            letterSpacing: '0.08em',
          }}>
            [SAP]
          </span>
        </div>
      </div>

      {/* ---- SAP OData Preview Modal ---- */}
      {sapPreviewDocs && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => { setSapPreviewDocs(null); setSapExportResult(null) }}>
          <div style={{
            background: '#fff', borderRadius: '8px', width: '720px', maxHeight: '85vh',
            display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          }} onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div style={{
              padding: '16px 20px', borderBottom: '1px solid #d9d9d9',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#354a5f' }}>
                  SAP OData Export — {solution.name}
                </div>
                <div style={{ fontSize: '11px', color: '#6a6d70', marginTop: '2px' }}>
                  {sapPreviewDocs.length} document{sapPreviewDocs.length !== 1 ? 's' : ''} · API_PURCHASEREQ_PROCESS_SRV · OData v2
                </div>
              </div>
              <button onClick={() => { setSapPreviewDocs(null); setSapExportResult(null) }} style={{
                background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6a6d70',
              }}>×</button>
            </div>

            {/* Export status banner */}
            {sapExportResult && (
              <div style={{
                padding: '8px 20px',
                background: sapExportResult.exportSuccess ? '#f0fdf4' : '#fefce8',
                borderBottom: '1px solid ' + (sapExportResult.exportSuccess ? '#bbf7d0' : '#fef08a'),
                fontSize: '12px',
                color: sapExportResult.exportSuccess ? '#166534' : '#854d0e',
                display: 'flex', alignItems: 'center', gap: '6px',
              }}>
                {sapExportResult.exportSuccess ? (
                  <>✅ Successfully exported · Ref: <code style={{ background: 'rgba(0,0,0,0.06)', padding: '1px 6px', borderRadius: 3, fontSize: '11px' }}>{sapExportResult.exportPath}</code></>
                ) : (
                  <>ℹ️ Export service is currently unavailable. The OData preview below is ready for manual integration. Please try again later.</>
                )}
              </div>
            )}
            {sapExporting && (
              <div style={{
                padding: '8px 20px', background: '#eff6ff', borderBottom: '1px solid #bfdbfe',
                fontSize: '12px', color: '#1e40af',
              }}>
                ⏳ Exporting...
              </div>
            )}

            {/* JSON preview */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
              <pre style={{
                background: '#1e293b', color: '#e2e8f0', padding: '16px',
                borderRadius: '6px', fontSize: '11px', lineHeight: '1.5',
                overflow: 'auto', margin: 0,
              }}>
                {/* nosemgrep: no-stringify-keys -- stringify is for display formatting in a <pre>, not object key generation */}
                {JSON.stringify(sapPreviewDocs.length === 1 ? sapPreviewDocs[0] : sapPreviewDocs, null, 2)}
              </pre>
            </div>

            {/* Footer */}
            <div style={{
              padding: '12px 20px', borderTop: '1px solid #d9d9d9',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ fontSize: '10px', color: '#89919a' }}>
                POST /sap/opu/odata/sap/API_PURCHASEREQ_PROCESS_SRV/A_PurchaseRequisitionHeader
              </span>
              <button onClick={() => { setSapPreviewDocs(null); setSapExportResult(null) }} style={{
                padding: '7px 16px', background: '#354a5f', border: 'none',
                borderRadius: '4px', fontSize: '12px', fontWeight: 600, color: '#fff', cursor: 'pointer',
              }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
