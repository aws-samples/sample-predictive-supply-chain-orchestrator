"""
Explainability tool for Bedrock agent.

Lambda function that generates human-readable explanations for
optimization decisions.

Invoked as an AgentCore Gateway MCP target — returns a raw dict (the
Gateway serializes the return value directly as the MCP tool result).
Errors are raised so the Gateway marks the tool call as failed.

Follows CDE standards:
- Type hints on all functions
- Error handling and validation
- Structured logging
"""

from typing import Dict, Any
import structlog

logger = structlog.get_logger()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for explainability tool.

    Args:
        event: Lambda event with solution to explain
        context: Lambda context

    Returns:
        Dict with the explanation and solution_name.

    Expected event structure:
    {
        "solution_name": "Balanced",
        "total_cost": 875000,
        "risk_score": 3.5,
        "quality_score": 8.2,
        "allocations": [...]
    }
    """
    logger.info(
        "explainability_tool_invoked",
        request_id=context.aws_request_id if context else "local"
    )

    # Validate input
    solution_name = event.get("solution_name")
    if not solution_name:
        raise ValueError("solution_name is required")

    total_cost = event.get("total_cost", 0)
    risk_score = event.get("risk_score", 0)
    quality_score = event.get("quality_score", 0)
    allocations = event.get("allocations", [])

    # Generate explanation
    explanation = _generate_explanation(
        solution_name,
        total_cost,
        risk_score,
        quality_score,
        allocations
    )

    logger.info(
        "explanation_generated",
        solution_name=solution_name,
        request_id=context.aws_request_id if context else "local"
    )

    return {
        "explanation": explanation,
        "solution_name": solution_name,
    }


def _generate_explanation(
    solution_name: str,
    total_cost: float,
    risk_score: float,
    quality_score: float,
    allocations: list
) -> str:
    """
    Generate human-readable explanation.

    Args:
        solution_name: Name of solution. The optimization engine emits
            Cost-Optimized, Balanced, and Risk-Diversified; legacy names
            (Budget, Premium, Resilient) are also accepted as aliases.
        total_cost: Total cost in USD
        risk_score: Risk score (0-10)
        quality_score: Quality score (0-10)
        allocations: List of supplier allocations

    Returns:
        Human-readable explanation text
    """
    # Count unique suppliers
    unique_suppliers = len(set(
        alloc.get("supplier_id") for alloc in allocations
    ))

    # Calculate TCO breakdown if available
    total_freight = sum(alloc.get("freight_cost", 0) for alloc in allocations)
    total_carbon = sum(alloc.get("carbon_cost", 0) for alloc in allocations)
    total_carrying = sum(alloc.get("carrying_cost", 0) for alloc in allocations)
    has_tco = total_freight > 0 or total_carbon > 0 or total_carrying > 0

    # Normalize strategy name: engine emits Cost-Optimized / Balanced /
    # Risk-Diversified; map legacy aliases to the same buckets.
    normalized = solution_name.lower().replace("-", "").replace("_", "").replace(" ", "")
    cost_aliases = {"costoptimized", "budget", "cost"}
    quality_aliases = {"riskdiversified", "premium", "risk"}

    # Generate explanation based on solution characteristics
    if normalized in cost_aliases:
        explanation = (
            f"The {solution_name} solution prioritizes cost minimization at ${total_cost:,.0f}. "
            f"This option uses {unique_suppliers} supplier(s) and accepts higher risk "
            f"(score: {risk_score:.1f}/10) in exchange for lower costs. "
            f"Quality score is {quality_score:.1f}/10. "
            f"Best for: Budget-conscious procurement where cost is the primary driver."
        )

    elif normalized == "balanced":
        explanation = (
            f"The {solution_name} solution offers optimal balance at ${total_cost:,.0f}. "
            f"This option distributes orders across {unique_suppliers} supplier(s) to achieve "
            f"moderate risk (score: {risk_score:.1f}/10) and good quality (score: {quality_score:.1f}/10). "
            f"Best for: Most procurement scenarios requiring balanced trade-offs."
        )

    elif normalized in quality_aliases:
        explanation = (
            f"The {solution_name} solution maximizes quality and minimizes risk at ${total_cost:,.0f}. "
            f"This option uses {unique_suppliers} high-quality supplier(s) with excellent ratings. "
            f"Risk is minimized (score: {risk_score:.1f}/10) and quality is maximized (score: {quality_score:.1f}/10). "
            f"Best for: Critical production where supply chain reliability is paramount."
        )

    elif normalized == "resilient":
        explanation = (
            f"The {solution_name} solution optimizes for demand uncertainty at ${total_cost:,.0f}. "
            f"Quantities are adjusted upward based on demand forecast confidence intervals "
            f"to handle demand surges without supply disruption. "
            f"Uses {unique_suppliers} supplier(s) with risk score {risk_score:.1f}/10 "
            f"and quality score {quality_score:.1f}/10. "
            f"Best for: Volatile demand environments or critical components where "
            f"stockouts are unacceptable."
        )

    else:
        explanation = (
            f"The {solution_name} solution costs ${total_cost:,.0f} with "
            f"{unique_suppliers} supplier(s). Risk score: {risk_score:.1f}/10, "
            f"Quality score: {quality_score:.1f}/10."
        )

    # Add TCO breakdown insight
    if has_tco:
        explanation += (
            f" Total Cost of Ownership includes ${total_freight:,.0f} in freight, "
            f"${total_carrying:,.0f} in carrying costs, and ${total_carbon:,.0f} in "
            f"carbon impact costs."
        )

    # Add supplier diversity insight
    if unique_suppliers > 1:
        explanation += (
            f" Supplier diversification across {unique_suppliers} sources reduces "
            f"concentration risk and improves supply chain resilience."
        )

    return explanation
