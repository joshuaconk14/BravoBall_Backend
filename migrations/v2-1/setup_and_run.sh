#!/bin/bash

# setup_and_run.sh
# Helper script to set up environment and run V2 migration

set -e  # Exit on any error

echo "🚀 V2 Migration Setup and Run Script"
echo "====================================="

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
echo "   V1 Database: ${V1_DATABASE_URL}"
echo "   V2 Database: ${V2_DATABASE_URL}"
echo "   Staging Database: ${STAGING_DATABASE_URL}"

# Ask user what they want to do
echo ""
echo "🎯 What would you like to do?"
echo "   1) Check migration status"
echo "   2) Test migration on staging (recommended first)"
echo "   3) Run full migration on staging"
echo "   4) Run migration on production V2 (⚠️  DANGEROUS)"
echo "   5) List rollback points"
echo "   6) Rollback migration"
echo "   7) Exit"
echo ""

read -p "Enter your choice (1-7): " choice

case $choice in
    1)
        echo "🔍 Checking migration status..."
        python3 run_migration.py "$V1_DATABASE_URL" "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" status
        ;;
    2)
        echo "🧪 Testing migration on staging..."
        python3 run_migration.py "$V1_DATABASE_URL" "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" test
        ;;
    3)
        echo "🚀 Running full migration on staging..."
        python3 run_migration.py "$V1_DATABASE_URL" "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" migrate
        ;;
    4)
        echo "⚠️  WARNING: This will run migration on PRODUCTION V2 database!"
        echo "   Make sure you have backups and have tested on staging first."
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "🚀 Running migration on production V2..."
            python3 run_migration.py "$V1_DATABASE_URL" "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" migrate --skip-staging
        else
            echo "❌ Migration cancelled"
        fi
        ;;
    5)
        echo "📋 Listing rollback points..."
        python3 rollback_manager.py "$V2_DATABASE_URL" "$STAGING_DATABASE_URL" list
        ;;
    6)
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
    7)
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
echo "📁 Check the logs/ directory for detailed logs"
echo "📁 Check the backups/ directory for backup files"
