# Stratum Platform - Local Development Setup Guide

Complete guide to set up the Stratum trading platform on your local machine.

## Prerequisites

Before starting, ensure you have these installed:

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Python** (v3.11 or higher) - [Download](https://www.python.org/downloads/)
- **PostgreSQL** (v14 or higher) - [Download](https://www.postgresql.org/download/)
- **Redis** (v6 or higher) - [Download](https://redis.io/download/)
- **Git** - [Download](https://git-scm.com/downloads/)

### Quick Check

Run these commands to verify installations:

```bash
node --version    # Should show v18.x.x or higher
python --version  # Should show Python 3.11.x or higher
psql --version    # Should show PostgreSQL 14.x or higher
redis-server --version  # Should show Redis 6.x or higher
git --version     # Should show git version 2.x.x or higher
```

## Automated Setup (Recommended)

We've provided an automated setup script that handles everything:

```bash
# Clone the repository
git clone https://github.com/rraushan1205/stratum.git
cd stratum

# Make the setup script executable
chmod +x setup-dev.sh

# Run the setup script
./setup-dev.sh
```

The script will:
1. ✅ Check all prerequisites
2. ✅ Set up PostgreSQL database
3. ✅ Start Redis server
4. ✅ Create Python virtual environment
5. ✅ Install backend dependencies
6. ✅ Run database migrations
7. ✅ Create admin user
8. ✅ Install frontend dependencies
9. ✅ Create environment files
10. ✅ Start both servers

**Skip to the [Testing](#testing-the-setup) section after running the script!**

---

## Manual Setup (Step-by-Step)

If you prefer to set up manually or the script fails, follow these detailed steps:

### Step 1: Clone the Repository

```bash
git clone https://github.com/rraushan1205/stratum.git
cd stratum
```

### Step 2: Set Up PostgreSQL Database

#### On macOS (using Homebrew):
```bash
# Start PostgreSQL service
brew services start postgresql@14

# Create database and user
psql postgres -c "CREATE DATABASE stratum;"
psql postgres -c "CREATE USER stratum WITH PASSWORD 'stratum';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE stratum TO stratum;"
psql postgres -c "ALTER USER stratum CREATEDB;"
```

#### On Ubuntu/Debian:
```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE stratum;"
sudo -u postgres psql -c "CREATE USER stratum WITH PASSWORD 'stratum';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE stratum TO stratum;"
sudo -u postgres psql -c "ALTER USER stratum CREATEDB;"
```

#### On Windows:
```bash
# Open SQL Shell (psql) and run:
CREATE DATABASE stratum;
CREATE USER stratum WITH PASSWORD 'stratum';
GRANT ALL PRIVILEGES ON DATABASE stratum TO stratum;
ALTER USER stratum CREATEDB;
```

### Step 3: Set Up Redis

#### On macOS:
```bash
brew services start redis
```

#### On Ubuntu/Debian:
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### On Windows:
Download and install from: https://redis.io/download/
Or use WSL (Windows Subsystem for Linux)

### Step 4: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env file with your configuration
# Default values should work for local development
```

**Backend .env Configuration:**
```env
DATABASE_URL=postgresql+psycopg://stratum:stratum@localhost:5432/stratum
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=2c9201438b5454a320c0a6a0b9f539c4af37918f44498cb9cdd9e9c352bcda94
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=480
COOKIE_SECURE=false
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeMe123!
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:3002"]
STRATEGY_STORAGE_PATH=./storage/strategies
TRADING_ENGINE_URL=
```

### Step 5: Run Database Migrations

```bash
# Still in backend directory with venv activated
alembic upgrade head
```

This creates all necessary database tables.

### Step 6: Start Backend Server

```bash
# Still in backend directory
python -m uvicorn app.main:app --reload
```

Backend should now be running at: http://localhost:8000

**Keep this terminal open!**

### Step 7: Frontend Setup

Open a **NEW terminal window/tab**:

```bash
# Navigate to project root
cd stratum

# Install Node.js dependencies
npm install

# Create .env.local file
cp .env.local.example .env.local
```

**Frontend .env.local Configuration:**
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
JWT_SECRET_KEY=2c9201438b5454a320c0a6a0b9f539c4af37918f44498cb9cdd9e9c352bcda94
```

### Step 8: Start Frontend Server

```bash
npm run dev
```

Frontend should start at: http://localhost:3000

**If port 3000 is in use, Next.js will automatically use the next available port (3001, 3002, etc.)**

## Testing the Setup

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### 2. Access Admin Panel

1. Open browser: http://localhost:3000/admin/login
2. Login with:
   - Email: `admin@example.com`
   - Password: `ChangeMe123!`
3. You should see the Admin Dashboard

### 3. Test User Registration

1. Open: http://localhost:3000/register
2. Create a new account
3. Login as admin and approve the user
4. Login as the new user

### 4. Test Strategy Upload (Admin)

1. Login as admin
2. Go to: http://localhost:3000/admin/strategies
3. Upload a Python file (.py)
4. Verify it appears in the list

### 5. Test User Marketplace

1. Login as regular user
2. Go to: http://localhost:3000/dashboard/marketplace
3. You should see the strategy uploaded by admin
4. Test Download and View Code buttons

## Project Structure

```
stratum/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core functionality
│   │   ├── db/             # Database setup
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── alembic/            # Database migrations
│   ├── storage/            # File storage
│   │   └── strategies/     # Uploaded strategy files
│   ├── tests/              # Backend tests
│   ├── .env                # Backend config
│   └── requirements.txt    # Python dependencies
│
├── src/                    # Next.js frontend
│   ├── app/                # App routes
│   │   ├── admin/          # Admin panel routes
│   │   └── dashboard/      # User dashboard routes
│   ├── components/         # Shared components
│   ├── features/           # Feature modules
│   │   ├── admin/          # Admin features
│   │   └── dashboard/      # Dashboard features
│   └── lib/                # Utilities
│
├── .env.local              # Frontend config
├── package.json            # Node dependencies
└── README.md               # Project readme
```

## Common Issues & Solutions

### Issue: PostgreSQL Connection Failed

**Error**: `could not connect to server: Connection refused`

**Solution**:
```bash
# Check if PostgreSQL is running
# macOS:
brew services list | grep postgresql

# Linux:
sudo systemctl status postgresql

# Start if not running:
brew services start postgresql@14        # macOS
sudo systemctl start postgresql          # Linux
```

### Issue: Redis Connection Failed

**Error**: `Error connecting to Redis`

**Solution**:
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running:
brew services start redis                # macOS
sudo systemctl start redis-server        # Linux
```

### Issue: Port Already in Use

**Error**: `Error: listen EADDRINUSE: address already in use`

**Solution**:
```bash
# Find process using the port (e.g., port 3000)
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use a different port:
PORT=3001 npm run dev
```

### Issue: Database Migration Fails

**Error**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solution**:
```bash
cd backend
source venv/bin/activate

# Check current migration
alembic current

# Upgrade to latest
alembic upgrade head

# If still failing, reset database:
alembic downgrade base
alembic upgrade head
```

### Issue: Module Not Found (Python)

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Make sure venv is activated
source backend/venv/bin/activate  # macOS/Linux
backend\venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Issue: npm install fails

**Error**: `npm ERR! code ERESOLVE`

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and lock file
rm -rf node_modules package-lock.json

# Reinstall
npm install

# If still failing, try legacy peer deps:
npm install --legacy-peer-deps
```

### Issue: CORS Errors in Browser

**Error**: `Access to fetch at 'http://localhost:8000' from origin 'http://localhost:3001' has been blocked by CORS`

**Solution**:
Update `backend/.env`:
```env
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:3002"]
```

Then restart backend server.

### Issue: Admin Cannot Login

**Checklist**:
1. ✅ Database migrations run? `alembic upgrade head`
2. ✅ Admin user created? (automatic on first backend start)
3. ✅ Using correct credentials? (from backend/.env)
4. ✅ Backend running? Check http://localhost:8000/health

**Manually create admin**:
```bash
cd backend
source venv/bin/activate
python -c "from app.db.session import SessionLocal; from app.services.admin_bootstrap import ensure_initial_super_admin; ensure_initial_super_admin(SessionLocal())"
```

## Development Workflow

### Starting Development

**Terminal 1 - Backend**:
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend**:
```bash
npm run dev
```

**Terminal 3 - Optional (Database CLI)**:
```bash
psql -U stratum -d stratum
```

### Stopping Services

```bash
# Stop frontend: Ctrl+C in terminal
# Stop backend: Ctrl+C in terminal

# Stop PostgreSQL (optional):
brew services stop postgresql@14        # macOS
sudo systemctl stop postgresql          # Linux

# Stop Redis (optional):
brew services stop redis                # macOS
sudo systemctl stop redis-server        # Linux
```

### Making Changes

**Backend Changes**:
- Edit files in `backend/app/`
- Server auto-reloads (watch terminal for errors)
- Test endpoint: `curl http://localhost:8000/your-endpoint`

**Frontend Changes**:
- Edit files in `src/`
- Next.js auto-reloads in browser
- Check browser console for errors

**Database Changes**:
```bash
cd backend
source venv/bin/activate

# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migration
alembic upgrade head
```

## API Documentation

Once backend is running, access interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Backend Tests
```bash
cd backend
source venv/bin/activate
pytest
```

### Frontend Tests
```bash
npm test
```

## Additional Resources

- **Backend Documentation**: See `backend/README.md`
- **API Integration Guide**: See `DASHBOARD_API_INTEGRATION.md`
- **Strategy Distribution**: See `STRATEGY_FILE_DISTRIBUTION.md`
- **Admin Panel Guide**: See `ADMIN_PANEL_STATUS.md`

## Getting Help

If you encounter issues:

1. **Check logs**:
   - Backend: Terminal where uvicorn is running
   - Frontend: Browser console (F12)
   - Database: Check PostgreSQL logs

2. **Verify services**:
   ```bash
   # PostgreSQL
   psql -U stratum -d stratum -c "SELECT 1;"
   
   # Redis
   redis-cli ping
   
   # Backend
   curl http://localhost:8000/health
   ```

3. **Common fixes**:
   - Restart all services
   - Clear caches (`npm cache clean --force`)
   - Recreate virtual environment
   - Drop and recreate database

4. **Report issues**: Create an issue on GitHub with:
   - Your OS and versions
   - Error messages
   - Steps to reproduce

## Next Steps

After successful setup:

1. ✅ Familiarize yourself with the codebase structure
2. ✅ Read the API documentation
3. ✅ Test all features (admin panel, user dashboard, marketplace)
4. ✅ Set up your IDE (VSCode recommended)
5. ✅ Install recommended VSCode extensions:
   - Python
   - Pylance
   - ESLint
   - Prettier
   - Tailwind CSS IntelliSense

Happy coding! 🚀
