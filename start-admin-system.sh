#!/bin/bash

# Comprehensive startup script for the admin panel system
# This will check dependencies, start services, and provide clear status

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Admin Panel System Startup Script           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    lsof -i :"$1" > /dev/null 2>&1
    return $?
}

# Step 1: Check Docker
echo -e "${YELLOW}[1/5]${NC} Checking Docker status..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗${NC} Docker is not installed!"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo -e "${RED}✗${NC} Docker daemon is not running!"
    echo "Please start Docker Desktop application"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is running"
echo ""

# Step 2: Start Database Services
echo -e "${YELLOW}[2/5]${NC} Starting database services..."

POSTGRES_RUNNING=$(docker ps --filter "name=postgres" --filter "status=running" -q)
REDIS_RUNNING=$(docker ps --filter "name=redis" --filter "status=running" -q)

if [ -z "$POSTGRES_RUNNING" ] || [ -z "$REDIS_RUNNING" ]; then
    echo "Starting PostgreSQL and Redis containers..."
    docker-compose up -d postgres redis
    echo "Waiting for databases to be ready..."
    sleep 5
else
    echo -e "${GREEN}✓${NC} Database services already running"
fi

echo ""

# Step 3: Check and Run Migrations
echo -e "${YELLOW}[3/5]${NC} Checking database migrations..."
cd backend

# Check if alembic has been run
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
    echo -e "${YELLOW}⚠${NC} No migrations found. This might be a first-time setup."
fi

# Check current migration status
CURRENT_MIGRATION=$(alembic current 2>&1 || echo "none")
if [[ "$CURRENT_MIGRATION" == *"none"* ]] || [[ "$CURRENT_MIGRATION" == *"Can't locate revision"* ]]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo -e "${GREEN}✓${NC} Migrations completed"
else
    echo -e "${GREEN}✓${NC} Database is up to date"
fi

cd ..
echo ""

# Step 4: Start Backend
echo -e "${YELLOW}[4/5]${NC} Starting backend API..."

if check_port 8000; then
    echo -e "${GREEN}✓${NC} Backend is already running on port 8000"
else
    echo "Starting backend server..."
    echo -e "${BLUE}→${NC} Backend will run in the background"
    echo -e "${BLUE}→${NC} Watch for admin user creation message!"
    echo ""
    
    cd backend
    # Start backend in background
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
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
        echo -e "${RED}✗${NC} Backend failed to start. Check backend.log for errors"
        cat backend.log
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

echo ""

# Step 5: Start Frontend
echo -e "${YELLOW}[5/5]${NC} Starting frontend..."

if check_port 3000; then
    echo -e "${GREEN}✓${NC} Frontend is already running on port 3000"
else
    echo "Starting Next.js development server..."
    echo -e "${BLUE}→${NC} Frontend will run in the background"
    
    # Start frontend in background
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
        echo -e "${RED}✗${NC} Frontend failed to start. Check frontend.log for errors"
        cat frontend.log
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
echo -e "  Backend:  ${GREEN}✓${NC} http://localhost:8000 (API docs: http://localhost:8000/docs)"
echo -e "  Frontend: ${GREEN}✓${NC} http://localhost:3000"
echo -e "  Database: ${GREEN}✓${NC} PostgreSQL + Redis running"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:  ${YELLOW}tail -f backend.log${NC}"
echo -e "  Frontend: ${YELLOW}tail -f frontend.log${NC}"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo -e "  ${YELLOW}bash stop-admin-system.sh${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Change the default admin password after first login!"
echo ""
