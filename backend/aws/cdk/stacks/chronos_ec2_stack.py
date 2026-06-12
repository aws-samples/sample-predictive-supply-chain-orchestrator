"""
EC2-based Chronos-2 Forecast Server stack.

Deploys a t3.xlarge EC2 instance in a private subnet running
Chronos-2 (120M params) as a Flask API on port 8080.

Lambda calls EC2 via private IP. No public exposure.
Instance can be stopped/started to save costs.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct
from cdk_nag import NagSuppressions


STARTUP_SCRIPT = """#!/bin/bash
set -e

# Log to file
exec > /var/log/chronos-setup.log 2>&1

echo "=== Installing Chronos-2 forecast server ==="

# System deps
yum update -y
yum install -y python3.11 python3.11-pip git

# Create app directory
mkdir -p /opt/chronos
cd /opt/chronos

# Install Python deps (CPU-only PyTorch for cost savings)
python3.11 -m pip install --upgrade pip
python3.11 -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python3.11 -m pip install chronos-forecasting flask gunicorn boto3 numpy pandas

# Create the forecast server
cat > /opt/chronos/server.py << 'PYEOF'
import json
import os
import numpy as np
import torch
from flask import Flask, request, jsonify
from chronos import ChronosPipeline

app = Flask(__name__)

# Load model once at startup
print("Loading Chronos-2 model (120M params)...")
pipeline = ChronosPipeline.from_pretrained(
    "amazon/chronos-t5-base",
    device_map="cpu",
    torch_dtype=torch.float32,
)
print("Model loaded!")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "model": "chronos-t5-base-120M"})


@app.route("/forecast", methods=["POST"])
def forecast():
    data = request.json
    inputs = data.get("inputs", [])
    prediction_length = data.get("parameters", {}).get("prediction_length", 30)

    predictions = []
    for inp in inputs:
        target = inp.get("target", [])
        if not target:
            predictions.append({"quantiles": {"0.1": [], "0.5": [], "0.9": []}, "mean": []})
            continue

        context = torch.tensor([target], dtype=torch.float32)
        forecast_out = pipeline.predict(context, prediction_length=prediction_length, num_samples=20)

        # forecast_out shape: (1, num_samples, prediction_length)
        samples = forecast_out[0].numpy()
        q10 = np.quantile(samples, 0.1, axis=0).tolist()
        q50 = np.quantile(samples, 0.5, axis=0).tolist()
        q90 = np.quantile(samples, 0.9, axis=0).tolist()
        mean = np.mean(samples, axis=0).tolist()

        predictions.append({
            "quantiles": {"0.1": q10, "0.5": q50, "0.9": q90},
            "mean": mean,
        })

    return jsonify({"predictions": predictions})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
PYEOF

# Create systemd service
cat > /etc/systemd/system/chronos.service << 'SVCEOF'
[Unit]
Description=Chronos-2 Forecast Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/chronos
ExecStart=/usr/bin/python3.11 -m gunicorn -w 2 -b 0.0.0.0:8080 --timeout 120 server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

# Start the service
systemctl daemon-reload
systemctl enable chronos
systemctl start chronos

echo "=== Chronos-2 forecast server running on port 8080 ==="
"""


class ChronosEc2Stack(Stack):
    """
    EC2-based Chronos-2 forecast server in a private subnet.

    - t3.xlarge (4 vCPU, 16GB RAM) for 120M param model
    - Private subnet, accessible only from Lambda SG
    - Flask API on port 8080
    - Stop/start to save costs
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        lambda_sg: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Security group — only Lambda can reach port 8080
        self.ec2_sg = ec2.SecurityGroup(
            self, "ChronosSG",
            vpc=vpc,
            description="Chronos-2 forecast server - Lambda access only",
            allow_all_outbound=True,
        )
        self.ec2_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(8080),
            description="Allow Lambda to call Chronos API",
        )

        # IAM role for EC2 (SSM for management, no SSH needed)
        role = iam.Role(
            self, "ChronosRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # EC2 instance
        self.instance = ec2.Instance(
            self, "ChronosInstance",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType("t3.xlarge"),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023,
            ),
            security_group=self.ec2_sg,
            role=role,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(30),  # 30GB for model + deps
                )
            ],
            user_data=ec2.UserData.custom(STARTUP_SCRIPT),
        )

        # Outputs
        CfnOutput(self, "ChronosInstanceId",
                  value=self.instance.instance_id,
                  description="EC2 instance ID (stop/start to save costs)")

        CfnOutput(self, "ChronosPrivateIp",
                  value=self.instance.instance_private_ip,
                  description="Private IP for Lambda to call Chronos API")

        CfnOutput(self, "ChronosEndpointUrl",
                  value=f"http://{self.instance.instance_private_ip}:8080",
                  description="Chronos forecast API URL (private)")

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            role,
            [
                {"id": "AwsSolutions-IAM4", "reason": "SSM managed policy for instance management"},
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            self.instance,
            [
                {"id": "AwsSolutions-EC26", "reason": "EBS encryption not required for hackathon demo"},
                {"id": "AwsSolutions-EC28", "reason": "Detailed monitoring not required for hackathon"},
                {"id": "AwsSolutions-EC29", "reason": "ASG termination protection not needed — single instance for demos"},
            ],
        )
