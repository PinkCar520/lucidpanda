import { APIClient } from '../network/APIClient';
import { SSEResolver } from '../network/SSEResolver';
import { AuthTokenStore } from '../common/AuthTokenStore';
import { FundDetailResponse, ValuationHistory } from '../model/FundDetailModels';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

@Observed
export class FundDetailViewModel {
  public valuation: FundDetailResponse;
  public liveGrowth: number;
  public isLive: boolean = false;
  public history: ValuationHistory[] = [];
  public isHistoryLoading: boolean = false;
  
  // 2σ Alarm Settings
  public isAlarmEnabled: boolean = true;
  public threshold2Sigma: number = 1.5;
  
  private apiClient = APIClient.getInstance();
  private sseResolver = SSEResolver.getInstance();
  private streamID?: string;
  private context: common.Context;

  constructor(initialValuation: FundDetailResponse, context: common.Context) {
    this.valuation = initialValuation;
    this.liveGrowth = initialValuation.estimated_growth;
    this.context = context;
  }

  public async startUpdates() {
    if (this.isLive) return;
    this.isLive = true;

    // 1. Fetch History & Calculate Threshold
    await this.fetchHistory();

    // 2. Start SSE Stream for this specific fund
    const tokenStore = await AuthTokenStore.getInstance(this.context);
    const token = await tokenStore.getAccessToken();
    
    const url = `http://43.139.108.187:8001/api/v1/web/funds/stream?codes=${this.valuation.fund_code}`;
    this.streamID = this.sseResolver.subscribe(url, token, (payload) => {
      try {
        const update = JSON.parse(payload) as FundDetailResponse;
        animateTo({ duration: 300, curve: Curve.EaseOut }, () => {
          this.valuation = update;
          this.liveGrowth = update.estimated_growth;
        });
      } catch (e) {
        hilog.error(0x0000, 'FundDetailVM', 'Failed to parse SSE payload');
      }
    });
  }

  public stopUpdates() {
    if (this.streamID) {
      this.sseResolver.stop(this.streamID);
      this.streamID = undefined;
    }
    this.isLive = false;
  }

  private async fetchHistory() {
    this.isHistoryLoading = true;
    try {
      const response = await this.apiClient.fetch<any>(`/api/v1/web/funds/${this.valuation.fund_code}/history?limit=20`);
      this.history = response.data as ValuationHistory[];
      
      this.calculateThreshold2Sigma();
    } catch (error) {
      hilog.error(0x0000, 'FundDetailVM', 'Failed to fetch history');
    }
    this.isHistoryLoading = false;
  }

  private calculateThreshold2Sigma() {
    const returns = this.history
      .map(h => h.official_growth)
      .filter((g): g is number => g !== undefined);
      
    if (returns.length < 5) {
      this.threshold2Sigma = 1.5;
      return;
    }

    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const sumOfSquaredDiff = returns.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0);
    const standardDeviation = Math.sqrt(sumOfSquaredDiff / returns.length);
    
    this.threshold2Sigma = standardDeviation * 2.0;
  }
}
