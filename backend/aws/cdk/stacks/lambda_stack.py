"""
Lambda stack for Bedrock agent tools.

Follows CDE standards:
- cdk-nag compliant
- Least privilege IAM
- Environment variable configuration
- VPC access for Neptune
"""

import os

from aws_cdk import (
    Stack,
    Duration,
    SymlinkFollowMode,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_neptune as neptune,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions



class LambdaStack(Stack):
    """
    Lambda functions stack for agent tools.
    
    Creates:
    - Optimization tool Lambda
    - Explainability tool Lambda
    - Data access tool Lambda
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        neptune_cluster: neptune.CfnDBCluster,
        data_bucket: s3.Bucket,
        shared_layer: lambda_.LayerVersion,
        vpc: ec2.IVpc,
        lambda_sg: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Common Lambda execution role
        lambda_role = iam.Role(
            self,
            "LambdaToolsRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Bedrock agent Lambda tools",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            ]
        )
        
        # Grant S3 read access
        data_bucket.grant_read(lambda_role)
        
        # Grant Neptune IAM-auth data-plane access scoped to this cluster's
        # resource ID. The agent tools query the graph and write derived
        # results back, so connect + read + write query actions are granted
        # (not the full neptune-db:* action set).
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "neptune-db:connect",
                    "neptune-db:ReadDataViaQuery",
                    "neptune-db:WriteDataViaQuery",
                    "neptune-db:GetQueryStatus",
                ],
                resources=[
                    (
                        f"arn:aws:neptune-db:{self.region}:{self.account}:"
                        f"{neptune_cluster.attr_cluster_resource_id}/*"
                    )
                ],
            )
        )

        # Grant SageMaker endpoint invocation (Chronos-2 forecasting)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sagemaker:InvokeEndpoint"],
                resources=[f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/chronos-*"]
            )
        )
        
        # Common Lambda environment variables
        common_env = {
            "NEPTUNE_ENDPOINT": neptune_cluster.attr_endpoint,
            "NEPTUNE_PORT": neptune_cluster.attr_port,
            "DATA_BUCKET": data_bucket.bucket_name,
            "CSV_DATA_DIR": "/var/task/csv_data",
            "SAGEMAKER_ENDPOINT_NAME": "chronos-2-forecast-endpoint",
            "LOG_LEVEL": "INFO"
        }
        
        # Optimization tool Lambda
        self.optimization_function = lambda_.Function(
            self,
            "OptimizationTool",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="optimization_tool.lambda_handler",
            code=lambda_.Code.from_asset("../lambda_tools", follow_symlinks=SymlinkFollowMode.ALWAYS),
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=2048,
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Optimization engine tool for Bedrock agent",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg]
        )
        
        # Explainability tool Lambda
        self.explainability_function = lambda_.Function(
            self,
            "ExplainabilityTool",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="explainability_tool.lambda_handler",
            code=lambda_.Code.from_asset("../lambda_tools", follow_symlinks=SymlinkFollowMode.ALWAYS),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Explainability tool for Bedrock agent",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg]
        )
        
        # Data access tool Lambda
        self.data_access_function = lambda_.Function(
            self,
            "DataAccessTool",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="data_access_tool.lambda_handler",
            code=lambda_.Code.from_asset("../lambda_tools", follow_symlinks=SymlinkFollowMode.ALWAYS),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=common_env,
            layers=[shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Data access tool for Neptune and S3",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg]
        )
        
        # Outputs
        CfnOutput(
            self,
            "OptimizationFunctionArn",
            value=self.optimization_function.function_arn,
            description="Optimization tool Lambda ARN"
        )
        
        CfnOutput(
            self,
            "ExplainabilityFunctionArn",
            value=self.explainability_function.function_arn,
            description="Explainability tool Lambda ARN"
        )
        
        CfnOutput(
            self,
            "DataAccessFunctionArn",
            value=self.data_access_function.function_arn,
            description="Data access tool Lambda ARN"
        )
        
        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            lambda_role,
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
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Resource::<ProcurementDataBucket28D81D70.Arn>/*",
                        # Neptune IAM-auth ARN uses the cluster resource id +
                        # "/*" (databases/queries under the cluster).
                        {"regex": "/^Resource::arn:aws:neptune-db:.*$/g"},
                        # SageMaker endpoint name is chronos-* (set at deploy).
                        {
                            "regex": "/^Resource::arn:aws:sagemaker:.*:"
                            "endpoint/chronos-\\*$/g"
                        },
                    ],
                    "reason": (
                        "Scoped S3 read to the procurement data bucket only; "
                        "wildcard actions are the GetObject/GetBucket/List "
                        "sub-actions of the grant_read permission set. The "
                        "Neptune statement is scoped to this cluster's IAM-auth "
                        "resource-id ARN (the trailing /* covers databases and "
                        "queries within the one cluster) and the SageMaker "
                        "statement is scoped to the chronos-* forecast "
                        "endpoint family."
                    ),
                },
            ],
            apply_to_children=True,
        )

        # The Python 3.11 runtime is pinned to match the shared Lambda layer,
        # whose scipy/numpy native wheels are compiled for Python 3.11
        # (compatible_runtimes=[PYTHON_3_11]). Moving the functions to a
        # newer runtime requires rebuilding those native dependencies.
        for fn in (
            self.optimization_function,
            self.explainability_function,
            self.data_access_function,
        ):
            NagSuppressions.add_resource_suppressions(
                fn,
                [
                    {
                        "id": "AwsSolutions-L1",
                        "reason": (
                            "Runtime pinned to Python 3.11 to match the shared "
                            "Lambda layer's scipy/numpy native wheels "
                            "(compiled for 3.11); a newer runtime requires "
                            "rebuilding those native dependencies."
                        ),
                    }
                ],
            )

        # LogRetention is a CDK-managed custom resource; its service role uses
        # the AWS-managed basic-execution policy and a logs:* wildcard that the
        # construct creates and the user cannot configure.
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
                        "log groups it does not know the names of at synth "
                        "time; the wildcard resource is created and managed by "
                        "the construct and is not user-configurable."
                    ),
                }
            ],
        )
