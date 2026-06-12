# Predictive Supply Chain Orchestrator — Demo Talk Track

**Target: 7-10 minutes recorded demo**
**URLs:**
- Frontend: https://d3f3da4hp0y229.cloudfront.net
- Login: demo@voltcycle.com / VoltCycle2026!

---

## PART 1: The Problem & Opportunity (60 seconds)

> "Procurement teams spend 60-70% of their time gathering data and comparing suppliers in spreadsheets. We automated that entire workflow with a multi-agent AI system.
>
> VoltCycle manufactures urban e-bikes. We source 18 materials from 15 suppliers across 10 countries — batteries from China and Korea, motors from Germany and Taiwan, frames from Taiwan and the UK.
>
> Today, a buyer gets a demand number, calls three suppliers, picks the cheapest one. No one models the trade-off between cost, risk, and lead time. No one asks: what happens if the Strait of Hormuz closes tomorrow?
>
> We built an AI-powered procurement orchestrator that replaces that workflow end-to-end."

---

## PART 2: Functional Demo (4 minutes)

### 2a. Demand Forecasting (45 sec)

*Navigate to Demand Forecasting page*

> "Step one in any procurement decision is knowing how much you need. We deploy a Chronos-2 model — 120 million parameters — on SageMaker with a GPU instance. It generates probabilistic demand forecasts with three confidence intervals."

*Click "Run Forecast" on a battery material*

> "P10 is optimistic, P50 is the median, P90 is conservative. For procurement planning, you want P90 — better to have too much than shut down the production line. You can see the model also returns explainability metrics: trend direction, seasonal strength, coefficient of variation."

*Select P90 scenario*

> "I'll take the P90 forecast forward into optimization."

### 2b. Multi-Objective Optimization (60 sec)

*Navigate to Optimize page, run optimization*

> "This is the core of the solution. We run a scipy SLSQP solver — Sequential Least Squares Quadratic Programming — with a weighted multi-objective function that minimizes cost, risk, and lead time simultaneously.
>
> The solver generates three Pareto-optimal strategies. Cost-Optimized accepts higher supplier concentration — up to 60% from a single supplier — to get the lowest price. Risk-Diversified caps any single supplier at 25% of total spend. Balanced splits the difference.
>
> The cost model isn't just unit price. It's total cost of ownership — base cost plus regional freight rates, inventory carrying cost based on lead time, carbon cost at $50 per ton, minus payment term benefits from contracted suppliers. Volume discounts apply automatically from the tier tables."

*Click on Balanced strategy to expand*

> "Each strategy shows every allocation — which supplier gets which material, the quantity, unit price, TCO breakdown. The solver excluded 10 supplier options that couldn't meet MOQ or delivery constraints. 15 contracted suppliers were available with negotiated terms."

### 2c. Risk Simulation (45 sec)

*Navigate to Risk Simulation, select Strait of Hormuz*

> "Now the interesting question: what if something goes wrong? We model five geopolitical scenarios. Let me simulate a Strait of Hormuz blockade.
>
> The system identifies 5 affected suppliers in the blast radius, calculates cost impact and lead time increases, and shows which materials are at risk. The recommendation section suggests alternative suppliers from the Neptune graph database — these are suppliers connected to the same materials through different trade routes.
>
> From here, I can re-optimize with the affected suppliers excluded. The solver runs again with those suppliers removed from the feasible set and finds the best alternative allocation."

### 2d. Agent Chat — The Full Chain (90 sec)

*Navigate to Agent Chat*

> "Everything I just showed you through the UI — a user can do through natural language with our multi-agent orchestrator.
>
> The architecture is three specialist agents — Procurement, Forecast, and Intelligence — coordinated by an orchestrator running on Amazon Nova Lite that classifies intent and routes to the right specialist. All three specialists run Claude Sonnet 4 and share the same MCP Gateway tools."

*Type: "Forecast demand for batteries for Q3"*

> "Watch the orchestrator route this to the Forecast Agent. It calls the same SageMaker endpoint through the MCP Gateway."

*After response, type: "Now optimize for 500 e-bikes using P90"*

> "This routes to the Procurement Agent. Same SLSQP solver, same TCO model — but now through natural language."

*Type: "What if there's a Strait of Hormuz blockade?"*

> "Routed to the Intelligence Agent. Risk simulation, affected suppliers, recommendations — all in one conversation. The agent has memory. It remembers that I prefer risk-diversified strategies from my last session and leads with that recommendation."

---

## PART 3: Operational / Enterprise Features (2.5 minutes)

*Navigate to Operations tab*

### 3a. MCP Gateway (30 sec)

> "The MCP Gateway is the secure tool layer. It exposes four Lambda tools — optimize_suppliers, query_supplier_data, explain_solution, create_purchase_requisitions — through MCP protocol with JWT authentication. Every tool call goes through the gateway, authenticated with the user's Cognito token. No IAM keys in the agent."

### 3b. Guardrails (30 sec)

*Go back to Agent Chat*

> "Guardrails are enforced at the Bedrock level. Watch what happens if I type a social security number."

*Type: "My SSN is 123-45-6789, please optimize"*

> "Blocked instantly. PII detection — SSNs and credit cards are blocked, phone numbers and emails are anonymized. Content safety filters catch violence, hate speech, and prompt injection attempts. This is a CDK-managed Bedrock Guardrail, deployed as infrastructure."

### 3c. Cedar Policies (30 sec)

> "Role-based access control through Cedar policies on the AgentCore PolicyEngine. We have three personas: Admin, Analyst, and Procurement Manager. Policies evaluate on every tool call through the gateway."

*Mention or show: "If I log in as an Analyst and try to optimize, the policy engine blocks the optimization tool but allows data queries. The agent adapts — instead of failing, it uses the permitted query tools to give the analyst what information it can."*

### 3d. Evaluators (30 sec)

*Show Evaluations panel*

> "Nine online evaluators run at 100% sampling on every agent conversation. Seven are built-in — Goal Success Rate, Correctness, Tool Selection Accuracy, Tool Parameter Accuracy, Helpfulness, Faithfulness, Harmfulness. Two are custom LLM-as-Judge evaluators we defined in CDK — one evaluates tool call accuracy for procurement operations, the other evaluates overall session quality on a 5-point scale."

### 3e. Memory (30 sec)

*Show Memory Explorer*

> "AgentCore Memory with three strategies. Semantic memory extracts supplier insights — facts about suppliers that persist across sessions. User Preference memory tracks what strategies a user favors. Session Summarization creates continuity across conversations. All scoped per actor with 90-day TTL."

---

## PART 4: Architecture and IaC (1.5 minutes)

*Navigate to Architecture page*

> "The entire solution deploys with a single command: `bash scripts/deploy-all.sh`. 14 CDK stacks. No manual steps except one interactive password prompt for demo users.
>
> Let me walk the data path. A user request hits CloudFront, authenticates through Cognito, hits API Gateway with a JWT, which invokes a Flask Lambda in a VPC. That Lambda talks to Neptune for graph queries, SageMaker for forecasts, and scipy for optimization.
>
> For agent chat, the frontend calls AgentCore Runtime directly with the Cognito JWT. The orchestrator classifies intent, delegates to a specialist agent, which calls tools through the MCP Gateway — same Lambda functions, same data.
>
> Neptune is our supplier knowledge graph — 33 nodes, 41 edges. Suppliers, materials, supply relationships with attributes like lead time, MOQ, pricing tiers. Graph traversal finds alternative suppliers, detects single-source risk, maps trade route dependencies.
>
> The SageMaker endpoint runs Chronos-2 on a g5.2xlarge GPU — a 120 million parameter foundation model for time-series forecasting deployed through JumpStart.
>
> Teardown is equally automated: `bash scripts/teardown.sh` deletes everything — AgentCore agents, SageMaker endpoints, CloudFormation stacks, S3 buckets, orphaned ENIs — in the correct dependency order."

---

## PART 5: Close (30 seconds)

> "The $13 trillion procurement industry loses billions annually to manual processes, forecast errors, and unmodeled risk. We showed how a multi-agent AI orchestrator — built entirely on AWS — can forecast demand with Chronos-2, optimize supplier allocation across cost, risk, and lead time with SLSQP, simulate geopolitical disruptions against a Neptune knowledge graph, and generate purchase requisitions — all through natural language.
>
> The result: three Pareto strategies from $597K to $802K, risk scores from 3.2 to 1.7, and zero spreadsheets. Secured with Bedrock Guardrails, Cedar RBAC policies, and 9 continuous evaluators. Deployed as 14 CDK stacks with a single command.
>
> If just 1% of the $13 trillion in global procurement adopted AI-driven multi-objective optimization, that's $6.5-13 billion in annual savings. This is what that looks like.
>
> This is the Predictive Supply Chain Orchestrator."

---

## Industry Stats (use as needed)

| Stat | Source |
|------|--------|
| Global procurement: **$13 trillion** function | Deloitte CPO Survey 2024 |
| AI-driven procurement reduces sourcing costs by **5-10%** | McKinsey 2024 |
| AI can cut supply chain disruptions by **up to 50%** | McKinsey 2023 |
| **73%** of supply chain leaders investing in AI for demand planning by 2027 | Gartner 2024 |
| Fewer than **10%** have deployed AI beyond pilots | Gartner 2024 |
| Manufacturers lose **2-4% of revenue** annually to demand forecast errors | IBF (Institute of Business Forecasting) |
| Suez Canal blockage (2021): **$9.6 billion/day** in global trade costs | Lloyd's List |
| Procurement teams spend **60-70%** of time on manual data gathering | Hackett Group |
| **$4 trillion** in global goods faced supply chain disruptions in 2023 | WTO |
| Average company carries **15-25%** of inventory value as holding cost annually | APICS/ASCM |

**One-liner business case:**
> "Procurement teams spend 60-70% of their time gathering data and comparing suppliers in spreadsheets. We automated that entire workflow with a multi-agent AI system."

## Key Numbers to Mention

| Metric | Value |
|--------|-------|
| Cost-Optimized | ~$597K |
| Balanced | ~$669K |
| Risk-Diversified | ~$802K |
| Savings (Cost vs Risk) | **~26%** (real solver output) |
| Materials | 18 |
| Suppliers | 15 across 10 countries |
| CDK stacks | 14 |
| Agent evaluators | 9 (7 built-in + 2 custom) |
| Memory strategies | 3 (semantic, preference, summarization) |
| Risk scenarios | 5 geopolitical |
| Forecast model | Chronos-2, 120M params, GPU |
| Optimization solver | scipy SLSQP, 3 Pareto strategies |
| Deploy command | `bash scripts/deploy-all.sh` (~25 min) |
| Teardown command | `bash scripts/teardown.sh` (~15 min) |

## Demo Tips

- **Pre-warm the Lambda** before recording — hit the health endpoint once so there's no cold start
- **Pre-warm the agent** — send one message so the container is hot
- **Use the Balanced strategy** for most discussions — it's the most interesting to explain
- **Show the SSN guardrail block** — it's the most visually dramatic enterprise feature
- **Keep the agent chat to 2-3 turns max** — long responses eat clock time
- **Record at 1080p** with browser at 90% zoom for readability
