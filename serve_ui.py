#!/usr/bin/env python3
"""
Simple web server to serve the ScrapeJET UI
This helps avoid CORS issues when opening the UI from file:// URLs
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Get the UI directory
ui_dir = Path(__file__).parent / "ui"

if not ui_dir.exists():
    print(f"Error: UI directory not found at {ui_dir}")
    sys.exit(1)

# Change to UI directory
os.chdir(ui_dir)

# Create server
PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

# Add CORS headers
class CORSHTTPRequestHandler(Handler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"🚀 ScrapeJET UI Server started!")
        print(f"📁 Serving files from: {ui_dir}")
        print(f"🌐 Open your browser to: http://localhost:{PORT}")
        print(f"🔗 API server should be running on: http://localhost:8000")
        print(f"⏹️  Press Ctrl+C to stop the server")
        print("-" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            httpd.shutdown()
