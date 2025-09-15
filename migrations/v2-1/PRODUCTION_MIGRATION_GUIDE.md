# V2 Production Migration Guide

## 🎯 Overview

This document provides a complete guide for migrating Apple user data from V1 to V2 database in production. The migration has been thoroughly tested and validated on staging.

## ✅ What We've Accomplished

### 1. **Enhanced Migration System**
- ✅ **Intelligent User Detection**: Automatically identifies Apple vs Android users
- ✅ **Fresh Data Creation**: Deletes stale data and creates fresh entries with new IDs
- ✅ **Enhanced Progress Metrics**: Calculates accurate progress data from actual completed sessions
- ✅ **Drill UUID Correction**: Fixes old UUIDs in completed sessions JSON to match V2 drills
- ✅ **Comprehensive Data Migration**: Migrates all related data (sessions, preferences, drill groups, etc.)

### 2. **Data Quality Improvements**
- ✅ **Correct Drill UUIDs**: V1 drill IDs are mapped to correct V2 drill UUIDs
- ✅ **Accurate Progress Metrics**: Uses `calculate_enhanced_progress_metrics()` for real data
- ✅ **Proper Data Structure**: UUIDs placed at beginning of drill dictionaries
- ✅ **Complete Related Data**: All user relationships preserved with new IDs

### 3. **Testing & Validation**
- ✅ **Individual User Testing**: `test_specific_user.py` for targeted testing
- ✅ **Staging Environment**: Safe testing without affecting production
- ✅ **Data Integrity**: All foreign key relationships maintained
- ✅ **Error Handling**: Comprehensive logging and rollback capabilities

## 🚀 Production Migration Plan

### Phase 1: Pre-Migration Setup

#### 1.1 Environment Preparation
```bash
# Set up production environment variables
export V1_DATABASE_URL="postgresql://user:pass@host:port/v1_production_db"
export V2_DATABASE_URL="postgresql://user:pass@host:port/v2_production_db"
export STAGING_DATABASE_URL="postgresql://user:pass@host:port/staging_db"
```

#### 1.2 Backup Strategy
```bash
# Create full backups before migration
pg_dump $V1_DATABASE_URL > v1_backup_$(date +%Y%m%d_%H%M%S).sql
pg_dump $V2_DATABASE_URL > v2_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 1.3 Schema Verification
- ✅ Ensure V2 database has latest schema
- ✅ Verify all required tables exist
- ✅ Confirm drill UUID mappings are current

### Phase 2: Migration Execution

#### 2.1 Single User Testing (Recommended First Step)
```bash
cd migrations/v2-1
python3 test_specific_user.py "user@example.com"
```

#### 2.2 Batch Migration for All Apple Users
```bash
cd migrations/v2-1
python3 run_migration.py migrate
```

### Phase 3: Post-Migration Validation

#### 3.1 Data Integrity Checks
```sql
-- Verify user count
SELECT COUNT(*) FROM users WHERE email LIKE '%@%';

-- Check completed sessions with correct UUIDs
SELECT u.email, cs.date, cs.drills 
FROM users u 
JOIN completed_sessions cs ON u.id = cs.user_id 
WHERE u.email = 'user@example.com';

-- Verify progress history has enhanced metrics
SELECT u.email, ph.drills_per_session, ph.minutes_per_session, 
       ph.dribbling_drills_completed, ph.favorite_drill
FROM users u 
JOIN progress_history ph ON u.id = ph.user_id 
WHERE u.email = 'user@example.com';
```

#### 3.2 User Experience Testing
- ✅ Test user login with migrated credentials
- ✅ Verify completed sessions display correctly
- ✅ Check progress metrics accuracy
- ✅ Confirm drill group items work properly

## 📋 Migration Process Details

### How the Migration Works

1. **User Identification**
   - Identifies Apple users (exist in V1)
   - Preserves Android users (exist only in V2)

2. **Data Processing**
   - **For Existing Users**: Deletes stale V2 data, creates fresh entries
   - **For New Users**: Creates new entries directly
   - **Enhanced Metrics**: Calculates progress from actual completed sessions
   - **Drill UUIDs**: Maps V1 drill IDs to correct V2 drill UUIDs

3. **Data Structure**
   ```json
   // Completed Session Drill Structure (Fixed)
   {
     "drill": {
       "uuid": "0a0ad37e-bc71-4760-b385-05e7d1edb6fc", // ✅ Correct V2 UUID
       "title": "L-drags",
       "skill": "dribbling",
       // ... other drill data
     },
     "setsDone": 2,
     "totalSets": 4,
     // ... other session data
   }
   ```

### Files and Scripts

#### Core Migration Files
- `v2_migration_manager.py` - Main migration logic
- `test_specific_user.py` - Individual user testing
- `run_migration.py` - Full migration orchestration
- `migration_config.py` - Configuration management

#### Key Functions
- `_migrate_apple_user_overwrite()` - For users with stale data
- `_migrate_apple_user_create()` - For new users
- `_fix_drills_json_uuids()` - Corrects drill UUIDs in completed sessions
- `_migrate_user_related_data_fresh()` - Migrates all related data with enhanced metrics

## ⚠️ Critical Considerations

### Data Safety
- ✅ **Android Users Preserved**: No Android data is modified
- ✅ **Backup Strategy**: Full backups created before migration
- ✅ **Rollback Capability**: Can restore from backups if needed
- ✅ **Staging Testing**: All changes tested on staging first

### Performance
- ✅ **Batch Processing**: Handles large numbers of users efficiently
- ✅ **Transaction Safety**: Each user migration is atomic
- ✅ **Memory Efficient**: Processes users individually to avoid memory issues

### Monitoring
- ✅ **Comprehensive Logging**: All operations logged with timestamps
- ✅ **Progress Tracking**: Shows migration progress and statistics
- ✅ **Error Handling**: Detailed error messages and recovery options

## 🔧 Troubleshooting

### Common Issues and Solutions

1. **User Not Found in V1**
   ```
   Solution: Verify user email exists in V1 database
   ```

2. **Drill UUID Mapping Fails**
   ```
   Solution: Check V2 drills table has correct drill titles
   ```

3. **Foreign Key Violations**
   ```
   Solution: Migration handles deletion order automatically
   ```

4. **Progress Metrics Calculation Errors**
   ```
   Solution: Verify completed sessions migrated correctly first
   ```

## 📊 Expected Results

### Before Migration
- Apple users have stale data in V2
- Completed sessions have incorrect drill UUIDs
- Progress metrics are inaccurate or missing

### After Migration
- ✅ All Apple users have current data in V2
- ✅ Completed sessions have correct drill UUIDs
- ✅ Progress metrics are accurate and calculated from real data
- ✅ Android users remain completely unchanged
- ✅ All user relationships preserved with new IDs

## 🎯 Success Criteria

- [ ] All Apple users can log in successfully
- [ ] Completed sessions display with correct drill information
- [ ] Progress metrics show accurate data
- [ ] Drill groups and preferences work correctly
- [ ] Android users unaffected
- [ ] No data loss or corruption
- [ ] Performance maintained

## 📞 Support and Escalation

### If Issues Arise
1. **Check logs** in `migrations/v2-1/logs/`
2. **Verify data integrity** using provided SQL queries
3. **Test individual users** with `test_specific_user.py`
4. **Restore from backup** if critical issues occur

### Rollback Procedure
```bash
# If rollback needed
psql $V2_DATABASE_URL < v2_backup_YYYYMMDD_HHMMSS.sql
```

## 🚀 Next Steps After Migration

1. **Update Apple App**: Point Apple app to V2 database
2. **Monitor Performance**: Watch for any issues in first 24-48 hours
3. **User Communication**: Notify users of improved features
4. **Data Cleanup**: Remove V1 database after successful transition

---

## 📝 Migration Checklist

### Pre-Migration
- [ ] Full database backups created
- [ ] Environment variables configured
- [ ] Schema verification completed
- [ ] Staging testing successful

### During Migration
- [ ] Migration script executed
- [ ] Progress monitored
- [ ] Errors addressed immediately
- [ ] Logs reviewed

### Post-Migration
- [ ] Data integrity verified
- [ ] User login tested
- [ ] Progress metrics validated
- [ ] Performance monitored
- [ ] Team notified of completion

---

**Migration Date**: ________________  
**Migrated By**: ________________  
**Backup Files**: ________________  
**Issues Encountered**: ________________  
**Resolution**: ________________
