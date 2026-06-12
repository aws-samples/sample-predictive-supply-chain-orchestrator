"""
Flask API server for Demand Forecasting Agent
Provides REST endpoints for frontend integration
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from seasonal_analysis_agent import agent
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "agent": "demand-forecasting"})

@app.route('/api/query', methods=['POST'])
def query_agent():
    """
    Query the demand forecasting agent
    
    Request body:
    {
        "query": "What are the total bike sales?"
    }
    
    Response:
    {
        "response": "The total number of bikes sold is...",
        "status": "success"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' in request body",
                "status": "error"
            }), 400
        
        user_query = data['query']
        logger.info(f"Received query: {user_query}")
        
        # Call the agent
        response = agent(user_query)
        
        logger.info(f"Agent response: {response[:100]}...")
        
        return jsonify({
            "response": response,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/materials', methods=['GET'])
def get_materials():
    """Get list of all materials"""
    try:
        response = agent("List all materials in the catalog with their IDs and names")
        return jsonify({
            "response": response,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error getting materials: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/api/seasonal-analysis/<material_id>', methods=['GET'])
def get_seasonal_analysis(material_id):
    """Get seasonal analysis for a specific material"""
    try:
        response = agent(f"Analyze seasonal patterns for material {material_id}")
        return jsonify({
            "response": response,
            "material_id": material_id,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error analyzing material {material_id}: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Demand Forecasting Agent API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET  /health                           - Health check")
    print("  POST /api/query                        - Query agent")
    print("  GET  /api/materials                    - List materials")
    print("  GET  /api/seasonal-analysis/<id>       - Seasonal analysis")
    print("\nServer running on http://localhost:5000")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5000, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
