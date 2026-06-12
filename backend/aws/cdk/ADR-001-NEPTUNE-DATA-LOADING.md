# ADR-001: Neptune Data Loading Approach

**Status**: Accepted  
**Date**: 2026-03-09  
**Decision Makers**: CDE Team  

## Context

We need a repeatable way to load initial data into Amazon Neptune graph database across AWS accounts. The data consists of:
- 15 supplier vertices
- 18 material vertices  
- 41 supplier-material relationship edges

## Decision Drivers

- **Repeatability**: Must work consistently across AWS accounts
- **Simplicity**: Junior developers should understand it
- **Reliability**: Must not fail due to network/timeout issues
- **Maintainability**: Easy to debug and modify
- **CDE Principle**: What is the MINIMUM that solves this problem?

## Options Considered

### Option 1: CDK Custom Resource (Lambda-based)
**Pros**:
- Pure Infrastructure as Code
- Automatic execution on stack deployment
- No manual steps after initial setup

**Cons**:
- Complex VPC networking (Lambda needs S3 + Neptune access)
- VPC endpoint routing configuration required
- Lambda cold starts and 10-minute timeout limits
- Harder to debug (CloudWatch logs, Custom Resource framework)
- Over-engineered for one-time data load

**Attempted**: Yes - failed due to VPC networking issues (Lambda couldn't reach S3)

### Option 2: Shell Script (deploy.sh) ✅ SELECTED
**Pros**:
- Simple and direct (no VPC networking complexity)
- Easy to understand and debug
- Works immediately without infrastructure changes
- Full control over execution flow
- Can be run from any machine with AWS CLI
- Still repeatable (just run the script)

**Cons**:
- Requires manual execution (one command)
- Not "pure" Infrastructure as Code
- Needs AWS CLI and Python installed locally

**Status**: Working and tested

### Option 3: Manual Python Script
**Pros**:
- Simple Python code
- Easy to modify

**Cons**:
- Not integrated with CDK deployment
- Requires manual configuration updates
- Less repeatable than shell script

## Decision

**Use Option 2: Shell Script (`deploy.sh`)**

## Rationale

Following CDE Phase 2 principle: "What is the MINIMUM that solves this problem?"

The shell script is the simplest solution that works:
1. **Works immediately** - No VPC networking issues
2. **Easy to debug** - Direct output, no Lambda/CloudWatch complexity
3. **Repeatable** - Single command deploys everything
4. **Maintainable** - Any developer can read and modify bash/Python
5. **Reliable** - No Lambda timeouts or cold starts

The Custom Resource approach violated the "simplest solution" principle by adding:
- VPC Lambda complexity
- S3 VPC endpoint routing configuration
- Custom Resource framework overhead
- CloudWatch log debugging
- 10-minute timeout constraints

For a **one-time data load** of small datasets, the shell script is the right tool.

## Consequences

### Positive
- ✅ Deployment works reliably
- ✅ Easy to troubleshoot
- ✅ No VPC networking complexity
- ✅ Fast execution (no Lambda cold start)
- ✅ Clear error messages

### Negative
- ❌ Requires one manual command after CDK deployment
- ❌ Not "pure" IaC (but still scripted and repeatable)

### Mitigation
- Document the deployment process clearly
- Make `deploy.sh` idempotent (can run multiple times safely)
- Include `deploy.sh` in CI/CD pipelines if needed

## Implementation

```bash
# Complete deployment (infrastructure + data)
./deploy.sh

# Or step-by-step:
cd backend/aws/cdk
cdk deploy --all
cd ../../..
./deploy.sh  # Only runs data loading steps
```

## Lessons Learned

1. **Don't over-engineer**: Custom Resource was overkill for one-time data load
2. **VPC Lambda is complex**: Requires careful networking configuration
3. **Shell scripts are underrated**: Sometimes the simplest tool is the best
4. **CDE Phase 2 matters**: Always ask "what's the MINIMUM solution?"

## Future Considerations

If requirements change:
- **Incremental updates**: Consider Lambda triggered by S3 events
- **Large datasets**: Use AWS Glue or Step Functions
- **Frequent updates**: Build proper data pipeline with CDC

For now, the shell script is the right solution.

## References

- CDE Framework Phase 2: Design (Simplest Solution)
- `deploy.sh` - Complete deployment script
- `backend/scripts/transform_to_neptune_csv.py` - CSV transformation
- `backend/scripts/load_neptune_bulk.py` - Neptune bulk loader invocation
