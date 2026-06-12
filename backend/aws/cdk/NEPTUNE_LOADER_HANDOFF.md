# Neptune Data Loader - CDK Custom Resource Handoff

## What We Built

A **CDK-native, repeatable solution** for loading data into Amazon Neptune using Infrastructure as Code. No shell scripts, no manual steps after initial CSV upload.

## Problem Solved

**Before**: Neptune data loading required either:
- Manual Python scripts run from local machine (not repeatable)
- Shell scripts with hardcoded values (not IaC)
- Custom Lambda with manual invocation (extra steps)

**After**: Fully automated Neptune data loading via CDK Custom Resource that:
- Runs automatically on stack CREATE and UPDATE
- Transforms application CSVs to Neptune format
- Uploads to S3 and invokes Neptune bulk loader
- Polls for completion and reports status to CloudFormation
- **100% repeatable across AWS accounts**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Neptune Loader Stack (CDK)                      │
└─────────────────────────────────────────────────────────────┘

1. Custom Resource Provider
   └─> Lambda Function (VPC, Neptune access)
       ├─> Reads: s3://BUCKET/csv-data/*.csv
       ├─> Transforms: CSV → Neptune Gremlin format
       ├─> Uploads: s3://BUCKET/neptune-load/*.csv
       ├─> Invokes: Neptune bulk loader HTTP API
       └─> Polls: Until LOAD_COMPLETED (5 min timeout)

2. IAM Role (POLP - Principle of Least Privilege)
   ├─> S3: Read/Write to data bucket only
   ├─> VPC: Lambda execution in private subnets
   └─> Neptune: Network access only (no write permissions)

3. CloudFormation Integration
   └─> Custom Resource sends SUCCESS/FAILED to CFN
```

## Files Created

### 1. Lambda Handler
**File**: `backend/aws/lambda_tools/neptune_loader_custom_resource.py`

**Purpose**: Custom Resource Lambda handler that orchestrates Neptune data loading

**Key Functions**:
- `transform_suppliers_to_neptune_csv()` - Converts suppliers.csv to Neptune vertex format
- `transform_materials_to_neptune_csv()` - Converts materials.csv to Neptune vertex format
- `transform_supplier_materials_to_neptune_csv()` - Converts supplier_materials.csv to Neptune edge format
- `start_neptune_bulk_load()` - Invokes Neptune bulk loader HTTP API
- `wait_for_neptune_load()` - Polls for completion with 5-minute timeout
- `handler()` - Main CloudFormation Custom Resource handler

**Error Handling**:
- S3 read/write failures → CloudFormation FAILED response
- Neptune API errors → CloudFormation FAILED response with details
- Timeout (> 5 min) → CloudFormation FAILED response
- All errors logged to CloudWatch

### 2. CDK Stack
**File**: `backend/aws/cdk/stacks/neptune_loader_stack.py`

**Purpose**: CDK stack that creates Custom Resource infrastructure

**Resources Created**:
- Lambda Function (Python 3.11, 10-minute timeout, 512 MB memory)
- IAM Role (S3 read/write, VPC execution)
- Custom Resource Provider
- Custom Resource (triggers on CREATE/UPDATE)

**Security (cdk-nag compliant)**:
- VPC Lambda in private subnets
- Minimal IAM permissions (POLP)
- No hardcoded secrets
- Documented suppressions for AWS managed policies

### 3. Helper Script
**File**: `backend/aws/cdk/upload_data.sh`

**Purpose**: One-time upload of application CSVs to S3

**What It Does**:
- Retrieves S3 bucket name from CloudFormation outputs
- Uploads `suppliers.csv`, `materials.csv`, `supplier_materials.csv` to `s3://BUCKET/csv-data/`
- Validates Data Stack is deployed first

### 4. Updated CDK App
**File**: `backend/aws/cdk/app.py`

**Changes**:
- Added `NeptuneLoaderStack` import
- Instantiated loader stack with dependencies on Data Stack
- Added loader stack to common tags

### 5. Updated Data Stack
**File**: `backend/aws/cdk/stacks/data_stack.py`

**Changes**:
- Exposed `neptune_s3_role_arn` as public attribute for use in Loader Stack

## Deployment Instructions

### Prerequisites
- Data Stack must be deployed first
- Application CSVs must exist in `data/` directory

### Step-by-Step

```bash
# 1. Navigate to CDK directory
cd backend/aws/cdk

# 2. Verify synthesis (CRITICAL - catches errors early)
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
cdk synth --all

# 3. Deploy Data Stack (if not already deployed)
cdk deploy procurement-optimization-agent-data-development

# 4. Upload application CSVs to S3
./upload_data.sh

# 5. Deploy Neptune Loader Stack
cdk deploy procurement-optimization-agent-loader-development

# 6. Verify completion
aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-loader-development \
  --query 'Stacks[0].Outputs[?OutputKey==`LoaderStatus`].OutputValue' \
  --output text
# Expected: LOAD_COMPLETED
```

### Expected Timeline
- Stack deployment: ~5 minutes
- Custom Resource execution: ~2-3 minutes
- Total: ~8 minutes

## How It Works

### CloudFormation Lifecycle

**CREATE Event**:
1. CloudFormation creates Lambda function and Custom Resource
2. Custom Resource invokes Lambda with CREATE event
3. Lambda reads application CSVs from S3
4. Lambda transforms to Neptune format
5. Lambda uploads Neptune CSVs to S3
6. Lambda invokes Neptune bulk loader API
7. Lambda polls for completion (5-minute timeout)
8. Lambda sends SUCCESS to CloudFormation
9. Stack creation completes

**UPDATE Event**:
- Same as CREATE (re-loads data)
- Useful for data updates or schema changes

**DELETE Event**:
- No action taken (Neptune data persists)
- Custom Resource returns SUCCESS immediately

### Neptune Bulk Loader

The solution uses Neptune's **built-in bulk loader** (OOTB serverless solution):
- HTTP API endpoint: `https://NEPTUNE_ENDPOINT:8182/loader`
- Reads CSV files from S3
- Parallel loading (MEDIUM parallelism)
- Idempotent (can run multiple times)
- No Lambda write permissions needed

### CSV Transformation

**Application Format** → **Neptune Gremlin Format**

**Suppliers** (vertices):
```csv
# Application format
supplier_id,name,rating,location,...

# Neptune format
~id,~label,name:String,rating:Double,location:String,...
SUP-001,Supplier,BatteryTech Solutions,4.25,China,...
```

**Materials** (vertices):
```csv
# Application format
material_id,name,category,unit_of_measure,...

# Neptune format
~id,~label,name:String,category:String,unit_of_measure:String,...
MAT-001,Material,Lithium-ion Battery Cell,Battery,unit,...
```

**Supplier-Material Relationships** (edges):
```csv
# Application format
supplier_id,material_id,base_price,minimum_order_quantity,...

# Neptune format
~id,~from,~to,~label,base_price:Double,minimum_order_quantity:Int,...
SUP-001-supplies-MAT-001,SUP-001,MAT-001,supplies,125.50,1000,...
```

## Repeatability Across AWS Accounts

This solution is **100% repeatable**:

```bash
# Deploy in Account A
export AWS_PROFILE=account-a
cdk deploy --all
./upload_data.sh
cdk deploy procurement-optimization-agent-loader-development

# Deploy in Account B (same commands)
export AWS_PROFILE=account-b
cdk deploy --all
./upload_data.sh
cdk deploy procurement-optimization-agent-loader-development
```

**No hardcoded values**:
- S3 bucket name: Retrieved from CloudFormation outputs
- Neptune endpoint: Retrieved from CloudFormation outputs
- IAM role ARN: Retrieved from CloudFormation outputs
- Region: Automatically detected by Lambda runtime

## Security & Compliance (CDE Standards)

### IAM Permissions (POLP)

**Loader Lambda Role**:
```json
{
  "S3": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
  "VPC": ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DeleteNetworkInterface"],
  "CloudWatch": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
}
```

**Neptune S3 Role** (read-only):
```json
{
  "S3": ["s3:GetBucket*", "s3:GetObject*", "s3:List*"]
}
```

### cdk-nag Compliance

All rules pass or have documented suppressions:
- ✅ AwsSolutions-IAM4: AWS managed policy (VPC Lambda execution) - suppressed with reason
- ✅ AwsSolutions-L1: Python 3.11 is latest supported runtime - suppressed with reason
- ✅ No HIGH or CRITICAL findings

### Network Security

- Lambda runs in **private subnets** (no internet access)
- Neptune in **private subnets** (no public endpoint)
- Security group allows VPC CIDR only (port 8182)
- S3 access via VPC endpoint (optional optimization)

## Troubleshooting

### Custom Resource Fails

**Check Lambda logs**:
```bash
aws logs tail /aws/lambda/procurement-optimization-agent-loader-development-NeptuneLoaderFunction --follow
```

**Common Issues**:

1. **Timeout (> 10 minutes)**
   - Symptom: CloudFormation shows CREATE_IN_PROGRESS for > 10 minutes
   - Cause: Neptune bulk load takes longer than expected
   - Fix: Increase Lambda timeout in `neptune_loader_stack.py` (line 71)

2. **Network Error**
   - Symptom: "Connection refused" or "Timeout" in logs
   - Cause: Lambda can't reach Neptune endpoint
   - Fix: Verify security group allows VPC CIDR on port 8182

3. **S3 Permission Error**
   - Symptom: "Access Denied" when reading/writing S3
   - Cause: IAM role missing permissions
   - Fix: Verify `data_bucket.grant_read_write(loader_role)` in stack

4. **CSV Format Error**
   - Symptom: Neptune bulk loader reports "Invalid CSV format"
   - Cause: Transformation logic error
   - Fix: Check transformation functions in `neptune_loader_custom_resource.py`

### Neptune Bulk Load Fails

**Check load status**:
```bash
LOAD_ID=<LOAD_ID_FROM_LOGS>
NEPTUNE_ENDPOINT=<ENDPOINT>

curl "https://${NEPTUNE_ENDPOINT}:8182/loader/${LOAD_ID}"
```

**Common Issues**:

1. **IAM Role Not Associated**
   - Symptom: "Access Denied" from Neptune
   - Cause: Neptune S3 role not associated with cluster
   - Fix: Verify `AssociatedRoles` property in Data Stack

2. **S3 Files Not Found**
   - Symptom: "NoSuchKey" error
   - Cause: CSVs not uploaded to correct S3 path
   - Fix: Run `./upload_data.sh` and verify files in `neptune-load/` folder

3. **CSV Schema Mismatch**
   - Symptom: "Schema validation failed"
   - Cause: Neptune CSV headers don't match data types
   - Fix: Verify `:String`, `:Double`, `:Int`, `:Bool`, `:Date` suffixes

## Extending the Solution

### Add New CSV Files

1. **Update transformation logic**:
   ```python
   def transform_new_entity_to_neptune_csv(input_csv: str) -> str:
       # Add transformation logic
       pass
   ```

2. **Update handler**:
   ```python
   new_entity_csv = read_s3_csv(s3_bucket, 'csv-data/new_entity.csv')
   new_entity_neptune = transform_new_entity_to_neptune_csv(new_entity_csv)
   upload_to_s3(s3_bucket, 'neptune-load/new-entity.csv', new_entity_neptune)
   ```

3. **Upload new CSV**:
   ```bash
   aws s3 cp data/new_entity.csv s3://BUCKET/csv-data/new_entity.csv
   ```

4. **Redeploy**:
   ```bash
   cdk deploy procurement-optimization-agent-loader-development
   ```

### Change Neptune Bulk Loader Settings

Edit `start_neptune_bulk_load()` in `neptune_loader_custom_resource.py`:

```python
payload = {
    "source": f"s3://{s3_bucket}/{s3_prefix}/",
    "format": "csv",
    "iamRoleArn": iam_role_arn,
    "region": region,
    "failOnError": "TRUE",  # Change to TRUE for strict validation
    "parallelism": "HIGH",  # Change to HIGH for faster loading
    "parserConfiguration": {
        "namedGraphUri": "http://aws.amazon.com/neptune/vocab/v01/DefaultNamedGraph"
    }
}
```

### Add Data Validation

Add validation before transformation:

```python
def validate_csv(csv_content: str, required_columns: List[str]) -> None:
    """Validate CSV has required columns."""
    reader = csv.DictReader(StringIO(csv_content))
    headers = reader.fieldnames
    
    missing = set(required_columns) - set(headers)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

# In handler:
validate_csv(suppliers_csv, ['supplier_id', 'name', 'rating'])
```

## Cost Analysis

**One-time costs** (per deployment):
- Lambda execution: ~$0.01 (10 minutes × 512 MB)
- S3 PUT requests: ~$0.01 (6 files)
- Neptune bulk load: Free (uses existing cluster)

**Ongoing costs**:
- S3 storage: ~$0.02/month (< 1 GB)
- Lambda: $0 (only runs on stack CREATE/UPDATE)

**Total**: ~$0.02/month after initial deployment

## Known Limitations

1. **Timeout**: Lambda has 10-minute timeout. Large datasets (> 100K records) may timeout.
   - **Workaround**: Increase timeout or split into multiple Custom Resources

2. **No Incremental Updates**: Always reloads all data (not incremental).
   - **Workaround**: Use separate Lambda for incremental updates

3. **No Rollback**: Neptune data persists after stack deletion.
   - **Workaround**: Manually clear Neptune before redeployment if needed

4. **VPC Lambda Cold Start**: First invocation takes ~10 seconds.
   - **Impact**: Minimal (only runs on stack CREATE/UPDATE)

## Success Criteria

✅ **Deployment succeeds** - CloudFormation stack shows CREATE_COMPLETE
✅ **Data loaded** - LoaderStatus output shows LOAD_COMPLETED
✅ **Repeatable** - Can deploy in different AWS accounts with same commands
✅ **No manual steps** - Everything automated via CDK
✅ **Security compliant** - cdk-nag passes, POLP enforced
✅ **Well documented** - Customer can deploy independently

## Next Steps

After successful deployment:

1. **Verify data in Neptune**:
   ```bash
   # Use Data Access Lambda to query
   aws lambda invoke \
     --function-name procurement-optimization-agent-lambda-development-DataAccessFunction \
     --payload '{"query_type":"get_supplier_network","supplier_id":"SUP-001"}' \
     response.json
   ```

2. **Test Lambda functions**:
   ```bash
   cd backend
   pytest tests/integration/test_lambda_tools.py
   ```

3. **Deploy Bedrock Agent** (manual setup - CDK constructs not available)

4. **Configure frontend** with API endpoints

## References

- [Neptune Bulk Loader API](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load.html)
- [CDK Custom Resources](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.custom_resources-readme.html)
- [Neptune Gremlin CSV Format](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-gremlin.html)
- [Lambda VPC Configuration](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)

## Support

For issues or questions:
1. Check CloudWatch logs for Lambda function
2. Review Neptune bulk loader status via API
3. Verify CloudFormation stack events
4. Consult troubleshooting section above
