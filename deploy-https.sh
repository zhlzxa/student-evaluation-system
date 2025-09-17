#!/bin/bash

# HTTPS deployment script for Student Admission Review System

set -e

DOMAIN="studentreview.uksouth.cloudapp.azure.com"
EMAIL="your-email@example.com"  # Change this to your email

echo "Starting HTTPS deployment for $DOMAIN..."

# Check if running as root (needed for certbot)
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root for security reasons."
   echo "Please run as a regular user with sudo privileges."
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
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

# Load environment variables for validation
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Basic environment validation
echo "Validating environment configuration..."
missing_vars=""

# Check critical Azure settings
if [ -z "$AZURE_AI_AGENT_ENDPOINT" ]; then
    missing_vars="$missing_vars AZURE_AI_AGENT_ENDPOINT"
fi

if [ -z "$AZURE_DI_ENDPOINT" ]; then
    missing_vars="$missing_vars AZURE_DI_ENDPOINT"
fi

if [ -z "$AZURE_DI_KEY" ]; then
    missing_vars="$missing_vars AZURE_DI_KEY"
fi

if [ -n "$missing_vars" ]; then
    echo "Warning: Missing critical environment variables:$missing_vars"
    echo "The application may not work properly without these settings."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled. Please configure the missing variables in .env"
        exit 1
    fi
fi

# Stop existing services
echo "Stopping existing services..."
docker-compose down

# Build images
echo "Building Docker images..."
docker-compose build

# Start database and Redis first
echo "Starting database services..."
docker-compose up -d db redis

echo "Waiting for database to be ready..."
sleep 10

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

# Initialize database and seed data
echo "Initializing database and seeding data..."
if docker-compose run --rm backend python scripts/seed_all.py; then
    echo "Database seeding completed successfully"
else
    echo "Database seeding failed. Check logs:"
    docker-compose logs backend
    echo "You can try running the seeding manually with:"
    echo "docker-compose run --rm backend python scripts/seed_all.py"
    echo "Continuing with deployment..."
fi

# Start application services (but not nginx yet)
echo "Starting application services..."
docker-compose up -d backend celery frontend

# Wait for services to start
echo "Waiting for services to start..."
sleep 20

# Create webroot for certbot
echo "Creating webroot for Let's Encrypt..."
sudo mkdir -p /var/www/certbot

# Start nginx with basic HTTP configuration first
echo "Starting nginx with HTTP configuration..."
docker-compose up -d nginx

# Wait a bit for nginx to start
sleep 10

# Obtain SSL certificate
echo "Obtaining SSL certificate for $DOMAIN..."
if sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive; then
    echo "SSL certificate obtained successfully!"
else
    echo "Failed to obtain SSL certificate. Please check:"
    echo "1. Domain $DOMAIN points to this server's IP"
    echo "2. Port 80 is accessible from the internet"
    echo "3. Nginx is running and serving /.well-known/acme-challenge/"
    echo "Continuing with HTTP-only deployment..."

    # Check service status
    echo "Checking service status..."
    docker-compose ps

    # Health check
    echo "Running health check..."
    if curl -s http://localhost/api/health > /dev/null; then
        echo "Backend service is healthy"
    else
        echo "Backend service failed health check. Check logs:"
        docker-compose logs backend
    fi

    if curl -s http://localhost > /dev/null; then
        echo "Frontend service is healthy"
    else
        echo "Frontend service failed health check. Check logs:"
        docker-compose logs frontend
    fi

    echo ""
    echo "HTTP deployment completed!"
    echo "Frontend URL: http://$DOMAIN"
    echo "Backend API URL: http://$DOMAIN/api"
    echo ""
    echo "To retry HTTPS setup later, run:"
    echo "sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos"
    echo "Then replace nginx.conf with nginx-https.conf and restart nginx"
    exit 1
fi

# Stop nginx to replace configuration
echo "Stopping nginx to update configuration..."
docker-compose stop nginx

# Replace nginx configuration with HTTPS version
echo "Updating nginx configuration for HTTPS..."
cp nginx-https.conf nginx.conf

# Update docker-compose to mount certificate directory
echo "Updating docker-compose for SSL certificates..."
if ! grep -q "/etc/letsencrypt" docker-compose.yml; then
    # Create backup
    cp docker-compose.yml docker-compose.yml.backup

    # Add SSL volume mount to nginx service
    sed -i '/nginx:/,/restart: unless-stopped/ {
        /volumes:/a\
      - /etc/letsencrypt:/etc/letsencrypt:ro\
      - /var/www/certbot:/var/www/certbot:ro
    }' docker-compose.yml

    # If volumes section doesn't exist, add it
    if ! grep -q "volumes:" docker-compose.yml; then
        sed -i '/nginx:/,/restart: unless-stopped/ {
            /restart: unless-stopped/a\
    volumes:\
      - ./nginx.conf:/etc/nginx/nginx.conf:ro\
      - /etc/letsencrypt:/etc/letsencrypt:ro\
      - /var/www/certbot:/var/www/certbot:ro
        }' docker-compose.yml
    fi
fi

# Start nginx with HTTPS configuration
echo "Starting nginx with HTTPS configuration..."
docker-compose up -d nginx

# Wait for nginx to start
sleep 10

# Check service status
echo "Checking service status..."
docker-compose ps

# Health check
echo "Running health check..."
if curl -s -k https://$DOMAIN/api/health > /dev/null; then
    echo "Backend service is healthy (HTTPS)"
elif curl -s http://$DOMAIN/api/health > /dev/null; then
    echo "Backend service is healthy (HTTP redirect working)"
else
    echo "Backend service failed health check. Check logs:"
    docker-compose logs backend nginx
fi

if curl -s -k https://$DOMAIN > /dev/null; then
    echo "Frontend service is healthy (HTTPS)"
elif curl -s http://$DOMAIN > /dev/null; then
    echo "Frontend service is healthy (HTTP redirect working)"
else
    echo "Frontend service failed health check. Check logs:"
    docker-compose logs frontend nginx
fi

# Set up automatic certificate renewal
echo "Setting up automatic certificate renewal..."
if ! sudo crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose -f $(pwd)/docker-compose.yml restart nginx'") | sudo crontab -
    echo "Automatic certificate renewal configured"
fi

echo ""
echo "HTTPS deployment completed successfully!"
echo "Frontend URL: https://$DOMAIN"
echo "Backend API URL: https://$DOMAIN/api"
echo "HTTP traffic will be automatically redirected to HTTPS"
echo ""
echo "Management commands:"
echo "  View logs: docker-compose logs -f [service_name]"
echo "  Stop services: docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Check status: docker-compose ps"
echo "  Renew certificate: sudo certbot renew"
echo ""
echo "Certificate will auto-renew via cron job."
echo "Remember to configure Azure AI services in the .env file!"