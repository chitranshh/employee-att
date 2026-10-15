# Review

I reviewed the API around the main attendance flow: creating and completing records, correcting them, reading audit history, and calculating summaries.

## What is working

- Punches are validated before they are written. Duplicate employee/day records are also protected by a MongoDB unique index.
- Corrections retain the old and new values, the reason, the actor, and the time of the change.
- Daily and employee analytics are computed in MongoDB, which keeps the application from pulling the full attendance collection into memory.
- The automated tests cover the API flow and the request validation rules. They currently pass with 9 tests.

## Things to address before production

- The correction endpoints do not yet enforce authentication or manager permissions. `corrected_by` should eventually come from the authenticated user rather than the request body.
- The audit insert and attendance update are separate MongoDB writes. A transaction would prevent a partial correction when MongoDB is running as a replica set.
- The business currently uses UTC to decide which day a punch belongs to. If the organisation works in another timezone, that rule should be made explicit and tested.

## Verification

- The API tests use `mongomock`, so they do not require a live database.
- A live MongoDB Atlas connection was also checked separately.
