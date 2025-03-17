#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing onboarding endpoint...${NC}"
echo "Sending request to http://127.0.0.1:8000/api/onboarding"
echo

# Get directory of script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Send request and format response
curl -s -X POST http://127.0.0.1:8000/api/onboarding \
  -H "Content-Type: application/json" \
  -d @"$DIR/onboarding_test.json" | python3 -m json.tool

# Check if curl was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Test completed successfully${NC}"
else
    echo -e "\n${RED}Test failed${NC}"
fi 