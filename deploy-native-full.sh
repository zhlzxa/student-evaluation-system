#!/bin/bash

set -e

DOMAIN="studentreview.uksouth.cloudapp.azure.com"
EMAIL="your-email@example.com"  # Change this to your email

echo "Student Evaluation System - Full Native Backend Deployment with HTTPS"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root for security reasons."
   echo "Please run as a regular user with sudo privileges."
   exit 1
fi

# Install Certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt update
    sudo apt install certbot python3-certbot-nginx -y
fi

# Check environment file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Creating from example..."
    cp .env.example .env
    echo "Created .env file. Please configure the settings."
    echo "IMPORTANT: You need to configure Azure AI and Document Intelligence settings in .env"
    read -p "Press Enter after configuring .env file..."
fi

# Stop existing containerized services
echo "Stopping existing containerized services..."
docker-compose down

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

# Start base services (database, Redis)
echo "Starting database and Redis services..."
docker-compose up -d db redis

# Wait for database to be fully ready
echo "Waiting for database to be fully ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
cd backend
python3 -m alembic upgrade head

# Initialize database and seed data
echo "Initializing database and seeding data..."
if python3 scripts/seed_all.py; then
    echo "Database seeding completed successfully"
else
    echo "Database seeding failed. Check the error above."
    echo "You can try running the seeding manually with:"
    echo "cd backend && python3 scripts/seed_all.py"
    echo "Continuing with deployment..."
fi

cd ..

# Start frontend and nginx with HTTP first
echo "Starting frontend and nginx services..."
docker-compose up -d frontend nginx

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Create webroot for certbot
echo "Creating webroot for Let's Encrypt..."
sudo mkdir -p /var/www/certbot

# Check if SSL certificate already exists
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "SSL certificate already exists for $DOMAIN"
    echo "Certificate will be used for HTTPS configuration"
    CERT_EXISTS=true
else
    echo "No existing SSL certificate found for $DOMAIN"
    CERT_EXISTS=false
fi

# Obtain SSL certificate if it doesn't exist
if [ "$CERT_EXISTS" = false ]; then
    echo "Obtaining SSL certificate for $DOMAIN..."
    if sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive; then
        echo "SSL certificate obtained successfully!"
        CERT_EXISTS=true
    else
        echo "Failed to obtain SSL certificate. Please check:"
        echo "1. Domain $DOMAIN points to this server's IP"
        echo "2. Port 80 is accessible from the internet"
        echo "3. Nginx is running and serving /.well-known/acme-challenge/"
        echo "Continuing with HTTP-only deployment..."
        CERT_EXISTS=false
    fi
fi

# Configure HTTPS if certificate exists
if [ "$CERT_EXISTS" = true ]; then
    echo "Configuring HTTPS..."

    # Stop nginx to update configuration
    docker-compose stop nginx

    # Backup current nginx.conf if it's not already HTTPS
    if ! grep -q "ssl_certificate" nginx.conf; then
        cp nginx.conf nginx-http.conf.backup
    fi

    # Update nginx configuration for HTTPS (nginx.conf should already be HTTPS-ready)
    echo "Using HTTPS-enabled nginx configuration..."

    # Start nginx with HTTPS configuration
    docker-compose up -d nginx

    # Set up automatic certificate renewal
    echo "Setting up automatic certificate renewal..."
    if ! sudo crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose -f $(pwd)/docker-compose.yml restart nginx'") | sudo crontab -
        echo "Automatic certificate renewal configured"
    fi
fi

# Azure CLI authentication prompt
echo ""
echo "=== IMPORTANT: Azure Authentication Required ==="
echo "Please run 'az login' to authenticate with Azure..."
echo "After authentication, start the backend services with:"
echo "sudo systemctl enable student-evaluation-backend"
echo "sudo systemctl enable student-evaluation-celery"
echo "sudo systemctl start student-evaluation-backend"
echo "sudo systemctl start student-evaluation-celery"
echo ""

# Service management commands
echo "=== Service Management Commands ==="
echo "Check backend status: sudo systemctl status student-evaluation-backend"
echo "Check celery status: sudo systemctl status student-evaluation-celery"
echo "View backend logs: sudo journalctl -u student-evaluation-backend -f"
echo "View celery logs: sudo journalctl -u student-evaluation-celery -f"
echo ""

# Display final URLs
if [ "$CERT_EXISTS" = true ]; then
    echo "=== Deployment Completed with HTTPS ==="
    echo "Frontend URL: https://$DOMAIN"
    echo "Backend API URL: https://$DOMAIN/api"
    echo "Health Check: https://$DOMAIN/api/health"
    echo "HTTP traffic will be automatically redirected to HTTPS"
else
    echo "=== Deployment Completed (HTTP Only) ==="
    echo "Frontend URL: http://$DOMAIN"
    echo "Backend API URL: http://$DOMAIN/api"
    echo "Health Check: http://$DOMAIN/api/health"
    echo ""
    echo "To enable HTTPS later, run:"
    echo "sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos"
    echo "Then restart nginx: docker-compose restart nginx"
fi

echo ""
echo "=== Next Steps ==="
echo "1. Run: az login"
echo "2. Run: sudo systemctl start student-evaluation-backend"
echo "3. Run: sudo systemctl start student-evaluation-celery"
echo "4. Check health: curl $([ "$CERT_EXISTS" = true ] && echo "https" || echo "http")://$DOMAIN/api/health"