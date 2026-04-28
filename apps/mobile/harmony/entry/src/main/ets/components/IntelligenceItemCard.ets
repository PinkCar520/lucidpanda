import { TaupeTheme } from '../common/Theme'
import { IntelligenceItem } from '../model/IntelligenceModels'

export enum IntelligenceCardStyle {
  FEATURED,
  STANDARD
}

@Component
export struct IntelligenceItemCard {
  @Prop item: IntelligenceItem
  @Prop style: IntelligenceCardStyle = IntelligenceCardStyle.STANDARD
  
  private getUrgencyColor(): string {
    return this.item.urgency_score >= 8 ? TaupeTheme.UP : TaupeTheme.BRAND
  }

  private getFormattedTime(): string {
    const date = new Date(this.item.timestamp)
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  }

  @Builder FeaturedLayout() {
    Column() {
      // Image Placeholder / Image
      Stack({ alignContent: Alignment.BottomStart }) {
        if (this.item.image_url) {
          Image(this.item.image_url)
            .width('100%')
            .aspectRatio(16/9)
            .objectFit(ImageFit.Cover)
        } else {
          Rect()
            .width('100%')
            .aspectRatio(16/9)
            .fill(TaupeTheme.BACKGROUND)
        }
        
        Row({ space: 8 }) {
          Text('精选分析')
            .fontSize(9)
            .fontWeight(FontWeight.Black)
            .fontColor('#FFFFFF')
            .backgroundColor(TaupeTheme.BRAND)
            .padding({ left: 8, right: 8, top: 4, bottom: 4 })
            .borderRadius(4)
          
          Text('5分钟阅读')
            .fontSize(9)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .shadow({ radius: 2, color: '#4D000000' })
        }
        .padding(16)
      }
      .width('100%')
      .borderRadius({ topLeft: 4, topRight: 4 })
      .clip(true)

      Column({ space: 12 }) {
        Text(this.item.summary)
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(TaupeTheme.TEXT_PRIMARY)
          .maxLines(3)
          .textOverflow({ overflow: TextOverflow.Ellipsis })

        Text(this.item.content)
          .fontSize(14)
          .fontColor(TaupeTheme.TEXT_SECONDARY)
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        
        Button('阅读全文')
          .width('100%')
          .height(44)
          .backgroundColor(TaupeTheme.BRAND)
          .labelStyle({ font: { size: 13, weight: FontWeight.Black } })
          .borderRadius(4)
      }
      .padding(20)
      .backgroundColor(TaupeTheme.SURFACE)
    }
    .width('100%')
    .borderRadius(4)
    .borderWidth(1)
    .borderColor(TaupeTheme.SEPARATOR)
  }

  @Builder StandardLayout() {
    Row({ space: 16 }) {
      Column({ space: 10 }) {
        // Meta info
        Row({ space: 8 }) {
          Text(`${this.item.urgency_score}.0`)
            .fontSize(10)
            .fontWeight(FontWeight.Black)
            .fontColor(this.getUrgencyColor())
            .backgroundColor(this.item.urgency_score >= 8 ? '#1ADC2626' : '#1AB35919')
            .padding({ left: 6, right: 6, top: 2, bottom: 2 })
            .borderRadius(2)

          Text(this.item.author)
            .fontSize(10)
            .fontWeight(FontWeight.Bold)
            .fontColor(TaupeTheme.NEUTRAL)
          
          Blank()
          
          Text(this.getFormattedTime())
            .fontSize(9)
            .fontWeight(FontWeight.Medium)
            .fontColor(TaupeTheme.NEUTRAL)
            .opacity(0.6)
        }
        .width('100%')

        // Summary
        Text(this.item.summary)
          .fontSize(15)
          .fontWeight(FontWeight.Bold)
          .fontColor(TaupeTheme.TEXT_PRIMARY)
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })

        // Asset Snapshot
        if (this.item.gold_price_snapshot) {
          Row({ space: 4 }) {
            Text('黄金')
              .fontSize(8)
              .fontWeight(FontWeight.Black)
              .fontColor(TaupeTheme.BRAND)
            Text(`$${this.item.gold_price_snapshot.toFixed(2)}`)
              .fontSize(10)
              .fontWeight(FontWeight.Bold)
              .fontColor(TaupeTheme.TEXT_SECONDARY)
          }
        }
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)

      // Thumbnail
      if (this.item.image_url) {
        Image(this.item.image_url)
          .width(80)
          .height(80)
          .borderRadius(4)
          .objectFit(ImageFit.Cover)
      } else {
        Stack() {
          SymbolGlyph($r('sys.symbol.newspaper_fill'))
            .fontSize(24)
            .fontColor([TaupeTheme.BRAND])
            .opacity(0.15)
        }
        .width(80)
        .height(80)
        .backgroundColor(TaupeTheme.BACKGROUND)
        .borderRadius(4)
      }
    }
    .width('100%')
    .padding(14)
    .backgroundColor(TaupeTheme.SURFACE)
    .borderRadius(4)
    .borderWidth(1)
    .borderColor(TaupeTheme.SEPARATOR)
  }

  build() {
    Column() {
      if (this.style === IntelligenceCardStyle.FEATURED) {
        this.FeaturedLayout()
      } else {
        this.StandardLayout()
      }
    }
    .width('100%')
  }
}
