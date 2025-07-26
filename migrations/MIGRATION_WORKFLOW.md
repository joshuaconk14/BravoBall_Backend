# BravoBall V2 Migration Workflow

This guide explains how to safely test your V2 migration using staging environment.

## 🎯 Goal
Test V2 migration with real production data in staging environment before applying to production.

## 📋 Two-Script Approach

### Script 1: Copy Production to Staging
**File**: `copy_production_to_staging.py`  
**Purpose**: Create exact replica of production in staging (schema + data)

### Script 2: V2 Migration 
**File**: `complete_v2_migration.py`  
**Purpose**: Apply V2 schema changes to preserve data while upgrading

## 🚀 Step-by-Step Workflow

### Step 1: Copy Production Data to Staging

```bash
# Preview what will be copied (recommended first)
python migrations/copy_production_to_staging.py --dry-run

# Copy production to staging
python migrations/copy_production_to_staging.py
```

This will:
- ✅ Clear staging database completely
- ✅ Recreate exact production schema in staging
- ✅ Copy ALL production data (users, drills, sessions, etc.)
- ✅ Create backups and verification logs

### Step 2: Apply V2 Migration to Staging

```bash
# Preview V2 migration changes (recommended first)
python migrations/complete_v2_migration.py --skip-data-import --dry-run

# Apply V2 migration to staging
python migrations/complete_v2_migration.py --skip-data-import
```

This will:
- ⏭️ Skip Phase 1 (data import) since data is already there
- ✅ Apply V2 schema changes (Phase 2)
- ✅ Populate UUIDs for existing drills (Phase 3)
- ✅ Seed mental training quotes (Phase 4)
- ✅ Verify complete migration (Phase 5)

## 📊 What You'll Have After Both Scripts

**Staging Database State:**
- All production users (3,292+ records) ✅
- All production drills (78 records) with UUIDs ✅
- All completed sessions (913+ records) ✅
- All progress history (1,742+ records) with new V2 columns ✅
- V2 schema with new tables (custom drills, mental training, etc.) ✅
- Mental training quotes (43 records) ✅

## 🧪 Testing Your Migration

After both scripts complete:

1. **Test Flutter App**: Point your app to staging and verify all features work
2. **Verify Data Integrity**: Check that existing user data is preserved
3. **Test New Features**: Mental training, custom drills, enhanced analytics
4. **Performance Testing**: Ensure queries work with real data volumes

## 🔄 Production Deployment

Once staging tests pass:

```bash
# Apply SAME migration to production
python migrations/complete_v2_migration.py --production-url $PROD_URL
```

## 🛠️ Script Options

### Copy Production to Staging Options
```bash
--dry-run          # Preview without changes
--skip-backup      # Skip backup creation (faster)
--staging-url      # Override staging URL
--production-url   # Override production URL
```

### V2 Migration Options
```bash
--dry-run           # Preview without changes
--skip-backup       # Skip backup creation
--skip-data-import  # Skip Phase 1 (use when data already copied)
--phase N           # Run specific phase only (1-5)
--staging-url       # Override staging URL
```

## 📝 Example Commands

### Full Staging Test Workflow
```bash
# Step 1: Copy production to staging
python migrations/copy_production_to_staging.py --dry-run
python migrations/copy_production_to_staging.py

# Step 2: Apply V2 migration
python migrations/complete_v2_migration.py --skip-data-import --dry-run
python migrations/complete_v2_migration.py --skip-data-import

# Step 3: Test your Flutter app with staging
```

### Production Deployment
```bash
# Apply complete migration to production (includes data + schema)
python migrations/complete_v2_migration.py --production-url $PROD_URL
```

## 🚨 Safety Features

Both scripts include:
- ✅ Automatic backups before major operations
- ✅ Dry-run mode to preview changes
- ✅ Comprehensive logging with timestamps
- ✅ Transaction rollback on errors
- ✅ Data verification after operations
- ✅ Graceful error handling

## 📞 Support

If you encounter issues:
1. Check the log files (auto-generated with timestamps)
2. Use `--dry-run` to preview changes
3. Use backup files to restore if needed
4. Run specific phases with `--phase N` to debug

## 🎉 Success Criteria

After both scripts complete successfully, you should see:
- ✅ All production data copied to staging
- ✅ V2 schema applied successfully  
- ✅ UUIDs generated for all drills
- ✅ Mental training quotes seeded
- ✅ All verification checks passed
- ✅ Flutter app works with staging environment

Your staging environment will then be an exact simulation of what production will look like after V2 migration! 