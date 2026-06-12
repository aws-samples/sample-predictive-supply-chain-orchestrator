"""
Invoke Neptune bulk loader API to load data from S3.

Uses Neptune's OOTB bulk loader for repeatable, serverless data loading.
"""

import requests
import json
import sys

# Configuration from CDK outputs
NEPTUNE_ENDPOINT = "neptunedbcluster-knun8wigfffs.cluster-crsipo8ynrlb.us-east-1.neptune.amazonaws.com"
NEPTUNE_PORT = 8182
S3_BUCKET = "procurement-optimization--procurementdatabucket28d-ljhgkqlxtog0"
S3_PREFIX = "neptune-load"
IAM_ROLE_ARN = "arn:aws:iam::REDACTED_ACCOUNT_ID:role/procurement-optimization--NeptuneS3AccessRole22331D-bqNlGjwEw209"

def start_bulk_load():
    """Start Neptune bulk loader job."""
    
    loader_endpoint = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/loader"
    
    payload = {
        "source": f"s3://{S3_BUCKET}/{S3_PREFIX}/",
        "format": "csv",
        "iamRoleArn": IAM_ROLE_ARN,
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "parserConfiguration": {
            "namedGraphUri": "http://aws.amazon.com/neptune/vocab/v01/DefaultNamedGraph"
        }
    }
    
    print(f"Starting Neptune bulk load from s3://{S3_BUCKET}/{S3_PREFIX}/")
    print(f"Loader endpoint: {loader_endpoint}")
    print(f"IAM Role: {IAM_ROLE_ARN}")
    
    try:
        response = requests.post(
            loader_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        print("\n✓ Bulk load job started successfully!")
        print(f"Load ID: {result.get('payload', {}).get('loadId', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to start bulk load: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)


def check_load_status(load_id: str):
    """Check status of bulk load job."""
    
    status_endpoint = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/loader/{load_id}"
    
    try:
        response = requests.get(status_endpoint, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        status = result.get('payload', {}).get('overallStatus', {}).get('status', 'UNKNOWN')
        print(f"\nLoad Status: {status}")
        
        if status == "LOAD_COMPLETED":
            stats = result.get('payload', {}).get('overallStatus', {})
            print(f"Total Records: {stats.get('totalRecords', 0)}")
            print(f"Total Duplicates: {stats.get('totalDuplicates', 0)}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Failed to check load status: {e}")
        sys.exit(1)


if __name__ == '__main__':
    result = start_bulk_load()
    load_id = result.get('payload', {}).get('loadId')
    
    if load_id:
        print(f"\nTo check status, run:")
        print(f"  python {__file__} check {load_id}")
        
        if len(sys.argv) > 1 and sys.argv[1] == 'check':
            check_load_status(sys.argv[2] if len(sys.argv) > 2 else load_id)
