import { TaupeTheme } from '../common/Theme'
import { LiquidGlassCard } from '../components/LiquidGlassCard'
import { LoginViewModel } from '../viewmodel/LoginViewModel'
import { router } from '@kit.ArkUI'

@Entry
@Component
struct Login {
  @State email: string = ''
  @State password: string = ''
  @State isLoading: boolean = false
  @State errorMessage: string = ''
  
  private viewModel: LoginViewModel = new LoginViewModel(getContext(this))

  async handleLogin() {
    if (!this.email || !this.password) {
      this.errorMessage = '请输入邮箱和密码'
      return
    }
    
    this.isLoading = true
    this.errorMessage = ''
    
    const success = await this.viewModel.login(this.email, this.password)
    this.isLoading = false
    
    if (success) {
      router.replaceUrl({ url: 'pages/Index' })
    } else {
      this.errorMessage = '登录失败，请检查凭据'
    }
  }

  build() {
    Stack() {
      // 1. Background
      Rect().width('100%').height('100%').fill(TaupeTheme.BACKGROUND)
      
      ScrollView() {
        Column() {
          Blank().height(80)
          
          // 2. Logo Area
          Column({ space: 12 }) {
            SymbolGlyph($r('sys.symbol.chart_line_uptrend_xyaxis_circle_fill'))
              .fontSize(64)
              .fontColor([TaupeTheme.BRAND])
            
            Text('LucidPanda')
              .fontSize(28)
              .fontWeight(FontWeight.Heavy)
              .fontColor(TaupeTheme.TEXT_PRIMARY)
          }
          .margin({ bottom: 40 })
          
          // 3. Login Card
          LiquidGlassCard() {
            Column({ space: 20 }) {
              // Email Field
              TextInput({ placeholder: '电子邮箱', text: this.email })
                .type(InputType.Email)
                .width('100%')
                .height(52)
                .backgroundColor(TaupeTheme.BACKGROUND)
                .onChange((value: string) => {
                  this.email = value
                })
              
              // Password Field
              TextInput({ placeholder: '密码', text: this.password })
                .type(InputType.Password)
                .width('100%')
                .height(52)
                .backgroundColor(TaupeTheme.BACKGROUND)
                .onChange((value: string) => {
                  this.password = value
                })
              
              if (this.errorMessage) {
                Text(this.errorMessage)
                  .fontSize(12)
                  .fontColor(TaupeTheme.UP)
                  .width('100%')
                  .textAlign(TextAlign.Start)
              }
              
              // Login Button
              Button() {
                if (this.isLoading) {
                  LoadingProgress().width(24).height(24).color('#FFFFFF')
                } else {
                  Text('登录')
                    .fontSize(16)
                    .fontWeight(FontWeight.Medium)
                    .fontColor('#FFFFFF')
                }
              }
              .width('100%')
              .height(48)
              .backgroundColor(TaupeTheme.BRAND)
              .onClick(() => this.handleLogin())
              .enabled(!this.isLoading)
              .scale({ x: this.isLoading ? 0.98 : 1, y: this.isLoading ? 0.98 : 1 })
            }
          }
          .padding(24)
          .margin({ left: 16, right: 16 })
          
          Blank().height(60)
          
          // 4. Footer
          Column({ space: 4 }) {
            Text('Powered by AI & Institutional Data Nodes')
              .fontSize(10)
              .fontColor(TaupeTheme.TEXT_SECONDARY)
              .opacity(0.6)
          }
          .margin({ bottom: 30 })
        }
        .width('100%')
      }
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
  }
}
