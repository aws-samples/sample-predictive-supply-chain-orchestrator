#!/usr/bin/env python3
"""
Unified server for E-bike Demand Forecasting System
Serves both the data viewer and the AI agent API
"""

import http.server
import socketserver
import json
import os
import sys
import numpy as np
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).parent / 'agents'
sys.path.insert(0, str(agent_dir))

# Import both agents
from seasonal_analysis_agent import agent as seasonal_agent
from chronos_forecasting_agent import agent as forecast_agent

# Import direct forecast functions (bypass LLM for calculator)
from chronos_forecasting_agent import (
    prepare_material_timeseries,
    generate_mock_forecast,
    get_chronos_pipeline,
    CHRONOS_AVAILABLE,
    load_csv,
    MATERIALS_FILE,
    BOM_FILE,
    MAINTENANCE_FILE
)
import pandas as pd

PORT = 8888

class UnifiedHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        # API endpoints
        if parsed_path.path == '/api/health':
            self.send_json_response({"status": "healthy", "agents": ["seasonal-analysis", "chronos-forecast"]})
        
        elif parsed_path.path == '/api/materials':
            try:
                agent_result = seasonal_agent("List all materials in the catalog with their IDs and names")
                response_text = str(agent_result)
                self.send_json_response({"response": response_text, "status": "success"})
            except Exception as e:
                self.send_json_response({"error": str(e), "status": "error"}, 500)
        
        elif parsed_path.path.startswith('/api/seasonal-analysis/'):
            material_id = parsed_path.path.split('/')[-1]
            try:
                agent_result = seasonal_agent(f"Analyze seasonal patterns for material {material_id}")
                response_text = str(agent_result)
                self.send_json_response({
                    "response": response_text,
                    "material_id": material_id,
                    "status": "success"
                })
            except Exception as e:
                self.send_json_response({"error": str(e), "status": "error"}, 500)
        
        # Serve static files
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/forecast':
            self.handle_direct_forecast()
            return
        
        elif parsed_path.path == '/api/query':
            try:
                # Read request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                if 'query' not in data:
                    self.send_json_response({
                        "error": "Missing 'query' in request body",
                        "status": "error"
                    }, 400)
                    return
                
                user_query = data['query']
                agent_type = data.get('agent', 'seasonal')  # Default to seasonal agent
                
                print(f"\n{'='*60}")
                print(f"📝 Query ({agent_type}): {user_query}")
                print(f"{'='*60}")
                
                # Call the appropriate agent
                if agent_type == 'forecast':
                    agent_result = forecast_agent(user_query)
                else:
                    agent_result = seasonal_agent(user_query)
                
                # Extract text from AgentResult object
                response_text = str(agent_result)
                
                print(f"✅ Response length: {len(response_text)} characters")
                print(f"✅ Response preview: {response_text[:200]}...")
                print(f"{'='*60}\n")
                
                self.send_json_response({
                    "response": response_text,
                    "agent": agent_type,
                    "status": "success"
                })
                
            except Exception as e:
                error_msg = str(e)
                print(f"\n{'='*60}")
                print(f"❌ Error: {error_msg}")
                print(f"{'='*60}\n")
                
                # Check for specific error types
                if "max_tokens" in error_msg.lower():
                    error_msg = "Agent response too long. Try asking a more specific question or request a summary."
                elif "rate limit" in error_msg.lower():
                    error_msg = "API rate limit reached. Please wait a moment and try again."
                
                self.send_json_response({
                    "error": error_msg,
                    "status": "error"
                }, 500)
        else:
            self.send_json_response({"error": "Not found"}, 404)
    
    def handle_direct_forecast(self):
        """Direct forecast endpoint - calls Chronos functions without LLM."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            material_id = data.get('material_id')
            prediction_length = min(data.get('prediction_length', 30), 90)
            product_id = data.get('product_id', None)  # None or 'ALL' = all models
            
            if not material_id:
                self.send_json_response({"error": "Missing material_id", "status": "error"}, 400)
                return
            
            print(f"🔮 Direct forecast: {material_id} for {prediction_length} days (product: {product_id or 'ALL'})")
            
            # Prepare time series (filtered by product if specified)
            context_df = prepare_material_timeseries(material_id, product_id=product_id)
            
            if context_df.empty:
                self.send_json_response({
                    "error": f"No historical data for {material_id}",
                    "status": "error"
                }, 404)
                return
            
            context_df['id'] = material_id
            quantile_levels = [0.1, 0.5, 0.9]
            
            # Generate forecast using Chronos or mock
            pipeline = get_chronos_pipeline()
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
                pred_df = generate_mock_forecast(context_df, prediction_length, quantile_levels)
            
            # Build response with percentiles
            forecast_points = []
            for _, row in pred_df.iterrows():
                forecast_points.append({
                    'date': row['timestamp'].strftime('%Y-%m-%d'),
                    'p10': round(float(row['0.1']), 2),
                    'p50': round(float(row['0.5']), 2),
                    'p90': round(float(row['0.9']), 2)
                })
            
            # Summary stats from percentiles
            total_p10 = sum(f['p10'] for f in forecast_points)
            total_p50 = sum(f['p50'] for f in forecast_points)
            total_p90 = sum(f['p90'] for f in forecast_points)
            
            # --- Explainability stats ---
            ts = context_df['target']
            hist_mean = float(ts.mean())
            hist_std = float(ts.std()) if len(ts) > 1 else 0
            hist_min = int(ts.min())
            hist_max = int(ts.max())
            cv = round(hist_std / hist_mean, 2) if hist_mean > 0 else 0  # coefficient of variation

            # Trend: compare first-half avg vs second-half avg
            half = len(ts) // 2
            first_half_avg = float(ts.iloc[:half].mean()) if half > 0 else hist_mean
            second_half_avg = float(ts.iloc[half:].mean()) if half > 0 else hist_mean
            trend_pct = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1) if first_half_avg > 0 else 0
            if trend_pct > 5:
                trend_direction = 'increasing'
            elif trend_pct < -5:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'

            # Weekly seasonality strength (std of day-of-week averages / overall mean)
            context_df_copy = context_df.copy()
            context_df_copy['dow'] = context_df_copy['timestamp'].dt.dayofweek
            dow_avg = context_df_copy.groupby('dow')['target'].mean()
            seasonal_strength = round(float(dow_avg.std()) / hist_mean, 2) if hist_mean > 0 else 0

            # Recent momentum: last 30 days avg vs overall avg
            recent_window = min(30, len(ts))
            recent_avg = float(ts.iloc[-recent_window:].mean())
            momentum_pct = round((recent_avg - hist_mean) / hist_mean * 100, 1) if hist_mean > 0 else 0

            # Spread ratio: how wide is the model's uncertainty
            spread_ratio = round((total_p90 - total_p10) / total_p50 * 100, 1) if total_p50 > 0 else 0

            explainability = {
                'hist_mean': round(hist_mean, 2),
                'hist_std': round(hist_std, 2),
                'hist_min': hist_min,
                'hist_max': hist_max,
                'cv': cv,
                'trend_direction': trend_direction,
                'trend_pct': trend_pct,
                'first_half_avg': round(first_half_avg, 2),
                'second_half_avg': round(second_half_avg, 2),
                'seasonal_strength': seasonal_strength,
                'dow_pattern': {int(k): round(v, 2) for k, v in dow_avg.to_dict().items()},
                'recent_avg': round(recent_avg, 2),
                'momentum_pct': momentum_pct,
                'spread_ratio': spread_ratio,
                'data_span_days': len(ts),
            }

            result = {
                'material_id': material_id,
                'prediction_length': prediction_length,
                'summary': {
                    'total_p10': round(total_p10, 1),
                    'total_p50': round(total_p50, 1),
                    'total_p90': round(total_p90, 1),
                    'avg_daily_p50': round(total_p50 / prediction_length, 2)
                },
                'historical': {
                    'data_points': len(context_df),
                    'total_demand': int(context_df['target'].sum()),
                    'avg_daily': round(float(context_df['target'].mean()), 2)
                },
                'explainability': explainability,
                'forecast': forecast_points,
                'model': 'chronos-2' if CHRONOS_AVAILABLE else 'mock',
                'status': 'success'
            }
            
            print(f"✅ Forecast complete: p10={total_p10:.0f}, p50={total_p50:.0f}, p90={total_p90:.0f}")
            self.send_json_response(result)
            
        except Exception as e:
            print(f"❌ Forecast error: {str(e)}")
            self.send_json_response({"error": str(e), "status": "error"}, 500)
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response with proper headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def start_server():
    handler = UnifiedHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("=" * 70)
        print("🚀 E-bike Demand Forecasting System - Unified Server")
        print("=" * 70)
        print(f"\n✅ Server running at: http://localhost:{PORT}")
        print("\n📊 Available Pages:")
        print(f"   • Data Viewer:    http://localhost:{PORT}/data/data_viewer.html")
        print(f"   • Agent Chat:     http://localhost:{PORT}/frontend/demand-forecasting.html")
        print("\n🔌 API Endpoints:")
        print(f"   • GET  /api/health")
        print(f"   • POST /api/query")
        print(f"   • POST /api/forecast  (direct Chronos - no LLM)")
        print(f"   • GET  /api/materials")
        print(f"   • GET  /api/seasonal-analysis/<material_id>")
        print("\n💡 Press Ctrl+C to stop the server\n")
        print("=" * 70)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    # Change to the project root directory
    os.chdir(Path(__file__).parent)
    start_server()
