"""
Evaluation suite for the procurement optimization agent.

Measures agent quality across:
- Task completion: Does the agent complete the requested task?
- Accuracy: Are optimization results mathematically correct?
- Tool selection: Does the agent pick the right tools?
- Response quality: Are explanations clear and actionable?
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class EvalCase:
    """A single evaluation test case."""
    name: str
    prompt: str
    expected_tools: List[str]
    validators: List[str]
    tags: List[str] = field(default_factory=list)
    max_turns: int = 5
    timeout_seconds: int = 60


@dataclass
class EvalResult:
    """Result of running a single evaluation case."""
    case_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    duration_ms: int
    tools_invoked: List[str]
    checks: Dict[str, bool]
    response_text: str = ""
    error: Optional[str] = None


# Evaluation test cases
EVAL_CASES: List[EvalCase] = [
    # Task completion: basic optimization
    EvalCase(
        name="basic_optimization",
        prompt="Optimize procurement for 500 battery packs (MAT-BAT-001)",
        expected_tools=["optimize_suppliers"],
        validators=["has_solutions", "has_allocations", "cost_positive"],
        tags=["task_completion", "optimization"],
    ),
    # Task completion: multi-material optimization
    EvalCase(
        name="multi_material_optimization",
        prompt=(
            "Optimize procurement for 500 battery packs (MAT-BAT-001) "
            "and 500 motor assemblies (MAT-MOT-001) with a budget cap of $800,000"
        ),
        expected_tools=["optimize_suppliers"],
        validators=["has_solutions", "has_allocations", "budget_respected"],
        tags=["task_completion", "optimization", "constraints"],
    ),
    # Tool selection: data query
    EvalCase(
        name="supplier_query",
        prompt="Find alternative suppliers for battery packs",
        expected_tools=["query_supplier_data"],
        validators=["has_suppliers"],
        tags=["tool_selection", "data_access"],
    ),
    # Tool selection: explanation
    EvalCase(
        name="solution_explanation",
        prompt="Optimize for 500 battery packs and explain the Balanced solution",
        expected_tools=["optimize_suppliers", "explain_solution"],
        validators=["has_explanation"],
        tags=["tool_selection", "explainability"],
    ),
    # Accuracy: constraint enforcement
    EvalCase(
        name="concentration_constraint",
        prompt=(
            "Optimize for 1000 battery packs with max supplier concentration of 30%"
        ),
        expected_tools=["optimize_suppliers"],
        validators=["has_solutions", "concentration_respected"],
        tags=["accuracy", "constraints"],
    ),
    # Accuracy: lead time constraint
    EvalCase(
        name="lead_time_constraint",
        prompt=(
            "Optimize for 500 battery packs with maximum lead time of 20 days"
        ),
        expected_tools=["optimize_suppliers"],
        validators=["has_solutions", "lead_time_respected"],
        tags=["accuracy", "constraints"],
    ),
    # Response quality: actionable recommendation
    EvalCase(
        name="actionable_recommendation",
        prompt="Which supplier mix should I choose for 500 battery packs and why?",
        expected_tools=["optimize_suppliers"],
        validators=["has_recommendation", "has_reasoning"],
        tags=["response_quality"],
    ),
    # Edge case: unknown material
    EvalCase(
        name="unknown_material_handling",
        prompt="Optimize procurement for 100 units of MAT-XYZ-999",
        expected_tools=["optimize_suppliers"],
        validators=["handles_error_gracefully"],
        tags=["edge_case", "error_handling"],
    ),
    # Multi-step: optimize then create PRs
    EvalCase(
        name="optimize_and_create_prs",
        prompt="Optimize for 500 battery packs, pick the Balanced solution, and create purchase requisitions",
        expected_tools=["optimize_suppliers", "create_purchase_requisitions"],
        validators=["has_solutions", "has_prs"],
        tags=["task_completion", "multi_step"],
        max_turns=8,
    ),
    # Supplier network exploration
    EvalCase(
        name="supplier_network_query",
        prompt="Show me the supplier network for SUP-001 and find alternatives for their materials",
        expected_tools=["query_supplier_data"],
        validators=["has_network_data"],
        tags=["tool_selection", "data_access"],
    ),
]


class Validators:
    """Validation functions for evaluation results."""

    @staticmethod
    def has_solutions(response: Dict[str, Any]) -> bool:
        """Check that optimization returned at least one solution."""
        solutions = response.get("solutions", [])
        return len(solutions) > 0

    @staticmethod
    def has_allocations(response: Dict[str, Any]) -> bool:
        """Check that solutions contain supplier allocations."""
        solutions = response.get("solutions", [])
        return any(len(s.get("allocations", [])) > 0 for s in solutions)

    @staticmethod
    def cost_positive(response: Dict[str, Any]) -> bool:
        """Check that all solution costs are positive."""
        solutions = response.get("solutions", [])
        return all(s.get("total_cost", 0) > 0 for s in solutions)

    @staticmethod
    def budget_respected(response: Dict[str, Any]) -> bool:
        """Check that budget constraint was respected."""
        solutions = response.get("solutions", [])
        budget_max = response.get("constraints", {}).get("budget_max", float("inf"))
        return all(s.get("total_cost", 0) <= budget_max for s in solutions)

    @staticmethod
    def concentration_respected(response: Dict[str, Any]) -> bool:
        """Check that supplier concentration constraint was respected."""
        solutions = response.get("solutions", [])
        max_conc = response.get("constraints", {}).get("max_supplier_concentration", 1.0)
        for sol in solutions:
            if sol.get("max_supplier_concentration", 0) > max_conc + 0.01:
                return False
        return True

    @staticmethod
    def lead_time_respected(response: Dict[str, Any]) -> bool:
        """Check that lead time constraint was respected."""
        solutions = response.get("solutions", [])
        max_lt = response.get("constraints", {}).get("max_lead_time_days", 365)
        for sol in solutions:
            if sol.get("lead_time_days", 0) > max_lt:
                return False
        return True

    @staticmethod
    def has_suppliers(response: Dict[str, Any]) -> bool:
        """Check that supplier data was returned."""
        return len(response.get("alternative_suppliers", response.get("suppliers", []))) > 0

    @staticmethod
    def has_explanation(response: Dict[str, Any]) -> bool:
        """Check that an explanation was generated."""
        explanation = response.get("explanation", "")
        return len(explanation) > 50

    @staticmethod
    def has_recommendation(response: Dict[str, Any]) -> bool:
        """Check that a recommendation was included."""
        text = response.get("response_text", "")
        recommendation_keywords = ["recommend", "suggest", "best", "should", "choose"]
        return any(kw in text.lower() for kw in recommendation_keywords)

    @staticmethod
    def has_reasoning(response: Dict[str, Any]) -> bool:
        """Check that reasoning was provided."""
        text = response.get("response_text", "")
        reasoning_keywords = ["because", "since", "due to", "trade-off", "balance"]
        return any(kw in text.lower() for kw in reasoning_keywords)

    @staticmethod
    def handles_error_gracefully(response: Dict[str, Any]) -> bool:
        """Check that errors are handled without crashing."""
        return response.get("status") != "crash"

    @staticmethod
    def has_prs(response: Dict[str, Any]) -> bool:
        """Check that purchase requisitions were created."""
        prs = response.get("purchase_requisitions", [])
        return len(prs) > 0

    @staticmethod
    def has_network_data(response: Dict[str, Any]) -> bool:
        """Check that network graph data was returned."""
        return response.get("nodes") is not None or response.get("suppliers") is not None


# Validator registry
VALIDATOR_REGISTRY = {
    "has_solutions": Validators.has_solutions,
    "has_allocations": Validators.has_allocations,
    "cost_positive": Validators.cost_positive,
    "budget_respected": Validators.budget_respected,
    "concentration_respected": Validators.concentration_respected,
    "lead_time_respected": Validators.lead_time_respected,
    "has_suppliers": Validators.has_suppliers,
    "has_explanation": Validators.has_explanation,
    "has_recommendation": Validators.has_recommendation,
    "has_reasoning": Validators.has_reasoning,
    "handles_error_gracefully": Validators.handles_error_gracefully,
    "has_prs": Validators.has_prs,
    "has_network_data": Validators.has_network_data,
}


def run_eval_case(
    case: EvalCase,
    invoke_fn,
) -> EvalResult:
    """
    Run a single evaluation case against the agent.

    Args:
        case: The evaluation case to run
        invoke_fn: Function that takes a prompt string and returns
                   a dict with 'response_text', 'tools_invoked', and tool output data

    Returns:
        EvalResult with pass/fail, score, and detailed checks
    """
    start = time.time()

    try:
        result = invoke_fn(case.prompt)
        duration_ms = int((time.time() - start) * 1000)

        tools_invoked = result.get("tools_invoked", [])
        response_text = result.get("response_text", "")

        # Check tool selection
        tool_check = all(
            tool in tools_invoked for tool in case.expected_tools
        )

        # Run validators
        checks = {"correct_tools": tool_check}
        for validator_name in case.validators:
            validator_fn = VALIDATOR_REGISTRY.get(validator_name)
            if validator_fn:
                checks[validator_name] = validator_fn(result)
            else:
                checks[validator_name] = False

        # Score: fraction of checks that passed
        passed_count = sum(1 for v in checks.values() if v)
        score = passed_count / len(checks) if checks else 0.0
        passed = all(checks.values())

        logger.info(
            "eval_case_complete",
            case=case.name,
            passed=passed,
            score=score,
            duration_ms=duration_ms,
            checks=checks,
        )

        return EvalResult(
            case_name=case.name,
            passed=passed,
            score=score,
            duration_ms=duration_ms,
            tools_invoked=tools_invoked,
            checks=checks,
            response_text=response_text,
        )

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("eval_case_error", case=case.name, error=str(e))
        return EvalResult(
            case_name=case.name,
            passed=False,
            score=0.0,
            duration_ms=duration_ms,
            tools_invoked=[],
            checks={},
            error=str(e),
        )


def run_eval_suite(
    invoke_fn,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run the full evaluation suite or a subset filtered by tags.

    Args:
        invoke_fn: Function that takes a prompt and returns agent response dict
        tags: Optional list of tags to filter test cases

    Returns:
        Summary dict with overall score, pass rate, and per-case results
    """
    cases = EVAL_CASES
    if tags:
        cases = [c for c in cases if any(t in c.tags for t in tags)]

    logger.info("eval_suite_start", total_cases=len(cases), tags=tags)

    results = []
    for case in cases:
        result = run_eval_case(case, invoke_fn)
        results.append(result)

    # Compute summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total if total > 0 else 0.0
    total_duration_ms = sum(r.duration_ms for r in results)

    summary = {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "avg_score": avg_score,
        "total_duration_ms": total_duration_ms,
        "results": [
            {
                "case": r.case_name,
                "passed": r.passed,
                "score": r.score,
                "duration_ms": r.duration_ms,
                "tools_invoked": r.tools_invoked,
                "checks": r.checks,
                "error": r.error,
            }
            for r in results
        ],
    }

    logger.info(
        "eval_suite_complete",
        total=total,
        passed=passed,
        pass_rate=summary["pass_rate"],
        avg_score=avg_score,
    )

    return summary
