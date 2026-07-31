#!/bin/bash

# Script to run Alembic database migrations

echo "Running database migrations..."

# Try different Python commands
if command -v python3 &> /dev/null; then
    echo "Using python3..."
    cd "$(dirname "$0")" && python3 -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('alembic.ini'); command.upgrade(alembic_cfg, 'head')"
elif command -v python &> /dev/null; then
    echo "Using python..."
    cd "$(dirname "$0")" && python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('alembic.ini'); command.upgrade(alembic_cfg, 'head')"
else
    echo "Error: Python not found. Please install Python 3.x"
    exit 1
fi

echo "Migration complete!"
