"""
Demand Forecasting Agent - User Story 1: Historical Data Management & Seasonal Analysis

This agent loads historical sales and maintenance data, performs seasonal analysis,
and prepares data for Chronos-2 forecasting.
"""

import os
import sys
import csv
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any
import json
from dotenv import load_dotenv
import boto3

# Load environment variables from .env file
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
HOLIDAY_FILE = os.path.join(FORECAST_DATA_DIR, 'holiday_calendar.csv')

# Helper functions
def get_season(date_str: str) -> str:
    """Determine season from date string."""
    date = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
    month = date.month
    if month in [12, 1, 2]:
        return 'WINTER'
    elif month in [3, 4, 5]:
        return 'SPRING'
    elif month in [6, 7, 8]:
        return 'SUMMER'
    else:
        return 'FALL'

def load_csv(filepath: str) -> List[Dict[str, str]]:
    """Load CSV file and return list of dictionaries."""
    with open(filepath, 'r', encoding="utf-8") as f:
        return list(csv.DictReader(f))

# Tool definitions
@tool
def load_bike_sales_data(start_date: str = "", end_date: str = "") -> str:
    """Load bike sales history data with optional date filtering.
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        JSON string with sales data summary and statistics (no raw records to save tokens)
    """
    try:
        sales_data = load_csv(BIKE_SALES_FILE)
        
        # Filter by date if provided
        if start_date:
            sales_data = [s for s in sales_data if s['timestamp'] >= start_date]
        if end_date:
            sales_data = [s for s in sales_data if s['timestamp'] <= end_date]
        
        # Calculate statistics
        total_transactions = len(sales_data)
        total_bikes = sum(int(s['quantity_sold']) for s in sales_data)
        urban_bikes = sum(int(s['quantity_sold']) for s in sales_data if 'URBAN' in s['product_id'])
        mountain_bikes = sum(int(s['quantity_sold']) for s in sales_data if 'MOUNTAIN' in s['product_id'])
        
        result = {
            'total_transactions': total_transactions,
            'total_bikes_sold': total_bikes,
            'urban_bikes': urban_bikes,
            'mountain_bikes': mountain_bikes,
            'date_range': {
                'start': sales_data[0]['timestamp'] if sales_data else None,
                'end': sales_data[-1]['timestamp'] if sales_data else None
            }
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error loading bike sales data: {str(e)}"

@tool
def load_maintenance_data(maintenance_type: str = "") -> str:
    """Load maintenance demand history with optional type filtering.
    
    Args:
        maintenance_type: Optional filter (SCHEDULED_MAINTENANCE, WEAR_REPLACEMENT, ACCIDENT_REPAIR, WEATHER_DAMAGE)
    
    Returns:
        JSON string with maintenance data summary and statistics (no raw records to save tokens)
    """
    try:
        maint_data = load_csv(MAINTENANCE_FILE)
        
        # Filter by type if provided
        if maintenance_type:
            maint_data = [m for m in maint_data if m['maintenance_type'] == maintenance_type]
        
        # Calculate statistics
        total_events = len(maint_data)
        total_parts = sum(int(m['quantity']) for m in maint_data)
        
        # Count by type
        type_counts = defaultdict(int)
        for m in maint_data:
            type_counts[m['maintenance_type']] += 1
        
        # Count by material
        material_counts = defaultdict(int)
        for m in maint_data:
            material_counts[m['material_id']] += int(m['quantity'])
        
        result = {
            'total_events': total_events,
            'total_parts_needed': total_parts,
            'by_type': dict(type_counts),
            'top_5_materials': dict(sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error loading maintenance data: {str(e)}"

@tool
def explode_sales_to_materials() -> str:
    """Explode bike sales to material-level demand using BOM (Bill of Materials).
    
    This converts product-level sales (bikes) into material-level demand (components)
    by joining with the BOM to determine which materials are needed for each bike sold.
    
    Returns:
        JSON string with material demand summary from production
    """
    try:
        sales_data = load_csv(BIKE_SALES_FILE)
        bom_data = load_csv(BOM_FILE)
        
        # Create BOM lookup: product_id -> list of (material_id, quantity_required)
        bom_lookup = defaultdict(list)
        for bom_entry in bom_data:
            bom_lookup[bom_entry['product_id']].append({
                'material_id': bom_entry['material_id'],
                'quantity_required': float(bom_entry['quantity_required'])
            })
        
        # Explode sales to material demand
        material_demand = defaultdict(int)
        for sale in sales_data:
            product_id = sale['product_id']
            bikes_sold = int(sale['quantity_sold'])
            
            # Get materials needed for this product
            for bom_item in bom_lookup[product_id]:
                material_id = bom_item['material_id']
                qty_per_bike = bom_item['quantity_required']
                material_demand[material_id] += int(bikes_sold * qty_per_bike)
        
        result = {
            'total_materials_needed': sum(material_demand.values()),
            'unique_materials': len(material_demand),
            'top_materials': dict(sorted(material_demand.items(), key=lambda x: x[1], reverse=True)[:10]),
            'all_materials': dict(material_demand)
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error exploding sales to materials: {str(e)}"

@tool
def analyze_seasonal_patterns(material_id: str = "") -> str:
    """Analyze seasonal demand patterns for materials.
    
    Combines production demand (from bike sales) and maintenance demand,
    then calculates statistics by season for each material.
    
    Args:
        material_id: Optional specific material to analyze (e.g., MAT-BAT-001)
    
    Returns:
        JSON string with seasonal analysis results
    """
    try:
        # Load all data
        sales_data = load_csv(BIKE_SALES_FILE)
        maint_data = load_csv(MAINTENANCE_FILE)
        bom_data = load_csv(BOM_FILE)
        materials_data = load_csv(MATERIALS_FILE)
        
        # Create BOM lookup
        bom_lookup = defaultdict(list)
        for bom_entry in bom_data:
            bom_lookup[bom_entry['product_id']].append({
                'material_id': bom_entry['material_id'],
                'quantity_required': float(bom_entry['quantity_required'])
            })
        
        # Explode sales to material demand with dates
        material_demand_by_date = defaultdict(lambda: defaultdict(int))
        for sale in sales_data:
            date = sale['timestamp'].split()[0]
            season = get_season(sale['timestamp'])
            product_id = sale['product_id']
            bikes_sold = int(sale['quantity_sold'])
            
            for bom_item in bom_lookup[product_id]:
                mat_id = bom_item['material_id']
                qty = int(bikes_sold * bom_item['quantity_required'])
                material_demand_by_date[mat_id][season] += qty
        
        # Add maintenance demand
        for maint in maint_data:
            mat_id = maint['material_id']
            season = get_season(maint['timestamp'])
            qty = int(maint['quantity'])
            material_demand_by_date[mat_id][season] += qty
        
        # Calculate seasonal statistics
        seasonal_analysis = {}
        materials_to_analyze = [material_id] if material_id else material_demand_by_date.keys()
        
        for mat_id in materials_to_analyze:
            if mat_id not in material_demand_by_date:
                continue
            
            # Get material name
            mat_name = next((m['name'] for m in materials_data if m['material_id'] == mat_id), mat_id)
            
            seasonal_stats = {}
            for season in ['WINTER', 'SPRING', 'SUMMER', 'FALL']:
                demand = material_demand_by_date[mat_id].get(season, 0)
                seasonal_stats[season] = {
                    'total_demand': demand,
                    'avg_daily_demand': round(demand / 90, 2)  # Approx 90 days per season
                }
            
            seasonal_analysis[mat_id] = {
                'material_name': mat_name,
                'seasonal_stats': seasonal_stats,
                'total_annual_demand': sum(s['total_demand'] for s in seasonal_stats.values())
            }
        
        return json.dumps(seasonal_analysis, indent=2)
    except Exception as e:
        return f"Error analyzing seasonal patterns: {str(e)}"

@tool
def get_material_info(material_id: str = "") -> str:
    """Get information about materials from the materials catalog.
    
    Args:
        material_id: Optional specific material ID (e.g., MAT-BAT-001). If empty, returns all materials.
    
    Returns:
        JSON string with material information
    """
    try:
        materials_data = load_csv(MATERIALS_FILE)
        
        if material_id:
            materials_data = [m for m in materials_data if m['material_id'] == material_id]
        
        return json.dumps(materials_data, indent=2)
    except Exception as e:
        return f"Error getting material info: {str(e)}"

# Create Bedrock model with API key authentication
# The AWS_BEARER_TOKEN_BEDROCK environment variable is automatically used by boto3
# Using Amazon Nova Lite model (faster and more cost-effective)
bedrock_model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    region_name="us-east-1"
)

# Create the agent with Bedrock model
agent = Agent(
    model=bedrock_model,
    tools=[
        load_bike_sales_data,
        load_maintenance_data,
        explode_sales_to_materials,
        analyze_seasonal_patterns,
        get_material_info
    ],
    system_prompt="""You are a Demand Forecasting Agent for E-bike manufacturing. Analyze sales and maintenance data to identify seasonal patterns.

CRITICAL: Keep ALL responses under 3 sentences. Be extremely concise. Only state the most important insight."""
)

# Interactive mode
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Demand Forecasting Agent - Seasonal Analysis")
    print("=" * 60)
    print("\nI can help you analyze historical sales and maintenance data")
    print("to identify seasonal demand patterns for E-bike materials.\n")
    print("Example questions:")
    print("  - What are the total bike sales?")
    print("  - Analyze seasonal patterns for MAT-BAT-001")
    print("  - What materials have the highest demand?")
    print("  - Show me maintenance demand by type")
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
