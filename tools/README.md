# Bash Scripts for Soccer Training App

This directory contains utility shell scripts for development and deployment workflows.

## Available Scripts

### deploy.sh

A CI/CD automation script that handles git operations for deploying changes:

- Commits and pushes changes to the current branch
- Optionally merges changes to the develop branch
- Optionally merges develop to main branch
- Handles merge conflicts gracefully

#### Usage

If in the root directory, run:
```bash
./tools/deploy.sh
```

The script will guide you through the process with interactive prompts.

#### Features

- Colored output for better readability
- Checks for uncommitted changes
- Handles merge conflicts with helpful instructions
- Maintains Git best practices with proper commit messages
- Returns to the original branch after completion

## Adding New Scripts

When adding new scripts to this directory:

1. Create the script file with a descriptive name
2. Add a shebang line (`#!/bin/bash`) at the top
3. Make it executable with `chmod +x script_name.sh`
4. Document the script in this README 