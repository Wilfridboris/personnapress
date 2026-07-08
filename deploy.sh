#!/usr/bin/env bash
set -euo pipefail

echo "Deploying PersonnaPress API to 134.209.72.22..."

ssh -i /c/Users/boris/.ssh/personapress_key root@134.209.72.22 bash -s << 'REMOTE'
set -euo pipefail
cd /var/www/personnapress

echo "Pulling latest code..."
git pull origin main

echo "Installing Python dependencies..."
VENV_PATH="/var/www/personnapress/.venv"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi
"$VENV_PATH/bin/pip" install --quiet -r backend/requirements.txt

echo "Running database migrations..."
cd backend
"$VENV_PATH/bin/alembic" upgrade head
cd ..

echo "Restarting API service..."
sudo systemctl restart personnapress-api

echo "Deploy complete."
REMOTE
