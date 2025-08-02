#!/usr/bin/env python3
"""
Script to pre-download ONNX models during Docker build
"""

import os
import sys

# Set up environment
os.environ['PYTHONPATH'] = '/app'
sys.path.append('/app')

def download_models():
    """Download ONNX models"""
    try:
        print("Pre-downloading ONNX models...")
        from src.rag.vector_store import VectorStore
        vector_store = VectorStore()
        print("✓ ONNX models downloaded successfully")
        return True
    except Exception as e:
        print(f"✗ Error downloading models: {e}")
        return False

if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1) 