"""
Quick test script for the seasonal analysis agent
"""
from seasonal_analysis_agent import agent

print("=" * 60)
print("Testing Demand Forecasting Agent")
print("=" * 60)

# Test 1: Load bike sales data
print("\n📊 Test 1: Loading bike sales data...")
try:
    response = agent("What are the total bike sales in the dataset?")
    print(f"✅ Success!\n{response}\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

# Test 2: Analyze seasonal patterns for a specific material
print("\n📊 Test 2: Analyzing seasonal patterns for battery MAT-BAT-001...")
try:
    response = agent("Analyze seasonal patterns for battery MAT-BAT-001")
    print(f"✅ Success!\n{response}\n")
except Exception as e:
    print(f"❌ Error: {str(e)}\n")

print("=" * 60)
print("Testing complete!")
print("=" * 60)
