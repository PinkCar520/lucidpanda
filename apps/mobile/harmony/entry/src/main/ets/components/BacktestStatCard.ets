import { TaupeTheme } from '../common/Theme'
import { LiquidGlassCard } from './LiquidGlassCard'

@Component
export struct BacktestStatCard {
  @Prop title: string
  @Prop value: string
  @Prop subValue: string
  @Prop color: string = TaupeTheme.TEXT_PRIMARY

  build() {
    LiquidGlassCard() {
      Column({ space: 6 }) {
        Text(this.title)
          .fontSize(9)
          .fontWeight(FontWeight.Black)
          .fontColor(TaupeTheme.TEXT_SECONDARY)
          .opacity(0.5)
          .textCase(TextCase.UpperCase)
        
        Text(this.value)
          .fontSize(20)
          .fontWeight(FontWeight.Black)
          .fontFamily('Monospace')
          .fontColor(this.color)
        
        Text(this.subValue)
          .fontSize(9)
          .fontWeight(FontWeight.Bold)
          .fontColor(TaupeTheme.TEXT_SECONDARY)
          .opacity(0.3)
      }
      .width('100%')
      .alignItems(HorizontalAlign.Center)
    }
  }
}
