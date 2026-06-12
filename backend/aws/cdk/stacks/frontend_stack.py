"""
Frontend hosting stack with S3 + CloudFront + Cognito.

Deploys the React UI to S3 behind CloudFront CDN
with Cognito authentication.
"""

import os

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cognito as cognito,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class FrontendStack(Stack):
    """
    Frontend hosting stack.

    Creates:
    - S3 bucket for static website hosting
    - CloudFront distribution with OAC
    - Deploys built React app from dist/
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool: cognito.UserPool,
        user_pool_client: cognito.UserPoolClient,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for frontend assets
        site_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # CloudFront Origin Access Identity
        oai = cloudfront.OriginAccessIdentity(
            self,
            "FrontendOAI",
            comment="OAI for procurement agent frontend",
        )
        site_bucket.grant_read(oai)

        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    site_bucket,
                    origin_access_identity=oai,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_page_path="/index.html",
                    response_http_status=200,
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                    ttl=Duration.seconds(0),
                ),
            ],
            comment="Procurement Agent UI",
        )

        # Deploy built frontend to S3
        frontend_dist_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..",
            "procurement-agent-ui", "dist",
        )

        s3deploy.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3deploy.Source.asset(frontend_dist_path)],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # Outputs
        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="Frontend URL",
        )

        CfnOutput(
            self,
            "DistributionId",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID",
        )

        CfnOutput(
            self,
            "SiteBucketName",
            value=site_bucket.bucket_name,
            description="S3 bucket for frontend assets",
        )

        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID (for frontend config)",
        )

        CfnOutput(
            self,
            "CognitoClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito Client ID (for frontend config)",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            site_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Access logging not required for static website bucket in development",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            distribution,
            [
                {
                    "id": "AwsSolutions-CFR1",
                    "reason": "Geo restriction not needed for hackathon demo",
                },
                {
                    "id": "AwsSolutions-CFR2",
                    "reason": "WAF not needed for hackathon demo",
                },
                {
                    "id": "AwsSolutions-CFR4",
                    "reason": "Using default CloudFront certificate for demo",
                },
                {
                    "id": "AwsSolutions-CFR3",
                    "reason": "Access logging not required for demo",
                },
            ],
        )
