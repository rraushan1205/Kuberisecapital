#!/bin/bash

# Admin Panel Connection Flow Verification Script
# This script verifies that all components of the admin panel are properly configured

echo "🔍 Verifying Admin Panel Connection Flow..."
echo "=============================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Environment Files
echo "📋 Step 1: Checking Environment Configuration"
echo "----------------------------------------------"

if [ -f ".env.local" ]; then
    echo -e "${GREEN}✓${NC} Frontend .env.local exists"
    if grep -q "NEXT_PUBLIC_API_BASE_URL" .env.local && grep -q "JWT_SECRET_KEY" .env.local; then
        echo -e "${GREEN}✓${NC} Frontend environment variables configured"
    else
        echo -e "${RED}✗${NC} Frontend environment variables incomplete"
    fi
else
    echo -e "${RED}✗${NC} Frontend .env.local missing"
fi

if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓${NC} Backend .env exists"
    if grep -q "JWT_SECRET_KEY" backend/.env && grep -q "DATABASE_URL" backend/.env; then
        echo -e "${GREEN}✓${NC} Backend environment variables configured"
    else
        echo -e "${RED}✗${NC} Backend environment variables incomplete"
    fi
else
    echo -e "${RED}✗${NC} Backend .env missing"
fi

echo ""

# Check 2: Database Services
echo "🗄️  Step 2: Checking Database & Services"
echo "----------------------------------------------"

# Check if PostgreSQL is running
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL is running"
    else
        echo -e "${YELLOW}⚠${NC} PostgreSQL is not accessible on localhost:5432"
    fi
else
    echo -e "${YELLOW}⚠${NC} pg_isready not found, cannot verify PostgreSQL"
fi

# Check if Redis is running
if command -v redis-cli &> /dev/null; then
    if redis-cli -h localhost -p 6379 ping &> /dev/null; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}⚠${NC} Redis is not accessible on localhost:6379"
    fi
else
    echo -e "${YELLOW}⚠${NC} redis-cli not found, cannot verify Redis"
fi

# Check Docker containers if docker-compose is used
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} Docker Compose configuration exists"
    if command -v docker &> /dev/null; then
        POSTGRES_RUNNING=$(docker ps --filter "name=postgres" --filter "status=running" -q)
        REDIS_RUNNING=$(docker ps --filter "name=redis" --filter "status=running" -q)
        
        if [ ! -z "$POSTGRES_RUNNING" ]; then
            echo -e "${GREEN}✓${NC} PostgreSQL container is running"
        else
            echo -e "${YELLOW}⚠${NC} PostgreSQL container is not running"
            echo -e "   ${YELLOW}→${NC} Run: docker-compose up -d postgres"
        fi
        
        if [ ! -z "$REDIS_RUNNING" ]; then
            echo -e "${GREEN}✓${NC} Redis container is running"
        else
            echo -e "${YELLOW}⚠${NC} Redis container is not running"
            echo -e "   ${YELLOW}→${NC} Run: docker-compose up -d redis"
        fi
    fi
fi

echo ""

# Check 3: Key Files
echo "📁 Step 3: Verifying Key Files"
echo "----------------------------------------------"

CRITICAL_FILES=(
    "src/app/admin/login/page.tsx"
    "src/app/admin/(portal)/layout.tsx"
    "src/app/admin/(portal)/dashboard/page.tsx"
    "src/features/admin/api/admin-api.ts"
    "src/features/admin/components/admin-login-form.tsx"
    "src/features/admin/components/admin-shell.tsx"
    "src/middleware.ts"
    "backend/app/api/admin.py"
    "backend/app/api/dependencies.py"
    "backend/app/core/security.py"
    "backend/app/services/admin_bootstrap.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file (MISSING)"
    fi
done

echo ""

# Check 4: Admin Credentials
echo "🔐 Step 4: Admin Credentials"
echo "----------------------------------------------"

if [ -f "backend/.env" ]; then
    ADMIN_EMAIL=$(grep "ADMIN_EMAIL" backend/.env | cut -d '=' -f2)
    ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD" backend/.env | cut -d '=' -f2)
    
    echo -e "${GREEN}✓${NC} Admin credentials configured:"
    echo "   Email: $ADMIN_EMAIL"
    echo "   Password: $ADMIN_PASSWORD"
    echo ""
    echo -e "   ${YELLOW}Note:${NC} Change these credentials after first login!"
fi

echo ""

# Summary and Next Steps
echo "📝 Summary & Next Steps"
echo "=============================================="
echo ""
echo "To access the admin panel:"
echo ""
echo "1. Start database services:"
echo "   ${YELLOW}docker-compose up -d postgres redis${NC}"
echo ""
echo "2. Run database migrations:"
echo "   ${YELLOW}cd backend && alembic upgrade head${NC}"
echo ""
echo "3. Start the backend API:"
echo "   ${YELLOW}cd backend && uvicorn app.main:app --reload${NC}"
echo "   (Backend will auto-create admin user on first start)"
echo ""
echo "4. Start the frontend:"
echo "   ${YELLOW}npm run dev${NC}"
echo ""
echo "5. Access admin login:"
echo "   ${YELLOW}http://localhost:3000/admin/login${NC}"
echo ""
echo "6. Login with credentials from backend/.env:"
echo "   Email: ${ADMIN_EMAIL:-admin@example.com}"
echo "   Password: ${ADMIN_PASSWORD:-ChangeMe123!}"
echo ""
echo "=============================================="
