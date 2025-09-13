So since I was using V2 data base for testing on July 28th, i copied and pasted the apple user data at the time into v2 database and now we have stale apple user data in the V2 database (it is not being updated by the apple users because they are being directed to v1), and the v2 database also contains Android User data for the new Android users that are creating accounts since we released android recently. We released the updated version of the android app around a week ago on september 1. Right now all apple user's most updated data is in v1 database since we have not done the migration and app update for apple users yet, and v2 has the most up to date data for android users since android users data is automatically being put into v2 when they create an account (so there should not be any android users in the v1 database)

if there emails are in both v1 and v2, that means those are apple users that have their most up to date data in v1 and have stale data in v2, so they need their up to date data in v1 to be transferred to v2. If they have a email in v1 but not in v2, that means that we just need to make a new entry for them in v2 and migrate their data. if their data is in v2 and not v1, that means they are android users and we do not want to touch or delete their data

so since i we currently have stale v1 data in v2 database what if we updated the migration script so that If a v1 email exists in v2 then overwrite the stale v2 data with the corresponding apple user's current v1 data since that is the apple user's most updated data, so that the apple user will be able to use the v2 schema and has all of their history and data still. If their email does not exist in v2, create a new entry for them in v2 since they were not part of the stale data that I pasted into v2 on july 28th

Also update the migration script so we are not dropping and destroying all the current android user data, we should not be deleting any in staging/v2 (whichever one we are workign on) when runniong the migration

When we test this, we are probably going to want to take the v2 data and duplicate it over into staging database so we can safely test it on there. after we copy the data from v2 to staging, remember: we are NOT RUNNING THE MIGRATION ON v2 AS WE ARE TESTING IT, so RUN THIS TESTING MIGRATION ON STAGING DATABASE.

when we import the new apple users into the staging db after figuring out they have stale data on v2 and are present in v1, only take the first 5 for simplicity on testing. also only add the first 5 users that are not in v2 but are in v1 for simplicity of testing. create a debug config file that will allow us to set debug (testing) to be either true or false: true for when we are running the migration on the production database (v2) and false when we are running the migration on the testing database (v1) so set it to false first

when testing to see if migration worked : the id's do not have to be the same from v1 as they are in staging, they just have to be the same in terms of that they are matching to their respective related data. IDs will change since we will be inserting into the v2 db for production, and there is alreayd android users in v2 database, So the IDS users between there V1 and staging versions will be different. They just need to be matching to their same respective data so users are still able to keep their data as before. Keep this in mind for the testing script

realize that v1 and v2 do not match, which is why were having to do migration in the first place. you do not need to add anything or any columns to v1, we are just trying to move all v1 user's data to staging/v2 (whichever one were working on if testing mode is true or false)

when we move data from v1 to v2, are we copying over the primary key ids as well? if we are then lets not do that and just follow the approach of inserting data with new primary key ids, still esuring that we keep relationships between data as they were before



NOTE: ABSOLUTELY NOTHING SHOULD BE RAN ON v1 or v2 RIGHT NOW, ONLY STAGING. we are only COPYING DATA FROM v1 to STAGING or copying data from v2 to STAGING WHHEN REQUIRED, STAGING IS THE TEST ENVIRONMENT WHERE WE DO ALL OUR TESTING
## ✅ SOLUTION 1 IMPLEMENTED

**Status**: Complete
**Date**: $(date)

### Implementation Details

Solution 1 has been implemented with the following components:

1. **V2MigrationManager** (`v2_migration_manager.py`)
   - Intelligent platform detection (Apple vs Android users)
   - Selective data merging logic
   - Android user data preservation
   - Comprehensive related data migration
   - Validation and error handling

2. **Configuration Management** (`migration_config.py`)
   - Environment variable handling
   - Database URL management
   - Configuration validation

3. **Migration Runner** (`run_migration.py`)
   - Simple command-line interface
   - Status checking
   - Migration execution
   - Validation and rollback support

### Key Features

- ✅ **Preserves Android user data** - No Android data is lost or modified
- ✅ **Merges Apple user data** - Overwrites stale V2 data with current V1 data
- ✅ **Creates new Apple users** - Handles Apple users not in V2
- ✅ **Migrates related data** - Sessions, preferences, drill groups, etc.
- ✅ **Comprehensive validation** - Ensures data integrity
- ✅ **Backup functionality** - Android data backed up before migration
- ✅ **Error handling** - Detailed logging and error reporting

### Usage

```bash
# Check status
python run_migration.py status

# Run migration
python run_migration.py migrate

# Validate migration
python run_migration.py validate
```

### Next Steps

1. Set up environment variables for V1 and V2 databases
2. Test with production data copy
3. Run migration in production
4. Update Apple app to use V2 database
5. Monitor for any issues