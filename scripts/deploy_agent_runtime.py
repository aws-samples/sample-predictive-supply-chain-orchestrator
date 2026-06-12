#!/usr/bin/env python3
"""
Deploy procurement agent to AgentCore Runtime using the starter toolkit.

Reads all IDs dynamically from CDK stack outputs — no hardcoded values.

Usage:
    python3 scripts/deploy_agent_runtime.py
    python3 scripts/deploy_agent_runtime.py --region us-east-1

The runtime receives the user's Cognito JWT via request headers and
forwards it to the Gateway for tool authentication.
"""

import argparse
import os
import sys
import time

import boto3
from bedrock_agentcore_starter_toolkit import Runtime

PROJECT_NAME = "procurement-optimization-agent"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


def get_stack_output(cf_client, stack_suffix: str, output_key: str) -> str:
    """Read a CDK stack output value."""
    stack_name = f"{PROJECT_NAME}-{stack_suffix}-{ENVIRONMENT}"
    try:
        resp = cf_client.describe_stacks(StackName=stack_name)
        for output in resp["Stacks"][0].get("Outputs", []):
            if output["OutputKey"] == output_key:
                return output["OutputValue"]
    except Exception as e:
        print(f"  Warning: could not read {output_key} from {stack_name}: {e}")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Deploy procurement agent to AgentCore")
    parser.add_argument("--region", default=None, help="AWS region")
    args = parser.parse_args()

    region = args.region or boto3.session.Session().region_name or "us-east-1"
    cf = boto3.client("cloudformation", region_name=region)

    # Read IDs from CDK stack outputs
    print("Reading configuration from CDK stack outputs...")
    memory_id = os.environ.get("MEMORY_ID") or get_stack_output(cf, "memory", "MemoryId")
    gateway_id = os.environ.get("GATEWAY_ID") or get_stack_output(cf, "gateway", "GatewayId")
    guardrail_id = os.environ.get("GUARDRAIL_ID") or get_stack_output(cf, "guardrail", "GuardrailId")
    guardrail_version = os.environ.get("GUARDRAIL_VERSION") or get_stack_output(cf, "guardrail", "GuardrailVersion") or "1"
    cognito_client_id = os.environ.get("COGNITO_CLIENT_ID") or get_stack_output(cf, "identity", "UserPoolClientId")
    cognito_pool_id = os.environ.get("COGNITO_POOL_ID") or get_stack_output(cf, "identity", "UserPoolId")

    cognito_discovery_url = os.environ.get(
        "COGNITO_DISCOVERY_URL",
        f"https://cognito-idp.{region}.amazonaws.com/{cognito_pool_id}/.well-known/openid-configuration"
        if cognito_pool_id else "",
    )

    agent_name = "procurement_optimization_agent"
    entrypoint = os.path.join(os.path.dirname(__file__), "..", "backend", "agentcore_bundle", "main.py")
    requirements = os.path.join(os.path.dirname(__file__), "..", "backend", "agentcore_bundle", "requirements.txt")

    print(f"  Agent:    {agent_name}")
    print(f"  Region:   {region}")
    print(f"  Memory:   {memory_id or '(none)'}")
    print(f"  Gateway:  {gateway_id or '(none)'}")
    print(f"  Guardrail: {guardrail_id or '(none)'}")
    print(f"  Cognito:  {cognito_client_id or '(none)'}")
    print()

    runtime = Runtime()

    # Configure with JWT authorizer if Cognito is available
    configure_kwargs = {
        "entrypoint": entrypoint,
        "auto_create_execution_role": True,
        "requirements_file": requirements,
        "region": region,
        "agent_name": agent_name,
    }

    if cognito_client_id and cognito_discovery_url:
        configure_kwargs["authorizer_configuration"] = {
            "customJWTAuthorizer": {
                "allowedClients": [cognito_client_id],
                "discoveryUrl": cognito_discovery_url,
            }
        }
        configure_kwargs["request_header_configuration"] = {
            "requestHeaderAllowlist": ["Authorization"],
        }

    response = runtime.configure(**configure_kwargs)
    print(f"Configured: {response}")

    # Launch with env vars
    env_vars = {
        "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    }
    if memory_id:
        env_vars["MEMORY_ID"] = memory_id
    if gateway_id:
        env_vars["GATEWAY_ID"] = gateway_id
    if guardrail_id:
        env_vars["GUARDRAIL_ID"] = guardrail_id
        env_vars["GUARDRAIL_VERSION"] = guardrail_version

    launch_result = runtime.launch(env_vars=env_vars, auto_update_on_conflict=True)
    print(f"Agent ARN: {launch_result.agent_arn}")

    # Wait for ready
    end_statuses = {"READY", "CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"}
    while True:
        status_response = runtime.status()
        status = status_response.endpoint["status"]
        print(f"Status: {status}")
        if status in end_statuses:
            break
        time.sleep(10)  # nosemgrep: arbitrary-sleep - intentional polling delay for agent runtime deployment

    if status == "READY":
        print(f"\nAgent deployed successfully!")
        print(f"ARN: {launch_result.agent_arn}")
    else:
        print(f"\nDeployment failed: {status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
