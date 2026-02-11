import { Session } from 'next-auth';
import { authenticatedFetch } from '@/lib/api-client';

/**
 * Service for Market Data API calls
 */
export const marketService = {
  /**
   * Fetch historical market data for a symbol
   */
  async getMarketData(symbol: string, range: string, interval: string, session: Session | null) {
    const res = await authenticatedFetch(
      `/api/market?symbol=${symbol}&range=${range}&interval=${interval}`, 
      session
    );
    if (!res.ok) {
      if (res.status === 429) {
        throw new Error('RATE_LIMIT_EXCEEDED');
      }
      throw new Error('Failed to fetch market data');
    }
    return res.json();
  }
};
