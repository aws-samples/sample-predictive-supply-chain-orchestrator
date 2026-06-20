"""
Neptune Loader Stack - CDK Custom Resource for data loading.

Creates a Custom Resource that loads data into Neptune using the bulk loader.
Runs automatically on stack CREATE and UPDATE.

Follows CDE standards:
- cdk-nag compliant
- Minimal IAM permissions (POLP)
- VPC Lambda for Neptune access
- Comprehensive error handling
"""

from aws_cdk import (
    Stack,
    Duration,
    CustomResource,
    SymlinkFollowMode,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_neptune as neptune,
    custom_resources as cr,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions


class NeptuneLoaderStack(Stack):
    """
    Neptune data loader stack using Custom Resource.
    
    Automatically loads data into Neptune on stack creation/update.
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        neptune_cluster: neptune.CfnDBCluster,
        data_bucket: s3.IBucket,
        neptune_s3_role_arn: str,
        vpc: ec2.IVpc,
        lambda_sg: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Lambda execution role
        loader_role = iam.Role(
            self,
            "NeptuneLoaderLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Neptune loader Lambda"
        )
        
        # Grant S3 permissions (read application CSVs, write Neptune CSVs)
        data_bucket.grant_read_write(loader_role)

        # Grant VPC execution permissions
        loader_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        # Grant Neptune IAM-auth permissions (required when
        # iam_auth_enabled=True). Neptune IAM auth uses the cluster resource ID
        # (not the cluster identifier) in ARNs, so attr_cluster_resource_id is
        # used. Scoped to the bulk-loader + query actions the loader needs
        # rather than the full neptune-db:* action set.
        loader_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "neptune-db:connect",
                    "neptune-db:StartLoaderJob",
                    "neptune-db:GetLoaderJobStatus",
                    "neptune-db:ReadDataViaQuery",
                    "neptune-db:WriteDataViaQuery",
                    "neptune-db:GetQueryStatus",
                ],
                resources=[
                    (
                        f"arn:aws:neptune-db:{Stack.of(self).region}:"
                        f"{Stack.of(self).account}:"
                        f"{neptune_cluster.attr_cluster_resource_id}/*"
                    )
                ]
            )
        )
        
        # Lambda function for Custom Resource
        loader_function = lambda_.Function(
            self,
            "NeptuneLoaderFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="neptune_loader_custom_resource.handler",
            code=lambda_.Code.from_asset("../lambda_tools", follow_symlinks=SymlinkFollowMode.ALWAYS),
            role=loader_role,
            timeout=Duration.minutes(15),
            memory_size=512,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg],
            environment={
                "NEPTUNE_ENDPOINT": neptune_cluster.attr_endpoint,
                "S3_BUCKET": data_bucket.bucket_name,
                "IAM_ROLE_ARN": neptune_s3_role_arn
            }
        )
        
        # Custom Resource Provider
        provider = cr.Provider(
            self,
            "NeptuneLoaderProvider",
            on_event_handler=loader_function
        )
        
        # Custom Resource
        loader_resource = CustomResource(
            self,
            "NeptuneLoaderResource",
            service_token=provider.service_token,
            properties={
                "S3Bucket": data_bucket.bucket_name,
                "NeptuneEndpoint": neptune_cluster.attr_endpoint,
                "IamRoleArn": neptune_s3_role_arn
            }
        )
        
        # Ensure Neptune cluster is ready before loading
        loader_resource.node.add_dependency(neptune_cluster)
        
        # Outputs
        CfnOutput(
            self,
            "LoaderFunctionArn",
            value=loader_function.function_arn,
            description="Neptune loader Lambda function ARN"
        )
        
        CfnOutput(
            self,
            "LoaderStatus",
            value=loader_resource.get_att_string("Status"),
            description="Neptune data load status"
        )
        
        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            loader_role,
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
                        "Action::s3:Abort*",
                        "Action::s3:DeleteObject*",
                        "Resource::<ProcurementDataBucket28D81D70.Arn>/*",
                        {"regex": "/^Resource::arn:aws:neptune-db:.*$/g"},
                    ],
                    "reason": (
                        "Scoped S3 read/write to the procurement data bucket "
                        "only; the wildcard actions are the "
                        "GetObject/GetBucket/List/Abort/DeleteObject "
                        "sub-actions of the grant_read_write permission set "
                        "the loader uses to read application CSVs and write "
                        "Neptune-format CSVs. The neptune-db statement is "
                        "scoped to this cluster's resource ID."
                    ),
                },
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            loader_function,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": (
                        "Runtime pinned to Python 3.11 to match the loader's "
                        "deployment package and the shared dependency layout; "
                        "moving to a newer runtime requires revalidating the "
                        "bundled dependencies."
                    ),
                }
            ],
        )

        # The custom-resource Provider framework Lambda and its role are
        # created and managed by the CDK Provider construct and are not
        # user-configurable.
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/NeptuneLoaderProvider/framework-onEvent/ServiceRole/Resource",
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/"
                        "service-role/AWSLambdaBasicExecutionRole",
                    ],
                    "reason": (
                        "AWS-managed basic-execution role is required by the "
                        "CDK Provider framework Lambda; not user-configurable."
                    ),
                }
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/NeptuneLoaderProvider/framework-onEvent/ServiceRole/"
            "DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "appliesTo": [
                        "Resource::<NeptuneLoaderFunction36609461.Arn>:*",
                    ],
                    "reason": (
                        "The CDK Provider framework grants lambda:InvokeFunction "
                        "on all versions/aliases of the loader function it "
                        "fronts; this is created by the Provider construct and "
                        "is not user-configurable."
                    ),
                }
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/" + self.stack_name
            + "/NeptuneLoaderProvider/framework-onEvent/Resource",
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": (
                        "Runtime is managed by the CDK Provider framework "
                        "construct and is not user-configurable."
                    ),
                }
            ],
        )
