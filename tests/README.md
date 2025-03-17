# BravoBall API Tests

This directory contains automated tests for the BravoBall API endpoints.

## Directory Structure

```
tests/
├── conftest.py            # Shared pytest fixtures and configuration
├── routers/               # Tests for API endpoints
│   ├── test_drill_groups.py   # Tests for drill groups and liked drills
│   └── ...                # Other router tests
└── README.md              # This file
```

## Running Tests

To run all tests:

```bash
pytest tests/
```

To run tests for a specific module:

```bash
pytest tests/routers/test_drill_groups.py
```

To run a specific test:

```bash
pytest tests/routers/test_drill_groups.py::TestDrillGroups::test_get_user_drill_groups
```

With verbose output:

```bash
pytest tests/routers/test_drill_groups.py -v
```

## Test Structure

The tests are organized into classes by feature area:

- `TestDrillGroups`: Tests for general drill group functionality
- `TestLikedDrills`: Tests specifically for the liked drills feature

## Test Database

Tests use an in-memory SQLite database that's created fresh for each test. This ensures tests are isolated and don't affect your development database.

## Authentication

Tests that require authentication use a fixture that creates a test user and generates a valid JWT token.

## Adding New Tests

When adding new test files:

1. Create them in the appropriate subdirectory (e.g., `tests/routers/` for API endpoints)
2. Use the existing fixtures from `conftest.py` where possible
3. Follow the naming convention `test_*.py` for files and `test_*` for functions
4. Group related tests into classes with descriptive names

## Requirements

To run the tests, make sure you have the testing dependencies installed:

```bash
pip install pytest pytest-cov
``` 