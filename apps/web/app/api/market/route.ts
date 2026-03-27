import { NextResponse } from 'next/server';
import YahooFinance from "yahoo-finance2";
import { marketRateLimiter, applyRateLimit } from '@/lib/rate-limit';
import { requireAuth } from '@/lib/auth';

// Enhanced in-memory cache with metadata
interface CacheEntry {
  data: Record<string, unknown>;
  timestamp: number;
  fetchedAt: string; // ISO timestamp for debugging
}

const cache = new Map<string, CacheEntry>();
const CACHE_TTL_SHORT = 60 * 1000;        // 1 minute for intraday
const CACHE_TTL_LONG = 5 * 60 * 1000;     // 5 minutes for historical
const STALE_CACHE_MAX_AGE = 60 * 60 * 1000; // 1 hour - max age for fallback
const REQUEST_TIMEOUT = 8000;              // 8 seconds timeout

// Retry configuration
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // 1 second

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchWithTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
  );
  return Promise.race([promise, timeout]);
}

async function fetchMarketData(symbol: string, queryOptions: Record<string, unknown>, retries = MAX_RETRIES): Promise<Record<string, unknown>> {
  try {
    const yahooFinance = new YahooFinance();
    const result = await fetchWithTimeout(
      yahooFinance.chart(symbol, queryOptions as { period1: Date | number | string; period2: Date | number | string; interval: "1m" | "2m" | "5m" | "15m" | "30m" | "60m" | "90m" | "1h" | "1d" | "5d" | "1wk" | "1mo" | "3mo" }) as Promise<Record<string, unknown>>,
      REQUEST_TIMEOUT
    );
    return result;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    if (retries > 0) {
      console.warn(`[Market API] Retry ${MAX_RETRIES - retries + 1}/${MAX_RETRIES} after error:`, message);
      await sleep(RETRY_DELAY);
      return fetchMarketData(symbol, queryOptions, retries - 1);
    }
    throw error;
  }
}

/**
 * Fetch real-time domestic gold spot price (AU9999) from Sina Finance
 */
async function fetchDomesticSpot(): Promise<number | null> {
  try {
    const response = await fetch('https://hq.sinajs.cn/list=gds_AU9999', {
      headers: { 'Referer': 'https://finance.sina.com.cn' },
      next: { revalidate: 30 } // Cache for 30s
    });
    const text = await response.text();
    const match = text.match(/\"(.*)\"/);
    if (match && match[1]) {
      const parts = match[1].split(',');
      const price = parseFloat(parts[1]);
      return isNaN(price) ? null : price;
    }
    return null;
  } catch (err) {
    console.error('[Market API] Failed to fetch domestic spot:', err);
    return null;
  }
}

/**
 * Fetch USD/CNH exchange rate from Yahoo Finance
 */
async function fetchExchangeRate(): Promise<number | null> {
  try {
    const yahooFinance = new YahooFinance();
    const result = await yahooFinance.quote('USDCNH=X');
    return result.regularMarketPrice || null;
  } catch (err) {
    console.error('[Market API] Failed to fetch FX rate:', err);
    return null;
  }
}

export async function GET(request: Request) {
  // Check authentication
  const authResponse = requireAuth(request);
  if (authResponse) {
    return authResponse;
  }

  // Apply rate limiting (10 req/min to protect primary data source)
  const rateLimitResponse = await applyRateLimit(request, marketRateLimiter);
  if (rateLimitResponse) {
    return rateLimitResponse;
  }

  const { searchParams } = new URL(request.url);

  try {
    const symbol = searchParams.get('symbol') || 'GC=F';
    const interval = searchParams.get('interval') || '1h';
    const range = searchParams.get('range') || '1mo';

    // Create a cache key based on the request parameters
    const cacheKey = `${symbol}-${interval}-${range}`;
    const cachedEntry = cache.get(cacheKey);

    // Dynamic TTL based on data type
    const ttl = ['1d', '5d'].includes(range) ? CACHE_TTL_SHORT : CACHE_TTL_LONG;

    // Check if we have fresh cache
    if (cachedEntry && (Date.now() - cachedEntry.timestamp < ttl)) {
      console.log(`[Market API] ✓ Cache hit for ${cacheKey}`);
      return NextResponse.json({
        ...cachedEntry.data,
        _cached: true,
        _fetchedAt: cachedEntry.fetchedAt
      });
    }

    // Calculate period1 based on range
    let period1Date = new Date();
    const period2Date = new Date();

    switch (range) {
      case '1d': period1Date.setDate(period1Date.getDate() - 1); break;
      case '1mo': period1Date.setMonth(period1Date.getMonth() - 1); break;
      case '2y': period1Date.setFullYear(period1Date.getFullYear() - 2); break;
      case '5y': period1Date.setFullYear(period1Date.getFullYear() - 5); break;
      case '10y': period1Date.setFullYear(period1Date.getFullYear() - 10); break;
      case 'max': period1Date = new Date('2000-01-01'); break;
      default: period1Date.setMonth(period1Date.getMonth() - 1);
    }

    const queryOptions: Record<string, unknown> = {
      period1: searchParams.get('period1') || period1Date,
      period2: searchParams.get('period2') || period2Date,
      interval: interval,
    };

    console.log(`[Market API] ⟳ Fetching fresh data for ${cacheKey}...`);

    try {
      interface ChartResult {
        meta?: {
          regularMarketPrice?: number;
          [key: string]: unknown;
        };
        [key: string]: unknown;
      }

      // Parallel fetch for chart data, domestic spot, and FX rate
      const [chartResult, domesticSpot, fxRate] = await Promise.all([
        fetchMarketData(symbol, queryOptions),
        symbol === 'GC=F' ? fetchDomesticSpot() : Promise.resolve(null),
        symbol === 'GC=F' ? fetchExchangeRate() : Promise.resolve(null)
      ]) as [ChartResult, number | null, number | null];

      // Calculate Indicators (Spread)
      let indicators = null;
      if (symbol === 'GC=F' && domesticSpot && fxRate && chartResult.meta?.regularMarketPrice) {
        const intlPriceUsd = chartResult.meta.regularMarketPrice;
        const intlPriceCnyPerGram = (intlPriceUsd * fxRate) / 31.1034768;
        const spread = domesticSpot - intlPriceCnyPerGram;
        const spreadPct = (spread / intlPriceCnyPerGram) * 100;

        indicators = {
          domestic_spot: domesticSpot,
          intl_spot_cny: intlPriceCnyPerGram,
          spread: spread,
          spread_pct: spreadPct,
          fx_rate: fxRate,
          last_updated: new Date().toISOString()
        };
      }

      const responseData = {
        ...chartResult,
        indicators,
        _cached: false,
        _fetchedAt: new Date().toISOString()
      };

      // Save to cache
      cache.set(cacheKey, {
        data: responseData,
        timestamp: Date.now(),
        fetchedAt: new Date().toISOString()
      });

      console.log(`[Market API] ✓ Fresh data cached for ${cacheKey}`);

      return NextResponse.json(responseData);

    } catch (fetchError: unknown) {
      const message = fetchError instanceof Error ? fetchError.message : 'Unknown error';
      console.error(`[Market API] ✗ Data source error:`, message);

      // Graceful degradation: serve stale cache if available
      if (cachedEntry && (Date.now() - cachedEntry.timestamp < STALE_CACHE_MAX_AGE)) {
        const ageMinutes = Math.round((Date.now() - cachedEntry.timestamp) / 60000);
        console.warn(`[Market API] ⚠ Serving stale cache (${ageMinutes} min old) due to API failure`);

        return NextResponse.json({
          ...(cachedEntry.data as object),
          _cached: true,
          _stale: true,
          _fetchedAt: cachedEntry.fetchedAt,
          _warning: `Using cached data from ${ageMinutes} minutes ago due to API unavailability`
        });
      }

      // No cache available, return error
      throw fetchError;
    }

  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Market API] ✗ Fatal error:', message);
    return NextResponse.json({
      error: 'Market data temporarily unavailable',
      message: message,
      suggestion: 'Please try again in a few moments'
    }, { status: 503 });
  }
}

// Cleanup old cache entries periodically (runs in background)
setInterval(() => {
  const now = Date.now();
  let cleaned = 0;
  for (const [key, entry] of cache.entries()) {
    if (now - entry.timestamp > STALE_CACHE_MAX_AGE) {
      cache.delete(key);
      cleaned++;
    }
  }
  if (cleaned > 0) {
    console.log(`[Market API] 🧹 Cleaned ${cleaned} stale cache entries`);
  }
}, 10 * 60 * 1000); // Run every 10 minutes