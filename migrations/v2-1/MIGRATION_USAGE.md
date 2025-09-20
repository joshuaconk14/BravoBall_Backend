# Migration Script Usage Guide

## 🚀 Full Migration Script

The `run_full_migration.py` script provides a comprehensive migration solution for moving all Apple user data from V1 to staging/V2.

## 📋 Available Commands

### 1. **View Statistics Only**
```bash
python3 run_full_migration.py --stats-only
```
- Shows user counts in both databases
- Identifies Apple vs Android users
- No changes made

### 2. **Dry Run (Preview)**
```bash
python3 run_full_migration.py --dry-run
```
- Shows exactly what would be migrated
- Lists users that would be updated/created
- No actual changes made

### 3. **Limited Migration (Testing)**
```bash
python3 run_full_migration.py --limit 10
```
- Migrates only first 10 users
- Good for testing before full migration
- Interactive confirmation required

### 4. **Full Migration (Staging)**
```bash
python3 run_full_migration.py
```
- Migrates all Apple users to staging database
- Interactive confirmation required
- Comprehensive logging

### 5. **Production Migration**
```bash
python3 run_full_migration.py --production
```
- Migrates all Apple users to **PRODUCTION V2 database**
- ⚠️ **DANGEROUS**: Modifies production data permanently
- Extra safety confirmations required
- Disables debug mode and user limits

## 🔧 Environment Setup

Make sure these environment variables are set:
```bash
export V1_DATABASE_URL="postgresql://user:pass@host:port/v1_db"
export V2_DATABASE_URL="postgresql://user:pass@host:port/v2_db"
export STAGING_DATABASE_URL="postgresql://user:pass@host:port/staging_db"
```

**Note**: 
- Default migration targets **staging** database
- Use `--production` flag to target **V2 production** database

## 📊 What the Script Does

### For Each Apple User:
1. **Checks if user exists in target database**
   - If yes: Overwrites stale data with fresh V1 data
   - If no: Creates new user entry with V1 data

2. **Data Migration Process:**
   - ✅ Deletes stale data (if exists)
   - ✅ Creates fresh user with new ID
   - ✅ Migrates completed sessions with corrected drill UUIDs
   - ✅ Migrates session preferences
   - ✅ Migrates drill groups and items
   - ✅ Creates enhanced progress history
   - ✅ Migrates refresh tokens and password reset codes
   - ✅ Migrates training sessions and ordered drills

3. **Data Quality Improvements:**
   - ✅ Corrects drill UUIDs in completed sessions
   - ✅ Calculates enhanced progress metrics
   - ✅ Preserves all user relationships

## 📈 Output and Logging

### Console Output:
- Real-time progress updates
- Success/failure notifications
- Final statistics summary

### Log Files:
- Detailed logs saved to `migration_log_YYYYMMDD_HHMMSS.log`
- Includes all operations and error details
- Useful for troubleshooting

## ⚠️ Safety Features

### Interactive Confirmation:
```
⚠️  MIGRATION CONFIRMATION
============================================================
Target Database: postgresql://user:pass@host:port/staging_db
Users to migrate: 150 Apple users
  - Overwrite stale data: 75 users
  - Create new entries: 75 users
Android users preserved: 25 users
============================================================

Do you want to proceed with the migration? (yes/no):
```

### Data Protection:
- ✅ Android users completely preserved
- ✅ Comprehensive error handling
- ✅ Transaction rollback on failures
- ✅ Detailed logging for audit trail

## 🎯 Recommended Workflow

### 1. **Pre-Migration Testing**
```bash
# Check statistics
python3 run_full_migration.py --stats-only

# Preview what would happen
python3 run_full_migration.py --dry-run

# Test with limited users
python3 run_full_migration.py --limit 5
```

### 2. **Full Migration**
```bash
# Run full migration
python3 run_full_migration.py
```

### 3. **Post-Migration Validation**
```bash
# Check statistics again
python3 run_full_migration.py --stats-only

# Test individual users
python3 test_specific_user.py "user@example.com"
```

## 📞 Troubleshooting

### Common Issues:
1. **Configuration errors**: Check environment variables
2. **Database connection**: Verify database URLs
3. **Permission errors**: Ensure database user has proper permissions

### Log Analysis:
- Check `migration_log_*.log` for detailed error information
- Look for specific error patterns in the logs
- Use individual user testing for targeted debugging

## 🚀 Production Usage

### Staging Testing (Recommended First):
```bash
# Test on staging first
python3 run_full_migration.py --dry-run
python3 run_full_migration.py --limit 5
python3 run_full_migration.py  # Full staging migration
```

### Production Migration:
```bash
# ⚠️ PRODUCTION MIGRATION - DANGEROUS!
python3 run_full_migration.py --production --dry-run  # Preview
python3 run_full_migration.py --production            # Execute
```

**Pre-Production Checklist:**
1. ✅ Create full V2 database backup
2. ✅ Test migration completely on staging
3. ✅ Coordinate with team (downtime if needed)
4. ✅ Have rollback plan ready
5. ✅ Monitor and validate results

---

**Script Location**: `migrations/v2-1/run_full_migration.py`  
**Last Updated**: 2025-09-16  
**Version**: 1.0
