#!/bin/bash
# deploy_dragon.sh - Deployment script for the Multi-Headed Dragon

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}Deploying Proletto's Multi-Headed Dragon${NC}"
echo -e "${BLUE}=======================================${NC}"
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# 1. Check environment
echo -e "${YELLOW}Checking environment...${NC}"

# Check Python version
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "✅ Python detected: ${PYTHON_VERSION}"
else
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

# Check if APScheduler is installed
if python3 -c "import apscheduler" 2>/dev/null; then
    echo -e "✅ APScheduler is installed"
else
    echo -e "${YELLOW}⚠️ APScheduler not found. Installing...${NC}"
    pip install apscheduler
fi

# 2. Create necessary directories
echo -e "\n${YELLOW}Creating necessary directories...${NC}"
mkdir -p data logs
echo -e "✅ Created data and logs directories"

# 3. Setup environment variables
echo -e "\n${YELLOW}Setting up environment variables...${NC}"

# Default port if not set
if [ -z "$PORT" ]; then
    export PORT=5002
    echo -e "✅ Set PORT to 5002"
else
    echo -e "✅ Using existing PORT=$PORT"
fi

# Set production mode
export FLASK_ENV=production
echo -e "✅ Set FLASK_ENV to production"

# 4. Run the dragon in the background
echo -e "\n${YELLOW}Starting the Multi-Headed Dragon...${NC}"

# Kill any existing process if there's a pid file
if [ -f dragon.pid ]; then
    OLD_PID=$(cat dragon.pid)
    if ps -p $OLD_PID > /dev/null; then
        echo -e "${YELLOW}⚠️ Existing Dragon process found (PID: $OLD_PID). Stopping it...${NC}"
        kill $OLD_PID
        sleep 2
    fi
    rm dragon.pid
fi

# Start the dragon process
if command_exists gunicorn; then
    echo -e "✅ Gunicorn found, using it to run the Dragon"
    gunicorn --bind 0.0.0.0:$PORT \
             --workers 3 \
             --timeout 120 \
             --access-logfile logs/dragon_access.log \
             --error-logfile logs/dragon_error.log \
             --daemon \
             --pid dragon.pid \
             "dragon_core:create_app()"
    
    echo -e "${GREEN}✅ Dragon started with Gunicorn (PID: $(cat dragon.pid))${NC}"
else
    echo -e "${YELLOW}⚠️ Gunicorn not found, falling back to Python script${NC}"
    nohup python3 run_dragon.py > logs/dragon.log 2>&1 &
    DRAGON_PID=$!
    echo $DRAGON_PID > dragon.pid
    echo -e "${GREEN}✅ Dragon started with Python (PID: $DRAGON_PID)${NC}"
fi

# 5. Display status
echo -e "\n${YELLOW}Checking Dragon status...${NC}"
sleep 2

if [ -f dragon.pid ]; then
    DRAGON_PID=$(cat dragon.pid)
    if ps -p $DRAGON_PID > /dev/null; then
        echo -e "${GREEN}✅ Multi-Headed Dragon is running (PID: $DRAGON_PID)${NC}"
        echo -e "${GREEN}✅ Access the Dragon at: http://localhost:$PORT/health${NC}"
        
        # Try to fetch health status
        if command_exists curl; then
            echo -e "\n${YELLOW}Fetching health status...${NC}"
            sleep 1
            HEALTH=$(curl -s http://localhost:$PORT/health)
            echo -e "${BLUE}$HEALTH${NC}"
        fi
    else
        echo -e "${RED}❌ Dragon process not found. Check logs/dragon.log for errors.${NC}"
    fi
else
    echo -e "${RED}❌ PID file not found. Dragon may not have started.${NC}"
fi

echo -e "\n${BLUE}=======================================${NC}"
echo -e "${GREEN}Dragon deployment complete${NC}"
echo -e "${BLUE}=======================================${NC}"

# Display some helpful commands
echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  • View logs: ${BLUE}tail -f logs/dragon.log${NC}"
echo -e "  • Stop Dragon: ${BLUE}kill \$(cat dragon.pid)${NC}"
echo -e "  • Dragon health: ${BLUE}curl http://localhost:$PORT/health${NC}"
echo -e "  • Trigger scrapers: ${BLUE}curl http://localhost:$PORT/admin/rescue/run-scrapers${NC}"
echo -e "  • Restart scheduler: ${BLUE}curl http://localhost:$PORT/admin/rescue/restart-scheduler${NC}"
echo