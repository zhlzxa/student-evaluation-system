#!/bin/bash

echo "Student Evaluation System - Minimal Native Backend Deployment (No Seed Data)"

# Check and install pip3 if needed
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip3..."
    sudo apt update && sudo apt install -y python3-pip
fi

# Stop existing containerized services
echo "Stopping existing containerized services..."
docker-compose down

# Clean up orphan containers
echo "Cleaning up orphan containers..."
docker-compose down --remove-orphans

# Install Python dependencies
echo "Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt
cd ..

# Install and configure systemd services
echo "Setting up systemd services..."
sudo cp student-evaluation-backend.service /etc/systemd/system/
sudo cp student-evaluation-celery.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start base services (database, Redis, frontend, Nginx)
echo "Starting containerized services (DB, Redis, Frontend, Nginx)..."
docker-compose up -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

# Run database migrations only (no seed data)
echo "Running database migrations..."
cd backend
if ! /home/UCLIXN/.local/bin/alembic upgrade head 2>/dev/null; then
    echo "Note: Database migrations may already be applied or encountered an issue."
    echo "This is normal if database already exists."
fi
cd ..

echo ""
echo "=== MINIMAL DEPLOYMENT COMPLETED ==="
echo "NOTE: No seed data was loaded. Database contains only schema."
echo ""
echo "=== IMPORTANT: Azure Authentication Required ==="
echo "Please run 'az login' to authenticate with Azure..."
echo "After authentication, start the backend services with:"
echo "sudo systemctl enable student-evaluation-backend"
echo "sudo systemctl enable student-evaluation-celery"
echo "sudo systemctl start student-evaluation-backend"
echo "sudo systemctl start student-evaluation-celery"
echo ""
echo "=== To Load Seed Data Later ==="
echo "cd backend && python3 scripts/seed_all.py"
echo ""
echo "=== Service Management Commands ==="
echo "Check backend status: sudo systemctl status student-evaluation-backend"
echo "Check celery status: sudo systemctl status student-evaluation-celery"
echo "View backend logs: sudo journalctl -u student-evaluation-backend -f"
echo "View celery logs: sudo journalctl -u student-evaluation-celery -f"