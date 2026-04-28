import { preferences } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

export class AuthTokenStore {
  private static readonly PREF_NAME = 'auth_prefs';
  private static readonly KEY_ACCESS_TOKEN = 'access_token';
  private static readonly KEY_REFRESH_TOKEN = 'refresh_token';
  private static readonly KEY_EXPIRY = 'access_token_expires_at';
  
  private static instance: AuthTokenStore;
  private pref?: preferences.Preferences;
  private context: common.Context;

  private constructor(context: common.Context) {
    this.context = context;
  }

  public static async getInstance(context: common.Context): Promise<AuthTokenStore> {
    if (!AuthTokenStore.instance) {
      AuthTokenStore.instance = new AuthTokenStore(context);
      await AuthTokenStore.instance.init();
    }
    return AuthTokenStore.instance;
  }

  private async init() {
    this.pref = await preferences.getPreferences(this.context, AuthTokenStore.PREF_NAME);
  }

  public async saveSession(accessToken: string, refreshToken: string, expiresIn?: number) {
    if (!this.pref) return;
    
    await this.pref.put(AuthTokenStore.KEY_ACCESS_TOKEN, accessToken);
    await this.pref.put(AuthTokenStore.KEY_REFRESH_TOKEN, refreshToken);
    
    if (expiresIn) {
      const expiresAt = Date.now() + (expiresIn * 1000);
      await this.pref.put(AuthTokenStore.KEY_EXPIRY, expiresAt.toString());
    }
    
    await this.pref.flush();
    hilog.info(0x0000, 'AuthTokenStore', 'Session saved');
  }

  public async getAccessToken(): Promise<string | null> {
    if (!this.pref) return null;
    return (await this.pref.get(AuthTokenStore.KEY_ACCESS_TOKEN, '')) as string || null;
  }

  public async getRefreshToken(): Promise<string | null> {
    if (!this.pref) return null;
    return (await this.pref.get(AuthTokenStore.KEY_REFRESH_TOKEN, '')) as string || null;
  }

  public async getExpiry(): Promise<number | null> {
    if (!this.pref) return null;
    const expiry = await this.pref.get(AuthTokenStore.KEY_EXPIRY, '');
    return expiry ? parseInt(expiry as string) : null;
  }

  public async clear() {
    if (!this.pref) return;
    await this.pref.delete(AuthTokenStore.KEY_ACCESS_TOKEN);
    await this.pref.delete(AuthTokenStore.KEY_REFRESH_TOKEN);
    await this.pref.delete(AuthTokenStore.KEY_EXPIRY);
    await this.pref.flush();
    hilog.info(0x0000, 'AuthTokenStore', 'Session cleared');
  }
}
