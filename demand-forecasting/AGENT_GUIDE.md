# Seasonal Analysis Agent

A Strands-based AI agent for analyzing historical sales and maintenance data to identify seasonal demand patterns for E-bike materials.

## Features

- Load and analyze bike sales history
- Load and analyze maintenance/repair demand
- Explode product-level sales to material-level demand using BOM
- Combine production and maintenance demand
- Perform seasonal analysis by material
- Prepare data for Chronos-2 forecasting

## Setup

### 1. Install Dependencies

```bash
pip install strands-agents strands-agents-tools
```

### 2. Configure Bedrock API Key

The agent uses Amazon Bedrock. Add your Bedrock API key to the `.env` file:

1. Create/edit `.env` file in the `agents/demand-forecasting/` directory
2. Add your Bedrock API key:
   ```
   BEDROCK_API_KEY=your-bedrock-api-key-here
   ```

**Note:** The API key should be in the format provided by AWS Bedrock console.

### 3. Enable Model Access

1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access" in left sidebar
3. Click "Manage model access"
4. Enable "Claude 4 Sonnet" or your preferred model
5. Wait a few minutes for access to propagate

## Usage

### Interactive Mode

```bash
python seasonal_analysis_agent.py
```

Then ask questions like:
- "What are the total bike sales?"
- "Analyze seasonal patterns for MAT-BAT-001"
- "What materials have the highest demand?"
- "Show me maintenance demand by type"
- "Explode bike sales to material demand"

### Programmatic Usage

```python
from seasonal_analysis_agent import agent

# Ask a question
response = agent("What are the total bike sales in the dataset?")
print(response)

# Analyze specific material
response = agent("Analyze seasonal patterns for battery MAT-BAT-001")
print(response)

# Get material demand
response = agent("What is the total material demand from production?")
print(response)
```

## Available Tools

The agent has access to these tools:

1. **load_bike_sales_data** - Load bike sales history with optional date filtering
2. **load_maintenance_data** - Load maintenance demand with optional type filtering
3. **explode_sales_to_materials** - Convert bike sales to material demand using BOM
4. **analyze_seasonal_patterns** - Calculate seasonal statistics for materials
5. **get_material_info** - Get information about materials from catalog

## Data Files

The agent reads from:
- `../../shared/data/bike_sales_history.csv` - Product-level sales (1,782 transactions)
- `../../shared/data/maintenance_demand_history.csv` - Material-level maintenance (1,207 events)
- `../../shared/data/bom.csv` - Bill of Materials (32 entries)
- `../../shared/data/materials.csv` - Material catalog (18 materials)
- `../../shared/data/holiday_calendar.csv` - Holiday reference (14 holidays)

## Example Queries

### Get Sales Summary
```
You: What are the total bike sales?

Agent: Let me load the bike sales data...
[Loads data and provides summary with total transactions, bikes sold, breakdown by model]
```

### Analyze Seasonal Patterns
```
You: Analyze seasonal patterns for MAT-BAT-001

Agent: Let me analyze the seasonal demand for battery MAT-BAT-001...
[Provides seasonal breakdown with demand by season, trends, and insights]
```

### Material Demand Analysis
```
You: What materials have the highest demand from production?

Agent: Let me explode the bike sales to material level...
[Shows top materials needed based on bike sales and BOM]
```

## Troubleshooting

### Error: "The security token included in the request is invalid"
**Solution:** Set AWS credentials (see Setup step 2)

### Error: "Access denied to model"
**Solution:** Enable model access in Bedrock console (see Setup step 3)

### Error: "Module 'strands' not found"
**Solution:** Run `pip install strands-agents strands-agents-tools`

### Error: "File not found"
**Solution:** Make sure you're running from the `agents/demand-forecasting/` directory

## Next Steps

After seasonal analysis, the output can be used for:
1. User Story 3: Chronos-2 forecasting
2. User Story 4: Forecast accuracy tracking
3. User Story 5: Demand visualization

## Architecture

```
User Query
    ↓
Strands Agent (Bedrock Claude 4 Sonnet)
    ↓
Tool Selection & Execution
    ├── load_bike_sales_data()
    ├── load_maintenance_data()
    ├── explode_sales_to_materials()
    ├── analyze_seasonal_patterns()
    └── get_material_info()
    ↓
Data Processing & Analysis
    ↓
Natural Language Response
```

## License

Part of the E-bike Demand Forecasting multi-agent system.
