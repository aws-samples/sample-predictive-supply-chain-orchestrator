"""
AgentCore Runtime stack.

Creates a Bedrock AgentCore Runtime resource for the procurement
optimization agent with Cognito JWT auth, environment variables,
and observability configuration.

The Runtime is the IaC-managed infrastructure. Agent code is deployed
separately via `agentcore launch --agent` (see deploy-all.sh Step 2).

Resource: AWS::BedrockAgentCore::Runtime
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput,
    CfnResource,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class RuntimeStack(Stack):
    """
    AgentCore Runtime stack.

    Creates:
    - IAM execution role for Runtime
    - AgentCore Runtime resource with JWT auth and env vars
    - Outputs Runtime ID and ARN for frontend and deploy script
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        gateway_id: str,
        memory_id: str,
        cognito_pool_id: str,
        cognito_client_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM execution role for the Runtime
        runtime_role = iam.Role(
            self,
            "RuntimeExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
        )

        # Bedrock model invocation
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/*",
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/*",
                ],
            )
        )

        # AgentCore access (Gateway, Memory, tools)
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:*"],
                resources=[f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:*"],
            )
        )

        # CloudWatch Logs
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/*"],
            )
        )

        # ECR (for container deployments)
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/bedrock-agentcore-*"],
            )
        )

        # Cognito JWT discovery URL
        discovery_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/"
            f"{cognito_pool_id}/.well-known/openid-configuration"
        )

        # AgentCore Runtime
        self.runtime = CfnResource(
            self,
            "ProcurementRuntime",
            type="AWS::BedrockAgentCore::Runtime",
            properties={
                "AgentRuntimeName": "procurement_optimization_agent",
                "Description": (
                    "Multi-agent procurement orchestrator with Strands agent framework, "
                    "MCP Gateway tools, AgentCore Memory, and OTEL observability"
                ),
                "RoleArn": runtime_role.role_arn,
                "AuthorizerConfiguration": {
                    "CustomJWTAuthorizer": {
                        "DiscoveryUrl": discovery_url,
                        "AllowedClients": [cognito_client_id],
                    }
                },
                "EnvironmentVariables": {
                    "GATEWAY_ID": gateway_id,
                    "MEMORY_ID": memory_id,
                    "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                },
            },
        )

        # Outputs
        CfnOutput(
            self,
            "RuntimeId",
            value=self.runtime.get_att("AgentRuntimeId").to_string(),
            description="AgentCore Runtime ID",
        )

        CfnOutput(
            self,
            "RuntimeArn",
            value=self.runtime.get_att("AgentRuntimeArn").to_string(),
            description="AgentCore Runtime ARN (use for VITE_AGENTCORE_RUNTIME_ARN)",
        )

        CfnOutput(
            self,
            "RuntimeStatus",
            value=self.runtime.get_att("Status").to_string(),
            description="AgentCore Runtime status",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            runtime_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "AmazonBedrockFullAccess needed for model invocation",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard needed for AgentCore, ECR, and CloudWatch access",
                },
            ],
        )
