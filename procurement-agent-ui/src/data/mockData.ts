// Mock data for procurement optimization demo
// Based on data/ CSV files

export interface Supplier {
  id: string;
  name: string;
  rating: number;
  financialStability: number;
  geopoliticalRisk: number;
  location: string;
}

export interface Material {
  id: string;
  name: string;
  quantity: number;
  unit: string;
}

export interface SupplierAllocation {
  supplierId: string;
  supplierName: string;
  materialId: string;
  quantity: number;
  unitPrice: number;
  totalCost: number;
  leadTimeDays: number;
}

export interface Solution {
  id: string;
  name: string;
  totalCost: number;
  riskScore: number;
  maxLeadTimeDays: number;
  allocations: SupplierAllocation[];
  explanation: string;
}

// Mock suppliers from suppliers.csv
export const mockSuppliers: Supplier[] = [
  {
    id: "SUP-001",
    name: "BatteryTech Solutions",
    rating: 4.25,
    financialStability: 7.5,
    geopoliticalRisk: 3.2,
    location: "South Korea"
  },
  {
    id: "SUP-002",
    name: "PremiumPower Corp",
    rating: 4.8,
    financialStability: 9.2,
    geopoliticalRisk: 1.8,
    location: "Germany"
  },
  {
    id: "SUP-003",
    name: "ReliableBattery Inc",
    rating: 4.5,
    financialStability: 8.1,
    geopoliticalRisk: 2.5,
    location: "USA"
  },
  {
    id: "SUP-004",
    name: "CostEffective Supplies",
    rating: 3.8,
    financialStability: 6.5,
    geopoliticalRisk: 5.2,
    location: "China"
  },
  {
    id: "SUP-005",
    name: "FastDelivery Materials",
    rating: 4.1,
    financialStability: 7.8,
    geopoliticalRisk: 2.9,
    location: "Japan"
  }
];

// Mock materials
export const mockMaterials: Material[] = [
  { id: "MAT-001", name: "Lithium-ion Battery Cells", quantity: 10000, unit: "units" },
  { id: "MAT-002", name: "Battery Management System", quantity: 5000, unit: "units" },
  { id: "MAT-003", name: "Electric Motor Assembly", quantity: 2500, unit: "units" }
];

// Mock Pareto frontier solutions
export const mockSolutions: Solution[] = [
  {
    id: "SOL-A",
    name: "Cost-Optimized",
    totalCost: 52000,
    riskScore: 6.8,
    maxLeadTimeDays: 45,
    allocations: [
      {
        supplierId: "SUP-004",
        supplierName: "CostEffective Supplies",
        materialId: "MAT-001",
        quantity: 7000,
        unitPrice: 5.0,
        totalCost: 35000,
        leadTimeDays: 45
      },
      {
        supplierId: "SUP-001",
        supplierName: "BatteryTech Solutions",
        materialId: "MAT-001",
        quantity: 3000,
        unitPrice: 5.67,
        totalCost: 17000,
        leadTimeDays: 30
      }
    ],
    explanation: "Lowest cost solution at $52k, but higher risk (6.8/10) due to 70% concentration with CostEffective Supplies. Longer lead time of 45 days."
  },
  {
    id: "SOL-B",
    name: "Balanced",
    totalCost: 67500,
    riskScore: 4.2,
    maxLeadTimeDays: 30,
    allocations: [
      {
        supplierId: "SUP-002",
        supplierName: "PremiumPower Corp",
        materialId: "MAT-001",
        quantity: 4000,
        unitPrice: 8.5,
        totalCost: 34000,
        leadTimeDays: 20
      },
      {
        supplierId: "SUP-003",
        supplierName: "ReliableBattery Inc",
        materialId: "MAT-001",
        quantity: 4000,
        unitPrice: 6.5,
        totalCost: 26000,
        leadTimeDays: 25
      },
      {
        supplierId: "SUP-001",
        supplierName: "BatteryTech Solutions",
        materialId: "MAT-001",
        quantity: 2000,
        unitPrice: 3.75,
        totalCost: 7500,
        leadTimeDays: 30
      }
    ],
    explanation: "Balanced solution with good risk diversification (4.2/10). Three suppliers, no single supplier >40%. Moderate cost at $67.5k, 30-day lead time."
  },
  {
    id: "SOL-C",
    name: "Risk-Minimized",
    totalCost: 87000,
    riskScore: 1.9,
    maxLeadTimeDays: 20,
    allocations: [
      {
        supplierId: "SUP-002",
        supplierName: "PremiumPower Corp",
        materialId: "MAT-001",
        quantity: 10000,
        unitPrice: 8.7,
        totalCost: 87000,
        leadTimeDays: 20
      }
    ],
    explanation: "Lowest risk solution (1.9/10) with premium supplier. Fastest delivery at 20 days. Highest cost at $87k. Single supplier concentration acceptable due to high reliability."
  }
];

// Mock chat messages
export const mockChatHistory = [
  {
    role: "user",
    content: "I need to optimize suppliers for Q2 battery cell production. We need 10,000 lithium-ion cells.",
    timestamp: new Date(Date.now() - 120000)
  },
  {
    role: "assistant",
    content: "I'll help you optimize the supplier mix for 10,000 lithium-ion battery cells. Let me analyze the available suppliers and generate optimal solutions...",
    timestamp: new Date(Date.now() - 110000)
  },
  {
    role: "assistant",
    content: "Analysis complete! I've identified 3 optimal solutions on the Pareto frontier:\n\n✅ Solution A (Cost-Optimized): $52k, 6.8 risk, 45 days\n✅ Solution B (Balanced): $67.5k, 4.2 risk, 30 days\n✅ Solution C (Risk-Minimized): $87k, 1.9 risk, 20 days\n\nYou can see the trade-offs in the Pareto chart. Which approach interests you?",
    timestamp: new Date(Date.now() - 100000)
  }
];

// Network graph data
export const mockNetworkData = {
  nodes: [
    { id: "MAT-001", label: "Li-ion Cells", type: "material", size: 30 },
    { id: "SUP-001", label: "BatteryTech", type: "supplier", size: 20, risk: 3.2 },
    { id: "SUP-002", label: "PremiumPower", type: "supplier", size: 25, risk: 1.8 },
    { id: "SUP-003", label: "ReliableBattery", type: "supplier", size: 22, risk: 2.5 },
    { id: "SUP-004", label: "CostEffective", type: "supplier", size: 18, risk: 5.2 },
    { id: "SUP-005", label: "FastDelivery", type: "supplier", size: 15, risk: 2.9 }
  ],
  links: [
    { source: "SUP-001", target: "MAT-001", value: 3000, price: 5.67 },
    { source: "SUP-002", target: "MAT-001", value: 4000, price: 8.5 },
    { source: "SUP-003", target: "MAT-001", value: 4000, price: 6.5 },
    { source: "SUP-004", target: "MAT-001", value: 7000, price: 5.0 },
    { source: "SUP-005", target: "MAT-001", value: 2000, price: 6.2 }
  ]
};
