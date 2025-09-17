# Student Admission Review System - Deployment Guide

## Deployment Options

This system supports multiple deployment architectures:

1. **Hybrid Deployment (Recommended)**: Backend/Celery run natively, others containerized - solves Azure authentication issues
2. **Full Docker Deployment**: All services containerized - may have Azure authentication limitations

### Prerequisites

- VPS server (Recommended: 2 CPU cores, 4GB RAM, 20GB storage)
- Docker and Docker Compose installed
- Python 3.8+ (for hybrid deployment)
- Azure CLI (for Azure authentication)
- Ports 80 and 443 open

### Service Architecture

#### Hybrid Architecture (Recommended)
- **Frontend**: Next.js frontend application (containerized)
- **Backend**: FastAPI backend API (native)
- **Worker**: Celery background task processor (native)
- **Database**: PostgreSQL database (containerized)
- **Cache**: Redis cache (containerized)
- **Proxy**: Nginx reverse proxy (containerized)

#### Full Docker Architecture
- All services run in Docker containers

### Deployment Steps

#### 1. Prepare VPS Environment

```bash
# Install Docker on Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Re-login or run
newgrp docker
```

#### 2. Download Project Code

```bash
# Clone project (replace with your repository URL)
git clone https://github.com/your-username/student-evaluation-system.git
cd student-evaluation-system
```

#### 3. Configure Environment Variables

**IMPORTANT: Never upload your local .env file to the server for security reasons!**

**Option 1: Use the automated configuration script (Recommended)**
```bash
# Make the configuration script executable
chmod +x configure-env.sh

# Run the interactive configuration
./configure-env.sh
```

**Option 2: Manual configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration file securely
nano .env
```

**Required Configuration Items:**

1. **Azure AI Service Configuration (Required)**
```bash
# Get these from your Azure AI Studio project
AZURE_AI_AGENT_ENDPOINT=https://your-project-resource.services.ai.azure.com/api/projects/your-project
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME="gpt-4.1"
AZURE_BING_CONNECTION_NAME=AgentGrounding
```

2. **Azure Document Intelligence (Required)**
```bash
# Get these from your Azure Document Intelligence resource
AZURE_DI_ENDPOINT="https://your-di-resource.cognitiveservices.azure.com/"
AZURE_DI_KEY="your_document_intelligence_key_here"
```

3. **Security Configuration (Important)**
```bash
# Generate a strong JWT secret (use: openssl rand -hex 32)
JWT_SECRET_KEY=your-super-secure-secret-key

# Database password (change from default)
POSTGRES_PASSWORD=your-secure-database-password

# Optional invite code
INVITE_CODE=UCLIXN
```

**Secure Configuration Steps:**
```bash
# 1. Generate a secure JWT secret
openssl rand -hex 32

# 2. Generate a secure database password
openssl rand -base64 32

# 3. Edit .env file with your actual values
nano .env
```

#### 4. Deployment Options

## Option A: Hybrid Deployment (Recommended)

### A1: First-time Full Deployment with HTTPS and Seed Data
```bash
# Update email in script (required for Let's Encrypt)
nano deploy-native-full.sh  # Change EMAIL variable to your email

# Give execution permission and run
chmod +x deploy-native-full.sh
./deploy-native-full.sh

# After script completes, authenticate with Azure
az login

# Start backend services
sudo systemctl enable student-evaluation-backend
sudo systemctl enable student-evaluation-celery
sudo systemctl start student-evaluation-backend
sudo systemctl start student-evaluation-celery
```

### A2: Minimal Deployment (No Seed Data)
```bash
# For updates or when database already has data
chmod +x deploy-native.sh
./deploy-native.sh

# Authenticate with Azure
az login

# Start backend services
sudo systemctl start student-evaluation-backend
sudo systemctl start student-evaluation-celery
```

### A3: Load Seed Data Separately
```bash
# If you used minimal deployment but need seed data
cd backend
python3 scripts/seed_all.py
cd ..
```

## Option B: Full Docker Deployment (Legacy)

**Note: May have Azure authentication issues. Use only if hybrid deployment is not suitable.**

### B1: HTTP Deployment
```bash
chmod +x deploy.sh
./deploy.sh
```

### B2: HTTPS Deployment
```bash
# Update email in script
nano deploy-https.sh  # Change EMAIL variable

chmod +x deploy-https.sh
./deploy-https.sh
```

## Why Choose Hybrid Deployment?

- **Solves Azure Authentication**: Backend runs natively, can use `az login` directly
- **Easier Debugging**: Direct access to logs via `journalctl`
- **Flexible Updates**: Update backend without rebuilding containers
- **Service Management**: Standard systemd service management

### Access Application

**HTTP Deployment:**
- **Frontend**: http://studentreview.uksouth.cloudapp.azure.com
- **Backend API**: http://studentreview.uksouth.cloudapp.azure.com/api

**HTTPS Deployment:**
- **Frontend**: https://studentreview.uksouth.cloudapp.azure.com
- **Backend API**: https://studentreview.uksouth.cloudapp.azure.com/api
- HTTP traffic automatically redirects to HTTPS

### Management Commands

## Hybrid Deployment Management

### Service Status and Control
```bash
# Check all containerized services
docker-compose ps

# Check native backend services
sudo systemctl status student-evaluation-backend
sudo systemctl status student-evaluation-celery

# Start/Stop/Restart backend services
sudo systemctl start student-evaluation-backend
sudo systemctl stop student-evaluation-backend
sudo systemctl restart student-evaluation-backend

sudo systemctl start student-evaluation-celery
sudo systemctl stop student-evaluation-celery
sudo systemctl restart student-evaluation-celery
```

### Viewing Logs
```bash
# Backend logs (native service)
sudo journalctl -u student-evaluation-backend -f

# Celery logs (native service)
sudo journalctl -u student-evaluation-celery -f

# Containerized service logs
docker-compose logs -f frontend
docker-compose logs -f nginx
docker-compose logs -f db
docker-compose logs -f redis
```

### Updates and Redeployment
```bash
# Update code
git pull

# Update Python dependencies
cd backend
pip3 install -r requirements.txt
cd ..

# Restart backend services
sudo systemctl restart student-evaluation-backend
sudo systemctl restart student-evaluation-celery

# Rebuild and restart containerized services if needed
docker-compose build frontend
docker-compose up -d frontend nginx
```

### Health Checks
```bash
# Check backend API health
curl http://localhost:8000/api/health

# Check if services are responding
sudo systemctl is-active student-evaluation-backend
sudo systemctl is-active student-evaluation-celery
```

## Full Docker Deployment Management

### Traditional Docker Commands
```bash
# View all service status
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Stop all services
docker-compose down

# Restart services
docker-compose restart [service_name]

# Redeploy after code update
git pull
docker-compose build
docker-compose up -d
```

### SSL Certificate Management
```bash
# Renew SSL certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Test nginx configuration
docker-compose exec nginx nginx -t
```

### Troubleshooting

#### Service Startup Failure
```bash
# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db
```

#### Database Connection Issues
```bash
# Check if database is running
docker-compose ps db

# Manually connect to database for testing
docker-compose exec db psql -U postgres -d student_evaluation_system
```

#### Reset Database
```bash
# Stop services and remove data volumes
docker-compose down -v

# Redeploy
./deploy.sh
```

### Monitoring and Maintenance

#### Log Management
```bash
# Clean up logs (to avoid disk space issues)
docker system prune -f
docker volume prune -f
```

#### Database Backup
```bash
# Backup
docker-compose exec db pg_dump -U postgres student_evaluation_system > backup.sql

# Restore
docker-compose exec -T db psql -U postgres student_evaluation_system < backup.sql
```

### Security Recommendations

1. **Change Default Passwords**: Update database password and JWT secret in `.env`
2. **Use HTTPS**: Configure SSL certificates (can use Let's Encrypt)
3. **Firewall Settings**: Only open necessary ports (80, 443, 22)
4. **Regular Updates**: Regularly update Docker images and system

### Extended Configuration

#### Enable HTTPS
Add the following to `nginx.conf`:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Other configurations...
}
```

#### Increase Worker Count
Modify in `docker-compose.yml`:
```yaml
celery:
  # ...
  deploy:
    replicas: 3  # Increase worker count
```

### Frequently Asked Questions

**Q: Frontend cannot access backend API after deployment?**
A: Check if `NEXT_PUBLIC_API_URL` environment variable is correctly set

**Q: File upload fails?**
A: Check local file storage permissions and available disk space

**Q: AI evaluation functionality not working?**
A: Verify Azure AI service endpoint and key configuration, ensure model deployment name is correct

**Q: Out of memory?**
A: Recommend at least 4GB memory, can reduce Celery Worker count

---

**After deployment is complete, remember to create admin account in the system and configure Azure AI services!**