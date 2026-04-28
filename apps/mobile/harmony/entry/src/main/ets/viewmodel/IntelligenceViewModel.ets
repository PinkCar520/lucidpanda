import { APIClient } from '../network/APIClient';
import { SSEResolver } from '../network/SSEResolver';
import { AuthTokenStore } from '../common/AuthTokenStore';
import { IntelligenceItem, IntelligenceEvent } from '../model/IntelligenceModels';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

@Observed
export class IntelligenceViewModel {
  public items: IntelligenceItem[] = [];
  public isStreaming: boolean = false;
  public connectionStatus: string = 'live'; // 'live', 'connecting', 'disconnected'
  
  private apiClient = APIClient.getInstance();
  private sseResolver = SSEResolver.getInstance();
  private streamID?: string;
  private context: common.Context;

  constructor(context: common.Context) {
    this.context = context;
  }

  public async startStream() {
    if (this.isStreaming) return;
    this.isStreaming = true;

    // 1. Fetch initial history
    await this.fetchInitialHistory();

    // 2. Start SSE
    const tokenStore = await AuthTokenStore.getInstance(this.context);
    const token = await tokenStore.getAccessToken();
    
    const url = 'http://43.139.108.187:8001/api/v1/intelligence/stream';
    this.streamID = this.sseResolver.subscribe(url, token, (payload) => {
      try {
        const event = JSON.parse(payload) as IntelligenceEvent;
        if (event.data) {
          this.processNewItems(event.data);
        }
      } catch (e) {
        hilog.error(0x0000, 'IntelligenceVM', 'Failed to parse SSE payload');
      }
    });
  }

  public stopStream() {
    if (this.streamID) {
      this.sseResolver.stop(this.streamID);
      this.streamID = undefined;
    }
    this.isStreaming = false;
  }

  private async fetchInitialHistory() {
    try {
      const response = await this.apiClient.fetch<IntelligenceItem[]>('/api/v1/mobile/intelligence?limit=50');
      this.processNewItems(response);
    } catch (error) {
      hilog.error(0x0000, 'IntelligenceVM', 'Failed to fetch history');
    }
  }

  private processNewItems(newItems: IntelligenceItem[]) {
    // Add only items that don't exist yet
    const existingIds = new Set(this.items.map(item => item.id));
    const itemsToAdd = newItems.filter(item => !existingIds.has(item.id));
    
    if (itemsToAdd.length > 0) {
      this.items = [...itemsToAdd, ...this.items].sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      
      if (this.items.length > 100) {
        this.items = this.items.slice(0, 100);
      }
    }
  }

  public async getAISummary(itemId: number): Promise<string> {
    try {
      const response = await this.apiClient.fetch<any>(`/api/v1/mobile/intelligence/${itemId}/ai_summary`);
      return response.ai_summary;
    } catch (error) {
      return '生成摘要失败，请稍后重试';
    }
  }
}
