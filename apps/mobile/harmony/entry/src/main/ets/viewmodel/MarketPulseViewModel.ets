import { APIClient } from '../network/APIClient';
import { SSEResolver } from '../network/SSEResolver';
import { AuthTokenStore } from '../common/AuthTokenStore';
import { MarketPulseResponse } from '../model/MarketDataModels';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

@Observed
export class MarketPulseViewModel {
  public pulseData?: MarketPulseResponse;
  public isLoading: boolean = false;
  
  private apiClient = APIClient.getInstance();
  private sseResolver = SSEResolver.getInstance();
  private streamID?: string;
  private context: common.Context;

  constructor(context: common.Context) {
    this.context = context;
  }

  public async start() {
    if (this.isLoading) return;
    
    // 1. Initial Fetch
    await this.fetchPulse();
    
    // 2. Start SSE
    const tokenStore = await AuthTokenStore.getInstance(this.context);
    const token = await tokenStore.getAccessToken();
    
    const url = 'http://43.139.108.187:8001/api/v1/mobile/market/pulse/stream';
    this.streamID = this.sseResolver.subscribe(url, token, (payload) => {
      try {
        const newData = JSON.parse(payload) as MarketPulseResponse;
        this.pulseData = newData;
        hilog.debug(0x0000, 'MarketPulseVM', 'SSE Update received');
      } catch (e) {
        hilog.error(0x0000, 'MarketPulseVM', 'Failed to parse SSE payload');
      }
    });
  }

  public stop() {
    if (this.streamID) {
      this.sseResolver.stop(this.streamID);
      this.streamID = undefined;
    }
  }

  public async fetchPulse() {
    this.isLoading = true;
    try {
      const data = await this.apiClient.fetch<MarketPulseResponse>('/api/v1/mobile/market/pulse');
      this.pulseData = data;
    } catch (error) {
      hilog.error(0x0000, 'MarketPulseVM', 'Fetch failed');
    }
    this.isLoading = false;
  }
}
