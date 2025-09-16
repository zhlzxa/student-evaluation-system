#!/bin/bash

# Deployment script for Student Admission Review System

set -e

echo "Starting deployment of Student Admission Review System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
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

# Start database and Redis
echo "Starting database services..."
docker-compose up -d db redis

echo "Waiting for database to be ready..."
sleep 10

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

# Start all services
echo "Starting all services..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 20

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
    exit 1
fi

if curl -s http://localhost > /dev/null; then
    echo "Frontend service is healthy"
else
    echo "Frontend service failed health check. Check logs:"
    docker-compose logs frontend
fi

echo ""
echo "Deployment completed successfully!"
echo "Frontend URL: http://localhost"
echo "Backend API URL: http://localhost/api"
echo ""
echo "Management commands:"
echo "  View logs: docker-compose logs -f [service_name]"
echo "  Stop services: docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Check status: docker-compose ps"
echo ""
echo "Remember to configure Azure AI services in the .env file!"