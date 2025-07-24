# Database Migrations

This directory contains database migration scripts for the BravoBall backend. Each migration is a standalone Python script that can be run to update the database schema or data.

## 📋 Migration Naming Convention

Migrations should be named with the following format:
```
YYYY_MM_DD_migration_description.py
```

Example: `2025_07_24_migrate_video_urls_to_h264.py`

## 🗂️ Directory Structure

```
migrations/
├── README.md                                    # This file
├── migration_runner.py                          # Helper script to run migrations
├── 2025_07_24_migrate_video_urls_to_h264.py    # Video URL migration
├── video_urls_backup_YYYYMMDD_HHMMSS.sql       # Backup files (auto-generated)
└── migration_log_YYYYMMDD_HHMMSS.log           # Log files (auto-generated)
```

## 🚀 Running Migrations

### Option 1: Run Individual Migration

```bash
# Preview changes (dry run)
python migrations/2025_07_24_migrate_video_urls_to_h264.py --dry-run

# Apply migration
python migrations/2025_07_24_migrate_video_urls_to_h264.py

# Use custom database URL
python migrations/2025_07_24_migrate_video_urls_to_h264.py --database-url "postgresql://user:pass@host:port/db"
```

### Option 2: Use Migration Runner (Recommended)

```bash
# List all migrations
python migrations/migration_runner.py --list

# Run specific migration
python migrations/migration_runner.py --run 2025_07_24_migrate_video_urls_to_h264

# Run with dry-run mode
python migrations/migration_runner.py --run 2025_07_24_migrate_video_urls_to_h264 --dry-run
```

## 📦 Production Deployment

For production deployments, follow these steps:

### 1. Pre-deployment Checklist
- [ ] Test migration on staging environment
- [ ] Verify backup system is working
- [ ] Schedule maintenance window if needed
- [ ] Notify team about deployment

### 2. Deployment Steps
```bash
# 1. Backup production database
pg_dump $DATABASE_URL > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# 2. Run migration with dry-run first
python migrations/2025_07_24_migrate_video_urls_to_h264.py --dry-run

# 3. Apply migration
python migrations/2025_07_24_migrate_video_urls_to_h264.py

# 4. Verify migration success
python migrations/migration_runner.py --verify 2025_07_24_migrate_video_urls_to_h264
```

### 3. Rollback Plan
Each migration automatically creates a backup file that can be used for rollback:
```bash
# Restore from backup if needed
psql $DATABASE_URL < migrations/video_urls_backup_YYYYMMDD_HHMMSS.sql
```

## 📝 Creating New Migrations

### 1. Template Structure
```python
#!/usr/bin/env python3
"""
Migration: [Description]
Date: YYYY-MM-DD
Purpose: [Detailed purpose]
"""

import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Standard migration template...
```

### 2. Migration Guidelines
- Always include dry-run functionality
- Create automatic backups before changes
- Include comprehensive logging
- Add verification steps
- Handle errors gracefully with rollback
- Document the migration purpose and changes

### 3. Testing Migrations
```bash
# Test on local database
python your_migration.py --dry-run

# Test with different database
python your_migration.py --database-url "postgresql://localhost:5432/test_db" --dry-run
```

## 🔧 Migration Tools

### Migration Runner Commands
```bash
# List all available migrations
python migrations/migration_runner.py --list

# Check migration status
python migrations/migration_runner.py --status

# Run specific migration
python migrations/migration_runner.py --run MIGRATION_NAME

# Verify migration
python migrations/migration_runner.py --verify MIGRATION_NAME
```

## 📊 Monitoring and Logs

All migrations generate:
- **Log files**: `migration_log_YYYYMMDD_HHMMSS.log`
- **Backup files**: `*_backup_YYYYMMDD_HHMMSS.sql`
- **Console output**: Real-time migration progress

Log levels:
- `INFO`: Normal operation messages
- `WARNING`: Non-critical issues
- `ERROR`: Critical errors requiring attention

## 🚨 Emergency Procedures

### If Migration Fails
1. Check the error message in logs
2. Verify database connection
3. Check for conflicting data
4. Use backup file to restore if needed
5. Fix issue and re-run migration

### If Production Issues Occur
1. Immediately check migration logs
2. Verify data integrity
3. Use backup to rollback if critical
4. Contact team for assistance

## 📚 Migration History

| Date | Migration | Purpose | Status |
|------|-----------|---------|--------|
| 2025-01-24 | `migrate_video_urls_to_h264` | Update video URLs for Android compatibility | ✅ Ready |

## 🔐 Security Notes

- Never commit database URLs to git
- Use environment variables for sensitive data
- Backup files may contain sensitive data - handle securely
- Test migrations on non-production data first
- Always verify migration results before deployment

## 📞 Support

For migration issues or questions:
1. Check the logs first
2. Review this documentation
3. Test on staging environment
4. Contact the development team if needed 