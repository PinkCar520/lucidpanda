export interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  timestamp?: string;
}

export interface MarketSnapshot {
  gold: MarketQuote;
  gold_cny?: MarketQuote;
  dxy: MarketQuote;
  oil: MarketQuote;
  us10y: MarketQuote;
  last_updated: string;
}

export interface MarketPulseAlert {
  id: number;
  timestamp: string;
  urgency_score: number;
  summary: string;
  sentiment: string;
}

export interface MarketPulseResponse {
  market_snapshot: MarketSnapshot;
  top_alerts: MarketPulseAlert[];
  overall_sentiment: string;
  overall_sentiment_zh: string;
  sentiment_score: number;
  alert_count_24h: number;
  generated_at: string;
}
