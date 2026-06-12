# Technical FAQ — Predictive Supply Chain Orchestrator

---

## Optimization

### What algorithm do you use for supplier optimization?

**SLSQP** (Sequential Least Squares Quadratic Programming) from scipy. It's a gradient-based constrained nonlinear optimizer. We chose it because our problem has continuous variables (allocation fractions 0-1), smooth objective functions, and equality/inequality constraints — exactly what SLSQP is designed for.

### What is the objective function?

A weighted sum of three normalized objectives:

```
minimize: w_cost × (TCO / 1,000,000) + w_risk × (risk / 10) + w_lead × (lead_time / 60)
```

Each objective is divided by a scaling constant so cost (dollars), risk (0-10 score), and lead time (days) are comparable. The weights differ per strategy.

### What are the three Pareto strategies?

| Strategy | Cost Weight | Risk Weight | Lead Time Weight | Max Concentration |
|----------|------------|-------------|------------------|-------------------|
| Cost-Optimized | 0.80 | 0.05 | 0.15 | 60% |
| Balanced | 0.35 | 0.30 | 0.35 | 40% |
| Risk-Diversified | 0.05 | 0.60 | 0.35 | 25% |

These are not arbitrary — they represent three real procurement mindsets: minimize spend, balance all factors, or maximize resilience.

### What is TCO (Total Cost of Ownership)?

Base unit price is just the start. Our TCO model adds:

- **Volume discounts** — tier-based pricing from supplier contracts
- **Regional freight** — 2-8% of base cost depending on supplier country (China 8%, USA 2%)
- **Inventory carrying cost** — 20-25% annual rate, scaled by lead time (longer lead = more safety stock)
- **Carbon cost** — shadow price at $50/ton CO2 ($0.05/kg × material carbon footprint)
- **Payment term benefit** — Net 60 saves 1%, Net 45 saves 0.5%, no contract penalizes 0.5%

### How is risk scored?

Six dimensions, weighted and combined into a 0-10 score:

| Dimension | Weight | Source |
|-----------|--------|--------|
| Geopolitical risk | 25% | Supplier country rating |
| Financial stability | 15% | Inverse of stability score |
| Quality performance | 15% | Exponentially weighted recent quality scores |
| Delivery performance | 15% | On-time delivery rate (weighted recent 3 months) |
| Defect rate | 15% | Recent defect rate from performance data |
| Defect history | 15% | Historical defect tracking system score |

Plus a **trend factor** (±0.3-0.5) based on whether quality is improving or degrading over time. Clamped to [0, 10].

### What constraints does the solver enforce?

1. **Demand satisfaction** — allocation fractions must sum to 1.0 per material (you order exactly what you need)
2. **Supplier concentration** — no single supplier exceeds the strategy's max % of total spend
3. **MOQ** — minimum order quantities filter out infeasible suppliers before optimization
4. **Delivery feasibility** — suppliers that can't deliver by the required date are excluded
5. **Excluded suppliers** — risk simulation can exclude specific suppliers (e.g., Hormuz-affected)

### Why not linear programming or mixed-integer?

Our TCO function is nonlinear (volume discounts create step functions, carrying cost is nonlinear in lead time). Risk scoring involves lookups and conditional logic. SLSQP handles this naturally. LP would require linearization that loses fidelity. MIP would be overkill — we don't have binary decisions (we allow split orders).

### What does "10 supplier options excluded" mean?

Before optimization, we filter out supplier-material combinations that are infeasible: below MOQ, can't deliver on time, or excluded by risk scenario. The solver only sees feasible options. "10 excluded" means 10 supplier-material pairs were removed for these reasons.

---

## Demand Forecasting

### What model do you use?

**Amazon Chronos-2** — a 120 million parameter foundation model for time-series forecasting, deployed on SageMaker with a ml.g5.2xlarge GPU instance via JumpStart.

### What makes Chronos-2 different from traditional forecasting?

Traditional forecasting (ARIMA, ETS, Prophet) fits a statistical model per time series. Chronos-2 is a **pretrained transformer** that has learned temporal patterns across millions of time series. It generalizes to new data without per-series training — you give it historical data, it returns predictions. Zero-shot forecasting.

### What are P10, P50, P90?

Probabilistic confidence intervals:

- **P10** (Optimistic) — 10th percentile, demand will be below this 90% of the time
- **P50** (Median) — 50th percentile, most likely demand
- **P90** (Conservative) — 90th percentile, demand will be below this only 10% of the time

For procurement planning, **P90 is recommended** — it's better to have 10% excess inventory than to shut down the production line.

### What data does the forecast use?

Historical demand data for each material — daily order quantities over the past ~2 years (731 days). The model also returns explainability metrics: trend direction, seasonal strength, coefficient of variation, momentum, and data span.

### How does the forecast relate to the BOM quantity?

The BOM (Bill of Materials) says you need 900 batteries for Q2 (500 Urban + 400 Mountain bikes). The AI forecast predicts demand based on historical ordering patterns. The UI uses **the higher of the two** — the production plan is the floor, the forecast may signal higher demand from market trends.

### What is the prediction length?

60 days by default (configurable up to 64). This covers roughly a Q2 production window.

---

## Agent Architecture

### Why three specialist agents instead of one?

- **Fewer tools per agent** = fewer hallucinated tool calls. Each specialist gets only the tools it needs.
- **Tighter system prompts** = more accurate responses. A procurement specialist gives better optimization advice than a generalist.
- **Cheaper to evaluate** = each agent's quality can be measured against its specific domain.

### Why Nova Lite for the orchestrator?

The orchestrator only does intent classification — read the message, return PROCUREMENT / FORECAST / INTELLIGENCE. Nova Lite is fast (~200ms), cheap, and accurate enough for keyword-based routing. The heavy reasoning happens in the specialists (Claude Sonnet 4).

### How does the MCP Gateway work?

The MCP (Model Context Protocol) Gateway exposes Lambda functions as tools. The agent connects to the gateway URL, gets a tool list, and calls tools through it. Every call is authenticated with the user's Cognito JWT. The gateway handles invocation, error handling, and logging.

### What is Mangum?

A Python library that wraps Flask (WSGI) to run inside AWS Lambda. It translates API Gateway events into HTTP requests that Flask understands. This lets the same Flask app run locally (`python -m api.server`) and in Lambda — one codebase, two runtimes.

---

## Enterprise Features

### What does the Guardrail protect against?

Three layers:
- **PII detection** — blocks SSNs and credit cards, anonymizes phone numbers, emails, and names
- **Content safety** — filters violence, hate speech, misconduct, prompt injection attacks
- **Topic filtering** — blocks malicious requests (hacking, malware, illegal content)

All defined as a CDK CloudFormation resource — infrastructure as code.

### What is Cedar and why use it?

Cedar is AWS's policy language (same as Amazon Verified Permissions). We use it for **tool-level RBAC** — not API-level. With agents, the AI decides which tools to call, not the user. So permissions must be enforced where the tools are invoked: the MCP Gateway. Cedar policies evaluate on every tool call.

### How does Memory work?

Three strategies, each solving a different problem:

| Strategy | Type | What it stores | Example |
|----------|------|---------------|---------|
| Semantic | SEMANTIC | Supplier facts and insights | "Shenzhen LiPower has 95% OTD but Hormuz exposure" |
| User Preference | USER_PREFERENCE | Behavioral patterns | "User prefers risk-diversified strategies" |
| Session Summary | SUMMARIZATION | Conversation continuity | Summary of last session's procurement decisions |

All scoped per actor (user), 90-day TTL.

### What are the 9 evaluators?

7 built-in + 2 custom, running at 100% sampling:

**Built-in:** Goal Success Rate, Correctness, Tool Selection Accuracy, Tool Parameter Accuracy, Helpfulness, Faithfulness, Harmfulness

**Custom (LLM-as-Judge):**
- **ProcurementToolAccuracy** — are optimization results valid? Do allocations sum correctly? Constraints respected?
- **ProcurementQuality** — did the agent complete the procurement task? Were recommendations actionable?

---

## Infrastructure

### How many CDK stacks?

14: Identity, Layer, Data, Lambda, Loader, Gateway, Policy, Memory, Evaluator, Guardrail, Observability, API, Frontend, SageMaker.

### Can I deploy to a fresh AWS account?

Yes. `bash scripts/deploy-all.sh` handles everything — creates venvs, builds Lambda layer, deploys CDK stacks, launches SageMaker endpoint, deploys agent runtime, builds and deploys frontend, creates Cognito users. ~25 minutes on a fresh account.

### What does teardown delete?

Everything: AgentCore resources (gateways, targets, runtimes, endpoints, memory, policies, eval configs), Bedrock guardrails, SageMaker endpoints, versioned S3 buckets, orphaned VPC ENIs, all CloudFormation stacks. Handles dependency ordering and retries on failures.

### What's the monthly cost?

| Resource | Cost |
|----------|------|
| Neptune db.t3.medium | ~$73/month |
| NAT Gateway | ~$32/month |
| SageMaker ml.g5.2xlarge | ~$912/month (24/7) |
| Lambda, S3, CloudFront, Cognito | < $5/month |
| **Total** | **~$1,022/month** |

Delete the SageMaker endpoint when not demoing to save ~$912/month.
