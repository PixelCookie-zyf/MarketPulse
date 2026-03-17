const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const DEFAULT_UA = "Mozilla/5.0 (MarketPulse; Cloudflare Worker)";
const INDEX_SPOT_FS = "i:100.HSI,i:100.N225,i:100.KS11,i:100.DJIA,i:100.SPX,i:100.NDX";

const INDEX_KLINE_SECIDS = {
  DJI: "100.DJIA",
  SPX: "100.SPX",
  IXIC: "100.NDX",
  HSI: "100.HSI",
  N225: "100.N225",
  KOSPI: "100.KS11",
};

const FUTURE_KLINE_SECIDS = {
  IXIC: "103.NQ00Y",
  SPX: "103.ES00Y",
  DJI: "103.YM00Y",
};

// Commodity futures kline security IDs (market_code.symbol)
const COMMODITY_KLINE_SECIDS = {
  XAU: "101.GC00Y",      // COMEX Gold
  XAG: "101.SI00Y",      // COMEX Silver
  BRENT: "112.B00Y",     // ICE Brent
  COPPER: "101.HG00Y",   // COMEX Copper
};

const COMMODITY_SPOT_URL = "https://futsseapi.eastmoney.com/list/COMEX,NYMEX,COBOT,SGX,NYBOT,LME,MDEX,TOCOM,IPE";
const COMMODITY_SPOT_TOKEN = "58b2fa8f54638b60b87d69b31969089c";

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }), env);
    }

    if (request.method !== "GET") {
      return json({ error: "method_not_allowed" }, 405, env);
    }

    if (!isAuthorized(request, env)) {
      return json({ error: "unauthorized" }, 401, env);
    }

    const url = new URL(request.url);
    const cache = caches.default;
    const cacheKey = new Request(url.toString(), request);
    const cached = await cache.match(cacheKey);
    if (cached) {
      return withCors(cached, env);
    }

    let upstreamUrl;
    let upstreamHeaders = {
      "accept": "application/json,text/plain,*/*",
      "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
      "referer": "https://quote.eastmoney.com/",
      "user-agent": env.UPSTREAM_USER_AGENT || DEFAULT_UA,
    };

    if (url.pathname === "/global-indices/spot") {
      upstreamUrl = buildIndexSpotUrl();
    } else if (url.pathname === "/global-indices/kline") {
      upstreamUrl = buildKlineUrl(INDEX_KLINE_SECIDS, url.searchParams);
    } else if (url.pathname === "/global-futures/kline") {
      upstreamUrl = buildKlineUrl(FUTURE_KLINE_SECIDS, url.searchParams);
    } else if (url.pathname === "/global-commodities/spot") {
      upstreamUrl = buildCommoditySpotUrl();
      upstreamHeaders.referer = "https://quote.eastmoney.com/center/gridlist.html";
    } else if (url.pathname === "/global-commodities/kline") {
      upstreamUrl = buildKlineUrl(COMMODITY_KLINE_SECIDS, url.searchParams);
    } else {
      return json({ error: "not_found" }, 404, env);
    }
    if (!upstreamUrl) {
      return json({ error: "unsupported_symbol" }, 400, env);
    }

    const upstream = await fetch(upstreamUrl, {
      headers: upstreamHeaders,
      cf: {
        cacheEverything: true,
        cacheTtl: 30,
      },
    });

    const body = await upstream.text();
    const response = new Response(body, {
      status: upstream.status,
      headers: {
        ...JSON_HEADERS,
        "cache-control": "public, max-age=30",
      },
    });

    const finalResponse = withCors(response, env);
    if (upstream.ok) {
      ctx.waitUntil(cache.put(cacheKey, finalResponse.clone()));
    }
    return finalResponse;
  },
};

function isAuthorized(request, env) {
  if (!env.PROXY_TOKEN) {
    return true;
  }
  return request.headers.get("x-proxy-token") === env.PROXY_TOKEN;
}

function buildIndexSpotUrl() {
  const upstream = new URL("https://push2.eastmoney.com/api/qt/clist/get");
  upstream.search = new URLSearchParams({
    np: "2",
    fltt: "1",
    invt: "2",
    fs: INDEX_SPOT_FS,
    fields: "f12,f13,f14,f292,f1,f2,f4,f3,f152,f17,f18,f15,f16,f6,f7,f124",
    fid: "f3",
    pn: "1",
    pz: "20",
    po: "1",
    dect: "1",
    wbp2u: "|0|0|0|web",
  }).toString();
  return upstream.toString();
}

function buildKlineUrl(secidMap, searchParams) {
  const symbol = searchParams.get("symbol") || "";
  const period = searchParams.get("period") || "1d";
  const secid = secidMap[symbol];
  if (!secid) {
    return null;
  }

  const upstream = new URL("https://push2his.eastmoney.com/api/qt/stock/kline/get");
  upstream.search = new URLSearchParams({
    secid,
    klt: period === "5d" ? "15" : "1",
    fqt: "1",
    lmt: period === "5d" ? "800" : "400",
    end: "20500000",
    iscca: "1",
    fields1: "f1,f2,f3,f4,f5,f6,f7,f8",
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64",
    ut: "f057cbcbce2a86e2866ab8877db1d059",
    forcect: "1",
  }).toString();
  return upstream.toString();
}

function buildCommoditySpotUrl() {
  const upstream = new URL(COMMODITY_SPOT_URL);
  upstream.search = new URLSearchParams({
    orderBy: "dm",
    sort: "desc",
    pageSize: "200",
    pageIndex: "0",
    token: COMMODITY_SPOT_TOKEN,
    field: "dm,sc,name,p,zsjd,zde,zdf,f152,o,h,l,zjsj,vol,wp,np,ccl",
    blockName: "callback",
  }).toString();
  return upstream.toString();
}

function json(payload, status, env) {
  return withCors(
    new Response(JSON.stringify(payload), {
      status,
      headers: JSON_HEADERS,
    }),
    env,
  );
}

function withCors(response, env) {
  const headers = new Headers(response.headers);
  headers.set("access-control-allow-methods", "GET, OPTIONS");
  headers.set("access-control-allow-headers", "Content-Type, X-Proxy-Token");
  if (env.ALLOWED_ORIGIN) {
    headers.set("access-control-allow-origin", env.ALLOWED_ORIGIN);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
