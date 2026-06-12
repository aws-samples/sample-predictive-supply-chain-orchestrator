#!/usr/bin/env python3
"""
Deploy Chronos-2 to SageMaker via JumpStart SDK.

Usage:
    python deploy_chronos_endpoint.py [--endpoint-name NAME] [--instance-type TYPE] [--test]

Alternative to CDK-managed deployment. Use this for quick testing
or when you want to deploy the endpoint independently of CDK.

For production, prefer the CDK stack (sagemaker_forecast_stack.py)
which manages the full lifecycle via CloudFormation.
"""

import argparse
import json
import sys

import boto3


JUMPSTART_MODEL_ID = "pytorch-forecasting-chronos-2"
DEFAULT_ENDPOINT_NAME = "chronos-2-forecast-endpoint"
DEFAULT_INSTANCE_TYPE = "ml.g5.2xlarge"


def deploy_endpoint(
    endpoint_name: str = DEFAULT_ENDPOINT_NAME,
    instance_type: str = DEFAULT_INSTANCE_TYPE,
    role_arn: str | None = None,
) -> str:
    """Deploy Chronos-2 JumpStart model to a SageMaker endpoint."""
    from sagemaker.jumpstart.model import JumpStartModel

    # Check if endpoint already exists
    sm_client = boto3.client("sagemaker")
    try:
        resp = sm_client.describe_endpoint(EndpointName=endpoint_name)
        status = resp["EndpointStatus"]
        if status == "InService":
            print(f"✅ Endpoint '{endpoint_name}' already exists and is InService")
            return endpoint_name
        print(f"⚠️  Endpoint '{endpoint_name}' exists with status: {status}")
        print("   Waiting for it to become InService or delete it first.")
        return endpoint_name
    except sm_client.exceptions.ClientError:
        pass  # Endpoint doesn't exist — proceed with deployment

    print(f"🚀 Deploying {JUMPSTART_MODEL_ID} to endpoint '{endpoint_name}'...")
    print(f"   Instance type: {instance_type}")

    kwargs = {
        "model_id": JUMPSTART_MODEL_ID,
        "model_version": "2.0.2",
        "instance_type": instance_type,
    }
    if role_arn:
        kwargs["role"] = role_arn

    model = JumpStartModel(**kwargs)
    predictor = model.deploy(
        endpoint_name=endpoint_name,
        initial_instance_count=1,
        model_data_download_timeout=1200,
        container_startup_health_check_timeout=600,
    )

    print(f"✅ Endpoint '{endpoint_name}' deployed successfully")
    return endpoint_name


def test_endpoint(endpoint_name: str = DEFAULT_ENDPOINT_NAME) -> None:
    """Quick smoke test of the deployed endpoint."""
    runtime = boto3.client("sagemaker-runtime")

    payload = {
        "inputs": [{"target": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]}],
        "parameters": {"prediction_length": 5},
    }

    print(f"\n🧪 Testing endpoint '{endpoint_name}'...")
    response = runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps(payload),
    )
    result = json.loads(response["Body"].read().decode())
    print(f"   Response: {json.dumps(result, indent=2)[:500]}")
    print("✅ Endpoint test passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Chronos-2 SageMaker endpoint")
    parser.add_argument(
        "--endpoint-name",
        default=DEFAULT_ENDPOINT_NAME,
        help=f"Endpoint name (default: {DEFAULT_ENDPOINT_NAME})",
    )
    parser.add_argument(
        "--instance-type",
        default=DEFAULT_INSTANCE_TYPE,
        help=f"Instance type (default: {DEFAULT_INSTANCE_TYPE})",
    )
    parser.add_argument(
        "--role-arn",
        default=None,
        help="SageMaker execution role ARN (from CDK stack output)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run smoke test after deployment",
    )
    args = parser.parse_args()

    endpoint_name = deploy_endpoint(
        endpoint_name=args.endpoint_name,
        instance_type=args.instance_type,
        role_arn=args.role_arn,
    )

    if args.test:
        test_endpoint(endpoint_name)


if __name__ == "__main__":
    main()
