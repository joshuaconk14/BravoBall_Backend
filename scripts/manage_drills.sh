#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display help message
display_help() {
    echo "BravoBall Drill Management Script"
    echo ""
    echo "Usage:"
    echo "  ./manage_drills.sh [options]"
    echo ""
    echo "Options:"
    echo "  --all                Import all drill categories"
    echo "  --category CATEGORY  Update drills for a specific category"
    echo "                       (passing, shooting, dribbling, first_touch, fitness, goalkeeper, defending)"
    echo "  --help               Display this help message"
    echo ""
    echo "Examples:"
    echo "  ./manage_drills.sh --all"
    echo "  ./manage_drills.sh --category dribbling"
    echo "  ./manage_drills.sh --category fitness"
}

# Function to import all drills
import_all_drills() {
    echo -e "${YELLOW}Importing all drill categories...${NC}"
    
    echo -e "${YELLOW}Importing passing drills...${NC}"
    python3 -m drills.drill_importer drills/passing_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import passing drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported passing drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing shooting drills...${NC}"
    python3 -m drills.drill_importer drills/shooting_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import shooting drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported shooting drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing first touch drills...${NC}"
    python3 -m drills.drill_importer drills/first_touch_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import first touch drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported first touch drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing dribbling drills...${NC}"
    python3 -m drills.drill_importer drills/dribbling_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import dribbling drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported dribbling drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing fitness drills...${NC}"
    python3 -m drills.drill_importer drills/fitness_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import fitness drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported fitness drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing goalkeeper drills...${NC}"
    python3 -m drills.drill_importer drills/goalkeeper_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import goalkeeper drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported goalkeeper drills.${NC}"
    fi
    
    echo -e "${YELLOW}Importing defending drills...${NC}"
    python3 -m drills.drill_importer drills/defending_drills.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to import defending drills. Continuing with other categories...${NC}"
    else
        echo -e "${GREEN}Successfully imported defending drills.${NC}"
    fi
    
    echo -e "${GREEN}All drill categories processed.${NC}"
}

# Function to update drills for a specific category
update_category_drills() {
    category=$1
    
    # Validate category - ✅ UPDATED: Added new categories
    if [[ ! "$category" =~ ^(passing|shooting|dribbling|first_touch|fitness|goalkeeper|defending)$ ]]; then
        echo -e "${RED}Invalid category: $category${NC}"
        echo -e "${YELLOW}Valid categories: passing, shooting, dribbling, first_touch, fitness, goalkeeper, defending${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Updating drills for category: $category${NC}"
    python3 -m drill_scripts.manage_drills --category $category
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to update drills for category: $category${NC}"
        exit 1
    else
        echo -e "${GREEN}Successfully updated drills for category: $category${NC}"
        
        # Prompt to re-import the category
        echo -e "${YELLOW}Do you want to re-import all drills for this category? (y/n)${NC}"
        read -r REIMPORT
        
        if [[ $REIMPORT == "y" || $REIMPORT == "Y" ]]; then
            echo -e "${YELLOW}Re-importing drills for category: $category${NC}"
            python3 -m drills.drill_importer drills/${category}_drills.txt
            
            if [ $? -ne 0 ]; then
                echo -e "${RED}Failed to re-import drills for category: $category${NC}"
                exit 1
            else
                echo -e "${GREEN}Successfully re-imported drills for category: $category${NC}"
            fi
        else
            echo -e "${YELLOW}Skipping re-import for category: $category${NC}"
        fi
    fi
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    display_help
    exit 0
fi

case "$1" in
    --all)
        import_all_drills
        ;;
    --category)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Category name is required${NC}"
            display_help
            exit 1
        fi
        update_category_drills "$2"
        ;;
    --help)
        display_help
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        display_help
        exit 1
        ;;
esac

exit 0 