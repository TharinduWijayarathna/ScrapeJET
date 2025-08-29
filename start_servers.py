#!/usr/bin/env python3
"""
Startup script for ScrapeJET
Runs both the API server and UI server
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def signal_handler(sig, frame):
    print('\n🛑 Shutting down servers...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_api_server():
    """Run the API server"""
    print("🚀 Starting ScrapeJET API server...")
    try:
        # Run the API server
        api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "src.api.main:app", 
            "--reload", "--host", "0.0.0.0", "--port", "8000"
        ])
        return api_process
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def run_ui_server():
    """Run the UI server"""
    print("🌐 Starting ScrapeJET UI server...")
    try:
        # Run the UI server
        ui_process = subprocess.Popen([
            sys.executable, "serve_ui.py"
        ])
        return ui_process
    except Exception as e:
        print(f"❌ Failed to start UI server: {e}")
        return None

def main():
    print("🎯 ScrapeJET Startup")
    print("=" * 50)
    
    # Start API server
    api_process = run_api_server()
    if not api_process:
        print("❌ Failed to start API server. Exiting.")
        sys.exit(1)
    
    # Wait a bit for API server to start
    time.sleep(3)
    
    # Start UI server
    ui_process = run_ui_server()
    if not ui_process:
        print("❌ Failed to start UI server. Exiting.")
        api_process.terminate()
        sys.exit(1)
    
    print("\n✅ Both servers started successfully!")
    print("=" * 50)
    print("🌐 UI Server: http://localhost:8080")
    print("🔗 API Server: http://localhost:8000")
    print("📊 Health Check: http://localhost:8000/health")
    print("=" * 50)
    print("⏹️  Press Ctrl+C to stop all servers")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if api_process.poll() is not None:
                print("❌ API server stopped unexpectedly")
                break
                
            if ui_process.poll() is not None:
                print("❌ UI server stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
    finally:
        # Cleanup
        if api_process:
            api_process.terminate()
            api_process.wait()
        if ui_process:
            ui_process.terminate()
            ui_process.wait()
        print("✅ All servers stopped")

if __name__ == "__main__":
    main()
