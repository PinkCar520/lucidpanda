import { TaupeTheme } from '../common/Theme'
import { FundDetailViewModel } from '../viewmodel/FundDetailViewModel'
import { LiquidTicker } from '../components/LiquidTicker'
import { LiquidGlassCard } from '../components/LiquidGlassCard'
import { router } from '@kit.ArkUI'

@Entry
@Component
struct FundDetailView {
  @State viewModel?: FundDetailViewModel = undefined

  aboutToAppear() {
    const params = router.getParams() as Record<string, any>
    if (params && params.valuation) {
      this.viewModel = new FundDetailViewModel(params.valuation, getContext(this))
      this.viewModel.startUpdates()
    }
  }

  aboutToDisappear() {
    this.viewModel?.stopUpdates()
  }

  @Builder ActuarialStat(label: string, value: string, grade: string, color: string) {
    Column({ space: 4 }) {
      Text(label)
        .fontSize(10)
        .fontWeight(FontWeight.Medium)
        .fontColor(TaupeTheme.TEXT_SECONDARY)
      Row({ space: 4 }) {
        Text(value)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontFamily('Monospace')
          .fontColor(TaupeTheme.TEXT_PRIMARY)
        Text(grade)
          .fontSize(10)
          .fontWeight(FontWeight.Medium)
          .padding({ left: 4, right: 4 })
          .backgroundColor(`${color}1A`)
          .fontColor(color)
          .borderRadius(2)
      }
    }
  }

  @Builder AllocationLegend(label: string, color: string) {
    Row({ space: 4 }) {
      Circle().width(6).height(6).fill(color)
      Text(label).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
    }
  }

  build() {
    if (this.viewModel) {
      Column() {
        // Navigation Header
        Row() {
          SymbolGlyph($r('sys.symbol.chevron_left'))
            .fontSize(24)
            .onClick(() => router.back())
          
          Blank()
          
          Text(this.viewModel.valuation.fund_name)
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .fontColor(TaupeTheme.TEXT_PRIMARY)
          
          Blank()
          
          SymbolGlyph($r('sys.symbol.share_fill'))
            .fontSize(20)
            .fontColor([TaupeTheme.BRAND])
        }
        .width('100%')
        .padding(16)
        .backgroundColor(TaupeTheme.SURFACE)

        Scroll() {
          Column({ space: 12 }) {
            // 1. Header Section (Live Growth)
            Column({ space: 8 }) {
              Row({ space: 2 }) {
                LiquidTicker({ 
                  value: this.viewModel.liveGrowth, 
                  precision: 2, 
                  prefix: this.viewModel.liveGrowth >= 0 ? '+' : '' 
                })
                Text('%')
                  .fontSize(16)
                  .fontWeight(FontWeight.Medium)
                  .fontFamily('Monospace')
                  .fontColor(this.viewModel.liveGrowth >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN)
                  .margin({ bottom: 4 })
              }
              .alignItems(VerticalAlign.Bottom)

              Row({ space: 6 }) {
                Circle()
                  .width(6)
                  .height(6)
                  .fill(this.viewModel.liveGrowth >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN)
                Text(this.viewModel.isLive ? '交易中' : '同步中...')
                  .fontSize(10)
                  .fontWeight(FontWeight.Medium)
                  .fontFamily('Monospace')
                  .fontColor(TaupeTheme.TEXT_SECONDARY)
              }
            }
            .width('100%')
            .padding({ top: 32, bottom: 32 })
            .alignItems(HorizontalAlign.Center)

            // 2. Asset Allocation Section
            Column({ space: 8 }) {
              Row() {
                Text('资产配置')
                  .fontSize(12)
                  .fontWeight(FontWeight.Medium)
                  .fontColor(TaupeTheme.TEXT_SECONDARY)
                Blank()
                Text('股票 / 债券 / 现金')
                  .fontSize(10)
                  .fontWeight(FontWeight.Medium)
                  .fontFamily('Monospace')
                  .fontColor(TaupeTheme.TEXT_SECONDARY)
                  .opacity(0.5)
              }
              .width('100%')
              .padding({ left: 16, right: 16 })

              // Progress Bar simulation
              Row() {
                Rect().height(6).fill(TaupeTheme.UP).layoutWeight(75).borderRadius({ topLeft: 3, bottomLeft: 3 })
                Rect().height(6).fill('#008080').layoutWeight(15)
                Rect().height(6).fill(TaupeTheme.NEUTRAL).layoutWeight(10).borderRadius({ topRight: 3, bottomRight: 3 })
              }
              .width('92%')
              .margin({ left: '4%', right: '4%' })

              Row({ space: 12 }) {
                this.AllocationLegend('股票', TaupeTheme.UP)
                this.AllocationLegend('债券', '#008080')
                this.AllocationLegend('现金', TaupeTheme.NEUTRAL)
              }
              .width('100%')
              .padding({ left: 16, right: 16 })
            }

            // 3. Actuarial Matrix
            LiquidGlassCard() {
              Column({ space: 16 }) {
                Row() {
                  this.ActuarialStat('夏普比率', 
                    this.viewModel.valuation.stats?.sharpe_ratio?.toFixed(2) || '0.00', 
                    this.viewModel.valuation.stats?.sharpe_grade || '-', '#FF8C00')
                  Blank()
                  Divider().vertical(true).height(30).color(TaupeTheme.SEPARATOR)
                  Blank()
                  this.ActuarialStat('最大回撤', 
                    `${this.viewModel.valuation.stats?.max_drawdown?.toFixed(2) || '0.00'}%`, 
                    this.viewModel.valuation.stats?.drawdown_grade || '-', '#008080')
                }
                .width('100%')

                Divider().color(TaupeTheme.SEPARATOR).opacity(0.5)

                Row() {
                  Column({ space: 4 }) {
                    Text('近1周').fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                    Text('+1.2%').fontSize(11).fontWeight(FontWeight.Medium).fontColor(TaupeTheme.UP)
                  }.layoutWeight(1)
                  Column({ space: 4 }) {
                    Text('近1月').fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                    Text('+3.5%').fontSize(11).fontWeight(FontWeight.Medium).fontColor(TaupeTheme.UP)
                  }.layoutWeight(1)
                  Column({ space: 4 }) {
                    Text('近3月').fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                    Text('+8.2%').fontSize(11).fontWeight(FontWeight.Medium).fontColor(TaupeTheme.UP)
                  }.layoutWeight(1)
                  Column({ space: 4 }) {
                    Text('近1年').fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                    Text('+12.4%').fontSize(11).fontWeight(FontWeight.Medium).fontColor(TaupeTheme.UP)
                  }.layoutWeight(1)
                }
              }
            }
            .margin({ left: 16, right: 16 })

            // 4. Smart Alarm Section
            LiquidGlassCard() {
              Column({ space: 16 }) {
                Row() {
                  Column({ space: 4 }) {
                    Text('智能波动预警')
                      .fontSize(14)
                      .fontWeight(FontWeight.Medium)
                      .fontColor(TaupeTheme.TEXT_PRIMARY)
                    Text('基于历史波动率的动态监控')
                      .fontSize(10)
                      .fontColor(TaupeTheme.TEXT_SECONDARY)
                  }
                  .alignItems(HorizontalAlign.Start)
                  Blank()
                  Toggle({ type: ToggleType.Switch, isOn: this.viewModel.isAlarmEnabled })
                    .selectedColor(TaupeTheme.BRAND)
                    .onChange((isOn: boolean) => {
                      if (this.viewModel) this.viewModel.isAlarmEnabled = isOn
                    })
                }
                .width('100%')

                Row({ space: 12 }) {
                  SymbolGlyph($r('sys.symbol.bell_badge_fill'))
                    .fontSize(18)
                    .fontColor(['#FF8C00'])
                  
                  Column({ space: 2 }) {
                    Text(`报警阈值: ±${this.viewModel.threshold2Sigma.toFixed(2)}%`)
                      .fontSize(12)
                      .fontWeight(FontWeight.Medium)
                      .fontFamily('Monospace')
                    Text('当前波动已进入 2σ 统计边界')
                      .fontSize(10)
                      .fontColor(TaupeTheme.TEXT_SECONDARY)
                  }
                  .alignItems(HorizontalAlign.Start)
                }
                .width('100%')
                .padding(12)
                .backgroundColor('#0DFF8C00')
                .borderRadius(12)
              }
            }
            .margin({ left: 16, right: 16 })

            // 5. History Ledger
            Column({ space: 12 }) {
              Text('历史对账')
                .fontSize(14)
                .fontWeight(FontWeight.Medium)
                .fontColor(TaupeTheme.TEXT_PRIMARY)
                .padding({ left: 16 })
                .width('100%')
                .textAlign(TextAlign.Start)

              LiquidGlassCard() {
                Column() {
                  Row() {
                    Text('日期').width(70).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                    Blank()
                    Text('估算').width(60).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY).textAlign(TextAlign.End)
                    Text('官方').width(60).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY).textAlign(TextAlign.End)
                    Text('偏离').width(40).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY).textAlign(TextAlign.End)
                  }
                  .width('100%')
                  .padding({ bottom: 12 })

                  ForEach(this.viewModel.history, (record: ValuationHistory) => {
                    Column() {
                      Divider().color(TaupeTheme.SEPARATOR).opacity(0.3)
                      Row() {
                        Text(record.trade_date.substring(5))
                          .width(70)
                          .fontSize(10)
                          .fontFamily('Monospace')
                        
                        Blank()
                        
                        Text(`${record.frozen_est_growth?.toFixed(2)}%`)
                          .width(60)
                          .fontSize(10)
                          .fontWeight(FontWeight.Medium)
                          .fontFamily('Monospace')
                          .fontColor((record.frozen_est_growth || 0) >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN)
                          .textAlign(TextAlign.End)
                        
                        Text(`${record.official_growth?.toFixed(2)}%`)
                          .width(60)
                          .fontSize(10)
                          .fontWeight(FontWeight.Medium)
                          .fontFamily('Monospace')
                          .fontColor((record.official_growth || 0) >= 0 ? TaupeTheme.UP : TaupeTheme.DOWN)
                          .textAlign(TextAlign.End)
                        
                        Text(`${record.deviation?.toFixed(2)}%`)
                          .width(40)
                          .fontSize(10)
                          .fontFamily('Monospace')
                          .fontColor(TaupeTheme.TEXT_SECONDARY)
                          .textAlign(TextAlign.End)
                      }
                      .width('100%')
                      .padding({ top: 10, bottom: 10 })
                    }
                  })
                }
              }
              .margin({ left: 16, right: 16 })
            }

            Blank().height(40)
            
            Text('数据由 AI 与机构数据节点提供支持')
              .fontSize(11)
              .fontColor(TaupeTheme.TEXT_SECONDARY)
              .opacity(0.6)
              .width('100%')
              .textAlign(TextAlign.Center)
              .padding({ bottom: 40 })
          }
        }
        .width('100%')
        .layoutWeight(1)
        .scrollBar(BarState.Off)
        .edgeEffect(EdgeEffect.Spring)
      }
      .width('100%')
      .height('100%')
      .backgroundColor(TaupeTheme.BACKGROUND)
    }
  }
}

import { FundValuation } from '../model/WatchlistModels'
import { ValuationHistory } from '../model/FundDetailModels'
