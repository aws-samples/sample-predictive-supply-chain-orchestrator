#!/bin/bash
# Package the Strands agent for AgentCore deployment.
# Creates agent-bundle/ with source code AND pre-installed arm64 dependencies.
#
# AgentCore Runtime uses direct_code_deploy which requires dependencies
# to be bundled in the zip (not installed at cold start).
# See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$BACKEND_DIR")"
BUNDLE_DIR="$BACKEND_DIR/agent-bundle"

echo "Packaging agent for AgentCore..."
echo "  Backend: $BACKEND_DIR"
echo "  Bundle:  $BUNDLE_DIR"

# Clean previous bundle
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

# ── Step 1: Pre-install dependencies for arm64 (AgentCore uses Graviton) ──
echo ""
echo "Installing arm64 dependencies into bundle..."
uv pip install \
  --python-platform aarch64-manylinux2014 \
  --python-version 3.12 \
  --target="$BUNDLE_DIR" \
  --only-binary=:all: \
  -r "$BACKEND_DIR/requirements-agentcore.txt" \
  2>&1 | tail -5 || true

echo "Dependencies installed."

# ── Step 2: Copy agent source code ──
echo ""
echo "Copying agent source code..."

# Copy agent code
cp -r "$BACKEND_DIR/agents" "$BUNDLE_DIR/agents"
cp -r "$BACKEND_DIR/core" "$BUNDLE_DIR/core"
cp -r "$BACKEND_DIR/data" "$BUNDLE_DIR/data" 2>/dev/null || mkdir -p "$BUNDLE_DIR/data"
cp -r "$BACKEND_DIR/config" "$BUNDLE_DIR/config" 2>/dev/null || mkdir -p "$BUNDLE_DIR/config"

# Copy CSV data files
cp -r "$PROJECT_DIR/data/"*.csv "$BUNDLE_DIR/data/" 2>/dev/null || true

# Copy entrypoint to bundle root
cp "$BACKEND_DIR/agents/agentcore_entrypoint.py" "$BUNDLE_DIR/main.py"

# Copy API handler, server, state, and route Blueprints for Lambda (shared bundle)
mkdir -p "$BUNDLE_DIR/api"
cp "$BACKEND_DIR/api/__init__.py" "$BUNDLE_DIR/api/" 2>/dev/null || touch "$BUNDLE_DIR/api/__init__.py"
cp "$BACKEND_DIR/api/server.py" "$BUNDLE_DIR/api/"
cp "$BACKEND_DIR/api/state.py" "$BUNDLE_DIR/api/"
cp -r "$BACKEND_DIR/api/routes" "$BUNDLE_DIR/api/routes"
cp "$BACKEND_DIR/aws/lambda_tools/api_handler.py" "$BUNDLE_DIR/"

# Copy requirements (for reference, deps are already pre-installed)
cp "$BACKEND_DIR/requirements.txt" "$BUNDLE_DIR/" 2>/dev/null || true

# ── Step 3: Clean up ──
find "$BUNDLE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUNDLE_DIR" -name "*.pyc" -delete 2>/dev/null || true

# Remove packages already provided by the Lambda Layer or Lambda runtime.
# This keeps the bundle under the 250MB unzipped Lambda limit.
# (AgentCore deploy uses its own bundling via scripts/deploy_agent_runtime.py)
echo ""
echo "Removing packages provided by Lambda Layer / runtime..."
LAYER_PROVIDED=(scipy scipy.libs numpy numpy.libs pandas botocore boto3 s3transfer
                gremlinpython flask flask_cors pydantic pydantic_core structlog
                apig_wsgi dotenv)
for pkg in "${LAYER_PROVIDED[@]}"; do
  rm -rf "$BUNDLE_DIR/$pkg" "$BUNDLE_DIR/${pkg}-"*.dist-info 2>/dev/null || true
done

# Show bundle contents
echo ""
echo "Bundle contents (source files):"
find "$BUNDLE_DIR" -maxdepth 2 -type f -name "*.py" | head -20 || true
echo ""
du -sh "$BUNDLE_DIR"
echo "Done!"
