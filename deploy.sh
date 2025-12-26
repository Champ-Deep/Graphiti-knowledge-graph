#!/bin/bash
# Quick Deploy Script for Graphiti Knowledge Graph API
# Usage: ./deploy.sh [platform]
# Platforms: docker, railway, render, digitalocean

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "ℹ $1"; }

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found"

    # Check Git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    print_success "Git found"
}

# Generate secure API key
generate_api_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

# Docker deployment
deploy_docker() {
    print_info "Deploying with Docker Compose..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker found"

    # Check .env file
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from example..."

        if [ -f .env.example ]; then
            cp .env.example .env
        else
            print_error ".env.example not found. Please create .env manually."
            exit 1
        fi

        # Generate API key
        API_KEY=$(generate_api_key)
        echo "" >> .env
        echo "API_KEY=$API_KEY" >> .env

        print_warning "Please edit .env and add your API keys:"
        print_info "  - OPENAI_API_KEY"
        print_info "  - GOOGLE_CLIENT_ID (optional, for Gmail sync)"
        print_info "  - GOOGLE_CLIENT_SECRET (optional, for Gmail sync)"
        print_info ""
        read -p "Press Enter after editing .env to continue..."
    fi

    # Build and start containers
    print_info "Building Docker images..."
    docker-compose build

    print_info "Starting containers..."
    docker-compose up -d

    print_success "Deployment complete!"
    print_info ""
    print_info "Services:"
    print_info "  - API: http://localhost:8080"
    print_info "  - Neo4j Browser: http://localhost:7474"
    print_info ""
    print_info "Check status: docker-compose ps"
    print_info "View logs: docker-compose logs -f"
    print_info "Stop: docker-compose down"
}

# Railway deployment
deploy_railway() {
    print_info "Deploying to Railway..."

    # Check Railway CLI
    if ! command -v railway &> /dev/null; then
        print_warning "Railway CLI not found. Installing..."

        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install railway
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            bash <(curl -fsSL https://railway.app/install.sh)
        else
            print_error "Please install Railway CLI manually: https://docs.railway.app/develop/cli"
            exit 1
        fi
    fi
    print_success "Railway CLI found"

    # Login
    print_info "Logging into Railway..."
    railway login

    # Initialize project
    if [ ! -f railway.json ]; then
        print_info "Initializing Railway project..."
        railway init
    fi

    # Add Neo4j plugin
    print_info "Adding Neo4j database..."
    print_warning "Please add Neo4j from Railway dashboard:"
    print_info "  1. Open dashboard: railway open"
    print_info "  2. Click 'New' -> 'Database' -> 'Neo4j'"
    print_info "  3. Wait for provisioning"
    print_info ""
    read -p "Press Enter after adding Neo4j to continue..."

    # Set environment variables
    print_info "Setting environment variables..."

    read -p "Enter your OpenRouter/OpenAI API key: " OPENAI_KEY
    railway variables set OPENAI_API_KEY="$OPENAI_KEY"

    railway variables set OPENAI_BASE_URL="https://openrouter.ai/api/v1"
    railway variables set MODEL_NAME="anthropic/claude-3.5-sonnet"

    API_KEY=$(generate_api_key)
    railway variables set API_KEY="$API_KEY"

    read -p "Enter your company domain(s) (comma-separated): " DOMAINS
    railway variables set TEAM_DOMAINS="$DOMAINS"

    # Deploy
    print_info "Deploying to Railway..."
    railway up

    print_success "Deployment initiated!"
    print_info "View deployment: railway open"
    print_info "Get URL: railway domain"
}

# Render deployment
deploy_render() {
    print_info "Deploying to Render..."

    print_info "Steps to deploy on Render:"
    print_info "  1. Commit and push your code to GitHub"
    print_info "  2. Go to https://dashboard.render.com"
    print_info "  3. Click 'New' -> 'Blueprint'"
    print_info "  4. Connect your GitHub repository"
    print_info "  5. Render will use render.yaml to configure services"
    print_info ""
    print_warning "Note: You'll need to set up Neo4j Aura separately"
    print_info "  - Sign up at https://neo4j.com/cloud/aura/"
    print_info "  - Create a free instance"
    print_info "  - Add the connection details to Render environment variables"
    print_info ""

    # Ensure render.yaml exists
    if [ ! -f render.yaml ]; then
        print_error "render.yaml not found. Please create it first."
        exit 1
    fi

    # Check if committed
    if ! git diff-index --quiet HEAD --; then
        print_warning "You have uncommitted changes. Commit them first:"
        print_info "  git add ."
        print_info "  git commit -m 'Prepare for Render deployment'"
        print_info "  git push"
    fi

    print_success "render.yaml is ready for Render Blueprint deployment"
}

# DigitalOcean deployment
deploy_digitalocean() {
    print_info "Deploying to DigitalOcean..."

    print_warning "DigitalOcean deployment requires manual setup."
    print_info "Please follow the step-by-step guide in DEPLOYMENT_GUIDE.md"
    print_info ""
    print_info "Quick summary:"
    print_info "  1. Create a Droplet (Ubuntu 22.04, 2GB RAM recommended)"
    print_info "  2. SSH into the server"
    print_info "  3. Run the server setup script (below)"
    print_info ""

    # Create server setup script
    cat > setup_server.sh << 'EOF'
#!/bin/bash
# Run this script on your DigitalOcean droplet

set -e

echo "Setting up Graphiti Knowledge Graph API on DigitalOcean..."

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Create app user
adduser --disabled-password --gecos "" graphiti || true

# Setup Neo4j
docker run -d \
  --name neo4j \
  --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -v neo4j_data:/data \
  -v neo4j_logs:/logs \
  -e NEO4J_AUTH=neo4j/$(openssl rand -hex 16) \
  neo4j:5.26.2

# Wait for Neo4j to start
sleep 10

echo "✓ Server setup complete!"
echo ""
echo "Next steps:"
echo "  1. Switch to graphiti user: su - graphiti"
echo "  2. Clone your repository"
echo "  3. Set up the application (see DEPLOYMENT_GUIDE.md)"
EOF

    chmod +x setup_server.sh

    print_success "Created setup_server.sh"
    print_info "Upload this script to your droplet and run it:"
    print_info "  scp setup_server.sh root@YOUR_DROPLET_IP:~/"
    print_info "  ssh root@YOUR_DROPLET_IP"
    print_info "  bash setup_server.sh"
}

# Test deployment
test_deployment() {
    print_info "Testing deployment..."

    if [ -z "$1" ]; then
        URL="http://localhost:8080"
    else
        URL="$1"
    fi

    print_info "Testing health endpoint: $URL/health"

    if command -v curl &> /dev/null; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health" || echo "000")

        if [ "$response" == "200" ]; then
            print_success "API is healthy!"

            # Show full response
            print_info "Response:"
            curl -s "$URL/health" | python3 -m json.tool || curl -s "$URL/health"
        else
            print_error "API health check failed (HTTP $response)"
            print_info "Check logs for errors"
        fi
    else
        print_warning "curl not found. Please test manually:"
        print_info "  curl $URL/health"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "=========================================="
    echo "  Graphiti Knowledge Graph - Deploy"
    echo "=========================================="
    echo ""
    echo "Choose deployment platform:"
    echo "  1) Docker Compose (Local/Development)"
    echo "  2) Railway (Recommended for Cloud)"
    echo "  3) Render (Free Tier Available)"
    echo "  4) DigitalOcean VPS"
    echo "  5) Test Existing Deployment"
    echo "  6) Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice

    case $choice in
        1)
            check_prerequisites
            deploy_docker
            test_deployment "http://localhost:8080"
            ;;
        2)
            check_prerequisites
            deploy_railway
            ;;
        3)
            check_prerequisites
            deploy_render
            ;;
        4)
            check_prerequisites
            deploy_digitalocean
            ;;
        5)
            read -p "Enter API URL (e.g., https://your-api.railway.app): " api_url
            test_deployment "$api_url"
            ;;
        6)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            show_menu
            ;;
    esac
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    show_menu
else
    case $1 in
        docker)
            check_prerequisites
            deploy_docker
            test_deployment "http://localhost:8080"
            ;;
        railway)
            check_prerequisites
            deploy_railway
            ;;
        render)
            check_prerequisites
            deploy_render
            ;;
        digitalocean|do)
            check_prerequisites
            deploy_digitalocean
            ;;
        test)
            test_deployment "${2:-http://localhost:8080}"
            ;;
        *)
            print_error "Unknown platform: $1"
            print_info "Usage: ./deploy.sh [docker|railway|render|digitalocean|test]"
            exit 1
            ;;
    esac
fi
