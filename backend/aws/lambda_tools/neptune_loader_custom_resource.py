"""
Neptune Loader Custom Resource Lambda Handler.

CDK Custom Resource that:
1. Transforms application CSVs to Neptune format
2. Uploads to S3
3. Invokes Neptune bulk loader
4. Polls for completion

Follows CDE standards:
- Type hints and docstrings
- Comprehensive error handling
- Structured logging
"""

import json
import csv
import time
import os
import logging
import urllib3
from typing import Dict, Any, List
from io import StringIO
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients with explicit timeouts (increased for VPC Lambda)
boto_config = Config(
    connect_timeout=60,
    read_timeout=60,
    retries={'max_attempts': 3}
)

s3_client = boto3.client('s3', config=boto_config)
session = boto3.Session()
http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=60.0, read=300.0))


def _sign_request(method: str, url: str, body: str = None, headers: dict = None) -> dict:
    """Sign an HTTP request with SigV4 for Neptune IAM auth."""
    region = os.environ.get('AWS_REGION', 'us-east-1')
    credentials = session.get_credentials().get_frozen_credentials()

    request = AWSRequest(
        method=method,
        url=url,
        data=body,
        headers=headers or {}
    )

    SigV4Auth(credentials, 'neptune-db', region).add_auth(request)
    return dict(request.headers)


def transform_suppliers_to_neptune_csv(suppliers_csv: str) -> str:
    """Transform suppliers CSV to Neptune vertex format."""
    reader = csv.DictReader(StringIO(suppliers_csv))
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        '~id', '~label', 
        'name:String', 'rating:Double', 'location:String',
        'financial_stability_score:Double', 'geopolitical_risk_score:Double',
        'active_status:Bool'
    ])
    
    for row in reader:
        writer.writerow([
            row['supplier_id'],
            'Supplier',
            row['name'],
            row['rating'],
            row['location'],
            row['financial_stability_score'],
            row['geopolitical_risk_score'],
            row['active_status'].lower()
        ])
    
    return output.getvalue()


def transform_materials_to_neptune_csv(materials_csv: str) -> str:
    """Transform materials CSV to Neptune vertex format."""
    reader = csv.DictReader(StringIO(materials_csv))
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        '~id', '~label',
        'name:String', 'category:String', 'unit_of_measure:String',
        'standard_cost:Double', 'criticality_level:String', 'weight_kg:Double'
    ])
    
    for row in reader:
        writer.writerow([
            row['material_id'],
            'Material',
            row['name'],
            row['category'],
            row['unit_of_measure'],
            row['standard_cost'],
            row['criticality_level'],
            row['weight_kg']
        ])
    
    return output.getvalue()


def transform_supplier_materials_to_neptune_csv(supplier_materials_csv: str) -> str:
    """Transform supplier_materials CSV to Neptune edge format."""
    reader = csv.DictReader(StringIO(supplier_materials_csv))
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        '~id', '~from', '~to', '~label',
        'base_price:Double', 'minimum_order_quantity:Int',
        'lead_time_days:Int', 'effective_date:Date'
    ])
    
    for row in reader:
        edge_id = f"{row['supplier_id']}-supplies-{row['material_id']}"
        writer.writerow([
            edge_id,
            row['supplier_id'],
            row['material_id'],
            'supplies',
            row['base_price'],
            row['minimum_order_quantity'],
            row['lead_time_days'],
            row['effective_date']
        ])
    
    return output.getvalue()


def read_s3_csv(bucket: str, key: str) -> str:
    """Read CSV file from S3."""
    logger.info("Reading s3://%s/%s...", bucket, key)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        logger.info("Successfully read %d bytes from s3://%s/%s", len(content), bucket, key)
        return content
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error("S3 ClientError reading s3://%s/%s: %s - %s", bucket, key, error_code, e)
        raise
    except Exception as e:
        logger.error("Unexpected error reading s3://%s/%s: %s - %s", bucket, key, type(e).__name__, e)
        raise


def upload_to_s3(bucket: str, key: str, content: str) -> None:
    """Upload content to S3."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/csv'
        )
        logger.info("Uploaded to s3://%s/%s", bucket, key)
    except ClientError as e:
        logger.error("Error uploading to s3://%s/%s: %s", bucket, key, e)
        raise


def start_neptune_bulk_load(
    neptune_endpoint: str,
    s3_bucket: str,
    s3_prefix: str,
    iam_role_arn: str,
    region: str
) -> str:
    """Start Neptune bulk loader job with SigV4 signed request."""
    loader_url = f"https://{neptune_endpoint}:8182/loader"

    payload = {
        "source": f"s3://{s3_bucket}/{s3_prefix}/",
        "format": "csv",
        "iamRoleArn": iam_role_arn,
        "region": region,
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "parserConfiguration": {
            "namedGraphUri": "http://aws.amazon.com/neptune/vocab/v01/DefaultNamedGraph"
        }
    }

    logger.info("Starting Neptune bulk load from s3://%s/%s/", s3_bucket, s3_prefix)

    body = json.dumps(payload)
    headers = {'Content-Type': 'application/json'}
    signed_headers = _sign_request('POST', loader_url, body=body, headers=headers)

    response = http.request(
        'POST',
        loader_url,
        body=body.encode('utf-8'),
        headers=signed_headers
    )

    if response.status != 200:
        raise Exception(f"Neptune bulk load failed: {response.data.decode('utf-8')}")

    result = json.loads(response.data.decode('utf-8'))
    load_id = result['payload']['loadId']

    logger.info("Bulk load started. Load ID: %s", load_id)
    return load_id


def check_neptune_load_status(neptune_endpoint: str, load_id: str) -> Dict[str, Any]:
    """Check Neptune bulk load status with SigV4 signed request."""
    status_url = f"https://{neptune_endpoint}:8182/loader/{load_id}"

    signed_headers = _sign_request('GET', status_url)

    response = http.request('GET', status_url, headers=signed_headers)

    if response.status != 200:
        raise Exception(f"Failed to check load status: {response.data.decode('utf-8')}")

    return json.loads(response.data.decode('utf-8'))


def wait_for_neptune_load(neptune_endpoint: str, load_id: str, timeout_seconds: int = 300) -> None:
    """Wait for Neptune bulk load to complete."""
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            raise Exception(f"Neptune bulk load timed out after {timeout_seconds}s")
        
        status_response = check_neptune_load_status(neptune_endpoint, load_id)
        status = status_response['payload']['overallStatus']['status']
        
        logger.info("Load status: %s (%ds elapsed)", status, int(elapsed))

        if status == 'LOAD_COMPLETED':
            total_records = status_response['payload']['overallStatus'].get('totalRecords', 0)
            logger.info("Load completed successfully. Total records: %s", total_records)
            return
        elif status in ['LOAD_FAILED', 'LOAD_CANCELLED']:
            raise Exception(f"Neptune bulk load failed with status: {status}")
        
        time.sleep(5)  # nosemgrep: arbitrary-sleep - intentional polling delay for Neptune bulk load status


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Neptune Loader Custom Resource.

    Used with CDK cr.Provider — must return a dict on success and raise on failure.
    The Provider framework handles CloudFormation responses automatically.
    """
    # Do NOT log the full event — ResourceProperties may contain sensitive
    # values (endpoints, ARNs). Log only non-sensitive routing fields.
    logger.info(
        "Received event: RequestType=%s LogicalResourceId=%s",
        event.get('RequestType'),
        event.get('LogicalResourceId'),
    )

    request_type = event['RequestType']
    properties = event['ResourceProperties']

    # Get region from Lambda environment (AWS_REGION is automatically set)
    region = os.environ.get('AWS_REGION', 'us-east-1')

    if request_type == 'Delete':
        # No cleanup needed - Neptune data persists
        logger.info("Delete request - no action needed")
        return {'Status': 'DELETE_SKIPPED'}

    # Extract properties
    s3_bucket = properties['S3Bucket']
    neptune_endpoint = properties['NeptuneEndpoint']
    iam_role_arn = properties['IamRoleArn']

    # Step 1: Read application CSVs from S3
    logger.info("Step 1: Reading application CSVs from S3...")
    suppliers_csv = read_s3_csv(s3_bucket, 'csv-data/suppliers.csv')
    materials_csv = read_s3_csv(s3_bucket, 'csv-data/materials.csv')
    supplier_materials_csv = read_s3_csv(s3_bucket, 'csv-data/supplier_materials.csv')

    # Step 2: Transform to Neptune format
    logger.info("Step 2: Transforming CSVs to Neptune format...")
    suppliers_neptune = transform_suppliers_to_neptune_csv(suppliers_csv)
    materials_neptune = transform_materials_to_neptune_csv(materials_csv)
    edges_neptune = transform_supplier_materials_to_neptune_csv(supplier_materials_csv)

    # Step 3: Upload Neptune CSVs to S3
    logger.info("Step 3: Uploading Neptune CSVs to S3...")
    upload_to_s3(s3_bucket, 'neptune-load/suppliers-vertices.csv', suppliers_neptune)
    upload_to_s3(s3_bucket, 'neptune-load/materials-vertices.csv', materials_neptune)
    upload_to_s3(s3_bucket, 'neptune-load/supplies-edges.csv', edges_neptune)

    # Step 4: Start Neptune bulk load
    logger.info("Step 4: Starting Neptune bulk load...")
    load_id = start_neptune_bulk_load(
        neptune_endpoint=neptune_endpoint,
        s3_bucket=s3_bucket,
        s3_prefix='neptune-load',
        iam_role_arn=iam_role_arn,
        region=region
    )

    # Step 5: Wait for completion
    logger.info("Step 5: Waiting for Neptune bulk load to complete...")
    wait_for_neptune_load(neptune_endpoint, load_id, timeout_seconds=600)

    # Success — return dict for cr.Provider framework
    logger.info("Neptune data loaded successfully. Load ID: %s", load_id)
    return {
        'Data': {
            'LoadId': load_id,
            'Status': 'LOAD_COMPLETED',
            'Message': 'Neptune data loaded successfully'
        }
    }
