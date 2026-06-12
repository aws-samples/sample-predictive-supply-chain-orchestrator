"""
SageMaker Chronos-2 Forecast Endpoint stack.

Deploys the IAM role and exports the endpoint name for the Chronos-2
SageMaker endpoint. The actual endpoint is deployed by the script:
  demand-forecasting/scripts/deploy_chronos_endpoint.py

This avoids requiring the heavy sagemaker SDK at CDK synth time.
The deploy script uses JumpStartModel.deploy() which correctly
resolves the model artifact URI and container image.

Model: pytorch-forecasting-chronos-2 (120M parameters)
Instance: ml.g5.2xlarge (GPU — NVIDIA A10G)
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions


# Must match the endpoint name in deploy_chronos_endpoint.py
ENDPOINT_NAME = "chronos-2-forecast-endpoint"


class SageMakerForecastStack(Stack):
    """
    SageMaker Chronos-2 forecast IAM + reference stack.

    Creates:
    - IAM execution role for SageMaker (used by deploy script)
    - Exports endpoint name for cross-stack reference

    The SageMaker Model, EndpointConfig, and Endpoint are created
    by deploy_chronos_endpoint.py using JumpStartModel.deploy().
    Run the script BEFORE deploying the Forecast Agent stack.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SageMaker execution role — used by the deploy script
        self.sagemaker_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
            ],
            description="Execution role for SageMaker Chronos-2 forecast endpoint",
        )

        # CloudWatch Logs for endpoint
        self.sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/*",
                ],
            )
        )

        # S3 read for JumpStart model artifacts (not covered by AmazonSageMakerFullAccess)
        self.sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    "arn:aws:s3:::jumpstart-cache-prod-*",
                    "arn:aws:s3:::jumpstart-cache-prod-*/*",
                ],
            )
        )

        # Store endpoint name for cross-stack reference
        self._endpoint_name = ENDPOINT_NAME

        # Outputs
        CfnOutput(
            self,
            "SageMakerEndpointName",
            value=self._endpoint_name,
            description="SageMaker Chronos-2 forecast endpoint name",
        )

        CfnOutput(
            self,
            "SageMakerRoleArn",
            value=self.sagemaker_role.role_arn,
            description="SageMaker execution role ARN (pass to deploy script with --role-arn)",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.sagemaker_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "AmazonSageMakerFullAccess managed policy required for JumpStart model deployment",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CloudWatch wildcard for log streams",
                },
            ],
            apply_to_children=True,
        )

    @property
    def endpoint_name(self) -> str:
        """SageMaker endpoint name for cross-stack reference."""
        return self._endpoint_name

    @property
    def role_arn(self) -> str:
        """SageMaker execution role ARN for the deploy script."""
        return self.sagemaker_role.role_arn
