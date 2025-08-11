# V2.1 Migration (Updated: Environment Variables + Blue-Green Deployment)

## Overview
Migration system supporting both staging and V2 databases with environment variable configuration for blue-green deployment strategy.

## Prerequisites
Set environment variables in `.env`:
```bash
PRODUCTION_DATABASE_URL=postgresql://...
STAGING_DATABASE_URL=postgresql://...
V2_DATABASE_URL=postgresql://...
```

## Scripts

### 1. `simple_production_to_staging.py`
- **Purpose**: Copies production database to target (staging or V2)
- **Targets**: `--target-db staging` (default) or `--target-db v2`
- **Steps**: Creates dump → clears target → restores data → verifies

### 2. `complete_v2_migration.py`
- **Purpose**: Applies v2 schema changes and populates UUIDs
- **Targets**: `--target-db staging` (default) or `--target-db v2`
- **9 Phases**: Schema migration → UUID population → new content seeding → data fixes

## Quick Commands

**Blue-Green Deployment (V2):**
```bash
# This resets the V2 database with copied-over production data and applies v2 schema
python migrations/v2-1/simple_production_to_staging.py --target-db v2
python migrations/v2-1/complete_v2_migration.py --target-db v2 --skip-data-import
```

**Traditional Staging:**
```bash
# This resets the STAGING database with copied-over production data and applies v2 schema
python migrations/v2-1/simple_production_to_staging.py
python migrations/v2-1/complete_v2_migration.py --skip-data-import
```

**Testing:**
```bash
# Dry run against V2
python migrations/v2-1/complete_v2_migration.py --dry-run --target-db v2
```

## What It Does
1. **Data Copy**: Full production database copied to staging
2. **Schema Updates**: Applies models.py changes (UUIDs, custom drills, etc.)
3. **UUID Population**: Generates UUIDs for existing drills
4. **Content Seeding**: Adds mental training quotes and new drill categories
5. **Data Fixes**: Corrects drill IDs in JSON, video URLs, categories