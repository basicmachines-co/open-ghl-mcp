#!/bin/bash
# Deploy script for open-ghl-mcp to Fly.io

set -e

echo "🚀 Deploying open-ghl-mcp to Fly.io..."

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged in to Fly.io
if ! fly auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io. Running 'fly auth login'..."
    fly auth login
fi

# Check if app exists
if ! fly status --app open-ghl-mcp &> /dev/null; then
    echo "📱 Creating new Fly.io app..."
    fly launch --name open-ghl-mcp --region iad --no-deploy
    
    echo "🔐 Setting up secrets..."
    echo "Please enter your SUPABASE_ANON_KEY:"
    read -s SUPABASE_ANON_KEY
    fly secrets set SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" --app open-ghl-mcp
fi

# Deploy the app
echo "📦 Deploying application..."
fly deploy --app open-ghl-mcp

# Check deployment status
echo "✅ Deployment complete! Checking status..."
fly status --app open-ghl-mcp

# Show app URL
echo "🌐 Your app is available at: https://open-ghl-mcp.fly.dev"
echo ""
echo "📊 View logs with: fly logs --app open-ghl-mcp"
echo "🔍 Debug with: fly ssh console --app open-ghl-mcp"
echo ""
echo "🧪 Test endpoints:"
echo "  - Health: https://open-ghl-mcp.fly.dev/health"
echo "  - OAuth Discovery: https://open-ghl-mcp.fly.dev/.well-known/oauth-authorization-server"
echo "  - Debug Tools: https://open-ghl-mcp.fly.dev/debug/tools"