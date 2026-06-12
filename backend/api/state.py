"""
Shared application state initialized once and imported by Blueprint modules.
"""

import json
import os
from collections import defaultdict
from typing import Dict, Any, Optional

import boto3
import numpy as np
import pandas as pd
import structlog

from config.settings import settings
from core.optimization.engine import OptimizationEngine
from data.csv_reader import CSVDataReader

logger = structlog.get_logger()

# ── Forecast lazy loaders ──

_forecast_s3_loader = None
_forecast_chronos_client = None


def _build_agentcore_arn(agent_id: str) -> str:
    if agent_id.startswith("arn:"):
        return agent_id
    region = os.environ.get("AWS_REGION", "us-east-1")
    account = os.environ.get("AWS_ACCOUNT_ID", "")
    if not account:
        account = boto3.client("sts").get_caller_identity()["Account"]
    return f"arn:aws:bedrock-agentcore:{region}:{account}:runtime/{agent_id}"


def _get_forecast_s3_loader():
    global _forecast_s3_loader
    if _forecast_s3_loader is None:
        try:
            from data.s3_data_loader import S3DataLoader
            bucket = os.environ.get("DATA_BUCKET", os.environ.get("PR_S3_BUCKET", ""))
            prefix = os.environ.get("FORECAST_DATA_PREFIX", "forecast-data/")
            if bucket:
                _forecast_s3_loader = S3DataLoader(bucket_name=bucket, prefix=prefix)
        except (ImportError, ConnectionError, OSError) as e:
            logger.warning("forecast_s3_loader_init_failed", error=str(e))
    return _forecast_s3_loader


def _get_forecast_chronos_client():
    global _forecast_chronos_client
    if _forecast_chronos_client is None:
        try:
            from data.chronos_client import ChronosClient
            endpoint = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "chronos-2-forecast-endpoint")
            _forecast_chronos_client = ChronosClient(endpoint_name=endpoint)
        except (ImportError, ConnectionError, OSError) as e:
            logger.warning("forecast_chronos_client_init_failed", error=str(e))
    return _forecast_chronos_client


def _prepare_material_timeseries(material_id: str, product_id: str = None) -> pd.DataFrame:
    loader = _get_forecast_s3_loader()
    if not loader:
        return pd.DataFrame(columns=["timestamp", "target"])

    sales_data = loader.load_csv("bike_sales_history.csv")
    maint_data = loader.load_csv("maintenance_demand_history.csv")
    bom_data = loader.load_csv("bom.csv")

    bom_lookup = defaultdict(list)
    for entry in bom_data:
        bom_lookup[entry["product_id"]].append({
            "material_id": entry["material_id"],
            "quantity_required": float(entry["quantity_required"]),
        })

    demand_by_date: Dict[str, int] = defaultdict(int)
    for sale in sales_data:
        if product_id and product_id != "ALL" and sale["product_id"] != product_id:
            continue
        date = sale["timestamp"].split()[0]
        bikes_sold = int(sale["quantity_sold"])
        for bom_item in bom_lookup[sale["product_id"]]:
            if bom_item["material_id"] == material_id:
                demand_by_date[date] += int(bikes_sold * bom_item["quantity_required"])

    for maint in maint_data:
        if maint["material_id"] == material_id:
            date = maint["timestamp"].split()[0]
            demand_by_date[date] += int(maint["quantity"])

    if not demand_by_date:
        return pd.DataFrame(columns=["timestamp", "target"])

    df = pd.DataFrame([
        {"timestamp": d, "target": v} for d, v in sorted(demand_by_date.items())
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    date_range = pd.date_range(start=df["timestamp"].min(), end=df["timestamp"].max(), freq="D")
    df = df.set_index("timestamp").reindex(date_range, fill_value=0).reset_index()
    df.columns = ["timestamp", "target"]
    return df


# ── Neptune client ──

neptune_client = None
_neptune_endpoint = os.environ.get("NEPTUNE_ENDPOINT", "")
if _neptune_endpoint:
    try:
        from data.neptune_client import NeptuneClient
        neptune_client = NeptuneClient(
            endpoint=_neptune_endpoint,
            port=int(os.environ.get("NEPTUNE_PORT", "8182"))
        )
        logger.info("neptune_client_initialized", endpoint=_neptune_endpoint)
    except (ImportError, ConnectionError, OSError) as e:
        logger.warning("neptune_client_init_failed", error=str(e))

# ── Optimization engine ──

data_reader: Optional[CSVDataReader] = None
optimization_engine: Optional[OptimizationEngine] = None
try:
    data_reader = CSVDataReader(data_dir=os.environ.get("DATA_DIR", "../data"))
    optimization_engine = OptimizationEngine(data_reader)
    logger.info("optimization_engine_initialized")
except (FileNotFoundError, ValueError, OSError) as e:
    logger.error("optimization_engine_init_failed", error=str(e))

# ── Procurement agent ──

invoke_agent = None
agent_get_prs = None
_pr_store: Dict[str, Any] = {}
try:
    from agents.procurement_agent import invoke_agent, get_purchase_requisitions as agent_get_prs, _pr_store
    logger.info("procurement_agent_imported")
except (ImportError, RuntimeError) as e:
    logger.warning("procurement_agent_import_failed", error=str(e))

# ── S3 client for purchase requisitions ──

_s3_client = None
S3_BUCKET = os.environ.get("PR_S3_BUCKET", "")
S3_PREFIX = "purchase-requisitions/"


def _get_s3_client():
    global _s3_client
    if _s3_client is None and S3_BUCKET:
        try:
            _s3_client = boto3.client("s3", region_name=settings.aws_region)
        except (ConnectionError, OSError):
            pass
    return _s3_client


# ── In-memory PR store ──

_local_pr_store: Dict[str, Dict[str, Any]] = {}

# ── Buffered memory event ──

pending_memory_event = None


def _send_memory_event(user_message: str, assistant_response: str, session_id: str = None, actor_id: str = None):
    try:
        memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
        if not memory_id:
            return

        from datetime import datetime
        import uuid as _uuid

        now = datetime.now().isoformat()
        session_id = session_id or f"web-{_uuid.uuid4().hex[:8]}"
        actor_id = actor_id or "demo-user"

        region = os.environ.get("AWS_REGION", "us-east-1")
        event_payload = {
            "memoryId": memory_id,
            "actorId": actor_id,
            "sessionId": session_id,
            "eventTimestamp": now,
            "payload": [
                {"conversational": {"content": {"text": user_message}, "role": "USER"}},
                {"conversational": {"content": {"text": assistant_response[:100000]}, "role": "ASSISTANT"}},
            ],
        }

        try:
            client = boto3.client("bedrock-agentcore", region_name=region)
            client.create_event(**event_payload)
            logger.info("memory_event_sent_boto3", memory_id=memory_id, session_id=session_id)
            return
        except (ConnectionError, OSError) as boto_err:
            logger.info("memory_boto3_failed_trying_http", error=str(boto_err))

        import urllib.request
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        session = boto3.Session()
        credentials = session.get_credentials().get_frozen_credentials()

        url = f"https://bedrock-agentcore.{region}.amazonaws.com/memories/{memory_id}/events"
        body = json.dumps(event_payload).encode()

        aws_req = AWSRequest(method="POST", url=url, data=body, headers={"Content-Type": "application/json"})
        SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(aws_req)

        signed_req = urllib.request.Request(url, data=body, method="POST")
        for key, val in aws_req.headers.items():
            signed_req.add_header(key, val)

        if not url.startswith("https://"):
            raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
        with urllib.request.urlopen(signed_req, timeout=10) as resp:  # nosec B310 — SigV4-signed AWS endpoint # nosemgrep: dynamic-urllib-use-detected
            logger.info("memory_event_sent_http", status=resp.status, memory_id=memory_id, session_id=session_id)

    except (ConnectionError, OSError, ValueError) as e:
        logger.warning("memory_event_failed", error=str(e))
