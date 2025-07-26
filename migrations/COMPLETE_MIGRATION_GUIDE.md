# Complete BravoBall v2 Migration Guide

## 🎯 Overview
The `complete_v2_migration.py` script handles the entire v2 migration process in the correct order:

1. ✅ **Import Production Data** - Load all production data into staging
2. ✅ **Apply v2 Schema Changes** - Add new tables and columns 
3. ✅ **Populate UUIDs** - Generate UUIDs for existing drills
4. ✅ **Seed Mental Training Quotes** - Add mental training content
5. ✅ **Verify Migration** - Ensure everything worked correctly

## 🚀 Quick Start

### Test with Dry Run (Recommended First)
```bash
cd BravoBall_Backend
python migrations/complete_v2_migration.py --dry-run
```

### Run Full Migration
```bash
python migrations/complete_v2_migration.py
```

### Run Specific Phase Only
```bash
# Phase 1: Import production data
python migrations/complete_v2_migration.py --phase 1

# Phase 2: Apply v2 schema
python migrations/complete_v2_migration.py --phase 2

# Phase 3: Populate UUIDs  
python migrations/complete_v2_migration.py --phase 3

# Phase 4: Seed quotes
python migrations/complete_v2_migration.py --phase 4

# Phase 5: Verify everything
python migrations/complete_v2_migration.py --phase 5
```

## 📋 Prerequisites

### Required Files
- ✅ `production_data_dump.sql` - 9.7MB production data dump
- ✅ `../drills/mental_training_quotes.txt` - Mental training quotes JSON

### Required Tools
- `psql` command line tool
- `pg_dump` command line tool
- Python packages: `sqlalchemy`, `python-dotenv`

### Database Access
- Staging database connection working
- Production data dump accessible

## 🔧 Command Options

```bash
python migrations/complete_v2_migration.py [OPTIONS]

Options:
  --dry-run              Preview changes without applying them
  --skip-backup          Skip creating backups (not recommended)
  --staging-url URL      Custom staging database URL
  --phase N              Run only specific phase (1-5)
  -h, --help            Show help message
```

## 📊 What Each Phase Does

### Phase 1: Import Production Data
- Clears staging database completely
- Imports all production data from SQL dump
- Verifies import with record counts
- **Result**: Staging has all production users, drills, sessions

### Phase 2: Apply v2 Schema
- Adds UUID extension
- Creates new tables: `mental_training_quotes`, `custom_drills`, etc.
- Adds new columns to existing tables
- **Result**: Database has v2 schema + production data

### Phase 3: Populate UUIDs
- Generates UUIDs for all existing drills
- Updates foreign key tables with drill UUIDs
- Adds unique constraints
- **Result**: All drills have UUIDs, relationships preserved

### Phase 4: Seed Mental Training Quotes
- Loads quotes from JSON file
- Inserts into `mental_training_quotes` table
- **Result**: Mental training feature ready

### Phase 5: Verify Migration
- Checks all table counts
- Verifies UUIDs were populated
- Validates data integrity
- **Result**: Confirmation everything worked

## 🚨 Safety Features

### Automatic Backups
The script creates backups before each major phase:
- `backup_initial_YYYYMMDD_HHMMSS.sql`
- `backup_phase_2_YYYYMMDD_HHMMSS.sql`
- `backup_phase_3_YYYYMMDD_HHMMSS.sql`

### Dry Run Mode
Test the migration without making changes:
```bash
python migrations/complete_v2_migration.py --dry-run
```

### Phase-by-Phase Execution
Run one phase at a time for safer execution:
```bash
# Run each phase individually
python migrations/complete_v2_migration.py --phase 1
python migrations/complete_v2_migration.py --phase 2
# ... etc
```

## 📝 Expected Output

### Successful Migration Log
```
🚀 Starting Complete BravoBall v2 Migration
======================================================================
🔗 Connected to staging database
📦 Creating initial backup: backup_initial_20250725_162345.sql

🎯 Phase 1: Import Production Data
==================================================
📋 Found production dump: migrations/production_data_dump.sql
🧹 Clearing staging database...
📥 Importing production data...
✅ Production data imported successfully
   ✅ Users: 3292 records
   ✅ Drills: 78 records
   ✅ Completed Sessions: 913 records
   ✅ Progress History: 1742 records

🎯 Phase 2: Apply v2 Schema
==================================================
📋 Schema migration contains 28 statements
✅ V2 schema changes applied successfully

🎯 Phase 3: Populate UUIDs
==================================================
🔧 Generating UUIDs for existing drills...
   ✅ Generated UUIDs for 78 drills
🔗 Updating drill_skill_focus with drill UUIDs...
   ✅ Updated 156 records in drill_skill_focus
✅ UUID population completed successfully

🎯 Phase 4: Seed Mental Training Quotes
==================================================
📋 Loaded 43 quotes from file
✅ Successfully seeded 43/43 quotes

🎯 Phase 5: Verify Migration
==================================================
   ✅ Users: 3292
   ✅ Drills: 78
   ✅ Drills with UUIDs: 78
   ✅ Mental Training Quotes: 43
✅ All verification checks passed!

🎉 Complete v2 migration finished successfully!
📱 Your Flutter app should now work with staging database
```

## 🔄 Current vs. Fixed Process

### ❌ What Happened Before (Wrong Order)
```
Empty Staging DB → Apply v2 Schema → Seed Quotes → Missing Production Data
```

### ✅ New Correct Process
```
Production Data → Import to Staging → Apply v2 Schema → Populate UUIDs → Ready!
```

## 🧪 Testing After Migration

### 1. Verify Database State
```sql
-- Check drill counts
SELECT COUNT(*) FROM drills;                    -- Should be 78
SELECT COUNT(*) FROM drills WHERE uuid IS NOT NULL;  -- Should be 78

-- Check users
SELECT COUNT(*) FROM users;                     -- Should be 3292

-- Check mental training
SELECT COUNT(*) FROM mental_training_quotes;    -- Should be 43
```

### 2. Test Flutter App
- Set `appDevCase = 4` in `app_config.dart` (already done)
- Run Flutter app locally
- Test drill loading, login, mental training features

### 3. API Endpoint Verification
- Drills: `GET /public/drills/limited` 
- Login: `POST /login/`
- Mental Training: `GET /api/mental-training/quotes`

## 🚀 Next Steps After Successful Migration

1. **Test Flutter App**: Verify all features work with staging
2. **Fix API Endpoints**: Update Flutter to use correct backend routes
3. **Production Migration**: Apply same process to production when ready
4. **Monitor Performance**: Ensure migration doesn't impact app performance

## 🆘 Troubleshooting

### Common Issues

#### "Production dump not found"
```bash
# Make sure production_data_dump.sql exists
ls -la migrations/production_data_dump.sql
```

#### "Quotes file not found"  
```bash
# Check mental training quotes file
ls -la drills/mental_training_quotes.txt
```

#### "Database connection failed"
```bash
# Test staging database connection
psql "postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db" -c "SELECT 1;"
```

### Recovery Options

#### If Migration Fails Mid-Process
```bash
# Restore from latest backup
psql STAGING_URL -f backup_phase_2_YYYYMMDD_HHMMSS.sql

# Re-run from specific phase
python migrations/complete_v2_migration.py --phase 3
```

#### If You Need to Start Over
```bash
# Run Phase 1 again (clears database and re-imports)
python migrations/complete_v2_migration.py --phase 1
```

## 📞 Support

If migration fails:
1. Check the log file: `complete_v2_migration_YYYYMMDD_HHMMSS.log`
2. Use backup files to restore if needed
3. Run individual phases to isolate issues
4. Test with `--dry-run` first to preview changes 