# Student Admission Review System - Deployment Guide

## Docker Deployment

This is a fully dockerized deployment solution that can be quickly deployed on any VPS that supports Docker.

### Prerequisites

- VPS server (Recommended: 2 CPU cores, 4GB RAM, 20GB storage)
- Docker and Docker Compose installed
- Port 80 open

### Service Architecture

After deployment, the following services will be included:
- **Frontend**: Next.js frontend application
- **Backend**: FastAPI backend API
- **Database**: PostgreSQL database
- **Cache**: Redis cache
- **Worker**: Celery background task processor
- **Proxy**: Nginx reverse proxy

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

**Option A: HTTP Deployment (Quick)**
```bash
# Give execution permission to deployment script
chmod +x deploy.sh

# Run one-click deployment
./deploy.sh
```

**Option B: HTTPS Deployment with SSL Certificate (Recommended for Production)**
```bash
# Give execution permission to HTTPS deployment script
chmod +x deploy-https.sh

# Update email in script (required for Let's Encrypt)
nano deploy-https.sh  # Change EMAIL variable to your email

# Run HTTPS deployment
./deploy-https.sh
```

The deployment script will automatically:
- Build all Docker images
- Start database and Redis
- Initialize database tables
- Start all services
- Perform health checks

### Access Application

**HTTP Deployment:**
- **Frontend**: http://studentreview.uksouth.cloudapp.azure.com
- **Backend API**: http://studentreview.uksouth.cloudapp.azure.com/api

**HTTPS Deployment:**
- **Frontend**: https://studentreview.uksouth.cloudapp.azure.com
- **Backend API**: https://studentreview.uksouth.cloudapp.azure.com/api
- HTTP traffic automatically redirects to HTTPS

### Management Commands

```bash
# View all service status
docker-compose ps

# View logs
docker-compose logs -f [service_name]
# Example: docker-compose logs -f backend

# Stop all services
docker-compose down

# Restart services
docker-compose restart [service_name]

# Redeploy after code update
git pull
docker-compose build
docker-compose up -d

# HTTPS-specific commands
# Renew SSL certificate manually
chmod +x renew-cert.sh
./renew-cert.sh

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