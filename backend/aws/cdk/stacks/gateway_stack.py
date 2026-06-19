"""
AgentCore Gateway stack.

Deploys an AgentCore Gateway that exposes Lambda tools as MCP endpoints,
enabling external agents and clients to discover and invoke procurement
optimization tools via the Model Context Protocol.

Resource types verified against AWS CloudFormation docs:
- AWS::BedrockAgentCore::Gateway
- AWS::BedrockAgentCore::GatewayTarget
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    CfnOutput,
    CfnResource,
)
from constructs import Construct
from cdk_nag import NagSuppressions


def _tool_definition(name: str, description: str, input_schema: dict) -> dict:
    """Build a ToolDefinition for InlinePayload array (PascalCase per CFN schema)."""
    return {
        "Name": name,
        "Description": description,
        "InputSchema": input_schema,
    }


def _schema(type_: str, description: str = "", properties: dict = None, required: list = None, items: dict = None) -> dict:
    """Build a SchemaDefinition with PascalCase keys per CloudFormation spec."""
    s: dict = {"Type": type_}
    if description:
        s["Description"] = description
    if properties:
        s["Properties"] = properties
    if required:
        s["Required"] = required
    if items:
        s["Items"] = items
    return s


class GatewayStack(Stack):
    """
    AgentCore Gateway stack.

    Creates:
    - AgentCore Gateway with MCP protocol
    - Gateway Targets linking each Lambda tool as an MCP tool
    - IAM role for gateway to invoke Lambda tools
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        optimization_function: lambda_.IFunction,
        explainability_function: lambda_.IFunction,
        data_access_function: lambda_.IFunction,
        cognito_pool_id: str = "",
        cognito_client_id: str = "",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Gateway execution role
        gateway_role = iam.Role(
            self,
            "GatewayRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            ),
            description="Execution role for AgentCore Gateway to invoke Lambda tools",
        )

        # Grant Lambda invoke permissions for each tool
        optimization_function.grant_invoke(gateway_role)
        explainability_function.grant_invoke(gateway_role)
        data_access_function.grant_invoke(gateway_role)

        # Grant CloudWatch Logs
        gateway_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/gateway/*",
                ],
            )
        )

        # AgentCore Gateway
        # Docs: AuthorizerType (required), ProtocolType (required),
        #       ProtocolConfiguration.Mcp.Instructions (optional)
        # JWT auth config (Cognito) — required for Runtime to pass user tokens
        discovery_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/"
            f"{cognito_pool_id}/.well-known/openid-configuration"
        ) if cognito_pool_id else ""

        gateway_properties: dict = {
            "Name": "procurement-optimization-gateway-jwt",
            "Description": (
                "MCP Gateway with Cognito JWT auth exposing procurement optimization tools"
            ),
            "RoleArn": gateway_role.role_arn,
            "ProtocolType": "MCP",
            "ProtocolConfiguration": {
                "Mcp": {
                    "Instructions": (
                        "This gateway provides procurement optimization tools for "
                        "VoltCycle e-bike manufacturing. Available tools: "
                        "optimize_suppliers (SLSQP multi-objective optimization returning "
                        "3 Pareto strategies: Cost-Optimized, Balanced, Risk-Diversified), "
                        "query_supplier_data (Neptune graph queries, forecasting, risk simulation), "
                        "explain_solution (business explanations with trade-off analysis)."
                    ),
                }
            },
        }

        if not cognito_pool_id or not cognito_client_id:
            raise ValueError("cognito_pool_id and cognito_client_id are required for JWT Gateway auth")

        gateway_properties["AuthorizerType"] = "CUSTOM_JWT"
        gateway_properties["AuthorizerConfiguration"] = {
            "CustomJWTAuthorizer": {
                "DiscoveryUrl": discovery_url,
                "AllowedClients": [cognito_client_id],
            }
        }

        self.gateway = CfnResource(
            self,
            "ProcurementGatewayJWT",
            type="AWS::BedrockAgentCore::Gateway",
            properties=gateway_properties,
        )

        gateway_id = self.gateway.get_att("GatewayIdentifier").to_string()

        # Credential config for Lambda targets — use gateway's IAM role
        lambda_cred_config = [{
            "CredentialProviderType": "GATEWAY_IAM_ROLE",
        }]

        # ── Gateway Target: Optimization Tool ───────────────────────

        optimization_target = CfnResource(
            self,
            "OptimizationTarget",
            type="AWS::BedrockAgentCore::GatewayTarget",
            properties={
                "GatewayIdentifier": gateway_id,
                "Name": "optimize-suppliers",
                "Description": (
                    "Multi-objective supplier optimization returning Pareto frontier solutions"
                ),
                "CredentialProviderConfigurations": lambda_cred_config,
                "TargetConfiguration": {
                    "Mcp": {
                        "Lambda": {
                            "LambdaArn": optimization_function.function_arn,
                            "ToolSchema": {
                                "InlinePayload": [
                                    _tool_definition(
                                        name="optimize_suppliers",
                                        description=(
                                            "Run multi-objective supplier optimization for e-bike "
                                            "manufacturing materials. Returns Pareto frontier solutions "
                                            "(Budget, Balanced, Premium, Resilient) with supplier "
                                            "allocations, costs, risk scores, and quality metrics."
                                        ),
                                        input_schema=_schema("object", "Optimization request", properties={
                                            "materials": _schema("array", "Materials to optimize", items=_schema("object", properties={
                                                "material_id": _schema("string", "Material ID (e.g. MAT-BAT-001)"),
                                                "quantity": _schema("integer", "Required quantity"),
                                            }, required=["material_id", "quantity"])),
                                            "constraints": _schema("object", "Optimization constraints", properties={
                                                "max_supplier_concentration": _schema("number", "Max order share per supplier (0.1-1.0)"),
                                                "max_lead_time_days": _schema("integer", "Max lead time in days"),
                                                "budget_max": _schema("number", "Maximum budget in USD"),
                                            }),
                                        }, required=["materials"]),
                                    ),
                                ],
                            },
                        },
                    },
                },
            },
        )
        optimization_target.add_dependency(self.gateway)

        # ── Gateway Target: Data Access Tool ────────────────────────

        data_access_target = CfnResource(
            self,
            "DataAccessTarget",
            type="AWS::BedrockAgentCore::GatewayTarget",
            properties={
                "GatewayIdentifier": gateway_id,
                "Name": "query-supplier-data",
                "Description": (
                    "Query supplier network graph for alternatives, relationships, and details"
                ),
                "CredentialProviderConfigurations": lambda_cred_config,
                "TargetConfiguration": {
                    "Mcp": {
                        "Lambda": {
                            "LambdaArn": data_access_function.function_arn,
                            "ToolSchema": {
                                "InlinePayload": [
                                    _tool_definition(
                                        name="query_supplier_data",
                                        description=(
                                            "Query supplier data, run Chronos-2 demand forecasts, and "
                                            "simulate supply chain risks. Handles all data queries."
                                        ),
                                        input_schema=_schema("object", "Query request", properties={
                                            "query_type": _schema("string", (
                                                "Type of query: find_alternative_suppliers, get_supplier_network, "
                                                "get_supplier_details, get_sourcing_summary, get_all_suppliers, "
                                                "get_supplier_performance, forecast_demand, simulate_risk, "
                                                "list_risk_scenarios"
                                            )),
                                            "material_id": _schema("string", "Material ID e.g. MAT-BAT-001"),
                                            "supplier_id": _schema("string", "Supplier ID e.g. SUP-001"),
                                            "scenario_id": _schema("string", "Risk scenario: strait_of_hormuz, suez_canal, taiwan_strait, us_china_tariff, european_port_strike"),
                                            "prediction_length": _schema("integer", "Forecast days (default 60, max 64)"),
                                            "max_hops": _schema("integer", "Graph traversal depth (1-5)"),
                                            "limit": _schema("integer", "Max results (1-50)"),
                                        }, required=["query_type"]),
                                    ),
                                ],
                            },
                        },
                    },
                },
            },
        )
        data_access_target.add_dependency(self.gateway)

        # ── Gateway Target: Explainability Tool ─────────────────────

        explainability_target = CfnResource(
            self,
            "ExplainabilityTarget",
            type="AWS::BedrockAgentCore::GatewayTarget",
            properties={
                "GatewayIdentifier": gateway_id,
                "Name": "explain-solution",
                "Description": (
                    "Generate business explanations for optimization decisions"
                ),
                "CredentialProviderConfigurations": lambda_cred_config,
                "TargetConfiguration": {
                    "Mcp": {
                        "Lambda": {
                            "LambdaArn": explainability_function.function_arn,
                            "ToolSchema": {
                                "InlinePayload": [
                                    _tool_definition(
                                        name="explain_solution",
                                        description=(
                                            "Generate a human-readable business explanation for an "
                                            "optimization solution including cost trade-offs, risk "
                                            "analysis, and TCO breakdown."
                                        ),
                                        input_schema=_schema("object", "Explanation request", properties={
                                            "solution_name": _schema("string", "Solution name: Budget, Balanced, Premium, Resilient, or Custom"),
                                            "total_cost": _schema("number", "Total cost in USD"),
                                            "risk_score": _schema("number", "Risk score (0-10)"),
                                            "quality_score": _schema("number", "Quality score (0-10)"),
                                            "allocations": _schema("array", "Supplier allocations", items=_schema("object", properties={
                                                "supplier_id": _schema("string", "Supplier ID"),
                                                "supplier_name": _schema("string", "Supplier name"),
                                                "material_id": _schema("string", "Material ID"),
                                                "quantity": _schema("integer", "Quantity"),
                                                "unit_price": _schema("number", "Unit price"),
                                                "total_cost": _schema("number", "Total cost"),
                                                "lead_time_days": _schema("integer", "Lead time in days"),
                                            })),
                                        }, required=["solution_name"]),
                                    ),
                                ],
                            },
                        },
                    },
                },
            },
        )
        explainability_target.add_dependency(self.gateway)

        # ── Outputs ─────────────────────────────────────────────────

        CfnOutput(
            self,
            "GatewayId",
            value=gateway_id,
            description="AgentCore Gateway ID",
        )

        CfnOutput(
            self,
            "GatewayArn",
            value=self.gateway.get_att("GatewayArn").to_string(),
            description="AgentCore Gateway ARN",
        )

        CfnOutput(
            self,
            "GatewayUrl",
            value=self.gateway.get_att("GatewayUrl").to_string(),
            description="AgentCore Gateway MCP endpoint URL",
        )

        CfnOutput(
            self,
            "OptimizationTargetId",
            value=optimization_target.get_att("TargetId").to_string(),
            description="Optimization tool Gateway Target ID",
        )

        CfnOutput(
            self,
            "DataAccessTargetId",
            value=data_access_target.get_att("TargetId").to_string(),
            description="Data access tool Gateway Target ID",
        )

        CfnOutput(
            self,
            "ExplainabilityTargetId",
            value=explainability_target.get_att("TargetId").to_string(),
            description="Explainability tool Gateway Target ID",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            gateway_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda invoke permissions are scoped to specific function ARNs; CloudWatch wildcard for log streams"
                }
            ],
            apply_to_children=True,
        )
