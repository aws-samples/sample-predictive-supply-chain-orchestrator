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
        
        # Grant Neptune access — neptune-db:* needed for HTTP API (SigV4)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["neptune-db:*"],
                resources=[f"arn:aws:neptune-db:{self.region}:{self.account}:*/*"]
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
                    "reason": "AWSLambdaVPCAccessExecutionRole is AWS managed policy required for VPC access"
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions required for Neptune cluster access and S3 bucket operations"
                }
            ],
            apply_to_children=True
        )
