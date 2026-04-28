import { TaupeTheme } from '../common/Theme'
import { AppRootViewModel, AppState } from '../viewmodel/AppRootViewModel'

@Component
export struct MarketPulseCapsule {
  @ObjectLink marketPulseViewModel: any // Using any for simplicity in prototype link
  @State isAnimating: boolean = false

  private getSentimentColor(): string {
    const sentiment = this.marketPulseViewModel.pulseData?.overall_sentiment || 'neutral'
    if (sentiment === 'bullish') return TaupeTheme.UP
    if (sentiment === 'bearish') return TaupeTheme.DOWN
    return TaupeTheme.NEUTRAL
  }

  build() {
    Row({ space: 8 }) {
      // Breathing Light Icon
      Stack() {
        Circle()
          .width(12)
          .height(12)
          .fill(this.getSentimentColor())
          .opacity(this.isAnimating ? 0.2 : 0.8)
          .scale({ x: this.isAnimating ? 1.4 : 1.0, y: this.isAnimating ? 1.4 : 1.0 })
        
        Circle()
          .width(6)
          .height(6)
          .fill(this.getSentimentColor())
      }
      .onAppear(() => {
        animateTo({ duration: 2000, iterations: -1, curve: Curve.EaseInOut, playMode: PlayMode.Alternate }, () => {
          this.isAnimating = true
        })
      })

      Text('市场脉搏')
        .fontSize(10)
        .fontWeight(FontWeight.Bold)
        .fontColor(TaupeTheme.TEXT_PRIMARY)

      if (this.marketPulseViewModel.pulseData) {
        Text(this.marketPulseViewModel.pulseData.overall_sentiment_zh)
          .fontSize(10)
          .fontWeight(FontWeight.Medium)
          .fontColor(this.getSentimentColor())
      }
    }
    .padding({ left: 12, right: 12, top: 8, bottom: 8 })
    .backgroundColor('#1A000000') // Ultra thin material simulation
    .borderRadius(20)
  }
}
