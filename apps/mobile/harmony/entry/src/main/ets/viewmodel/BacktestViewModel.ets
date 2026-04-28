import { APIClient } from '../network/APIClient';
import { BacktestStats } from '../model/BacktestModels';
import { hilog } from '@kit.PerformanceAnalysisKit';

@Observed
export class BacktestViewModel {
  public stats?: BacktestStats;
  public isLoading: boolean = false;
  public errorMessage: string = '';
  
  // Configuration
  public selectedWindow: string = '1h';
  public minScore: number = 8;
  public sentiment: string = 'bearish';
  
  private apiClient = APIClient.getInstance();

  public async fetchStats() {
    this.isLoading = true;
    this.errorMessage = '';
    
    try {
      const path = `/api/v1/web/stats?window=${this.selectedWindow}&min_score=${this.minScore}&sentiment=${this.sentiment}`;
      const response = await this.apiClient.fetch<BacktestStats>(path);
      
      animateTo({ duration: 300, curve: Curve.EaseOut }, () => {
        this.stats = response;
      });
    } catch (error) {
      hilog.error(0x0000, 'BacktestVM', 'Fetch failed');
      this.errorMessage = '获取回测数据失败，请检查网络';
    } finally {
      this.isLoading = false;
    }
  }

  public setConfig(window: string, minScore: number, sentiment: string) {
    this.selectedWindow = window;
    this.minScore = minScore;
    this.sentiment = sentiment;
    this.fetchStats();
  }
}
