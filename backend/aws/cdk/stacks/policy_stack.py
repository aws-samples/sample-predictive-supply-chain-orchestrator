"""
AgentCore Policy stack.

Creates a Bedrock AgentCore PolicyEngine and Cedar policies for
RBAC and guardrails on Gateway tool invocations.

Resources:
- AWS::BedrockAgentCore::PolicyEngine
- AWS::BedrockAgentCore::Policy
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    CfnResource,
)
from constructs import Construct


# Cedar policies for procurement gateway RBAC + guardrails.
# Note: Cedar schema is auto-generated from Gateway tool schemas.
# These policies reference the tool names defined in the Gateway targets.
CEDAR_POLICIES = {
    "AnalystReadData": {
        "description": "Analyst role: read-only access to supplier data queries",
        "statement": (
            'permit (principal, action == Action::"ToolCall", resource == Tool::"query-supplier-data::query_supplier_data")\n'
            'when { principal has role && principal.role == "Analyst" };'
        ),
    },
    "AnalystExplain": {
        "description": "Analyst role: read-only access to solution explanations",
        "statement": (
            'permit (principal, action == Action::"ToolCall", resource == Tool::"explain-solution::explain_solution")\n'
            'when { principal has role && principal.role == "Analyst" };'
        ),
    },
    "ManagerOptimize": {
        "description": "Procurement Manager: run optimization within budget authority",
        "statement": (
            'permit (principal, action == Action::"ToolCall", resource == Tool::"optimize-suppliers::optimize_suppliers")\n'
            'when { principal has role && principal.role == "ProcurementManager" };'
        ),
    },
    "ManagerDataAccess": {
        "description": "Procurement Manager: query supplier data",
        "statement": (
            'permit (principal, action == Action::"ToolCall", resource == Tool::"query-supplier-data::query_supplier_data")\n'
            'when { principal has role && principal.role == "ProcurementManager" };'
        ),
    },
    "ManagerExplain": {
        "description": "Procurement Manager: view solution explanations",
        "statement": (
            'permit (principal, action == Action::"ToolCall", resource == Tool::"explain-solution::explain_solution")\n'
            'when { principal has role && principal.role == "ProcurementManager" };'
        ),
    },
    "AdminFullAccess": {
        "description": "Admin: unrestricted access to all gateway tools",
        "statement": (
            'permit (principal, action, resource)\n'
            'when { principal has role && principal.role == "Admin" };'
        ),
    },
    "DenyExcessiveBudget": {
        "description": "Guardrail: forbid optimization requests exceeding $10M budget",
        "statement": (
            'forbid (principal, action == Action::"ToolCall", resource == Tool::"optimize-suppliers::optimize_suppliers")\n'
            'when { context has budget_max && context.budget_max > 10000000 };'
        ),
    },
}


class PolicyStack(Stack):
    """
    AgentCore Policy stack.

    Creates:
    - PolicyEngine for Cedar-based authorization
    - Cedar policies for RBAC (Analyst, Manager, Admin) + guardrails
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # PolicyEngine
        self.policy_engine = CfnResource(
            self,
            "ProcurementPolicyEngine",
            type="AWS::BedrockAgentCore::PolicyEngine",
            properties={
                "Name": "ProcurementPolicyEngine",
                "Description": (
                    "Cedar policy engine for procurement optimization gateway - "
                    "RBAC with Analyst/Manager/Admin roles and budget guardrails"
                ),
            },
        )

        policy_engine_id = self.policy_engine.get_att("PolicyEngineId").to_string()

        # Note: Cedar policies are created after gateway deployment via
        # scripts/deploy_policies.py, because Cedar schema is auto-generated
        # from the gateway's tool schemas and must exist before policies
        # can reference tool resources. The CEDAR_POLICIES dict above
        # documents the intended policies for reference.

        # Outputs
        CfnOutput(
            self,
            "PolicyEngineId",
            value=policy_engine_id,
            description="AgentCore PolicyEngine ID",
        )

        CfnOutput(
            self,
            "PolicyEngineArn",
            value=self.policy_engine.get_att("PolicyEngineArn").to_string(),
            description="AgentCore PolicyEngine ARN",
        )

        CfnOutput(
            self,
            "PolicyCount",
            value=str(len(CEDAR_POLICIES)),
            description="Number of Cedar policies deployed",
        )
