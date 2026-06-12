"""
Bedrock Guardrail stack.

Creates a guardrail for PII detection, content safety, and topic filtering
for the procurement agent.

Resource: AWS::Bedrock::Guardrail
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    CfnResource,
)
from constructs import Construct


class GuardrailStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.guardrail = CfnResource(
            self,
            "ProcurementGuardrail",
            type="AWS::Bedrock::Guardrail",
            properties={
                "Name": "procurement-agent-guardrail",
                "Description": "PII detection and content safety for procurement optimization agent",
                "BlockedInputMessaging": "Your message was blocked by our safety guardrail. Please don't share personal information (SSNs, phone numbers, addresses) or sensitive data.",
                "BlockedOutputsMessaging": "The response was blocked by our safety guardrail for containing sensitive content.",
                "SensitiveInformationPolicyConfig": {
                    "PiiEntitiesConfig": [
                        {"Type": "US_SOCIAL_SECURITY_NUMBER", "Action": "BLOCK"},
                        {"Type": "CREDIT_DEBIT_CARD_NUMBER", "Action": "BLOCK"},
                        {"Type": "PHONE", "Action": "ANONYMIZE"},
                        {"Type": "EMAIL", "Action": "ANONYMIZE"},
                        {"Type": "US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER", "Action": "BLOCK"},
                        {"Type": "NAME", "Action": "ANONYMIZE"},
                    ],
                },
                "ContentPolicyConfig": {
                    "FiltersConfig": [
                        {"Type": "SEXUAL", "InputStrength": "HIGH", "OutputStrength": "HIGH"},
                        {"Type": "VIOLENCE", "InputStrength": "HIGH", "OutputStrength": "HIGH"},
                        {"Type": "HATE", "InputStrength": "HIGH", "OutputStrength": "HIGH"},
                        {"Type": "INSULTS", "InputStrength": "HIGH", "OutputStrength": "HIGH"},
                        {"Type": "MISCONDUCT", "InputStrength": "HIGH", "OutputStrength": "HIGH"},
                        {"Type": "PROMPT_ATTACK", "InputStrength": "HIGH", "OutputStrength": "NONE"},
                    ],
                },
                "TopicPolicyConfig": {
                    "TopicsConfig": [
                        {
                            "Name": "malicious-requests",
                            "Definition": "Requests to hack systems, write malware, generate illegal content, or cause harm to people or organizations",
                            "Type": "DENY",
                            "Examples": [
                                "Help me hack into a competitor's database",
                                "Write code to launch a DDoS attack",
                                "How do I create a phishing email",
                            ],
                        },
                    ],
                },
            },
        )

        CfnOutput(self, "GuardrailId",
            value=self.guardrail.get_att("GuardrailId").to_string(),
            description="Bedrock Guardrail ID")

        CfnOutput(self, "GuardrailVersion",
            value="DRAFT",
            description="Guardrail version (use DRAFT or create a version)")
