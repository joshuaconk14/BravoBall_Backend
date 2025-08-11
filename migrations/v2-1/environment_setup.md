# Environment Variables Setup for V2 Migration

## Overview
The migration scripts now use environment variables instead of hard-coded database URLs for better security and flexibility.

## Required Environment Variables

### For Migration Scripts
```bash
# Production database (source for data copy)
PRODUCTION_DATABASE_URL=postgresql://prod_user:prod_pass@prod_host:5432/bravoballdb

# Staging database (current target)
STAGING_DATABASE_URL=postgresql://staging_user:staging_pass@staging_host:5432/bravoball_staging_db

# V2 database (for blue-green deployment)
V2_DATABASE_URL=postgresql://v2_user:v2_pass@v2_host:5432/bravoball_v2_db
```

### For Main Application
```bash
# Main application database (used by db.py)
DATABASE_URL=postgresql://username:password@host:port/database
```

## Setup Instructions

### 1. Local Development
Create a `.env` file in the BravoBall_Backend directory:
```bash
# Copy the current staging URL for local testing
STAGING_DATABASE_URL=postgresql://bravoball_staging_db_user:DszQQ1qg7XH2ocCNSCU844S43SMU4G4V@dpg-d21l5oh5pdvs7382nib0-a.oregon-postgres.render.com/bravoball_staging_db

# Add V2 URL when created
V2_DATABASE_URL=postgresql://v2_user:v2_pass@v2_host:5432/bravoball_v2_db
```

### 2. Render Deployment
Set environment variables in Render dashboard:

#### Staging Backend Service
- `DATABASE_URL` → staging database URL
- `STAGING_DATABASE_URL` → staging database URL

#### V2 Backend Service  
- `DATABASE_URL` → V2 database URL
- `V2_DATABASE_URL` → V2 database URL

#### Production Backend Service
- `DATABASE_URL` → production database URL
- `PRODUCTION_DATABASE_URL` → production database URL

## Migration Usage Examples

### Test with Staging Database (Default)
```bash
python migrations/v2-1/complete_v2_migration.py --dry-run
```

### Migrate to V2 Database (Blue-Green Deployment)
```bash
python migrations/v2-1/complete_v2_migration.py --target-db v2 --skip-data-import
```

### Override Database URLs
```bash
python migrations/v2-1/complete_v2_migration.py \
  --v2-url "postgresql://new_v2_url" \
  --target-db v2
```

## Benefits

1. **Security**: No hard-coded credentials in source code
2. **Flexibility**: Easy to switch between environments
3. **Blue-Green**: Support for parallel v1/v2 databases
4. **Testing**: Safe testing with staging before production
5. **Rollback**: Easy to revert to previous database if needed

## Migration Workflow

1. **Setup Staging**: Test environment variables with staging
2. **Create V2 DB**: Set up new V2 database and backend service
3. **Migrate V2**: Run migration targeting V2 database
4. **Test V2**: Thoroughly test V2 database and backend
5. **Deploy Flutter**: Update Flutter app to conditionally use V2
6. **Gradual Rollout**: Move users from V1 to V2 gradually
7. **Cleanup**: Retire V1 database once migration complete 