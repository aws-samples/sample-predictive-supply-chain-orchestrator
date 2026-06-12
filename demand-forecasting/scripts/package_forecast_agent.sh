#!/bin/bash
# Package the forecast agent for AgentCore deployment.
# Copies source files into agent-bundle/ (generated, gitignored).
# Follows same pattern as backend/scripts/package_agent.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FORECAST_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$FORECAST_DIR")"
BUNDLE_DIR="$FORECAST_DIR/agent-bundle"

echo "Packaging forecast agent for AgentCore..."
echo "  Source:  $FORECAST_DIR"
echo "  Bundle:  $BUNDLE_DIR"

# Clean previous bundle
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/agents"
mkdir -p "$BUNDLE_DIR/data"

# Copy entrypoint
cp "$FORECAST_DIR/agents/agentcore_entrypoint.py" "$BUNDLE_DIR/main.py"

# Copy agent code
cp "$FORECAST_DIR/agents/__init__.py" "$BUNDLE_DIR/agents/" 2>/dev/null || \
    echo "# forecast agents" > "$BUNDLE_DIR/agents/__init__.py"

# Copy data modules
cp "$FORECAST_DIR/data/chronos_client.py" "$BUNDLE_DIR/data/"
cp "$FORECAST_DIR/data/s3_data_loader.py" "$BUNDLE_DIR/data/"
echo "# data modules" > "$BUNDLE_DIR/data/__init__.py"

# Create requirements.txt
cat > "$BUNDLE_DIR/requirements.txt" << 'EOF'
bedrock-agentcore
strands-agents
strands-agents-builder
boto3>=1.34.0
pandas>=2.2.0
numpy>=1.26.0
python-dotenv>=1.0.0
EOF

# Verify
if [ ! -f "$BUNDLE_DIR/main.py" ]; then
    echo "ERROR: main.py not found in bundle"
    exit 1
fi

# Remove __pycache__
find "$BUNDLE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "Bundle contents:"
find "$BUNDLE_DIR" -type f | sort
echo ""
du -sh "$BUNDLE_DIR"
echo "Done!"
