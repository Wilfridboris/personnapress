#!/usr/bin/env bash
set -euo pipefail

DROPLET_IP="${DROPLET_IP:?DROPLET_IP env var must be set}"
SSH_USER="${SSH_USER:-root}"

echo "Deploying PersonnaPress API to $SSH_USER@$DROPLET_IP..."

ssh "$SSH_USER@$DROPLET_IP" bash -s << 'REMOTE'
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
