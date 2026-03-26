import { Session } from 'next-auth';
import { authenticatedFetch } from '@/lib/api-client';

export interface FundConfidence {
  level: 'high' | 'medium' | 'low';
  score: number;
  is_suspected_rebalance?: boolean;
  reasons: string[];
}

export interface WatchlistItem {
  code: string;
  name: string;
  is_qdii?: boolean;
  estimated_growth?: number;
  previous_growth?: number;
  source?: string;
  confidence?: FundConfidence;
  risk_level?: string;
  stats?: FundStats;
}

export interface SubSectorStat {
  impact: number;
  weight: number;
}

export interface SectorStat {
  impact: number;
  weight: number;
  sub: Record<string, SubSectorStat>;
}

export interface ComponentStock {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  impact: number;
  weight: number;
}

export interface FundStats {
  return_1w: number;
  return_1m: number;
  return_3m: number;
  return_1y: number;
  sharpe_ratio: number;
  sharpe_grade: string;
  max_drawdown: number;
  drawdown_grade: string;
  volatility: number;
  sparkline_data: number[];
}

export interface ValuationHistory {
  trade_date: string;
  frozen_est_growth: number;
  official_growth: number;
  deviation: number;
  tracking_status: string;
  sector_attribution?: Record<string, SectorStat>;
  timestamp: string;
  source?: string;
}

export interface FundValuation {
  fund_code: string;
  fund_name: string;
  estimated_growth: number;
  total_weight: number;
  is_qdii?: boolean;
  confidence?: FundConfidence;
  risk_level?: string;
  status?: string;
  message?: string;
  components: ComponentStock[];
  sector_attribution?: Record<string, SectorStat>;
  timestamp: string;
  source?: string;
  stats?: FundStats;
}

export interface Anomaly {
  fund_code: string;
  trade_date: string;
  deviation: number;
  frozen_est_growth: number;
  official_growth: number;
  tracking_status: string;
  frozen_sector_attribution?: Record<string, number>;
}

export interface DailyStat {
  trade_date: string;
  total_count: number;
  reconciled_count: number;
  avg_mae: number;
}

export interface HeatmapItem {
  trade_date: string;
  category: string;
  mae: number;
}

export interface MonitorStats {
  health: {
    score: number;
    components: {
      coverage: number;
      accuracy: number;
      anomaly: number;
    };
  };
  daily: DailyStat[];
  heatmap: HeatmapItem[];
  anomalies: Anomaly[];
  updated_at: string;
}

const V1_BASE = '/api/v1/web';

/**
 * Service for Fund related API calls
 */
export const fundService = {
  /**
   * Fetch user's watchlist
   */
  async getWatchlist(session: Session | null): Promise<WatchlistItem[]> {
    const res = await authenticatedFetch(`${V1_BASE}/watchlist`, session);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Fetch batch valuation for multiple funds
   */
  async getBatchValuation(codes: string[], session: Session | null): Promise<FundValuation[]> {
    if (!codes.length) return [];
    const res = await authenticatedFetch(`${V1_BASE}/funds/batch-valuation?codes=${codes.join(',')}&mode=summary`, session);
    if (!res.ok) throw new Error('Failed to fetch batch valuation');
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Fetch detailed valuation for a single fund
   */
  async getFundValuation(code: string, session: Session | null): Promise<FundValuation> {
    if (!code) throw new Error('Fund code is required');
    const res = await authenticatedFetch(`${V1_BASE}/funds/${code}/valuation`, session);
    if (!res.ok) throw new Error(`Failed to fetch valuation for ${code}`);
    const json = await res.json();
    return json; // Assuming the JSON structure matches FundValuation
  },

  /**
   * Fetch history for a single fund
   */
  async getFundHistory(code: string, session: Session | null): Promise<ValuationHistory[]> {
    if (!code) return [];
    const res = await authenticatedFetch(`${V1_BASE}/funds/${code}/history`, session);
    if (!res.ok) throw new Error(`Failed to fetch history for ${code}`);
    const json = await res.json();
    return json.data || [];
  },

  /**
   * Add a fund to watchlist
   */
  async addToWatchlist(code: string, name: string, session: Session | null): Promise<{success: boolean}> {
    const res = await authenticatedFetch(`${V1_BASE}/watchlist`, session, {
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
  async removeFromWatchlist(code: string, session: Session | null): Promise<{success: boolean}> {
    const res = await authenticatedFetch(`${V1_BASE}/watchlist/${code}`, session, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to remove from watchlist');
    return await res.json();
  },

  /**
   * Fetch admin monitor stats
   */
  async getMonitorStats(session: Session | null): Promise<MonitorStats> {
    const res = await authenticatedFetch(`${V1_BASE}/admin/monitor`, session);
    if (!res.ok) throw new Error('Failed to fetch monitor stats');
    return await res.json();
  },

  /**
   * Trigger manual reconciliation for a date/fund
   */
  async triggerReconciliation(payload: { trade_date: string, fund_code?: string }, session: Session | null): Promise<{success: boolean, matched_count?: number, error?: string}> {
    const res = await authenticatedFetch(`${V1_BASE}/admin/reconcile/trigger`, session, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to trigger reconciliation');
    const json = await res.json();
    return json;
  }
};
