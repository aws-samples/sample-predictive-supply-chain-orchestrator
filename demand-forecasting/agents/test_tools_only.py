"""
Test the agent tools directly (without LLM) to verify data loading works
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from seasonal_analysis_agent import (
    load_bike_sales_data,
    load_maintenance_data,
    explode_sales_to_materials,
    analyze_seasonal_patterns,
    get_material_info
)

print("=" * 60)
print("Testing Agent Tools (Direct Calls)")
print("=" * 60)

# Test 1: Load bike sales data
print("\n📊 Test 1: Loading bike sales data...")
try:
    result = load_bike_sales_data()
    print(f"✅ Success!\n{result[:500]}...\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

# Test 2: Load maintenance data
print("\n📊 Test 2: Loading maintenance data...")
try:
    result = load_maintenance_data()
    print(f"✅ Success!\n{result[:500]}...\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

# Test 3: Explode sales to materials
print("\n📊 Test 3: Exploding sales to material demand...")
try:
    result = explode_sales_to_materials()
    print(f"✅ Success!\n{result[:500]}...\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

# Test 4: Analyze seasonal patterns for battery
print("\n📊 Test 4: Analyzing seasonal patterns for MAT-BAT-001...")
try:
    result = analyze_seasonal_patterns("MAT-BAT-001")
    print(f"✅ Success!\n{result}\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

# Test 5: Get material info
print("\n📊 Test 5: Getting material info for MAT-BAT-001...")
try:
    result = get_material_info("MAT-BAT-001")
    print(f"✅ Success!\n{result}\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

print("=" * 60)
print("Tool testing complete!")
print("=" * 60)
