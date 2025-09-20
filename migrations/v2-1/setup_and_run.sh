#!/bin/bash

# setup_and_run.sh
# Helper script to set up environment and run V2 migration

set -e  # Exit on any error

echo "🚀 V2 Migration Setup and Run Script"
echo "====================================="
echo ""
echo "💡 Usage:"
echo "   ./setup_and_run.sh                    # Run staging migration"
echo "   ./setup_and_run.sh --production       # Run PRODUCTION migration"
echo ""

# Check if we're in the right directory
if [ ! -f "migration_config.py" ]; then
    echo "❌ Error: Please run this script from the migrations/v2-1 directory"
    exit 1
fi

# Function to check if environment variable is set
check_env_var() {
    if [ -z "${!1}" ]; then
        echo "❌ Error: Environment variable $1 is not set"
        echo "   Please set it with: export $1=<your_database_url>"
        return 1
    fi
    return 0
}

# Check required environment variables
echo "📋 Checking environment variables..."
if ! check_env_var "V1_DATABASE_URL" || ! check_env_var "V2_DATABASE_URL" || ! check_env_var "STAGING_DATABASE_URL"; then
    echo ""
    echo "💡 Example setup:"
    echo "   export V1_DATABASE_URL='postgresql://user:pass@host:port/v1_db'"
    echo "   export V2_DATABASE_URL='postgresql://user:pass@host:port/v2_db'"
    echo "   export STAGING_DATABASE_URL='postgresql://user:pass@host:port/staging_db'"
    echo ""
    echo "   # Optional: Set debug mode (default: true)"
    echo "   export MIGRATION_DEBUG=true"
    echo "   export MAX_TEST_USERS=5"
    exit 1
fi

echo "✅ All environment variables are set"

# Check if Python dependencies are available
echo "📦 Checking Python dependencies..."
python3 -c "import sqlalchemy, psycopg2" 2>/dev/null || {
    echo "❌ Error: Missing Python dependencies"
    echo "   Please install with: pip install sqlalchemy psycopg2-binary"
    exit 1
}
echo "✅ Python dependencies are available"

# Check if PostgreSQL tools are available
echo "🔧 Checking PostgreSQL tools..."
command -v pg_dump >/dev/null 2>&1 || {
    echo "❌ Error: pg_dump not found"
    echo "   Please install PostgreSQL client tools"
    exit 1
}
command -v pg_restore >/dev/null 2>&1 || {
    echo "❌ Error: pg_restore not found"
    echo "   Please install PostgreSQL client tools"
    exit 1
}
echo "✅ PostgreSQL tools are available"

# Show current configuration
echo ""
echo "📊 Current Configuration:"
echo "   Debug Mode: ${MIGRATION_DEBUG:-true}"
echo "   Max Test Users: ${MAX_TEST_USERS:-5}"
echo "   V1 Database: ${V1_DATABASE_URL:0:30}..."
echo "   V2 Database: ${V2_DATABASE_URL:0:30}..."
echo "   Staging Database: ${STAGING_DATABASE_URL:0:30}..."

# Check for production flag
PRODUCTION_FLAG=""
if [ "$1" = "--production" ]; then
    PRODUCTION_FLAG="--production"
    echo "🏭 PRODUCTION MODE ENABLED"
    echo "⚠️  WARNING: This will target the PRODUCTION V2 database!"
fi

# Database connectivity test
echo ""
echo "🔌 Testing database connections..."
python3 -c "
import os
from sqlalchemy import create_engine, text
try:
    v1_engine = create_engine(os.getenv('V1_DATABASE_URL'))
    v2_engine = create_engine(os.getenv('V2_DATABASE_URL'))
    with v1_engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    with v2_engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ All database connections successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Ask user what they want to do
echo ""
echo "🎯 What would you like to do?"
echo ""
echo "   📊 SAFE OPERATIONS:"
echo "   1) View statistics only (shows user counts)"
echo "   2) Dry run preview (shows what would be migrated)"
echo "   3) Test with 5 users (safe test run)"
echo ""
echo "   🛡️  BACKUP & ROLLBACK:"
echo "   5) Create rollback point (recommended before migration)"
echo "   6) List rollback points"
echo "   7) Quick rollback (to latest backup)"
echo "   8) Advanced rollback (select specific backup)"
echo ""
if [ -n "$PRODUCTION_FLAG" ]; then
    echo "   🚨 PRODUCTION OPERATIONS:"
    echo "   4) Run PRODUCTION migration (PERMANENT CHANGES!)"
else
    echo "   🧪 STAGING OPERATIONS:"
    echo "   4) Run full staging migration"
fi
echo ""
echo "   9) Exit"
echo ""
echo "💡 Recommended workflow: 5 → 1 → 2 → 3 → 4"
echo ""

read -p "Enter your choice (1-9): " choice

case $choice in
    1)
        echo "📊 Viewing migration statistics..."
        python3 run_full_migration.py $PRODUCTION_FLAG --stats-only
        ;;
    2)
        echo "🔍 Running dry run (preview)..."
        python3 run_full_migration.py $PRODUCTION_FLAG --dry-run
        ;;
    3)
        echo "🧪 Testing with limited users..."
        python3 run_full_migration.py $PRODUCTION_FLAG --limit 5
        ;;
    4)
        if [ -n "$PRODUCTION_FLAG" ]; then
            echo ""
            echo "🚨" | tr -d '\n'; for i in {1..20}; do echo -n "🚨"; done; echo ""
            echo "🚨 FINAL PRODUCTION MIGRATION WARNING 🚨"
            echo "🚨" | tr -d '\n'; for i in {1..20}; do echo -n "🚨"; done; echo ""
            echo ""
            echo "⚠️  This will PERMANENTLY modify your PRODUCTION V2 database!"
            echo "⚠️  This affects your live Android users' data!"
            echo ""
            echo "📋 Pre-flight checklist:"
            echo "   ✅ Created rollback point? (option 5)"
            echo "   ✅ Tested dry run? (option 2)" 
            echo "   ✅ Tested with 5 users? (option 3)"
            echo "   ✅ Verified statistics look correct? (option 1)"
            echo "   ✅ Team coordinated and aware?"
            echo "   ✅ Ready to monitor for ~97 minutes?"
            echo ""
            read -p "🔴 Type 'I UNDERSTAND THE RISKS' to proceed: " confirm
            if [ "$confirm" = "I UNDERSTAND THE RISKS" ]; then
                echo ""
                echo "🚀 Initiating PRODUCTION migration..."
                echo "📊 This will take approximately 97 minutes"
                echo "📱 Monitor Android user performance during migration"
                echo ""
                python3 run_full_migration.py --production
            else
                echo "❌ Production migration cancelled - confirmation failed"
                echo "💡 Run tests first: options 1, 2, 3, then try again"
            fi
        else
            echo "🚀 Running full staging migration..."
            python3 run_full_migration.py
        fi
        ;;
    5)
        echo "🔄 Creating rollback point..."
        python3 create_rollback_point.py
        ;;
    6)
        echo "📋 Listing rollback points..."
        python3 rollback_manager.py "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" list
        ;;
    7)
        echo "🔄 Quick rollback to latest backup..."
        python3 quick_rollback.py
        ;;
    8)
        echo "📋 Available rollback points:"
        python3 rollback_manager.py "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" list
        echo ""
        read -p "Enter rollback file path: " rollback_file
        if [ -f "$rollback_file" ]; then
            echo "🔄 Rolling back migration..."
            python3 rollback_manager.py "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" rollback "$rollback_file"
        else
            echo "❌ Rollback file not found: $rollback_file"
        fi
        ;;
    9)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "✅ Operation completed!"
echo ""
echo "📁 Check the logs/ directory for detailed logs:"
ls -la logs/ 2>/dev/null | tail -3 || echo "   No logs directory found"
echo ""
echo "📁 Check the backups/ directory for backup files:"
ls -la backups/ 2>/dev/null | tail -3 || echo "   No backups directory found"
echo ""
echo "💡 To run this script again: ./setup_and_run.sh --production"
echo "🆘 For emergency rollback: python3 quick_rollback.py"
