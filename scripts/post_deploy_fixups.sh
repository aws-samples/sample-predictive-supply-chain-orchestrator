#!/bin/bash
# Post-deployment fixups for AgentCore agent
#
# Only handles things that CANNOT be done in CDK:
# - Runtime ID (created by agentcore CLI, not CDK) → API Lambda env var
# - Runtime role IAM (role created by CLI, not CDK)
# - Online Eval Config (needs Runtime ID for log group name)
# - Cedar Policies (needs Gateway live + schema generated)
# - Guardrail ID → Agent Runtime env var (guardrail is CDK, runtime is CLI)
#
# Everything else is in CDK:
# - Gateway/Memory/Policy IDs → API Lambda env vars (cross-stack refs)
# - Lambda IAM (Neptune, SageMaker, CloudWatch Logs)
# - SageMaker endpoint env var
# - Guardrail creation
set -euo pipefail

PROJECT_NAME="procurement-optimization-agent"
ENVIRONMENT=${ENVIRONMENT:-development}
AWS_REGION=${AWS_REGION:-us-east-1}

echo "═══ Post-deploy fixups (runtime-only) ═══"

# ── Read Runtime ID from agentcore config ──────────────────────────
RUNTIME_ID=""
for cfg in .bedrock_agentcore.yaml backend/agentcore_bundle/.bedrock_agentcore.yaml; do
  if [ -f "$cfg" ]; then
    RUNTIME_ID=$(python3 -c "
import yaml
with open('$cfg') as f:
    cfg = yaml.safe_load(f)
for a in cfg.get('agents', {}).values():
    rid = a.get('bedrock_agentcore', {}).get('agent_id', '')
    if rid: print(rid); break
" 2>/dev/null || echo "")
    [ -n "$RUNTIME_ID" ] && break
  fi
done

if [ -z "$RUNTIME_ID" ]; then
  echo "  ✗ Could not find Runtime ID — check .bedrock_agentcore.yaml"
  exit 1
fi
echo "  Runtime: $RUNTIME_ID"

# ── 1. Set Runtime ID on API Lambda ────────────────────────────────
echo ""
echo "Step 1: Setting Runtime ID on API Lambda..."
API_LAMBDA=$(aws cloudformation describe-stack-resources \
  --stack-name ${PROJECT_NAME}-api-${ENVIRONMENT} \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function' && starts_with(LogicalResourceId, 'ApiFunction')].PhysicalResourceId" \
  --output text)

if [ -n "$API_LAMBDA" ]; then
  CURRENT_ENV=$(aws lambda get-function-configuration \
    --function-name "$API_LAMBDA" --query Environment --output json)
  UPDATED_ENV=$(echo "$CURRENT_ENV" | python3 -c "
import sys, json
d = json.load(sys.stdin)
d['Variables']['AGENTCORE_RUNTIME_ID'] = '$RUNTIME_ID'
print(json.dumps(d))
")
  aws lambda update-function-configuration \
    --function-name "$API_LAMBDA" \
    --environment "$UPDATED_ENV" \
    --query 'LastUpdateStatus' --output text
  echo "  ✓ Runtime ID set on API Lambda"
fi

# ── 2. Fix Runtime role IAM (CLI-created role) ─────────────────────
echo ""
echo "Step 2: Fixing Runtime role IAM..."
RUNTIME_ROLE=""
for cfg in .bedrock_agentcore.yaml backend/agentcore_bundle/.bedrock_agentcore.yaml; do
  if [ -f "$cfg" ]; then
    RUNTIME_ROLE=$(python3 -c "
import yaml
with open('$cfg') as f:
    cfg = yaml.safe_load(f)
for a in cfg.get('agents', {}).values():
    role = a.get('aws', {}).get('execution_role', '')
    if role:
        print(role.split('/')[-1])
        break
" 2>/dev/null || echo "")
    [ -n "$RUNTIME_ROLE" ] && break
  fi
done

if [ -n "$RUNTIME_ROLE" ] && [ "$RUNTIME_ROLE" != "None" ]; then
  echo "  Runtime role: $RUNTIME_ROLE"
  aws iam put-role-policy --role-name "$RUNTIME_ROLE" --policy-name agentcore-bedrock-full \
    --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"bedrock-agentcore:*\",\"bedrock:*\"],\"Resource\":\"*\"}]}" \
    && echo "  ✓ AgentCore + Bedrock permissions"
  aws iam put-role-policy --role-name "$RUNTIME_ROLE" --policy-name ecr-access \
    --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ecr:GetAuthorizationToken\",\"ecr:BatchGetImage\",\"ecr:GetDownloadUrlForLayer\"],\"Resource\":\"*\"}]}" \
    && echo "  ✓ ECR permissions"
else
  echo "  ⚠ Could not find runtime role"
fi

# ── 3. Create Online Eval Config ───────────────────────────────────
echo ""
echo "Step 3: Creating Online Eval Config..."
EXISTING_EVAL=$(aws bedrock-agentcore-control list-online-evaluation-configs --query "items[0].onlineEvaluationConfigId" --output text 2>/dev/null || echo "None")
if [ "$EXISTING_EVAL" = "None" ] || [ -z "$EXISTING_EVAL" ]; then
  EVAL_ROLE_ARN=$(aws iam get-role --role-name ProcurementEvalRole --query "Role.Arn" --output text 2>/dev/null || \
    aws iam create-role --role-name ProcurementEvalRole \
      --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"bedrock-agentcore.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
      --query "Role.Arn" --output text)
  aws iam put-role-policy --role-name ProcurementEvalRole --policy-name eval-full \
    --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock:*","bedrock-agentcore:*","logs:*"],"Resource":"*"}]}' 2>/dev/null
  sleep 5

  LOG_GROUP="/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT"

  # Read custom evaluator IDs from CDK stack
  TOOL_EVAL_ID=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-evaluator-${ENVIRONMENT} \
    --query 'Stacks[0].Outputs[?OutputKey==`ToolAccuracyEvaluatorId`].OutputValue' --output text 2>/dev/null || echo "")
  QUALITY_EVAL_ID=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-evaluator-${ENVIRONMENT} \
    --query 'Stacks[0].Outputs[?OutputKey==`QualityEvaluatorId`].OutputValue' --output text 2>/dev/null || echo "")

  # 7 built-in + custom evaluators
  EVALUATORS='[{"evaluatorId":"Builtin.GoalSuccessRate"},{"evaluatorId":"Builtin.Correctness"},{"evaluatorId":"Builtin.ToolSelectionAccuracy"},{"evaluatorId":"Builtin.ToolParameterAccuracy"},{"evaluatorId":"Builtin.Helpfulness"},{"evaluatorId":"Builtin.Faithfulness"},{"evaluatorId":"Builtin.Harmfulness"}'
  if [ -n "$TOOL_EVAL_ID" ] && [ "$TOOL_EVAL_ID" != "None" ]; then
    EVALUATORS="${EVALUATORS},{\"evaluatorId\":\"${TOOL_EVAL_ID}\"}"
    echo "  + Custom: ProcurementToolAccuracy"
  fi
  if [ -n "$QUALITY_EVAL_ID" ] && [ "$QUALITY_EVAL_ID" != "None" ]; then
    EVALUATORS="${EVALUATORS},{\"evaluatorId\":\"${QUALITY_EVAL_ID}\"}"
    echo "  + Custom: ProcurementQuality"
  fi
  EVALUATORS="${EVALUATORS}]"

  EVAL_CONFIG=$(aws bedrock-agentcore-control create-online-evaluation-config \
    --online-evaluation-config-name "procurement_agent_eval" \
    --rule "{\"samplingConfig\":{\"samplingPercentage\":100.0}}" \
    --data-source-config "{\"cloudWatchLogs\":{\"logGroupNames\":[\"$LOG_GROUP\"],\"serviceNames\":[\"procurement_optimization_agent.DEFAULT\"]}}" \
    --evaluators "$EVALUATORS" \
    --evaluation-execution-role-arn "$EVAL_ROLE_ARN" \
    --enable-on-create \
    --query "onlineEvaluationConfigId" --output text 2>/dev/null || echo "failed")
  echo "  ✓ Eval config: $EVAL_CONFIG"
else
  echo "  Already exists: $EXISTING_EVAL"
fi

# ── 4. Cedar Policies ─────────────────────────────────────────────
# PolicyEngine is in LOG_ONLY mode (CDK). Cedar policies are not created
# automatically — the "Overly Permissive" safety check rejects broad permits.
# Create specific policies manually when ready to switch to ENFORCE mode.
echo ""
echo "Step 4: Cedar Policies — PolicyEngine in LOG_ONLY mode (no policies needed)"

# ── 5. Push Guardrail ID to Agent Runtime ──────────────────────────
echo ""
echo "Step 5: Updating Agent Runtime with Guardrail ID..."
GUARDRAIL_ID=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-guardrail-${ENVIRONMENT} \
  --query 'Stacks[0].Outputs[?OutputKey==`GuardrailId`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$RUNTIME_ID" ] && [ -n "$GUARDRAIL_ID" ] && [ "$GUARDRAIL_ID" != "None" ]; then
  python3 -c "
import boto3
ctrl = boto3.client('bedrock-agentcore-control', region_name='$AWS_REGION')
runtime = ctrl.get_agent_runtime(agentRuntimeId='$RUNTIME_ID')
env_vars = runtime.get('environmentVariables', {})

# Check if already set
if env_vars.get('GUARDRAIL_ID') == '$GUARDRAIL_ID':
    print('  Already set')
else:
    env_vars['GUARDRAIL_ID'] = '$GUARDRAIL_ID'
    env_vars['GUARDRAIL_VERSION'] = 'DRAFT'
    # update requires full params — use the existing config
    ctrl.update_agent_runtime(
        agentRuntimeId='$RUNTIME_ID',
        agentRuntimeArtifact=runtime['agentRuntimeArtifact'],
        roleArn=runtime['roleArn'],
        networkConfiguration=runtime.get('networkConfiguration', {'networkMode': 'PUBLIC'}),
        environmentVariables=env_vars,
        **({'authorizerConfiguration': runtime['authorizerConfiguration']} if 'authorizerConfiguration' in runtime else {}),
        **({'requestHeaderConfiguration': runtime['requestHeaderConfiguration']} if 'requestHeaderConfiguration' in runtime else {}),
    )
    print('  ✓ GUARDRAIL_ID=$GUARDRAIL_ID set on runtime')
" 2>&1 || echo "  ⚠ Could not update runtime env vars"
else
  echo "  ⚠ Skipped — RUNTIME_ID=${RUNTIME_ID:-empty} GUARDRAIL_ID=${GUARDRAIL_ID:-empty}"
fi

echo ""
echo "═══ Post-deploy fixups complete ═══"
