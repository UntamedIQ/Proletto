"""
Gunicorn Configuration for Proletto Production Deployment

This file contains configuration settings for running the Proletto app
with Gunicorn in production environments.

Usage:
    gunicorn -c gunicorn_config.py main:app
"""

import os
import multiprocessing

import os

# Bind to port provided by Replit or default to 5000
# Replit deployment typically sets PORT=5000 (maps to external port 80)
# It's critical to use the PORT environment variable Replit provides
PORT = os.getenv("PORT", "5000")

# Force port to 5000 for Replit deployment to ensure port forwarding works
if PORT != "5000":
    print(f"⚠️ WARNING: PORT is set to {PORT}, but Replit requires port 5000.")
    print("⚠️ Overriding to PORT=5000 to ensure external port 80 mapping works.")
    PORT = "5000"
    os.environ["PORT"] = PORT
    
bind = f"0.0.0.0:{PORT}"

# Log the port being used to help with debugging
print(f"✅ Gunicorn binding to: 0.0.0.0:{PORT} (will forward to external port 80 in deployment)")

# Dynamic worker count based on CPU cores
workers = max(2, (os.cpu_count() or 1) * 2)

# Use 2 threads per worker for handling concurrent requests
# This helps improve throughput when there are blocking I/O operations
threads = 2

# Timeout for worker processes (60 seconds)
# This prevents workers from hanging indefinitely
timeout = 60

# Access log configuration
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Preload the application to save memory
preload_app = True

# Recommended settings for Replit environments
worker_class = "sync"  # Use sync workers since we have threading enabled
worker_connections = 1000
max_requests = 1000  # Restart workers after handling this many requests
max_requests_jitter = 100  # Add jitter to avoid all workers restarting at once

# Process naming
proc_name = "proletto_gunicorn"

# Security settings
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190