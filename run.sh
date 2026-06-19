#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "================================================================="
echo "                  Orbit Radio Initialization                     "
echo "================================================================="

# 1. Check dependencies
echo "Checking system requirements..."

if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Error: docker compose is not installed/working. Please install Docker Compose v2."
    exit 1
fi

echo "✓ System dependencies verified."

# 2. Setup .env file
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Configuring environment (.env)..."
    
    # Read settings interactively
    read -p "Enter Navidrome URL (e.g., http://192.168.1.100:4000): " SUBSONIC_URL
    read -p "Enter Subsonic/Navidrome Username: " SUBSONIC_USER
    read -sp "Enter Subsonic/Navidrome Password: " SUBSONIC_PASS
    echo ""
    
    echo "Choose LLM Provider:"
    echo "1) OpenAI (default)"
    echo "2) Anthropic"
    read -p "Selection [1-2]: " LLM_CHOICE
    
    LLM_PROVIDER="openai"
    OPENAI_KEY=""
    ANTHROPIC_KEY=""
    
    if [ "$LLM_CHOICE" = "2" ]; then
        LLM_PROVIDER="anthropic"
        read -sp "Enter Anthropic API Key: " ANTHROPIC_KEY
        echo ""
    else
        read -sp "Enter OpenAI API Key: " OPENAI_KEY
        echo ""
    fi
    
    read -p "Enter Orbit Domain Name [orbit.localhost]: " DOMAIN_NAME
    DOMAIN_NAME=${DOMAIN_NAME:-orbit.localhost}
    
    # Generate random flask secret key
    SECRET_KEY=$(head -c 16 /dev/urandom | xxd -p)
    
    # Write to .env
    cat << EOF > "$ENV_FILE"
# Flask Configuration
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
DATABASE_PATH=/app/data/orbit.db

# Subsonic / Navidrome connection
SUBSONIC_URL=$SUBSONIC_URL
SUBSONIC_USER=$SUBSONIC_USER
SUBSONIC_PASS=$SUBSONIC_PASS

# LLM Integration Settings
LLM_PROVIDER=$LLM_PROVIDER
OPENAI_API_KEY=$OPENAI_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_KEY

# Reverse Proxy Configuration (Traefik)
DOMAIN_NAME=$DOMAIN_NAME
EOF
    echo "✓ .env file created successfully."
else
    echo "✓ .env file already exists. Skipping configuration."
fi

# 3. Build and launch containers
echo "Starting Orbit container services..."
docker compose up -d --build

echo "================================================================="
echo "🎉 Success! Orbit has been deployed."
echo "You can access your station at: http://$(grep DOMAIN_NAME .env | cut -d '=' -f2)"
echo "================================================================="
echo "To sync tracks from Navidrome to your local database, run:"
echo "  docker compose exec backend flask sync-subsonic"
echo ""
echo "To enrich tracks with Mutagen metadata JSON, copy your JSON file to the volume,"
echo "then execute:"
echo "  docker compose exec backend flask ingest-mutagen <path-to-json-in-container>"
echo "================================================================="
EOF
