"""
AgentCore Runtime entrypoint for procurement optimization agent.

Uses BedrockAgentCoreApp to expose the Strands agent via AgentCore Runtime.
"""

import os

import structlog
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = structlog.get_logger()

from agents.procurement_agent import (
    optimize_suppliers,
    explain_solution,
    query_supplier_data,
    create_purchase_requisitions,
)

app = BedrockAgentCoreApp()

# Wrap tool functions with @tool decorator for Strands
optimize_tool = tool(optimize_suppliers)
explain_tool = tool(explain_solution)
query_tool = tool(query_supplier_data)
pr_tool = tool(create_purchase_requisitions)

# Create agent with Bedrock model
model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
model = BedrockModel(
    model_id=model_id,
)

agent = Agent(
    model=model,
    tools=[optimize_tool, explain_tool, query_tool, pr_tool],
    system_prompt="""You are a procurement optimization assistant for VoltCycle, an e-bike manufacturer.
You help users optimize supplier selection for manufacturing materials. You can:

1. Run multi-objective optimization to find Pareto-optimal supplier mixes
2. Explain optimization decisions in business terms
3. Query supplier network data to find alternatives and performance metrics
4. Create purchase requisitions from selected solutions

Always provide clear, actionable recommendations with reasoning.
When asked to optimize, use realistic constraints unless the user specifies otherwise.
Format currency values and percentages clearly.""",
)


@app.entrypoint
def procurement_agent_handler(payload):
    """
    Invoke the procurement agent with a payload.
    Expected payload: {"prompt": "optimize for 500 e-bikes"}
    """
    user_input = payload.get("prompt", "")
    # Do not log the full user input — it may contain PII. Log length only.
    logger.info("invoke", input_length=len(user_input))
    response = agent(user_input)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
