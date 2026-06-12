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
            db_cluster_identifier=self.neptune_cluster.ref
        )
        
        neptune_instance.add_dependency(self.neptune_cluster)
        
        # S3 bucket for data storage
        self.data_bucket = s3.Bucket(
            self,
            "ProcurementDataBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True
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
                    "reason": "VPC Flow Logs not required for demo/PoC environment"
                }
            ]
        )
        
        NagSuppressions.add_resource_suppressions(
            self.neptune_sg,
            [
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Neptune security group allows VPC CIDR for legitimate database access"
                }
            ]
        )
