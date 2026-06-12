"""
Chronos-2 Forecasting Agent - User Story 2: Chronos-2 Forecasting Engine

This agent uses Amazon Chronos-2 for time series forecasting of E-bike component demand.
It generates probabilistic forecasts with confidence intervals for material-level demand.
"""

import os
import sys
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

# Data paths — forecasting CSVs live in demand-forecasting/data/,
# while bom.csv and materials.csv live in the repo root data/ folder.
FORECAST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
PROCUREMENT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data')
DATA_DIR = FORECAST_DATA_DIR  # default for backward compat
BIKE_SALES_FILE = os.path.join(FORECAST_DATA_DIR, 'bike_sales_history.csv')
MAINTENANCE_FILE = os.path.join(FORECAST_DATA_DIR, 'maintenance_demand_history.csv')
BOM_FILE = os.path.join(PROCUREMENT_DATA_DIR, 'bom.csv')
MATERIALS_FILE = os.path.join(PROCUREMENT_DATA_DIR, 'materials.csv')

# Chronos-2 pipeline (lazy loaded)
chronos_pipeline = None
CHRONOS_AVAILABLE = False

def get_chronos_pipeline():
    """Lazy load Chronos-2 pipeline to avoid loading on import."""
    global chronos_pipeline, CHRONOS_AVAILABLE
    if chronos_pipeline is None:
        try:
            from chronos import Chronos2Pipeline
            print("Loading Chronos-2 model... (this may take a minute)")
            chronos_pipeline = Chronos2Pipeline.from_pretrained(
                "amazon/chronos-2",
                device_map="cpu"  # Use CPU for local development
            )
            CHRONOS_AVAILABLE = True
            print("✅ Chronos-2 model loaded successfully")
        except ImportError:
            print("⚠️  Chronos-2 not installed - using mock forecasts for testing")
            print("   See CHRONOS_SETUP.md for installation instructions")
            CHRONOS_AVAILABLE = False
            chronos_pipeline = None
    return chronos_pipeline

def generate_mock_forecast(context_df: pd.DataFrame, prediction_length: int, quantile_levels: List[float]) -> pd.DataFrame:
    """Generate mock forecast data for testing when Chronos-2 is not available."""
    # Calculate simple moving average from historical data
    avg_demand = context_df['target'].mean()
    std_demand = context_df['target'].std()
    
    # Generate future dates starting from today
    from datetime import date as _date
    today = pd.Timestamp(_date.today())
    future_dates = pd.date_range(start=today, periods=prediction_length, freq='D')
    
    # Generate mock predictions with some variation
    predictions = []
    for i, date in enumerate(future_dates):
        # Add slight trend and seasonality
        trend = i * 0.1
        seasonal = np.sin(i / 7 * 2 * np.pi) * std_demand * 0.3
        base_value = max(0, avg_demand + trend + seasonal + np.random.normal(0, std_demand * 0.1))
        
        pred_row = {
            'timestamp': date,
            'id': context_df['id'].iloc[0]
        }
        
        for q in quantile_levels:
            if q == 0.1:
                pred_row[str(q)] = max(0, base_value * 0.7)
            elif q == 0.5:
                pred_row[str(q)] = base_value
            elif q == 0.9:
                pred_row[str(q)] = base_value * 1.3
        
        predictions.append(pred_row)
    
    return pd.DataFrame(predictions)

# Helper functions
def load_csv(filepath: str) -> List[Dict[str, str]]:
    """Load CSV file and return list of dictionaries."""
    with open(filepath, 'r', encoding="utf-8") as f:
        return list(csv.DictReader(f))

def prepare_material_timeseries(material_id: str, product_id: str = None) -> pd.DataFrame:
    """
    Prepare time series data for a specific material by combining sales and maintenance demand.
    Returns a DataFrame with daily demand aggregated from both sources.
    If product_id is provided, only includes sales from that specific product.
    If product_id is None or 'ALL', includes sales from all products.
    """
    # Load data
    sales_data = load_csv(BIKE_SALES_FILE)
    maint_data = load_csv(MAINTENANCE_FILE)
    bom_data = load_csv(BOM_FILE)
    
    # Create BOM lookup
    bom_lookup = defaultdict(list)
    for bom_entry in bom_data:
        bom_lookup[bom_entry['product_id']].append({
            'material_id': bom_entry['material_id'],
            'quantity_required': float(bom_entry['quantity_required'])
        })
    
    # Explode sales to material demand by date
    material_demand_by_date = defaultdict(int)
    
    for sale in sales_data:
        # Filter by product if specified
        if product_id and product_id != 'ALL' and sale['product_id'] != product_id:
            continue
        date = sale['timestamp'].split()[0]
        sale_product_id = sale['product_id']
        bikes_sold = int(sale['quantity_sold'])
        
        for bom_item in bom_lookup[sale_product_id]:
            if bom_item['material_id'] == material_id:
                qty = int(bikes_sold * bom_item['quantity_required'])
                material_demand_by_date[date] += qty
    
    # Add maintenance demand
    for maint in maint_data:
        if maint['material_id'] == material_id:
            date = maint['timestamp'].split()[0]
            qty = int(maint['quantity'])
            material_demand_by_date[date] += qty
    
    # Convert to DataFrame
    if not material_demand_by_date:
        return pd.DataFrame(columns=['timestamp', 'target'])
    
    df = pd.DataFrame([
        {'timestamp': date, 'target': demand}
        for date, demand in sorted(material_demand_by_date.items())
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Fill missing dates with 0 demand
    date_range = pd.date_range(start=df['timestamp'].min(), end=df['timestamp'].max(), freq='D')
    df = df.set_index('timestamp').reindex(date_range, fill_value=0).reset_index()
    df.columns = ['timestamp', 'target']
    
    return df

# Tool definitions
@tool
def list_available_materials() -> str:
    """List all materials available for forecasting.
    
    Returns:
        JSON string with material IDs, names, and categories
    """
    try:
        materials_data = load_csv(MATERIALS_FILE)
        result = {
            'total_materials': len(materials_data),
            'materials': [
                {
                    'material_id': m['material_id'],
                    'name': m['name'],
                    'category': m['category']
                }
                for m in materials_data
            ]
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error listing materials: {str(e)}"

@tool
def generate_forecast(
    material_id: str,
    prediction_length: int = 30,
    include_confidence_intervals: bool = True
) -> str:
    """Generate demand forecast for a specific material using Chronos-2.
    
    Args:
        material_id: Material ID to forecast (e.g., MAT-BAT-001)
        prediction_length: Number of days to forecast (default: 30, max: 90)
        include_confidence_intervals: Whether to include 10th and 90th percentile forecasts
    
    Returns:
        JSON string with forecast results including dates, predicted demand, and confidence intervals
    """
    try:
        # Validate inputs
        if prediction_length > 90:
            return json.dumps({
                "error": "prediction_length cannot exceed 90 days",
                "status": "error"
            })
        
        # Prepare historical data
        print(f"📊 Preparing time series data for {material_id}...")
        context_df = prepare_material_timeseries(material_id)
        
        if context_df.empty:
            return json.dumps({
                "error": f"No historical data found for material {material_id}",
                "status": "error"
            })
        
        # Add ID column for Chronos-2
        context_df['id'] = material_id
        
        # Load Chronos-2 pipeline
        pipeline = get_chronos_pipeline()
        
        # Generate forecast
        print(f"🔮 Generating {prediction_length}-day forecast...")
        quantile_levels = [0.1, 0.5, 0.9] if include_confidence_intervals else [0.5]
        
        if CHRONOS_AVAILABLE and pipeline is not None:
            pred_df = pipeline.predict_df(
                context_df,
                prediction_length=prediction_length,
                quantile_levels=quantile_levels,
                id_column="id",
                timestamp_column="timestamp",
                target="target"
            )
        else:
            # Use mock forecast for testing
            pred_df = generate_mock_forecast(context_df, prediction_length, quantile_levels)
        
        # Format results
        forecast_data = []
        for _, row in pred_df.iterrows():
            forecast_point = {
                'date': row['timestamp'].strftime('%Y-%m-%d'),
                'predicted_demand': round(row['0.5'], 2)
            }
            if include_confidence_intervals:
                forecast_point['lower_bound_10th'] = round(row['0.1'], 2)
                forecast_point['upper_bound_90th'] = round(row['0.9'], 2)
            forecast_data.append(forecast_point)
        
        # Calculate summary statistics
        total_forecast = sum(f['predicted_demand'] for f in forecast_data)
        avg_daily = total_forecast / prediction_length
        
        result = {
            'material_id': material_id,
            'forecast_period': {
                'start_date': forecast_data[0]['date'],
                'end_date': forecast_data[-1]['date'],
                'days': prediction_length
            },
            'summary': {
                'total_forecasted_demand': round(total_forecast, 2),
                'average_daily_demand': round(avg_daily, 2),
                'peak_demand': round(max(f['predicted_demand'] for f in forecast_data), 2),
                'min_demand': round(min(f['predicted_demand'] for f in forecast_data), 2)
            },
            'historical_context': {
                'data_points': len(context_df),
                'date_range': f"{context_df['timestamp'].min().strftime('%Y-%m-%d')} to {context_df['timestamp'].max().strftime('%Y-%m-%d')}",
                'total_historical_demand': int(context_df['target'].sum())
            },
            'forecast': forecast_data,
            'status': 'success'
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "status": "error"
        })

@tool
def compare_forecasts(
    material_ids: str,
    prediction_length: int = 30
) -> str:
    """Compare forecasts for multiple materials side-by-side.
    
    Args:
        material_ids: Comma-separated list of material IDs (e.g., "MAT-BAT-001,MAT-MOT-001")
        prediction_length: Number of days to forecast (default: 30)
    
    Returns:
        JSON string with comparative forecast analysis
    """
    try:
        material_list = [m.strip() for m in material_ids.split(',')]
        
        if len(material_list) > 5:
            return json.dumps({
                "error": "Cannot compare more than 5 materials at once",
                "status": "error"
            })
        
        comparisons = []
        
        for material_id in material_list:
            # Generate forecast for each material
            forecast_result = generate_forecast(material_id, prediction_length, False)
            forecast_data = json.loads(forecast_result)
            
            if forecast_data.get('status') == 'success':
                comparisons.append({
                    'material_id': material_id,
                    'total_demand': forecast_data['summary']['total_forecasted_demand'],
                    'avg_daily': forecast_data['summary']['average_daily_demand'],
                    'peak_demand': forecast_data['summary']['peak_demand']
                })
        
        # Sort by total demand
        comparisons.sort(key=lambda x: x['total_demand'], reverse=True)
        
        result = {
            'comparison_period': f"{prediction_length} days",
            'materials_compared': len(comparisons),
            'rankings': comparisons,
            'status': 'success'
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "status": "error"
        })

@tool
def get_material_info(material_id: str) -> str:
    """Get detailed information about a specific material.
    
    Args:
        material_id: Material ID (e.g., MAT-BAT-001)
    
    Returns:
        JSON string with material details
    """
    try:
        materials_data = load_csv(MATERIALS_FILE)
        material = next((m for m in materials_data if m['material_id'] == material_id), None)
        
        if not material:
            return json.dumps({
                "error": f"Material {material_id} not found",
                "status": "error"
            })
        
        return json.dumps(material, indent=2)
    except Exception as e:
        return f"Error getting material info: {str(e)}"

# Create Bedrock model
bedrock_model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    region_name="us-east-1"
)

# Create the agent
agent = Agent(
    model=bedrock_model,
    tools=[
        list_available_materials,
        generate_forecast,
        compare_forecasts,
        get_material_info
    ],
    system_prompt="""You are a Chronos-2 Forecasting Agent for E-bike component demand prediction. Generate forecasts with confidence intervals (10th, 50th, 90th percentiles).

CRITICAL: Keep ALL responses under 3 sentences. Be extremely concise. Only state the most important insight."""
)

# Interactive mode
if __name__ == "__main__":
    print("=" * 60)
    print("🔮 Chronos-2 Forecasting Agent")
    print("=" * 60)
    print("\nI can generate demand forecasts for E-bike materials using")
    print("Amazon Chronos-2 time series foundation model.\n")
    print("Example questions:")
    print("  - Generate a 30-day forecast for MAT-BAT-001")
    print("  - Compare forecasts for batteries and motors")
    print("  - What materials will have highest demand next month?")
    print("  - Show me a forecast with confidence intervals")
    print("\nType 'exit' to quit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Agent: ", end="", flush=True)
            response = agent(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
