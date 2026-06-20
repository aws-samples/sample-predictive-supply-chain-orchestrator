#!/bin/bash
# Complete teardown script for Procurement Optimization Agent
#
# Deletes ALL resources: SageMaker endpoint, AgentCore agents, CDK stacks,
# and orphaned CloudFormation stacks not managed by CDK.
#
# Usage: bash scripts/teardown.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CDK_DIR="$PROJECT_ROOT/backend/aws/cdk"
PROJECT_NAME="procurement-optimization-agent"
AWS_REGION=${AWS_REGION:-us-east-1}

echo "═══ Teardown: Procurement Optimization Agent ═══"
echo "Region: $AWS_REGION"
echo ""

echo "Step 0: Delete Bedrock Guardrails..."
python3 -c "
import boto3
client = boto3.client('bedrock', region_name='$AWS_REGION')
for g in client.list_guardrails().get('guardrails', []):
    name = g.get('name', '')
    if 'Procurement' in name or 'procurement' in name:
        gid = g.get('guardrailId', g.get('id', ''))
        if gid:
            try:
                client.delete_guardrail(guardrailIdentifier=gid)
                print(f'  Deleted guardrail: {name} ({gid})')
            except Exception as e:
                print(f'  Failed: {e}')
" 2>/dev/null || echo "  Could not delete guardrails"


echo ""
echo "Step 1: Delete SageMaker endpoint..."
aws sagemaker delete-endpoint --endpoint-name chronos-2-forecast-endpoint --region $AWS_REGION 2>/dev/null && echo "  Endpoint deletion initiated" || echo "  No endpoint found"
aws sagemaker delete-endpoint-config --endpoint-config-name chronos-2-forecast-endpoint --region $AWS_REGION 2>/dev/null || true

echo ""
echo "Step 2: Delete AgentCore resources (correct dependency order)..."
python3 -c "
import boto3, time
ctrl = boto3.client('bedrock-agentcore-control', region_name='$AWS_REGION')

# 1. Detach policy engines from gateways (must happen before gateway delete)
for gw in ctrl.list_gateways().get('items', []):
    if 'procurement' in gw.get('name', '').lower():
        gw_id = gw['gatewayId']
        # 2. Delete gateway targets first (must happen before gateway delete)
        try:
            targets = ctrl.list_gateway_targets(gatewayIdentifier=gw_id).get('items', [])
            for t in targets:
                try:
                    ctrl.delete_gateway_target(gatewayIdentifier=gw_id, targetId=t['targetId'])
                    print(f'  Deleted target: {gw_id}/{t[\"name\"]}')
                except Exception as e:
                    print(f'  Failed target: {e}')
            if targets:
                time.sleep(5)
        except Exception as e:
            print(f'  Failed listing targets: {e}')
        # 3. Now delete the gateway
        try:
            ctrl.delete_gateway(gatewayIdentifier=gw_id)
            print(f'  Deleted gateway: {gw.get(\"name\", gw_id)}')
        except Exception as e:
            print(f'  Failed gateway: {e}')

# 4. Delete runtime endpoints first, then runtimes
for agent in ctrl.list_agent_runtimes().get('agentRuntimes', []):
    name = agent.get('agentRuntimeName', '')
    if 'procurement' in name.lower() or 'forecast' in name.lower() or 'demand' in name.lower():
        rid = agent['agentRuntimeId']
        # Delete endpoints
        try:
            eps = ctrl.list_agent_runtime_endpoints(agentRuntimeId=rid).get('items', [])
            for ep in eps:
                try:
                    ctrl.delete_agent_runtime_endpoint(agentRuntimeId=rid, agentRuntimeEndpointId=ep['agentRuntimeEndpointId'])
                    print(f'  Deleted endpoint: {rid}/{ep[\"agentRuntimeEndpointId\"]}')
                except Exception as e:
                    print(f'  Failed endpoint: {e}')
            if eps:
                print(f'  Waiting for endpoints to delete...')
                time.sleep(15)
        except Exception as e:
            print(f'  Failed listing endpoints: {e}')
        # Now delete runtime
        try:
            ctrl.delete_agent_runtime(agentRuntimeId=rid)
            print(f'  Deleted runtime: {name}')
        except Exception as e:
            print(f'  Failed runtime {name}: {e}')

# 5. Delete policy engines (policies auto-deleted with engine)
try:
    for pe in ctrl.list_policy_engines().get('items', ctrl.list_policy_engines().get('policyEngines', [])):
        if 'procurement' in pe.get('name', pe.get('policyEngineName', '')).lower():
            try:
                # Delete policies first
                policies = ctrl.list_policies(policyEngineId=pe['policyEngineId']).get('policies', [])
                for p in policies:
                    try:
                        ctrl.delete_policy(policyEngineId=pe['policyEngineId'], policyId=p['policyId'])
                        print(f'  Deleted policy: {p.get(\"name\",\"?\")}')
                    except: pass
                ctrl.delete_policy_engine(policyEngineId=pe['policyEngineId'])
                print(f'  Deleted policy engine: {pe.get(\"name\", pe.get(\"policyEngineName\",\"?\"))}')
            except Exception as e:
                print(f'  Failed policy engine: {e}')
except Exception as e:
    print(f'  Failed listing policy engines: {e}')

# 6. Delete memory
try:
    for mem in ctrl.list_memory().get('items', []):
        name = mem.get('name', mem.get('memoryName', ''))
        if 'procurement' in name.lower():
            try:
                ctrl.delete_memory(memoryId=mem.get('memoryId', ''))
                print(f'  Deleted memory: {name}')
            except Exception as e:
                print(f'  Failed memory: {e}')
except Exception as e:
    print(f'  Failed listing memory: {e}')

# 7. Delete evaluators and eval configs
try:
    for ec in ctrl.list_online_evaluation_configs().get('items', []):
        try:
            ctrl.delete_online_evaluation_config(onlineEvaluationConfigId=ec['onlineEvaluationConfigId'])
            print(f'  Deleted eval config: {ec.get(\"onlineEvaluationConfigName\",\"?\")}')
        except Exception as e:
            print(f'  Failed eval config: {e}')
except: pass

print('  AgentCore cleanup complete')
" 2>/dev/null || echo "  Could not clean AgentCore resources"

echo ""
echo "Step 3: Delete orphaned CloudWatch log groups..."
for lg in /procurement-agent/traces /procurement-agent/gateway-access; do
  aws logs delete-log-group --log-group-name "$lg" --region $AWS_REGION 2>/dev/null && echo "  Deleted $lg" || true
done

echo ""
echo "Step 4a: Empty versioned S3 buckets..."
python3 -c "
import boto3
s3_client = boto3.client('s3', region_name='$AWS_REGION')
s3 = boto3.resource('s3', region_name='$AWS_REGION')
buckets = [b['Name'] for b in s3_client.list_buckets().get('Buckets', []) if 'procurement' in b['Name'].lower()]
for name in buckets:
    try:
        s3.Bucket(name).object_versions.delete()
        s3_client.delete_bucket(Bucket=name)
        print(f'  Deleted bucket: {name}')
    except Exception as e:
        print(f'  Failed {name}: {e}')
if not buckets: print('  No procurement buckets found')
" 2>/dev/null || echo "  Could not clean S3 buckets"

echo ""
echo "Step 4b: Clean up orphaned VPC ENIs..."
python3 -c "
import boto3, time
ec2 = boto3.client('ec2', region_name='$AWS_REGION')
# Find all ENIs with procurement-related descriptions
enis = ec2.describe_network_interfaces(
    Filters=[{'Name': 'description', 'Values': ['*procurement-optimization*']}]
).get('NetworkInterfaces', [])
for eni in enis:
    eid = eni['NetworkInterfaceId']
    if eni['Status'] == 'in-use':
        att = eni.get('Attachment', {})
        if att:
            try:
                ec2.detach_network_interface(AttachmentId=att['AttachmentId'], Force=True)
                time.sleep(3)
            except: pass
    try:
        ec2.delete_network_interface(NetworkInterfaceId=eid)
        print(f'  Deleted ENI {eid}')
    except Exception as e:
        print(f'  Failed {eid}: {e}')
if not enis: print('  No orphaned ENIs found')
" 2>/dev/null || echo "  Could not clean ENIs"

echo ""
echo "Step 5: Delete ALL procurement CloudFormation stacks..."
echo "  Finding stacks..."
STACKS=$(python3 -c "
import boto3
cf = boto3.client('cloudformation', region_name='$AWS_REGION')
stacks = cf.list_stacks(StackStatusFilter=[
    'CREATE_COMPLETE','UPDATE_COMPLETE','ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE','IMPORT_COMPLETE'
])
names = [s['StackName'] for s in stacks['StackSummaries'] if '$PROJECT_NAME' in s['StackName']]
print(' '.join(names))
")

if [ -z "$STACKS" ]; then
  echo "  No stacks found"
else
  echo "  Found: $STACKS"

  echo "  Trying CDK destroy --all first..."
  cd "$CDK_DIR"
  source "$PROJECT_ROOT/.venv/bin/activate" 2>/dev/null || true
  export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
  cdk destroy --all --force || echo "  CDK destroy completed (some may have failed)"

  echo "  Cleaning up any remaining stacks..."
  for stack in $STACKS; do
    STATUS=$(aws cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0].StackStatus' --output text --region $AWS_REGION 2>/dev/null || echo "DELETED")
    if [ "$STATUS" != "DELETED" ] && [ "$STATUS" != "DELETE_COMPLETE" ]; then
      echo "  Deleting $stack ($STATUS)..."
      aws cloudformation delete-stack --stack-name "$stack" --region $AWS_REGION 2>/dev/null || true
    fi
  done

  echo "  Waiting for deletions to complete (this may take 10+ minutes for Neptune)..."
  for stack in $STACKS; do
    aws cloudformation wait stack-delete-complete --stack-name "$stack" --region $AWS_REGION 2>/dev/null || true
  done

  echo "  Retrying any DELETE_FAILED stacks (ENI/VPC dependencies)..."
  for attempt in 1 2 3; do
    FAILED=$(python3 -c "
import boto3
cf = boto3.client('cloudformation', region_name='$AWS_REGION')
stacks = cf.list_stacks(StackStatusFilter=['DELETE_FAILED'])
failed = [s['StackName'] for s in stacks['StackSummaries'] if '$PROJECT_NAME' in s['StackName']]
print(' '.join(failed))
")
    if [ -z "$FAILED" ]; then break; fi
    echo "  Attempt $attempt: retrying $FAILED"
    # Clean ENIs that may be blocking
    python3 -c "
import boto3, time
ec2 = boto3.client('ec2', region_name='$AWS_REGION')
enis = ec2.describe_network_interfaces(
    Filters=[{'Name': 'description', 'Values': ['*procurement-optimization*']}]
).get('NetworkInterfaces', [])
for eni in enis:
    if eni['Status'] == 'in-use':
        att = eni.get('Attachment', {})
        if att:
            try: ec2.detach_network_interface(AttachmentId=att['AttachmentId'], Force=True); time.sleep(3)
            except: pass
    try: ec2.delete_network_interface(NetworkInterfaceId=eni['NetworkInterfaceId'])
    except: pass
" 2>/dev/null || true
    for stack in $FAILED; do
      aws cloudformation delete-stack --stack-name "$stack" --region $AWS_REGION 2>/dev/null || true
    done
    sleep 15
    for stack in $FAILED; do
      aws cloudformation wait stack-delete-complete --stack-name "$stack" --region $AWS_REGION 2>/dev/null || true
    done
  done
fi

echo ""
echo "Step 6: Delete ECR repositories created by the AgentCore toolkit..."
# The bedrock-agentcore starter toolkit builds and pushes agent container
# images to ECR repos named bedrock-agentcore-*. These are not CDK-managed,
# so they (and their stored images) outlive `cdk destroy` and incur storage
# cost. Force-delete them here.
for repo in $(aws ecr describe-repositories --region $AWS_REGION \
    --query "repositories[?starts_with(repositoryName, 'bedrock-agentcore')].repositoryName" \
    --output text 2>/dev/null); do
  echo "  Deleting ECR repo: $repo"
  aws ecr delete-repository --repository-name "$repo" --force --region $AWS_REGION 2>/dev/null \
    && echo "    deleted" || echo "    (already gone)"
done

echo ""
echo "Step 7: Verify cleanup..."
REMAINING=$(python3 -c "
import boto3
cf = boto3.client('cloudformation', region_name='$AWS_REGION')
stacks = cf.list_stacks(StackStatusFilter=['CREATE_COMPLETE','UPDATE_COMPLETE','DELETE_IN_PROGRESS'])
remaining = [s['StackName'] for s in stacks['StackSummaries'] if '$PROJECT_NAME' in s['StackName']]
print(' '.join(remaining) if remaining else 'ALL CLEAN')
")
echo "  $REMAINING"

echo ""
echo "═══ Teardown complete ═══"
