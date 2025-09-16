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
docker-compose run --rm backend python scripts/seed_all.py

# Start all services
echo "Starting all services..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 20

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