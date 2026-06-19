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

# Check if BEDROCK_API_KEY is set (never print the value or fragments)
api_key = os.environ.get('BEDROCK_API_KEY', '')

if api_key:
    print("✅ BEDROCK_API_KEY is set")
    print(f"   Length: {len(api_key)} characters")
else:
    print("❌ BEDROCK_API_KEY is NOT set")
    print("\nPlease add your Bedrock API key to the .env file:")
    print("   BEDROCK_API_KEY=your-key-here")

print("\n" + "=" * 60)
