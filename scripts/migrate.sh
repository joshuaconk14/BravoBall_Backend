#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_data() {
    echo -e "${PURPLE}[DATA]${NC} $1"
}

show_help() {
    echo "BravoBall Database Migration Tool"
    echo ""
    echo "Usage: ./scripts/migrate.sh [COMMAND]"
    echo ""
    echo "Schema Commands:"
    echo "  status       - Show database status compared to models"
    echo "  migrate      - Run full migration (creates tables, adds columns, indexes)"
    echo "  tables       - Create missing tables only"
    echo "  columns      - Add missing columns only"
    echo "  indexes      - Create missing indexes only"
    echo ""
    echo "Data Commands:"
    echo "  seed         - Seed all data (quotes + drills)"
    echo "  seed-quotes  - Seed mental training quotes only"
    echo "  sync-drills  - Sync drill data from JSON files"
    echo "  full         - Run migration + seed all data"
    echo ""
    echo "Safety Commands:"
    echo "  backup       - Show backup commands"
    echo "  dry-run      - Show what would be changed (safe)"
    echo "  help         - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/migrate.sh status        # Check what needs to be migrated"
    echo "  ./scripts/migrate.sh dry-run       # Safe preview of all changes"
    echo "  ./scripts/migrate.sh full          # Complete setup (migration + data)"
    echo "  ./scripts/migrate.sh migrate       # Schema changes only"
    echo "  ./scripts/migrate.sh seed          # Data seeding only"
    echo "  ./scripts/migrate.sh sync-drills   # Sync drill changes only"
    echo ""
    echo "For new engineers:"
    echo "  ./scripts/migrate.sh full          # Sets up everything from scratch"
    echo ""
}

# Check if we're in the right directory
if [ ! -f "migrate_schema.py" ]; then
    print_error "migrate_schema.py not found. Please run this script from the project root."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not detected. Activating..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment not found. Please create one with: python -m venv venv"
        exit 1
    fi
fi

# Function to run migration command with error handling
run_migration() {
    local command="$1"
    local description="$2"
    
    print_status "$description"
    if python migrate_schema.py $command; then
        print_success "Completed: $description"
        return 0
    else
        print_error "Failed: $description"
        return 1
    fi
}

# Main command handling
case "${1:-help}" in
    "status")
        print_status "Checking database schema status..."
        run_migration "status" "Database status check"
        ;;
    
    "migrate")
        print_status "Running database migration..."
        run_migration "migrate" "Schema migration"
        ;;
    
    "tables")
        print_status "Creating missing tables..."
        # We'll simulate this by doing a targeted run
        print_warning "Use 'migrate' command for complete table creation"
        run_migration "migrate --dry-run" "Preview table creation"
        ;;
    
    "columns")
        print_status "Adding missing columns..."
        print_warning "Use 'migrate' command for complete column addition"
        run_migration "migrate --dry-run" "Preview column addition"
        ;;
    
    "indexes")
        print_status "Creating missing indexes..."
        print_warning "Use 'migrate' command for complete index creation"
        run_migration "migrate --dry-run" "Preview index creation"
        ;;
    
    "seed")
        print_data "Seeding all data (quotes + drills)..."
        run_migration "seed" "Data seeding"
        ;;
    
    "seed-quotes")
        print_data "Seeding mental training quotes..."
        # We'll run the quotes seeding via the comprehensive seed command
        print_status "Running quotes seeding (part of full seed command)..."
        if python migrate_schema.py seed --dry-run | grep -q "mental training quotes"; then
            python migrate_schema.py seed
        else
            print_success "Mental training quotes already seeded"
        fi
        ;;
    
    "sync-drills")
        print_data "Syncing drill data from JSON files..."
        run_migration "sync-drills" "Drill data synchronization"
        ;;
    
    "full")
        print_status "Running complete setup (migration + data seeding)..."
        echo "This will:"
        echo "  1. Create/update database schema"
        echo "  2. Seed mental training quotes"
        echo "  3. Sync drill data from files"
        echo ""
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if run_migration "migrate --seed" "Complete migration with data seeding"; then
                print_success "🎉 Complete setup finished! Your database is ready."
                print_status "Next steps:"
                print_status "  - Start your backend: uvicorn main:app --reload"
                print_status "  - Run tests: ./scripts/run_tests.sh"
            fi
        else
            print_status "Setup cancelled"
        fi
        ;;
    
    "backup")
        print_status "Showing backup commands..."
        run_migration "backup" "Backup command generation"
        ;;
    
    "dry-run")
        print_status "Running dry run (preview mode - no changes made)..."
        echo "🔍 Schema changes:"
        run_migration "migrate --dry-run" "Schema preview"
        echo ""
        echo "🔍 Data changes:"
        run_migration "seed --dry-run" "Data preview"
        ;;
    
    "help"|"--help"|"-h")
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

# Check exit status
if [ $? -eq 0 ]; then
    case "$1" in
        "migrate"|"seed"|"sync-drills"|"full")
            print_success "✅ Operation completed successfully!"
            ;;
    esac
else
    print_error "❌ Operation failed. Check the logs above for details."
    exit 1
fi 