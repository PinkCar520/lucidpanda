import { AppRootViewModel, AppState } from '../viewmodel/AppRootViewModel'
import { Login } from './Login'
import { MainTab } from './MainTab'
import { TaupeTheme } from '../common/Theme'

@Entry
@Component
struct Index {
  @State rootViewModel: AppRootViewModel = new AppRootViewModel(getContext(this))

  async onPageShow() {
    await this.rootViewModel.checkAuthentication()
  }

  build() {
    Stack() {
      if (this.rootViewModel.currentState === AppState.LOADING) {
        // Splash / Loading
        Column() {
          LoadingProgress().width(64).height(64).color(TaupeTheme.BRAND)
        }
        .width('100%')
        .height('100%')
        .justifyContent(FlexAlign.Center)
        .backgroundColor(TaupeTheme.BACKGROUND)
      } else if (this.rootViewModel.currentState === AppState.UNAUTHENTICATED) {
        Login()
      } else {
        MainTab({ rootViewModel: this.rootViewModel })
      }
    }
    .width('100%')
    .height('100%')
  }
}
