# V2 Migration - Solution 1

This directory contains the complete migration solution for moving Apple users from V1 to V2 database while preserving Android user data.

## Problem Statement

- **V2 database** contains stale Apple user data (copied from V1 on July 28th)
- **V2 database** contains current Android user data (new users since September 1st)
- **V1 database** contains current Apple user data (most up-to-date)
- Need to migrate Apple users to V2 while preserving Android user data

## Solution Overview

**Solution 1**: Intelligent data merging with platform detection
- Preserves all Android user data
- Overwrites stale V2 Apple data with current V1 data
- Creates new entries for Apple users not in V2
- Migrates all related data (sessions, preferences, drill groups, etc.)

## Migration Components

### 1. Schema Sync (`schema_sync.py`)
Ensures staging database has the same schema as V2 database.

**Usage:**
```bash
python schema_sync.py <V2_DATABASE_URL> <STAGING_DATABASE_URL>
```

**Features:**
- Compares table structures between V2 and staging
- Creates missing tables in staging
- Adds missing columns to existing tables
- Validates schema synchronization

### 2. Staging Setup (`staging_setup.py`)
Sets up staging database for safe testing by copying V2 production data.

**Usage:**
```bash
python staging_setup.py <V2_DATABASE_URL> <STAGING_DATABASE_URL>
```

**Features:**
- Creates backup of current staging data
- Syncs schemas to match V2
- Clears staging database
- Copies all V2 data to staging
- Validates copy integrity

### 3. Migration Manager (`v2_migration_manager.py`)
Core migration logic that intelligently merges data based on user platforms.

**Usage:**
```bash
python v2_migration_manager.py <V1_DATABASE_URL> <V2_DATABASE_URL>
```

**Features:**
- Identifies Apple vs Android users
- Backs up Android user data
- Merges Apple user data from V1 to V2
- Migrates related data (sessions, preferences, drill groups, etc.)
- Validates migration integrity

### 4. Migration Tester (`test_migration.py`)
Comprehensive testing suite for validating migration results.

**Usage:**
```bash
python test_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL>
```

**Features:**
- Data integrity testing
- User experience scenario testing
- Comprehensive validation
- Detailed test reports

### 5. Rollback Manager (`rollback_manager.py`)
Provides safe rollback capabilities in case of issues.

**Usage:**
```bash
# Create rollback point
python rollback_manager.py <V2_DATABASE_URL> <STAGING_DATABASE_URL> create

# List rollback points
python rollback_manager.py <V2_DATABASE_URL> <STAGING_DATABASE_URL> list

# Rollback migration
python rollback_manager.py <V2_DATABASE_URL> <STAGING_DATABASE_URL> rollback <rollback_info_file>

# Cleanup old backups
python rollback_manager.py <V2_DATABASE_URL> <STAGING_DATABASE_URL> cleanup [days]
```

**Features:**
- Creates rollback points before migration
- Full database backups
- Android user data backups
- Safe rollback procedures
- Backup cleanup

### 6. Migration Orchestrator (`run_migration.py`)
Main orchestration script that coordinates the entire migration process.

**Usage:**
```bash
# Run full migration
python run_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL> migrate

# Test migration
python run_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL> test

# Check status
python run_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL> status

# Rollback migration
python run_migration.py <V1_DATABASE_URL> <V2_DATABASE_URL> <STAGING_DATABASE_URL> rollback --rollback-file <file>
```

**Options:**
- `--skip-staging`: Skip staging setup
- `--skip-tests`: Skip testing phase

## Migration Process

### Phase 1: Preparation
1. **Sync database schemas**
   - Ensure staging has same schema as V2
   - Create missing tables and columns
   - Validate schema synchronization

2. **Set up staging database**
   - Copy V2 production data to staging
   - Validate staging copy
   - Create backup of current staging data

3. **Create rollback point**
   - Full V2 database backup
   - Android user data backup
   - Save rollback information

### Phase 2: Migration
1. **Identify user platforms**
   - Apple users: exist in V1 database
   - Android users: created after September 1st, 2024

2. **Merge Apple user data**
   - If Apple user exists in V2: overwrite with V1 data
   - If Apple user doesn't exist in V2: create new entry

3. **Migrate related data**
   - Completed sessions
   - Session preferences
   - Drill groups and items
   - Progress history
   - Saved filters

### Phase 3: Validation
1. **Data integrity testing**
   - User count validation
   - Apple user data accuracy
   - Android user preservation
   - Related data migration
   - Data consistency

2. **User experience testing**
   - Apple user login scenarios
   - Android user login scenarios
   - Data access validation

### Phase 4: Rollback (if needed)
1. **Automatic rollback** if migration fails
2. **Manual rollback** if testing fails
3. **Validation** of rollback success

## Safety Features

### Data Preservation
- **Android user data**: Completely preserved, never modified
- **Apple user data**: Only updated with current V1 data
- **Related data**: Migrated with proper foreign key handling

### Backup Strategy
- **Full database backups** before migration
- **Selective backups** of critical data
- **Multiple rollback points** for different scenarios

### Validation
- **Pre-migration validation** of data integrity
- **Post-migration validation** of results
- **Comprehensive testing** of user scenarios

### Error Handling
- **Graceful error handling** with detailed logging
- **Automatic rollback** on critical failures
- **Detailed error reporting** for troubleshooting

## Testing Strategy

### Staging Environment
1. Copy V2 production data to staging
2. Run migration on staging
3. Test all scenarios
4. Validate results
5. Only proceed to production if all tests pass

### Test Coverage
- **Data integrity**: All data correctly migrated
- **User experience**: Login and data access work
- **Platform detection**: Apple vs Android users correctly identified
- **Related data**: All relationships preserved
- **Rollback**: Can safely rollback if needed

## Production Deployment

### Pre-deployment Checklist
- [ ] Staging tests pass
- [ ] Rollback point created
- [ ] Backup strategy confirmed
- [ ] Monitoring in place
- [ ] Team notified

### Deployment Steps
1. **Create rollback point**
2. **Run migration**
3. **Validate results**
4. **Monitor for issues**
5. **Update Apple app** to use V2 database

### Post-deployment
- **Monitor user experience**
- **Check for any issues**
- **Clean up old backups** after successful deployment
- **Decommission V1 database** when ready

## Troubleshooting

### Common Issues
1. **Migration fails**: Check logs, use rollback
2. **Data mismatch**: Validate staging copy
3. **User login issues**: Check password hashes
4. **Missing data**: Verify related data migration

### Log Files
- Migration logs: `migration_*.log`
- Test reports: `migration_test_report_*.json`
- Rollback info: `rollback_info_*.json`

### Support
- Check logs for detailed error messages
- Use rollback if critical issues occur
- Validate data integrity at each step

## File Structure

```
migrations/v2-1/
├── README.md                 # This file
├── migration_ref.md         # Original problem statement
├── staging_setup.py         # Staging database setup
├── v2_migration_manager.py  # Core migration logic
├── test_migration.py        # Testing suite
├── rollback_manager.py      # Rollback capabilities
├── run_migration.py         # Main orchestration script
└── logs/                    # Migration logs
    └── complete_v2_migration_20250909_160252.log
```

## Environment Variables

Make sure you have the following environment variables set:
- `V1_DATABASE_URL`: V1 database connection string
- `V2_DATABASE_URL`: V2 database connection string
- `STAGING_DATABASE_URL`: Staging database connection string

## Dependencies

- Python 3.8+
- SQLAlchemy
- PostgreSQL client tools (pg_dump, psql)
- Standard Python libraries (json, datetime, subprocess)

## Success Criteria

✅ **All Apple users migrated** with current data
✅ **All Android users preserved** without modification
✅ **All related data migrated** (sessions, preferences, etc.)
✅ **Data integrity maintained** throughout process
✅ **User experience preserved** for both platforms
✅ **Rollback capability** available if needed
✅ **Comprehensive testing** validates results

## Next Steps

1. **Set up staging environment**
2. **Run staging migration**
3. **Test thoroughly**
4. **Create production rollback point**
5. **Run production migration**
6. **Update Apple app** to use V2 database
7. **Monitor and validate**
8. **Decommission V1 database**
