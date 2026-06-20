# CDK Deployment Guide - Procurement Optimization Agent

Complete deployment instructions for the Procurement Optimization Agent infrastructure.

## Prerequisites

- AWS CLI configured with credentials (`aws configure --profile <your-profile>`)
- AWS CDK CLI installed and matching the CDK lib version (`npm install -g aws-cdk@latest`)
- Python 3.11+ with a virtual environment
- Node.js 18+ with npm (for frontend build)
- Docker (for Lambda layer builds)
- SageMaker Python SDK v2 (`pip install "sagemaker>=2.200,<3"`) — needed for Chronos-2 endpoint deployment only (install in a separate venv)

## Architecture Overview

The deployment consists of 15 CDK stacks:

| Stack | Description |
|-------|-------------|
| Identity | Cognito User Pool + Client for frontend auth |
| Lambda Layer | Shared Python dependencies (scipy, numpy, pandas, gremlinpython) |
| Data | VPC, Neptune cluster, S3 bucket, forecast data upload |
| Lambda | Optimization, Data Access, Explainability Lambda functions |
| Neptune Loader | Custom Resource for Neptune bulk data loading |
| Agent | Procurement agent on Bedrock AgentCore Runtime |
| Gateway | AgentCore Gateway exposing Lambda tools via MCP |
| Policy | AgentCore PolicyEngine with Cedar RBAC |
| Memory | AgentCore Memory with semantic strategies |
| Evaluator | AgentCore Evaluators for agent quality |
| Observability | CloudWatch dashboards, alarms, tracing |
| API | Flask Lambda + API Gateway (procurement + forecast endpoints) |
| Frontend | S3 + CloudFront + Cognito auth |
| SageMaker Forecast | IAM role for Chronos-2 SageMaker endpoint |
| Forecast Agent | Demand forecasting agent on AgentCore Runtime |

## Deployment Steps

### Step 0: Environment Setup

```bash
export AWS_PROFILE=<your-profile>
export AWS_REGION=us-east-1

# Verify credentials
aws sts get-caller-identity

# Install CDK Python dependencies
cd backend/aws/cdk
pip install -r requirements.txt
```

Verify `cdk.json` uses a portable Python path:
```json
"app": "python3 app.py"
```

### Step 1: Build Assets

```bash
cd backend/aws/cdk

# 1. Lambda layer (shared Python dependencies)
bash lambda_layer/build.sh

# 2. Lambda code bundle (Flask API + procurement tools — for API Lambda)
bash ../../scripts/package_agent.sh

# 3. Frontend (required before cdk synth/deploy — the Frontend stack references dist/)
cd ../../../procurement-agent-ui
npm install
npx vite build
cd ..
```

### Step 1b: Deploy Procurement Agent to AgentCore (via toolkit)

The procurement agent is deployed separately using the AgentCore starter toolkit,
not via CDK. This handles dependency packaging for arm64 automatically.

```bash
pip install bedrock-agentcore-starter-toolkit
python3 scripts/deploy_agent_runtime.py --region us-east-1
```

The agent ARN will be printed on success and saved to `.bedrock_agentcore.yaml`.

### Step 2: Bootstrap CDK (One-time)

```bash
cdk bootstrap aws://<ACCOUNT_ID>/<REGION>
```

### Step 3: Deploy Backend Stacks

```bash
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
cd backend/aws/cdk

# Synthesize first to catch errors
cdk synth --all

# Deploy all backend stacks
cdk deploy \
  procurement-optimization-agent-identity-development \
  procurement-optimization-agent-layer-development \
  procurement-optimization-agent-data-development \
  procurement-optimization-agent-lambda-development \
  procurement-optimization-agent-loader-development \
  procurement-optimization-agent-agent-development \
  procurement-optimization-agent-gateway-development \
  procurement-optimization-agent-policy-development \
  procurement-optimization-agent-memory-development \
  procurement-optimization-agent-evaluator-development \
  procurement-optimization-agent-observability-development \
  procurement-optimization-agent-api-development \
  procurement-optimization-agent-sagemaker-forecast-development \
  procurement-optimization-agent-forecast-agent-development \
  --require-approval never
```

### Step 4: Deploy Chronos-2 SageMaker Endpoint

The Chronos-2 model is deployed via the SageMaker JumpStart SDK (not CDK) because it needs to resolve model artifact URIs at deploy time.

```bash
# Create a separate venv for the SageMaker SDK (heavy dependency)
cd ../../../demand-forecasting/scripts
python3 -m venv .venv
source .venv/bin/activate
pip install "sagemaker>=2.200,<3" boto3

# Get the IAM role ARN from the CDK stack
ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-sagemaker-forecast-development \
  --query 'Stacks[0].Outputs[?OutputKey==`SageMakerRoleArn`].OutputValue' --output text)

# Deploy the endpoint (~10-15 minutes)
python deploy_chronos_endpoint.py --role-arn "$ROLE_ARN"

# Verify endpoint is InService
aws sagemaker wait endpoint-in-service --endpoint-name chronos-2-forecast-endpoint

# Test the endpoint
python deploy_chronos_endpoint.py --test

deactivate
```

**Known issue**: The `AmazonSageMakerFullAccess` managed policy does NOT grant `s3:GetObject` on `jumpstart-cache-prod-*` buckets. The CDK stack adds this permission explicitly. If the endpoint fails with "Request to service failed", verify the IAM role has:
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": ["arn:aws:s3:::jumpstart-cache-prod-*", "arn:aws:s3:::jumpstart-cache-prod-*/*"]
}
```

### Step 5: Build and Deploy Frontend

The frontend requires three environment variables at build time:

| Variable | Source | Purpose |
|----------|--------|---------|
| `VITE_API_URL` | API stack output `ApiUrl` | Backend API Gateway URL |
| `VITE_COGNITO_USER_POOL_ID` | Identity stack output `UserPoolId` | Cognito authentication |
| `VITE_COGNITO_CLIENT_ID` | Identity stack output `UserPoolClientId` | Cognito authentication |

```bash
# Get values from stack outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-api-development \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-identity-development \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-identity-development \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' --output text)

# Build frontend with all env vars
cd ../../procurement-agent-ui
VITE_API_URL="$API_URL" \
VITE_COGNITO_USER_POOL_ID="$POOL_ID" \
VITE_COGNITO_CLIENT_ID="$CLIENT_ID" \
npx vite build

# Deploy to CloudFront
cd ../backend/aws/cdk
cdk deploy procurement-optimization-agent-frontend-development --require-approval never
```

**Without Cognito**: If `VITE_COGNITO_USER_POOL_ID` and `VITE_COGNITO_CLIENT_ID` are not set, the app skips authentication and uses a demo user (`demo@voltcycle.com`).

**Without API URL**: If `VITE_API_URL` is not set, the frontend falls back to local dev proxy paths (`/api/*` and `/forecast-api/*`).

### Step 6: Create Cognito User (if auth enabled)

```bash
# Create a user
aws cognito-idp admin-create-user \
  --user-pool-id "$POOL_ID" \
  --username user@example.com \
  --temporary-password "<choose-a-strong-temporary-password>" \
  --user-attributes Name=email,Value=user@example.com

# User will be prompted to set a new password on first login
```

### Step 7: Verify Deployment

```bash
# Check all stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `procurement`)].{Name: StackName, Status: StackStatus}' \
  --output table

# Test forecast API
curl -s -X POST "$API_URL/api/demand/forecast" \
  -H "Content-Type: application/json" \
  -d '{"material_id": "MAT-BAT-001", "prediction_length": 30}' | python3 -m json.tool

# Test health endpoint
curl -s "$API_URL/health"

# Get frontend URL
aws cloudformation describe-stacks \
  --stack-name procurement-optimization-agent-frontend-development \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' --output text
```

## API Lambda Environment Variables

The API Lambda (`server.py`) requires these environment variables (set by CDK):

| Variable | Description |
|----------|-------------|
| `FLASK_ENV` | `production` |
| `DATA_DIR` | `/var/task/data` — path to bundled CSV data |
| `DATA_BUCKET` | S3 bucket name for forecast data |
| `PR_S3_BUCKET` | S3 bucket name for purchase requisitions |
| `FORECAST_DATA_PREFIX` | `forecast-data/` — S3 prefix for forecast CSVs |
| `SAGEMAKER_ENDPOINT_NAME` | `chronos-2-forecast-endpoint` |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `NEPTUNE_ENDPOINT` | Neptune cluster endpoint |
| `NEPTUNE_PORT` | `8182` |
| `AGENTCORE_GATEWAY_ID` | AgentCore Gateway ID |
| `AGENTCORE_MEMORY_ID` | AgentCore Memory ID |
| `AGENTCORE_POLICY_ENGINE_ID` | AgentCore PolicyEngine ID |
| `CORS_ORIGINS` | `*` |

## Frontend Environment Variables

Set at build time via `VITE_*` prefix:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes (production) | empty (uses Vite proxy) | API Gateway base URL |
| `VITE_COGNITO_USER_POOL_ID` | No | empty (auth disabled) | Cognito User Pool ID |
| `VITE_COGNITO_CLIENT_ID` | No | empty (auth disabled) | Cognito App Client ID |

## API Endpoints

### Procurement

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/optimize` | Run Pareto optimization |
| POST | `/api/optimize-custom` | Custom weight optimization |
| GET | `/api/suppliers` | List suppliers |
| GET | `/api/materials` | List materials |
| POST | `/api/chat` | Chat with procurement agent |
| POST | `/api/purchase-requisitions` | Create PRs |
| GET | `/api/purchase-requisitions` | List PRs |

### Demand Forecasting

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/demand/forecast` | Direct Chronos-2 forecast (no LLM) |

Request: `{"material_id": "MAT-BAT-001", "prediction_length": 90}`
Response: `{summary: {total_p10, total_p50, total_p90, avg_daily_p50}, forecast: [...], explainability: {...}}`


## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CDK Deployment Flow                      │
└─────────────────────────────────────────────────────────────┘

1. Identity Stack (Cognito)
   └─> User Pool + Client

2. Lambda Layer Stack
   └─> Shared dependencies (scipy, numpy, pandas, gremlinpython)

3. Data Stack
   ├─> VPC (2 AZs, private + public subnets)
   ├─> Neptune Cluster (db.t3.medium)
   ├─> S3 Bucket (encrypted, versioned)
   ├─> S3 Upload: csv-data/ (procurement CSVs)
   ├─> S3 Upload: forecast-data/ (demand forecasting CSVs)
   └─> IAM Role (Neptune S3 access)

4. Lambda Stack (depends on Data + Layer)
   ├─> Optimization Lambda (VPC, Neptune access)
   ├─> Data Access Lambda (VPC, Neptune access)
   └─> Explainability Lambda (VPC, Neptune access)

5. Neptune Loader Stack (depends on Data)
   └─> Custom Resource (bulk load CSVs into Neptune)

6. API Stack (depends on Data + Layer)
   ├─> Flask Lambda (procurement + forecast endpoints)
   ├─> API Gateway REST API with CORS
   └─> IAM: Bedrock, Neptune, S3, SageMaker invoke

7. SageMaker Forecast Stack
   └─> IAM Role for Chronos-2 endpoint (+ JumpStart S3 access)

8. Forecast Agent Stack (depends on Data + SageMaker)
   ├─> AgentCore Runtime (forecast agent bundle)
   └─> AgentCore RuntimeEndpoint

9. Frontend Stack
   ├─> S3 Bucket (static site)
   └─> CloudFront Distribution
```

## Incremental Deployment (Existing Stacks Already Deployed)

When adding new features to an existing deployment:

```bash
# 1. Rebuild the Lambda code bundle
bash backend/scripts/package_agent.sh

# 2. Deploy only the changed CDK stacks
cdk deploy procurement-optimization-agent-api-development --exclusively --require-approval broadening
cdk deploy procurement-optimization-agent-data-development --exclusively --require-approval broadening

# 3. Redeploy procurement agent (if agent code changed)
python3 scripts/deploy_agent_runtime.py --region us-east-1

# 4. Rebuild and deploy frontend (always include all three VITE_ env vars)
```

Use `--exclusively` to deploy a single stack without triggering updates to its dependencies.
Use `--require-approval broadening` to review IAM changes before applying.

## Rollback Instructions

> **Warning:** Destroying stacks deletes all associated data (Neptune graph, S3 objects,
> purchase requisitions, CloudWatch logs). Export any data you need before proceeding.

### Step 1: Delete SageMaker Endpoint (Highest Cost — $1.14/hr)

```bash
aws sagemaker delete-endpoint --endpoint-name chronos-2-forecast-endpoint
aws sagemaker delete-endpoint-config --endpoint-config-name chronos-2-forecast-endpoint
```

### Step 2: Delete AgentCore Resources Deployed via Starter Toolkit

```bash
# Run from the project root directory
cd /path/to/predictive-supply-chain-orchestrator

# Procurement agent (deployed via scripts/deploy_agent_runtime.py)
AGENT_ID=$(grep 'agent_id:' backend/agentcore_bundle/.bedrock_agentcore.yaml 2>/dev/null | head -1 | awk '{print $2}')
if [ -n "$AGENT_ID" ]; then
  echo "Deleting procurement agent: $AGENT_ID"
  aws bedrock-agentcore-control delete-agent-runtime \
    --agent-runtime-id "$AGENT_ID" --region us-east-1
else
  echo "No procurement agent config found — skipping"
fi
```

### Step 3: Destroy All CDK Stacks

```bash
cd ./backend/aws/cdk
cdk destroy --all --force
```

### Step 3 (Alternative): Destroy Individual CDK Stacks in Reverse Dependency Order

```bash
# Frontend (no dependencies on it)
cdk destroy procurement-optimization-agent-frontend-development

# API (depends on data, layer)
cdk destroy procurement-optimization-agent-api-development

# Observability (standalone)
cdk destroy procurement-optimization-agent-observability-development

# AgentCore platform stacks (standalone)
cdk destroy procurement-optimization-agent-evaluator-development
cdk destroy procurement-optimization-agent-memory-development
cdk destroy procurement-optimization-agent-policy-development
cdk destroy procurement-optimization-agent-gateway-development

# SageMaker IAM role (standalone, endpoint already deleted in Step 1)
cdk destroy procurement-optimization-agent-sagemaker-forecast-development

# Neptune loader (depends on data)
cdk destroy procurement-optimization-agent-loader-development

# Lambda tools (depends on data, layer)
cdk destroy procurement-optimization-agent-lambda-development

# Data layer — Neptune cluster + S3 bucket (WARNING: deletes all data)
cdk destroy procurement-optimization-agent-data-development

# Lambda layer (shared dependencies)
cdk destroy procurement-optimization-agent-layer-development

# Identity — Cognito (WARNING: deletes all user accounts)
cdk destroy procurement-optimization-agent-identity-development
```

### Verify Cleanup

After rollback, confirm no costly resources remain:

```bash
# Check for running SageMaker endpoints
aws sagemaker list-endpoints --query 'Endpoints[?contains(EndpointName, `chronos`)].{Name:EndpointName,Status:EndpointStatus}'

# Check for Neptune clusters
aws neptune describe-db-clusters --query 'DBClusters[?contains(DBClusterIdentifier, `procurement`)].{Id:DBClusterIdentifier,Status:Status}'

# Check for remaining CloudFormation stacks
aws cloudformation list-stacks --query 'StackSummaries[?contains(StackName, `procurement-optimization`) && StackStatus!=`DELETE_COMPLETE`].{Name:StackName,Status:StackStatus}'
```

## Troubleshooting

### SageMaker Endpoint Fails with "Request to service failed"

This is usually an IAM permissions issue. The `AmazonSageMakerFullAccess` policy does NOT cover JumpStart S3 buckets.

1. Check the IAM role has `s3:GetObject` on `jumpstart-cache-prod-*`
2. Verify no CloudWatch logs exist (means container never started = IAM issue)
3. Try `enable_network_isolation=False` in the deploy script
4. Check service quotas: `aws service-quotas list-service-quotas --service-code sagemaker --query 'Quotas[?contains(QuotaName, `endpoint`)].{Name: QuotaName, Value: Value}'`

### Frontend Shows Demo User (No Login Page)

Cognito env vars were not set at build time. Rebuild with:
```bash
VITE_COGNITO_USER_POOL_ID=<pool-id> VITE_COGNITO_CLIENT_ID=<client-id> npx vite build
```

### Forecast Returns All Zeros

The ChronosClient response parsing may not match the endpoint response format. Test the raw endpoint:
```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name chronos-2-forecast-endpoint \
  --content-type application/json \
  --body '{"inputs":[{"target":[10,20,30,40,50]}],"parameters":{"prediction_length":5}}' \
  /dev/stdout
```
Verify the response has `predictions[0]["0.1"]` (not nested under `quantiles`).

### CDK Deploy Fails with Layer Export Error

If the Lambda Layer stack tries to update and fails with "Cannot update export", deploy the API stack exclusively:
```bash
cdk deploy procurement-optimization-agent-api-development --exclusively --require-approval never
```

## Cost Estimate

**Monthly cost (us-east-1, development environment):**

| Resource | Cost |
|----------|------|
| Neptune db.t3.medium | ~$73/month |
| NAT Gateway | ~$32/month |
| SageMaker ml.g5.2xlarge (Chronos-2) | ~$912/month (24/7) or $1.14/hr |
| S3 storage (< 1 GB) | < $1/month |
| Lambda invocations | < $1/month |
| CloudFront | < $1/month |
| Cognito (< 50K MAU) | Free tier |
| **Total** | **~$1,019/month** |

**Cost Optimization:**
- Delete the SageMaker endpoint when not in use (`aws sagemaker delete-endpoint --endpoint-name chronos-2-forecast-endpoint`)
- Redeploy with `deploy_chronos_endpoint.py` when needed
- Use Neptune Serverless for variable workloads

## References

- [Neptune Bulk Loader](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load.html)
- [CDK Custom Resources](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.custom_resources-readme.html)
- [Chronos-2 SageMaker Deployment](https://github.com/amazon-science/chronos-forecasting/blob/main/notebooks/deploy-chronos-to-amazon-sagemaker.ipynb)
- [AgentCore Runtime Quickstart](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.md)
