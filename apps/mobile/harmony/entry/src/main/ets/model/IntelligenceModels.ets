export interface IntelligenceItem {
  id: number;
  timestamp: string;
  author: string;
  summary: string;
  content: string;
  image_url?: string;
  sentiment_label: string;
  urgency_score: number;
  gold_price_snapshot?: number;
}

export interface IntelligenceEvent {
  type: string;
  data?: IntelligenceItem[];
}

export interface AISummaryResponse {
  ai_summary: string;
}
