#!/bin/bash

# BravoBall Premium System Deployment Script

echo "🚀 Deploying BravoBall Premium System..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the BravoBall_Backend directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create premium database tables
echo "🗄️ Setting up premium database tables..."
python create_premium_tables.py

if [ $? -eq 0 ]; then
    echo "✅ Premium tables created successfully"
else
    echo "❌ Error creating premium tables"
    exit 1
fi

# Test the premium system
echo "🧪 Testing premium system..."
python scripts/test_premium.py

if [ $? -eq 0 ]; then
    echo "✅ Premium system tests passed"
else
    echo "⚠️ Premium system tests failed - check logs for details"
fi

# Start the server
echo "🌐 Starting BravoBall server with premium features..."
echo "📱 Premium endpoints available at:"
echo "   - GET  /api/premium/status"
echo "   - POST /api/premium/validate"
echo "   - POST /api/premium/verify-receipt"
echo "   - GET  /api/premium/usage-stats"
echo ""
echo "🔗 Server will be available at: http://localhost:8000"
echo "📚 API documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

# Start the server
python main.py
