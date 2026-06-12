/**
 * Generate SAP OData v2 JSON for API_PURCHASEREQ_PROCESS_SRV.
 * Runs entirely client-side — no backend dependency.
 */

interface Allocation {
  supplierId: string
  supplierName: string
  materialId: string
  materialName: string
  quantity: number
  unitPrice: number
  leadTimeDays: number
}

export interface SAPODataDocument {
  __metadata: { uri: string; type: string }
  PurchaseRequisition: string
  PurchaseRequisitionType: string
  PurReqnDescription: string
  Requester: string
  to_PurchaseReqnItem: { results: SAPODataItem[] }
}

export interface SAPODataItem {
  PurchaseRequisitionItem: string
  PurchaseRequisitionItemText: string
  Material: string
  Plant: string
  RequestedQuantity: string
  BaseUnit: string
  PurchaseRequisitionPrice: string
  PurReqnItemCurrency: string
  DeliveryDate: string
  FixedSupplier: string
  PurchasingOrganization: string
  PurchasingGroup: string
  AccountAssignmentCategory: string
}

function getUoM(materialName: string): string {
  const lower = materialName.toLowerCase()
  if (lower.includes('cell') || lower.includes('module') || lower.includes('pack') || lower.includes('bms') || lower.includes('connector') || lower.includes('sensor')) return 'EA'
  if (lower.includes('electrolyte') || lower.includes('slurry') || lower.includes('solvent')) return 'L'
  if (lower.includes('foil') || lower.includes('sheet') || lower.includes('film')) return 'M2'
  if (lower.includes('powder') || lower.includes('cathode') || lower.includes('anode')) return 'KG'
  return 'EA'
}

export function generateODataDocuments(
  solutionName: string,
  allocations: Allocation[],
  requester: string = 'procurement@voltcycle.com',
): SAPODataDocument[] {
  // Group by supplier
  const bySupplier: Record<string, { supplierName: string; items: Allocation[] }> = {}
  for (const alloc of allocations) {
    if (!bySupplier[alloc.supplierId]) {
      bySupplier[alloc.supplierId] = { supplierName: alloc.supplierName, items: [] }
    }
    bySupplier[alloc.supplierId].items.push(alloc)
  }

  return Object.entries(bySupplier).map(([supplierId, data], idx) => {
    const prNumber = 10020000 + idx + 1

    const odataItems: SAPODataItem[] = data.items.map((item, itemIdx) => {
      const deliveryDate = new Date(Date.now() + item.leadTimeDays * 86400000)
        .toISOString().split('T')[0] + 'T00:00:00'

      return {
        PurchaseRequisitionItem: String((itemIdx + 1) * 10).padStart(5, '0'),
        PurchaseRequisitionItemText: item.materialName,
        Material: item.materialId,
        Plant: '1100',
        RequestedQuantity: String(item.quantity),
        BaseUnit: getUoM(item.materialName),
        PurchaseRequisitionPrice: String(item.unitPrice.toFixed(2)),
        PurReqnItemCurrency: 'USD',
        DeliveryDate: deliveryDate,
        FixedSupplier: supplierId,
        PurchasingOrganization: '1000',
        PurchasingGroup: '001',
        AccountAssignmentCategory: 'K',
      }
    })

    return {
      __metadata: {
        uri: `A_PurchaseRequisitionHeader('${prNumber}')`,
        type: 'API_PURCHASEREQ_PROCESS_SRV.A_PurchaseRequisitionHeaderType',
      },
      PurchaseRequisition: String(prNumber),
      PurchaseRequisitionType: 'NB',
      PurReqnDescription: `${solutionName} - ${data.supplierName}`,
      Requester: requester,
      to_PurchaseReqnItem: { results: odataItems },
    }
  })
}
