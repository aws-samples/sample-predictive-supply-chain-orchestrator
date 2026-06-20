#!/usr/bin/env python3
"""
CDK app entry point for Procurement Optimization Agent.

Deploys infrastructure stacks: Identity, Lambda Layer, Data, Lambda Tools,
Neptune Loader, Gateway, Policy Engine, Memory, Evaluators, Observability,
API, and Frontend.

NOTE: AgentCore agents (procurement + demand forecast) are deployed via
bedrock-agentcore-starter-toolkit, not CDK. See:
  backend/agentcore_bundle/              (procurement agent)
  demand-forecasting/agentcore-deploy/     (demand forecast agent)
"""

import os
import aws_cdk as cdk
from aws_cdk import Tags
from cdk_nag import AwsSolutionsChecks

from stacks.identity_stack import IdentityStack
from stacks.data_stack import DataStack
from stacks.lambda_layer_stack import LambdaLayerStack
from stacks.lambda_stack import LambdaStack
from stacks.neptune_loader_stack import NeptuneLoaderStack
from stacks.gateway_stack import GatewayStack
from stacks.policy_stack import PolicyStack
from stacks.memory_stack import MemoryStack
from stacks.evaluator_stack import EvaluatorStack
from stacks.guardrail_stack import GuardrailStack
from stacks.observability_stack import ObservabilityStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack
from stacks.sagemaker_forecast_stack import SageMakerForecastStack
# from stacks.runtime_stack import RuntimeStack  # deployed via CLI


app = cdk.App()

# Run cdk-nag AWS Solutions checks at synth time so security findings are
# surfaced (and any suppressions are real, justified exceptions). Set
# CDK_NAG_DISABLE=1 to skip locally when iterating quickly.
if os.environ.get("CDK_NAG_DISABLE", "") != "1":
    cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

project_name = "procurement-optimization-agent"
environment = os.environ.get("ENVIRONMENT", "development")

# Identity stack (Cognito)
identity_stack = IdentityStack(
    app, f"{project_name}-identity-{environment}",
    env=env, description="Identity and authentication with Cognito"
)

# Lambda layer stack (shared dependencies)
layer_stack = LambdaLayerStack(
    app, f"{project_name}-layer-{environment}",
    env=env, description="Lambda layer with shared Python dependencies"
)

# Data stack (Neptune + S3)
data_stack = DataStack(
    app, f"{project_name}-data-{environment}",
    env=env, description="Data layer with Neptune graph database and S3 storage"
)

# Lambda tools stack
lambda_stack = LambdaStack(
    app, f"{project_name}-lambda-{environment}",
    neptune_cluster=data_stack.neptune_cluster,
    data_bucket=data_stack.data_bucket,
    shared_layer=layer_stack.shared_layer,
    vpc=data_stack.vpc,
    lambda_sg=data_stack.lambda_sg,
    env=env, description="Lambda functions for Bedrock agent tools"
)

# Neptune data loader stack (Custom Resource)
loader_stack = NeptuneLoaderStack(
    app, f"{project_name}-loader-{environment}",
    neptune_cluster=data_stack.neptune_cluster,
    data_bucket=data_stack.data_bucket,
    neptune_s3_role_arn=data_stack.neptune_s3_role_arn,
    vpc=data_stack.vpc,
    lambda_sg=data_stack.lambda_sg,
    env=env, description="Neptune data loader using Custom Resource"
)

# Gateway stack (AgentCore Gateway exposing Lambda tools via MCP)
gateway_stack = GatewayStack(
    app, f"{project_name}-gateway-{environment}",
    optimization_function=lambda_stack.optimization_function,
    explainability_function=lambda_stack.explainability_function,
    data_access_function=lambda_stack.data_access_function,
    cognito_pool_id=identity_stack.user_pool.user_pool_id,
    cognito_client_id=identity_stack.user_pool_client.user_pool_client_id,
    env=env, description="AgentCore Gateway with JWT auth exposing Lambda tools via MCP"
)

# Policy stack (AgentCore PolicyEngine + Cedar policies)
policy_stack = PolicyStack(
    app, f"{project_name}-policy-{environment}",
    env=env, description="AgentCore PolicyEngine with Cedar RBAC and guardrails"
)

# Memory stack (AgentCore Memory with strategies)
memory_stack = MemoryStack(
    app, f"{project_name}-memory-{environment}",
    env=env, description="AgentCore Memory with semantic, preference, and summary strategies"
)

# Evaluator stack (AgentCore Evaluators for agent quality)
evaluator_stack = EvaluatorStack(
    app, f"{project_name}-evaluator-{environment}",
    env=env, description="AgentCore Evaluators for tool accuracy and session quality"
)

# Guardrail stack (Bedrock Guardrail for PII detection + content safety)
guardrail_stack = GuardrailStack(
    app, f"{project_name}-guardrail-{environment}",
    env=env, description="Bedrock Guardrail for PII detection and content safety"
)

# Observability stack (CloudWatch dashboard + alarms + tracing)
observability_stack = ObservabilityStack(
    app, f"{project_name}-observability-{environment}",
    env=env, description="CloudWatch dashboards, alarms, and OpenTelemetry tracing"
)

# API stack (Lambda + API Gateway with Flask backend)
api_stack = ApiStack(
    app, f"{project_name}-api-{environment}",
    data_bucket=data_stack.data_bucket,
    shared_layer=layer_stack.shared_layer,
    neptune_cluster=data_stack.neptune_cluster,
    vpc=data_stack.vpc,
    lambda_sg=data_stack.lambda_sg,
    user_pool=identity_stack.user_pool,
    gateway_id=gateway_stack.gateway.get_att("GatewayIdentifier").to_string(),
    memory_id=memory_stack.memory.get_att("MemoryId").to_string(),
    policy_engine_id=policy_stack.policy_engine.get_att("PolicyEngineId").to_string(),
    frontend_url=os.environ.get("FRONTEND_URL", ""),
    env=env, description="Flask API on Lambda with VPC/Neptune/Bedrock"
)

# Frontend stack (S3 + CloudFront + Cognito)
frontend_stack = FrontendStack(
    app, f"{project_name}-frontend-{environment}",
    user_pool=identity_stack.user_pool,
    user_pool_client=identity_stack.user_pool_client,
    env=env, description="Frontend hosting with S3, CloudFront, and Cognito auth"
)

# AgentCore Runtime stack — DISABLED: requires AgentRuntimeArtifact (container image)
# which is built by the agentcore CLI toolkit, not CDK. Agent deployed in Step 2 of deploy-all.sh.
# runtime_stack = RuntimeStack(
#     app, f"{project_name}-runtime-{environment}",
#     gateway_id=gateway_stack.gateway.get_att("GatewayIdentifier").to_string(),
#     memory_id=memory_stack.memory.get_att("MemoryId").to_string(),
#     cognito_pool_id=identity_stack.user_pool.user_pool_id,
#     cognito_client_id=identity_stack.user_pool_client.user_pool_client_id,
#     env=env, description="AgentCore Runtime for procurement optimization agent"
# )

# SageMaker Forecast stack (IAM role for Chronos-2 endpoint)
sagemaker_forecast_stack = SageMakerForecastStack(
    app, f"{project_name}-sagemaker-forecast-{environment}",
    env=env, description="IAM role for SageMaker Chronos-2 forecast endpoint"
)


# Apply common tags
for stack in [identity_stack, layer_stack, data_stack, lambda_stack, loader_stack,
              gateway_stack, policy_stack, memory_stack, evaluator_stack,
              guardrail_stack, observability_stack, api_stack, frontend_stack,
              sagemaker_forecast_stack]:
    Tags.of(stack).add("Project", project_name)
    Tags.of(stack).add("Environment", environment)
    Tags.of(stack).add("ManagedBy", "CDK")
    Tags.of(stack).add("Owner", os.environ.get("OWNER", "cde-team"))

app.synth()
