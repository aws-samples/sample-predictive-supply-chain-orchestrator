# Procurement Optimization Agent - Data Schema

## Overview

This document defines the complete data model for the Procurement Optimization Agent, designed for E-bike manufacturing procurement optimization.

## Entity Definitions

### 1. Supplier

Represents vendors who provide components for E-bike manufacturing.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| supplier_id | VARCHAR(50) | Primary key, unique supplier identifier | SUP-001 |
| name | VARCHAR(200) | Supplier company name | BatteryTech Solutions |
| location | VARCHAR(100) | Geographic location (City, Country) | Shenzhen, China |
| rating | DECIMAL(3,2) | Overall supplier rating (0.00-5.00) | 4.25 |
| lead_time_days | INTEGER | Average lead time in days | 30 |
| payment_terms | VARCHAR(20) | Payment terms (NET 30, NET 60, NET 90) | NET 60 |
| financial_stability_score | DECIMAL(3,2) | Financial health rating (0.00-10.00) | 7.5 |
| geopolitical_risk_score | DECIMAL(3,2) | Location-based risk (0.00-10.00) | 3.2 |
| active_status | BOOLEAN | Whether supplier is currently active | TRUE |
| contact_email | VARCHAR(200) | Primary contact email | contact@batterytech.com |
| contact_phone | VARCHAR(50) | Primary contact phone | +86-755-1234567 |

### 2. SupplierContract

Represents contractual agreements with suppliers.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| contract_id | VARCHAR(50) | Primary key | CONT-001 |
| supplier_id | VARCHAR(50) | Foreign key to Supplier | SUP-001 |
| start_date | DATE | Contract start date | 2024-01-01 |
| end_date | DATE | Contract end date | 2025-12-31 |
| pricing_model | VARCHAR(50) | Pricing structure type | VOLUME_TIERED |
| terms | TEXT | Contract terms and conditions | Standard terms... |
| minimum_order_value | DECIMAL(12,2) | Minimum order value in USD | 10000.00 |

### 3. SupplierPerformance

Historical performance metrics for suppliers.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| performance_id | VARCHAR(50) | Primary key | PERF-001 |
| supplier_id | VARCHAR(50) | Foreign key to Supplier | SUP-001 |
| measurement_period | VARCHAR(20) | Period (YYYY-MM) | 2024-01 |
| on_time_delivery_rate | DECIMAL(5,2) | Percentage (0.00-100.00) | 95.50 |
| quality_score | DECIMAL(3,2) | Quality rating (0.00-10.00) | 8.75 |
| defect_rate | DECIMAL(5,2) | Defect percentage (0.00-100.00) | 1.25 |
| cost_variance | DECIMAL(5,2) | Cost variance percentage | -2.50 |
| response_time_hours | INTEGER | Average response time | 24 |

### 4. Material (Component)

Represents E-bike components and materials.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| material_id | VARCHAR(50) | Primary key, SKU | MAT-BAT-001 |
| name | VARCHAR(200) | Component name | Lithium-ion Battery Pack 48V 20Ah |
| category | VARCHAR(50) | Component category | BATTERY_SYSTEM |
| unit_of_measure | VARCHAR(20) | Unit (EACH, KG, METER) | EACH |
| standard_cost | DECIMAL(10,2) | Standard cost in USD | 450.00 |
| technical_specs | JSON | Technical specifications | {"voltage": "48V", "capacity": "20Ah"} |
| criticality_level | VARCHAR(20) | CRITICAL, HIGH, MEDIUM, LOW | CRITICAL |
| weight_kg | DECIMAL(8,2) | Component weight | 6.50 |

**Category Values:**
- BATTERY_SYSTEM
- DRIVE_SYSTEM
- FRAME_COMPONENT
- ELECTRONICS
- STANDARD_PARTS

### 5. BillOfMaterials (BOM)

Defines which materials are required for each E-bike model.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| bom_id | VARCHAR(50) | Primary key | BOM-001 |
| product_id | VARCHAR(50) | E-bike model identifier | EBIKE-URBAN-2024 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| quantity_required | DECIMAL(10,2) | Quantity per unit | 1.00 |
| lead_time_days | INTEGER | Component lead time | 30 |
| assembly_sequence | INTEGER | Assembly order | 5 |

### 6. MaterialSpecification

Detailed technical specifications for materials.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| spec_id | VARCHAR(50) | Primary key | SPEC-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| specification_type | VARCHAR(50) | Type of specification | ELECTRICAL |
| specification_key | VARCHAR(100) | Specification parameter | voltage |
| specification_value | VARCHAR(200) | Parameter value | 48V |
| unit | VARCHAR(50) | Unit of measurement | Volts |
| tolerance | VARCHAR(50) | Acceptable tolerance | ±2V |

### 7. SupplierMaterial (Supplier-Component Mapping)

Links suppliers to the materials they can provide with pricing.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| supplier_material_id | VARCHAR(50) | Primary key | SM-001 |
| supplier_id | VARCHAR(50) | Foreign key to Supplier | SUP-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| base_price | DECIMAL(10,2) | Base unit price in USD | 480.00 |
| currency | VARCHAR(10) | Currency code | USD |
| effective_date | DATE | Price effective date | 2024-01-01 |
| minimum_order_quantity | INTEGER | MOQ | 100 |
| lead_time_days | INTEGER | Supplier-specific lead time | 35 |
| quality_certification | VARCHAR(100) | Certifications | ISO 9001, UL Listed |
| sustainability_score | DECIMAL(3,2) | Environmental score (0.00-10.00) | 7.80 |
| carbon_footprint_kg | DECIMAL(8,2) | CO2 per unit | 12.50 |

### 8. VolumeTier

Volume-based pricing tiers for supplier-material combinations.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| tier_id | VARCHAR(50) | Primary key | TIER-001 |
| supplier_material_id | VARCHAR(50) | Foreign key to SupplierMaterial | SM-001 |
| tier_level | INTEGER | Tier number (1, 2, 3...) | 1 |
| min_quantity | INTEGER | Minimum quantity for tier | 100 |
| max_quantity | INTEGER | Maximum quantity (NULL = unlimited) | 499 |
| discount_percentage | DECIMAL(5,2) | Discount percentage | 0.00 |
| unit_price | DECIMAL(10,2) | Price at this tier | 480.00 |

### 9. PurchaseRequisition

Internal requests for material procurement.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| requisition_id | VARCHAR(50) | Primary key | REQ-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| quantity_requested | INTEGER | Requested quantity | 1000 |
| requested_by | VARCHAR(100) | Requester name/ID | John Smith |
| requested_date | DATE | Request date | 2024-02-01 |
| required_by_date | DATE | Required delivery date | 2024-03-15 |
| urgency_level | VARCHAR(20) | CRITICAL, HIGH, NORMAL, LOW | NORMAL |
| justification | TEXT | Reason for request | Q1 production requirements |
| status | VARCHAR(20) | PENDING, APPROVED, ORDERED | APPROVED |

### 10. PurchaseOrder

Orders placed with suppliers.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| po_id | VARCHAR(50) | Primary key | PO-001 |
| supplier_id | VARCHAR(50) | Foreign key to Supplier | SUP-001 |
| requisition_id | VARCHAR(50) | Foreign key to PurchaseRequisition | REQ-001 |
| order_date | DATE | Order placement date | 2024-02-05 |
| expected_delivery_date | DATE | Expected delivery | 2024-03-12 |
| actual_delivery_date | DATE | Actual delivery (NULL if pending) | NULL |
| total_amount | DECIMAL(12,2) | Total order value | 456000.00 |
| status | VARCHAR(20) | DRAFT, SENT, CONFIRMED, DELIVERED | CONFIRMED |
| payment_terms | VARCHAR(20) | Payment terms for this order | NET 60 |
| order_type | VARCHAR(20) | PLANNED, UNPLANNED | PLANNED |

### 11. PurchaseOrderLine

Individual line items in purchase orders.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| po_line_id | VARCHAR(50) | Primary key | POL-001 |
| po_id | VARCHAR(50) | Foreign key to PurchaseOrder | PO-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| quantity | INTEGER | Ordered quantity | 1000 |
| unit_price | DECIMAL(10,2) | Price per unit | 456.00 |
| line_total | DECIMAL(12,2) | Line total amount | 456000.00 |
| delivery_date | DATE | Line item delivery date | 2024-03-12 |
| received_quantity | INTEGER | Quantity received | 0 |

### 12. InventoryLevel

Current inventory status for materials.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| inventory_id | VARCHAR(50) | Primary key | INV-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| warehouse_location | VARCHAR(100) | Warehouse identifier | WH-MAIN-01 |
| current_stock | INTEGER | Current quantity on hand | 250 |
| reorder_point | INTEGER | Reorder trigger quantity | 200 |
| safety_stock | INTEGER | Safety stock level | 150 |
| last_updated | TIMESTAMP | Last update timestamp | 2024-02-20 10:30:00 |

### 13. DemandForecast

Predicted future demand for materials.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| forecast_id | VARCHAR(50) | Primary key | FCST-001 |
| material_id | VARCHAR(50) | Foreign key to Material | MAT-BAT-001 |
| forecast_period | VARCHAR(20) | Period (YYYY-MM) | 2024-03 |
| predicted_demand | INTEGER | Forecasted quantity | 1200 |
| confidence_level | DECIMAL(5,2) | Confidence percentage | 85.00 |
| forecast_method | VARCHAR(50) | Forecasting method used | TIME_SERIES |
| created_date | DATE | Forecast creation date | 2024-02-01 |

### 14. ProductionSchedule

Planned production schedule driving material requirements.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| schedule_id | VARCHAR(50) | Primary key | SCHED-001 |
| product_id | VARCHAR(50) | E-bike model | EBIKE-URBAN-2024 |
| planned_quantity | INTEGER | Units to produce | 1000 |
| start_date | DATE | Production start | 2024-03-01 |
| end_date | DATE | Production end | 2024-03-31 |
| status | VARCHAR(20) | PLANNED, IN_PROGRESS, COMPLETED | PLANNED |
| priority | VARCHAR(20) | HIGH, MEDIUM, LOW | HIGH |

## Relationships

### Primary Relationships

```
Supplier (1) ──── (N) SupplierContract
Supplier (1) ──── (N) SupplierPerformance
Supplier (1) ──── (N) SupplierMaterial
Supplier (1) ──── (N) PurchaseOrder

Material (1) ──── (N) BillOfMaterials
Material (1) ──── (N) MaterialSpecification
Material (1) ──── (N) SupplierMaterial
Material (1) ──── (N) InventoryLevel
Material (1) ──── (N) DemandForecast
Material (1) ──── (N) PurchaseRequisition
Material (1) ──── (N) PurchaseOrderLine

SupplierMaterial (1) ──── (N) VolumeTier

PurchaseRequisition (1) ──── (N) PurchaseOrder
PurchaseOrder (1) ──── (N) PurchaseOrderLine

ProductionSchedule (1) ──── (N) BillOfMaterials (via product_id)
```

## Graph Database Schema (Neptune/Gremlin)

### Vertex Labels

- `Supplier`
- `Material`
- `SupplierContract`
- `SupplierPerformance`
- `PurchaseOrder`
- `InventoryLevel`
- `DemandForecast`
- `ProductionSchedule`

### Edge Labels

- `SUPPLIES` (Supplier → Material)
- `HAS_CONTRACT` (Supplier → SupplierContract)
- `HAS_PERFORMANCE` (Supplier → SupplierPerformance)
- `PART_OF` (Material → BillOfMaterials)
- `HAS_SPECIFICATION` (Material → MaterialSpecification)
- `STORED_IN` (Material → InventoryLevel)
- `REQUESTS` (PurchaseRequisition → Material)
- `FULFILLED_BY` (PurchaseRequisition → PurchaseOrder)
- `ORDERED_FROM` (PurchaseOrder → Supplier)
- `CONTAINS` (PurchaseOrder → PurchaseOrderLine)
- `FORECASTS` (DemandForecast → Material)
- `REQUIRES` (ProductionSchedule → Material)

## Indexes

### Recommended Indexes for Performance

```sql
-- Supplier lookups
CREATE INDEX idx_supplier_location ON Supplier(location);
CREATE INDEX idx_supplier_rating ON Supplier(rating);
CREATE INDEX idx_supplier_active ON Supplier(active_status);

-- Material lookups
CREATE INDEX idx_material_category ON Material(category);
CREATE INDEX idx_material_criticality ON Material(criticality_level);

-- Supplier-Material pricing
CREATE INDEX idx_sm_supplier ON SupplierMaterial(supplier_id);
CREATE INDEX idx_sm_material ON SupplierMaterial(material_id);
CREATE INDEX idx_sm_effective_date ON SupplierMaterial(effective_date);

-- Purchase orders
CREATE INDEX idx_po_supplier ON PurchaseOrder(supplier_id);
CREATE INDEX idx_po_status ON PurchaseOrder(status);
CREATE INDEX idx_po_order_date ON PurchaseOrder(order_date);

-- Inventory
CREATE INDEX idx_inv_material ON InventoryLevel(material_id);
CREATE INDEX idx_inv_warehouse ON InventoryLevel(warehouse_location);

-- Demand forecast
CREATE INDEX idx_fcst_material ON DemandForecast(material_id);
CREATE INDEX idx_fcst_period ON DemandForecast(forecast_period);
```

## Data Validation Rules

1. **Supplier Rating**: Must be between 0.00 and 5.00
2. **Risk Scores**: Must be between 0.00 and 10.00
3. **Percentages**: Must be between 0.00 and 100.00
4. **Payment Terms**: Must be one of: NET 15, NET 30, NET 45, NET 60, NET 90, NET 120
5. **Dates**: end_date must be >= start_date
6. **Quantities**: Must be positive integers
7. **Prices**: Must be positive decimals
8. **Status Values**: Must match predefined enum values

## Notes

- All monetary values are in USD unless otherwise specified
- All dates are in ISO 8601 format (YYYY-MM-DD)
- All timestamps are in UTC
- JSON fields use standard JSON format
- NULL values are allowed for optional fields
