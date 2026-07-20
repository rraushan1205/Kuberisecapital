#!/bin/bash

# Simple startup script for admin panel (uses existing PostgreSQL)
# This version assumes PostgreSQL is already running on your system

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Admin Panel Simple Startup                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    lsof -i :"$1" > /dev/null 2>&1
    return $?
}

# Step 1: Check PostgreSQL
echo -e "${YELLOW}[1/4]${NC} Checking PostgreSQL..."
if check_port 5432; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running on port 5432"
else
    echo -e "${RED}✗${NC} PostgreSQL is not running!"
    echo "Please start PostgreSQL first."
    echo "You can start it with: brew services start postgresql"
    exit 1
fi

# Step 2: Start Redis (via Docker)
echo ""
echo -e "${YELLOW}[2/4]${NC} Starting Redis..."
REDIS_RUNNING=$(docker ps --filter "name=redis" --filter "status=running" -q 2>/dev/null)

if [ -z "$REDIS_RUNNING" ]; then
    echo "Starting Redis container..."
    docker-compose up -d redis
    sleep 2
    echo -e "${GREEN}✓${NC} Redis started"
else
    echo -e "${GREEN}✓${NC} Redis is already running"
fi

# Step 3: Start Backend
echo ""
echo -e "${YELLOW}[3/4]${NC} Starting backend API..."

if check_port 8000; then
    echo -e "${GREEN}✓${NC} Backend is already running on port 8000"
else
    echo "Starting backend server..."
    
    # Check if virtual environment exists
    if [ -d "backend/.venv" ]; then
        echo "Using virtual environment..."
        cd backend
        source .venv/bin/activate
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
        BACKEND_PID=$!
        cd ..
    else
        echo "No virtual environment found, using system Python..."
        cd backend
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
        BACKEND_PID=$!
        cd ..
    fi
    
    # Wait for backend to start
    echo -n "Waiting for backend to start"
    for i in {1..15}; do
        if check_port 8000; then
            echo ""
            echo -e "${GREEN}✓${NC} Backend started successfully (PID: $BACKEND_PID)"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! check_port 8000; then
        echo ""
        echo -e "${RED}✗${NC} Backend failed to start. Check backend.log for errors:"
        tail -20 backend.log
        exit 1
    fi
    
    # Show admin credentials from backend startup
    sleep 2
    if grep -q "Initial Super Admin" backend.log; then
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════${NC}"
        grep -A 4 "Initial Super Admin" backend.log | grep -v "^--"
        echo -e "${GREEN}════════════════════════════════════════════════${NC}"
    fi
fi

# Step 4: Start Frontend
echo ""
echo -e "${YELLOW}[4/4]${NC} Starting frontend..."

if check_port 3000; then
    echo -e "${GREEN}✓${NC} Frontend is already running on port 3000"
else
    echo "Starting Next.js development server..."
    
    nohup npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    echo -n "Waiting for frontend to start"
    for i in {1..20}; do
        if check_port 3000; then
            echo ""
            echo -e "${GREEN}✓${NC} Frontend started successfully (PID: $FRONTEND_PID)"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! check_port 3000; then
        echo ""
        echo -e "${RED}✗${NC} Frontend failed to start. Check frontend.log for errors:"
        tail -20 frontend.log
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🎉 System Started Successfully!        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Admin Panel Access:${NC}"
echo -e "  URL: ${YELLOW}http://localhost:3000/admin/login${NC}"
echo ""
echo -e "${BLUE}Default Credentials:${NC}"
ADMIN_EMAIL=$(grep "ADMIN_EMAIL" backend/.env | cut -d '=' -f2)
ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD" backend/.env | cut -d '=' -f2)
echo -e "  Email:    ${YELLOW}${ADMIN_EMAIL}${NC}"
echo -e "  Password: ${YELLOW}${ADMIN_PASSWORD}${NC}"
echo ""
echo -e "${BLUE}Service Status:${NC}"
echo -e "  Backend:  ${GREEN}✓${NC} http://localhost:8000"
echo -e "  Frontend: ${GREEN}✓${NC} http://localhost:3000"
echo -e "  Database: ${GREEN}✓${NC} PostgreSQL (system) + Redis (Docker)"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:  ${YELLOW}tail -f backend.log${NC}"
echo -e "  Frontend: ${YELLOW}tail -f frontend.log${NC}"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo -e "  ${YELLOW}bash stop-admin-system.sh${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Now try logging in to the admin panel!"
echo ""
