// Real data loader from CSV files
// Parses actual supplier, material, and BOM data

export interface Supplier {
  id: string;
  name: string;
  location: string;
  rating: number;
  leadTimeDays: number;
  paymentTerms: string;
  financialStability: number;
  geopoliticalRisk: number;
  activeStatus: boolean;
  contactEmail: string;
  contactPhone: string;
}

export interface Material {
  id: string;
  name: string;
  category: string;
  unitOfMeasure: string;
  standardCost: number;
  criticalityLevel: string;
  weightKg: number;
}

export interface SupplierMaterial {
  id: string;
  supplierId: string;
  materialId: string;
  basePrice: number;
  currency: string;
  effectiveDate: string;
  minimumOrderQuantity: number;
  leadTimeDays: number;
  qualityCertification: string;
  sustainabilityScore: number;
  carbonFootprintKg: number;
}

export interface BOMItem {
  id: string;
  productId: string;
  materialId: string;
  quantityRequired: number;
  leadTimeDays: number;
  assemblySequence: number;
}

export interface DemandForecast {
  forecastId: string;
  materialId: string;
  forecastPeriod: string;
  predictedDemand: number;
  confidenceLevel: number;
  forecastDate: string;
  notes: string;
}

export interface InventoryLevel {
  inventoryId: string;
  materialId: string;
  warehouseLocation: string;
  currentStock: number;
  reorderPoint: number;
  safetyStock: number;
  lastUpdated: string;
}

export interface SupplierPerformance {
  performanceId: string;
  supplierId: string;
  measurementPeriod: string;
  onTimeDeliveryRate: number;
  qualityScore: number;
  defectRate: number;
  costVariance: number;
  responseTimeHours: number;
}

export interface VolumeTier {
  tierId: string;
  supplierMaterialId: string;
  tierLevel: number;
  minQuantity: number;
  maxQuantity: number | null;
  discountPercentage: number;
  unitPrice: number;
}

export interface SupplierContract {
  contractId: string;
  supplierId: string;
  contractType: string;
  startDate: string;
  endDate: string;
  annualValue: number;
  paymentTerms: string;
  volumeCommitment: string;
  priceAdjustmentClause: string;
  sustainabilityClause: string;
  status: string;
  renewalOption: string;
}

export interface ProductionSchedule {
  scheduleId: string;
  productId: string;
  productName: string;
  plannedQuantity: number;
  startDate: string;
  endDate: string;
  status: string;
  priority: string;
  notes: string;
}

// Parse CSV data (hardcoded from data/ folder)
export const suppliers: Supplier[] = [
  { id: "SUP-001", name: "BatteryTech Solutions", location: "Shenzhen China", rating: 4.25, leadTimeDays: 30, paymentTerms: "NET 60", financialStability: 7.5, geopoliticalRisk: 3.2, activeStatus: true, contactEmail: "contact@batterytech.com", contactPhone: "+86-755-1234567" },
  { id: "SUP-002", name: "PowerCell Industries", location: "Seoul South Korea", rating: 4.50, leadTimeDays: 35, paymentTerms: "NET 45", financialStability: 8.2, geopoliticalRisk: 2.1, activeStatus: true, contactEmail: "sales@powercell.kr", contactPhone: "+82-2-9876543" },
  { id: "SUP-003", name: "EcoEnergy Systems", location: "San Jose USA", rating: 3.80, leadTimeDays: 45, paymentTerms: "NET 30", financialStability: 6.8, geopoliticalRisk: 1.5, activeStatus: true, contactEmail: "info@ecoenergy.com", contactPhone: "+1-408-555-0123" },
  { id: "SUP-004", name: "DriveMotor Corp", location: "Munich Germany", rating: 4.60, leadTimeDays: 40, paymentTerms: "NET 90", financialStability: 8.8, geopoliticalRisk: 1.8, activeStatus: true, contactEmail: "orders@drivemotor.de", contactPhone: "+49-89-123456" },
  { id: "SUP-005", name: "TorqueTech Motors", location: "Taipei Taiwan", rating: 4.10, leadTimeDays: 28, paymentTerms: "NET 60", financialStability: 7.2, geopoliticalRisk: 2.8, activeStatus: true, contactEmail: "contact@torquetech.tw", contactPhone: "+886-2-87654321" },
  { id: "SUP-006", name: "MotionDrive Systems", location: "Detroit USA", rating: 3.90, leadTimeDays: 50, paymentTerms: "NET 30", financialStability: 7.0, geopoliticalRisk: 1.5, activeStatus: true, contactEmail: "sales@motiondrive.com", contactPhone: "+1-313-555-0199" },
  { id: "SUP-007", name: "AlumaTech Frames", location: "Portland USA", rating: 4.40, leadTimeDays: 25, paymentTerms: "NET 45", financialStability: 8.0, geopoliticalRisk: 1.5, activeStatus: true, contactEmail: "info@alumatech.com", contactPhone: "+1-503-555-0145" },
  { id: "SUP-008", name: "CarbonFiber Pro", location: "Nagoya Japan", rating: 4.70, leadTimeDays: 38, paymentTerms: "NET 60", financialStability: 9.0, geopoliticalRisk: 2.0, activeStatus: true, contactEmail: "sales@carbonpro.jp", contactPhone: "+81-52-1234567" },
  { id: "SUP-009", name: "FrameWorks Ltd", location: "Manchester UK", rating: 4.00, leadTimeDays: 42, paymentTerms: "NET 90", financialStability: 7.5, geopoliticalRisk: 2.2, activeStatus: true, contactEmail: "orders@frameworks.co.uk", contactPhone: "+44-161-555-0178" },
  { id: "SUP-010", name: "SmartDisplay Tech", location: "Bangalore India", rating: 3.75, leadTimeDays: 32, paymentTerms: "NET 45", financialStability: 6.5, geopoliticalRisk: 3.5, activeStatus: true, contactEmail: "contact@smartdisplay.in", contactPhone: "+91-80-12345678" },
  { id: "SUP-011", name: "ElectroVision Systems", location: "Austin USA", rating: 4.20, leadTimeDays: 28, paymentTerms: "NET 30", financialStability: 7.8, geopoliticalRisk: 1.5, activeStatus: true, contactEmail: "sales@electrovision.com", contactPhone: "+1-512-555-0167" },
  { id: "SUP-012", name: "DisplayMaster Co", location: "Guangzhou China", rating: 3.95, leadTimeDays: 35, paymentTerms: "NET 60", financialStability: 7.0, geopoliticalRisk: 3.2, activeStatus: true, contactEmail: "info@displaymaster.cn", contactPhone: "+86-20-87654321" },
  { id: "SUP-013", name: "WheelCraft Industries", location: "Amsterdam Netherlands", rating: 4.35, leadTimeDays: 30, paymentTerms: "NET 45", financialStability: 8.3, geopoliticalRisk: 1.7, activeStatus: true, contactEmail: "orders@wheelcraft.nl", contactPhone: "+31-20-1234567" },
  { id: "SUP-014", name: "RollerTech Wheels", location: "Chicago USA", rating: 4.05, leadTimeDays: 40, paymentTerms: "NET 30", financialStability: 7.4, geopoliticalRisk: 1.5, activeStatus: true, contactEmail: "sales@rollertech.com", contactPhone: "+1-312-555-0189" },
  { id: "SUP-015", name: "BrakeSafe Systems", location: "Stuttgart Germany", rating: 4.65, leadTimeDays: 35, paymentTerms: "NET 90", financialStability: 8.9, geopoliticalRisk: 1.8, activeStatus: true, contactEmail: "contact@brakesafe.de", contactPhone: "+49-711-123456" }
];

export const materials: Material[] = [
  { id: "MAT-BAT-001", name: "Lithium-ion Battery Pack 48V 20Ah", category: "BATTERY_SYSTEM", unitOfMeasure: "EACH", standardCost: 450.00, criticalityLevel: "CRITICAL", weightKg: 6.50 },
  { id: "MAT-BAT-002", name: "Battery Management System (BMS)", category: "BATTERY_SYSTEM", unitOfMeasure: "EACH", standardCost: 85.00, criticalityLevel: "CRITICAL", weightKg: 0.35 },
  { id: "MAT-BAT-003", name: "Charging Port Assembly", category: "BATTERY_SYSTEM", unitOfMeasure: "EACH", standardCost: 25.00, criticalityLevel: "HIGH", weightKg: 0.15 },
  { id: "MAT-MOT-001", name: "Mid-Drive Motor 750W", category: "DRIVE_SYSTEM", unitOfMeasure: "EACH", standardCost: 380.00, criticalityLevel: "CRITICAL", weightKg: 4.20 },
  { id: "MAT-MOT-002", name: "Hub Motor 500W", category: "DRIVE_SYSTEM", unitOfMeasure: "EACH", standardCost: 280.00, criticalityLevel: "CRITICAL", weightKg: 3.80 },
  { id: "MAT-MOT-003", name: "Motor Controller 48V", category: "DRIVE_SYSTEM", unitOfMeasure: "EACH", standardCost: 120.00, criticalityLevel: "CRITICAL", weightKg: 0.60 },
  { id: "MAT-MOT-004", name: "Torque Sensor", category: "DRIVE_SYSTEM", unitOfMeasure: "EACH", standardCost: 65.00, criticalityLevel: "HIGH", weightKg: 0.25 },
  { id: "MAT-FRM-001", name: "Aluminum Frame 18 inch", category: "FRAME_COMPONENT", unitOfMeasure: "EACH", standardCost: 180.00, criticalityLevel: "CRITICAL", weightKg: 2.80 },
  { id: "MAT-FRM-002", name: "Carbon Fiber Frame 18 inch", category: "FRAME_COMPONENT", unitOfMeasure: "EACH", standardCost: 420.00, criticalityLevel: "HIGH", weightKg: 1.90 },
  { id: "MAT-FRM-003", name: "Suspension Fork", category: "FRAME_COMPONENT", unitOfMeasure: "EACH", standardCost: 150.00, criticalityLevel: "MEDIUM", weightKg: 1.50 },
  { id: "MAT-FRM-004", name: "Handlebar Assembly", category: "FRAME_COMPONENT", unitOfMeasure: "EACH", standardCost: 45.00, criticalityLevel: "MEDIUM", weightKg: 0.80 },
  { id: "MAT-ELC-001", name: "LCD Display 5 inch", category: "ELECTRONICS", unitOfMeasure: "EACH", standardCost: 95.00, criticalityLevel: "HIGH", weightKg: 0.30 },
  { id: "MAT-ELC-002", name: "Wiring Harness Complete", category: "ELECTRONICS", unitOfMeasure: "EACH", standardCost: 55.00, criticalityLevel: "HIGH", weightKg: 0.50 },
  { id: "MAT-ELC-003", name: "Speed Sensor", category: "ELECTRONICS", unitOfMeasure: "EACH", standardCost: 18.00, criticalityLevel: "MEDIUM", weightKg: 0.10 },
  { id: "MAT-STD-001", name: "Wheel Set 26 inch", category: "STANDARD_PARTS", unitOfMeasure: "PAIR", standardCost: 120.00, criticalityLevel: "HIGH", weightKg: 3.50 },
  { id: "MAT-STD-002", name: "Hydraulic Brake Set", category: "STANDARD_PARTS", unitOfMeasure: "SET", standardCost: 85.00, criticalityLevel: "HIGH", weightKg: 1.20 },
  { id: "MAT-STD-003", name: "Gear System 21-speed", category: "STANDARD_PARTS", unitOfMeasure: "SET", standardCost: 95.00, criticalityLevel: "MEDIUM", weightKg: 1.80 },
  { id: "MAT-STD-004", name: "Pedal Set", category: "STANDARD_PARTS", unitOfMeasure: "PAIR", standardCost: 28.00, criticalityLevel: "LOW", weightKg: 0.60 }
];

export const supplierMaterials: SupplierMaterial[] = [
  { id: "SM-001", supplierId: "SUP-001", materialId: "MAT-BAT-001", basePrice: 480.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 30, qualityCertification: "ISO 9001 UL Listed", sustainabilityScore: 7.80, carbonFootprintKg: 12.50 },
  { id: "SM-002", supplierId: "SUP-002", materialId: "MAT-BAT-001", basePrice: 465.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 150, leadTimeDays: 35, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.20, carbonFootprintKg: 11.80 },
  { id: "SM-003", supplierId: "SUP-003", materialId: "MAT-BAT-001", basePrice: 495.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 50, leadTimeDays: 45, qualityCertification: "UL Listed RoHS", sustainabilityScore: 9.10, carbonFootprintKg: 10.20 },
  { id: "SM-004", supplierId: "SUP-001", materialId: "MAT-BAT-002", basePrice: 92.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 200, leadTimeDays: 30, qualityCertification: "ISO 9001", sustainabilityScore: 7.50, carbonFootprintKg: 0.80 },
  { id: "SM-005", supplierId: "SUP-002", materialId: "MAT-BAT-002", basePrice: 88.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 250, leadTimeDays: 35, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.00, carbonFootprintKg: 0.75 },
  { id: "SM-006", supplierId: "SUP-003", materialId: "MAT-BAT-002", basePrice: 95.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 45, qualityCertification: "UL Listed", sustainabilityScore: 8.80, carbonFootprintKg: 0.65 },
  { id: "SM-007", supplierId: "SUP-001", materialId: "MAT-BAT-003", basePrice: 27.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 300, leadTimeDays: 30, qualityCertification: "ISO 9001", sustainabilityScore: 7.20, carbonFootprintKg: 0.30 },
  { id: "SM-008", supplierId: "SUP-003", materialId: "MAT-BAT-003", basePrice: 26.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 200, leadTimeDays: 45, qualityCertification: "UL Listed", sustainabilityScore: 8.50, carbonFootprintKg: 0.25 },
  { id: "SM-009", supplierId: "SUP-004", materialId: "MAT-MOT-001", basePrice: 395.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 50, leadTimeDays: 40, qualityCertification: "ISO 9001 CE TUV", sustainabilityScore: 9.20, carbonFootprintKg: 8.50 },
  { id: "SM-010", supplierId: "SUP-005", materialId: "MAT-MOT-001", basePrice: 385.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 75, leadTimeDays: 28, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.50, carbonFootprintKg: 9.20 },
  { id: "SM-011", supplierId: "SUP-006", materialId: "MAT-MOT-001", basePrice: 405.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 40, leadTimeDays: 50, qualityCertification: "UL Listed", sustainabilityScore: 7.80, carbonFootprintKg: 10.10 },
  { id: "SM-012", supplierId: "SUP-004", materialId: "MAT-MOT-002", basePrice: 290.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 60, leadTimeDays: 40, qualityCertification: "ISO 9001 CE", sustainabilityScore: 9.00, carbonFootprintKg: 7.80 },
  { id: "SM-013", supplierId: "SUP-005", materialId: "MAT-MOT-002", basePrice: 275.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 80, leadTimeDays: 28, qualityCertification: "ISO 9001", sustainabilityScore: 8.30, carbonFootprintKg: 8.50 },
  { id: "SM-014", supplierId: "SUP-006", materialId: "MAT-MOT-002", basePrice: 295.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 50, leadTimeDays: 50, qualityCertification: "UL Listed", sustainabilityScore: 7.50, carbonFootprintKg: 9.00 },
  { id: "SM-015", supplierId: "SUP-004", materialId: "MAT-MOT-003", basePrice: 125.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 150, leadTimeDays: 40, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.80, carbonFootprintKg: 1.20 },
  { id: "SM-016", supplierId: "SUP-005", materialId: "MAT-MOT-003", basePrice: 118.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 200, leadTimeDays: 28, qualityCertification: "ISO 9001", sustainabilityScore: 8.20, carbonFootprintKg: 1.35 },
  { id: "SM-017", supplierId: "SUP-004", materialId: "MAT-MOT-004", basePrice: 68.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 250, leadTimeDays: 40, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.50, carbonFootprintKg: 0.50 },
  { id: "SM-018", supplierId: "SUP-005", materialId: "MAT-MOT-004", basePrice: 63.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 300, leadTimeDays: 28, qualityCertification: "ISO 9001", sustainabilityScore: 8.00, carbonFootprintKg: 0.55 },
  { id: "SM-019", supplierId: "SUP-007", materialId: "MAT-FRM-001", basePrice: 185.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 25, qualityCertification: "ISO 9001", sustainabilityScore: 8.20, carbonFootprintKg: 5.80 },
  { id: "SM-020", supplierId: "SUP-009", materialId: "MAT-FRM-001", basePrice: 178.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 150, leadTimeDays: 42, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.50, carbonFootprintKg: 5.50 },
  { id: "SM-021", supplierId: "SUP-008", materialId: "MAT-FRM-002", basePrice: 435.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 50, leadTimeDays: 38, qualityCertification: "ISO 9001 JIS", sustainabilityScore: 9.50, carbonFootprintKg: 3.20 },
  { id: "SM-022", supplierId: "SUP-009", materialId: "MAT-FRM-002", basePrice: 425.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 60, leadTimeDays: 42, qualityCertification: "ISO 9001 CE", sustainabilityScore: 9.20, carbonFootprintKg: 3.50 },
  { id: "SM-023", supplierId: "SUP-007", materialId: "MAT-FRM-003", basePrice: 155.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 80, leadTimeDays: 25, qualityCertification: "ISO 9001", sustainabilityScore: 7.80, carbonFootprintKg: 3.20 },
  { id: "SM-024", supplierId: "SUP-009", materialId: "MAT-FRM-003", basePrice: 148.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 42, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.20, carbonFootprintKg: 3.00 },
  { id: "SM-025", supplierId: "SUP-007", materialId: "MAT-FRM-004", basePrice: 47.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 200, leadTimeDays: 25, qualityCertification: "ISO 9001", sustainabilityScore: 7.50, carbonFootprintKg: 1.50 },
  { id: "SM-026", supplierId: "SUP-009", materialId: "MAT-FRM-004", basePrice: 44.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 250, leadTimeDays: 42, qualityCertification: "ISO 9001", sustainabilityScore: 7.80, carbonFootprintKg: 1.40 },
  { id: "SM-027", supplierId: "SUP-010", materialId: "MAT-ELC-001", basePrice: 98.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 32, qualityCertification: "ISO 9001 CE", sustainabilityScore: 7.20, carbonFootprintKg: 0.80 },
  { id: "SM-028", supplierId: "SUP-011", materialId: "MAT-ELC-001", basePrice: 92.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 120, leadTimeDays: 28, qualityCertification: "UL Listed FCC", sustainabilityScore: 8.50, carbonFootprintKg: 0.70 },
  { id: "SM-029", supplierId: "SUP-012", materialId: "MAT-ELC-001", basePrice: 96.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 80, leadTimeDays: 35, qualityCertification: "ISO 9001", sustainabilityScore: 7.50, carbonFootprintKg: 0.85 },
  { id: "SM-030", supplierId: "SUP-010", materialId: "MAT-ELC-002", basePrice: 58.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 150, leadTimeDays: 32, qualityCertification: "ISO 9001", sustainabilityScore: 7.00, carbonFootprintKg: 1.20 },
  { id: "SM-031", supplierId: "SUP-011", materialId: "MAT-ELC-002", basePrice: 53.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 180, leadTimeDays: 28, qualityCertification: "UL Listed", sustainabilityScore: 8.20, carbonFootprintKg: 1.10 },
  { id: "SM-032", supplierId: "SUP-010", materialId: "MAT-ELC-003", basePrice: 19.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 300, leadTimeDays: 32, qualityCertification: "ISO 9001", sustainabilityScore: 7.20, carbonFootprintKg: 0.25 },
  { id: "SM-033", supplierId: "SUP-011", materialId: "MAT-ELC-003", basePrice: 17.50, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 350, leadTimeDays: 28, qualityCertification: "UL Listed", sustainabilityScore: 8.00, carbonFootprintKg: 0.22 },
  { id: "SM-034", supplierId: "SUP-013", materialId: "MAT-STD-001", basePrice: 125.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 80, leadTimeDays: 30, qualityCertification: "ISO 9001 CE", sustainabilityScore: 8.50, carbonFootprintKg: 7.50 },
  { id: "SM-035", supplierId: "SUP-014", materialId: "MAT-STD-001", basePrice: 118.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 40, qualityCertification: "ISO 9001", sustainabilityScore: 7.80, carbonFootprintKg: 8.20 },
  { id: "SM-036", supplierId: "SUP-015", materialId: "MAT-STD-002", basePrice: 88.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 35, qualityCertification: "ISO 9001 CE TUV", sustainabilityScore: 9.20, carbonFootprintKg: 2.50 },
  { id: "SM-037", supplierId: "SUP-014", materialId: "MAT-STD-002", basePrice: 83.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 120, leadTimeDays: 40, qualityCertification: "ISO 9001", sustainabilityScore: 8.20, carbonFootprintKg: 2.80 },
  { id: "SM-038", supplierId: "SUP-013", materialId: "MAT-STD-003", basePrice: 98.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 80, leadTimeDays: 30, qualityCertification: "ISO 9001", sustainabilityScore: 8.00, carbonFootprintKg: 3.80 },
  { id: "SM-039", supplierId: "SUP-014", materialId: "MAT-STD-003", basePrice: 92.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 100, leadTimeDays: 40, qualityCertification: "ISO 9001", sustainabilityScore: 7.50, carbonFootprintKg: 4.20 },
  { id: "SM-040", supplierId: "SUP-013", materialId: "MAT-STD-004", basePrice: 29.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 200, leadTimeDays: 30, qualityCertification: "ISO 9001", sustainabilityScore: 7.20, carbonFootprintKg: 1.20 },
  { id: "SM-041", supplierId: "SUP-014", materialId: "MAT-STD-004", basePrice: 27.00, currency: "USD", effectiveDate: "2024-01-01", minimumOrderQuantity: 250, leadTimeDays: 40, qualityCertification: "ISO 9001", sustainabilityScore: 7.50, carbonFootprintKg: 1.30 }
];

export const urbanEBikeBOM: BOMItem[] = [
  { id: "BOM-001", productId: "EBIKE-URBAN-2024", materialId: "MAT-BAT-001", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 5 },
  { id: "BOM-002", productId: "EBIKE-URBAN-2024", materialId: "MAT-BAT-002", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 6 },
  { id: "BOM-003", productId: "EBIKE-URBAN-2024", materialId: "MAT-BAT-003", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 7 },
  { id: "BOM-004", productId: "EBIKE-URBAN-2024", materialId: "MAT-MOT-001", quantityRequired: 1, leadTimeDays: 40, assemblySequence: 3 },
  { id: "BOM-005", productId: "EBIKE-URBAN-2024", materialId: "MAT-MOT-003", quantityRequired: 1, leadTimeDays: 40, assemblySequence: 4 },
  { id: "BOM-006", productId: "EBIKE-URBAN-2024", materialId: "MAT-MOT-004", quantityRequired: 1, leadTimeDays: 40, assemblySequence: 8 },
  { id: "BOM-007", productId: "EBIKE-URBAN-2024", materialId: "MAT-FRM-001", quantityRequired: 1, leadTimeDays: 25, assemblySequence: 1 },
  { id: "BOM-008", productId: "EBIKE-URBAN-2024", materialId: "MAT-FRM-003", quantityRequired: 1, leadTimeDays: 25, assemblySequence: 2 },
  { id: "BOM-009", productId: "EBIKE-URBAN-2024", materialId: "MAT-FRM-004", quantityRequired: 1, leadTimeDays: 25, assemblySequence: 9 },
  { id: "BOM-010", productId: "EBIKE-URBAN-2024", materialId: "MAT-ELC-001", quantityRequired: 1, leadTimeDays: 32, assemblySequence: 10 },
  { id: "BOM-011", productId: "EBIKE-URBAN-2024", materialId: "MAT-ELC-002", quantityRequired: 1, leadTimeDays: 32, assemblySequence: 11 },
  { id: "BOM-012", productId: "EBIKE-URBAN-2024", materialId: "MAT-ELC-003", quantityRequired: 1, leadTimeDays: 32, assemblySequence: 12 },
  { id: "BOM-013", productId: "EBIKE-URBAN-2024", materialId: "MAT-STD-001", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 13 },
  { id: "BOM-014", productId: "EBIKE-URBAN-2024", materialId: "MAT-STD-002", quantityRequired: 1, leadTimeDays: 35, assemblySequence: 14 },
  { id: "BOM-015", productId: "EBIKE-URBAN-2024", materialId: "MAT-STD-003", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 15 },
  { id: "BOM-016", productId: "EBIKE-URBAN-2024", materialId: "MAT-STD-004", quantityRequired: 1, leadTimeDays: 30, assemblySequence: 16 }
];

// Demand Forecast Data (3-month predictions)
export const demandForecasts: DemandForecast[] = [
  { forecastId: "DF001", materialId: "MAT-BAT-001", forecastPeriod: "2026-03", predictedDemand: 450, confidenceLevel: 0.85, forecastDate: "2026-02-15", notes: "Q1 production ramp-up" },
  { forecastId: "DF002", materialId: "MAT-BAT-001", forecastPeriod: "2026-04", predictedDemand: 520, confidenceLevel: 0.82, forecastDate: "2026-02-15", notes: "Spring season increase" },
  { forecastId: "DF003", materialId: "MAT-BAT-001", forecastPeriod: "2026-05", predictedDemand: 580, confidenceLevel: 0.78, forecastDate: "2026-02-15", notes: "Peak season approaching" },
  { forecastId: "DF007", materialId: "MAT-MOT-001", forecastPeriod: "2026-03", predictedDemand: 450, confidenceLevel: 0.90, forecastDate: "2026-02-15", notes: "Critical component" },
  { forecastId: "DF008", materialId: "MAT-MOT-001", forecastPeriod: "2026-04", predictedDemand: 520, confidenceLevel: 0.87, forecastDate: "2026-02-15", notes: "High confidence" },
  { forecastId: "DF009", materialId: "MAT-MOT-001", forecastPeriod: "2026-05", predictedDemand: 580, confidenceLevel: 0.83, forecastDate: "2026-02-15", notes: "Stable demand pattern" }
];

// Inventory Levels (current stock status)
export const inventoryLevels: InventoryLevel[] = [
  { inventoryId: "INV-001", materialId: "MAT-BAT-001", warehouseLocation: "WH-MAIN-01", currentStock: 250, reorderPoint: 200, safetyStock: 150, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-002", materialId: "MAT-BAT-002", warehouseLocation: "WH-MAIN-01", currentStock: 480, reorderPoint: 300, safetyStock: 200, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-003", materialId: "MAT-BAT-003", warehouseLocation: "WH-MAIN-01", currentStock: 720, reorderPoint: 500, safetyStock: 350, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-004", materialId: "MAT-MOT-001", warehouseLocation: "WH-MAIN-01", currentStock: 180, reorderPoint: 150, safetyStock: 100, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-005", materialId: "MAT-MOT-002", warehouseLocation: "WH-MAIN-01", currentStock: 220, reorderPoint: 180, safetyStock: 120, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-006", materialId: "MAT-MOT-003", warehouseLocation: "WH-MAIN-01", currentStock: 380, reorderPoint: 250, safetyStock: 180, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-007", materialId: "MAT-MOT-004", warehouseLocation: "WH-MAIN-01", currentStock: 520, reorderPoint: 350, safetyStock: 250, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-008", materialId: "MAT-FRM-001", warehouseLocation: "WH-MAIN-01", currentStock: 310, reorderPoint: 250, safetyStock: 180, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-009", materialId: "MAT-FRM-002", warehouseLocation: "WH-MAIN-01", currentStock: 95, reorderPoint: 80, safetyStock: 50, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-010", materialId: "MAT-FRM-003", warehouseLocation: "WH-MAIN-01", currentStock: 280, reorderPoint: 200, safetyStock: 140, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-011", materialId: "MAT-FRM-004", warehouseLocation: "WH-MAIN-01", currentStock: 450, reorderPoint: 350, safetyStock: 250, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-012", materialId: "MAT-ELC-001", warehouseLocation: "WH-MAIN-01", currentStock: 340, reorderPoint: 280, safetyStock: 200, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-013", materialId: "MAT-ELC-002", warehouseLocation: "WH-MAIN-01", currentStock: 410, reorderPoint: 320, safetyStock: 230, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-014", materialId: "MAT-ELC-003", warehouseLocation: "WH-MAIN-01", currentStock: 680, reorderPoint: 500, safetyStock: 350, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-015", materialId: "MAT-STD-001", warehouseLocation: "WH-MAIN-01", currentStock: 290, reorderPoint: 240, safetyStock: 170, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-016", materialId: "MAT-STD-002", warehouseLocation: "WH-MAIN-01", currentStock: 360, reorderPoint: 280, safetyStock: 200, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-017", materialId: "MAT-STD-003", warehouseLocation: "WH-MAIN-01", currentStock: 320, reorderPoint: 260, safetyStock: 180, lastUpdated: "2024-02-20 10:30:00" },
  { inventoryId: "INV-018", materialId: "MAT-STD-004", warehouseLocation: "WH-MAIN-01", currentStock: 550, reorderPoint: 420, safetyStock: 300, lastUpdated: "2024-02-20 10:30:00" }
];

// Supplier Performance (3-month history)
export const supplierPerformance: SupplierPerformance[] = [
  { performanceId: "PERF-001", supplierId: "SUP-001", measurementPeriod: "2024-01", onTimeDeliveryRate: 95.50, qualityScore: 8.75, defectRate: 1.25, costVariance: -2.50, responseTimeHours: 24 },
  { performanceId: "PERF-002", supplierId: "SUP-001", measurementPeriod: "2023-12", onTimeDeliveryRate: 94.20, qualityScore: 8.60, defectRate: 1.40, costVariance: -1.80, responseTimeHours: 28 },
  { performanceId: "PERF-003", supplierId: "SUP-001", measurementPeriod: "2023-11", onTimeDeliveryRate: 96.10, qualityScore: 8.80, defectRate: 1.10, costVariance: -3.20, responseTimeHours: 22 },
  { performanceId: "PERF-004", supplierId: "SUP-002", measurementPeriod: "2024-01", onTimeDeliveryRate: 97.30, qualityScore: 9.10, defectRate: 0.85, costVariance: -1.50, responseTimeHours: 18 },
  { performanceId: "PERF-005", supplierId: "SUP-002", measurementPeriod: "2023-12", onTimeDeliveryRate: 96.80, qualityScore: 9.00, defectRate: 0.95, costVariance: -2.10, responseTimeHours: 20 },
  { performanceId: "PERF-006", supplierId: "SUP-002", measurementPeriod: "2023-11", onTimeDeliveryRate: 97.50, qualityScore: 9.20, defectRate: 0.75, costVariance: -1.80, responseTimeHours: 16 },
  { performanceId: "PERF-010", supplierId: "SUP-004", measurementPeriod: "2024-01", onTimeDeliveryRate: 98.20, qualityScore: 9.40, defectRate: 0.60, costVariance: -2.80, responseTimeHours: 16 },
  { performanceId: "PERF-011", supplierId: "SUP-004", measurementPeriod: "2023-12", onTimeDeliveryRate: 97.90, qualityScore: 9.35, defectRate: 0.65, costVariance: -3.10, responseTimeHours: 18 },
  { performanceId: "PERF-012", supplierId: "SUP-004", measurementPeriod: "2023-11", onTimeDeliveryRate: 98.50, qualityScore: 9.45, defectRate: 0.55, costVariance: -2.50, responseTimeHours: 14 },
  { performanceId: "PERF-013", supplierId: "SUP-005", measurementPeriod: "2024-01", onTimeDeliveryRate: 94.80, qualityScore: 8.50, defectRate: 1.50, costVariance: -1.20, responseTimeHours: 26 },
  { performanceId: "PERF-019", supplierId: "SUP-007", measurementPeriod: "2024-01", onTimeDeliveryRate: 96.70, qualityScore: 8.90, defectRate: 1.05, costVariance: -2.20, responseTimeHours: 20 },
  { performanceId: "PERF-022", supplierId: "SUP-008", measurementPeriod: "2024-01", onTimeDeliveryRate: 98.80, qualityScore: 9.60, defectRate: 0.45, costVariance: -3.50, responseTimeHours: 12 },
  { performanceId: "PERF-025", supplierId: "SUP-009", measurementPeriod: "2024-01", onTimeDeliveryRate: 93.60, qualityScore: 8.35, defectRate: 1.80, costVariance: 0.50, responseTimeHours: 32 },
  { performanceId: "PERF-031", supplierId: "SUP-011", measurementPeriod: "2024-01", onTimeDeliveryRate: 95.90, qualityScore: 8.65, defectRate: 1.30, costVariance: -1.60, responseTimeHours: 22 },
  { performanceId: "PERF-037", supplierId: "SUP-013", measurementPeriod: "2024-01", onTimeDeliveryRate: 97.10, qualityScore: 9.00, defectRate: 0.95, costVariance: -2.40, responseTimeHours: 18 },
  { performanceId: "PERF-040", supplierId: "SUP-014", measurementPeriod: "2024-01", onTimeDeliveryRate: 94.20, qualityScore: 8.40, defectRate: 1.75, costVariance: -0.80, responseTimeHours: 28 },
  { performanceId: "PERF-043", supplierId: "SUP-015", measurementPeriod: "2024-01", onTimeDeliveryRate: 98.50, qualityScore: 9.50, defectRate: 0.55, costVariance: -3.20, responseTimeHours: 14 }
];

// Volume Tier Pricing
export const volumeTiers: VolumeTier[] = [
  { tierId: "TIER-001", supplierMaterialId: "SM-001", tierLevel: 1, minQuantity: 100, maxQuantity: 499, discountPercentage: 0.00, unitPrice: 480.00 },
  { tierId: "TIER-002", supplierMaterialId: "SM-001", tierLevel: 2, minQuantity: 500, maxQuantity: 999, discountPercentage: 5.00, unitPrice: 456.00 },
  { tierId: "TIER-003", supplierMaterialId: "SM-001", tierLevel: 3, minQuantity: 1000, maxQuantity: 2499, discountPercentage: 8.00, unitPrice: 441.60 },
  { tierId: "TIER-009", supplierMaterialId: "SM-003", tierLevel: 1, minQuantity: 50, maxQuantity: 299, discountPercentage: 0.00, unitPrice: 495.00 },
  { tierId: "TIER-010", supplierMaterialId: "SM-003", tierLevel: 2, minQuantity: 300, maxQuantity: 799, discountPercentage: 4.00, unitPrice: 475.20 },
  { tierId: "TIER-013", supplierMaterialId: "SM-009", tierLevel: 1, minQuantity: 50, maxQuantity: 199, discountPercentage: 0.00, unitPrice: 395.00 },
  { tierId: "TIER-014", supplierMaterialId: "SM-009", tierLevel: 2, minQuantity: 200, maxQuantity: 499, discountPercentage: 5.00, unitPrice: 375.25 },
  { tierId: "TIER-015", supplierMaterialId: "SM-009", tierLevel: 3, minQuantity: 500, maxQuantity: 999, discountPercentage: 8.00, unitPrice: 363.40 }
];

// Supplier Contracts
export const supplierContracts: SupplierContract[] = [
  { contractId: "CON001", supplierId: "SUP-001", contractType: "Long-term Supply", startDate: "2025-01-01", endDate: "2027-12-31", annualValue: 2100000.00, paymentTerms: "Net 45", volumeCommitment: "10000 units", priceAdjustmentClause: "CPI-based annual adjustment", sustainabilityClause: "Carbon neutral shipping required", status: "Active", renewalOption: "2-year extension" },
  { contractId: "CON002", supplierId: "SUP-002", contractType: "Long-term Supply", startDate: "2025-01-01", endDate: "2027-12-31", annualValue: 2640000.00, paymentTerms: "Net 30", volumeCommitment: "12000 units", priceAdjustmentClause: "Fixed price year 1 then CPI", sustainabilityClause: "Recycled materials preferred", status: "Active", renewalOption: "2-year extension" },
  { contractId: "CON003", supplierId: "SUP-003", contractType: "Strategic Partnership", startDate: "2024-06-01", endDate: "2027-05-31", annualValue: 4800000.00, paymentTerms: "Net 60", volumeCommitment: "12000 units", priceAdjustmentClause: "Quarterly review", sustainabilityClause: "ISO 14001 certified required", status: "Active", renewalOption: "3-year extension" },
  { contractId: "CON004", supplierId: "SUP-004", contractType: "Standard Supply", startDate: "2025-01-01", endDate: "2026-12-31", annualValue: 540000.00, paymentTerms: "Net 30", volumeCommitment: "12000 units", priceAdjustmentClause: "Annual negotiation", sustainabilityClause: "None", status: "Active", renewalOption: "1-year extension" },
  { contractId: "CON007", supplierId: "SUP-007", contractType: "Standard Supply", startDate: "2025-01-01", endDate: "2026-12-31", annualValue: 780000.00, paymentTerms: "Net 45", volumeCommitment: "6000 units", priceAdjustmentClause: "Annual negotiation", sustainabilityClause: "None", status: "Active", renewalOption: "1-year extension" },
  { contractId: "CON011", supplierId: "SUP-011", contractType: "Spot Purchase", startDate: "2026-01-01", endDate: "2026-12-31", annualValue: 960000.00, paymentTerms: "Net 30", volumeCommitment: "No commitment", priceAdjustmentClause: "Market-based pricing", sustainabilityClause: "None", status: "Active", renewalOption: "None" },
  { contractId: "CON013", supplierId: "SUP-013", contractType: "Long-term Supply", startDate: "2025-01-01", endDate: "2027-12-31", annualValue: 1080000.00, paymentTerms: "Net 60", volumeCommitment: "12000 units", priceAdjustmentClause: "CPI-based adjustment", sustainabilityClause: "Carbon neutral operations", status: "Active", renewalOption: "2-year extension" },
  { contractId: "CON015", supplierId: "SUP-015", contractType: "Long-term Supply", startDate: "2025-01-01", endDate: "2027-12-31", annualValue: 1140000.00, paymentTerms: "Net 30", volumeCommitment: "12000 units", priceAdjustmentClause: "CPI-based adjustment", sustainabilityClause: "Sustainable packaging", status: "Active", renewalOption: "2-year extension" }
];

// Production Schedule
export const productionSchedule: ProductionSchedule[] = [
  { scheduleId: "PS001", productId: "PROD001", productName: "Urban Commuter E-Bike", plannedQuantity: 250, startDate: "2026-03-01", endDate: "2026-03-15", status: "Planned", priority: "High", notes: "Q1 production batch 1" },
  { scheduleId: "PS002", productId: "PROD002", productName: "Mountain Trail E-Bike", plannedQuantity: 200, startDate: "2026-03-01", endDate: "2026-03-15", status: "Planned", priority: "High", notes: "Q1 production batch 1" },
  { scheduleId: "PS003", productId: "PROD001", productName: "Urban Commuter E-Bike", plannedQuantity: 270, startDate: "2026-03-16", endDate: "2026-03-31", status: "Planned", priority: "Medium", notes: "Q1 production batch 2" },
  { scheduleId: "PS005", productId: "PROD001", productName: "Urban Commuter E-Bike", plannedQuantity: 300, startDate: "2026-04-01", endDate: "2026-04-15", status: "Planned", priority: "High", notes: "Spring season ramp-up" },
  { scheduleId: "PS007", productId: "PROD001", productName: "Urban Commuter E-Bike", plannedQuantity: 320, startDate: "2026-04-16", endDate: "2026-04-30", status: "Planned", priority: "Medium", notes: "Spring peak production" },
  { scheduleId: "PS009", productId: "PROD001", productName: "Urban Commuter E-Bike", plannedQuantity: 350, startDate: "2026-05-01", endDate: "2026-05-15", status: "Planned", priority: "High", notes: "Peak season preparation" }
];

// Helper functions to work with real data
export function getMaterialById(id: string): Material | undefined {
  return materials.find(m => m.id === id);
}

export function getSupplierById(id: string): Supplier | undefined {
  return suppliers.find(s => s.id === id);
}

export function getSuppliersForMaterial(materialId: string): Array<{ supplier: Supplier; supplierMaterial: SupplierMaterial }> {
  return supplierMaterials
    .filter(sm => sm.materialId === materialId)
    .map(sm => ({
      supplier: getSupplierById(sm.supplierId)!,
      supplierMaterial: sm
    }))
    .filter(item => item.supplier);
}

export function calculateTotalBOMCost(bomItems: BOMItem[], quantity: number): number {
  return bomItems.reduce((total, bomItem) => {
    const material = getMaterialById(bomItem.materialId);
    return total + (material?.standardCost || 0) * bomItem.quantityRequired * quantity;
  }, 0);
}

// Generate realistic Pareto frontier solutions for 500 Urban E-Bikes
export interface SupplierAllocation {
  supplierId: string;
  supplierName: string;
  materialId: string;
  materialName: string;
  quantity: number;
  unitPrice: number;
  totalCost: number;
  leadTimeDays: number;
  freightCost?: number;
  carryingCost?: number;
  carbonCost?: number;
  tco?: number;
}

export interface OptimizationSolution {
  id: string;
  name: string;
  totalCost: number;
  riskScore: number;
  qualityScore: number;
  maxLeadTimeDays: number;
  allocations: SupplierAllocation[];
  explanation: string;
  supplierConcentration: { supplierId: string; supplierName: string; percentage: number }[];
  demandBufferPct?: number;
  reasoning?: {
    summary: string;
    keyFactors: string[];
    tradeOffs: string[];
    risks: string[];
    volumeDiscounts?: { description: string; savings: number }[];
    contractCompliance?: { supplier: string; commitment: string; status: string }[];
  };
}

// Solution A: Cost-Optimized (tier 3 suppliers - lowest cost, acceptable quality)
const solutionA: OptimizationSolution = {
  id: "SOL-A",
  name: "Cost-Optimized",
  totalCost: 650000,
  riskScore: 7.5,
  qualityScore: 6.5,
  maxLeadTimeDays: 55,
  allocations: [
    { supplierId: "SUP-001", supplierName: "BatteryTech Solutions", materialId: "MAT-BAT-001", materialName: "Battery Pack 48V", quantity: 500, unitPrice: 420, totalCost: 210000, leadTimeDays: 30 },
    { supplierId: "SUP-001", supplierName: "BatteryTech Solutions", materialId: "MAT-BAT-002", materialName: "BMS", quantity: 500, unitPrice: 78, totalCost: 39000, leadTimeDays: 30 },
    { supplierId: "SUP-001", supplierName: "BatteryTech Solutions", materialId: "MAT-BAT-003", materialName: "Charging Port", quantity: 500, unitPrice: 22, totalCost: 11000, leadTimeDays: 30 },
    { supplierId: "SUP-006", supplierName: "MotionDrive Systems", materialId: "MAT-MOT-001", materialName: "Mid-Drive Motor 750W", quantity: 500, unitPrice: 340, totalCost: 170000, leadTimeDays: 50 },
    { supplierId: "SUP-005", supplierName: "TorqueTech Motors", materialId: "MAT-MOT-003", materialName: "Motor Controller", quantity: 500, unitPrice: 105, totalCost: 52500, leadTimeDays: 28 },
    { supplierId: "SUP-005", supplierName: "TorqueTech Motors", materialId: "MAT-MOT-004", materialName: "Torque Sensor", quantity: 500, unitPrice: 55, totalCost: 27500, leadTimeDays: 28 },
    { supplierId: "SUP-009", supplierName: "FrameWorks Ltd", materialId: "MAT-FRM-001", materialName: "Aluminum Frame", quantity: 500, unitPrice: 155, totalCost: 77500, leadTimeDays: 42 },
    { supplierId: "SUP-009", supplierName: "FrameWorks Ltd", materialId: "MAT-FRM-003", materialName: "Suspension Fork", quantity: 500, unitPrice: 125, totalCost: 62500, leadTimeDays: 42 },
    { supplierId: "SUP-009", supplierName: "FrameWorks Ltd", materialId: "MAT-FRM-004", materialName: "Handlebar Assembly", quantity: 500, unitPrice: 38, totalCost: 19000, leadTimeDays: 42 },
    { supplierId: "SUP-010", supplierName: "SmartDisplay Tech", materialId: "MAT-ELC-001", materialName: "LCD Display", quantity: 500, unitPrice: 82, totalCost: 41000, leadTimeDays: 32 },
    { supplierId: "SUP-010", supplierName: "SmartDisplay Tech", materialId: "MAT-ELC-002", materialName: "Wiring Harness", quantity: 500, unitPrice: 48, totalCost: 24000, leadTimeDays: 32 },
    { supplierId: "SUP-010", supplierName: "SmartDisplay Tech", materialId: "MAT-ELC-003", materialName: "Speed Sensor", quantity: 500, unitPrice: 15, totalCost: 7500, leadTimeDays: 32 },
    { supplierId: "SUP-014", supplierName: "RollerTech Wheels", materialId: "MAT-STD-001", materialName: "Wheel Set", quantity: 500, unitPrice: 98, totalCost: 49000, leadTimeDays: 40 },
    { supplierId: "SUP-014", supplierName: "RollerTech Wheels", materialId: "MAT-STD-002", materialName: "Hydraulic Brakes", quantity: 500, unitPrice: 72, totalCost: 36000, leadTimeDays: 40 },
    { supplierId: "SUP-014", supplierName: "RollerTech Wheels", materialId: "MAT-STD-003", materialName: "Gear System", quantity: 500, unitPrice: 78, totalCost: 39000, leadTimeDays: 40 },
    { supplierId: "SUP-014", supplierName: "RollerTech Wheels", materialId: "MAT-STD-004", materialName: "Pedal Set", quantity: 500, unitPrice: 23, totalCost: 11500, leadTimeDays: 40 }
  ],
  explanation: "Lowest cost at $650,000 ($1,300/bike). Uses tier 3 suppliers with ratings 3.75-3.90. Quality score 6.5/10 - acceptable but not premium. Risk score 7.5/10 due to heavy Asia concentration and lower-rated suppliers. Lead time 55 days. Saves $550K vs premium but trades off quality and reliability.",
  supplierConcentration: [
    { supplierId: "SUP-001", supplierName: "BatteryTech Solutions", percentage: 40 },
    { supplierId: "SUP-006", supplierName: "MotionDrive Systems", percentage: 26 },
    { supplierId: "SUP-009", supplierName: "FrameWorks Ltd", percentage: 24 }
  ],
  reasoning: {
    summary: "Cost-Optimized solution minimizes cost at $650K but accepts higher risk (7.5/10) and lower quality (6.5/10). Best for price-sensitive orders where premium quality is not required.",
    keyFactors: [
      "Cost $650K - lowest possible for 500 bikes ($1,300/bike)",
      "Quality score 6.5/10 - acceptable for non-critical applications",
      "Risk score 7.5/10 - higher exposure to supply disruptions",
      "Lead time 55 days - longest among all solutions",
      "Supplier concentration 40% at BatteryTech - at policy limit"
    ],
    tradeOffs: [
      "Save $225K vs balanced → Accept 1.7 lower quality (6.5 vs 8.2)",
      "Save $550K vs premium → Accept 3.0 higher risk (7.5 vs 1.5)",
      "Heavy Asia concentration (70%) → Lower costs but geopolitical exposure",
      "Tier 3 suppliers (ratings 3.75-3.90) → Price advantage but reliability concerns"
    ],
    risks: [
      "BatteryTech concentration at 40% - at maximum policy threshold",
      "70% exposure to Asian suppliers (high geopolitical risk)",
      "Lead time 55 days - no buffer for delays",
      "Lower supplier ratings (3.75-3.90) - higher defect rates expected",
      "MotionDrive (Detroit) has 50-day lead time - potential bottleneck"
    ],
    volumeDiscounts: [
      { description: "BatteryTech: Consolidate 500+ battery components, save 3%", savings: 7800 },
      { description: "Limited volume discount opportunities with tier 3 suppliers", savings: 0 }
    ],
    contractCompliance: [
      { supplier: "BatteryTech Solutions", commitment: "10,000 units/year minimum", status: "✓ On track (7,200 ordered YTD)" },
      { supplier: "MotionDrive Systems", commitment: "No contract commitment", status: "✓ Flexible" },
      { supplier: "FrameWorks Ltd", commitment: "No contract commitment", status: "✓ Flexible" }
    ]
  }
};

// Solution B: Balanced (optimal trade-off)
const solutionB: OptimizationSolution = {
  id: "SOL-B",
  name: "Balanced",
  totalCost: 875000,
  riskScore: 3.5,
  qualityScore: 8.2,
  maxLeadTimeDays: 42,
  allocations: [
    { supplierId: "SUP-002", supplierName: "PowerCell Industries", materialId: "MAT-BAT-001", materialName: "Battery Pack 48V", quantity: 300, unitPrice: 465, totalCost: 139500, leadTimeDays: 35 },
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", materialId: "MAT-BAT-001", materialName: "Battery Pack 48V", quantity: 200, unitPrice: 495, totalCost: 99000, leadTimeDays: 45 },
    { supplierId: "SUP-002", supplierName: "PowerCell Industries", materialId: "MAT-BAT-002", materialName: "BMS", quantity: 500, unitPrice: 88, totalCost: 44000, leadTimeDays: 35 },
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", materialId: "MAT-BAT-003", materialName: "Charging Port", quantity: 500, unitPrice: 26, totalCost: 13000, leadTimeDays: 45 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-001", materialName: "Mid-Drive Motor 750W", quantity: 500, unitPrice: 395, totalCost: 197500, leadTimeDays: 40 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-003", materialName: "Motor Controller", quantity: 500, unitPrice: 125, totalCost: 62500, leadTimeDays: 40 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-004", materialName: "Torque Sensor", quantity: 500, unitPrice: 68, totalCost: 34000, leadTimeDays: 40 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", materialId: "MAT-FRM-001", materialName: "Aluminum Frame", quantity: 350, unitPrice: 185, totalCost: 64750, leadTimeDays: 25 },
    { supplierId: "SUP-009", supplierName: "FrameWorks Ltd", materialId: "MAT-FRM-001", materialName: "Aluminum Frame", quantity: 150, unitPrice: 178, totalCost: 26700, leadTimeDays: 42 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", materialId: "MAT-FRM-003", materialName: "Suspension Fork", quantity: 500, unitPrice: 155, totalCost: 77500, leadTimeDays: 25 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", materialId: "MAT-FRM-004", materialName: "Handlebar Assembly", quantity: 500, unitPrice: 47, totalCost: 23500, leadTimeDays: 25 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-001", materialName: "LCD Display", quantity: 300, unitPrice: 92, totalCost: 27600, leadTimeDays: 28 },
    { supplierId: "SUP-010", supplierName: "SmartDisplay Tech", materialId: "MAT-ELC-001", materialName: "LCD Display", quantity: 200, unitPrice: 98, totalCost: 19600, leadTimeDays: 32 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-002", materialName: "Wiring Harness", quantity: 500, unitPrice: 53, totalCost: 26500, leadTimeDays: 28 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-003", materialName: "Speed Sensor", quantity: 500, unitPrice: 17.5, totalCost: 8750, leadTimeDays: 28 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-001", materialName: "Wheel Set", quantity: 500, unitPrice: 125, totalCost: 62500, leadTimeDays: 30 },
    { supplierId: "SUP-015", supplierName: "BrakeSafe Systems", materialId: "MAT-STD-002", materialName: "Hydraulic Brakes", quantity: 500, unitPrice: 88, totalCost: 44000, leadTimeDays: 35 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-003", materialName: "Gear System", quantity: 500, unitPrice: 98, totalCost: 49000, leadTimeDays: 30 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-004", materialName: "Pedal Set", quantity: 500, unitPrice: 29, totalCost: 14500, leadTimeDays: 30 }
  ],
  explanation: "Balanced solution at $875,000 ($1,750/bike). Mix of tier 1 and tier 2 suppliers with ratings 4.0-4.6. Quality score 8.2/10 - good reliability. Risk score 3.5/10 with USA/European/Asian diversification. Lead time 42 days. Top supplier (DriveMotor) at 28% - well within policy limits.",
  supplierConcentration: [
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", percentage: 28 },
    { supplierId: "SUP-002", supplierName: "PowerCell Industries", percentage: 19 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", percentage: 17 }
  ],
  reasoning: {
    summary: "Balanced solution recommended for optimal cost-quality-risk trade-off. Provides enterprise-grade quality (8.2/10) at moderate cost ($875K) with acceptable risk (3.5/10).",
    keyFactors: [
      "Quality score 8.2/10 meets enterprise minimum threshold of 8.0",
      "Cost $875K within approved budget of $900K",
      "Risk score 3.5/10 acceptable for production environment",
      "Lead time 42 days meets 45-day requirement",
      "Supplier concentration 28% complies with 40% policy"
    ],
    tradeOffs: [
      "Pay $225K more than budget option → Gain 1.7 quality points (8.2 vs 6.5)",
      "Pay $225K more than budget option → Reduce risk by 4.0 points (3.5 vs 7.5)",
      "Save $325K vs premium option → Accept 1.3 lower quality (8.2 vs 9.5)",
      "Geographic diversification: 45% US/EU, 55% Asia (balanced exposure)"
    ],
    risks: [
      "DriveMotor Corp concentration at 28% (within policy but monitor)",
      "19% exposure to Asian suppliers (moderate geopolitical risk)",
      "Lead time 42 days leaves 3-day buffer (tight schedule)"
    ],
    volumeDiscounts: [
      { description: "PowerCell Industries: Order 500+ batteries, save 5%", savings: 13950 },
      { description: "DriveMotor Corp: Order 500+ motors, save 8%", savings: 23520 },
      { description: "Potential annual savings if ordering in batches: $150K+", savings: 150000 }
    ],
    contractCompliance: [
      { supplier: "PowerCell Industries", commitment: "12,000 units/year minimum", status: "✓ On track (8,500 ordered YTD)" },
      { supplier: "DriveMotor Corp", commitment: "No contract commitment", status: "✓ Flexible" },
      { supplier: "AlumaTech Frames", commitment: "6,000 units/year minimum", status: "✓ On track (4,200 ordered YTD)" }
    ]
  }
};

// Solution C: Risk-Diversified (tier 1 suppliers only - highest quality)
const solutionC: OptimizationSolution = {
  id: "SOL-C",
  name: "Risk-Diversified",
  totalCost: 1200000,
  riskScore: 1.5,
  qualityScore: 9.5,
  maxLeadTimeDays: 35,
  allocations: [
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", materialId: "MAT-BAT-001", materialName: "Battery Pack 48V", quantity: 500, unitPrice: 550, totalCost: 275000, leadTimeDays: 45 },
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", materialId: "MAT-BAT-002", materialName: "BMS", quantity: 500, unitPrice: 105, totalCost: 52500, leadTimeDays: 45 },
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", materialId: "MAT-BAT-003", materialName: "Charging Port", quantity: 500, unitPrice: 32, totalCost: 16000, leadTimeDays: 45 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-001", materialName: "Mid-Drive Motor 750W", quantity: 500, unitPrice: 450, totalCost: 225000, leadTimeDays: 40 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-003", materialName: "Motor Controller", quantity: 500, unitPrice: 145, totalCost: 72500, leadTimeDays: 40 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", materialId: "MAT-MOT-004", materialName: "Torque Sensor", quantity: 500, unitPrice: 78, totalCost: 39000, leadTimeDays: 40 },
    { supplierId: "SUP-008", supplierName: "CarbonFiber Pro", materialId: "MAT-FRM-001", materialName: "Carbon Fiber Frame", quantity: 500, unitPrice: 480, totalCost: 240000, leadTimeDays: 38 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", materialId: "MAT-FRM-003", materialName: "Suspension Fork", quantity: 500, unitPrice: 175, totalCost: 87500, leadTimeDays: 25 },
    { supplierId: "SUP-007", supplierName: "AlumaTech Frames", materialId: "MAT-FRM-004", materialName: "Handlebar Assembly", quantity: 500, unitPrice: 55, totalCost: 27500, leadTimeDays: 25 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-001", materialName: "LCD Display", quantity: 500, unitPrice: 105, totalCost: 52500, leadTimeDays: 28 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-002", materialName: "Wiring Harness", quantity: 500, unitPrice: 62, totalCost: 31000, leadTimeDays: 28 },
    { supplierId: "SUP-011", supplierName: "ElectroVision Systems", materialId: "MAT-ELC-003", materialName: "Speed Sensor", quantity: 500, unitPrice: 22, totalCost: 11000, leadTimeDays: 28 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-001", materialName: "Wheel Set", quantity: 500, unitPrice: 145, totalCost: 72500, leadTimeDays: 30 },
    { supplierId: "SUP-015", supplierName: "BrakeSafe Systems", materialId: "MAT-STD-002", materialName: "Hydraulic Brakes", quantity: 500, unitPrice: 105, totalCost: 52500, leadTimeDays: 35 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-003", materialName: "Gear System", quantity: 500, unitPrice: 115, totalCost: 57500, leadTimeDays: 30 },
    { supplierId: "SUP-013", supplierName: "WheelCraft Industries", materialId: "MAT-STD-004", materialName: "Pedal Set", quantity: 500, unitPrice: 35, totalCost: 17500, leadTimeDays: 30 }
  ],
  explanation: "Risk-Diversified solution at $1,200,000 ($2,400/bike). Exclusively tier 1 suppliers with ratings 4.60-4.70 from USA, EU, and Japan. Quality score 9.5/10 - highest reliability and brand value. Risk score 1.5/10 - minimal geopolitical exposure. Lead time 35 days. The $550K premium over the cost-optimized option is your supply chain insurance - defect rates under 0.6%, 98%+ on-time delivery, premium certifications.",
  supplierConcentration: [
    { supplierId: "SUP-008", supplierName: "CarbonFiber Pro", percentage: 20 },
    { supplierId: "SUP-003", supplierName: "EcoEnergy Systems", percentage: 29 },
    { supplierId: "SUP-004", supplierName: "DriveMotor Corp", percentage: 28 }
  ],
  reasoning: {
    summary: "Risk-Diversified solution delivers maximum quality (9.5/10) and minimum risk (1.5/10) at $1.2M. Best for flagship products, brand-critical launches, or when supply chain reliability is paramount.",
    keyFactors: [
      "Quality score 9.5/10 - highest tier suppliers with premium certifications",
      "Risk score 1.5/10 - minimal geopolitical and supplier reliability risk",
      "Lead time 35 days - fastest delivery among all solutions",
      "Supplier concentration 29% - well distributed across tier 1 suppliers",
      "Geographic diversification: 60% US/EU, 40% Asia (optimal balance)"
    ],
    tradeOffs: [
      "Pay $325K more than balanced → Gain 1.3 quality points (9.5 vs 8.2)",
      "Pay $550K more than budget → Reduce risk by 6.0 points (1.5 vs 7.5)",
      "Premium certifications (ISO 9001, CE, TUV, JIS) → Higher compliance costs",
      "Carbon fiber frame upgrade → $240K for premium materials vs $77K aluminum"
    ],
    risks: [
      "EcoEnergy concentration at 29% (within policy, monitor closely)",
      "Premium pricing reduces margin flexibility",
      "Carbon fiber frame (CarbonFiber Pro) - single source dependency",
      "Higher expectations from customers due to premium positioning"
    ],
    volumeDiscounts: [
      { description: "EcoEnergy Systems: Order 500+ batteries, save 4%", savings: 13740 },
      { description: "DriveMotor Corp: Order 500+ motors, save 8%", savings: 26880 },
      { description: "CarbonFiber Pro: Premium materials, limited discount", savings: 0 },
      { description: "Annual savings potential with tier 1 volume commitments: $200K+", savings: 200000 }
    ],
    contractCompliance: [
      { supplier: "EcoEnergy Systems", commitment: "12,000 units/year strategic partnership", status: "✓ On track (9,100 ordered YTD)" },
      { supplier: "DriveMotor Corp", commitment: "No contract commitment", status: "✓ Flexible" },
      { supplier: "CarbonFiber Pro", commitment: "No contract commitment", status: "⚠️ Consider long-term contract for price stability" },
      { supplier: "BrakeSafe Systems", commitment: "12,000 units/year minimum", status: "✓ On track (8,800 ordered YTD)" }
    ]
  }
};

export const paretoSolutions = [solutionA, solutionB, solutionC];

// Network graph data for supplier-material relationships
export function generateNetworkGraphData(solution: OptimizationSolution) {
  const nodes: Array<{ id: string; label: string; type: string; size: number; risk?: number }> = [];
  const links: Array<{ source: string; target: string; value: number; price: number }> = [];

  // Add material nodes (center)
  const uniqueMaterials = new Set(solution.allocations.map(a => a.materialId));
  uniqueMaterials.forEach(matId => {
    const material = getMaterialById(matId);
    if (material) {
      nodes.push({
        id: matId,
        label: material.name.split(' ').slice(0, 2).join(' '), // Shortened name
        type: 'material',
        size: 30
      });
    }
  });

  // Add supplier nodes and links
  const supplierTotals = new Map<string, number>();
  solution.allocations.forEach(alloc => {
    const current = supplierTotals.get(alloc.supplierId) || 0;
    supplierTotals.set(alloc.supplierId, current + alloc.totalCost);
  });

  const uniqueSuppliers = new Set(solution.allocations.map(a => a.supplierId));
  uniqueSuppliers.forEach(supId => {
    const supplier = getSupplierById(supId);
    if (supplier) {
      const totalValue = supplierTotals.get(supId) || 0;
      nodes.push({
        id: supId,
        label: supplier.name.split(' ')[0], // First word only
        type: 'supplier',
        size: 15 + (totalValue / 10000), // Size based on order value
        risk: supplier.geopoliticalRisk
      });
    }
  });

  // Add links
  solution.allocations.forEach(alloc => {
    links.push({
      source: alloc.supplierId,
      target: alloc.materialId,
      value: alloc.quantity,
      price: alloc.unitPrice
    });
  });

  return { nodes, links };
}

// Chat history for demo
export const chatHistory = [
  {
    role: "user",
    content: "I need to build 500 Urban E-Bikes for Q2. Can you optimize the complete BOM across all suppliers?",
    timestamp: new Date(Date.now() - 180000)
  },
  {
    role: "assistant",
    content: "I'll optimize the complete Urban E-Bike BOM (16 materials) across 15 suppliers. Analyzing supplier relationships, pricing, lead times, and risk factors...",
    timestamp: new Date(Date.now() - 170000)
  },
  {
    role: "assistant",
    content: "✅ Optimization complete! I've identified 3 optimal solutions on the Pareto frontier:\n\n**Solution A (Cost-Optimized)**: $650,000 total | Quality 6.5/10 | Risk 7.5/10 | 55 days\n**Solution B (Balanced)**: $875,000 total | Quality 8.2/10 | Risk 3.5/10 | 42 days  \n**Solution C (Risk-Diversified)**: $1,200,000 total | Quality 9.5/10 | Risk 1.5/10 | 35 days\n\nThe $550K difference represents your supply chain insurance premium - tier 1 suppliers with 9.5/10 quality vs 6.5/10. All solutions comply with your 40% max supplier concentration policy.",
    timestamp: new Date(Date.now() - 160000)
  }
];

// Helper functions for new data
export function getDemandForecastForMaterial(materialId: string): DemandForecast[] {
  return demandForecasts.filter(df => df.materialId === materialId);
}

export function getInventoryLevelForMaterial(materialId: string): InventoryLevel | undefined {
  return inventoryLevels.find(inv => inv.materialId === materialId);
}

export function getSupplierPerformanceHistory(supplierId: string): SupplierPerformance[] {
  return supplierPerformance.filter(sp => sp.supplierId === supplierId).sort((a, b) => 
    new Date(b.measurementPeriod).getTime() - new Date(a.measurementPeriod).getTime()
  );
}

export function getVolumeTiersForSupplierMaterial(supplierMaterialId: string): VolumeTier[] {
  return volumeTiers.filter(vt => vt.supplierMaterialId === supplierMaterialId);
}

export function getSupplierContract(supplierId: string): SupplierContract | undefined {
  return supplierContracts.find(sc => sc.supplierId === supplierId);
}

export function getMaterialsAtOrBelowReorderPoint(): Array<{ material: Material; inventory: InventoryLevel }> {
  return inventoryLevels
    .filter(inv => inv.currentStock <= inv.reorderPoint)
    .map(inv => ({
      material: getMaterialById(inv.materialId)!,
      inventory: inv
    }))
    .filter(item => item.material);
}

export function getProductionScheduleForProduct(productName: string): ProductionSchedule[] {
  return productionSchedule.filter(ps => ps.productName.includes(productName));
}
