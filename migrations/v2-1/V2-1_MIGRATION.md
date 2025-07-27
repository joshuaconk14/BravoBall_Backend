# V2.1 Migration

## Overview
Two-step migration process to copy production data to staging and apply v2 schema changes.

## Scripts

### 1. `simple_production_to_staging.py`
- **Purpose**: Copies production database to staging using pg_dump/psql
- **Steps**: Creates dump → clears staging → restores data → verifies
- **Usage**: `python migrations/v2-1/simple_production_to_staging.py`

### 2. `complete_v2_migration.py`
- **Purpose**: Applies v2 schema changes and populates UUIDs
- **9 Phases**: Schema migration → UUID population → new content seeding → data fixes
- **Usage**: `python migrations/v2-1/complete_v2_migration.py --skip-data-import`

## Quick Commands

**Run both scripts sequentially:**
```bash
source venv/bin/activate && python migrations/v2-1/simple_production_to_staging.py && python migrations/v2-1/complete_v2_migration.py --skip-data-import
```

**Individual execution:**
```bash
# Step 1: Copy production data
python migrations/v2-1/simple_production_to_staging.py

# Step 2: Apply v2 schema
python migrations/v2-1/complete_v2_migration.py --skip-data-import
```

## What It Does
1. **Data Copy**: Full production database copied to staging
2. **Schema Updates**: Applies models.py changes (UUIDs, custom drills, etc.)
3. **UUID Population**: Generates UUIDs for existing drills
4. **Content Seeding**: Adds mental training quotes and new drill categories
5. **Data Fixes**: Corrects drill IDs in JSON, video URLs, categories