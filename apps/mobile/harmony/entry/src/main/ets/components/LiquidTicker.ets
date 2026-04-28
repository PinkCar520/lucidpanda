import { TaupeTheme } from '../common/Theme'

@Component
export struct LiquidTicker {
  @Prop value: number
  @Prop precision: number = 2
  @Prop prefix: string = ''
  
  @State flickerOpacity: number = 0
  @State displayValue: number = 0

  private triggerFlicker() {
    animateTo({ duration: 50, curve: Curve.EaseIn }, () => {
      this.flickerOpacity = 1.0
    })
    
    setTimeout(() => {
      animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
        this.flickerOpacity = 0
      })
    }, 100)
  }

  aboutToAppear() {
    this.displayValue = this.value
  }

  build() {
    Stack() {
      // Amber Flicker Effect
      Rect()
        .width('100%')
        .height(40)
        .fill('#4DB35919')
        .opacity(this.flickerOpacity)
        .blur(20)
        .borderRadius(12)

      Row({ space: 2 }) {
        if (this.prefix) {
          Text(this.prefix)
            .fontSize(16)
            .fontWeight(FontWeight.Medium)
            .fontColor(TaupeTheme.TEXT_SECONDARY)
            .fontFamily('Monospace')
        }
        
        Text(this.value.toFixed(this.precision))
          .fontSize(20)
          .fontWeight(FontWeight.Black)
          .fontColor(this.value >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN)
          .fontFamily('Monospace')
          .contentTransition(ContentTransition.NumericText) // NEXT special feature
      }
    }
    .onAppear(() => {
      if (this.value !== this.displayValue) {
        this.triggerFlicker()
        this.displayValue = this.value
      }
    })
  }
}
