# BravoBall Scripts

This directory contains utility scripts for development, deployment, and data management workflows.

## Available Scripts

### 1. deploy.sh

A CI/CD automation script that handles git operations for deploying changes:

- Commits and pushes changes to the current branch
- Optionally merges changes to the develop branch
- Optionally merges develop to main branch
- Handles merge conflicts gracefully

#### Usage

```bash
./deploy.sh
```

The script will guide you through the process with interactive prompts.

#### Features

- Colored output for better readability
- Checks for uncommitted changes
- Handles merge conflicts with helpful instructions
- Maintains Git best practices with proper commit messages
- Returns to the original branch after completion

### 2. manage_drills.sh

A utility script for managing drill data in the BravoBall database:

- Imports all drill categories at once
- Updates and manages drills for specific categories
- Handles error reporting and logging

#### Usage

```bash
# Import all drill categories
./manage_drills.sh --all

# Update drills for a specific category
./manage_drills.sh --category dribbling

# Display help
./manage_drills.sh --help
```

#### Valid Categories

- `passing`
- `shooting`
- `dribbling`
- `first_touch`

#### Features

- Color-coded output for better readability
- Validates category inputs
- Continues processing other categories if one fails
- Interactive prompts for confirmation before reimporting
- Detailed error reporting

### 3. run_tests.sh

A test runner script for running the API tests with various options:

- Run all tests in the project
- Run specific test modules
- Generate coverage reports
- Control verbosity of test output

#### Usage

```bash
# Run all tests
./run_tests.sh --all

# Run only drill groups tests
./run_tests.sh --drill-groups

# Run with verbose output
./run_tests.sh --all --verbose

# Run with coverage report
./run_tests.sh --all --coverage

# Display help
./run_tests.sh --help
```

#### Features

- Colorful and clear test output
- Simple command-line interface
- Coverage reporting
- Focused test runs for specific features
- Validates that required dependencies are installed

## Adding New Scripts

When adding new scripts to this directory:

1. Create the script file with a descriptive name
2. Add a shebang line (`#!/bin/bash`) at the top
3. Make it executable with `chmod +x script_name.sh`
4. Document the script in this README
5. Add color coding for consistent user experience
6. Include a help function for usage instructions

## Best Practices

- Use color coding consistently:
  - `GREEN` for success messages
  - `YELLOW` for warnings and information
  - `RED` for errors
- Provide detailed error messages
- Include help documentation
- Add descriptive comments
- Check return codes after command execution
- Use functions to organize code
- Validate user inputs 