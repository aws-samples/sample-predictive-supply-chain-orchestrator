"""
S3 Data Loader for forecast agent bundle.

Loads CSV data from S3 instead of local filesystem.
Drop-in replacement for the local load_csv() pattern used
by the forecasting agents.

Implements in-memory caching per loader instance so repeated
calls within the same request don't hit S3 again.
"""

import csv
import io
import os
from typing import Dict, List

import boto3
import pandas as pd
from botocore.exceptions import ClientError


class S3DataLoader:
    """
    Load CSV data from S3 with in-memory caching.

    Usage:
        loader = S3DataLoader(bucket_name="my-bucket", prefix="forecast-data/")
        data = loader.load_csv("bike_sales_history.csv")
        df = loader.load_dataframe("bike_sales_history.csv")
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        prefix: str = "forecast-data/",
    ):
        """
        Initialize S3 data loader.

        Args:
            bucket_name: S3 bucket name. Defaults to DATA_BUCKET env var.
            prefix: S3 key prefix for forecast data files.
        """
        self.bucket = bucket_name or os.environ.get("DATA_BUCKET", "")
        self.prefix = prefix
        self.s3 = boto3.client("s3")
        self._cache: Dict[str, str] = {}  # filename -> raw CSV text

    def _get_s3_key(self, filename: str) -> str:
        """Build full S3 key from prefix and filename."""
        return f"{self.prefix}{filename}"

    def _fetch_raw(self, filename: str) -> str:
        """
        Fetch raw CSV text from S3, with caching.

        Returns cached content if already loaded in this instance.
        """
        if filename in self._cache:
            return self._cache[filename]

        s3_key = self._get_s3_key(filename)
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            body = response["Body"].read().decode("utf-8")
            self._cache[filename] = body
            return body
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(
                    f"S3 file not found: s3://{self.bucket}/{s3_key}"
                ) from e
            if error_code == "AccessDenied":
                raise PermissionError(
                    f"Access denied to S3 file: s3://{self.bucket}/{s3_key}"
                ) from e
            raise

    def load_csv(self, filename: str) -> List[Dict[str, str]]:
        """
        Load a CSV file from S3 and return list of dicts.

        This is a drop-in replacement for the local load_csv() used
        by the forecasting agents.

        Args:
            filename: CSV filename (e.g., "bike_sales_history.csv")

        Returns:
            List of dicts, one per row, keyed by column headers.

        Raises:
            FileNotFoundError: If the file doesn't exist in S3.
            PermissionError: If access is denied.
        """
        raw = self._fetch_raw(filename)
        reader = csv.DictReader(io.StringIO(raw))
        return list(reader)

    def load_dataframe(self, filename: str) -> pd.DataFrame:
        """
        Load a CSV file from S3 as a pandas DataFrame.

        Args:
            filename: CSV filename (e.g., "bike_sales_history.csv")

        Returns:
            pandas DataFrame with the file contents.

        Raises:
            FileNotFoundError: If the file doesn't exist in S3.
            PermissionError: If access is denied.
        """
        raw = self._fetch_raw(filename)
        return pd.read_csv(io.StringIO(raw))

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
