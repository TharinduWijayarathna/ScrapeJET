#!/usr/bin/env python3
"""
Celery Configuration for ScrapeJET
Production-grade queue management for concurrent scraping tasks
"""

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Construct Redis URL
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Create Celery application
celery_app = Celery(
    "scrapejet",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "src.tasks.scrape_website_task": {"queue": "scraping"},
        "src.tasks.scrape_business_task": {"queue": "business"},
        "src.tasks.process_rag_task": {"queue": "rag"},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Disable prefetching for better load balancing
    task_acks_late=True,  # Acknowledge tasks only after completion
    worker_disable_rate_limits=False,
    
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task time limits
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,  # 2 hour hard limit
    
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Retry configuration
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Queue configuration
    task_default_queue="default",
    task_create_missing_queues=True,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    
    # Performance optimizations
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Queue priorities
    task_inherit_parent_priority=True,
    task_default_priority=5,
    worker_direct=True,
)

# Define queue priorities
celery_app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "sep": ":",
    "queue_order_strategy": "priority",
}

if __name__ == "__main__":
    celery_app.start()
