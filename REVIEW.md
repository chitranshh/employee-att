# Review

## Scope

The service records employee punch-in and punch-out events, supports audited corrections, and exposes attendance analytics through a FastAPI API backed by MongoDB.

## Current risks

- Correction endpoints have no authentication or authorization. In production, the correcting actor should come from the authenticated identity and manager permissions should be enforced.
- A correction writes the audit record and attendance update separately. A MongoDB transaction would provide all-or-nothing behavior when running against a replica set.
- Attendance days are calculated in UTC. This should be changed if the business operates in a local timezone.

## Verification

- Unit and API tests use `mongomock` for deterministic checks.
- A live MongoDB Atlas ping was verified locally.
- The test suite currently passes with 9 tests.
