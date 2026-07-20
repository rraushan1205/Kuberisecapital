#!/bin/bash

# Stop all admin panel system services

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Stopping Admin Panel System                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Stop frontend
echo "Stopping frontend (port 3000)..."
FRONTEND_PIDS=$(lsof -ti :3000)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "$FRONTEND_PIDS" | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✓${NC} Frontend stopped"
else
    echo -e "${YELLOW}○${NC} Frontend was not running"
fi

# Stop backend
echo "Stopping backend (port 8000)..."
BACKEND_PIDS=$(lsof -ti :8000)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✓${NC} Backend stopped"
else
    echo -e "${YELLOW}○${NC} Backend was not running"
fi

# Optionally stop Docker containers
echo ""
read -p "Stop Docker containers (postgres, redis)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose stop postgres redis
    echo -e "${GREEN}✓${NC} Docker containers stopped"
else
    echo -e "${YELLOW}○${NC} Docker containers left running"
fi

# Clean up log files
if [ -f "backend.log" ] || [ -f "frontend.log" ]; then
    echo ""
    read -p "Remove log files? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f backend.log frontend.log
        echo -e "${GREEN}✓${NC} Log files removed"
    fi
fi

echo ""
echo -e "${GREEN}System stopped successfully!${NC}"
echo ""
