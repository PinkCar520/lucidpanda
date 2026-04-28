import { relationalStore } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { WatchlistItem, WatchlistGroup } from '../model/WatchlistModels';

export class DatabaseManager {
  private static instance: DatabaseManager;
  private rdbStore?: relationalStore.RdbStore;
  private context: common.Context;
  private readonly DB_NAME = 'LucidPanda.db';
  private readonly TAG = 'DatabaseManager';

  private constructor(context: common.Context) {
    this.context = context;
  }

  public static async getInstance(context: common.Context): Promise<DatabaseManager> {
    if (!DatabaseManager.instance) {
      DatabaseManager.instance = new DatabaseManager(context);
      await DatabaseManager.instance.init();
    }
    return DatabaseManager.instance;
  }

  private async init() {
    const config: relationalStore.StoreConfig = {
      name: this.DB_NAME,
      securityLevel: relationalStore.SecurityLevel.S1
    };

    const SQL_CREATE_WATCHLIST = `
      CREATE TABLE IF NOT EXISTS watchlist (
        fund_code TEXT PRIMARY KEY,
        fund_name TEXT,
        group_id TEXT,
        sort_index INTEGER,
        last_sync_time INTEGER,
        is_deleted INTEGER,
        cached_valuation TEXT
      )`;

    const SQL_CREATE_GROUPS = `
      CREATE TABLE IF NOT EXISTS watchlist_groups (
        id TEXT PRIMARY KEY,
        name TEXT,
        icon TEXT,
        color TEXT,
        sort_index INTEGER,
        last_sync_time INTEGER
      )`;

    try {
      this.rdbStore = await relationalStore.getRdbStore(this.context, config);
      await this.rdbStore.executeSql(SQL_CREATE_WATCHLIST);
      await this.rdbStore.executeSql(SQL_CREATE_GROUPS);
      hilog.info(0x0000, this.TAG, 'RDB initialized successfully');
    } catch (e) {
      hilog.error(0x0000, this.TAG, 'RDB init failed: ' + JSON.stringify(e));
    }
  }

  // --- Watchlist Operations ---

  public async saveWatchlistItems(items: WatchlistItem[]) {
    if (!this.rdbStore) return;
    
    for (const item of items) {
      const value: relationalStore.ValuesBucket = {
        'fund_code': item.fund_code,
        'fund_name': item.fund_name,
        'group_id': item.group_id || '',
        'sort_index': item.sort_index,
        'last_sync_time': item.last_sync_time,
        'is_deleted': item.is_deleted ? 1 : 0,
        'cached_valuation': item.cached_valuation || ''
      };
      await this.rdbStore.insert('watchlist', value, relationalStore.ConflictResolution.REPLACE);
    }
  }

  public async getAllWatchlistItems(): Promise<WatchlistItem[]> {
    if (!this.rdbStore) return [];
    
    const predicates = new relationalStore.RdbPredicates('watchlist');
    predicates.equalTo('is_deleted', 0).orderByAsc('sort_index');
    
    const resultSet = await this.rdbStore.query(predicates);
    const items: WatchlistItem[] = [];
    
    while (resultSet.goToNextRow()) {
      items.push({
        fund_code: resultSet.getString(resultSet.getColumnIndex('fund_code')),
        fund_name: resultSet.getString(resultSet.getColumnIndex('fund_name')),
        group_id: resultSet.getString(resultSet.getColumnIndex('group_id')),
        sort_index: resultSet.getLong(resultSet.getColumnIndex('sort_index')),
        last_sync_time: resultSet.getLong(resultSet.getColumnIndex('last_sync_time')),
        is_deleted: resultSet.getLong(resultSet.getColumnIndex('is_deleted')) === 1,
        cached_valuation: resultSet.getString(resultSet.getColumnIndex('cached_valuation'))
      });
    }
    resultSet.close();
    return items;
  }

  // --- Group Operations ---

  public async saveGroups(groups: WatchlistGroup[]) {
    if (!this.rdbStore) return;
    
    for (const group of groups) {
      const value: relationalStore.ValuesBucket = {
        'id': group.id,
        'name': group.name,
        'icon': group.icon,
        'color': group.color,
        'sort_index': group.sort_index,
        'last_sync_time': group.last_sync_time
      };
      await this.rdbStore.insert('watchlist_groups', value, relationalStore.ConflictResolution.REPLACE);
    }
  }

  public async getAllGroups(): Promise<WatchlistGroup[]> {
    if (!this.rdbStore) return [];
    
    const predicates = new relationalStore.RdbPredicates('watchlist_groups');
    predicates.orderByAsc('sort_index');
    
    const resultSet = await this.rdbStore.query(predicates);
    const groups: WatchlistGroup[] = [];
    
    while (resultSet.goToNextRow()) {
      groups.push({
        id: resultSet.getString(resultSet.getColumnIndex('id')),
        name: resultSet.getString(resultSet.getColumnIndex('name')),
        icon: resultSet.getString(resultSet.getColumnIndex('icon')),
        color: resultSet.getString(resultSet.getColumnIndex('color')),
        sort_index: resultSet.getLong(resultSet.getColumnIndex('sort_index')),
        last_sync_time: resultSet.getLong(resultSet.getColumnIndex('last_sync_time'))
      });
    }
    resultSet.close();
    return groups;
  }
}
