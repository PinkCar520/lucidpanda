import { TaupeTheme } from '../common/Theme'
import { FundValuation } from '../model/WatchlistModels'
import { LiquidTicker } from './LiquidTicker'

@Component
export struct FundCompactCard {
  @Prop valuation: FundValuation
  
  private getGrowthColor(): string {
    return this.valuation.estimated_growth >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN
  }

  build() {
    Column({ space: 16 }) {
      Row() {
        // 1. Fund Name & Code
        Column({ space: 6 }) {
          Row({ space: 6 }) {
            Text(this.valuation.fund_name)
              .fontSize(16)
              .fontWeight(FontWeight.Bold)
              .fontColor(TaupeTheme.TEXT_PRIMARY)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
              .layoutWeight(1)
          }
          
          Text(this.valuation.fund_code)
            .fontSize(11)
            .fontWeight(FontWeight.Bold)
            .fontColor(TaupeTheme.TEXT_SECONDARY)
            .fontFamily('Monospace')
            .opacity(0.8)
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start)

        // 2. Real-time Valuation
        Column({ space: 4 }) {
          LiquidTicker({ 
            value: this.valuation.estimated_growth, 
            prefix: this.valuation.estimated_growth >= 0 ? '+' : ''
          })
          
          Row({ space: 3 }) {
            Circle().width(5).height(5).fill(this.getGrowthColor())
            Text('盘中估值')
              .fontSize(9)
              .fontWeight(FontWeight.Bold)
              .fontColor(TaupeTheme.TEXT_SECONDARY)
              .opacity(0.7)
          }
        }
        .alignItems(HorizontalAlign.End)
      }
      .width('100%')
    }
    .width('100%')
    .padding(16)
    .backgroundColor(TaupeTheme.SURFACE)
    .borderRadius(4)
    .borderWidth(1)
    .borderColor(TaupeTheme.SEPARATOR)
  }
}
