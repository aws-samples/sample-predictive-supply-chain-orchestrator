# Architecture: VoltCycle Procurement Optimization Agent

## System Overview

```
                              ┌──────────────────────────────────┐
                              │       FRONTEND (React/Vite)      │
                              │  CloudFront + S3, Cognito Auth   │
                              │  Command Center Industrial Theme │
                              └───────┬──────────────┬───────────┘
                                      │              │
                          CHAT FLOW   │              │  REST FLOW
                          (direct)    │              │  (API GW)
                                      │              │
             ┌────────────────────────▼──┐    ┌─────▼─────────────────────┐
             │  AgentCore Runtime         │    │  API Gateway + Flask      │
             │  (HTTP, Bearer JWT,        │    │  Lambda (VPC)             │
             │   90s timeout)             │    │                           │
             │                            │    │  /api/suppliers           │
             │  Strands Agent             │    │  /api/materials           │
             │  + Claude Sonnet 4         │    │  /api/optimize            │
             │                            │    │  /api/demand/forecast     │
             │  ┌─────────────────────┐   │    │  /api/graph/*             │
             │  │ Gateway MCP Tools   │   │    │  /api/defects             │
             │  │ (JWT auth)          │   │    │  /api/purchase-reqs       │
             │  │  - optimize         │   │    └──────┬──────┬──────┬─────┘
             │  │  - query            │   │           │      │      │
             │  │  - explain          │   │           ▼      ▼      ▼
             │  └─────────────────────┘   │     Neptune   S3    SageMaker
             │                            │     (graph)  (data) (Chronos-2)
             │  ┌─────────────────────┐   │
             │  │ Memory              │   │
             │  │ (semantic +         │   │
             │  │  preferences +      │   │
             │  │  summarization)     │   │
             │  └─────────────────────┘   │
             │                            │
             │  ┌─────────────────────┐   │
             │  │ Guardrails          │   │
             │  │ (topic + content    │   │
             │  │  filtering)         │   │
             │  └─────────────────────┘   │
             │                            │
             │  ┌─────────────────────┐   │
             │  │ Online Evaluations  │   │
             │  │ (7 evaluators,      │   │
             │  │  100% sampling)     │   │
             │  └─────────────────────┘   │
             │                            │
             │  ┌─────────────────────┐   │
             │  │ Policy Engine       │   │
             │  │ (Cedar, LOG_ONLY)   │   │
             │  └─────────────────────┘   │
             │                            │
             │  ┌─────────────────────┐   │
             │  │ Observability       │   │
             │  │ (OTEL, automatic)   │   │
             │  └─────────────────────┘   │
             └────────────────────────────┘
```

## Data Flows

### Chat Flow (Agent)
```
Frontend (Cognito JWT) → AgentCore Runtime (direct HTTP, 90s timeout)
  → Strands Agent + Bedrock Claude Sonnet 4
    → Gateway MCP tools (JWT auth, 3 Lambda targets: optimize, query, explain)
    → Memory (AgentCoreMemorySessionManager — semantic + preferences + summarization)
    → Guardrails (Bedrock Guardrail — topic filtering, content filtering)
    → Evaluations (online eval, 7 built-in evaluators, 100% sampling)
    → Observability (aws-opentelemetry-distro, automatic traces + logs)
```

### REST Flow (Data + Optimization)
```
Frontend → API Gateway → Flask Lambda (VPC)
  → Neptune (supplier graph queries, Gremlin)
  → S3 (CSV data, purchase requisitions)
  → SageMaker (Chronos-2 demand forecasting, GPU inference)
  → scipy (Pareto multi-objective optimization, in-Lambda)
```

### Optimization Engine
```
POST /api/optimize → Lambda runs scipy optimization
  ├── Reads supplier/material data from S3 CSV
  ├── 16 materials x 2-3 suppliers each
  ├── Greedy per-material selection with weight profiles
  ├── TCO: base price + freight + carrying + carbon costs
  └── Returns 4 Pareto-optimal strategies:
      Budget ($905K) | Balanced ($963K) | Premium ($1,098K) | Resilient ($1,387K)
```

### Neptune Graph Queries
```
GET /api/graph/network           → Full supplier-material graph (33 nodes, 41 edges)
GET /api/graph/alternatives/{id} → g.V('MAT-001').in('supplies')
GET /api/graph/supplier-materials/{id} → g.V('SUP-001').out('supplies')
GET /api/suppliers               → g.V().hasLabel('Supplier').elementMap()
GET /api/materials               → g.V().hasLabel('Material').elementMap()
```

### Purchase Requisition Flow
```
User approves solution → POST /api/purchase-requisitions
  → Groups allocations by supplier
  → Writes PR JSON to S3 (purchase-requisitions/ prefix)
  → SAP S/4HANA ME51N format (PR number, plant, purchase org)
```

## Deployed Resources (us-east-1)

| Resource | ID | Details |
|----------|----|---------|
| Runtime | `procurement_optimization_agent-7Oun1q2AkV` | starter-toolkit, CodeBuild ARM64 |
| Gateway (JWT) | `procurement-optimization-gateway-jwt-tkrfaendc5` | CUSTOM_JWT, Cognito |
| Memory | `ProcurementAgentMemory-qKZH084FPM` | semantic + preferences + summarization |
| Policy Engine | `ProcurementPolicyEngine-0ah92mw_uq` | Cedar, LOG_ONLY |
| Guardrail | `m34inb353ymo` | topic + content filtering |
| Online Eval | `procurement_agent_eval-14LpzW3Fxn` | 7 evaluators, 100% sampling |
| Cognito | Pool `us-east-1_65nSiUqYA` | 3 users: admin, manager, analyst |

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React 19, Vite, TypeScript, Recharts, Leaflet | Procurement UI (Command Center theme) |
| Auth | Amazon Cognito | User authentication (3 personas) |
| CDN | CloudFront + S3 | Static hosting, HTTPS |
| API | API Gateway + Lambda (Flask, VPC) | REST endpoints for data/optimization |
| LLM | Amazon Bedrock (Claude Sonnet 4) | Agent reasoning |
| Agent Framework | Strands SDK | Tool-augmented agent |
| Agent Hosting | Bedrock AgentCore Runtime | Managed agent deployment (direct HTTP) |
| Agent Gateway | AgentCore Gateway (JWT) | MCP tool routing to Lambda targets |
| Agent Memory | AgentCore Memory | Semantic + preferences + summarization |
| Guardrails | Bedrock Guardrails | Topic + content filtering |
| Evaluations | AgentCore Online Eval | 7 built-in evaluators, 100% sampling |
| Policy | AgentCore Policy (Cedar) | Declarative business rules |
| Observability | aws-opentelemetry-distro | Automatic traces + logs |
| Graph DB | Amazon Neptune | Supplier-material graph (33 nodes, 41 edges) |
| Forecasting | SageMaker Chronos-2 | Probabilistic demand forecasting (GPU) |
| Optimization | scipy SLSQP + numpy | Multi-objective Pareto solver |
| IaC | AWS CDK (Python) | 14 CloudFormation stacks |

## CDK Stacks (14)

| Stack | Resources |
|-------|-----------|
| Identity | Cognito User Pool, Client, RBAC groups |
| Lambda Layer | numpy, scipy, pydantic, gremlinpython |
| Data | Neptune cluster, S3 bucket, VPC, security groups |
| Lambda Tools | Optimization, Explainability, Data Access Lambdas |
| Neptune Loader | Custom Resource for bulk CSV loading |
| Agent | AgentCore Runtime (deployed via starter-toolkit, not CDK) |
| API | Lambda (Flask, VPC), API Gateway with CORS |
| Frontend | S3 bucket, CloudFront distribution, OAI |
| SageMaker Forecast | Chronos-2 endpoint (ml.g5.2xlarge GPU) |
| Forecast Agent | Forecast AgentCore Runtime |
| + additional stacks | Supporting infrastructure |

Note: Agent runtime is deployed via `bedrock-agentcore-starter-toolkit` (CodeBuild ARM64), not CDK.

## Security

- Cognito auth required for all UI access (3 user personas)
- JWT flows: Frontend -> AgentCore Runtime (direct Bearer token)
- Gateway MCP tools authenticated via JWT (CUSTOM_JWT provider)
- Neptune IAM authentication (SigV4 signed HTTP)
- Lambda in VPC with security group for Neptune port 8182
- S3 block public access + CloudFront OAI
- Gremlin query input validation (parameterized queries)
- Bedrock Guardrails for topic + content filtering
- Cedar policies for business rule enforcement
- No hardcoded credentials (IAM roles + JWT throughout)
- CORS scoped to CloudFront domain + localhost
- Error responses sanitized (no internal details)
