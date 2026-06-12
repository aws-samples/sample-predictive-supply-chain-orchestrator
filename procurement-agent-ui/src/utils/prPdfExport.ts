import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

interface PRLineItem {
  materialId: string
  materialName: string
  quantity: number
  unitPrice: number
  totalCost: number
  leadTimeDays: number
}

interface PRData {
  prNumber: string
  supplierId: string
  supplierName: string
  items: PRLineItem[]
  subtotal: number
  freightEstimate: number
  taxEstimate: number
  grandTotal: number
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

function renderPRToPdf(doc: jsPDF, pr: PRData, startY: number, solutionName: string): number {
  const creationDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })
  const pageWidth = doc.internal.pageSize.getWidth()
  let y = startY

  // PR Header bar
  doc.setFillColor(53, 74, 95) // #354a5f
  doc.rect(14, y, pageWidth - 28, 10, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.text(`Purchase Requisition: ${pr.prNumber}`, 18, y + 7)
  doc.setFontSize(8)
  doc.text(`Supplier: ${pr.supplierName}`, pageWidth - 18, y + 7, { align: 'right' })
  y += 14

  // Header fields
  doc.setTextColor(106, 109, 112)
  doc.setFontSize(7)
  doc.setFont('helvetica', 'normal')
  const fields = [
    ['Document Type', 'NB - Standard'],
    ['Created By', 'VOLTCYCLE_PROC'],
    ['Creation Date', creationDate],
    ['Purchase Org.', '1000 - VoltCycle NA'],
    ['Plant', '1100 - Denver'],
    ['Strategy', solutionName],
  ]
  const colWidth = (pageWidth - 28) / 3
  fields.forEach((f, i) => {
    const col = i % 3
    const row = Math.floor(i / 3)
    const x = 14 + col * colWidth
    const fy = y + row * 10
    doc.setTextColor(106, 109, 112)
    doc.text(f[0], x, fy)
    doc.setTextColor(50, 54, 58)
    doc.setFont('helvetica', 'bold')
    doc.text(f[1], x, fy + 4)
    doc.setFont('helvetica', 'normal')
  })
  y += Math.ceil(fields.length / 3) * 10 + 4

  // Line items table
  const tableData = pr.items.map((item, idx) => {
    const deliveryDate = new Date(Date.now() + item.leadTimeDays * 86400000)
      .toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })
    return [
      String((idx + 1) * 10).padStart(4, '0'),
      generateMaterialNumber(item.materialId, idx),
      item.materialName,
      item.quantity.toLocaleString(),
      getUoM(item.materialName),
      deliveryDate,
      formatCurrency(item.unitPrice),
      formatCurrency(item.totalCost),
    ]
  })

  autoTable(doc, {
    startY: y,
    head: [['Item', 'Material', 'Short Text', 'Qty', 'UoM', 'Delivery', 'Price', 'Net Value']],
    body: tableData,
    theme: 'grid',
    headStyles: { fillColor: [53, 74, 95], fontSize: 7, fontStyle: 'bold', halign: 'center' },
    bodyStyles: { fontSize: 7 },
    columnStyles: {
      0: { halign: 'center', cellWidth: 12 },
      1: { cellWidth: 20, font: 'courier' },
      2: { cellWidth: 40 },
      3: { halign: 'right', cellWidth: 14 },
      4: { halign: 'center', cellWidth: 12 },
      5: { halign: 'center', cellWidth: 20 },
      6: { halign: 'right', cellWidth: 22 },
      7: { halign: 'right', cellWidth: 24 },
    },
    margin: { left: 14, right: 14 },
  })

  y = (doc as any).lastAutoTable.finalY + 4

  // Totals
  const totalsX = pageWidth - 14 - 70
  const totals = [
    ['Subtotal', formatCurrency(pr.subtotal)],
    ['Freight Est.', formatCurrency(pr.freightEstimate)],
    ['Tax (7.5%)', formatCurrency(pr.taxEstimate)],
  ]
  doc.setFontSize(7)
  totals.forEach((t, i) => {
    doc.setTextColor(106, 109, 112)
    doc.text(t[0], totalsX, y + i * 5)
    doc.setTextColor(50, 54, 58)
    doc.text(t[1], pageWidth - 14, y + i * 5, { align: 'right' })
  })
  y += totals.length * 5 + 2

  // Grand total line
  doc.setDrawColor(53, 74, 95)
  doc.setLineWidth(0.5)
  doc.line(totalsX, y, pageWidth - 14, y)
  y += 4
  doc.setFontSize(9)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(50, 54, 58)
  doc.text('Total', totalsX, y)
  doc.text(formatCurrency(pr.grandTotal), pageWidth - 14, y, { align: 'right' })
  doc.setFont('helvetica', 'normal')

  return y + 10
}

export function downloadSinglePR(pr: PRData, solutionName: string): void {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })

  // Title
  doc.setFontSize(8)
  doc.setTextColor(150)
  doc.text('VoltCycle Procurement | SAP S/4HANA ME51N', 14, 10)
  doc.text(`Generated: ${new Date().toLocaleString()}`, doc.internal.pageSize.getWidth() - 14, 10, { align: 'right' })

  renderPRToPdf(doc, pr, 16, solutionName)

  doc.save(`PR-${pr.prNumber}-${pr.supplierName.replace(/\s+/g, '_')}.pdf`)
}

export function downloadAllPRs(prList: PRData[], solutionName: string): void {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const pageWidth = doc.internal.pageSize.getWidth()

  // Cover info
  doc.setFontSize(8)
  doc.setTextColor(150)
  doc.text('VoltCycle Procurement | SAP S/4HANA ME51N', 14, 10)
  doc.text(`Generated: ${new Date().toLocaleString()}`, pageWidth - 14, 10, { align: 'right' })

  doc.setFontSize(14)
  doc.setTextColor(50, 54, 58)
  doc.setFont('helvetica', 'bold')
  doc.text(`Purchase Requisitions — ${solutionName}`, 14, 20)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(106, 109, 112)
  doc.text(`${prList.length} documents | Total: ${formatCurrency(prList.reduce((s, p) => s + p.grandTotal, 0))}`, 14, 26)

  let y = 34

  prList.forEach((pr, idx) => {
    // Check if we need a new page (leave room for at least header + a few rows)
    if (y > doc.internal.pageSize.getHeight() - 60) {
      doc.addPage()
      y = 14
    }
    y = renderPRToPdf(doc, pr, y, solutionName)

    // Add spacing between PRs
    if (idx < prList.length - 1) {
      y += 4
    }
  })

  doc.save(`PRs-${solutionName.replace(/\s+/g, '_')}-${new Date().toISOString().slice(0, 10)}.pdf`)
}
