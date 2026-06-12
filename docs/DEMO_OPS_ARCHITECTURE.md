# Operations & Architecture Deep Dive — Demo Talk Track

**Target: 5-7 minutes**
**Audience: Technical evaluators who want to understand WHY, not just WHAT**

---

## Opening (15 seconds)

> "You've seen what the system does — forecast, optimize, simulate, chat. Now let me show you how it's built, and more importantly, why we made the choices we did."

---

## 1. The Agent Architecture (90 seconds)

*Show Architecture page or diagram*

> "We have three specialist agents — Procurement, Forecast, and Intelligence — each running Claude Sonnet 4. They're coordinated by an orchestrator on Amazon Nova Lite.
>
> Why not one big agent with all the tools? Because specialist agents have tighter system prompts, make fewer tool selection errors, and are cheaper to evaluate. The orchestrator is just a classifier — it reads the user's message, picks the right specialist, and routes. Nova Lite is perfect for that: fast, cheap, accurate for intent classification. The heavy reasoning happens in the specialist.
>
> Why three specialists and not five or ten? Because we have three distinct tool domains. The Procurement Agent handles optimization and purchase requisitions. The Forecast Agent handles Chronos-2 predictions. The Intelligence Agent handles risk simulation and supplier performance. Each agent gets only the tools it needs — fewer tools means fewer hallucinated tool calls."

---

## 2. MCP Gateway — Why Not Direct Lambda Invocation? (60 seconds)

*Show Gateway panel in Operations*

> "Every tool call flows through an MCP Gateway. Four Lambda tools behind one gateway endpoint, authenticated with JWT.
>
> Why not just give the agent direct Lambda invoke permissions? Three reasons.
>
> First, **security**. The gateway validates the user's Cognito JWT on every tool call. The agent never holds IAM credentials. If someone compromises the agent runtime, they can't call tools without a valid user token. That's zero-trust at the tool layer.
>
> Second, **observability**. Every tool call through the gateway is logged with the user identity, the tool name, the parameters, and the response. We get a complete audit trail without instrumenting each Lambda individually.
>
> Third, **policy enforcement**. Cedar policies evaluate at the gateway level — which means we can control who can call which tools without changing any agent code. The agent doesn't even know policies exist. It just gets a permission denied and adapts."

---

## 3. Cedar Policies — Why RBAC at the Tool Layer? (60 seconds)

*Show Cedar Policies panel*

> "Traditional RBAC puts permissions at the API layer — you either can or can't hit an endpoint. But with agents, the user doesn't choose which tools to call. The AI does. So you need RBAC at the tool layer, not the API layer.
>
> That's what Cedar gives us. Cedar is AWS's policy language — the same one that powers Amazon Verified Permissions. We define policies like: 'An Analyst can call query_supplier_data but not optimize_suppliers.' The policy engine evaluates on every tool call through the gateway.
>
> Here's the interesting part: when the agent gets a policy denial, it doesn't just fail. The agent sees 'access denied' and adapts. If an Analyst asks to optimize, the Procurement Agent can't call the optimization tool — so instead it uses the query tool to pull supplier data and gives the analyst what information it can. The agent degrades gracefully within the permission boundary.
>
> That's something you can't do with API-level RBAC. The intelligence is in the agent's ability to work within constraints."

---

## 4. Guardrails — Defense in Depth (45 seconds)

*Switch to Agent Chat, type an SSN*

> "Guardrails are a Bedrock-native defense layer. We have three types of protection running simultaneously.
>
> PII detection — SSNs and credit card numbers are blocked outright. Phone numbers and emails are anonymized in-flight. This runs before the model even sees the input.
>
> Content safety — filters for violence, hate speech, misconduct, and prompt injection attacks. The prompt attack filter catches jailbreak attempts before they reach the agent.
>
> And this is all defined in CDK — it's a CloudFormation resource, not a manual configuration. When we tear down and redeploy, guardrails come back exactly as defined. Infrastructure as code, not infrastructure as hope."

*Show the SSN block*

> "Watch — 'My SSN is 123-45-6789.' Blocked instantly. The user gets a clear message, the agent never processes it, and we have an audit log."

---

## 5. Memory — Why Three Strategies? (45 seconds)

*Show Memory Explorer*

> "AgentCore Memory gives us long-term persistence across sessions. We run three memory strategies, each solving a different problem.
>
> **Semantic memory** extracts facts — 'Shenzhen LiPower has a 95% on-time delivery rate but is exposed to Hormuz risk.' These persist so the agent builds institutional knowledge about our supply chain over time.
>
> **User Preference memory** tracks behavior — 'This user always prefers risk-diversified strategies.' Next time they ask to optimize, the agent leads with their preferred approach. No re-explaining.
>
> **Session Summarization** creates continuity — if a conversation runs long, the summary carries context to the next session. The user doesn't start from zero.
>
> All three are scoped per actor with 90-day TTL. Different users build different memory profiles. The analyst sees different recalled insights than the procurement manager."

---

## 6. Evaluators — Continuous Quality at 100% Sampling (45 seconds)

*Show Evaluations panel*

> "We run nine evaluators on every single agent conversation — 100% sampling, not a random subset.
>
> Seven are built-in: Goal Success Rate, Correctness, Tool Selection Accuracy, Tool Parameter Accuracy, Helpfulness, Faithfulness, and Harmfulness. These give us a baseline quality signal across all conversations.
>
> Two are custom LLM-as-Judge evaluators we defined in CDK. **ProcurementToolAccuracy** evaluates at the tool-call level — did the optimizer return valid Pareto solutions? Do allocations sum to the requested quantities? Are constraints respected? **ProcurementQuality** evaluates at the session level — did the agent complete the procurement task? Were recommendations actionable?
>
> This isn't post-hoc testing. It's continuous production monitoring. Every conversation gets scored. If quality drops, we see it in real time."

---

## 7. Infrastructure as Code — One Command (60 seconds)

*Show terminal or architecture diagram*

> "The entire solution deploys with `bash scripts/deploy-all.sh`. 14 CDK stacks, one command, about 25 minutes on a fresh account.
>
> Let me walk the stack dependency chain. Identity creates Cognito. Layer builds the shared Lambda dependencies. Data creates Neptune and S3. Lambda deploys the tool functions into the VPC. Loader populates Neptune from CSV using a custom resource. Gateway, Policy, Memory, Evaluator, and Guardrail create the AgentCore infrastructure. API deploys the Flask Lambda with cross-stack references to the Gateway, Memory, and Policy IDs — those are CDK Fn::ImportValue, not hardcoded strings. Frontend builds the React app with the right Cognito and API URLs baked in, deploys to S3 behind CloudFront.
>
> Then a Python script deploys the agent runtime to AgentCore with JWT auth configuration. And a slim post-deploy script handles the five things that can't be CDK — the runtime ID on the API Lambda, the runtime role permissions, the eval config, Cedar policies, and pushing the guardrail ID to the running agent.
>
> Teardown is equally automated. `bash scripts/teardown.sh` deletes AgentCore resources in dependency order, empties versioned S3 buckets, cleans orphaned VPC ENIs, removes all CloudFormation stacks, and retries on failures. We've torn down and redeployed this across two AWS accounts to validate repeatability."

---

## Close (15 seconds)

> "The technical choices all serve the same goal: an agent system that's secure, observable, and reproducible. MCP Gateway for zero-trust tool access. Cedar for tool-level RBAC. Guardrails for PII and content safety. Nine evaluators for continuous quality. Three memory strategies for institutional learning. And 14 CDK stacks so the whole thing deploys from a single command.
>
> That's the operations and architecture of the Predictive Supply Chain Orchestrator."
