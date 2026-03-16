# Data Reliability Follow-up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the backend more host-friendly and data-complete by adding a root route, restoring Hong Kong index coverage, expanding reliable commodity coverage, and fixing the iOS unit-test target.

**Architecture:** Keep the API contract stable for the iOS app while improving reliability under the hood. Use a stable public quote/history source for Hong Kong and broader commodities, keep GoldAPI for precious metals, preserve AKShare for mainland data, and fix the Xcode project generator config so test-target issues do not return on regeneration.

**Tech Stack:** FastAPI, APScheduler, AKShare, GoldAPI, public quote/history source, XcodeGen, SwiftUI, XCTest, pytest

---

### Task 1: Add root-route coverage with a failing test first

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/tests/test_main.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/main.py`

**Step 1: Write the failing test**

Add a test that requests `/` and asserts the route responds with a non-404 JSON payload containing service metadata.

**Step 2: Run test to verify it fails**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_main.py -q`

Expected: FAIL because `/` is not implemented yet.

**Step 3: Write minimal implementation**

Add a lightweight root route on the FastAPI app that returns:

```python
{
    "name": "MarketPulse API",
    "status": "ok",
    "routes": ["/health", "/api/v1/overview"]
}
```

**Step 4: Run test to verify it passes**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_main.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_main.py backend/app/main.py
git commit -m "feat: add backend root status route"
```

### Task 2: Restore Hong Kong index coverage with stable normalization

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/tests/test_fetchers.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/fetchers/stooq_fetcher.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/fetchers/akshare_fetcher.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/scheduler.py`

**Step 1: Write the failing test**

Add a test for a Hong Kong index normalizer that maps a stable quote/history payload to:

```python
{
    "symbol": "HSI",
    "name": "恒生指数",
    "value": 18456.23,
    "change": -132.40,
    "change_pct": -0.71,
    "high": 18620.50,
    "low": 18388.10,
    "volume": 0.0,
    "sparkline": [18720.0, 18690.0, 18580.0, 18456.23],
}
```

**Step 2: Run test to verify it fails**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: FAIL because no Hong Kong stable-source normalizer exists yet.

**Step 3: Write minimal implementation**

- Add Hong Kong index specs to the stable-source fetcher
- Add a Hong Kong fetch method that returns `恒生指数`
- Update the scheduler index refresh path so `indices.hk` is populated from that fetcher
- Remove or demote the fragile Eastmoney-backed Hong Kong path

**Step 4: Run test to verify it passes**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_fetchers.py backend/app/fetchers/stooq_fetcher.py backend/app/fetchers/akshare_fetcher.py backend/app/scheduler.py
git commit -m "feat: restore hong kong index coverage"
```

### Task 3: Expand commodity coverage and stabilize aggregation

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/tests/test_fetchers.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/tests/test_main.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/fetchers/stooq_fetcher.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/scheduler.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/routers/overview.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/routers/commodities.py`

**Step 1: Write the failing tests**

- Add or extend a test that asserts the intended commodity set includes:

```python
{"XAU", "XAG", "WTI", "BRENT", "NATGAS", "COPPER", "CORN", "WHEAT", "COTTON", "SUGAR", "COFFEE"}
```

- Add an overview or commodities test that ensures the combined response reads from the stable broader-commodity cache path.

**Step 2: Run tests to verify they fail**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py backend/tests/test_main.py -q`

Expected: FAIL if the broader commodity list or fallback path is incomplete.

**Step 3: Write minimal implementation**

- Keep precious metals from GoldAPI
- Keep broader commodities from the stable-source fetcher
- Ensure broader commodity fetches use deterministic ordering plus retry logic
- Ensure combined cache paths read from the stable-source commodity cache consistently

**Step 4: Run tests to verify they pass**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py backend/tests/test_main.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_fetchers.py backend/tests/test_main.py backend/app/fetchers/stooq_fetcher.py backend/app/scheduler.py backend/app/routers/overview.py backend/app/routers/commodities.py
git commit -m "feat: stabilize broader commodity aggregation"
```

### Task 4: Fix the iOS unit-test target at the generator level

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/ios/project.yml`
- Regenerate: `/Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj`
- Modify if needed: `/Users/zyf/VibeCodes/MarketPulse/ios/MarketPulseTests/Info.plist`
- Test: `/Users/zyf/VibeCodes/MarketPulse/ios/MarketPulseTests/MarketPulseTests.swift`

**Step 1: Write the failing verification step**

Use the existing failure as the red state:

Run: `xcodebuild test -project /Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj -scheme MarketPulse -destination 'platform=iOS Simulator,OS=18.5,name=iPhone 16'`

Expected: FAIL with the duplicate `.xctest` output error.

**Step 2: Write minimal configuration fix**

- Correct the test target configuration in `project.yml`
- Regenerate the project from the config
- Keep the app target configuration unchanged unless the generator requires a paired adjustment

**Step 3: Run build verification**

Run: `xcodebuild build -project /Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj -scheme MarketPulse -destination 'platform=iOS Simulator,OS=18.5,name=iPhone 16'`

Expected: PASS.

**Step 4: Run test verification**

Run: `xcodebuild test -project /Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj -scheme MarketPulse -destination 'platform=iOS Simulator,OS=18.5,name=iPhone 16'`

Expected: PASS.

**Step 5: Commit**

```bash
git add ios/project.yml ios/MarketPulse.xcodeproj ios/MarketPulseTests
git commit -m "fix: restore ios unit test target"
```

### Task 5: Run full verification and push

**Files:**
- Review all modified files from previous tasks

**Step 1: Run backend suite**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests -q`

Expected: PASS.

**Step 2: Run local backend and verify live payloads**

Run:

```bash
source backend/.venv/bin/activate
cd backend
ENABLE_SCHEDULER=false CACHE_BACKEND=memory GOLDAPI_KEY='***' ALPHAVANTAGE_KEY='***' uvicorn app.main:app --port 8001
```

Then in another shell:

```bash
python - <<'PY'
import json, urllib.request
for path in ('/', '/health', '/api/v1/overview'):
    with urllib.request.urlopen(f'http://127.0.0.1:8001{path}', timeout=90) as response:
        print(path, response.status)
        payload = json.load(response)
        if path == '/api/v1/overview':
            print('hk', payload['indices']['hk'])
            print('commodities', [item['symbol'] for item in payload['commodities']])
PY
```

Expected:
- `/` returns JSON, not `404`
- `/health` returns healthy status
- `/api/v1/overview` includes `indices.hk`
- `/api/v1/overview` includes the expanded commodity set

**Step 3: Run iOS build and tests**

Run:

```bash
xcodebuild build -project /Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj -scheme MarketPulse -destination 'platform=iOS Simulator,OS=18.5,name=iPhone 16'
xcodebuild test -project /Users/zyf/VibeCodes/MarketPulse/ios/MarketPulse.xcodeproj -scheme MarketPulse -destination 'platform=iOS Simulator,OS=18.5,name=iPhone 16'
```

Expected: PASS.

**Step 4: Review diff**

Run: `git diff -- backend ios docs/plans/2026-03-16-data-reliability-followup-design.md docs/plans/2026-03-16-data-reliability-followup-implementation.md`

**Step 5: Commit and push**

Run:

```bash
git add backend ios docs/plans/2026-03-16-data-reliability-followup-design.md docs/plans/2026-03-16-data-reliability-followup-implementation.md
git commit -m "feat: improve market data reliability"
git push origin main
```
