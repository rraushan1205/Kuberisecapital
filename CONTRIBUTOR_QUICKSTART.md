# Stratum Platform - Contributor Quick Start 🚀

Welcome to the Stratum Trading Platform! This guide will get you up and running in minutes.

## 📋 What You'll Need

Before starting, install these tools on your laptop:

1. **Node.js** (v18+) - https://nodejs.org/
2. **Python** (v3.11+) - https://www.python.org/downloads/
3. **PostgreSQL** (v14+) - https://www.postgresql.org/download/
4. **Redis** (v6+) - https://redis.io/download/
5. **Git** - https://git-scm.com/downloads/

**Quick verification:**
```bash
node --version && python --version && psql --version && redis-cli --version
```

## 🎯 3-Step Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/rraushan1205/stratum.git
cd stratum
```

### Step 2: Run Automated Setup

```bash
chmod +x setup-dev.sh
./setup-dev.sh
```

This script automatically:
- ✅ Checks all prerequisites
- ✅ Sets up PostgreSQL database
- ✅ Starts Redis
- ✅ Creates Python virtual environment
- ✅ Installs all dependencies (backend & frontend)
- ✅ Runs database migrations
- ✅ Creates admin user
- ✅ Configures environment variables

**Takes ~2-5 minutes depending on your internet speed.**

### Step 3: Start Development Servers

```bash
./start-dev.sh
```

This starts both backend and frontend servers in the background.

**That's it!** 🎉

## 🌐 Access the Application

Open your browser:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔐 Login Credentials

### Admin Panel
- **URL**: http://localhost:3000/admin/login
- **Email**: `admin@example.com`
- **Password**: `ChangeMe123!`

### Test User Account
You can create test users through registration, or use the admin panel to approve accounts.

## 📁 Project Structure

```
stratum/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST API endpoints
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   └── core/        # Security, config
│   └── alembic/         # Database migrations
│
├── src/                 # Next.js frontend
│   ├── app/            # Pages and routes
│   │   ├── admin/      # Admin panel
│   │   └── dashboard/  # User dashboard
│   ├── components/     # Reusable UI components
│   └── features/       # Feature modules
│
├── setup-dev.sh        # Automated setup script
├── start-dev.sh        # Server startup script
└── SETUP_GUIDE.md      # Detailed setup guide
```

## 🛠️ Development Workflow

### Starting Development

**Option 1: Using the helper script (Recommended)**
```bash
./start-dev.sh
```

**Option 2: Manual (separate terminals)**

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

Terminal 2 - Frontend:
```bash
npm run dev
```

### Stopping Servers

If using `start-dev.sh`: Press `Ctrl+C`

If manual: Press `Ctrl+C` in each terminal

### Making Changes

**Backend changes:**
- Edit files in `backend/app/`
- Server auto-reloads
- Check terminal for errors

**Frontend changes:**
- Edit files in `src/`
- Browser auto-refreshes
- Check browser console for errors

**Database changes:**
```bash
cd backend
source venv/bin/activate

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## 🧪 Testing Your Setup

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### 2. Test Admin Login
1. Go to http://localhost:3000/admin/login
2. Login with admin credentials
3. Explore admin dashboard

### 3. Test User Flow
1. Go to http://localhost:3000/register
2. Create a test account
3. Login as admin and approve the account
4. Login as the test user
5. Explore user dashboard

### 4. Test Strategy Distribution
1. Login as admin
2. Go to Strategies section
3. Upload a `.py` file
4. Login as regular user
5. Check Marketplace - your strategy should appear!

## 📚 Key Features You Can Work On

### Admin Panel
- **User Management**: Approve/reject registrations
- **Strategy Upload**: Upload Python trading strategies
- **Execution Logs**: Monitor system activity
- **Announcements**: Broadcast messages
- **Connected Users**: Track live broker connections

### User Dashboard
- **Marketplace**: Browse and download strategies
- **Broker Connection**: Connect to trading platforms
- **Portfolio Overview**: View trading performance
- **Settings**: Manage account preferences

## 🐛 Common Issues & Fixes

### Issue: Scripts won't run
```bash
# Make them executable
chmod +x setup-dev.sh start-dev.sh
```

### Issue: Port already in use
```bash
# Find and kill process
lsof -i :3000  # or :8000 for backend
kill -9 <PID>
```

### Issue: Database connection failed
```bash
# Start PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

### Issue: Redis connection failed
```bash
# Start Redis
brew services start redis       # macOS
sudo systemctl start redis      # Linux
```

### Issue: Module not found (Python)
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: npm install fails
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

## 📖 Documentation

- **Setup Guide**: [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Detailed manual setup
- **Admin Panel**: [ADMIN_PANEL_STATUS.md](./ADMIN_PANEL_STATUS.md) - Admin features guide
- **Strategy System**: [STRATEGY_FILE_DISTRIBUTION.md](./STRATEGY_FILE_DISTRIBUTION.md) - How strategies work
- **API Integration**: [DASHBOARD_API_INTEGRATION.md](./DASHBOARD_API_INTEGRATION.md) - API docs

## 🔧 Useful Commands

```bash
# View logs
tail -f backend.log    # Backend logs
tail -f frontend.log   # Frontend logs

# Database CLI
psql -U stratum -d stratum

# Redis CLI
redis-cli

# Run tests
cd backend && pytest   # Backend tests
npm test              # Frontend tests

# Check running processes
lsof -i :8000         # Backend
lsof -i :3000         # Frontend
```

## 🎨 Tech Stack

**Backend:**
- FastAPI (Python web framework)
- PostgreSQL (Database)
- Redis (Caching)
- SQLAlchemy (ORM)
- Alembic (Migrations)
- JWT (Authentication)

**Frontend:**
- Next.js 15 (React framework)
- TypeScript
- TanStack Query (Data fetching)
- Tailwind CSS (Styling)
- Lucide Icons

## 🤝 Contributing Guidelines

1. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and test thoroughly

3. **Commit with clear messages**:
   ```bash
   git commit -m "Add: feature description"
   ```

4. **Push to your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub

## 💡 Tips for Success

1. **Always activate the virtual environment** when working with backend:
   ```bash
   cd backend
   source venv/bin/activate
   ```

2. **Check logs when something breaks**:
   - Backend: Terminal or `backend.log`
   - Frontend: Browser console (F12)

3. **Use API documentation** at http://localhost:8000/docs for testing endpoints

4. **Keep dependencies updated**:
   ```bash
   pip install --upgrade -r backend/requirements.txt
   npm update
   ```

5. **Run migrations after pulling changes**:
   ```bash
   cd backend && alembic upgrade head
   ```

## 🎯 Your First Task Ideas

### Easy (Good for starting)
- [ ] Fix UI styling issues
- [ ] Add loading spinners
- [ ] Improve error messages
- [ ] Add form validation

### Medium
- [ ] Create new dashboard widgets
- [ ] Add filtering to data tables
- [ ] Implement search functionality
- [ ] Add export to CSV features

### Advanced
- [ ] Integrate new broker APIs
- [ ] Implement real-time WebSocket updates
- [ ] Add backtesting features
- [ ] Create advanced analytics

## 🆘 Need Help?

1. **Check documentation** in this repo
2. **Review existing code** for patterns
3. **Check backend logs** for API errors
4. **Use browser DevTools** for frontend debugging
5. **Ask questions** - create an issue on GitHub

## 🎉 You're Ready!

You now have:
- ✅ Complete development environment
- ✅ Running backend and frontend
- ✅ Admin access
- ✅ Understanding of project structure
- ✅ Knowledge of common tasks

**Start exploring the codebase and happy coding!** 🚀

---

**Quick Reference:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Admin: http://localhost:3000/admin/login
- API Docs: http://localhost:8000/docs

**Admin Credentials:**
- Email: `admin@example.com`
- Password: `ChangeMe123!`
