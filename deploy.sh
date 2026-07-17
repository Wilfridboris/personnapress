#!/usr/bin/env bash
set -euo pipefail
# Deploy runbook: after first deploy with spacy in requirements.txt, run once on the server:
# python -m spacy download en_core_web_sm

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

echo "Waiting for service to become active (up to 15s)..."
SERVICE_UP=0
for i in 1 2 3 4 5; do
    sleep 3
    if sudo systemctl is-active --quiet personnapress-api; then
        SERVICE_UP=1
        break
    fi
    echo "  attempt $i/5 — not active yet..."
done

if [ "$SERVICE_UP" -eq 0 ]; then
    echo "ERROR: Service failed to start after 15s!" >&2
    echo "--- systemctl status ---"
    sudo systemctl status personnapress-api --no-pager -l || true
    echo "--- Last 50 log lines ---"
    sudo journalctl -u personnapress-api -n 50 --no-pager || true
    exit 1
fi

echo "Service is running. Last 20 log lines:"
sudo journalctl -u personnapress-api -n 20 --no-pager

echo "Deploy complete."
REMOTE
