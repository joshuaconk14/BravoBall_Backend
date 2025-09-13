# V2 Migration Guide

This guide will walk you through the complete V2 migration process using Solution 1.

## 🎯 Overview

The migration will:
- ✅ **Preserve all Android user data** (never modified)
- ✅ **Update Apple users** with current V1 data (overwrites stale V2 data)
- ✅ **Create new Apple users** not present in V2
- ✅ **Migrate all related data** (sessions, preferences, drill groups, etc.)
- ✅ **Provide comprehensive testing** and rollback capabilities

## 📋 Prerequisites

### 1. Environment Setup

Set the following environment variables:

```bash
export V1_DATABASE_URL="postgresql://user:pass@host:port/v1_db"
export V2_DATABASE_URL="postgresql://user:pass@host:port/v2_db"
export STAGING_DATABASE_URL="postgresql://user:pass@host:port/staging_db"

# Optional: Debug mode (default: true for testing)
export MIGRATION_DEBUG=true
export MAX_TEST_USERS=5
```

### 2. Dependencies

Install required Python packages:
```bash
pip install sqlalchemy psycopg2-binary
```

Install PostgreSQL client tools:
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql
```

## 🚀 Quick Start

### Option 1: Interactive Script (Recommended)

```bash
cd migrations/v2-1
./setup_and_run.sh
```

This will guide you through the entire process with a menu-driven interface.

### Option 2: Manual Commands

```bash
cd migrations/v2-1

# 1. Check status
python3 run_migration.py $V1_DATABASE_URL $V2_DATABASE_URL $STAGING_DATABASE_URL status

# 2. Test migration on staging
python3 run_migration.py $V1_DATABASE_URL $V2_DATABASE_URL $STAGING_DATABASE_URL test

# 3. Run migration on staging
python3 run_migration.py $V1_DATABASE_URL $V2_DATABASE_URL $STAGING_DATABASE_URL migrate

# 4. Run migration on production (⚠️ DANGEROUS)
python3 run_migration.py $V1_DATABASE_URL $V2_DATABASE_URL $STAGING_DATABASE_URL migrate --skip-staging
```

## 📊 Migration Process

### Phase 1: Preparation
1. **Status Check** - Validates configuration and database connectivity
2. **Rollback Point** - Creates full backups before any changes
3. **Schema Sync** - Ensures staging has same schema as V2
4. **Staging Setup** - Copies V2 data to staging for safe testing

### Phase 2: Migration
1. **Platform Detection** - Identifies Apple vs Android users
2. **Android Backup** - Backs up all Android user data
3. **Apple Migration** - Updates Apple users with current V1 data
4. **Related Data** - Migrates sessions, preferences, drill groups, etc.

### Phase 3: Validation
1. **Data Integrity** - Validates all data was migrated correctly
2. **User Experience** - Tests login scenarios for both platforms
3. **Platform Detection** - Verifies user categorization
4. **Related Data** - Confirms all relationships are preserved

## 🧪 Testing Strategy

### Debug Mode (Default)
- Processes only first 5 users from each category
- Safe for testing and validation
- Set `MIGRATION_DEBUG=true`

### Production Mode
- Processes all users
- Set `MIGRATION_DEBUG=false`
- Only run after thorough testing

## 🔄 Rollback Procedures

### List Available Rollbacks
```bash
python3 rollback_manager.py $V2_DATABASE_URL $STAGING_DATABASE_URL list
```

### Rollback Migration
```bash
python3 rollback_manager.py $V2_DATABASE_URL $STAGING_DATABASE_URL rollback <rollback_file>
```

### Clean Up Old Backups
```bash
python3 rollback_manager.py $V2_DATABASE_URL $STAGING_DATABASE_URL cleanup 7
```

## 📁 File Structure

```
migrations/v2-1/
├── migration_config.py      # Configuration management
├── schema_sync.py           # Schema synchronization
├── staging_setup.py         # Staging database setup
├── v2_migration_manager.py  # Core migration logic
├── test_migration.py        # Comprehensive testing
├── rollback_manager.py      # Rollback capabilities
├── run_migration.py         # Main orchestration
├── setup_and_run.sh         # Interactive setup script
├── backups/                 # Backup files
├── logs/                    # Migration logs
└── MIGRATION_GUIDE.md       # This guide
```

## 🔍 Monitoring and Logs

### Log Files
- `logs/migration_runner_*.log` - Main orchestration logs
- `logs/migration_manager_*.log` - Core migration logs
- `logs/test_migration_*.log` - Testing logs
- `logs/rollback_manager_*.log` - Rollback logs

### Backup Files
- `backups/v2_full_backup_*.dump` - Full V2 database backups
- `backups/staging_backup_*.dump` - Staging database backups
- `backups/android_users_backup_*.json` - Android user data backups
- `backups/rollback_info_*.json` - Rollback information

### Report Files
- `backups/migration_report_*.json` - Migration statistics
- `backups/migration_test_report_*.json` - Test results

## ⚠️ Safety Features

### Data Preservation
- **Android users**: Completely preserved, never modified
- **Apple users**: Only updated with current V1 data
- **Related data**: Migrated with proper foreign key handling

### Backup Strategy
- **Full database backups** before migration
- **Selective backups** of critical data
- **Multiple rollback points** for different scenarios

### Validation
- **Pre-migration validation** of data integrity
- **Post-migration validation** of results
- **Comprehensive testing** of user scenarios

## 🚨 Troubleshooting

### Common Issues

1. **Migration fails**
   - Check logs for detailed error messages
   - Use rollback if critical issues occur
   - Validate data integrity at each step

2. **Data mismatch**
   - Validate staging copy
   - Check schema synchronization
   - Verify user platform detection

3. **User login issues**
   - Check password hashes
   - Verify user data migration
   - Test with sample users

4. **Missing data**
   - Verify related data migration
   - Check foreign key relationships
   - Validate data consistency

### Getting Help

1. Check the log files for detailed error messages
2. Use the rollback functionality if needed
3. Validate data integrity at each step
4. Test with debug mode first

## ✅ Success Criteria

- ✅ All Apple users migrated with current data
- ✅ All Android users preserved without modification
- ✅ All related data migrated (sessions, preferences, etc.)
- ✅ Data integrity maintained throughout process
- ✅ User experience preserved for both platforms
- ✅ Rollback capability available if needed
- ✅ Comprehensive testing validates results

## 🎉 Post-Migration

After successful migration:

1. **Monitor user experience** for any issues
2. **Check for any problems** in the logs
3. **Clean up old backups** after successful deployment
4. **Update Apple app** to use V2 database
5. **Decommission V1 database** when ready

## 📞 Support

If you encounter issues:

1. Check the logs in the `logs/` directory
2. Use the rollback functionality if needed
3. Validate data integrity at each step
4. Test with debug mode first

Remember: **ALWAYS test on staging first before running on production!**
