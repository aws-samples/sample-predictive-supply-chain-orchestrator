"""
CSV data reader with caching and validation.

Reads procurement data from CSV files and returns Pydantic models.
Implements in-memory caching for performance.

Follows CDE standards:
- Type hints
- Error handling
- Pydantic validation
- Structured logging
"""

import csv
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger()


class Supplier(BaseModel):
    """Supplier data model with validation."""

    supplier_id: str = Field(..., pattern=r"^SUP-\d{3}$")
    name: str = Field(..., min_length=1, max_length=200)
    location: str
    rating: float = Field(..., ge=0.0, le=5.0)
    lead_time_days: int = Field(..., gt=0)
    payment_terms: str
    financial_stability_score: float = Field(..., ge=0.0, le=10.0)
    geopolitical_risk_score: float = Field(..., ge=0.0, le=10.0)
    active_status: bool
    contact_email: str
    contact_phone: str


class Material(BaseModel):
    """Material data model with validation."""

    material_id: str = Field(..., pattern=r"^MAT-[A-Z]{3}-\d{3}$")
    name: str = Field(..., min_length=1)
    category: str
    unit_of_measure: str
    standard_cost: float = Field(..., gt=0)
    criticality_level: str
    weight_kg: float = Field(..., gt=0)


class SupplierMaterial(BaseModel):
    """Supplier-material relationship with pricing."""

    supplier_material_id: str
    supplier_id: str
    material_id: str
    base_price: float = Field(..., gt=0)
    currency: str
    effective_date: date
    minimum_order_quantity: int = Field(..., gt=0)
    lead_time_days: int = Field(..., gt=0)
    quality_certification: str
    sustainability_score: float = Field(..., ge=0.0, le=10.0)
    carbon_footprint_kg: float = Field(..., ge=0.0)


class VolumeTier(BaseModel):
    """Volume discount tier."""

    tier_id: str
    supplier_material_id: str
    tier_level: int = Field(..., gt=0)
    min_quantity: int = Field(..., gt=0)
    max_quantity: Optional[int] = Field(None, gt=0)
    discount_percentage: float = Field(..., ge=0.0, le=100.0)
    unit_price: float = Field(..., gt=0)

    @field_validator("max_quantity")
    @classmethod
    def max_must_be_greater_than_min(cls, v, info):
        """Validate max_quantity > min_quantity."""
        if v is not None and "min_quantity" in info.data:
            if v <= info.data["min_quantity"]:
                raise ValueError("max_quantity must be greater than min_quantity")
        return v


class SupplierPerformance(BaseModel):
    """Supplier performance metrics."""

    performance_id: str
    supplier_id: str
    measurement_period: str
    on_time_delivery_rate: float = Field(..., ge=0.0, le=100.0)
    quality_score: float = Field(..., ge=0.0, le=10.0)
    defect_rate: float = Field(..., ge=0.0, le=100.0)
    cost_variance: float
    response_time_hours: int = Field(..., gt=0)


class DemandForecast(BaseModel):
    """Demand forecast with confidence levels."""

    forecast_id: str
    material_id: str
    forecast_period: str
    predicted_demand: int = Field(..., gt=0)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    forecast_date: date
    notes: str = ""


class ProductionSchedule(BaseModel):
    """Production schedule entry."""

    schedule_id: str
    product_id: str
    product_name: str
    planned_quantity: int = Field(..., gt=0)
    start_date: date
    end_date: date
    status: str
    priority: str
    notes: str = ""


class SupplierContract(BaseModel):
    """Supplier contract details."""

    contract_id: str
    supplier_id: str
    contract_type: str
    start_date: date
    end_date: date
    annual_value: float = Field(..., gt=0)
    payment_terms: str
    volume_commitment: str
    price_adjustment_clause: str = ""
    sustainability_clause: str = ""
    status: str
    renewal_option: str = ""


class DefectRecord(BaseModel):
    """Defect tracking record for supplier parts."""

    defect_id: str = Field(..., pattern=r"^DEF-\d{3}$")
    supplier_id: str
    material_id: str
    defect_date: date
    severity: str = Field(..., description="CRITICAL, MAJOR, or MINOR")
    category: str = Field(..., description="ELECTRICAL, MECHANICAL, STRUCTURAL, PERFORMANCE, COSMETIC")
    quantity_affected: int = Field(..., gt=0)
    batch_id: str
    description: str
    root_cause: str
    status: str = Field(..., description="OPEN, RESOLVED, CLOSED")
    recall_initiated: bool
    resolution_date: Optional[date] = None
    corrective_action: str = ""

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"CRITICAL", "MAJOR", "MINOR"}
        if v.upper() not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v.upper()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"OPEN", "RESOLVED", "CLOSED"}
        if v.upper() not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v.upper()


class CSVDataReader:
    """
    CSV data reader with caching.

    Reads procurement data from CSV files and caches in memory.
    Validates data using Pydantic models.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize CSV reader.

        Args:
            data_dir: Directory containing CSV files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        logger.info("csv_reader_initialized", data_dir=str(self.data_dir))

    @lru_cache(maxsize=1)
    def get_suppliers(self) -> List[Supplier]:
        """
        Read and cache suppliers.

        Returns:
            List of validated Supplier models

        Raises:
            FileNotFoundError: If suppliers.csv not found
            ValueError: If validation fails
        """
        file_path = self.data_dir / "suppliers.csv"
        logger.info("reading_suppliers", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                suppliers = []

                for row in reader:
                    # Convert boolean
                    row["active_status"] = row["active_status"].upper() == "TRUE"
                    # Convert numeric fields
                    row["rating"] = float(row["rating"])
                    row["lead_time_days"] = int(row["lead_time_days"])
                    row["financial_stability_score"] = float(row["financial_stability_score"])
                    row["geopolitical_risk_score"] = float(row["geopolitical_risk_score"])

                    suppliers.append(Supplier(**row))

                logger.info("suppliers_loaded", count=len(suppliers))
                return suppliers

        except FileNotFoundError as e:
            logger.error("suppliers_file_not_found", file_path=str(file_path))
            raise
        except Exception as e:
            logger.error("suppliers_load_failed", error=str(e))
            raise ValueError(f"Failed to load suppliers: {e}")

    @lru_cache(maxsize=1)
    def get_materials(self) -> List[Material]:
        """
        Read and cache materials.

        Returns:
            List of validated Material models

        Raises:
            FileNotFoundError: If materials.csv not found
            ValueError: If validation fails
        """
        file_path = self.data_dir / "materials.csv"
        logger.info("reading_materials", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                materials = []

                for row in reader:
                    # Convert numeric fields
                    row["standard_cost"] = float(row["standard_cost"])
                    row["weight_kg"] = float(row["weight_kg"])

                    materials.append(Material(**row))

                logger.info("materials_loaded", count=len(materials))
                return materials

        except FileNotFoundError as e:
            logger.error("materials_file_not_found", file_path=str(file_path))
            raise
        except Exception as e:
            logger.error("materials_load_failed", error=str(e))
            raise ValueError(f"Failed to load materials: {e}")

    @lru_cache(maxsize=1)
    def get_supplier_materials(self) -> List[SupplierMaterial]:
        """
        Read and cache supplier-material relationships.

        Returns:
            List of validated SupplierMaterial models

        Raises:
            FileNotFoundError: If supplier_materials.csv not found
            ValueError: If validation fails
        """
        file_path = self.data_dir / "supplier_materials.csv"
        logger.info("reading_supplier_materials", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                supplier_materials = []

                for row in reader:
                    # Convert numeric fields
                    row["base_price"] = float(row["base_price"])
                    row["minimum_order_quantity"] = int(row["minimum_order_quantity"])
                    row["lead_time_days"] = int(row["lead_time_days"])
                    row["sustainability_score"] = float(row["sustainability_score"])
                    row["carbon_footprint_kg"] = float(row["carbon_footprint_kg"])
                    # Convert date
                    row["effective_date"] = datetime.strptime(
                        row["effective_date"], "%Y-%m-%d"
                    ).date()

                    supplier_materials.append(SupplierMaterial(**row))

                logger.info("supplier_materials_loaded", count=len(supplier_materials))
                return supplier_materials

        except FileNotFoundError as e:
            logger.error("supplier_materials_file_not_found", file_path=str(file_path))
            raise
        except Exception as e:
            logger.error("supplier_materials_load_failed", error=str(e))
            raise ValueError(f"Failed to load supplier materials: {e}")

    @lru_cache(maxsize=1)
    def get_volume_tiers(self) -> List[VolumeTier]:
        """
        Read and cache volume discount tiers.

        Returns:
            List of validated VolumeTier models

        Raises:
            FileNotFoundError: If volume_tiers.csv not found
            ValueError: If validation fails
        """
        file_path = self.data_dir / "volume_tiers.csv"
        logger.info("reading_volume_tiers", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                volume_tiers = []

                for row in reader:
                    # Convert numeric fields
                    row["tier_level"] = int(row["tier_level"])
                    row["min_quantity"] = int(row["min_quantity"])
                    # Handle empty max_quantity (unlimited)
                    row["max_quantity"] = (
                        int(row["max_quantity"]) if row["max_quantity"] else None
                    )
                    row["discount_percentage"] = float(row["discount_percentage"])
                    row["unit_price"] = float(row["unit_price"])

                    volume_tiers.append(VolumeTier(**row))

                logger.info("volume_tiers_loaded", count=len(volume_tiers))
                return volume_tiers

        except FileNotFoundError as e:
            logger.error("volume_tiers_file_not_found", file_path=str(file_path))
            raise
        except Exception as e:
            logger.error("volume_tiers_load_failed", error=str(e))
            raise ValueError(f"Failed to load volume tiers: {e}")

    @lru_cache(maxsize=1)
    def get_supplier_performance(self) -> List[SupplierPerformance]:
        """
        Read and cache supplier performance metrics.

        Returns:
            List of validated SupplierPerformance models

        Raises:
            FileNotFoundError: If supplier_performance.csv not found
            ValueError: If validation fails
        """
        file_path = self.data_dir / "supplier_performance.csv"
        logger.info("reading_supplier_performance", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                performance_records = []

                for row in reader:
                    # Convert numeric fields
                    row["on_time_delivery_rate"] = float(row["on_time_delivery_rate"])
                    row["quality_score"] = float(row["quality_score"])
                    row["defect_rate"] = float(row["defect_rate"])
                    row["cost_variance"] = float(row["cost_variance"])
                    row["response_time_hours"] = int(row["response_time_hours"])

                    performance_records.append(SupplierPerformance(**row))

                logger.info("supplier_performance_loaded", count=len(performance_records))
                return performance_records

        except FileNotFoundError as e:
            logger.error("supplier_performance_file_not_found", file_path=str(file_path))
            raise
        except Exception as e:
            logger.error("supplier_performance_load_failed", error=str(e))
            raise ValueError(f"Failed to load supplier performance: {e}")

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """
        Get supplier by ID.

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            Supplier model or None if not found
        """
        suppliers = self.get_suppliers()
        for supplier in suppliers:
            if supplier.supplier_id == supplier_id:
                return supplier
        return None

    def get_material_by_id(self, material_id: str) -> Optional[Material]:
        """
        Get material by ID.

        Args:
            material_id: Material ID (e.g., MAT-BAT-001)

        Returns:
            Material model or None if not found
        """
        materials = self.get_materials()
        for material in materials:
            if material.material_id == material_id:
                return material
        return None

    def get_suppliers_for_material(self, material_id: str) -> List[SupplierMaterial]:
        """
        Get all suppliers that can provide a material.

        Args:
            material_id: Material ID (e.g., MAT-BAT-001)

        Returns:
            List of SupplierMaterial relationships
        """
        supplier_materials = self.get_supplier_materials()
        return [
            sm for sm in supplier_materials
            if sm.material_id == material_id
        ]

    def get_volume_tiers_for_supplier_material(
        self, supplier_material_id: str
    ) -> List[VolumeTier]:
        """
        Get volume discount tiers for a supplier-material relationship.

        Args:
            supplier_material_id: SupplierMaterial ID (e.g., SM-001)

        Returns:
            List of VolumeTier models sorted by min_quantity
        """
        volume_tiers = self.get_volume_tiers()
        tiers = [
            vt for vt in volume_tiers
            if vt.supplier_material_id == supplier_material_id
        ]
        return sorted(tiers, key=lambda t: t.min_quantity)

    def get_latest_performance(self, supplier_id: str) -> Optional[SupplierPerformance]:
        """
        Get latest performance record for a supplier.

        Args:
            supplier_id: Supplier ID (e.g., SUP-001)

        Returns:
            Latest SupplierPerformance model or None
        """
        performance_records = self.get_supplier_performance()
        supplier_records = [
            p for p in performance_records
            if p.supplier_id == supplier_id
        ]

        if not supplier_records:
            return None

        # Sort by measurement_period descending
        return sorted(
            supplier_records,
            key=lambda p: p.measurement_period,
            reverse=True
        )[0]

    @lru_cache(maxsize=1)
    def get_demand_forecasts(self) -> List[DemandForecast]:
        """Read and cache demand forecasts."""
        file_path = self.data_dir / "demand_forecast.csv"
        logger.info("reading_demand_forecasts", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                forecasts = []

                for row in reader:
                    row["predicted_demand"] = int(row["predicted_demand"])
                    row["confidence_level"] = float(row["confidence_level"])
                    row["forecast_date"] = datetime.strptime(
                        row["forecast_date"], "%Y-%m-%d"
                    ).date()

                    forecasts.append(DemandForecast(**row))

                logger.info("demand_forecasts_loaded", count=len(forecasts))
                return forecasts

        except FileNotFoundError:
            logger.warning("demand_forecast_file_not_found", file_path=str(file_path))
            return []
        except Exception as e:
            logger.error("demand_forecasts_load_failed", error=str(e))
            return []

    def get_forecasts_for_material(self, material_id: str) -> List[DemandForecast]:
        """
        Get demand forecasts for a material.

        Handles ID format mismatch between forecast data (e.g. MAT001)
        and material data (e.g. MAT-BAT-001) by trying exact match first,
        then falling back to numeric suffix matching.
        """
        forecasts = self.get_demand_forecasts()
        # Try exact match first
        result = [f for f in forecasts if f.material_id == material_id]
        if result:
            return result

        # Fallback: extract numeric part from material_id for fuzzy match
        # e.g., MAT-BAT-001 -> try matching against MAT001 style IDs
        nums = re.findall(r'\d+', material_id)
        if nums:
            # Use the last numeric group (e.g., "001" from "MAT-BAT-001")
            num_suffix = nums[-1].lstrip('0') or '0'
            result = []
            for f in forecasts:
                f_nums = re.findall(r'\d+', f.material_id)
                if f_nums:
                    f_suffix = f_nums[-1].lstrip('0') or '0'
                    if f_suffix == num_suffix:
                        result.append(f)
        return result

    @lru_cache(maxsize=1)
    def get_production_schedules(self) -> List[ProductionSchedule]:
        """Read and cache production schedules."""
        file_path = self.data_dir / "production_schedule.csv"
        logger.info("reading_production_schedules", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                schedules = []

                for row in reader:
                    row["planned_quantity"] = int(row["planned_quantity"])
                    row["start_date"] = datetime.strptime(
                        row["start_date"], "%Y-%m-%d"
                    ).date()
                    row["end_date"] = datetime.strptime(
                        row["end_date"], "%Y-%m-%d"
                    ).date()

                    schedules.append(ProductionSchedule(**row))

                logger.info("production_schedules_loaded", count=len(schedules))
                return schedules

        except FileNotFoundError:
            logger.warning("production_schedule_file_not_found", file_path=str(file_path))
            return []
        except Exception as e:
            logger.error("production_schedules_load_failed", error=str(e))
            return []

    @lru_cache(maxsize=1)
    def get_supplier_contracts(self) -> List[SupplierContract]:
        """Read and cache supplier contracts."""
        file_path = self.data_dir / "supplier_contracts.csv"
        logger.info("reading_supplier_contracts", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                contracts = []

                for row in reader:
                    row["annual_value"] = float(row["annual_value"])
                    row["start_date"] = datetime.strptime(
                        row["start_date"], "%Y-%m-%d"
                    ).date()
                    row["end_date"] = datetime.strptime(
                        row["end_date"], "%Y-%m-%d"
                    ).date()
                    # Normalize supplier_id format (SUP001 -> SUP-001)
                    sid = row["supplier_id"]
                    if "-" not in sid and sid.startswith("SUP"):
                        row["supplier_id"] = f"SUP-{sid[3:]}"

                    contracts.append(SupplierContract(**row))

                logger.info("supplier_contracts_loaded", count=len(contracts))
                return contracts

        except FileNotFoundError:
            logger.warning("supplier_contracts_file_not_found", file_path=str(file_path))
            return []
        except Exception as e:
            logger.error("supplier_contracts_load_failed", error=str(e))
            return []

    def get_contract_for_supplier(self, supplier_id: str) -> Optional[SupplierContract]:
        """Get active contract for a supplier."""
        contracts = self.get_supplier_contracts()
        today = date.today()
        for contract in contracts:
            if (contract.supplier_id == supplier_id and
                    contract.status == "Active" and
                    contract.start_date <= today <= contract.end_date):
                return contract
        return None

    def get_performance_history(self, supplier_id: str) -> List[SupplierPerformance]:
        """
        Get all performance records for a supplier (not just latest).

        Returns records sorted by measurement_period descending (most recent first).
        """
        performance_records = self.get_supplier_performance()
        supplier_records = [
            p for p in performance_records
            if p.supplier_id == supplier_id
        ]
        return sorted(
            supplier_records,
            key=lambda p: p.measurement_period,
            reverse=True
        )

    @lru_cache(maxsize=1)
    def get_defects(self) -> List[DefectRecord]:
        """Read and cache defect records."""
        file_path = self.data_dir / "defects.csv"
        logger.info("reading_defects", file_path=str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                defects = []

                for row in reader:
                    row["defect_date"] = datetime.strptime(
                        row["defect_date"], "%Y-%m-%d"
                    ).date()
                    row["quantity_affected"] = int(row["quantity_affected"])
                    row["recall_initiated"] = row["recall_initiated"].upper() == "TRUE"
                    row["resolution_date"] = (
                        datetime.strptime(row["resolution_date"], "%Y-%m-%d").date()
                        if row.get("resolution_date")
                        else None
                    )

                    defects.append(DefectRecord(**row))

                logger.info("defects_loaded", count=len(defects))
                return defects

        except FileNotFoundError:
            logger.warning("defects_file_not_found", file_path=str(file_path))
            return []
        except Exception as e:
            logger.error("defects_load_failed", error=str(e))
            return []

    def get_defects_for_supplier(self, supplier_id: str) -> List[DefectRecord]:
        """Get all defect records for a supplier, sorted by date descending."""
        defects = self.get_defects()
        supplier_defects = [d for d in defects if d.supplier_id == supplier_id]
        return sorted(supplier_defects, key=lambda d: d.defect_date, reverse=True)

    def get_defects_for_material(self, material_id: str) -> List[DefectRecord]:
        """Get all defect records for a material, sorted by date descending."""
        defects = self.get_defects()
        material_defects = [d for d in defects if d.material_id == material_id]
        return sorted(material_defects, key=lambda d: d.defect_date, reverse=True)

    def get_defects_for_supplier_material(
        self, supplier_id: str, material_id: str
    ) -> List[DefectRecord]:
        """Get defect records for a specific supplier-material pair."""
        defects = self.get_defects()
        return sorted(
            [d for d in defects if d.supplier_id == supplier_id and d.material_id == material_id],
            key=lambda d: d.defect_date,
            reverse=True,
        )

    def get_supplier_defect_score(self, supplier_id: str) -> float:
        """
        Calculate a defect risk score (0-10) for a supplier.

        Considers: number of defects, severity weighting, open vs resolved,
        recall history, and recency.
        """
        defects = self.get_defects_for_supplier(supplier_id)
        if not defects:
            return 0.0  # No defects = no defect risk

        severity_weights = {"CRITICAL": 3.0, "MAJOR": 2.0, "MINOR": 1.0}
        status_multiplier = {"OPEN": 1.5, "RESOLVED": 0.8, "CLOSED": 0.5}

        total_score = 0.0
        for d in defects:
            base = severity_weights.get(d.severity, 1.0)
            status_mult = status_multiplier.get(d.status, 1.0)
            recall_mult = 1.5 if d.recall_initiated else 1.0
            # Recency: defects in last 60 days weigh more
            days_ago = (date.today() - d.defect_date).days
            recency_mult = 1.3 if days_ago < 60 else (1.0 if days_ago < 180 else 0.7)
            total_score += base * status_mult * recall_mult * recency_mult

        # Normalize to 0-10 scale (cap at 10)
        return min(10.0, total_score)
