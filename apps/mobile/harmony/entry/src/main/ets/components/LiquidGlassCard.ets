import { TaupeTheme } from '../common/Theme'

@Component
export struct LiquidGlassCard {
  @BuilderParam content: () => void
  private backgroundColor: string = TaupeTheme.SURFACE
  
  build() {
    Column() {
      this.content()
    }
    .width('100%')
    .padding(16)
    .backgroundColor(this.backgroundColor)
    .borderRadius(4)
    .borderWidth(1)
    .borderColor(TaupeTheme.SEPARATOR)
    .shadow({
      radius: 2,
      color: '#0D000000',
      offsetX: 0,
      offsetY: 1
    })
  }
}
