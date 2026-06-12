"""
Check if Bedrock API key is configured correctly
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Configuration Check")
print("=" * 60)

# Check if BEDROCK_API_KEY is set
api_key = os.environ.get('BEDROCK_API_KEY', '')

if api_key:
    print(f"✅ BEDROCK_API_KEY is set")
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with: {api_key[:20]}...")
    print(f"   Ends with: ...{api_key[-20:]}")
else:
    print("❌ BEDROCK_API_KEY is NOT set")
    print("\nPlease add your Bedrock API key to the .env file:")
    print("   BEDROCK_API_KEY=your-key-here")

print("\n" + "=" * 60)
