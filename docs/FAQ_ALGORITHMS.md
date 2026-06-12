# Algorithms & Domain FAQ — Procurement Optimization & Demand Forecasting

---

## The Procurement Problem

### What problem are we solving?

A manufacturer needs to decide **how much to order from which supplier for each material**. Today this is done in spreadsheets — a buyer picks the cheapest supplier, checks if they can deliver on time, and places the order. This ignores:

- Trade-offs between cost, risk, and lead time
- Volume discounts across suppliers
- Hidden costs (freight, inventory carrying, carbon)
- Geopolitical exposure (what if a trade route closes?)
- Supplier concentration risk (what if your sole source goes down?)

We formulate this as a **constrained multi-objective optimization problem** and solve it mathematically.

### Why is this hard?

Because the objectives conflict. The cheapest supplier might be in a high-risk country with long lead times. The safest option costs more. Spreading orders across many suppliers reduces risk but loses volume discounts. There is no single "best" answer — there's a **Pareto frontier** of trade-offs, and the procurement team needs to see all of them to make an informed decision.

---

## Optimization Algorithm

### What is SLSQP in business terms?

You have 15 suppliers, 18 materials, and three things you care about — cost, risk, and delivery speed. You can't have all three. The cheapest supplier is in a risky country. The safest option costs more. Spreading orders across everyone loses volume discounts.

SLSQP is a mathematical solver that finds the best possible split — how much to order from each supplier — given your priorities. With 41 supplier-material options each taking any value from 0% to 100%, the search space is effectively infinite. But SLSQP doesn't brute-force it — it uses calculus (gradients) to navigate directly to the optimal point in 1-5 steps, solving in under 10 milliseconds. The result is an allocation where you literally cannot improve one thing without making another worse. That's the Pareto frontier.

We run it three times with different priorities: once favoring cost, once balanced, once favoring safety. You get three strategies to choose from — each one is mathematically optimal for its priority. No spreadsheet can do that.

### What is SLSQP technically?

Sequential Least Squares Quadratic Programming. It's a gradient-based solver for constrained nonlinear optimization from scipy. At each iteration, it approximates the problem as a quadratic program, solves it, and steps toward the optimum. It handles both equality constraints (allocations must sum to 100%) and inequality constraints (no supplier exceeds 40% of spend).

### Why SLSQP and not something else?

| Alternative | Why not |
|-------------|---------|
| **Linear Programming** | Our cost function is nonlinear — volume discounts create step functions, carrying cost depends on lead time nonlinearly |
| **Mixed-Integer Programming** | We allow split orders (60% from supplier A, 40% from B). No binary on/off decisions needed |
| **Genetic Algorithms** | Slower convergence, no optimality guarantees. SLSQP converges in 1-5 iterations for our problem size |
| **Reinforcement Learning** | Needs training data we don't have. SLSQP works out of the box on the mathematical formulation |

SLSQP is the right tool: our problem is continuous, smooth, constrained, and small enough (15 suppliers × 18 materials) that it solves in milliseconds.

### How do you handle multiple objectives?

**Weighted sum method.** We combine cost, risk, and lead time into a single scalar objective with different weight vectors:

```
f(x) = w_cost × normalized_cost + w_risk × normalized_risk + w_lead × normalized_lead_time
```

Running the solver three times with different weights traces out the Pareto frontier. This is simpler than epsilon-constraint or evolutionary multi-objective methods, and it produces exactly three actionable strategies — not a cloud of 50 solutions that overwhelm the decision-maker.

### What are the decision variables?

For each supplier-material combination, a fraction between 0 and 1 representing the share of demand allocated to that supplier. If `x[i] = 0.6` for "Battery from Shenzhen LiPower", that means 60% of battery demand goes to LiPower. Fractions per material must sum to 1.0.

### What gets filtered before optimization?

The solver only sees feasible options. Before it runs, we remove:

- Suppliers below **minimum order quantity** for the requested volume
- Suppliers that **can't deliver on time** (lead time exceeds the required-by date)
- Suppliers **excluded by risk simulation** (e.g., Hormuz-affected)

This pre-filtering keeps the solver efficient and avoids infeasible solutions.

---

## Total Cost of Ownership (TCO)

### What is TCO in business terms?

When your buyer says "this supplier is cheapest," they're looking at unit price. But what actually hits your P&L is unit price PLUS shipping from China, PLUS the warehouse space you need because their lead time is 45 days, PLUS the carbon offset your ESG team requires, MINUS the cash flow benefit of paying Net 60 instead of Net 30. That's TCO — what procurement actually costs you, not what the price tag says.

### Why not just use unit price?

Unit price is misleading. A $450 battery from China looks cheaper than a $480 battery from Korea, but after freight (8% vs 7%), longer lead time safety stock, and carbon costs, the total cost difference shrinks or reverses. TCO captures the real cost of procurement.

### What's in the TCO model?

| Component | Data Source | Formula | Example |
|-----------|-------------|---------|---------|
| **Base cost** | `supplier_materials.csv` → `base_price` | unit price × quantity | $450 × 500 = $225,000 |
| **Volume discount** | `volume_tiers.csv` → `min_quantity`, `unit_price` | tier-based lookup | 500 units hits Tier 2: $435/unit |
| **Freight** | `suppliers.csv` → `location` → hardcoded regional rates | base cost × rate (2-8%) | China: 8% = $17,400 |
| **Carrying cost** | `supplier_materials.csv` → `lead_time_days` | (daily demand × safety days × price) × rate/365 | 45-day lead = 31 extra days of buffer |
| **Carbon cost** | `supplier_materials.csv` → `carbon_footprint_kg` | kg × quantity × $0.05 | 1.2 kg × 500 × $0.05 = $30 |
| **Payment terms** | `supplier_contracts.csv` → `payment_terms` | Net 60: +1% benefit, Net 45: +0.5%, no contract: -0.5% penalty | Net 60 saves $2,175 |

**TCO = base + freight + carrying + carbon - payment benefit**

### Why does lead time affect cost?

Longer lead time requires more safety stock (buffer inventory to avoid stockouts while waiting for delivery). More safety stock means more capital tied up in warehouses. Our carrying cost rate is 20-25% annually — a supplier with 45-day lead time costs meaningfully more in carrying than one with 14-day lead time, even at the same unit price.

### How do volume discounts work?

Each supplier-material pair has pricing tiers in the data. For example:

| Tier | Min Qty | Max Qty | Discount | Unit Price |
|------|---------|---------|----------|------------|
| 1 | 100 | 499 | 0% | $480.00 |
| 2 | 500 | 999 | 5% | $456.00 |
| 3 | 1000 | 2499 | 8% | $441.60 |
| 4 | 2500 | — | 12% | $422.40 |

The solver considers these when calculating TCO. This is why consolidated orders to a single supplier can be cheaper — you hit higher volume tiers.

---

## Risk Scoring

### What is risk scoring in business terms?

Every supplier carries risk — political instability in their country, shaky financials, declining quality, late deliveries, manufacturing defects. We score each of these on a 0-10 scale and combine them into a single number. A score of 2 means low risk. A score of 7 means you should have a backup plan.

The critical insight: risk isn't just about the supplier — it's about how much you depend on them. Buying 60% of your batteries from one supplier in a geopolitically risky region is far more dangerous than buying 15% from that same supplier. Our scoring weights risk by spend share — so concentrating your budget amplifies risk, and diversifying reduces it.

### How is supplier risk calculated?

Six dimensions combined into a 0-10 score, each grounded in actual data:

| Dimension | Weight | Data Source | Example |
|-----------|--------|-------------|---------|
| Geopolitical | 25% | `suppliers.csv` → `geopolitical_risk_score` | China: 6.2, USA: 1.0 |
| Financial stability | 15% | `suppliers.csv` → `financial_stability_score` (inverted) | Bosch: 8.0 → risk 2.0 |
| Quality | 15% | `supplier_performance.csv` → `quality_score` (exp. weighted last 3 months) | 5.5, 6.6, 6.3 → weighted 5.9 |
| Delivery | 15% | `supplier_performance.csv` → `on_time_delivery_rate` (exp. weighted) | 84.4% → risk 1.56 |
| Defect rate | 15% | `supplier_performance.csv` → `defect_rate` | 2.69% |
| Defect history | 15% | `defects.csv` → severity, recency, resolution status | CRITICAL + unresolved = high score |

### How does trend detection work?

We use **exponential weighting** on the last 3 months of performance data: 50% weight on the most recent month, 30% on the month before, 20% on the oldest. This makes the score responsive to recent changes.

Additionally, we compare the newest and oldest quality scores. The trend is calculated as `recent - oldest`: a positive trend means quality improved, negative means it declined. If quality declined (trend < -0.5), the trend factor is -0.5. If quality improved (trend > 0.5), the trend factor is +0.3. This factor is added directly to the risk score.

### How does risk affect the optimization?

The risk score is a weighted average across allocated suppliers, weighted by their share of total TCO. A supplier handling 60% of your spend contributes more to portfolio risk than one handling 10%. The Risk-Diversified strategy caps any single supplier at 25% to force diversification.

Additional risk adjustments during optimization:
- **MOQ proximity penalty** (+0.8 risk if order < 1.5× MOQ, +0.3 if order < 2× MOQ — suppliers deprioritize small orders)
- **Capacity concentration** (+0.5 risk if a supplier handles > 800 total units, +0.2 if > 500 units across all materials)

---

## Demand Forecasting

### Why does forecasting matter for procurement?

The biggest waste in manufacturing is ordering the wrong amount. Order too much — you tie up capital in warehouse inventory. Order too little — your production line stops, costing thousands per hour. Traditional forecasting uses last quarter's numbers plus a gut feel buffer. AI forecasting uses 2 years of historical patterns to give you a range: "you'll need between 107 and 264 batteries with 90% confidence." That range directly drives how much safety stock to carry and how aggressively to negotiate with suppliers.

### What is Chronos-2?

A **120 million parameter transformer model** for time-series forecasting, developed by Amazon and deployed on SageMaker via JumpStart. Unlike traditional statistical models (ARIMA, ETS, Prophet) that fit one model per time series, Chronos-2 is **pretrained on millions of time series** and generalizes to new data without per-series training. You provide historical data; it returns probabilistic predictions.

### Why probabilistic forecasting?

A single-point forecast ("you'll need 450 batteries") gives false confidence. In reality, demand is uncertain. Probabilistic forecasting provides a range:

- **P10** = 10th percentile — optimistic, demand is likely higher
- **P50** = 50th percentile — median expectation
- **P90** = 90th percentile — conservative, only 10% chance demand exceeds this

This directly feeds procurement strategy: use **P90 for safety stock planning** (protect against stockouts), **P50 for budgeting** (most likely spend), **P10 for minimum commitment** (floor for supplier negotiations).

### What data does the model use?

Historical daily order quantities per material over approximately 2 years (731 days). The model detects:

- **Trend** — is demand increasing or decreasing?
- **Seasonality** — are there recurring patterns (quarterly, monthly)?
- **Variability** — how much does demand fluctuate (coefficient of variation)?
- **Momentum** — is the recent trend accelerating or decelerating?

These are returned as explainability metrics alongside the forecast.

### Why do forecast quantities differ across materials that should be 1:1?

If every bike needs 1 suspension fork and 1 gear system, shouldn't the forecast be the same for both? No — and that's by design.

Chronos-2 forecasts each material **independently** based on its own historical demand time series. Materials have different ordering patterns because not every order is for a new bike:

- **Maintenance and spare parts** — suspension forks fail more often than gear systems, generating different replacement demand
- **Quality rejects** — some materials have higher defect rates, requiring re-orders
- **Safety stock builds** — procurement teams may have been pre-building inventory for some materials and not others
- **Seasonal patterns** — some components have stronger seasonal demand than others

The alternative approach — forecast at the bike level and multiply through the BOM — would give consistent quantities but would miss these material-specific demand signals. A flat BOM multiplication says "order 500 of everything." The AI says "you actually need 535 wheel sets but only 191 motors based on real consumption patterns."

Both approaches are valid. We chose material-level forecasting because it captures more signal. In production, you could reconcile the two: use BOM-derived quantities as a sanity check against AI forecasts, flagging materials where they diverge significantly.

### How does the forecast connect to the optimizer?

The forecast determines **how much** to order. The optimizer determines **from whom**.

1. Chronos-2 forecasts P90 demand for each material over the next 60 days
2. The UI shows both BOM plan and AI forecast side by side
3. Materials with a procurement gap (forecast > stock on hand) are sent to the optimizer
4. The optimizer allocates those quantities across suppliers, minimizing TCO + risk + lead time

Without forecasting, you use static BOM numbers (900/500/400 for all materials regardless of actual demand). With forecasting, each material gets its own demand signal — the AI might predict 535 wheel sets but only 191 motors, reflecting actual consumption patterns rather than flat BOM multiplication.

---

## Risk Simulation

### Why simulate disruptions?

In 2021 the Suez Canal blockage cost global trade $9.6 billion per day. In 2022 the Ukraine conflict disrupted European energy supply chains overnight. Most procurement teams had no contingency plan because they'd never modeled "what happens if this supplier can't ship?"

Our simulation engine lets you ask that question before it happens. Pick a scenario — Hormuz blockade, Taiwan crisis, US-China tariffs — and see which suppliers are affected, which materials are at risk, and what it costs to switch to alternatives. Then re-optimize with the affected suppliers removed. You get a Plan B with real numbers, not a panic spreadsheet built at 2am during an actual crisis.

### What scenarios are available?

Five geopolitical disruption scenarios:

| Scenario | What it models |
|----------|---------------|
| Strait of Hormuz blockade | Oil/shipping chokepoint — affects Middle East and Asia-routed suppliers |
| Suez Canal disruption | Europe-Asia shipping route — affects European and Asian suppliers |
| Taiwan Strait crisis | Semiconductor and electronics supply — affects Taiwan-based suppliers |
| US-China tariff escalation | Trade war — affects Chinese-manufactured components |
| European port strike | Labor action — affects all European-sourced materials |

### How does simulation work?

Each scenario defines which suppliers are in the "blast radius" based on their geography and trade routes. The system calculates:

- Which materials are affected (and how many alternative suppliers exist)
- Cost impact (price increases from switching to alternatives)
- Lead time impact (alternative suppliers may have longer delivery)
- Specific supplier-level impact details

### Can I re-optimize after a simulation?

Yes. The simulation identifies affected suppliers, and you can feed those as **excluded suppliers** into the optimizer. The solver runs again without them and finds the best allocation from the remaining supply base. This answers: "What's our best option if Hormuz closes?" — with real numbers, not a guess.

---

## Technical Deep Dive: The Math

### SLSQP — Formal Problem Definition

The solver solves the following at each strategy:

```
minimize    f(x) = w₁·C(x)/10⁶ + w₂·R(x)/10 + w₃·L(x)/60

subject to  Σ x[i] = 1.0          for each material (demand satisfaction)
            sup_tco/total_tco ≤ k  for each supplier (concentration limit)
            0 ≤ x[i] ≤ 1          for all i (allocation bounds)
```

Where:
- `x[i]` = fraction of material demand allocated to supplier option i
- `C(x)` = total TCO across all allocations (dollars)
- `R(x)` = spend-weighted portfolio risk score (0-10)
- `L(x)` = maximum lead time across active allocations (days)
- `w₁, w₂, w₃` = strategy-specific weights (sum to 1.0)
- `k` = max supplier concentration (0.25 to 0.60 depending on strategy)

The divisors (10⁶, 10, 60) are **normalization constants** that bring all three objectives into roughly the same [0,1] range so weights are meaningful. Without normalization, cost (hundreds of thousands) would dominate risk (0-10) regardless of weights.

SLSQP approximates the Lagrangian with a quadratic model at each iteration, solves the QP subproblem, and updates the solution. For our problem size (~50 variables, ~20 constraints), it converges in 1-5 iterations — under 10ms.

### TCO — Total Cost of Ownership Model

For each allocation of `q` units from supplier `s` at unit price `p`:

```
TCO(s,q) = base_cost + freight + carrying + carbon - payment_benefit

where:
  base_cost       = p × q
  freight         = base_cost × freight_rate(country)      // 2-8% by region
  carrying        = (q/30 × safety_days × p) × (rate/365)  // annualized holding cost
  safety_days     = max(lead_time - 14, 0)                  // buffer beyond 2-week baseline
  rate            = 0.20 + 0.05 × min(q/500, 1)            // 20-25% annual, scales with volume
  carbon          = carbon_kg × q × $0.05                   // shadow price at $50/ton CO₂
  payment_benefit = base_cost × term_factor                 // Net60: 1% benefit, Net45: 0.5%, none: -0.5% penalty
```

The carrying cost is the key differentiator between suppliers — a 45-day lead time supplier requires 31 extra days of safety stock compared to a 14-day supplier. At 22% annual carrying rate, that's real money.

Volume discounts are applied via tier lookup before TCO calculation. The solver sees the discounted price, which means consolidating volume with one supplier can reduce per-unit cost enough to offset concentration risk.

### Risk Scoring — Multi-Dimensional Composite

Individual supplier risk (0-10):

```
risk(s) = 0.25 × geopolitical(s)
        + 0.15 × (10 - financial_stability(s))
        + 0.15 × (10 - weighted_quality(s))
        + 0.15 × (100 - weighted_otd(s)) / 10
        + 0.15 × weighted_defect_rate(s)
        + 0.15 × defect_history_score(s)
        + trend_factor(s)
```

Where `weighted_quality` uses exponential decay over the last 3 months:

```
weighted_quality = (0.5 × month₁ + 0.3 × month₂ + 0.2 × month₃) / (0.5 + 0.3 + 0.2)
```

This makes the score **recency-sensitive** — a supplier that was great 3 months ago but declined last month gets penalized more than a flat average would show.

Portfolio risk (what appears on the strategy card):

```
R(x) = Σ (tco_i / total_tco) × min(10, risk(supplier_i) + moq_penalty_i + capacity_penalty_i)
```

The spend-weighting means a supplier handling 25% of your budget contributes 5x more to portfolio risk than one handling 5%. This is why the Cost-Optimized strategy (60% concentration allowed) has higher risk — one supplier dominates the portfolio.

### Demand Forecasting — Chronos-2 Architecture

Chronos-2 is a **decoder-only transformer** pretrained on 27 billion time-series observations across diverse domains (energy, retail, transport, finance). Key technical properties:

- **Tokenization**: continuous values are quantized into 4096 bins via learned bin boundaries, converting time-series forecasting into a sequence-to-sequence token prediction problem
- **Zero-shot generalization**: no fine-tuning needed per time series — the pretrained model handles unseen data
- **Probabilistic output**: generates multiple sample paths, from which quantiles (P10, P50, P90) are computed
- **Context window**: up to 2048 time steps of history (we use ~731 days of daily data)
- **Inference**: runs on ml.g5.2xlarge (1 NVIDIA A10G GPU, 24GB VRAM) via SageMaker JumpStart

The model returns daily point predictions at three quantiles. We sum over the 60-day prediction horizon to get total demand per confidence level.

### Neptune Graph Queries — Supplier Network Analysis

The supplier knowledge graph in Neptune models:

```
(Supplier) --[SUPPLIES {lead_time, moq, price, carbon_kg}]--> (Material)
```

33 vertices (15 suppliers + 18 materials) and 41 edges (supply relationships). Graph queries power:

- **Alternative supplier discovery**: `g.V('MAT-BAT-001').in('supplies').out('supplies')` — find suppliers of the same material, then find what else they supply. Two-hop traversal reveals backup options.
- **Single-source risk detection**: `g.V().hasLabel('material').where(in('supplies').count().is(1))` — materials with only one supplier are critical vulnerabilities.
- **Risk correlation**: if two materials share the same supplier in the same country, a geopolitical event affects both simultaneously. Graph traversal detects this faster than relational joins.

Neptune HTTP API with SigV4 authentication is used instead of Gremlin WebSocket — this works natively in Lambda without needing aiohttp in the dependency layer.

### Post-Processing — Solution Cleanup

After SLSQP converges, we apply a cleanup pass:

1. **Zero out tiny allocations** — any allocation below 5% is set to zero (a 3% order isn't practical)
2. **Re-normalize** — remaining allocations are scaled to sum to 1.0 per material
3. **Round to integers** — fractional quantities are rounded to whole units

This sacrifices strict mathematical optimality for **practical feasibility**. A procurement manager can't order 3.7% of their batteries from one supplier — but the cleanup ensures the solution is immediately actionable.

---

## How It All Fits Together

The procurement workflow is a pipeline:

```
Forecast (how much?) → Optimize (from whom?) → Simulate (what if?) → Re-optimize (plan B) → Purchase Requisitions (execute)
```

Each step is mathematically grounded:
- Forecasting uses a pretrained transformer (Chronos-2) for probabilistic demand prediction
- Optimization uses constrained nonlinear programming (SLSQP) with a TCO objective
- Risk scoring uses exponentially weighted multi-dimensional assessment
- Simulation uses graph-based supplier network analysis (Neptune)

The AI agent orchestrates all of these through natural language — a procurement manager can run this entire pipeline in a single conversation.
