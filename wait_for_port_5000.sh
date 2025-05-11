#!/bin/bash
# Helper script to wait for port 5000
# This is used by the deployment workflow

echo "Waiting for port 5000 to become available..."
MAX_RETRIES=30
COUNT=0

while [ $COUNT -lt $MAX_RETRIES ]; do
    # Check if port 5000 is listening
    if netstat -tuln | grep ":5000 " > /dev/null; then
        echo "✅ Port 5000 is now available!"
        exit 0
    fi
    
    echo "Attempt $COUNT: Port 5000 not available yet, waiting..."
    sleep 2
    COUNT=$((COUNT+1))
done

echo "❌ Timed out waiting for port 5000"
exit 1
