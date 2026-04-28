import { AuthTokenStore } from '../common/AuthTokenStore';
import { common } from '@kit.AbilityKit';
import { MarketPulseViewModel } from './MarketPulseViewModel';
import { IntelligenceViewModel } from './IntelligenceViewModel';

export enum AppState {
  LOADING,
  UNAUTHENTICATED,
  AUTHENTICATED
}

@Observed
export class AppRootViewModel {
  public currentState: AppState = AppState.LOADING;
  public marketPulseViewModel: MarketPulseViewModel;
  public intelligenceViewModel: IntelligenceViewModel;
  private context: common.Context;

  constructor(context: common.Context) {
    this.context = context;
    this.marketPulseViewModel = new MarketPulseViewModel(context);
    this.intelligenceViewModel = new IntelligenceViewModel(context);
  }

  public async checkAuthentication() {
    const tokenStore = await AuthTokenStore.getInstance(this.context);
    const token = await tokenStore.getAccessToken();
    
    if (token) {
      this.currentState = AppState.AUTHENTICATED;
      // Start services if authenticated
      this.marketPulseViewModel.start();
      this.intelligenceViewModel.startStream();
    } else {
      this.currentState = AppState.UNAUTHENTICATED;
    }
  }

  public updateState(newState: AppState) {
    this.currentState = newState;
    if (newState === AppState.AUTHENTICATED) {
      this.marketPulseViewModel.start();
      this.intelligenceViewModel.startStream();
    } else {
      this.marketPulseViewModel.stop();
      this.intelligenceViewModel.stopStream();
    }
  }
}
