"""
Data stack with Neptune graph database and S3 storage.

Follows CDE standards:
- cdk-nag compliant
- Encryption at rest
- VPC isolation for Neptune
- Proper IAM policies
"""

from aws_cdk import (
    Stack,
    aws_neptune as neptune,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_ec2 as ec2,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions


class DataStack(Stack):
    """
    Data layer stack.
    
    Creates:
    - Neptune graph database cluster
    - S3 bucket for data storage
    - VPC for Neptune isolation
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # VPC for Neptune (required)
        self.vpc = ec2.Vpc(
            self,
            "ProcurementVPC",
            max_azs=2,
            nat_gateways=1,
            gateway_endpoints={
                "S3": ec2.GatewayVpcEndpointOptions(
                    service=ec2.GatewayVpcEndpointAwsService.S3
                )
            },
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ]
        )
        
        # Security group for Neptune
        self.neptune_sg = ec2.SecurityGroup(
            self,
            "NeptuneSG",
            vpc=self.vpc,
            description="Security group for Neptune cluster",
            allow_all_outbound=False
        )

        # Allow inbound from VPC on Neptune port
        self.neptune_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8182),
            description="Allow Gremlin connections from VPC"
        )

        # Allow Neptune outbound HTTPS for S3 bulk loader access via VPC endpoint
        self.neptune_sg.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS outbound for S3 bulk loader"
        )

        # Security group for Lambda functions (needs outbound for S3, Neptune, CloudWatch)
        self.lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSG",
            vpc=self.vpc,
            description="Security group for Lambda functions accessing Neptune",
            allow_all_outbound=True
        )

        # Allow Neptune to accept inbound from Lambda SG on port 8182
        self.neptune_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(8182),
            description="Allow Neptune access from Lambda functions"
        )

        # Neptune subnet group
        subnet_group = neptune.CfnDBSubnetGroup(
            self,
            "NeptuneSubnetGroup",
            db_subnet_group_description="Subnet group for Neptune cluster",
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets]
        )
        
        # Neptune cluster
        self.neptune_cluster = neptune.CfnDBCluster(
            self,
            "SupplierNetworkGraph",
            storage_encrypted=True,
            iam_auth_enabled=True,
            vpc_security_group_ids=[self.neptune_sg.security_group_id],
            db_subnet_group_name=subnet_group.ref,
            backup_retention_period=7,
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="mon:04:00-mon:05:00"
        )
        
        self.neptune_cluster.add_dependency(subnet_group)
        
        # Neptune instance
        neptune_instance = neptune.CfnDBInstance(
            self,
            "NeptuneInstance",
            db_instance_class="db.t3.medium",
            db_cluster_identifier=self.neptune_cluster.ref,
            auto_minor_version_upgrade=True
        )
        
        neptune_instance.add_dependency(self.neptune_cluster)
        
        # Dedicated bucket for S3 server access logs (kept self-contained
        # in this stack). It is its own access-log target to avoid a
        # recursive logging loop.
        access_logs_bucket = s3.Bucket(
            self,
            "ProcurementAccessLogsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED
        )

        # S3 bucket for data storage
        self.data_bucket = s3.Bucket(
            self,
            "ProcurementDataBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix="data-bucket-access-logs/"
        )
        
        # Upload CSV data files to S3 so the Neptune loader can find them
        s3deploy.BucketDeployment(
            self,
            "UploadCsvData",
            sources=[s3deploy.Source.asset("../../../data")],
            destination_bucket=self.data_bucket,
            destination_key_prefix="csv-data"
        )

        # Upload forecast CSV data to S3 for the demand forecasting agent
        s3deploy.BucketDeployment(
            self,
            "UploadForecastData",
            sources=[s3deploy.Source.asset("../../../demand-forecasting/data")],
            destination_bucket=self.data_bucket,
            destination_key_prefix="forecast-data"
        )

        # IAM role for Neptune to access S3 (for bulk loader)
        neptune_s3_role = iam.Role(
            self,
            "NeptuneS3AccessRole",
            assumed_by=iam.ServicePrincipal("rds.amazonaws.com"),
            description="Allows Neptune to read from S3 for bulk loading"
        )
        
        self.data_bucket.grant_read(neptune_s3_role)
        
        # Store role ARN for use in other stacks
        self.neptune_s3_role_arn = neptune_s3_role.role_arn
        
        # Associate role with Neptune cluster
        self.neptune_cluster.add_property_override(
            "AssociatedRoles",
            [{"RoleArn": neptune_s3_role.role_arn}]
        )
        
        # Outputs
        CfnOutput(
            self,
            "NeptuneEndpoint",
            value=self.neptune_cluster.attr_endpoint,
            description="Neptune cluster endpoint"
        )
        
        CfnOutput(
            self,
            "NeptunePort",
            value=self.neptune_cluster.attr_port,
            description="Neptune cluster port"
        )
        
        CfnOutput(
            self,
            "DataBucketName",
            value=self.data_bucket.bucket_name,
            description="S3 bucket for procurement data"
        )
        
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID for Neptune access"
        )
        
        CfnOutput(
            self,
            "NeptuneS3RoleArn",
            value=neptune_s3_role.role_arn,
            description="IAM role ARN for Neptune S3 access"
        )
        
        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.vpc,
            [
                {
                    "id": "AwsSolutions-VPC7",
                    "reason": (
                        "Neptune and the Lambda tools run in private subnets "
                        "with security-group isolation; VPC Flow Logs are not "
                        "enabled to keep this reference stack self-contained "
                        "and avoid a CloudWatch Logs cost with no consumer in "
                        "this sample. Operators can enable flow logs by adding "
                        "flow_logs to the Vpc construct."
                    )
                }
            ]
        )

        NagSuppressions.add_resource_suppressions(
            self.neptune_sg,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": (
                        "Ingress is restricted to the VPC CIDR (and the Lambda "
                        "security group) on the Neptune port only. The rule "
                        "references the VPC CidrBlock intrinsic which the nag "
                        "rule cannot resolve at synth time."
                    )
                },
                {
                    "id": "CdkNagValidationFailure",
                    "reason": (
                        "AwsSolutions-EC23 cannot validate the ingress peer "
                        "because it is the VPC CidrBlock intrinsic "
                        "(Fn::GetAtt), not a literal CIDR. Ingress is scoped "
                        "to the VPC CIDR on the Neptune port only."
                    )
                }
            ]
        )

        # The access-logs bucket is its own server-access-log target, which
        # would create a recursive logging loop, so logging is intentionally
        # not enabled on it.
        NagSuppressions.add_resource_suppressions(
            access_logs_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": (
                        "This bucket is the dedicated server-access-log "
                        "destination for the data bucket; enabling access "
                        "logging on it would create a self-referential "
                        "logging loop."
                    )
                }
            ]
        )

        # S3 grant_read on the Neptune bulk-loader role expands to scoped
        # read sub-actions on this bucket only.
        NagSuppressions.add_resource_suppressions(
            neptune_s3_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "appliesTo": [
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Resource::<ProcurementDataBucket28D81D70.Arn>/*",
                    ],
                    "reason": (
                        "Scoped S3 read to the procurement data bucket only; "
                        "the wildcard actions are the GetObject/GetBucket/List "
                        "sub-actions of the grant_read permission set the "
                        "Neptune bulk loader needs to read CSV objects."
                    )
                }
            ],
            apply_to_children=True
        )

        # CDK BucketDeployment custom-resource internals: service role
        # wildcards, the AWS-managed basic-execution policy, and the
        # construct-managed Lambda runtime are not user-configurable. The two
        # BucketDeployments share one singleton custom-resource handler.
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
                        "CloudWatch logging; an equivalent customer-managed "
                        "policy adds maintenance burden without security "
                        "benefit for a sample."
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
                        "Resource::<ProcurementDataBucket28D81D70.Arn>/*",
                        "Resource::arn:aws:s3:::cdk-hnb659fds-assets-"
                        + self.account
                        + "-"
                        + self.region
                        + "/*",
                    ],
                    "reason": (
                        "Scoped S3 read/write to the CDK asset bucket and the "
                        "destination data bucket only; wildcard actions are "
                        "sub-actions of the grant_read_write permission set "
                        "used by the managed BucketDeployment construct."
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
