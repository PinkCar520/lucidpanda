export interface ValuationHistory {
  trade_date: string;
  frozen_est_growth?: number;
  official_growth?: number;
  deviation?: number;
  tracking_status?: string;
}

export interface FundStats {
  return_1w?: number;
  return_1m?: number;
  return_3m?: number;
  return_1y?: number;
  sharpe_ratio?: number;
  sharpe_grade?: string;
  max_drawdown?: number;
  drawdown_grade?: string;
  volatility?: number;
  sparkline_data?: number[];
}

export interface FundConfidence {
  level: string; // "high", "medium", "low"
  score: number;
  is_suspected_rebalance?: boolean;
  reasons?: string[];
}

export interface SubSectorStat {
  id?: string;
  impact: number;
  weight: number;
}

export interface SectorStat {
  id?: string;
  impact: number;
  weight: number;
  sub?: Record<string, SubSectorStat>;
}

export interface FundDetailResponse extends FundValuation {
  stats?: FundStats;
  confidence?: FundConfidence;
  risk_level?: string;
  sector_attribution?: Record<string, SectorStat>;
}

import { FundValuation } from './WatchlistModels';
