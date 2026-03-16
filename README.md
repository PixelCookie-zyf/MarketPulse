# MarketPulse

Global market monitoring dashboard with a Python FastAPI backend and a native SwiftUI iOS client.

## Features

- Commodities: gold, silver, copper, and crude oil
- Global indices: US, Japan, Korea, Hong Kong, and mainland China
- China sector movers with turnover and leading stocks
- Light and dark themes for a dashboard-style mobile experience

## Tech Stack

- Backend: Python, FastAPI, AKShare, APScheduler, Redis-compatible cache
- iOS: Swift, SwiftUI, Swift Charts

## Project Structure

- `backend/`: FastAPI application and tests
- `ios/`: SwiftUI app project
- `docs/`: design and implementation plans

## Local Development

1. Create the backend virtual environment and install dependencies:
   `python3 -m venv backend/.venv && source backend/.venv/bin/activate && pip install -r backend/requirements.txt`
2. Start the backend:
   `cd backend && uvicorn app.main:app --reload --port 8000`
3. Generate the iOS project:
   `cd ios && ~/bin/xcodegen generate`

## Notes

- `backend/.env` is configured locally with the provided GoldAPI and Alpha Vantage keys.
- The backend falls back to in-memory caching when Redis is unavailable, which keeps local development working on this machine.
- Alpha Vantage free-tier limits are tight, so US/JP/KR index and copper/oil refreshes are intentionally scheduled at 12-hour intervals.
