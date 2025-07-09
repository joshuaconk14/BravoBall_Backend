#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

show_help() {
    echo "BravoBall Database Migration Tool"
    echo ""
    echo "Usage: ./scripts/migrate.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status    - Show database status compared to models"
    echo "  migrate   - Run full migration (creates tables, adds columns, indexes)"
    echo "  tables    - Create missing tables only"
    echo "  columns   - Add missing columns only"
    echo "  indexes   - Create missing indexes only"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/migrate.sh status     # Check what needs to be migrated"
    echo "  ./scripts/migrate.sh migrate    # Run full migration"
    echo "  ./scripts/migrate.sh tables     # Create only missing tables"
    echo ""
}

# Check if we're in the right directory
if [ ! -f "migrate_database.py" ]; then
    print_error "migrate_database.py not found. Please run this script from the project root."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not detected. Make sure you've activated your venv."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Handle command line arguments
case "$1" in
    "status")
        print_status "Checking database status..."
        python migrate_database.py status
        ;;
    "migrate")
        print_status "Running full database migration..."
        python migrate_database.py migrate
        ;;
    "tables")
        print_status "Creating missing tables..."
        python migrate_database.py tables
        ;;
    "columns")
        print_status "Adding missing columns..."
        python migrate_database.py columns
        ;;
    "indexes")
        print_status "Creating missing indexes..."
        python migrate_database.py indexes
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    "")
        print_status "Running interactive migration..."
        python migrate_database.py
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 