export interface WatchlistGroup {
  id: string;
  name: string;
  icon: string;
  color: string;
  sort_index: number;
  last_sync_time: number;
}

export interface WatchlistItem {
  fund_code: string;
  fund_name: string;
  group_id?: string;
  sort_index: number;
  last_sync_time: number;
  is_deleted: boolean;
  cached_valuation?: string; // JSON string of FundValuation
}

export interface FundComponent {
  code: string;
  name: string;
  weight: number;
  change_pct: number;
  impact: number;
}

export interface FundValuation {
  fund_code: string;
  fund_name: string;
  estimated_growth: number;
  total_weight: number;
  components: FundComponent[];
  timestamp: string;
  market_status?: string;
}
