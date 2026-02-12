import { Session } from 'next-auth';
import { authenticatedFetch } from '@/lib/api-client';

export interface WatchlistItem {
  code: string;
  name: string;
  is_qdii?: boolean;
  estimated_growth?: number;
  previous_growth?: number;
  source?: string;
  stats?: any;
}

export interface FundValuation {
  fund_code: string;
  fund_name: string;
  estimated_growth: number;
  total_weight: number;
  is_qdii?: boolean;
  status?: string;
  message?: string;
  components: any[];
  sector_attribution?: any;
  timestamp: string;
  source?: string;
  stats?: any;
}

/**
 * Service for Fund related API calls
 */
export const fundService = {
  /**
   * Fetch user's watchlist
   */
  async getWatchlist(session: Session | null): Promise<WatchlistItem[]> {
    const res = await authenticatedFetch('/api/watchlist', session);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Fetch batch valuation for multiple funds
   */
  async getBatchValuation(codes: string[], session: Session | null): Promise<any[]> {
    if (!codes.length) return [];
    const res = await authenticatedFetch(`/api/funds/batch-valuation?codes=${codes.join(',')}&mode=summary`, session);
    if (!res.ok) throw new Error('Failed to fetch batch valuation');
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Fetch detailed valuation for a single fund
   */
  async getFundValuation(code: string, session: Session | null): Promise<FundValuation> {
    if (!code) throw new Error('Fund code is required');
    const res = await authenticatedFetch(`/api/funds/${code}/valuation`, session);
    if (!res.ok) throw new Error(`Failed to fetch valuation for ${code}`);
    const json = await res.json();
    return json; // Assuming the JSON structure matches FundValuation
  },

  /**
   * Fetch history for a single fund
   */
  async getFundHistory(code: string, session: Session | null): Promise<any[]> {
    if (!code) return [];
    const res = await authenticatedFetch(`/api/funds/${code}/history`, session);
    if (!res.ok) throw new Error(`Failed to fetch history for ${code}`);
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Add a fund to watchlist
   */
  async addToWatchlist(code: string, name: string, session: Session | null): Promise<any> {
    const res = await authenticatedFetch('/api/watchlist', session, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name }),
    });
    if (!res.ok) throw new Error('Failed to add to watchlist');
    return await res.json();
  },

  /**
   * Remove a fund from watchlist
   */
  async removeFromWatchlist(code: string, session: Session | null): Promise<any> {
    const res = await authenticatedFetch(`/api/watchlist/${code}`, session, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to remove from watchlist');
    return await res.json();
  }
};
