#!/bin/bash
# Full deployment script for Procurement Optimization Agent
#
# Repeatable across AWS accounts. Handles both first-run and subsequent deploys.
#
# Order:
#   0. Build Lambda layer
#   1. CDK infra stacks (identity, data, lambda tools, API, gateway, SageMaker IAM, etc.)
#   1b. Deploy SageMaker Chronos-2 endpoint (~10-15 min)
#   2. Deploy procurement agent to AgentCore Runtime (Python SDK)
#   3. Extract procurement agent ARN
#   4. Update API Lambda code
#   5. Build frontend with Cognito, API URL, and AgentCore Runtime ARN
#   6. Deploy frontend to CloudFront
#   7. Create demo Cognito user
#   8. Verify deployment
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - AWS CDK CLI installed (npm install -g aws-cdk)
#   - Python 3.11+ with venv activated (pip install -r requirements.txt)
#   - Node.js 18+ (for frontend build)
#   - bedrock-agentcore-starter-toolkit (pip install bedrock-agentcore-starter-toolkit)
#   - uv (for arm64 cross-compilation: pip install uv)
#   - sagemaker SDK (pip install "sagemaker>=2.200,<3") — for Chronos-2 endpoint
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CDK_DIR="$PROJECT_ROOT/backend/aws/cdk"
SAGEMAKER_VENV="$PROJECT_ROOT/demand-forecasting/scripts/.venv"
ENVIRONMENT=${ENVIRONMENT:-development}
PROJECT_NAME="procurement-optimization-agent"
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}
export AWS_REGION=${AWS_REGION:-$AWS_DEFAULT_REGION}

echo "═══ Preflight: checking prerequisites ═══"
MISSING=""
command -v aws &>/dev/null || MISSING="$MISSING aws-cli"
command -v cdk &>/dev/null || MISSING="$MISSING aws-cdk"
command -v python3 &>/dev/null || MISSING="$MISSING python3"
command -v node &>/dev/null || MISSING="$MISSING node"
command -v uv &>/dev/null || MISSING="$MISSING uv"
# aws_cdk check — the venv may not exist yet (created in Step 1)
"$PROJECT_ROOT/.venv/bin/python" -c "import aws_cdk" 2>/dev/null || python3 -c "import aws_cdk" 2>/dev/null || echo "  (aws-cdk-lib will be installed in Step 1 venv)"
python3 -c "from bedrock_agentcore_starter_toolkit import Runtime" 2>/dev/null || {
  echo "  Installing bedrock-agentcore-starter-toolkit..."
  pip install -q bedrock-agentcore-starter-toolkit 2>&1 | tail -1
}
aws sts get-caller-identity &>/dev/null || MISSING="$MISSING aws-credentials"

if [ -n "$MISSING" ]; then
  echo "  ✗ Missing:$MISSING"
  echo "  Install missing prerequisites and retry."
  exit 1
fi

echo "  Setting up SageMaker venv (isolated from CDK)..."
if [ ! -f "$SAGEMAKER_VENV/bin/python" ]; then
  python3 -m venv "$SAGEMAKER_VENV"
fi
"$SAGEMAKER_VENV/bin/pip" install -q "sagemaker>=2.200,<3" boto3 2>&1 | tail -1

echo "  ✓ All prerequisites met"
echo ""

# Clear stale agentcore config (account-specific, must be regenerated)
rm -f "$PROJECT_ROOT/.bedrock_agentcore.yaml"

echo "═══ Step 0: Build prerequisites ═══"

echo "Building Lambda layer..."
bash "$CDK_DIR/lambda_layer/build.sh"

echo "Packaging agent bundle (needed by CDK ApiStack asset)..."
bash "$PROJECT_ROOT/backend/scripts/package_agent.sh"

# Create placeholder frontend dist/ so CDK synth doesn't fail on FrontendStack.
# The real build happens in Step 5; Step 6 deploys the actual content.
if [ ! -f "$PROJECT_ROOT/procurement-agent-ui/dist/index.html" ]; then
  echo "Creating placeholder frontend dist/ for CDK synth..."
  mkdir -p "$PROJECT_ROOT/procurement-agent-ui/dist"
  echo "<html><body>placeholder</body></html>" > "$PROJECT_ROOT/procurement-agent-ui/dist/index.html"
fi

echo ""
echo "═══ Step 1: Deploy CDK infrastructure stacks ═══"
cd "$CDK_DIR"
if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
  echo "Creating CDK venv..."
  python3 -m venv "$PROJECT_ROOT/.venv"
  "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$CDK_DIR/requirements.txt"
fi
source "$PROJECT_ROOT/.venv/bin/activate"
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Bootstrap CDK if not already done (required once per account/region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cdk bootstrap aws://${ACCOUNT_ID}/${AWS_REGION} 2>&1 | tail -3

cdk deploy \
  ${PROJECT_NAME}-identity-${ENVIRONMENT} \
  ${PROJECT_NAME}-layer-${ENVIRONMENT} \
  ${PROJECT_NAME}-data-${ENVIRONMENT} \
  ${PROJECT_NAME}-lambda-${ENVIRONMENT} \
  ${PROJECT_NAME}-loader-${ENVIRONMENT} \
  ${PROJECT_NAME}-gateway-${ENVIRONMENT} \
  ${PROJECT_NAME}-policy-${ENVIRONMENT} \
  ${PROJECT_NAME}-memory-${ENVIRONMENT} \
  ${PROJECT_NAME}-evaluator-${ENVIRONMENT} \
  ${PROJECT_NAME}-guardrail-${ENVIRONMENT} \
  ${PROJECT_NAME}-observability-${ENVIRONMENT} \
  ${PROJECT_NAME}-api-${ENVIRONMENT} \
  ${PROJECT_NAME}-sagemaker-forecast-${ENVIRONMENT} \
  --require-approval never

SKIP_SAGEMAKER=${SKIP_SAGEMAKER:-false}
if [ "$SKIP_SAGEMAKER" != "true" ]; then
  echo ""
  echo "═══ Step 1b: Deploy SageMaker Chronos-2 endpoint ═══"
  echo "(This takes 10-15 minutes and costs ~\$1.14/hr while running)"
  SAGEMAKER_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-sagemaker-forecast-${ENVIRONMENT} \
    --query 'Stacks[0].Outputs[?OutputKey==`SageMakerRoleArn`].OutputValue' \
    --output text)
  echo "SageMaker Role: $SAGEMAKER_ROLE_ARN"
  "$SAGEMAKER_VENV/bin/python" "$PROJECT_ROOT/demand-forecasting/scripts/deploy_chronos_endpoint.py" \
    --role-arn "$SAGEMAKER_ROLE_ARN" --test
fi

cd "$PROJECT_ROOT"

echo ""
echo "═══ Step 2: Deploy procurement agent to AgentCore ═══"
pip install -q bedrock-agentcore-starter-toolkit 2>&1 | tail -1
python3 "$PROJECT_ROOT/scripts/deploy_agent_runtime.py" --region "$AWS_REGION"

echo ""
echo "═══ Step 3: Extract agent ARN ═══"
PROCUREMENT_AGENT_ARN=$(python3 -c "
import yaml, os
for path in ['.bedrock_agentcore.yaml', 'backend/agentcore_bundle/.bedrock_agentcore.yaml']:
    if os.path.exists(path):
        with open(path) as f:
            cfg = yaml.safe_load(f)
        for a in cfg.get('agents', {}).values():
            ac = a.get('bedrock_agentcore', {})
            if ac.get('agent_arn'): print(ac['agent_arn']); break
        break
")
echo "Procurement Agent ARN: $PROCUREMENT_AGENT_ARN"

if [ -z "$PROCUREMENT_AGENT_ARN" ]; then
  echo "  ✗ ERROR: Could not extract agent ARN from .bedrock_agentcore.yaml"
  echo "  Check that Step 2 completed successfully and the file exists at project root."
  exit 1
fi

echo ""
echo "═══ Step 3b: Post-deploy fixups (IAM, env vars, permissions) ═══"
bash "$SCRIPT_DIR/post_deploy_fixups.sh"

echo ""
echo "═══ Step 4: Update API Lambda code ═══"
# The Lambda handles REST endpoints (optimize, suppliers, forecast).
# Chat goes directly from frontend to AgentCore Runtime — no Lambda involved.

API_LAMBDA=$(aws cloudformation describe-stack-resources \
  --stack-name ${PROJECT_NAME}-api-${ENVIRONMENT} \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function' && starts_with(LogicalResourceId, 'ApiFunction')].PhysicalResourceId" \
  --output text)

if [ -z "$API_LAMBDA" ]; then
  echo "  ✗ ERROR: Could not find API Lambda function in stack ${PROJECT_NAME}-api-${ENVIRONMENT}"
  exit 1
fi

echo "Packaging API Lambda code..."
bash "$PROJECT_ROOT/backend/scripts/package_agent.sh"

rm -f /tmp/api-lambda-code.zip
cd "$PROJECT_ROOT/backend/agent-bundle"
zip -rq /tmp/api-lambda-code.zip \
  api_handler.py api/ agents/ core/ config/ data/ \
  -x '*.pyc' '*__pycache__*'
cd "$PROJECT_ROOT"

echo "Updating Lambda code: $API_LAMBDA"
aws lambda update-function-code \
  --function-name "$API_LAMBDA" \
  --zip-file fileb:///tmp/api-lambda-code.zip \
  --query 'FunctionName' --output text

rm -f /tmp/api-lambda-code.zip

echo ""
echo "═══ Step 5: Build frontend ═══"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-api-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)
POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-identity-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`UserPoolId`)].OutputValue' \
  --output text 2>/dev/null || echo "")
CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-identity-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`ClientId`)].OutputValue' \
  --output text 2>/dev/null || echo "")

cd "$PROJECT_ROOT/procurement-agent-ui"
echo "Installing frontend dependencies..."
npm ci

VITE_API_URL="$API_URL" \
VITE_COGNITO_USER_POOL_ID="$POOL_ID" \
VITE_COGNITO_CLIENT_ID="$CLIENT_ID" \
VITE_AGENTCORE_RUNTIME_ARN="$PROCUREMENT_AGENT_ARN" \
npx vite build
echo "Frontend built with API_URL=$API_URL RUNTIME_ARN=$PROCUREMENT_AGENT_ARN"

echo ""
echo "═══ Step 6: Deploy frontend stack ═══"
cd "$CDK_DIR"
cdk deploy ${PROJECT_NAME}-frontend-${ENVIRONMENT} --require-approval never

echo ""
echo "═══ Step 7: Create demo Cognito user ═══"
POOL_ID_FOR_USER=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-identity-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`UserPoolId`)].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$POOL_ID_FOR_USER" ]; then
  # Add custom:role attribute if it doesn't exist
  aws cognito-idp add-custom-attributes --user-pool-id "$POOL_ID_FOR_USER" \
    --custom-attributes 'Name=role,AttributeDataType=String,Mutable=true,StringAttributeConstraints={MaxLength=50}' 2>/dev/null || true

  # Prompt for password or use env var
  DEMO_PASSWORD="${DEMO_PASSWORD:-}"
  if [ -z "$DEMO_PASSWORD" ]; then
    echo -n "  Enter password for demo users (min 8 chars, upper+lower+number+special): "
    read -r DEMO_PASSWORD
    if [ -z "$DEMO_PASSWORD" ]; then
      echo "  No password provided — skipping user creation"
      POOL_ID_FOR_USER=""
    fi
  fi

  if [ -n "$POOL_ID_FOR_USER" ]; then
    # Create users with permanent passwords (no forced change on first login).
    # The temporary password is random per-run and immediately overwritten by
    # the permanent DEMO_PASSWORD below — never hardcode a credential literal.
    for pair in "demo@voltcycle.com Admin" "analyst@voltcycle.com Analyst" "manager@voltcycle.com ProcurementManager"; do
      EMAIL=$(echo "$pair" | awk '{print $1}')
      ROLE=$(echo "$pair" | awk '{print $2}')
      TEMP_PW="Tmp-$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9')-9!"
      aws cognito-idp admin-create-user \
        --user-pool-id "$POOL_ID_FOR_USER" \
        --username "$EMAIL" \
        --temporary-password "$TEMP_PW" \
        --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
        --message-action SUPPRESS 2>/dev/null || true
      aws cognito-idp admin-set-user-password \
        --user-pool-id "$POOL_ID_FOR_USER" \
        --username "$EMAIL" \
        --password "$DEMO_PASSWORD" --permanent 2>/dev/null || true
      aws cognito-idp admin-update-user-attributes \
        --user-pool-id "$POOL_ID_FOR_USER" \
        --username "$EMAIL" \
        --user-attributes Name=custom:role,Value="$ROLE" 2>/dev/null || true
      echo "  $EMAIL -> $ROLE"
    done
  fi
else
  echo "  Skipped — Cognito pool not found"
fi

echo ""
echo "═══ Step 8: Verify deployment ═══"
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-frontend-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text)

echo "Checking backend health..."
HEALTH=$(curl -s --max-time 10 "$API_URL/health" 2>/dev/null || echo '{"status":"unreachable"}')
HEALTH_STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "error")
if [ "$HEALTH_STATUS" = "healthy" ]; then
  echo "  ✓ Backend API: healthy"
else
  echo "  ✗ Backend API: $HEALTH_STATUS (may need a moment for cold start)"
fi

echo "Checking frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$CLOUDFRONT_URL" 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
  echo "  ✓ Frontend: live"
else
  echo "  ✗ Frontend: HTTP $FRONTEND_STATUS (CloudFront may still be propagating)"
fi

echo "Checking SageMaker endpoint..."
SM_STATUS=$(aws sagemaker describe-endpoint --endpoint-name chronos-2-forecast-endpoint --query 'EndpointStatus' --output text 2>/dev/null || echo "NotFound")
if [ "$SM_STATUS" = "InService" ]; then
  echo "  ✓ SageMaker Chronos-2: InService"
else
  echo "  ✗ SageMaker Chronos-2: $SM_STATUS"
fi

echo ""
echo "═══ Deployment complete ═══"
echo ""
echo "  Frontend:  $CLOUDFRONT_URL"
echo "  API:       $API_URL"
echo "  Agent ARN: $PROCUREMENT_AGENT_ARN"
echo "  Users:     demo@voltcycle.com (Admin), analyst@voltcycle.com (Analyst), manager@voltcycle.com (ProcurementManager)"
echo ""
echo "Done!"
