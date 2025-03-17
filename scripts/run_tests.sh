#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Help message
display_help() {
    echo -e "${BLUE}BravoBall API Test Runner${NC}"
    echo ""
    echo "Usage:"
    echo "  ./run_tests.sh [options]"
    echo ""
    echo "Options:"
    echo "  --all         Run all tests"
    echo "  --drill-groups Run only drill groups tests"
    echo "  --coverage    Run tests with coverage report"
    echo "  --verbose     Run with verbose output"
    echo "  --help        Display this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh --all"
    echo "  ./run_tests.sh --drill-groups --verbose"
    echo "  ./run_tests.sh --coverage"
}

# Ensure we're in the project root
cd "$(dirname "$0")/.." || exit 1

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed. Please run:${NC}"
    echo "pip install pytest pytest-cov"
    exit 1
fi

# Default values
VERBOSITY=""
TEST_PATH="tests/"
COVERAGE=""

# Parse arguments
if [ $# -eq 0 ]; then
    display_help
    exit 0
fi

while [ "$1" != "" ]; do
    case $1 in
        --all )
            TEST_PATH="tests/"
            ;;
        --drill-groups )
            TEST_PATH="tests/routers/test_drill_groups.py"
            ;;
        --verbose )
            VERBOSITY="-v"
            ;;
        --coverage )
            COVERAGE="--cov=routers --cov-report=term-missing"
            ;;
        --help )
            display_help
            exit 0
            ;;
        * )
            echo -e "${RED}Unknown option: $1${NC}"
            display_help
            exit 1
            ;;
    esac
    shift
done

# Print test run info
echo -e "${BLUE}=== Running BravoBall API Tests ===${NC}"
echo -e "${YELLOW}Test path:${NC} $TEST_PATH"
if [ -n "$VERBOSITY" ]; then
    echo -e "${YELLOW}Verbosity:${NC} Enabled"
fi
if [ -n "$COVERAGE" ]; then
    echo -e "${YELLOW}Coverage:${NC} Enabled"
fi
echo ""

# Run tests
echo -e "${PURPLE}Starting test run...${NC}"
echo "--------------------------------------------------------------------------------"
if pytest $TEST_PATH $VERBOSITY $COVERAGE; then
    echo "--------------------------------------------------------------------------------"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo "--------------------------------------------------------------------------------"
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi 