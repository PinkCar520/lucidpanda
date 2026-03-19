/**
 * Market Data Provider Configuration
 * 
 * This file centralizes market data source configuration.
 * Switch between providers by changing the PROVIDER constant.
 */

export const MARKET_DATA_CONFIG = {
    // Current provider: 'primary' | 'polygon' | 'alphavantage' | 'binance'
    PROVIDER: 'primary' as const,

    // Primary Data Source (current - free but unreliable)
    PRIMARY: {
        enabled: true,
        baseUrl: 'https://query1.finance.yahoo.com',
        rateLimit: {
            requestsPerMinute: 60,
            burstLimit: 10
        }
    },

    // Polygon.io (recommended for production)
    POLYGON: {
        enabled: false,
        apiKey: process.env.POLYGON_API_KEY || '',
        baseUrl: 'https://api.polygon.io',
        tier: 'free', // 'free' | 'starter' | 'developer' | 'advanced'
        rateLimit: {
            requestsPerMinute: 5, // Free tier
            requestsPerDay: 500
        }
    },

    // Alpha Vantage (alternative)
    ALPHAVANTAGE: {
        enabled: false,
        apiKey: process.env.ALPHAVANTAGE_API_KEY || '',
        baseUrl: 'https://www.alphavantage.co',
        rateLimit: {
            requestsPerMinute: 5, // Free tier
            requestsPerDay: 500
        }
    },

    // Binance (for crypto/tokenized gold like PAXG)
    BINANCE: {
        enabled: false,
        baseUrl: 'https://api.binance.com',
        symbols: {
            gold: 'PAXGUSDT', // PAX Gold (tokenized gold)
            btc: 'BTCUSDT'
        },
        rateLimit: {
            requestsPerMinute: 1200,
            weight: 10 // Request weight
        }
    },

    // Cache configuration
    CACHE: {
        ttlShort: 60 * 1000,          // 1 minute for real-time data
        ttlLong: 5 * 60 * 1000,       // 5 minutes for historical data
        staleMaxAge: 60 * 60 * 1000,  // 1 hour max age for fallback
        cleanupInterval: 10 * 60 * 1000 // 10 minutes
    },

    // Request configuration
    REQUEST: {
        timeout: 8000,      // 8 seconds
        maxRetries: 2,
        retryDelay: 1000    // 1 second
    }
};

/**
 * Migration Guide:
 * 
 * To switch to Polygon.io:
 * 1. Sign up at https://polygon.io (free tier: 5 req/min)
 * 2. Add POLYGON_API_KEY to .env.local
 * 3. Set PROVIDER to 'polygon'
 * 4. Implement adapter in /app/api/market/providers/polygon.ts
 * 
 * To switch to Alpha Vantage:
 * 1. Sign up at https://www.alphavantage.co
 * 2. Add ALPHAVANTAGE_API_KEY to .env.local
 * 3. Set PROVIDER to 'alphavantage'
 * 4. Implement adapter in /app/api/market/providers/alphavantage.ts
 * 
 * To use Binance for tokenized gold:
 * 1. No API key needed for public endpoints
 * 2. Set PROVIDER to 'binance'
 * 3. Implement adapter in /app/api/market/providers/binance.ts
 * 4. Note: This tracks PAXG (tokenized gold), not physical gold futures
 */

export type MarketDataProvider = typeof MARKET_DATA_CONFIG.PROVIDER;
