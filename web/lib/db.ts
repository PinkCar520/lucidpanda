import { Pool } from 'pg';

export const db = new Pool({
  user: process.env.POSTGRES_USER || 'alphasignal',
  host: process.env.POSTGRES_HOST || 'db',
  database: process.env.POSTGRES_DB || 'alphasignal_core',
  password: process.env.POSTGRES_PASSWORD || 'secure_password',
  port: 5432,
});

export interface Intelligence {
  id: number;
  timestamp: string;
  source_id: string;
  author: string;
  content: string | any;
  summary: string | any;
  sentiment: string | any;
  urgency_score: number;
  market_implication: string | any;
  actionable_advice: string | any;
  url: string;
  gold_price_snapshot: number | null;
  price_15m: number | null;
  price_1h: number | null;
  price_4h: number | null;
  price_12h: number | null;
  price_24h: number | null;
  clustering_score?: number;
  exhaustion_score?: number;
  gvz_snapshot?: number;
  dxy_snapshot?: number;
  us10y_snapshot?: number;
  sentiment_score?: number;
  fed_regime?: number;
  macro_adjustment?: number;
}
