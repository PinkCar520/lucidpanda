import { Pool } from 'pg';

export const db = new Pool({
  user: process.env.POSTGRES_USER || 'lucidpanda',
  host: process.env.POSTGRES_HOST || 'db',
  database: process.env.POSTGRES_DB || 'lucidpanda_core',
  password: process.env.POSTGRES_PASSWORD || 'secure_password',
  port: 5432,
});

export type LocalizedText = string | Record<string, string>;

export interface Intelligence {
  id: number;
  timestamp: string;
  source_id: string;
  author: string;
  content: LocalizedText;
  summary: LocalizedText;
  sentiment: LocalizedText;
  urgency_score: number;
  market_implication: LocalizedText;
  actionable_advice: LocalizedText;
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
  entities?: Array<{ name: string; type: string; impact: string }>;
  relation_triples?: Array<{
    subject: string;
    predicate: string;
    object: string;
    direction: string;
    strength: number;
  }>;
  event_cluster_id?: string | null;
  corroboration_count?: number;
  confidence_score?: number;
  confidence_level?: 'LOW' | 'MEDIUM' | 'HIGH';
}
