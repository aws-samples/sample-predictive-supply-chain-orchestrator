"""
Identity stack with Cognito User Pool for authentication.

Follows CDE standards:
- cdk-nag validation
- Secure defaults
- Proper IAM roles
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
)
from constructs import Construct


class IdentityStack(Stack):
    """
    Identity stack with Cognito User Pool.
    
    Creates:
    - Cognito User Pool with email authentication
    - User Pool Client for frontend
    - User groups for RBAC (procurement_manager, analyst, executive)
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "ProcurementUserPool",
            user_pool_name="procurement-agent-users",
            self_sign_up_enabled=False,  # Admin creates users
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(3)
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
            # Threat protection (compromised-credential + adaptive auth).
            advanced_security_mode=cognito.AdvancedSecurityMode.ENFORCED,
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=False,
                otp=True
            )
        )

        # User Pool Client for frontend
        self.user_pool_client = self.user_pool.add_client(
            "ProcurementWebClient",
            user_pool_client_name="procurement-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
            generate_secret=False  # Public client (web/mobile)
        )

        # User groups for RBAC
        self.procurement_manager_group = cognito.CfnUserPoolGroup(
            self,
            "ProcurementManagerGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="procurement_manager",
            description="Full access to all procurement tools",
            precedence=1
        )

        self.analyst_group = cognito.CfnUserPoolGroup(
            self,
            "AnalystGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="analyst",
            description="Read-only access to data and reports",
            precedence=2
        )

        self.executive_group = cognito.CfnUserPoolGroup(
            self,
            "ExecutiveGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="executive",
            description="Access to explainability and high-level insights",
            precedence=3
        )

        # Outputs
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name=f"{self.stack_name}-UserPoolId"
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name=f"{self.stack_name}-UserPoolClientId"
        )

        CfnOutput(
            self,
            "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN",
            export_name=f"{self.stack_name}-UserPoolArn"
        )
