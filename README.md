# Predictive Supply Chain Orchestrator

AI-powered procurement optimization for VoltCycle e-bike manufacturing. Combines SageMaker Chronos-2 demand forecasting, multi-objective Pareto optimization, and a multi-agent AI orchestrator to replace spreadsheet-based supplier allocation with mathematically optimal decisions.

## What It Does

1. **Demand Forecasting** -- SageMaker Chronos-2 (120M params, GPU) generates P10/P50/P90 probabilistic demand forecasts
2. **Multi-Objective Optimization** -- SLSQP solver minimizes cost, risk, and lead time simultaneously. Generates 3 Pareto strategies: Cost-Optimized, Balanced, Risk-Diversified
3. **Supplier Intelligence** -- Neptune graph database with 15 suppliers across 10 countries. Dynamic 6-dimension risk scoring with trend detection
4. **Risk Simulation** -- 5 geopolitical scenarios (Hormuz, Suez, Taiwan, tariffs, port strikes)
5. **Purchase Requisitions** -- SAP ME51N-format PRs from approved optimization solutions
6. **AI Agent** -- Natural language interface via 3 specialist agents orchestrated by Amazon Bedrock AgentCore

## Architecture

```
                         Procurement Team
                        /                \
                Direct UI              Agent Chat
                   |                      |
            API Gateway           AgentCore Runtime
            Flask Lambda          Orchestrator (Nova Lite)
                   |                /     |      \
                   |     Procurement  Forecast  Intelligence
                   |       Agent      Agent       Agent
                   |        (Claude Sonnet 4, all three)
                   |                \     |      /
                   |              MCP Gateway (JWT + IAM)
                   |                      |
                   +----------+-----------+
                              |
                     Shared Lambda Tools
              optimize | query | explain | create_prs
                              |
                 +------------+------------+
                 |            |            |
              Neptune     SageMaker    Optimization
            (graph DB)   (Chronos-2)  (scipy SLSQP)
```

Both paths invoke the same Lambda tools. The agent adds reasoning, memory, and multi-turn context on top.

## Tech Stack

| Layer | Services |
|-------|----------|
| **Frontend** | React 19, Vite, TypeScript, Recharts, Leaflet -- CloudFront + S3 |
| **Auth** | Cognito (3 personas: Analyst, Manager, Admin) |
| **API** | API Gateway + Flask Lambda (Mangum, VPC) |
| **Agents** | Orchestrator (Nova Lite) + 3 specialists (Claude Sonnet 4) |
| **AgentCore** | MCP Gateway (4 tools), Memory (3 strategies), Cedar Policies, 9 Evaluators, Guardrails |
| **ML** | SageMaker Chronos-2 (ml.g5.2xlarge GPU, JumpStart) |
| **Optimization** | scipy SLSQP -- TCO model with freight, carrying cost, carbon, volume discounts |
| **Data** | Neptune (33 nodes, 41 edges), S3 (CSV, PRs) |
| **Observability** | AWS OTEL Distro (auto-instrumented traces + logs) |
| **IaC** | 14 CDK stacks |

## Quick Start (Local Development)

### Prerequisites

- Python 3.10+, Node.js 18+, AWS credentials (for Bedrock)

### Start All Services

```bash
# Terminal 1 -- Backend (port 5001)
cd backend && python -m api.server

# Terminal 2 -- Frontend (port 5174)
cd procurement-agent-ui && npm install && npm run dev
```

Open http://localhost:5174. Run Forecast --> select P90 --> Optimize.

## Production Deployment

### Prerequisites

- AWS CLI, CDK CLI, Python 3.11+, Node.js 18+
- `pip install bedrock-agentcore-starter-toolkit "sagemaker>=2.200,<3" uv`
- `pip install -r backend/aws/cdk/requirements.txt`

### Deploy (~25 min first run)

```bash
bash scripts/deploy-all.sh
```

Steps: Lambda layer --> 12 CDK stacks --> SageMaker Chronos-2 --> AgentCore agents --> Frontend to CloudFront.

### Teardown

```bash
bash scripts/teardown.sh
```

## Cognito Users

| Email | Role |
|-------|------|
| `demo@voltcycle.com` | Admin |
| `manager@voltcycle.com` | Procurement Manager |
| `analyst@voltcycle.com` | Analyst |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/demand/forecast` | Chronos-2 forecast (P10/P50/P90) |
| POST | `/api/optimize` | Pareto optimization (3 strategies) |
| GET | `/api/suppliers` | List suppliers (Neptune/CSV) |
| GET | `/api/materials` | List materials |
| POST | `/api/purchase-requisitions` | Create SAP-format PRs |
| GET | `/api/graph/network` | Supplier-material graph |
| GET | `/api/defects` | Defect tracking data |
| POST | `/api/risk-simulation` | Geopolitical scenario simulation |

Agent chat bypasses API Gateway -- frontend calls AgentCore Runtime directly via HTTP with Cognito JWT (90s timeout).

## Optimization Engine

**Solver:** scipy SLSQP (Sequential Least Squares Quadratic Programming)

**Objective:** Weighted sum of cost, risk, and lead time (normalized to comparable ranges)

**3 Strategies:**

| Strategy | Cost | Risk | Lead Time | Max Concentration |
|----------|------|------|-----------|-------------------|
| Cost-Optimized | 0.80 | 0.05 | 0.15 | 60% |
| Balanced | 0.35 | 0.30 | 0.35 | 40% |
| Risk-Diversified | 0.05 | 0.60 | 0.35 | 25% |

**TCO Model:** base cost + volume discounts + regional freight (2-8%) + carrying cost + carbon ($0.05/kg) - payment term benefits

**Risk Scoring:** 6 dimensions (geopolitical, financial, quality, delivery, defect rate, defect history) + exponentially weighted 3-month trend factor

**Constraints:** demand satisfaction, supplier concentration, MOQ, delivery feasibility, budget bounds

## Agent Architecture

```
Orchestrator (Nova Lite -- intent classification)
  |
  +-- Procurement Agent (Claude Sonnet 4)
  |     Tools: optimize_suppliers, query_supplier_data, explain_solution, create_purchase_requisitions
  |
  +-- Demand Forecast Agent (Claude Sonnet 4)
  |     Tools: query_supplier_data (query_type: forecast_demand)
  |
  +-- Supplier Intelligence Agent (Claude Sonnet 4)
        Tools: query_supplier_data (query_types: simulate_risk, get_supplier_performance, get_sourcing_summary, find_alternative_suppliers)
```

**Enterprise Features:**
- **Memory:** Semantic (supplier insights) + Preference (user behavior) + Summarization (session context) -- 90-day TTL, per-actor scoped
- **Evaluators:** 7 built-in (GoalSuccessRate, Correctness, ToolSelection, Faithfulness, etc.) + 2 custom LLM-as-Judge (ProcurementToolAccuracy, ProcurementQuality) -- 100% sampling
- **Cedar Policies:** 3 roles (Analyst/Manager/Admin), deny rules for budget/quantity limits, LOG_ONLY mode
- **Guardrails:** Bedrock Guardrail for PII detection and content safety
- **Observability:** OTEL auto-instrumented, CloudWatch structured logs

## Project Structure

```
SupplyChainOptimization-v2/
|-- procurement-agent-ui/        # React frontend (20+ components)
|-- backend/
|   |-- api/server.py            # Flask API (also runs in Lambda)
|   |-- agentcore_bundle/        # Agent runtime (main.py entrypoint)
|   |-- core/optimization/       # SLSQP Pareto engine
|   |-- evaluations/             # Eval suite (10 test cases)
|   |-- aws/cdk/                 # 14 CDK stacks
|   `-- aws/lambda_tools/        # Lambda tool handlers
|-- demand-forecasting/          # Chronos-2 forecasting module
|-- data/                        # Supplier/material CSVs (15 files)
|-- scripts/                     # deploy-all.sh, teardown.sh
`-- docs/                        # Architecture, schema, requirements
```

## Cost Estimate (us-east-1)

| Resource | Cost |
|----------|------|
| Neptune db.t3.medium | ~$73/month |
| NAT Gateway | ~$32/month |
| SageMaker ml.g5.2xlarge | ~$912/month (24/7) |
| Lambda, S3, CloudFront, Cognito | < $5/month |
| **Total** | **~$1,022/month** |

Delete SageMaker endpoint when not in use: `aws sagemaker delete-endpoint --endpoint-name chronos-2-forecast-endpoint`

## Documentation

- [CDK Deployment Guide](./backend/aws/cdk/DEPLOYMENT.md)
- [Data Schema](./docs/DATA_SCHEMA.md)
- [Graph DB Strategy](./docs/GRAPH_DB_STRATEGY.md)
- [Architecture Details](./docs/ARCHITECTURE.md)
- [Scalability Notes](./docs/SCALABILITY.md)
