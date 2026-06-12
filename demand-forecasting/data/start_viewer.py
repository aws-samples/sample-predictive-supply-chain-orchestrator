#!/usr/bin/env python3
"""
Simple HTTP server to view the data visualization
Run this script and open http://localhost:8000/data_viewer.html in your browser
"""

import http.server
import socketserver
import webbrowser
import os

PORT = 8888

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def start_server():
    handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("=" * 60)
        print("📊 Data Viewer Server Started")
        print("=" * 60)
        print(f"\n✅ Server running at: http://localhost:{PORT}")
        print(f"✅ Open this URL in your browser: http://localhost:{PORT}/data_viewer.html")
        print("\n💡 Press Ctrl+C to stop the server\n")
        
        # Try to open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}/data_viewer.html')
            print("🌐 Opening browser automatically...\n")
        except:
            print("⚠️  Could not open browser automatically. Please open the URL manually.\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    start_server()
