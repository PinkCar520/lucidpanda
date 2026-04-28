export interface SessionWinRate {
  count: number;
  win_rate: number;
}

export interface SessionPerformance {
  session: string;
  count: number;
  win_rate: number;
  avg_drop: number;
}

export interface DistributionBin {
  bin: number;
  count: number;
}

export interface BacktestItem {
  id: number;
  title: string;
  timestamp: string;
  score: number;
  entry: number;
  exit: number;
  is_win: boolean;
  change_pct: number;
}

export interface HygieneStats {
  avg_clustering: number;
  avg_exhaustion: number;
  avg_dxy?: number;
  avg_us10y?: number;
  avg_gvz?: number;
}

export interface BacktestStats {
  count: number;
  win_rate: number;
  adj_win_rate?: number;
  avg_drop: number;
  hygiene: HygieneStats;
  correlation: Record<string, SessionWinRate>;
  positioning?: Record<string, SessionWinRate>;
  volatility?: Record<string, SessionWinRate>;
  distribution?: DistributionBin[];
  session_stats: SessionPerformance[];
  items?: BacktestItem[];
}
