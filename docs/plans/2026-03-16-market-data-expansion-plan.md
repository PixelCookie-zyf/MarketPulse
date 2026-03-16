# Market Data Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand the commodity dashboard to cover a broader set of major commodities and replace the fragile US index fetch path with a more stable source for overview rendering.

**Architecture:** Keep the existing overview response contract unchanged while broadening backend fetch coverage. Preserve GoldAPI for precious metals, expand Alpha Vantage commodity coverage where it is a good fit, and source US index quotes from AKShare global spot data so free-tier Alpha Vantage limits do not blank the dashboard.

**Tech Stack:** FastAPI, APScheduler, AKShare, Alpha Vantage, pytest

---

### Task 1: Lock desired behavior with tests

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/tests/test_fetchers.py`

**Step 1: Write the failing tests**

- Add a test that asserts the commodity spec list includes the expanded set of symbols needed by the dashboard.
- Add a test that asserts the global spot normalizer can transform a US index row into the existing `IndexItem` payload shape.

**Step 2: Run tests to verify they fail**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: FAIL because the expanded commodity symbols and AKShare global quote normalizer do not exist yet.

**Step 3: Write minimal implementation**

- Expand the commodity spec list in the Alpha Vantage fetcher.
- Add a global index row normalizer for US indices.

**Step 4: Run tests to verify they pass**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: PASS.

### Task 2: Replace the US index source and keep overview stable

**Files:**
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/fetchers/akshare_fetcher.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/fetchers/alphavantage_fetcher.py`
- Modify: `/Users/zyf/VibeCodes/MarketPulse/backend/app/scheduler.py`

**Step 1: Write the failing test**

- Add or extend tests so that US index rows can be normalized from AKShare global spot data.

**Step 2: Run targeted test to verify it fails**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: FAIL on the new US-index normalization coverage.

**Step 3: Write minimal implementation**

- Add a new AKShare fetch path for US indices using global spot data.
- Update scheduler index refresh to use AKShare for US data and keep Alpha Vantage only for JP/KR indices.
- Leave the overview schema unchanged so iOS works without model changes.

**Step 4: Run tests to verify it passes**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests/test_fetchers.py -q`

Expected: PASS.

### Task 3: Verify the end-to-end payload

**Files:**
- No code changes required unless verification reveals a gap

**Step 1: Run the full backend suite**

Run: `source backend/.venv/bin/activate && python -m pytest backend/tests -q`

Expected: PASS with zero failures.

**Step 2: Run the API locally and inspect overview**

Run:

```bash
source backend/.venv/bin/activate
cd backend
ENABLE_SCHEDULER=false CACHE_BACKEND=memory GOLDAPI_KEY='***' ALPHAVANTAGE_KEY='***' uvicorn app.main:app --port 8001
```

Then in another shell:

```bash
source backend/.venv/bin/activate
python - <<'PY'
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:8001/api/v1/overview", timeout=60) as response:
    data = json.load(response)
print("commodities", [item["symbol"] for item in data["commodities"]])
print("us indices", [item["symbol"] for item in data["indices"]["us"]])
PY
```

Expected:
- Commodity list includes the expanded symbols that successfully resolve from the live providers.
- `indices.us` is non-empty.

### Task 4: Commit and push

**Files:**
- Include all modified backend files and the plan doc if it remains relevant

**Step 1: Review the diff**

Run: `git diff -- backend/app backend/tests docs/plans/2026-03-16-market-data-expansion-plan.md`

**Step 2: Commit**

Run:

```bash
git add backend/app backend/tests docs/plans/2026-03-16-market-data-expansion-plan.md
git commit -m "feat: expand commodities and stabilize us indices"
```

**Step 3: Push**

Run: `git push origin main`
