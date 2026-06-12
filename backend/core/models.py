"""
Pydantic data models for Procurement Optimization Agent.

"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SupplierAdjustment(BaseModel):
    """Risk-scenario adjustment for a specific supplier."""
    freight_multiplier: float = Field(default=1.0, ge=1.0, description="Multiplier on freight cost (1.25 = +25%)")
    lead_time_add_days: int = Field(default=0, ge=0, description="Additional lead time days due to disruption")
    tariff_multiplier: float = Field(default=1.0, ge=1.0, description="Multiplier on base cost for tariffs (1.25 = +25%)")


class OptimizationConstraints(BaseModel):
    """Business constraints for supplier optimization."""

    max_supplier_concentration: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Max % of total order from single supplier (0.40 = 40%)"
    )
    excluded_suppliers: List[str] = Field(
        default_factory=list,
        description="Supplier IDs to exclude entirely from optimization"
    )
    supplier_adjustments: Dict[str, SupplierAdjustment] = Field(
        default_factory=dict,
        description="Per-supplier cost/lead-time adjustments from risk scenarios"
    )
    max_lead_time_days: int = Field(
        default=45,
        gt=0,
        description="Maximum acceptable lead time in days"
    )
    budget_max: float = Field(
        default=1_000_000,
        gt=0,
        description="Maximum budget in USD"
    )
    budget_min: float = Field(
        default=0,
        ge=0,
        description="Minimum budget in USD (for quality floor)"
    )
    prefer_contracted_suppliers: bool = Field(
        default=True,
        description="Prefer suppliers with active contracts"
    )


class ObjectiveWeights(BaseModel):
    """Weights for multi-objective optimization."""

    cost: float = Field(default=0.4, ge=0.0, le=1.0)
    risk: float = Field(default=0.3, ge=0.0, le=1.0)
    lead_time: float = Field(default=0.3, ge=0.0, le=1.0)

    @field_validator("cost", "risk", "lead_time")
    @classmethod
    def weights_must_sum_to_one(cls, v, info):
        """Validate that weights sum to 1.0."""
        # This validator runs per field, so we can't check sum here
        # We'll validate in __init__ instead
        return v

    def model_post_init(self, __context) -> None:
        """Validate weights sum to 1.0 after all fields set."""
        total = self.cost + self.risk + self.lead_time
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(
                f"Objective weights must sum to 1.0, got {total}"
            )


class MaterialDemand(BaseModel):
    """Material demand for optimization."""

    material_id: str = Field(..., description="Material ID (e.g., MAT-001)")
    quantity: int = Field(..., gt=0, description="Quantity needed")
    required_by: Optional[date] = Field(
        None,
        description="Required delivery date"
    )


class SupplierAllocation(BaseModel):
    """Allocation of material to supplier."""

    supplier_id: str
    supplier_name: str
    material_id: str
    material_name: str
    quantity: int
    unit_price: float
    total_cost: float
    lead_time_days: int
    quality_score: float = Field(ge=0.0, le=10.0)
    freight_cost: float = 0.0
    carrying_cost: float = 0.0
    carbon_cost: float = 0.0
    tco: float = 0.0


class SupplierMix(BaseModel):
    """One solution in the Pareto frontier."""

    name: str = Field(..., description="Solution name (Budget, Balanced, Premium, Resilient)")
    total_cost: float = Field(..., gt=0)
    risk_score: float = Field(..., ge=0.0, le=10.0)
    quality_score: float = Field(..., ge=0.0, le=10.0)
    lead_time_days: int = Field(..., gt=0)
    max_supplier_concentration: float = Field(..., ge=0.0, le=1.0)
    allocations: List[SupplierAllocation]
    reasoning: Optional[str] = None
    demand_buffer_pct: Optional[float] = None


class OptimizationRequest(BaseModel):
    """Request to optimize supplier selection."""

    materials: List[MaterialDemand] = Field(
        ...,
        min_length=1,
        description="Materials to procure"
    )
    constraints: OptimizationConstraints = Field(
        default_factory=OptimizationConstraints
    )
    objectives: ObjectiveWeights = Field(
        default_factory=ObjectiveWeights
    )


class OptimizationResponse(BaseModel):
    """Response with Pareto frontier solutions."""

    solutions: List[SupplierMix] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Pareto-optimal solutions (3-5 typically)"
    )
    request_id: str = Field(..., description="Unique request ID for tracing")
    computation_time_ms: int = Field(..., ge=0)


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    environment: str
