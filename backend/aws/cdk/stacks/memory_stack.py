"""
AgentCore Memory stack.

Creates a Bedrock AgentCore Memory resource with strategies for
semantic extraction, user preferences, and summarization.

Resource: AWS::BedrockAgentCore::Memory
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput,
    CfnResource,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class MemoryStack(Stack):
    """
    AgentCore Memory stack.

    Creates:
    - IAM execution role for Memory
    - AgentCore Memory resource with SEMANTIC and USER_PREFERENCE strategies
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Memory execution role
        memory_role = iam.Role(
            self,
            "MemoryExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            ),
            description="Execution role for AgentCore Memory resource",
        )

        # Grant Bedrock model invocation for memory extraction/consolidation
        memory_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-sonnet-4-20250514",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-haiku-4-5-20251001",
                ],
            )
        )

        # AgentCore Memory
        self.memory = CfnResource(
            self,
            "ProcurementAgentMemory",
            type="AWS::BedrockAgentCore::Memory",
            properties={
                "Name": "ProcurementAgentMemory",
                "Description": (
                    "Memory for procurement optimization agent - stores supplier insights, "
                    "user preferences, and conversation summaries across sessions"
                ),
                "EventExpiryDuration": 90,  # 90 days
                "MemoryExecutionRoleArn": memory_role.role_arn,
                "MemoryStrategies": [
                    {
                        "SemanticMemoryStrategy": {
                            "Name": "SupplierInsights",
                            "Description": "Extracts and consolidates supplier-related facts and insights",
                            "Namespaces": ["{actorId}/supplier-insights"],
                        },
                    },
                    {
                        "UserPreferenceMemoryStrategy": {
                            "Name": "UserPreferences",
                            "Description": "Tracks user optimization preferences, budget constraints, and strategy choices",
                            "Namespaces": ["{actorId}/preferences"],
                        },
                    },
                    {
                        "SummaryMemoryStrategy": {
                            "Name": "SessionSummaries",
                            "Description": "Summarizes procurement conversations for cross-session continuity",
                            "Namespaces": ["{actorId}/{sessionId}/summaries"],
                        },
                    },
                ],
            },
        )

        # Outputs
        CfnOutput(
            self,
            "MemoryId",
            value=self.memory.get_att("MemoryId").to_string(),
            description="AgentCore Memory ID",
        )

        CfnOutput(
            self,
            "MemoryArn",
            value=self.memory.get_att("MemoryArn").to_string(),
            description="AgentCore Memory ARN",
        )

        CfnOutput(
            self,
            "MemoryStatus",
            value=self.memory.get_att("Status").to_string(),
            description="AgentCore Memory status",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            memory_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Bedrock model invocation requires specific model ARNs; no wildcard used"
                }
            ],
            apply_to_children=True,
        )
