So since I was using V2 data base for testing on July 28th, i copied and pasted the apple user data at the time into v2 database and now we have stale apple user data in the V2 database (it is not being updated by the apple users because they are being directed to v1), and the v2 database also contains Android User data for the new Android users that are creating accounts since we released android recently. We released the updated version of the android app around a week ago on september 1. Right now all apple user's most updated data is in v1 database since we have not done the migration and app update for apple users yet, and v2 has the most up to date data for android users since android users data is automatically being put into v2 when they create an account (so there should not be any android users in the v1 database)

if there emails are in both v1 and v2, that means those are apple users that have their most up to date data in v1 and have stale data in v2, so they need their up to date data in v1 to be transferred to v2. If they have a email in v1 but not in v2, that means that we just need to make a new entry for them in v2 and migrate their data. if their data is in v2 and not v1, that means they are android users and we do not want to touch or delete their data

so since i we currently have stale v1 data in v2 database what if we updated the migration script so that If a v1 email exists in v2 then overwrite the stale v2 data with the corresponding apple user's current v1 data since that is the apple user's most updated data, so that the apple user will be able to use the v2 schema and has all of their history and data still. If their email does not exist in v2, create a new entry for them in v2 since they were not part of the stale data that I pasted into v2 on july 28th


realize that v1 and v2 do not match, which is why were having to do migration in the first place. you do not need to add anything or any columns to v1, we are just trying to move all v1 user's data to staging/v2 (whichever one were working on if testing mode is true or false)


In the staging database, we now have stale data that belongs to Apple users from the V1 database and up-to-date android User data. There is no way to determine whether data in the staging database if it is stale data or Android data so lets not worry about that.



NOTE: STAGING IS THE TEST ENVIRONMENT WHERE WE DO ALL OUR TESTING