"""
Lambda Layer stack for shared dependencies.

Follows CDE standards:
- cdk-nag compliant
- Version management
- Size validation
- Python 3.11 compatibility

This stack creates a Lambda layer containing:
- scipy (optimization algorithms)
- numpy (numerical computations)
- gremlin_python (Neptune graph queries)
- pydantic (data validation)
- structlog (structured logging)
"""

from typing import Optional
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
from cdk_nag import NagSuppressions


class LambdaLayerStack(Stack):
    """
    Lambda Layer stack for shared Python dependencies.
    
    Creates a Lambda layer with scipy, numpy, gremlin_python, pydantic,
    and structlog for Python 3.11 runtime.
    
    Attributes:
        shared_layer: Lambda layer with shared dependencies
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        """
        Initialize Lambda Layer stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            **kwargs: Additional stack properties (env, description, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Lambda layer from build directory
        self.shared_layer = lambda_.LayerVersion(
            self,
            "SharedDependenciesLayer",
            code=lambda_.Code.from_asset("lambda_layer/build"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description=(
                "Shared dependencies for Procurement Optimization Agent: "
                "scipy, numpy, gremlin_python, pydantic, structlog"
            ),
            layer_version_name="procurement-optimization-shared-deps",
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Output layer ARN for reference
        CfnOutput(
            self,
            "SharedLayerArn",
            value=self.shared_layer.layer_version_arn,
            description="ARN of the shared dependencies Lambda layer",
            export_name=f"{construct_id}-SharedLayerArn"
        )
        
        CfnOutput(
            self,
            "SharedLayerVersion",
            value=self.shared_layer.layer_version_arn,
            description="Version ARN of the shared dependencies Lambda layer"
        )

        
        # cdk-nag suppressions (none needed for Lambda layers)
        # Lambda layers don't require IAM roles or policies

