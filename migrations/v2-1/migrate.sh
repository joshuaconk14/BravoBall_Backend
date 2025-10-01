#!/bin/bash

# migrate.sh - Simple launcher for V2 production migration
# Usage: ./migrate.sh

echo "🚀 BravoBall V2 Production Migration Launcher"
echo "============================================="
echo ""

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Make setup script executable
chmod +x setup_and_run.sh

# Check if this looks like production environment
if [ -n "$RENDER" ] || [ -n "$RENDER_SERVICE_NAME" ]; then
    echo "🏭 Production environment detected (Render)"
    echo "🎯 Launching PRODUCTION migration setup..."
    echo ""
    ./setup_and_run.sh --production
else
    echo "🧪 Development/Local environment detected"
    echo "🎯 Launching staging migration setup..."
    echo ""
    ./setup_and_run.sh
fi
