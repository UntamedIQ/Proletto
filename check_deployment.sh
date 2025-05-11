#!/bin/bash
# Script to verify that the Gunicorn deployment is running correctly

echo "=============================================="
echo "Proletto Deployment Verification Tool"
echo "=============================================="

# Check if gunicorn process is running
gunicorn_count=$(ps aux | grep gunicorn | grep -v grep | wc -l)
if [ $gunicorn_count -gt 0 ]; then
    echo "✅ Gunicorn is running ($gunicorn_count processes found)"
else
    echo "❌ Gunicorn is not running"
fi

# Check if something is listening on port 5000
port_5000=$(netstat -tuln 2>/dev/null | grep ":5000 " | wc -l)
if [ $port_5000 -gt 0 ]; then
    echo "✅ Port 5000 is in use (likely by Gunicorn)"
else
    echo "❌ Port 5000 is not in use"
fi

# Check if the application responds on port 5000
echo "Testing HTTP response from localhost:5000..."
curl_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ 2>/dev/null)
if [ $? -eq 0 ] && [ "$curl_response" != "000" ]; then
    echo "✅ HTTP status $curl_response received from localhost:5000"
else
    echo "❌ No response from localhost:5000"
fi

# Check environment variables
echo -e "\nChecking environment variables:"
if [ -n "$PORT" ]; then
    echo "✅ PORT is set to: $PORT"
else
    echo "❌ PORT is not set"
fi

if [ -n "$REPLIT_DEPLOYMENT" ]; then
    echo "✅ REPLIT_DEPLOYMENT is set to: $REPLIT_DEPLOYMENT"
else
    echo "❌ REPLIT_DEPLOYMENT is not set"
fi

# Check .replit file for expected configuration
echo -e "\nChecking .replit configuration:"
if [ -f .replit ]; then
    echo "✅ .replit file exists"
    
    # Check for port configuration
    if grep -q "waitForPort = 5000" .replit; then
        echo "✅ waitForPort is correctly set to 5000"
    elif grep -q "waitForPort" .replit; then
        echo "❌ waitForPort exists but is NOT set to 5000"
        echo "   You need to manually update the .replit file"
    else
        echo "❌ waitForPort configuration not found in .replit"
        echo "   You need to manually add this configuration"
    fi
    
    if grep -q "localPort = 5000" .replit && grep -q "externalPort = 80" .replit; then
        echo "✅ Port mapping configuration appears correct"
    else
        echo "❌ Port mapping configuration missing or incorrect"
        echo "   You need to update the .replit file with:"
        echo "   [[ports]]"
        echo "   localPort = 5000"
        echo "   externalPort = 80"
    fi
else
    echo "❌ .replit file not found - this is required for proper deployment"
fi

echo -e "\nFor help with fixing deployment issues, refer to:"
echo "REPLIT_DEPLOYMENT_UPDATE.md"