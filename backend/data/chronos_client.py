"""
SageMaker Chronos-2 Client for forecast agent bundle.

Invokes the SageMaker Chronos-2 endpoint for probabilistic
time series forecasting. Replaces the local Chronos2Pipeline
used in development.

Endpoint payload format (JumpStart pytorch-forecasting-chronos-2):
  Request:
    {
      "inputs": [{"target": [1.0, 2.0, 3.0, ...]}],
      "parameters": {"prediction_length": 90}
    }
  Response:
    {
      "predictions": [{
        "quantiles": {"0.1": [...], "0.5": [...], "0.9": [...]},
        "mean": [...]
      }]
    }
"""

import json
import os
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError


class ChronosClientError(Exception):
    """Base exception for Chronos client errors."""


class ChronosThrottlingError(ChronosClientError):
    """SageMaker endpoint throttling."""


class ChronosTimeoutError(ChronosClientError):
    """SageMaker endpoint timeout."""


class ChronosModelError(ChronosClientError):
    """SageMaker model inference error."""


class ChronosClient:
    """
    Client for invoking Chronos-2 forecast model.

    Supports two backends:
    - EC2: HTTP call to private Flask server (set CHRONOS_EC2_URL)
    - SageMaker: boto3 invoke_endpoint (set SAGEMAKER_ENDPOINT_NAME)

    EC2 is preferred when CHRONOS_EC2_URL is set.

    Usage:
        client = ChronosClient()
        result = client.forecast(
            time_series=[10, 20, 30, 40, 50],
            prediction_length=5,
        )
        # result = {"p10": [...], "p50": [...], "p90": [...], "mean": [...]}
    """

    def __init__(self, endpoint_name: str | None = None):
        self.ec2_url = os.environ.get("CHRONOS_EC2_URL", "")
        self.endpoint_name = endpoint_name or os.environ.get(
            "SAGEMAKER_ENDPOINT_NAME", ""
        )
        if not self.ec2_url:
            self.runtime = boto3.client("sagemaker-runtime")

    def forecast(
        self,
        time_series: List[float],
        prediction_length: int,
    ) -> Dict[str, List[float]]:
        """
        Invoke Chronos-2 for probabilistic forecast.

        Tries EC2 first (if configured), falls back to SageMaker.
        """
        payload = {
            "inputs": [{"target": time_series}],
            "parameters": {"prediction_length": prediction_length},
        }

        if self.ec2_url:
            return self._call_ec2(payload)
        return self._call_sagemaker(payload)

    def _call_ec2(self, payload: dict) -> Dict[str, List[float]]:
        """Call Chronos-2 on EC2 via HTTP."""
        import urllib.request

        url = f"{self.ec2_url.rstrip('/')}/forecast"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            if not url.startswith("https://"):
                raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
            with urllib.request.urlopen(req, timeout=120) as resp:  # nosemgrep: dynamic-urllib-use-detected
                result = json.loads(resp.read())
        except Exception as e:
            raise ChronosClientError(f"EC2 forecast call failed: {e}") from e

        predictions = result.get("predictions", [{}])[0]
        quantiles = predictions.get("quantiles", {})
        return {
            "p10": quantiles.get("0.1", []),
            "p50": quantiles.get("0.5", []),
            "p90": quantiles.get("0.9", []),
            "mean": predictions.get("mean", []),
        }

    def _call_sagemaker(self, payload: dict) -> Dict[str, List[float]]:
        """Call Chronos-2 on SageMaker endpoint."""
        try:
            response = self.runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload),
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]

            if error_code == "ThrottlingException":
                raise ChronosThrottlingError(
                    f"Endpoint throttled: {message}"
                ) from e
            if error_code == "ModelNotReadyException":
                raise ChronosTimeoutError(
                    f"Endpoint not ready: {message}"
                ) from e
            if error_code == "ModelError":
                raise ChronosModelError(
                    f"Model inference error: {message}"
                ) from e
            raise ChronosClientError(
                f"Endpoint invocation failed ({error_code}): {message}"
            ) from e

        body = response["Body"].read().decode("utf-8")
        result = json.loads(body)

        predictions = result.get("predictions", [{}])[0]
        mean = predictions.get("mean", [])

        return {
            "p10": predictions.get("0.1", []),
            "p50": predictions.get("0.5", []),
            "p90": predictions.get("0.9", []),
            "mean": mean,
        }
