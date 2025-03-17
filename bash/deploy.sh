#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Get current branch name
CURRENT_BRANCH=$(git branch --show-current)

# Check if there are any uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}You have uncommitted changes. Do you want to commit them? (y/n)${NC}"
    read -r COMMIT_CHANGES
    
    if [[ $COMMIT_CHANGES == "y" || $COMMIT_CHANGES == "Y" ]]; then
        echo -e "${YELLOW}Enter commit message:${NC}"
        read -r COMMIT_MESSAGE
        
        # Add all changes and commit
        git add .
        git commit -m "$COMMIT_MESSAGE"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to commit changes. Exiting.${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Changes committed successfully.${NC}"
    else
        echo -e "${YELLOW}Continuing without committing changes.${NC}"
    fi
fi

# Push current branch to remote
echo -e "${YELLOW}Pushing $CURRENT_BRANCH to remote...${NC}"
git push origin "$CURRENT_BRANCH"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to push to remote. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}Successfully pushed to remote.${NC}"

# Ask if you want to merge to develop
echo -e "${YELLOW}Do you want to merge to develop? (y/n)${NC}"
read -r MERGE_TO_DEVELOP

if [[ $MERGE_TO_DEVELOP == "y" || $MERGE_TO_DEVELOP == "Y" ]]; then
    # Checkout to develop branch
    echo -e "${YELLOW}Checking out to develop branch...${NC}"
    git checkout develop

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to checkout develop branch. Exiting.${NC}"
        exit 1
    fi

    # Pull latest changes from develop
    echo -e "${YELLOW}Pulling latest changes from develop...${NC}"
    git pull origin develop

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to pull latest changes from develop. Exiting.${NC}"
        exit 1
    fi

    # Merge feature branch into develop
    echo -e "${YELLOW}Merging $CURRENT_BRANCH into develop...${NC}"
    git merge "$CURRENT_BRANCH" --no-ff --no-commit

    # Check if there are merge conflicts
    if [ $? -ne 0 ]; then
        echo -e "${RED}Merge conflicts detected. Please resolve them manually and then continue the merge process.${NC}"
        echo -e "${YELLOW}After resolving conflicts, run:${NC}"
        echo -e "  git add ."
        echo -e "  git commit -m \"Merge $CURRENT_BRANCH into develop\""
        echo -e "  git push origin develop"
        exit 1
    fi

    # Commit the merge into develop
    echo -e "${YELLOW}Committing merge into develop...${NC}"
    git commit -m "Merge $CURRENT_BRANCH into develop"

    echo -e "${GREEN}Successfully merged $CURRENT_BRANCH into develop.${NC}"

    # Push develop to remote
    echo -e "${YELLOW}Pushing develop to remote...${NC}"
    git push origin develop

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to push develop to remote. Exiting.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Successfully pushed develop to remote.${NC}"

    # Ask if user wants to merge to main
    echo -e "${YELLOW}Do you want to merge develop into main? (y/n)${NC}"
    read -r MERGE_TO_MAIN

    if [[ $MERGE_TO_MAIN == "y" || $MERGE_TO_MAIN == "Y" ]]; then
        # Checkout to main branch
        echo -e "${YELLOW}Checking out to main branch...${NC}"
        git checkout main
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to checkout main branch. Exiting.${NC}"
            exit 1
        fi
        
        # Pull latest changes from main
        echo -e "${YELLOW}Pulling latest changes from main...${NC}"
        git pull origin main
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to pull latest changes from main. Exiting.${NC}"
            exit 1
        fi
        
        # Merge develop into main
        echo -e "${YELLOW}Merging develop into main...${NC}"
        git merge develop --no-ff --no-commit
        
        # Check if there are merge conflicts
        if [ $? -ne 0 ]; then
            echo -e "${RED}Merge conflicts detected. Please resolve them manually and then continue the merge process.${NC}"
            echo -e "${YELLOW}After resolving conflicts, run:${NC}"
            echo -e "  git add ."
            echo -e "  git commit -m \"Merge develop into main\""
            echo -e "  git push origin main"
            exit 1
        fi
        
        # Commit the merge into main
        echo -e "${YELLOW}Committing merge into main...${NC}"
        git commit -m "Merge develop into main"
        
        echo -e "${GREEN}Successfully merged develop into main.${NC}"
        
        # Push main to remote
        echo -e "${YELLOW}Pushing main to remote...${NC}"
        git push origin main
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to push main to remote. Exiting.${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Successfully pushed main to remote.${NC}"
    fi
fi

# Return to original branch
echo -e "${YELLOW}Returning to $CURRENT_BRANCH branch...${NC}"
git checkout "$CURRENT_BRANCH"

if [ $? -ne 0 ]; then
    echo -e "${RED} Failed to checkout $CURRENT_BRANCH branch. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}All done! Your changes have been successfully merged.${NC}" 