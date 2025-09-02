#!/usr/bin/env python3
"""
Celery Worker Script for ScrapeJET
Run scalable workers for concurrent scraping tasks
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.celery_app import celery_app

if __name__ == "__main__":
    # Configure worker
    worker_args = [
        "worker",
        "--loglevel=info",
        "--concurrency=4",  # Number of worker processes
        "--queues=default,scraping,business,rag",  # Queues to handle
        "--prefetch-multiplier=1",  # Disable prefetching
        "--max-tasks-per-child=50",  # Restart worker after 50 tasks
        "--time-limit=7200",  # 2 hour hard limit
        "--soft-time-limit=3600",  # 1 hour soft limit
    ]
    
    # Add worker name if specified
    worker_name = os.getenv("WORKER_NAME", f"worker@{os.uname().nodename}")
    worker_args.extend(["--hostname", worker_name])
    
    # Start worker
    celery_app.worker_main(worker_args)
