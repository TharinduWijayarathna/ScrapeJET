#!/usr/bin/env python3
"""
Demo UI Server for ScrapeJET - Serves the graphical demo interface
This allows users to visually see how the web scraper works
"""

import os
import sys
import argparse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
from loguru import logger

class CORSHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support for demo UI"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        logger.info(f"Demo UI Server: {format % args}")

def find_free_port(start_port=8080):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports found in range {start_port}-{start_port + 100}")

def main():
    parser = argparse.ArgumentParser(description='Serve ScrapeJET Demo UI')
    parser.add_argument('--port', type=int, default=8080, help='Port to serve on (default: 8080)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--directory', default='.', help='Directory to serve (default: current directory)')
    
    args = parser.parse_args()
    
    # Change to the UI directory
    ui_dir = Path(__file__).parent
    os.chdir(ui_dir)
    
    # Check if index.html exists
    if not Path('index.html').exists():
        logger.error("❌ index.html not found in UI directory!")
        logger.error(f"Expected location: {ui_dir}/index.html")
        sys.exit(1)
    
    # Find a free port if the specified port is in use
    try:
        port = args.port
        server = HTTPServer((args.host, port), CORSHTTPRequestHandler)
    except OSError:
        logger.warning(f"Port {port} is in use, trying to find a free port...")
        port = find_free_port(port + 1)
        server = HTTPServer((args.host, port), CORSHTTPRequestHandler)
    
    logger.info(f"🚀 ScrapeJET Demo UI Server starting...")
    logger.info(f"📁 Serving demo UI from: {ui_dir}")
    logger.info(f"🌐 Demo URL: http://{args.host}:{port}")
    logger.info(f"📄 Main demo file: http://{args.host}:{port}/index.html")
    logger.info(f"🔗 API Server: http://{args.host}:8000")
    logger.info(f"📊 Health Check: http://{args.host}:8000/health")
    logger.info("=" * 60)
    logger.info("🎯 This demo UI shows how the scraper works graphically!")
    logger.info("📱 Open the URL in your browser to see the scraper in action")
    logger.info("⏹️  Press Ctrl+C to stop the demo server")
    logger.info("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down demo UI server...")
        server.shutdown()
        logger.info("✅ Demo UI server stopped")

if __name__ == "__main__":
    main()
