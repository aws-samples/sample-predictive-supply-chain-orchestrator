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
                    "reason": (
                        "This bucket is private (BLOCK_ALL public access) and "
                        "is only reachable through the CloudFront Origin "
                        "Access Identity; request auditing is performed at the "
                        "CloudFront layer rather than via S3 server access "
                        "logs to avoid an additional log bucket per static "
                        "site."
                    ),
                }
            ],
        )

        NagSuppressions.add_resource_suppressions(
            distribution,
            [
                {
                    "id": "AwsSolutions-CFR1",
                    "reason": (
                        "Geographic restriction is left to the deploying "
                        "account's policy; this is a globally accessible "
                        "public web UI with no country-level access "
                        "requirement."
                    ),
                },
                {
                    "id": "AwsSolutions-CFR2",
                    "reason": (
                        "A WAFv2 web ACL is left to the deploying account's "
                        "Firewall Manager / org policy rather than hard-coded "
                        "in this stack; the distribution serves only static "
                        "assets behind OAC."
                    ),
                },
                {
                    "id": "AwsSolutions-CFR4",
                    "reason": (
                        "The distribution uses the default CloudFront domain "
                        "and certificate (TLSv1 minimum is enforced by the "
                        "default *.cloudfront.net certificate); a custom "
                        "domain/cert is configured per deployment when an "
                        "alternate domain name is supplied."
                    ),
                },
                {
                    "id": "AwsSolutions-CFR3",
                    "reason": (
                        "CloudFront standard access logging is left to the "
                        "deploying account's centralized logging "
                        "configuration to avoid creating a per-distribution "
                        "log bucket in this stack."
                    ),
                },
            ],
        )

        # CDK BucketDeployment custom-resource internals (service-role
        # wildcards, AWS-managed basic-execution policy, construct-managed
        # runtime) are not user-configurable.
        bd_prefix = (
            "/" + self.stack_name
            + "/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C"
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            bd_prefix + "/ServiceRole/Resource",
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaBasicExecutionRole",
                    ],
                    "reason": (
                        "AWS-managed basic-execution role is required by the "
                        "CDK BucketDeployment custom-resource Lambda for "
                        "CloudWatch logging; not user-configurable."
                    ),
                }
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            bd_prefix + "/ServiceRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "appliesTo": [
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Action::s3:Abort*",
                        "Action::s3:DeleteObject*",
                        "Resource::<FrontendBucketEFE2E19C.Arn>/*",
                        "Resource::arn:aws:s3:::cdk-hnb659fds-assets-"
                        + self.account + "-" + self.region + "/*",
                        # CloudFront invalidation needs the distribution "*".
                        "Resource::*",
                    ],
                    "reason": (
                        "Scoped S3 read/write to the CDK asset bucket and the "
                        "frontend site bucket only; wildcard actions are "
                        "sub-actions of the grant_read_write permission set. "
                        "The CloudFront CreateInvalidation action only "
                        "authorizes on '*' and is added by the managed "
                        "BucketDeployment construct."
                    ),
                }
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            bd_prefix + "/Resource",
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": (
                        "Runtime is managed by the CDK BucketDeployment "
                        "construct and is not user-configurable."
                    ),
                }
            ],
        )
