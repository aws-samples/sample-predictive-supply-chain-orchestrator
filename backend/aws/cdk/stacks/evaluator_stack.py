"""
AgentCore Evaluator stack.

Creates Bedrock AgentCore Evaluators for agent quality assessment
using LLM-as-a-Judge with custom rating scales.

Resources:
- AWS::BedrockAgentCore::Evaluator (custom)
- Also uses built-in evaluators: Builtin.Helpfulness, Builtin.Correctness
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    CfnResource,
)
from constructs import Construct


class EvaluatorStack(Stack):
    """
    AgentCore Evaluator stack.

    Creates custom evaluators for procurement agent quality:
    - ToolAccuracy: Validates optimization results are correct
    - ProcurementQuality: Assesses recommendation quality for procurement domain
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Custom Evaluator: Tool Accuracy
        self.tool_accuracy_evaluator = CfnResource(
            self,
            "ToolAccuracyEvaluator",
            type="AWS::BedrockAgentCore::Evaluator",
            properties={
                "EvaluatorName": "ProcurementToolAccuracy",
                "Description": "Evaluates whether optimization tool calls produce correct, valid results",
                "Level": "TOOL_CALL",
                "EvaluatorConfig": {
                    "LlmAsAJudge": {
                        "Instructions": (
                            "You are evaluating a procurement optimization tool call for an e-bike manufacturer. "
                            "Assess whether the tool was called correctly and produced valid results.\n\n"
                            "Available tools: {available_tools}\n\n"
                            "Context: {context}\n\n"
                            "Tool call to evaluate: {tool_turn}\n\n"
                            "Check the following criteria:\n"
                            "1. Were the correct materials and quantities passed to the optimization tool?\n"
                            "2. Did the tool return valid Pareto frontier solutions (Cost-Optimized, Balanced, Risk-Diversified)?\n"
                            "3. Are the cost values positive and realistic for e-bike manufacturing?\n"
                            "4. Were constraints (supplier concentration, lead time, budget) respected?\n"
                            "5. Do allocations sum to the requested quantities?\n\n"
                            "Rate the tool call accuracy based on these criteria."
                        ),
                        "RatingScale": {
                            "Numerical": [
                                {"Value": 1.0, "Label": "Incorrect", "Definition": "Tool call failed, returned errors, or produced invalid/impossible results"},
                                {"Value": 2.0, "Label": "Partially Correct", "Definition": "Tool returned results but with constraint violations or incorrect allocations"},
                                {"Value": 3.0, "Label": "Mostly Correct", "Definition": "Results are valid but minor issues like suboptimal diversification"},
                                {"Value": 4.0, "Label": "Correct", "Definition": "All results valid, constraints respected, allocations sum correctly"},
                                {"Value": 5.0, "Label": "Excellent", "Definition": "Perfect results with clear Pareto differentiation and all constraints satisfied"},
                            ],
                        },
                        "ModelConfig": {
                            "BedrockEvaluatorModelConfig": {
                                "ModelId": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                                "InferenceConfig": {
                                    "MaxTokens": 1024,
                                    "Temperature": 0.0,
                                },
                            }
                        },
                    }
                },
            },
        )

        # Custom Evaluator: Procurement Quality (session-level)
        self.quality_evaluator = CfnResource(
            self,
            "ProcurementQualityEvaluator",
            type="AWS::BedrockAgentCore::Evaluator",
            properties={
                "EvaluatorName": "ProcurementQuality",
                "Description": "Evaluates overall quality of procurement agent sessions",
                "Level": "SESSION",
                "EvaluatorConfig": {
                    "LlmAsAJudge": {
                        "Instructions": (
                            "You are evaluating a procurement optimization agent session for VoltCycle, "
                            "an e-bike manufacturer. Assess the overall quality of the agent's assistance.\n\n"
                            "Available tools: {available_tools}\n\n"
                            "Full session (user prompts, assistant responses, tool calls): {context}\n\n"
                            "Evaluation criteria:\n"
                            "1. Task Completion: Did the agent complete the user's procurement request?\n"
                            "2. Tool Selection: Did the agent use the right tools in the right order?\n"
                            "3. Explanation Quality: Were recommendations explained with clear business reasoning?\n"
                            "4. Actionability: Could the user take action based on the agent's output?\n"
                            "5. Accuracy: Were cost figures, risk scores, and supplier data correct?\n\n"
                            "Consider the procurement context: users need to make supplier selection decisions "
                            "for manufacturing materials with cost, risk, quality, and lead time trade-offs."
                        ),
                        "RatingScale": {
                            "Numerical": [
                                {"Value": 1.0, "Label": "Poor", "Definition": "Agent failed to help with the procurement task or gave incorrect advice"},
                                {"Value": 2.0, "Label": "Below Average", "Definition": "Partial help but missing key insights or using wrong tools"},
                                {"Value": 3.0, "Label": "Average", "Definition": "Completed the task but with generic or shallow recommendations"},
                                {"Value": 4.0, "Label": "Good", "Definition": "Clear recommendations with good tool usage and business context"},
                                {"Value": 5.0, "Label": "Excellent", "Definition": "Outstanding procurement guidance with deep trade-off analysis and actionable next steps"},
                            ],
                        },
                        "ModelConfig": {
                            "BedrockEvaluatorModelConfig": {
                                "ModelId": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                                "InferenceConfig": {
                                    "MaxTokens": 2048,
                                    "Temperature": 0.0,
                                },
                            }
                        },
                    }
                },
            },
        )

        # Outputs
        CfnOutput(
            self,
            "ToolAccuracyEvaluatorId",
            value=self.tool_accuracy_evaluator.get_att("EvaluatorId").to_string(),
            description="Tool Accuracy evaluator ID",
        )

        CfnOutput(
            self,
            "ToolAccuracyEvaluatorArn",
            value=self.tool_accuracy_evaluator.get_att("EvaluatorArn").to_string(),
            description="Tool Accuracy evaluator ARN",
        )

        CfnOutput(
            self,
            "QualityEvaluatorId",
            value=self.quality_evaluator.get_att("EvaluatorId").to_string(),
            description="Procurement Quality evaluator ID",
        )

        CfnOutput(
            self,
            "QualityEvaluatorArn",
            value=self.quality_evaluator.get_att("EvaluatorArn").to_string(),
            description="Procurement Quality evaluator ARN",
        )
