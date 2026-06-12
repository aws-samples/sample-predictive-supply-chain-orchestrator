# Graph Database Strategy - Neptune for Supply Chain

## Current State: NOT IMPLEMENTED

The demo currently uses flat CSV data. Neptune graph database is **mentioned in architecture** but not implemented.

## Why Graph DB for Supply Chain?

### Graph Model

```
(Supplier)-[:SUPPLIES]->(Material)-[:USED_IN]->(Product)
(Supplier)-[:LOCATED_IN]->(Country)-[:HAS_RISK]->(GeopoliticalRisk)
(Supplier)-[:CERTIFIED_BY]->(Certification)
(Supplier)-[:COMPETES_WITH]->(Supplier)
(Material)-[:ALTERNATIVE_TO]->(Material)
(Supplier)-[:CONTRACTS_WITH]->(Contract)-[:COVERS]->(Material)
```

### Queries That Are HARD Without Graph DB

#### 1. Multi-Hop Alternative Supplier Discovery
**Question**: "If BatteryTech (China) becomes unavailable, what are ALL alternative paths to get batteries?"

**Graph Query (Gremlin)**:
```gremlin
g.V().has('supplier', 'id', 'SUP-001')
  .out('supplies').as('material')
  .in('supplies').where(neq('SUP-001'))
  .dedup()
  .path()
```

**Why Hard in SQL**: Requires recursive CTEs, multiple self-joins, complex logic

#### 2. Supply Chain Risk Propagation
**Question**: "If Taiwan has geopolitical issues, which products are affected and what's the cascading impact?"

**Graph Query**:
```gremlin
g.V().has('country', 'name', 'Taiwan')
  .in('located_in').as('affected_suppliers')
  .out('supplies').as('affected_materials')
  .out('used_in').as('affected_products')
  .path()
```

**Why Hard in SQL**: 3-4 table joins, filtering, grouping - slow and complex

#### 3. Supplier Dependency Clustering
**Question**: "Show me suppliers that share the same sub-suppliers (hidden dependencies)"

**Graph Query**:
```gremlin
g.V().hasLabel('supplier')
  .out('sources_from').as('subsupplier')
  .in('sources_from').where(neq('start'))
  .groupCount()
```

**Why Hard in SQL**: Self-referential joins, recursive relationships

#### 4. Shortest Path to Alternative Material
**Question**: "What's the fastest way to switch from Material A to Material B through supplier relationships?"

**Graph Query**:
```gremlin
g.V().has('material', 'id', 'MAT-BAT-001')
  .repeat(both('alternative_to', 'compatible_with'))
  .until(has('material', 'id', 'MAT-BAT-002'))
  .path()
  .limit(1)
```

**Why Hard in SQL**: Pathfinding algorithms not native to SQL

#### 5. Circular Dependency Detection
**Question**: "Are there any circular dependencies in our supply chain?"

**Graph Query**:
```gremlin
g.V().hasLabel('supplier')
  .repeat(out('sources_from'))
  .emit(cyclicPath())
  .path()
```

**Why Hard in SQL**: Detecting cycles requires complex recursive logic

## Implementation Plan

### Phase 1: Data Model (Neptune)

**Vertices (Nodes)**:
- Supplier (id, name, rating, location, financialStability, geopoliticalRisk)
- Material (id, name, category, criticalityLevel)
- Product (id, name, type)
- Country (name, geopoliticalRiskScore, tradeAgreements)
- Certification (type, issuingBody, validUntil)
- Contract (id, type, startDate, endDate, value)

**Edges (Relationships)**:
- SUPPLIES (Supplier → Material): basePrice, leadTime, moq, qualityScore
- USED_IN (Material → Product): quantity, assemblySequence
- LOCATED_IN (Supplier → Country)
- CERTIFIED_BY (Supplier → Certification)
- ALTERNATIVE_TO (Material → Material): compatibilityScore
- COMPETES_WITH (Supplier → Supplier): overlapPercentage
- SOURCES_FROM (Supplier → Supplier): for sub-tier suppliers
- CONTRACTS_WITH (Supplier → Contract)
- COVERS (Contract → Material)

### Phase 2: Agent Tools Using Neptune

**Tool 1: find_alternative_suppliers**
```python
def find_alternative_suppliers(material_id: str, max_hops: int = 2) -> List[Dict]:
    """
    Find alternative suppliers through graph traversal.
    Includes direct alternatives and 2nd-tier options.
    """
    query = """
    g.V().has('material', 'id', material_id)
     .in('supplies').as('primary')
     .out('supplies').where(neq('primary'))
     .dedup()
     .valueMap()
    """
    return neptune_client.submit(query, {"material_id": material_id})
```

**Tool 2: assess_supply_chain_risk**
```python
def assess_supply_chain_risk(product_id: str) -> Dict:
    """
    Calculate risk propagation through supply chain graph.
    Returns risk score and vulnerable paths.
    """
    query = """
    g.V().has('product', 'id', product_id)
     .in('used_in').as('materials')
     .in('supplies').as('suppliers')
     .out('located_in').as('countries')
     .select('materials', 'suppliers', 'countries')
     .by(valueMap())
    """
    return analyze_risk_paths(neptune_client.submit(query))
```

**Tool 3: find_hidden_dependencies**
```python
def find_hidden_dependencies(supplier_id: str) -> List[Dict]:
    """
    Discover suppliers that share sub-suppliers (hidden risk).
    """
    query = """
    g.V().has('supplier', 'id', supplier_id)
     .out('sources_from').as('subsupplier')
     .in('sources_from').where(neq(supplier_id))
     .path()
    """
    return neptune_client.submit(query)
```

### Phase 3: UI Enhancements

**Network Graph Component** (already exists, enhance with Neptune data):
- Show real-time graph from Neptune
- Click to expand sub-suppliers
- Highlight risk paths in red
- Show alternative paths in green

**New: Supply Chain Explorer**:
- Interactive graph visualization
- "What-if" scenario: "Remove this supplier, show alternatives"
- Risk propagation heatmap
- Dependency depth visualization

## Demo Talking Points

**Current (CSV-based)**:
"We're analyzing 15 suppliers and 16 materials..."

**With Neptune**:
"Behind the scenes, we're using Amazon Neptune graph database to model the entire supply chain network. This lets us answer questions like 'If this supplier fails, what are ALL the alternative paths?' or 'Show me hidden dependencies where multiple suppliers share the same sub-tier supplier.' These queries are nearly impossible with traditional SQL."

## Cost Estimate

- Neptune db.r5.large: ~$0.35/hour = $252/month
- Storage: 10GB = $1/month
- **Total**: ~$253/month for graph capabilities

## Implementation Effort

- Data modeling: 2 days
- ETL pipeline (CSV → Neptune): 1 day
- Agent tools: 2 days
- UI updates: 1 day
- **Total**: ~1 week

## Value Proposition

**Without Graph DB**: "We optimize based on current supplier relationships"

**With Graph DB**: "We optimize while understanding the ENTIRE supply chain network - including hidden dependencies, alternative paths, and cascading risks that traditional databases can't reveal"

This is a key differentiator for enterprise customers with complex, multi-tier supply chains.
