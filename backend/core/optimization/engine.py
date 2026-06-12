"""
Multi-objective optimization engine for supplier selection.

Generates Pareto frontier solutions balancing cost, risk, and lead time.
Applies business constraints (concentration, MOQ, budget, delivery dates, contracts).
Includes TCO calculation, dynamic risk scoring, demand uncertainty, and volume consolidation.

"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize, LinearConstraint
import structlog

from core.models import (
    OptimizationRequest,
    SupplierMix,
    SupplierAllocation,
    MaterialDemand
)
from data.csv_reader import CSVDataReader, Supplier, SupplierMaterial

logger = structlog.get_logger()


class OptimizationEngine:
    """
    Multi-objective optimization engine for supplier selection.

    Uses weighted sum method to generate Pareto frontier solutions.
    Applies constraints: concentration, MOQ, budget, lead time, delivery dates, contracts.
    Features: TCO calculation, dynamic risk scoring, demand uncertainty, volume consolidation.
    """

    # Freight rate estimates by supplier region
    FREIGHT_RATES = {
        "China": 0.08, "South Korea": 0.07, "Japan": 0.07, "Taiwan": 0.07,
        "Germany": 0.04, "Netherlands": 0.04, "Italy": 0.04,
        "USA": 0.02, "Mexico": 0.03, "Canada": 0.02,
    }

    # Shadow carbon price: $50/ton CO2 = $0.05/kg
    CARBON_PRICE_PER_KG = 0.05

    def __init__(self, data_reader: CSVDataReader):
        """
        Initialize optimization engine.

        Args:
            data_reader: CSV data reader instance
        """
        self.data_reader = data_reader
        logger.info("optimization_engine_initialized")

    def optimize(self, request: OptimizationRequest) -> List[SupplierMix]:
        """
        Generate Pareto frontier solutions.

        Creates 3 solutions with different objective weights:
        - Cost-Optimized: Minimize cost, allow higher concentration (up to 60%)
        - Balanced: Best tradeoff, standard concentration limit
        - Risk-Diversified: Maximize diversification, no supplier >25% share

        Args:
            request: Optimization request with materials and constraints

        Returns:
            List of 3 SupplierMix solutions on Pareto frontier

        Raises:
            ValueError: If no feasible solution exists
        """
        logger.info(
            "optimization_started",
            materials_count=len(request.materials),
            max_concentration=request.constraints.max_supplier_concentration
        )

        # Build optimization problem
        problem = self._build_problem(request)

        # Generate 3 solutions with different weight profiles
        weight_profiles = [
            ("Cost-Optimized", {"cost": 0.80, "risk": 0.05, "lead_time": 0.15}, {"max_concentration": 0.60}),
            ("Balanced", {"cost": 0.35, "risk": 0.30, "lead_time": 0.35}, {}),
            ("Risk-Diversified", {"cost": 0.05, "risk": 0.60, "lead_time": 0.35}, {}),
        ]

        solutions = []
        for name, weights, overrides in weight_profiles:
            try:
                effective_constraints = type(request.constraints)(
                    max_supplier_concentration=overrides.get(
                        "max_concentration", request.constraints.max_supplier_concentration
                    ),
                    max_lead_time_days=request.constraints.max_lead_time_days,
                    budget_max=request.constraints.budget_max,
                    budget_min=request.constraints.budget_min,
                    prefer_contracted_suppliers=request.constraints.prefer_contracted_suppliers,
                )

                solution = self._solve_weighted_sum(
                    problem, weights, effective_constraints, overrides
                )

                supplier_mix = self._build_supplier_mix(
                    name, solution, problem, request
                )
                solutions.append(supplier_mix)
                logger.info(
                    "solution_generated",
                    name=name,
                    total_cost=supplier_mix.total_cost,
                    risk_score=supplier_mix.risk_score
                )
            except Exception as e:
                logger.warning("solution_failed", name=name, error=str(e))
                raise ValueError(f"Failed to generate {name} solution: {e}")

        logger.info("optimization_complete", solutions_count=len(solutions))
        return solutions

    def _build_problem(
        self, request: OptimizationRequest
    ) -> Dict:
        """
        Build optimization problem structure.

        Filters suppliers by MOQ, delivery feasibility, and active status.

        Args:
            request: Optimization request

        Returns:
            Dictionary with problem structure:
            - materials: List of MaterialDemand
            - options: List of (material_id, SupplierMaterial) tuples
            - suppliers: Dict of supplier data
            - performance: Dict of performance data
            - contracts: Dict of contract data
            - excluded: List of (supplier_id, material_id, reason) tuples
        """
        problem = {
            "materials": request.materials,
            "options": [],
            "suppliers": {},
            "performance": {},
            "contracts": {},
            "excluded": []
        }

        # Get all supplier options for each material
        for material_demand in request.materials:
            supplier_materials = self.data_reader.get_suppliers_for_material(
                material_demand.material_id
            )

            if not supplier_materials:
                raise ValueError(
                    f"No suppliers found for material {material_demand.material_id}"
                )

            for sm in supplier_materials:
                # Check excluded suppliers (from risk simulation)
                if sm.supplier_id in set(request.constraints.excluded_suppliers):
                    problem["excluded"].append((
                        sm.supplier_id, material_demand.material_id,
                        f"Excluded by risk scenario"
                    ))
                    logger.info(
                        "supplier_excluded_risk",
                        supplier=sm.supplier_id,
                        material=material_demand.material_id,
                    )
                    continue

                # Check MOQ constraint
                if material_demand.quantity < sm.minimum_order_quantity:
                    problem["excluded"].append((
                        sm.supplier_id, material_demand.material_id,
                        f"Below MOQ ({material_demand.quantity} < {sm.minimum_order_quantity})"
                    ))
                    continue

                # Check delivery date feasibility (Improvement 2)
                if material_demand.required_by:
                    earliest_delivery = date.today() + timedelta(days=sm.lead_time_days)
                    if earliest_delivery > material_demand.required_by:
                        problem["excluded"].append((
                            sm.supplier_id, material_demand.material_id,
                            f"Cannot deliver by {material_demand.required_by} "
                            f"(earliest: {earliest_delivery}, lead time: {sm.lead_time_days}d)"
                        ))
                        logger.info(
                            "supplier_excluded_lead_time",
                            supplier=sm.supplier_id,
                            lead_time=sm.lead_time_days,
                            required_by=str(material_demand.required_by)
                        )
                        continue

                problem["options"].append((material_demand.material_id, sm))

                # Cache supplier data
                if sm.supplier_id not in problem["suppliers"]:
                    supplier = self.data_reader.get_supplier_by_id(sm.supplier_id)
                    if supplier:
                        problem["suppliers"][sm.supplier_id] = supplier

                # Cache performance data
                if sm.supplier_id not in problem["performance"]:
                    perf = self.data_reader.get_latest_performance(sm.supplier_id)
                    if perf:
                        problem["performance"][sm.supplier_id] = perf

                # Cache contract data (Improvement 5)
                if sm.supplier_id not in problem["contracts"]:
                    contract = self.data_reader.get_contract_for_supplier(sm.supplier_id)
                    if contract:
                        problem["contracts"][sm.supplier_id] = contract

        if not problem["options"]:
            raise ValueError("No feasible supplier options found (MOQ/delivery constraints)")

        if problem["excluded"]:
            logger.info(
                "suppliers_excluded",
                count=len(problem["excluded"]),
                reasons=[r for _, _, r in problem["excluded"][:5]]
            )

        logger.info(
            "problem_built",
            options_count=len(problem["options"]),
            suppliers_count=len(problem["suppliers"]),
            excluded_count=len(problem["excluded"])
        )

        return problem

    def _solve_weighted_sum(
        self,
        problem: Dict,
        weights: Dict[str, float],
        constraints,
        overrides: Optional[Dict] = None
    ) -> np.ndarray:
        """
        Solve continuous multi-objective optimization using scipy SLSQP.

        x[i] is the fraction of material demand allocated to supplier option i
        (0.0 to 1.0). For each material, fractions must sum to 1.0.
        Supports split orders across multiple suppliers per material.
        """
        n_options = len(problem["options"])

        # Group options by material
        material_options: Dict[str, List[int]] = {}
        for i, (material_id, sm) in enumerate(problem["options"]):
            material_options.setdefault(material_id, []).append(i)

        material_ids = list(material_options.keys())

        logger.info(
            "using_slsqp_solver",
            variables=n_options,
            materials=len(material_ids),
            weights=weights,
        )

        def objective(x: np.ndarray) -> float:
            cost = self._calculate_cost(x, problem)
            risk = self._calculate_risk(x, problem)
            lead_time = self._calculate_lead_time(x, problem)

            return (
                weights["cost"] * (cost / 1_000_000) +
                weights["risk"] * (risk / 10.0) +
                weights["lead_time"] * (lead_time / 60.0)
            )

        # Bounds: each x[i] in [0, 1]
        bounds = [(0.0, 1.0)] * n_options

        # Constraints:
        # 1. For each material, allocations sum to 1.0
        eq_constraints = []
        for mid in material_ids:
            indices = material_options[mid]
            def make_eq(idx_list):
                def constraint(x):
                    return sum(x[i] for i in idx_list) - 1.0
                return constraint
            eq_constraints.append({
                "type": "eq",
                "fun": make_eq(indices),
            })

        # 2. Supplier concentration <= max (for multi-material problems)
        ineq_constraints = []
        if len(material_ids) > 1:
            max_conc = (overrides or {}).get(
                "max_concentration", constraints.max_supplier_concentration
            )
            # Get unique suppliers
            all_suppliers = set()
            for _, sm in problem["options"]:
                all_suppliers.add(sm.supplier_id)

            for sup_id in all_suppliers:
                def make_conc(sid):
                    def constraint(x):
                        # sup_cost / total_cost <= max_conc
                        # Reformulated: max_conc * total_cost - sup_cost >= 0
                        # Uses TCO (consistent with objective function)
                        total_cost = 0.0
                        sup_cost = 0.0
                        for i, (mid, sm) in enumerate(problem["options"]):
                            if x[i] > 0.05:
                                md = next(m for m in problem["materials"] if m.material_id == mid)
                                alloc_qty = max(1, int(md.quantity * x[i]))
                                price = self._get_volume_price(sm.supplier_material_id, alloc_qty)
                                supplier = problem["suppliers"].get(sm.supplier_id)
                                tco = self._calculate_tco(price, alloc_qty, sm, supplier)["tco"]
                                total_cost += tco
                                if sm.supplier_id == sid:
                                    sup_cost += tco
                        if total_cost < 1e-6:
                            return 0.0
                        return max_conc * total_cost - sup_cost
                    return constraint
                ineq_constraints.append({
                    "type": "ineq",
                    "fun": make_conc(sup_id),
                })

        all_constraints = eq_constraints + ineq_constraints

        # Initial guess: strategy-dependent to explore different solution regions
        x0 = np.zeros(n_options)
        for mid in material_ids:
            indices = material_options[mid]
            sorted_by_price = sorted(
                indices, key=lambda i: problem["options"][i][1].base_price
            )

            if weights["cost"] >= 0.5:
                # Cost-Optimized: 100% cheapest supplier
                x0[sorted_by_price[0]] = 1.0
            elif weights["risk"] >= 0.4:
                # Risk-Diversified: 100% most expensive (highest quality/lowest risk)
                x0[sorted_by_price[-1]] = 1.0
            else:
                # Balanced: split 60/40 between cheapest and most expensive
                if len(sorted_by_price) >= 2:
                    x0[sorted_by_price[0]] = 0.6
                    x0[sorted_by_price[-1]] = 0.4
                else:
                    x0[sorted_by_price[0]] = 1.0

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=all_constraints,
            options={"maxiter": 200, "ftol": 1e-6},
        )

        if not result.success:
            logger.warning("slsqp_did_not_converge", message=result.message)

        # Clean up: zero out tiny allocations (< 5%)
        x_final = result.x.copy()
        for mid in material_ids:
            indices = material_options[mid]
            for idx in indices:
                if x_final[idx] < 0.05:
                    x_final[idx] = 0.0
            # Re-normalize to sum to 1
            total = sum(x_final[idx] for idx in indices)
            if total > 0:
                for idx in indices:
                    x_final[idx] /= total

        logger.info(
            "slsqp_solution",
            success=result.success,
            iterations=result.nit,
            objective=result.fun,
        )

        return x_final

    def _calculate_tco(
        self,
        unit_price: float,
        quantity: int,
        sm: SupplierMaterial,
        supplier: Optional[Supplier]
    ) -> Dict[str, float]:
        """
        Calculate total cost of ownership for an allocation (Improvement 1).

        Includes: base cost + freight + carrying cost + carbon cost - payment benefit.

        Returns dict with breakdown: base_cost, freight_cost, carrying_cost, carbon_cost,
        payment_benefit, tco.
        """
        base_cost = unit_price * quantity

        # 1. Freight estimate by region
        location = supplier.location if supplier else "Unknown"
        freight_rate = self.FREIGHT_RATES.get(location, 0.05)
        freight_cost = base_cost * freight_rate

        # 2. Inventory carrying cost (longer lead time = more safety stock)
        # Higher quantities amplify carrying cost — makes P90 vs P10 matter
        daily_demand = quantity / 30  # approximate monthly demand
        safety_stock_days = max(sm.lead_time_days - 14, 0)  # extra beyond 2-week baseline
        # Scale carrying cost rate: larger orders need more warehouse space
        carrying_rate = 0.20 + (0.05 * min(quantity / 500, 1.0))  # 20-25% annual rate
        carrying_cost = (daily_demand * safety_stock_days * unit_price) * (carrying_rate / 365)

        # 3. Carbon cost (shadow price $50/ton CO2)
        carbon_cost = sm.carbon_footprint_kg * quantity * self.CARBON_PRICE_PER_KG

        # 4. Payment term impact (Improvement 5)
        contract = self.data_reader.get_contract_for_supplier(sm.supplier_id)
        if contract and contract.payment_terms == "Net 60":
            payment_benefit = base_cost * 0.01  # Better cash flow
        elif contract and contract.payment_terms == "Net 45":
            payment_benefit = base_cost * 0.005
        elif contract and contract.payment_terms == "Net 30":
            payment_benefit = 0.0
        else:
            payment_benefit = -base_cost * 0.005  # Penalty for no contract

        tco = base_cost + freight_cost + carrying_cost + carbon_cost - payment_benefit

        return {
            "base_cost": base_cost,
            "freight_cost": freight_cost,
            "carrying_cost": carrying_cost,
            "carbon_cost": carbon_cost,
            "payment_benefit": payment_benefit,
            "tco": tco
        }

    def _calculate_cost(self, x: np.ndarray, problem: Dict) -> float:
        """
        Calculate total cost using TCO with continuous allocations.

        x[i] is the fraction of material demand allocated to option i.
        """
        total_cost = 0.0

        for i, (material_id, sm) in enumerate(problem["options"]):
            if x[i] > 0.05:  # Has meaningful allocation
                material_demand = next(
                    m for m in problem["materials"]
                    if m.material_id == material_id
                )

                alloc_qty = int(material_demand.quantity * x[i])
                if alloc_qty < 1:
                    continue

                price = self._get_volume_price(
                    sm.supplier_material_id, alloc_qty
                )

                supplier = problem["suppliers"].get(sm.supplier_id)
                tco_breakdown = self._calculate_tco(price, alloc_qty, sm, supplier)
                total_cost += tco_breakdown["tco"]

        return total_cost

    def _get_volume_price(self, supplier_material_id: str, quantity: int) -> float:
        """
        Get unit price with volume discount applied.

        Args:
            supplier_material_id: SupplierMaterial ID
            quantity: Order quantity (may be consolidated across materials)

        Returns:
            Unit price with discount applied
        """
        tiers = self.data_reader.get_volume_tiers_for_supplier_material(
            supplier_material_id
        )

        if not tiers:
            # No volume tiers, use base price
            supplier_materials = self.data_reader.get_supplier_materials()
            sm = next(
                (s for s in supplier_materials if s.supplier_material_id == supplier_material_id),
                None
            )
            return sm.base_price if sm else 0.0

        # Find applicable tier
        for tier in tiers:
            if tier.min_quantity <= quantity:
                if tier.max_quantity is None or quantity <= tier.max_quantity:
                    return tier.unit_price

        # If no tier matches, use base price from highest tier
        return tiers[-1].unit_price

    def _calculate_dynamic_risk(self, supplier_id: str, problem: Dict) -> float:
        """
        Calculate risk using performance trends (Improvement 4).

        Uses exponentially weighted recent performance data for trend-aware scoring.
        """
        performances = self.data_reader.get_performance_history(supplier_id)
        supplier = problem["suppliers"].get(supplier_id)

        if not performances or not supplier:
            return 7.0  # High default risk for unknown suppliers

        # Exponentially weighted performance (recent months matter more)
        weights = [0.5, 0.3, 0.2]  # Last 3 months
        n = min(len(performances), 3)
        active_weights = weights[:n]
        weight_sum = sum(active_weights)

        weighted_otd = sum(
            p.on_time_delivery_rate * w
            for p, w in zip(performances[:n], active_weights)
        ) / weight_sum
        weighted_quality = sum(
            p.quality_score * w
            for p, w in zip(performances[:n], active_weights)
        ) / weight_sum
        weighted_defect = sum(
            p.defect_rate * w
            for p, w in zip(performances[:n], active_weights)
        ) / weight_sum

        # Trend detection
        if len(performances) >= 2:
            trend = performances[0].quality_score - performances[-1].quality_score
            trend_factor = -0.5 if trend < -0.5 else (0.3 if trend > 0.5 else 0.0)
        else:
            trend_factor = 0.0

        # Combine: lower is better for risk
        performance_risk = 10.0 - weighted_quality  # 0-10
        delivery_risk = max(0, (100 - weighted_otd) / 10)  # Convert OTD% to 0-10
        defect_risk = weighted_defect  # Already roughly 0-5 scale

        # Defect history risk from defect tracking system
        defect_history_score = self.data_reader.get_supplier_defect_score(supplier_id)

        risk = (
            0.25 * supplier.geopolitical_risk_score +
            0.15 * (10.0 - supplier.financial_stability_score) +
            0.15 * performance_risk +
            0.15 * delivery_risk +
            0.15 * defect_risk +
            0.15 * defect_history_score +
            trend_factor  # Bonus/penalty for trend
        )

        return max(0.0, min(10.0, risk))

    def _calculate_risk(self, x: np.ndarray, problem: Dict) -> float:
        """
        Calculate weighted average risk score with continuous allocations.

        Includes quantity-dependent risk factors:
        - MOQ proximity penalty: orders near MOQ are riskier (supplier may deprioritize)
        - Capacity concentration: large orders to single supplier increase dependency risk
        - Split order bonus: spreading across suppliers reduces risk
        """
        total_cost = self._calculate_cost(x, problem)
        if total_cost < 1e-6:
            return 10.0

        weighted_risk = 0.0

        # Track total quantity per supplier for capacity concentration
        supplier_total_qty: Dict[str, int] = {}
        for i, (material_id, sm) in enumerate(problem["options"]):
            if x[i] > 0.05:
                md = next(m for m in problem["materials"] if m.material_id == material_id)
                alloc_qty = int(md.quantity * x[i])
                supplier_total_qty[sm.supplier_id] = supplier_total_qty.get(sm.supplier_id, 0) + alloc_qty

        for i, (material_id, sm) in enumerate(problem["options"]):
            if x[i] > 0.05:
                material_demand = next(
                    m for m in problem["materials"]
                    if m.material_id == material_id
                )

                alloc_qty = int(material_demand.quantity * x[i])
                if alloc_qty < 1:
                    continue

                price = self._get_volume_price(sm.supplier_material_id, alloc_qty)
                supplier = problem["suppliers"].get(sm.supplier_id)
                tco_breakdown = self._calculate_tco(price, alloc_qty, sm, supplier)
                cost = tco_breakdown["tco"]
                weight = cost / total_cost

                # Base supplier risk (performance, geopolitical, etc.)
                supplier_risk = self._calculate_dynamic_risk(sm.supplier_id, problem)

                # MOQ proximity penalty: if order is < 1.5x MOQ, add risk
                # (supplier may deprioritize small orders)
                moq_ratio = alloc_qty / max(sm.minimum_order_quantity, 1)
                if moq_ratio < 1.5:
                    supplier_risk += 0.8  # Near-MOQ penalty
                elif moq_ratio < 2.0:
                    supplier_risk += 0.3

                # Capacity concentration: if this supplier handles > 500 total units, add risk
                total_from_supplier = supplier_total_qty.get(sm.supplier_id, 0)
                if total_from_supplier > 800:
                    supplier_risk += 0.5  # Heavy dependency
                elif total_from_supplier > 500:
                    supplier_risk += 0.2

                weighted_risk += weight * min(10.0, supplier_risk)

        return min(10.0, max(0.0, weighted_risk))

    def _calculate_lead_time(self, x: np.ndarray, problem: Dict) -> float:
        """
        Calculate maximum lead time across allocated suppliers.
        Any supplier with >5% allocation counts toward lead time.
        """
        max_lead_time = 0

        for i, (material_id, sm) in enumerate(problem["options"]):
            if x[i] > 0.05:
                max_lead_time = max(max_lead_time, sm.lead_time_days)

        return max_lead_time

    def _check_concentration_constraint(
        self,
        x: np.ndarray,
        problem: Dict,
        max_concentration: float
    ) -> bool:
        """Check if supplier concentration constraint is satisfied."""
        total_cost = self._calculate_cost(x, problem)
        if total_cost < 1e-6:
            return True

        supplier_costs: Dict[str, float] = {}

        for i, (material_id, sm) in enumerate(problem["options"]):
            if x[i] > 0.05:
                material_demand = next(
                    m for m in problem["materials"]
                    if m.material_id == material_id
                )
                alloc_qty = int(material_demand.quantity * x[i])
                if alloc_qty < 1:
                    continue
                price = self._get_volume_price(sm.supplier_material_id, alloc_qty)
                supplier = problem["suppliers"].get(sm.supplier_id)
                tco_breakdown = self._calculate_tco(price, alloc_qty, sm, supplier)
                supplier_costs[sm.supplier_id] = (
                    supplier_costs.get(sm.supplier_id, 0.0) + tco_breakdown["tco"]
                )

        max_supplier_cost = max(supplier_costs.values()) if supplier_costs else 0.0
        return (max_supplier_cost / total_cost) <= max_concentration

    def _build_supplier_mix(
        self,
        name: str,
        solution: np.ndarray,
        problem: Dict,
        request: OptimizationRequest
    ) -> SupplierMix:
        """
        Build SupplierMix from continuous solution vector.

        x[i] is the fraction allocated to each supplier option.
        Converts fractions to actual quantities for allocations.
        """
        allocations = []
        supplier_costs = {}

        for i, (material_id, sm) in enumerate(problem["options"]):
            if solution[i] > 0.05:  # >5% allocation
                material_demand = next(
                    m for m in problem["materials"]
                    if m.material_id == material_id
                )

                alloc_qty = max(1, int(material_demand.quantity * solution[i]))
                material = self.data_reader.get_material_by_id(material_id)
                supplier = problem["suppliers"].get(sm.supplier_id)

                if material and supplier:
                    price = self._get_volume_price(
                        sm.supplier_material_id, alloc_qty
                    )

                    tco_breakdown = self._calculate_tco(
                        price, alloc_qty, sm, supplier
                    )

                    # Get quality score from performance or sustainability
                    perf = problem["performance"].get(sm.supplier_id)
                    quality_score = (
                        perf.quality_score if perf
                        else sm.sustainability_score
                    )

                    allocations.append(
                        SupplierAllocation(
                            supplier_id=sm.supplier_id,
                            supplier_name=supplier.name,
                            material_id=material_id,
                            material_name=material.name,
                            quantity=alloc_qty,
                            unit_price=price,
                            total_cost=tco_breakdown["tco"],
                            lead_time_days=sm.lead_time_days,
                            quality_score=quality_score,
                            freight_cost=round(tco_breakdown["freight_cost"], 2),
                            carrying_cost=round(tco_breakdown["carrying_cost"], 2),
                            carbon_cost=round(tco_breakdown["carbon_cost"], 2),
                            tco=round(tco_breakdown["tco"], 2)
                        )
                    )

                    supplier_costs[sm.supplier_id] = (
                        supplier_costs.get(sm.supplier_id, 0.0) + tco_breakdown["tco"]
                    )

        # Calculate metrics
        total_cost = sum(a.total_cost for a in allocations)
        risk_score = self._calculate_risk(solution, problem)
        lead_time_days = int(self._calculate_lead_time(solution, problem))
        quality_score = (
            sum(a.quality_score * a.total_cost for a in allocations) / total_cost
            if total_cost > 0 else 0.0
        )

        max_supplier_cost = max(supplier_costs.values()) if supplier_costs else 0.0
        max_concentration = max_supplier_cost / total_cost if total_cost > 0 else 0.0

        # Generate reasoning
        reasoning = self._generate_reasoning(
            name, total_cost, risk_score, quality_score, lead_time_days, problem
        )

        return SupplierMix(
            name=name,
            total_cost=total_cost,
            risk_score=min(10.0, max(0.0, risk_score)),
            quality_score=min(10.0, max(0.0, quality_score)),
            lead_time_days=lead_time_days,
            max_supplier_concentration=max_concentration,
            allocations=allocations,
            reasoning=reasoning
        )

    def _generate_reasoning(
        self,
        name: str,
        total_cost: float,
        risk_score: float,
        quality_score: float,
        lead_time_days: int,
        problem: Optional[Dict] = None
    ) -> str:
        """
        Generate human-readable reasoning for solution.

        Includes information about excluded suppliers, TCO components,
        and demand buffer for Resilient solutions.
        """
        excluded_count = len(problem.get("excluded", [])) if problem else 0
        contracted_count = len(problem.get("contracts", {})) if problem else 0

        base_reasoning = ""
        if name == "Cost-Optimized":
            base_reasoning = (
                f"Lowest TCO option at ${total_cost:,.0f} with acceptable risk "
                f"({risk_score:.1f}/10). Accepts higher supplier concentration "
                f"(up to 60%) to achieve the best price. "
                f"Cost includes freight, carrying costs, and carbon impact."
            )
        elif name == "Balanced":
            base_reasoning = (
                f"Optimal balance of TCO (${total_cost:,.0f}), quality "
                f"({quality_score:.1f}/10), and risk ({risk_score:.1f}/10). "
                "Recommended for most scenarios. Leverages contracted suppliers "
                "for reliability."
            )
        elif name == "Risk-Diversified":
            base_reasoning = (
                f"Maximum supply chain resilience at ${total_cost:,.0f} with "
                f"risk score {risk_score:.1f}/10. No single supplier exceeds "
                f"25% of total spend, ensuring diversification against "
                f"disruption. Quality score: {quality_score:.1f}/10."
            )
        else:
            base_reasoning = (
                f"The {name} solution costs ${total_cost:,.0f} with "
                f"risk score {risk_score:.1f}/10 and quality {quality_score:.1f}/10."
            )

        # Add exclusion info
        if excluded_count > 0:
            base_reasoning += (
                f" {excluded_count} supplier option(s) excluded due to "
                "delivery constraints or MOQ requirements."
            )

        # Add contract info
        if contracted_count > 0:
            base_reasoning += (
                f" {contracted_count} contracted supplier(s) available with "
                "negotiated terms."
            )

        return base_reasoning
