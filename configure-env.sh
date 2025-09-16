#!/bin/bash

# Secure environment configuration script for VPS deployment

echo "=========================================================="
echo "Student Admission Review System - Environment Setup"
echo "=========================================================="
echo

# Check if .env already exists
if [ -f ".env" ]; then
    echo "Warning: .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Copy template
if [ ! -f ".env.example" ]; then
    echo "Error: .env.example not found. Are you in the project root directory?"
    exit 1
fi

cp .env.example .env
echo "Created .env from template"
echo

# Generate secure secrets
echo "Generating secure secrets..."
if command -v openssl &> /dev/null; then
    JWT_SECRET=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    echo "Generated JWT_SECRET: $JWT_SECRET"
    echo "Generated DB_PASSWORD: $DB_PASSWORD"
    echo

    # Update .env with generated secrets
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" .env
    sed -i "s/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=$DB_PASSWORD/" .env

    # Update DATABASE_URL if it exists
    if grep -q "DATABASE_URL.*postgres:postgres@" .env; then
        sed -i "s/postgres:postgres@/postgres:$DB_PASSWORD@/" .env
    fi

    echo "Updated .env with secure secrets"
else
    echo "Warning: openssl not found. Please manually set strong passwords in .env"
fi
echo

# Show Azure configuration guide
echo "=========================================================="
echo "Azure Configuration Required"
echo "=========================================================="
echo
echo "You need to configure the following Azure services:"
echo
echo "1. Azure AI Agent Configuration:"
echo "   Get these from your Azure AI Studio project:"
echo "   - AZURE_AI_AGENT_ENDPOINT"
echo "   - AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME (usually 'gpt-4.1')"
echo "   - AZURE_BING_CONNECTION_NAME (usually 'AgentGrounding')"
echo
echo "2. Azure Document Intelligence Configuration:"
echo "   Get these from your Azure Document Intelligence resource:"
echo "   - AZURE_DI_ENDPOINT"
echo "   - AZURE_DI_KEY"
echo
echo "3. Optional Configuration:"
echo "   - INVITE_CODE (for user registration, default: UCLIXN)"
echo

# Ask user how they want to configure
echo "How would you like to configure Azure settings?"
echo "1) Open nano editor now"
echo "2) Configure manually later"
echo "3) Use interactive prompts"
read -p "Choose option (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        echo "Opening nano editor..."
        nano .env
        ;;
    2)
        echo "You can edit .env manually later with: nano .env"
        ;;
    3)
        echo "Interactive configuration:"
        read -p "Azure AI Agent Endpoint: " ai_endpoint
        read -p "Azure AI Model Deployment Name [gpt-4.1]: " ai_model
        read -p "Azure Bing Connection Name [AgentGrounding]: " bing_conn
        read -p "Azure DI Endpoint: " di_endpoint
        read -p "Azure DI Key: " di_key
        read -p "Invite Code [UCLIXN]: " invite_code

        # Set defaults
        ai_model=${ai_model:-"gpt-4.1"}
        bing_conn=${bing_conn:-"AgentGrounding"}
        invite_code=${invite_code:-"UCLIXN"}

        # Update .env file
        if [ -n "$ai_endpoint" ]; then
            sed -i "s|AZURE_AI_AGENT_ENDPOINT=.*|AZURE_AI_AGENT_ENDPOINT=$ai_endpoint|" .env
        fi
        if [ -n "$ai_model" ]; then
            sed -i "s|AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=.*|AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=\"$ai_model\"|" .env
        fi
        if [ -n "$bing_conn" ]; then
            sed -i "s|AZURE_BING_CONNECTION_NAME=.*|AZURE_BING_CONNECTION_NAME=$bing_conn|" .env
        fi
        if [ -n "$di_endpoint" ]; then
            sed -i "s|AZURE_DI_ENDPOINT=.*|AZURE_DI_ENDPOINT=\"$di_endpoint\"|" .env
        fi
        if [ -n "$di_key" ]; then
            sed -i "s|AZURE_DI_KEY=.*|AZURE_DI_KEY=\"$di_key\"|" .env
        fi
        if [ -n "$invite_code" ]; then
            sed -i "s|INVITE_CODE=.*|INVITE_CODE=$invite_code|" .env
        fi

        echo "Configuration updated!"
        ;;
    *)
        echo "Invalid option. You can configure manually later."
        ;;
esac

echo
echo "=========================================================="
echo "Configuration Summary"
echo "=========================================================="
echo "- JWT secret generated and configured"
echo "- Database password generated and configured"
echo "- Environment file created at .env"
echo
echo "Security Notes:"
echo "- Keep your .env file secure and never commit it to git"
echo "- The generated secrets are unique to this deployment"
echo "- Make sure all Azure endpoints and keys are configured"
echo
echo "Next steps:"
echo "1. Verify your .env configuration: cat .env"
echo "2. Run deployment: ./deploy.sh"
echo
echo "If deployment fails, check:"
echo "- Azure service endpoints are accessible"
echo "- API keys are valid and have proper permissions"
echo "- All required environment variables are set"
echo