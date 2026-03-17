# Eastmoney Proxy Worker

This worker exists to proxy the Eastmoney endpoints that are blocked from the backend runtime.

## Endpoints

- `GET /global-indices/spot`
- `GET /global-indices/kline?symbol=DJI|SPX|IXIC|HSI|N225|KOSPI&period=1d|5d`
- `GET /global-futures/kline?symbol=IXIC|SPX|DJI&period=1d|5d`

## Deploy

1. Create a Worker and copy in [`eastmoney-proxy-worker.js`](/Users/zyf/VibeCodes/MarketPulse/cloudflare/eastmoney-proxy-worker.js).
2. Set secrets and vars:
   - `wrangler secret put PROXY_TOKEN`
   - `ALLOWED_ORIGIN=https://your-backend-domain`
   - Optional: `UPSTREAM_USER_AGENT=Mozilla/5.0 (MarketPulse)`
3. Deploy with `wrangler deploy`.

## Backend Wiring

Set these backend env vars:

- `EASTMONEY_PROXY_BASE_URL=https://<your-worker>.workers.dev`
- `EASTMONEY_PROXY_TOKEN=<same token as PROXY_TOKEN>`

Once set, the backend will:

- fill `us/hk/jp/kr` global index groups from the proxy
- fetch global index charts and sparklines through the proxy when available

## Notes

- The worker is intentionally whitelist-only, not a generic forward proxy.
- Cache TTL is 30 seconds to reduce Eastmoney pressure without making charts feel stale.
- If you update the worker code in this repo, you must run `npx wrangler deploy` again for the changes to take effect.
