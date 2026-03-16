# Market Data Reliability Follow-up Design

## Goal

Improve MarketPulse's data completeness and operational reliability before any further UI polish. This follow-up focuses on four concrete outcomes:

1. The backend root route `/` should return a healthy response so Render no longer reports `404` for its probe.
2. Hong Kong market coverage should include a stable `恒生指数` entry in `indices.hk`.
3. The commodity dashboard should show a broader and more reliable set of major commodities.
4. The iOS unit test target should build and run cleanly without the `.xctest` packaging conflict.

## Current Problems

### Root Route

The backend currently exposes `/health` and `/api/v1/*`, but not `/`. Render probes `/`, so the service is healthy but logs repeated `404` responses.

### Hong Kong Index Coverage

The current Hong Kong fetch path in `AKShareFetcher.fetch_hk_index()` relies on an Eastmoney-backed AKShare call. In this environment that path is intermittently blocked by proxy/network failures, so `indices.hk` is often empty.

### Commodity Coverage

The app now shows precious metals from GoldAPI and several broader commodities from a new public quote source, but the reliability goal is broader than “some symbols appear eventually”. We want the aggregate list to be intentionally curated, fetched through stable sources, and combined in a way that avoids cold-start gaps.

### iOS Test Target

`xcodebuild test` is currently blocked by a generated project configuration issue that creates duplicate `.xctest` output commands. The app target builds and runs, but the test target configuration is not correct enough for repeatable CI-style verification.

## Recommended Approach

Use a reliability-first mixed-source design:

- Keep `GoldAPI` for `XAU` and `XAG`, since it is already working well for precious metals.
- Keep `AKShare` for mainland China indices and A-share sectors, where we already have working normalization and sparkline support.
- Move `Hong Kong` index coverage onto the same stable public market-data style used for the restored US index data, instead of the current Eastmoney-dependent Hong Kong path.
- Continue using the stable public quote source for broader commodities, but make the combined commodity refresh path more deliberate and resilient.
- Fix the generated iOS project configuration at the source (`project.yml`) so the `.xctest` conflict does not reappear.

This keeps the response contract stable for the iOS app while reducing fragility from the most failure-prone paths.

## Data Design

### Root Route

Add a lightweight root endpoint on the FastAPI app:

- Path: `/`
- Response: a short JSON payload indicating service name, status, and key routes

This endpoint is not meant to replace `/health`; it exists primarily to make hosting probes and manual browser checks friendlier.

### Hong Kong Index

Expose `恒生指数` in `indices.hk` using a stable public quote/history source with this normalized shape:

- `symbol`
- `name`
- `value`
- `change`
- `change_pct`
- `high`
- `low`
- `volume`
- `sparkline`

The backend should still return `indices.hk` as a list, so the iOS models remain unchanged.

### Commodity Set

The intended commodity dashboard set after this follow-up is:

- `XAU`
- `XAG`
- `WTI`
- `BRENT`
- `NATGAS`
- `COPPER`
- `CORN`
- `WHEAT`
- `COTTON`
- `SUGAR`
- `COFFEE`

These should come from:

- GoldAPI: `XAU`, `XAG`
- Stable public quote source: the broader commodity set above

The combined cache should continue to publish a single `commodities:all` payload so the app only needs one overview fetch.

### Aggregation Rules

Commodity aggregation should favor completeness and predictable ordering:

- Fetch precious metals and broader commodities separately
- Retry broader commodity quote fetches when a symbol transiently fails
- Combine the final list in a deterministic order suitable for the dashboard

The goal is to avoid the current situation where concurrent transient failures can make symbols disappear on cold start.

## iOS Test Target Design

The `.xctest` packaging problem should be fixed in the source generator config rather than by hand-editing the generated `.xcodeproj`.

Expected result:

- `xcodebuild build` continues to pass
- `xcodebuild test` becomes viable
- Future regenerations of the project preserve the fix

Any project file changes that are only generator noise should be avoided unless they are necessary outputs of the corrected configuration.

## Error Handling

- If a non-critical market source fails, the backend should still return the rest of the overview payload.
- If `恒生指数` cannot be fetched, `indices.hk` may remain empty, but the fetch path should be chosen to minimize that outcome.
- Root route failure should never affect `/health` or API routes.
- Commodity refresh should degrade gracefully without dropping the entire combined payload.

## Testing Strategy

### Backend

- Add or update tests for:
  - root route `/`
  - Hong Kong index normalization/output
  - commodity spec coverage
  - combined commodity refresh behavior

### iOS

- Keep the sparkline normalization test
- Repair the test target so `xcodebuild test` can run

### End-to-End Verification

- Run backend tests
- Run iOS build and tests
- Start the backend locally and confirm:
  - `/` returns a non-404 JSON response
  - `/health` returns healthy status
  - `/api/v1/overview` includes:
    - `indices.hk` with `恒生指数`
    - the expanded commodity set

## Non-Goals

- No visual redesign of overview or indices screens in this pass
- No new paid data providers
- No API contract changes for the iOS app unless strictly required for reliability
