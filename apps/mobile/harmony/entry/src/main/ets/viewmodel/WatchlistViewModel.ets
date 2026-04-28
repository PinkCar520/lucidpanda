import { APIClient } from '../network/APIClient';
import { SSEResolver } from '../network/SSEResolver';
import { AuthTokenStore } from '../common/AuthTokenStore';
import { DatabaseManager } from '../common/DatabaseManager';
import { FundValuation, WatchlistGroup, WatchlistItem } from '../model/WatchlistModels';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

@Observed
export class WatchlistViewModel {
  public watchlist: FundValuation[] = [];
  public groups: WatchlistGroup[] = [];
  public isLoading: boolean = false;
  
  private apiClient = APIClient.getInstance();
  private sseResolver = SSEResolver.getInstance();
  private databaseManager?: DatabaseManager;
  private streamID?: string;
  private context: common.Context;

  constructor(context: common.Context) {
    this.context = context;
    this.initDatabase();
  }

  private async initDatabase() {
    this.databaseManager = await DatabaseManager.getInstance(this.context);
    await this.loadFromCache();
  }

  private async loadFromCache() {
    if (!this.databaseManager) return;
    
    const cachedGroups = await this.databaseManager.getAllGroups();
    const cachedItems = await this.databaseManager.getAllWatchlistItems();
    
    this.groups = cachedGroups;
    
    const cachedValuations: FundValuation[] = cachedItems.compactMap(item => {
      if (item.cached_valuation) {
        try {
          return JSON.parse(item.cached_valuation) as FundValuation;
        } catch (e) {
          return null;
        }
      }
      return null;
    });

    if (cachedValuations.length > 0) {
      this.watchlist = cachedValuations;
      hilog.info(0x0000, 'WatchlistVM', 'Loaded from cache');
    }
  }

  public async fetchWatchlist() {
    this.isLoading = true;
    try {
      // 1. Fetch remote watchlist
      const response = await this.apiClient.fetch<any>('/api/v2/watchlist');
      const remoteItems = response.data as WatchlistItem[];
      const remoteGroups = response.groups as WatchlistGroup[];

      this.groups = remoteGroups;
      
      // 2. Fetch valuations for these items
      const codes = remoteItems.map(item => item.fund_code);
      if (codes.length > 0) {
        await this.fetchValuations(codes);
      }

      // 3. Update cache
      if (this.databaseManager) {
        await this.databaseManager.saveGroups(remoteGroups);
        const itemsToCache = remoteItems.map(item => {
          const val = this.watchlist.find(v => v.fund_code === item.fund_code);
          return {
            ...item,
            cached_valuation: val ? JSON.stringify(val) : ''
          } as WatchlistItem;
        });
        await this.databaseManager.saveWatchlistItems(itemsToCache);
      }
    } catch (error) {
      hilog.error(0x0000, 'WatchlistVM', 'Remote fetch failed');
    }
    this.isLoading = false;
  }

  private async fetchValuations(codes: string[]) {
    try {
      const response = await this.apiClient.fetch<any>(`/api/v1/web/funds/batch-valuation?codes=${codes.join(',')}&mode=summary`);
      this.watchlist = response.data as FundValuation[];
      this.startLiveUpdates();
    } catch (error) {
      hilog.error(0x0000, 'WatchlistVM', 'Valuation fetch failed');
    }
  }

  public async startLiveUpdates() {
    if (this.streamID || this.watchlist.length === 0) return;
    
    const tokenStore = await AuthTokenStore.getInstance(this.context);
    const token = await tokenStore.getAccessToken();
    
    const codes = this.watchlist.map(v => v.fund_code).join(',');
    const url = `http://43.139.108.187:8001/api/v1/web/funds/stream?codes=${codes}`;
    
    this.streamID = this.sseResolver.subscribe(url, token, (payload) => {
      try {
        const update = JSON.parse(payload) as FundValuation;
        this.applyLiveUpdate(update);
      } catch (e) {
        // Handle batch updates if payload is array
      }
    });
  }

  private applyLiveUpdate(update: FundValuation) {
    const index = this.watchlist.findIndex(v => v.fund_code === update.fund_code);
    if (index !== -1) {
      // Use array spread to trigger UI update in HarmonyOS NEXT
      const newList = [...this.watchlist];
      newList[index] = update;
      this.watchlist = newList;
    }
  }

  public stopLiveUpdates() {
    if (this.streamID) {
      this.sseResolver.stop(this.streamID);
      this.streamID = undefined;
    }
  }
}

// Helper extension for HarmonyOS NEXT style
extension Array {
  compactMap<T>(callback: (item: any) => T | null): T[] {
    const result: T[] = [];
    for (const item of this) {
      const mapped = callback(item);
      if (mapped !== null) {
        result.push(mapped);
      }
    }
    return result;
  }
}
