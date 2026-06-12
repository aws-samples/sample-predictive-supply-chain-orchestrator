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
    Client for invoking the SageMaker Chronos-2 endpoint.

    Usage:
        client = ChronosClient(endpoint_name="chronos-2-forecast-endpoint")
        result = client.forecast(
            time_series=[10, 20, 30, 40, 50],
            prediction_length=5,
        )
        # result = {"p10": [...], "p50": [...], "p90": [...], "mean": [...]}
    """

    def __init__(self, endpoint_name: str | None = None):
        """
        Initialize Chronos client.

        Args:
            endpoint_name: SageMaker endpoint name.
                Defaults to SAGEMAKER_ENDPOINT_NAME env var.
        """
        self.endpoint_name = endpoint_name or os.environ.get(
            "SAGEMAKER_ENDPOINT_NAME", ""
        )
        self.runtime = boto3.client("sagemaker-runtime")

    def forecast(
        self,
        time_series: List[float],
        prediction_length: int,
    ) -> Dict[str, List[float]]:
        """
        Invoke Chronos-2 SageMaker endpoint for probabilistic forecast.

        Args:
            time_series: Historical time series values.
            prediction_length: Number of future steps to predict.

        Returns:
            Dict with keys "p10", "p50", "p90", "mean", each a list
            of floats with length == prediction_length.

        Raises:
            ChronosThrottlingError: If endpoint is throttled.
            ChronosTimeoutError: If endpoint times out.
            ChronosModelError: If model returns an error.
            ChronosClientError: For other invocation errors.
        """
        payload = {
            "inputs": [{"target": time_series}],
            "parameters": {"prediction_length": prediction_length},
        }

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

        # Parse response
        body = response["Body"].read().decode("utf-8")
        result = json.loads(body)

        # Extract quantile predictions from JumpStart response format
        predictions = result.get("predictions", [{}])[0]
        mean = predictions.get("mean", [])

        return {
            "p10": predictions.get("0.1", []),
            "p50": predictions.get("0.5", []),
            "p90": predictions.get("0.9", []),
            "mean": mean,
        }
