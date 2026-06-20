"""
API Gateway + Lambda stack for the Flask backend.

Exposes the Flask server as a REST API via API Gateway + Lambda.
Lambda is in VPC for Neptune access. Strands agent hits Bedrock directly.
"""

import os

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_neptune as neptune,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class ApiStack(Stack):
    """
    API Gateway + Lambda stack.

    Creates:
    - Lambda function running Flask (in VPC for Neptune access)
    - API Gateway REST API with CORS
    - IAM permissions for Bedrock model invocation + Neptune
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        data_bucket: s3.Bucket,
        shared_layer: lambda_.LayerVersion,
        neptune_cluster: neptune.CfnDBCluster,
        vpc: ec2.IVpc,
        lambda_sg: ec2.ISecurityGroup,
        user_pool: cognito.IUserPool,
        gateway_id: str = "",
        memory_id: str = "",
        policy_engine_id: str = "",
        frontend_url: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cors_origins = [o for o in [
            frontend_url,
            "http://localhost:5173",
            "http://localhost:5174",
        ] if o]

        # Lambda execution role
        api_role = iam.Role(
            self,
            "ApiLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            ],
        )

        # Grant Bedrock model invocation (for Strands agent)
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Converse",
                    "bedrock:ConverseStream",
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/*",
                    f"arn:aws:bedrock:us::{self.account}:inference-profile/*",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                ],
            )
        )

        # Grant Neptune access
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "neptune-db:connect",
                    "neptune-db:ReadDataViaQuery",
                ],
                resources=[
                    (
                        f"arn:aws:neptune-db:{self.region}:{self.account}:"
                        f"{neptune_cluster.attr_cluster_resource_id}/*"
                    )
                ],
            )
        )

        # Grant SageMaker Chronos-2 endpoint invocation (for demand forecasting)
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sagemaker:InvokeEndpoint"],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/chronos-2-forecast-endpoint",
                ],
            )
        )

        # Grant AgentCore control + data plane access (for admin Operations
        # panel). Per-resource Get/data actions are scoped to the gateway,
        # memory, and policy-engine resources owned by this deployment.
        agentcore_arn_prefix = (
            f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:"
        )
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:GetGateway",
                    "bedrock-agentcore:ListGatewayTargets",
                    "bedrock-agentcore:GetGatewayTarget",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:GetPolicyEngine",
                    "bedrock-agentcore:ListPolicies",
                    "bedrock-agentcore:GetPolicy",
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:ListSessions",
                ],
                resources=[
                    f"{agentcore_arn_prefix}gateway/{gateway_id}",
                    f"{agentcore_arn_prefix}gateway/{gateway_id}/*",
                    f"{agentcore_arn_prefix}memory/{memory_id}",
                    f"{agentcore_arn_prefix}memory/{memory_id}/*",
                    f"{agentcore_arn_prefix}policy-engine/{policy_engine_id}",
                    f"{agentcore_arn_prefix}policy-engine/{policy_engine_id}/*",
                ],
            )
        )

        # List/discovery and runtime-invoke actions that the AgentCore API
        # only authorizes on "*" (they enumerate resources or target a
        # runtime whose ARN is not known at synth time).
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:ListGateways",
                    "bedrock-agentcore:ListMemories",
                    "bedrock-agentcore:ListPolicyEngines",
                    "bedrock-agentcore:ListEvaluators",
                    "bedrock-agentcore:GetEvaluator",
                    "bedrock-agentcore:InvokeAgentRuntime",
                ],
                resources=["*"],
            )
        )

        # Grant CloudWatch Logs read access (for eval traces in Operations
        # panel). DescribeLogGroups must run against "*" (the API does not
        # accept a resource for it); the per-log-group read actions are scoped
        # to the Bedrock AgentCore and Lambda log-group hierarchies.
        scoped_log_groups = [
            f"arn:aws:logs:{self.region}:{self.account}:"
            "log-group:/aws/bedrock-agentcore/*",
            f"arn:aws:logs:{self.region}:{self.account}:"
            "log-group:/aws/lambda/*",
            f"arn:aws:logs:{self.region}:{self.account}:"
            "log-group:/aws/bedrock-agentcore/*:log-stream:*",
            f"arn:aws:logs:{self.region}:{self.account}:"
            "log-group:/aws/lambda/*:log-stream:*",
        ]
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:FilterLogEvents",
                    "logs:GetLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=scoped_log_groups,
            )
        )
        api_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:DescribeLogGroups"],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:*"
                ],
            )
        )

        # Grant S3 access for data and PRs
        data_bucket.grant_read_write(api_role)

        # Lambda function with Flask app
        # Use agent-bundle/ but exclude pre-installed arm64 deps (those are in the Lambda layer).
        # Only source code (api/, agents/, core/, config/, data/) + api_handler.py are needed.
        agent_bundle_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "agent-bundle"
        )
        api_function = lambda_.Function(
            self,
            "ApiFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="api_handler.handler",
            code=lambda_.Code.from_asset(
                agent_bundle_path,
                exclude=[
                    "*.dist-info/*", "*.dist-info",
                    "bin/*", "bin",
                    "*.so",
                    "boto3/*", "botocore/*", "s3transfer/*", "urllib3/*",
                    "bedrock_agentcore/*", "bedrock_agentcore*",
                    "pydantic/*", "pydantic_core/*",
                    "numpy/*", "numpy*", "scipy/*", "scipy*",
                    "pandas/*", "pandas*",
                    "anyio/*", "httpx/*", "httpcore/*", "sniffio/*",
                    "attr/*", "attrs/*",
                    "certifi/*", "charset_normalizer/*",
                    "yaml/*", "_yaml/*",
                    "uvicorn/*", "starlette/*", "fastapi/*",
                    "opentelemetry*/*",
                    "wrapt/*", "watchdog/*", "websockets/*",
                    "packaging/*", "annotated_types/*",
                    "jwt/*", "cffi/*", "cryptography/*",
                    "_cffi_backend*",
                    "*.pyc", "__pycache__",
                ],
            ),
            role=api_role,
            timeout=Duration.seconds(120),
            memory_size=2048,
            environment={
                "FLASK_ENV": "production",
                "DATA_DIR": "/var/task/data",
                "DATA_PATH": "/var/task/data",
                "CORS_ORIGINS": ",".join(cors_origins),
                "PR_S3_BUCKET": data_bucket.bucket_name,
                "DATA_BUCKET": data_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
                "NEPTUNE_ENDPOINT": neptune_cluster.attr_endpoint,
                "NEPTUNE_PORT": neptune_cluster.attr_port,
                # AgentCore IDs — cross-stack references from CDK
                "AGENTCORE_GATEWAY_ID": gateway_id,
                "AGENTCORE_MEMORY_ID": memory_id,
                "AGENTCORE_POLICY_ENGINE_ID": policy_engine_id,
                "AGENTCORE_RUNTIME_ID": "",
                "AGENTCORE_AGENT_ID": "",
                "PROCUREMENT_AGENT_ID": "",
                "FORECAST_AGENT_ID": "",
                "AGENT_MODE": "local",
                "SAGEMAKER_ENDPOINT_NAME": "chronos-2-forecast-endpoint",
                "FORECAST_DATA_PREFIX": "forecast-data/",
            },
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Flask API for procurement agent (VPC, Neptune, Bedrock)",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg],
        )

        # Cognito authorizer
        cognito_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="procurement-cognito-auth",
        )

        # API Gateway — Cognito auth on all routes by default
        api = apigw.LambdaRestApi(
            self,
            "ProcurementApi",
            handler=api_function,
            proxy=False,
            rest_api_name="procurement-agent-api",
            description="Procurement Agent REST API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Access-Token", "X-Session-Id"],
            ),
            default_method_options=apigw.MethodOptions(
                authorization_type=apigw.AuthorizationType.COGNITO,
                authorizer=cognito_authorizer,
            ),
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
        )

        lambda_integration = apigw.LambdaIntegration(api_function)

        # Public endpoints (no auth)
        health = api.root.add_resource("health")
        health.add_method("GET", lambda_integration, authorization_type=apigw.AuthorizationType.NONE)

        # All other routes require Cognito auth (proxy to Lambda)
        api.root.add_proxy(
            default_integration=lambda_integration,
            any_method=True,
            default_method_options=apigw.MethodOptions(
                authorization_type=apigw.AuthorizationType.COGNITO,
                authorizer=cognito_authorizer,
            ),
        )

        self.api_url = api.url

        # Add CORS headers to API Gateway error responses (authorizer 401/403).
        # Without this, the browser blocks error responses from the Cognito authorizer.
        for status_code, response_type in [
            ("401", apigw.ResponseType.UNAUTHORIZED),
            ("403", apigw.ResponseType.ACCESS_DENIED),
            ("4XX", apigw.ResponseType.DEFAULT_4_XX),
            ("5XX", apigw.ResponseType.DEFAULT_5_XX),
        ]:
            api.add_gateway_response(
                f"CorsResponse{status_code}",
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": f"'{cors_origins[0]}'" if cors_origins else "'*'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization'",
                    "Access-Control-Allow-Methods": "'OPTIONS,GET,POST,PUT,DELETE'",
                },
            )

        # Outputs
        CfnOutput(self, "ApiUrl", value=api.url, description="API Gateway URL")
        CfnOutput(self, "ApiFunctionArn", value=api_function.function_arn, description="API Lambda ARN")

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            api_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaVPCAccessExecutionRole",
                    ],
                    "reason": (
                        "AWS-managed VPC access execution role is required for "
                        "a Lambda placed in a VPC to manage its ENIs; an "
                        "equivalent customer-managed policy adds maintenance "
                        "burden without security benefit for a sample."
                    ),
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "appliesTo": [
                        # Bedrock foundation models / inference profiles are
                        # not known at synth time and are addressed by family.
                        "Resource::arn:aws:bedrock:*::foundation-model/*",
                        {
                            "regex": "/^Resource::arn:aws:bedrock:.*:"
                            "inference-profile/\\*$/g"
                        },
                        # S3 grant_read_write expands to scoped sub-actions on
                        # the data bucket only.
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Action::s3:Abort*",
                        "Action::s3:DeleteObject*",
                        "Resource::<ProcurementDataBucket28D81D70.Arn>/*",
                        # Neptune scoped to this cluster's IAM-auth resource id.
                        {"regex": "/^Resource::arn:aws:neptune-db:.*$/g"},
                        # AgentCore per-resource Get actions scoped to this
                        # deployment's gateway/memory/policy-engine ARNs (which
                        # carry a trailing /* for sub-resources).
                        {
                            "regex": "/^Resource::arn:aws:bedrock-agentcore:.*:"
                            "(gateway|memory|policy-engine)/.*$/g"
                        },
                        # AgentCore list/discovery and runtime-invoke only
                        # authorize on "*".
                        "Resource::*",
                        # Per-log-group reads scoped to the AgentCore/Lambda
                        # log-group hierarchies; DescribeLogGroups uses "*".
                        {"regex": "/^Resource::arn:aws:logs:.*:log-group:.*$/g"},
                    ],
                    "reason": (
                        "Bedrock InvokeModel targets foundation models and "
                        "inference profiles whose IDs are not known at synth "
                        "time; S3 wildcards are sub-actions of grant_read_write "
                        "scoped to the data bucket; the Neptune statement is "
                        "scoped to this cluster's IAM-auth resource id; the "
                        "AgentCore per-resource Get actions are scoped to this "
                        "deployment's gateway/memory/policy-engine ARNs; "
                        "AgentCore List* / InvokeAgentRuntime and "
                        "logs:DescribeLogGroups only authorize on '*' per their "
                        "IAM action definitions, and the per-log-group read "
                        "actions are scoped to the /aws/bedrock-agentcore and "
                        "/aws/lambda log-group hierarchies."
                    ),
                },
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            api,
            [
                {
                    "id": "AwsSolutions-APIG2",
                    "reason": (
                        "The backend is a single Lambda proxy that performs "
                        "its own Pydantic request validation; API Gateway "
                        "request validation would duplicate that logic."
                    ),
                },
                {
                    "id": "AwsSolutions-APIG3",
                    "reason": (
                        "A WAFv2 web ACL is left to the deploying account's "
                        "Firewall Manager / org policy rather than hard-coded "
                        "in this stack; CloudFront in front of the UI and the "
                        "Cognito authorizer provide the request controls."
                    ),
                },
            ],
            apply_to_children=True,
        )
        # Stage-level logging (access logs + execution logging) is left to the
        # deploying account's centralized API Gateway logging configuration to
        # avoid hard-coding a log destination + CloudWatch role in this stack.
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/ProcurementApi/DeploymentStage.prod/Resource",
            [
                {
                    "id": "AwsSolutions-APIG1",
                    "reason": (
                        "Access logging is left to the deploying account's "
                        "centralized API Gateway logging configuration rather "
                        "than hard-coding a log-group destination in this "
                        "stack."
                    ),
                },
                {
                    "id": "AwsSolutions-APIG6",
                    "reason": (
                        "Method-level CloudWatch execution logging is left to "
                        "the deploying account's centralized API Gateway "
                        "logging configuration (which requires an "
                        "account-level CloudWatch role) rather than being "
                        "hard-coded in this stack."
                    ),
                },
            ],
        )
        # /health GET is intentionally unauthenticated (uptime probes) and CORS
        # preflight OPTIONS requests are sent without credentials, so neither
        # the generic authorization rule (APIG4) nor the Cognito authorizer
        # rule (COG4) can apply to them. All other routes use Cognito.
        unauth_methods = {
            "/health/GET/Resource": (
                "The /health GET endpoint is intentionally unauthenticated for "
                "load-balancer/uptime probes; all other routes use the "
                "Cognito authorizer."
            ),
            "/OPTIONS/Resource": (
                "CORS preflight OPTIONS requests are sent by the browser "
                "without credentials and must remain unauthenticated; all "
                "non-OPTIONS routes (except /health) use the Cognito "
                "authorizer."
            ),
            "/health/OPTIONS/Resource": (
                "CORS preflight OPTIONS requests are sent by the browser "
                "without credentials and must remain unauthenticated; all "
                "non-OPTIONS routes (except /health) use the Cognito "
                "authorizer."
            ),
            "/{proxy+}/OPTIONS/Resource": (
                "CORS preflight OPTIONS requests are sent by the browser "
                "without credentials and must remain unauthenticated; all "
                "non-OPTIONS routes (except /health) use the Cognito "
                "authorizer."
            ),
        }
        for method_path, reason in unauth_methods.items():
            NagSuppressions.add_resource_suppressions_by_path(
                self,
                "/" + self.stack_name + "/ProcurementApi/Default"
                + method_path,
                [
                    {"id": "AwsSolutions-APIG4", "reason": reason},
                    {"id": "AwsSolutions-COG4", "reason": reason},
                ],
            )
        NagSuppressions.add_resource_suppressions(
            api_function,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": (
                        "Runtime pinned to Python 3.11 to match the shared "
                        "Lambda layer's scipy/numpy native wheels (compiled "
                        "for 3.11); a newer runtime requires rebuilding those "
                        "native dependencies."
                    ),
                },
            ],
            apply_to_children=True,
        )
        # LogRetention is a CDK-managed custom resource (AWS-managed
        # basic-execution policy + logs wildcard) not user-configurable.
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/"
            "Resource",
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaBasicExecutionRole",
                    ],
                    "reason": (
                        "AWS-managed basic-execution role is required by the "
                        "CDK LogRetention custom-resource Lambda; not "
                        "user-configurable."
                    ),
                }
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/"
            "DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "appliesTo": ["Resource::*"],
                    "reason": (
                        "The CDK LogRetention custom resource must call "
                        "logs:PutRetentionPolicy/DeleteRetentionPolicy across "
                        "log groups whose names are not known at synth time; "
                        "the wildcard resource is created and managed by the "
                        "construct and is not user-configurable."
                    ),
                }
            ],
        )
