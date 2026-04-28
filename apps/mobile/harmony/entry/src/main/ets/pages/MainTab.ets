import { TaupeTheme } from '../common/Theme'
import { MarketPulseCapsule } from '../components/MarketPulseCapsule'
import { IntelligenceItemCard, IntelligenceCardStyle } from '../components/IntelligenceItemCard'
import { FundCompactCard } from '../components/FundCompactCard'
import { BacktestStatCard } from '../components/BacktestStatCard'
import { LiquidGlassCard } from '../components/LiquidGlassCard'
import { AppRootViewModel } from '../viewmodel/AppRootViewModel'
import { WatchlistViewModel } from '../viewmodel/WatchlistViewModel'
import { BacktestViewModel } from '../viewmodel/BacktestViewModel'
import { router } from '@kit.ArkUI'

@Component
export struct MainTab {
  @ObjectLink rootViewModel: AppRootViewModel
  @State watchlistViewModel: WatchlistViewModel = new WatchlistViewModel(getContext(this))
  @State backtestViewModel: BacktestViewModel = new BacktestViewModel()
  @State selectedIndex: number = 0

  @Builder TabBuilder(index: number, name: string, icon: string) {
    Column() {
      SymbolGlyph($r(icon))
        .fontSize(24)
        .fontColor([this.selectedIndex === index ? TaupeTheme.BRAND : TaupeTheme.TEXT_SECONDARY])
      Text(name)
        .fontSize(10)
        .fontColor(this.selectedIndex === index ? TaupeTheme.BRAND : TaupeTheme.TEXT_SECONDARY)
    }
    .width('100%')
    .height(50)
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Tabs({ barPosition: BarPosition.End, index: this.selectedIndex }) {
      // Tab 1: 情报
      TabContent() {
        Column() {
          Row() {
            MarketPulseCapsule({ marketPulseViewModel: this.rootViewModel.marketPulseViewModel })
            Blank()
            Circle().width(28).height(28).fill(TaupeTheme.BRAND).opacity(0.1)
          }
          .width('100%')
          .padding(16)
          
          List() {
            if (this.rootViewModel.intelligenceViewModel.items.length === 0) {
              ListItem() {
                Column() {
                  LoadingProgress().width(40).height(40).color(TaupeTheme.BRAND)
                  Text('加载情报流...')
                    .fontSize(12)
                    .fontColor(TaupeTheme.TEXT_SECONDARY)
                    .margin({ top: 16 })
                }
                .width('100%')
                .height(400)
                .justifyContent(FlexAlign.Center)
              }
            } else {
              ListItem() {
                IntelligenceItemCard({ 
                  item: this.rootViewModel.intelligenceViewModel.items[0],
                  style: IntelligenceCardStyle.FEATURED
                })
                .margin({ bottom: 20 })
              }
              .padding({ left: 16, right: 16, top: 10 })

              ListItem() {
                Row() {
                  Text('近期要闻')
                    .fontSize(13)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(TaupeTheme.NEUTRAL)
                    .letterSpacing(1.5)
                  Blank()
                  SymbolGlyph($r('sys.symbol.line_3_horizontal_decrease_circle'))
                    .fontSize(16)
                    .fontColor([TaupeTheme.BRAND])
                }
                .width('100%')
                .padding({ left: 16, right: 16, top: 16, bottom: 16 })
              }

              ForEach(this.rootViewModel.intelligenceViewModel.items.slice(1), (item) => {
                ListItem() {
                  IntelligenceItemCard({ 
                    item: item,
                    style: IntelligenceCardStyle.STANDARD
                  })
                }
                .padding({ left: 16, right: 16, top: 6, bottom: 6 })
              }, (item) => item.id.toString())

              ListItem() { Blank().height(100) }
            }
          }
          .width('100%')
          .layoutWeight(1)
          .edgeEffect(EdgeEffect.Spring)
        }
        .width('100%')
        .height('100%')
        .backgroundColor(TaupeTheme.BACKGROUND)
      }
      .tabBar(this.TabBuilder(0, '情报', 'sys.symbol.waveform_path_ecg'))

      // Tab 2: 基金 (Watchlist)
      TabContent() {
        Column() {
          Row() {
            Text('自选列表')
              .fontSize(20)
              .fontWeight(FontWeight.Bold)
              .fontColor(TaupeTheme.TEXT_PRIMARY)
            Blank()
            SymbolGlyph($r('sys.symbol.plus_circle'))
              .fontSize(24)
              .fontColor([TaupeTheme.BRAND])
          }
          .width('100%')
          .padding(16)

          if (this.watchlistViewModel.groups.length > 0) {
            Scroll() {
              Row({ space: 8 }) {
                ForEach(this.watchlistViewModel.groups, (group) => {
                  Text(group.name)
                    .fontSize(12)
                    .padding({ left: 12, right: 12, top: 6, bottom: 6 })
                    .backgroundColor('#1A000000')
                    .borderRadius(15)
                })
              }
              .padding({ left: 16, right: 16, bottom: 12 })
            }
            .scrollable(ScrollDirection.Horizontal)
            .scrollBar(BarState.Off)
          }

          List() {
            if (this.watchlistViewModel.watchlist.length === 0 && !this.watchlistViewModel.isLoading) {
              ListItem() {
                Column({ space: 16 }) {
                  SymbolGlyph($r('sys.symbol.chart_line_uptrend_xyaxis'))
                    .fontSize(48)
                    .fontColor([TaupeTheme.NEUTRAL])
                    .opacity(0.3)
                  Text('暂无自选基金')
                    .fontSize(14)
                    .fontColor(TaupeTheme.NEUTRAL)
                }
                .width('100%')
                .height(400)
                .justifyContent(FlexAlign.Center)
              }
            } else {
              ForEach(this.watchlistViewModel.watchlist, (valuation) => {
                ListItem() {
                  FundCompactCard({ valuation: valuation })
                }
                .padding({ left: 16, right: 16, top: 8, bottom: 8 })
                .onClick(() => {
                  router.pushUrl({
                    url: 'pages/FundDetailView',
                    params: { valuation: valuation }
                  })
                })
              }, (v) => v.fund_code)
            }
          }
          .width('100%')
          .layoutWeight(1)
          .edgeEffect(EdgeEffect.Spring)
          .onRefresh(() => {
            this.watchlistViewModel.fetchWatchlist()
          })
        }
        .width('100%')
        .height('100%')
        .backgroundColor(TaupeTheme.BACKGROUND)
        .onAppear(() => {
          this.watchlistViewModel.fetchWatchlist()
        })
      }
      .tabBar(this.TabBuilder(1, '基金', 'sys.symbol.star'))

      // Tab 3: 回测 (Strategy)
      TabContent() {
        Column() {
          // Header
          Row() {
            Column({ space: 4 }) {
              Row({ space: 4 }) {
                Text('策略').fontSize(26).fontWeight(FontWeight.Black).fontColor(TaupeTheme.TEXT_PRIMARY)
                Text('回测').fontSize(26).fontWeight(FontWeight.Black).fontColor(TaupeTheme.BRAND)
              }
              Text('基于历史样本的策略绩效评估')
                .fontSize(11)
                .fontWeight(FontWeight.Bold)
                .fontColor(TaupeTheme.TEXT_SECONDARY)
                .opacity(0.6)
                .textCase(TextCase.UpperCase)
            }
            .alignItems(HorizontalAlign.Start)
            Blank()
            SymbolGlyph($r('sys.symbol.slider_horizontal_3'))
              .fontSize(18)
              .fontColor([TaupeTheme.TEXT_PRIMARY])
          }
          .width('100%')
          .padding(24)

          Scroll() {
            Column({ space: 32 }) {
              // 1. Configuration Card
              LiquidGlassCard() {
                Column({ space: 20 }) {
                  Text('策略配置')
                    .fontSize(11)
                    .fontWeight(FontWeight.Black)
                    .fontColor(TaupeTheme.TEXT_SECONDARY)
                    .opacity(0.7)
                    .letterSpacing(1.5)
                  
                  Column({ space: 16 }) {
                    // Window Picker (Segmented control simulation)
                    Row({ space: 8 }) {
                      ['15m', '1h', '4h', '12h'].map((w) => {
                        Text(w.toUpperCase())
                          .fontSize(12)
                          .fontWeight(FontWeight.Medium)
                          .layoutWeight(1)
                          .textAlign(TextAlign.Center)
                          .padding(8)
                          .backgroundColor(this.backtestViewModel.selectedWindow === w ? TaupeTheme.BRAND : '#0D000000')
                          .fontColor(this.backtestViewModel.selectedWindow === w ? '#FFFFFF' : TaupeTheme.TEXT_SECONDARY)
                          .borderRadius(4)
                          .onClick(() => this.backtestViewModel.setConfig(w, this.backtestViewModel.minScore, this.backtestViewModel.sentiment))
                      })
                    }
                    .width('100%')
                  }
                  
                  Button('运行回测')
                    .width('100%')
                    .height(48)
                    .backgroundColor(TaupeTheme.BRAND)
                    .labelStyle({ font: { size: 14, weight: FontWeight.Black } })
                    .borderRadius(4)
                    .onClick(() => this.backtestViewModel.fetchStats())
                }
              }
              .margin({ left: 16, right: 16 })

              if (this.backtestViewModel.isLoading) {
                LoadingProgress().width(40).height(40).color(TaupeTheme.BRAND)
              } else if (this.backtestViewModel.stats) {
                // 2. Results Header
                Row() {
                  Text('回测结果').fontSize(18).fontWeight(FontWeight.Bold).fontColor(TaupeTheme.TEXT_PRIMARY)
                  Blank()
                  Text('已完成').fontSize(11).fontWeight(FontWeight.Bold).fontColor(TaupeTheme.TEXT_SECONDARY).opacity(0.5)
                }
                .width('100%')
                .padding({ left: 24, right: 24 })

                // 3. Stats Grid
                Flex({ direction: FlexDirection.Row, wrap: FlexWrap.Wrap }) {
                  BacktestStatCard({ 
                    title: '样本数', 
                    value: this.backtestViewModel.stats.count.toString(), 
                    subValue: '样本规模' 
                  }).width('31%').margin({ right: '2%' })
                  
                  BacktestStatCard({ 
                    title: '风险调整胜率', 
                    value: `${(this.backtestViewModel.stats.adj_win_rate || this.backtestViewModel.stats.win_rate).toFixed(1)}%`, 
                    subValue: 'RAR',
                    color: '#3B82F6'
                  }).width('31%').margin({ right: '2%' })
                  
                  BacktestStatCard({ 
                    title: '平均收益率', 
                    value: `${Math.abs(this.backtestViewModel.stats.avg_drop).toFixed(2)}%`, 
                    subValue: 'RETURN',
                    color: '#EF4444'
                  }).width('31%')
                }
                .width('100%')
                .padding({ left: 16, right: 16 })

                // 4. Session Breakdown
                Column({ space: 12 }) {
                  Text('时段可靠性细分').fontSize(12).fontWeight(FontWeight.Medium).padding({ left: 24 })
                  
                  Grid() {
                    ForEach(this.backtestViewModel.stats.session_stats, (item) => {
                      GridItem() {
                        LiquidGlassCard() {
                          Column({ space: 6 }) {
                            Row() {
                              Text(item.session).fontSize(9).fontWeight(FontWeight.Medium).fontColor(TaupeTheme.TEXT_SECONDARY)
                              Blank()
                            }
                            Row({ space: 4 }) {
                              Text(`${item.win_rate.toFixed(0)}%`).fontSize(16).fontWeight(FontWeight.Bold).fontFamily('Monospace')
                              Text(`n=${item.count}`).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY).opacity(0.6)
                            }
                            .alignItems(VerticalAlign.Bottom)
                          }
                        }
                      }
                    })
                  }
                  .columnsTemplate('1fr 1fr')
                  .columnsGap(10)
                  .rowsGap(10)
                  .width('100%')
                  .padding({ left: 16, right: 16 })
                  .height(160)
                }
                .alignItems(HorizontalAlign.Start)

                // 5. Evidence List
                if (this.backtestViewModel.stats.items) {
                  Column({ space: 12 }) {
                    Text('交易样本明细').fontSize(12).fontWeight(FontWeight.Medium).padding({ left: 24 })
                    
                    ForEach(this.backtestViewModel.stats.items, (item) => {
                      LiquidGlassCard() {
                        Column({ space: 8 }) {
                          Row() {
                            Text(item.title).fontSize(12).fontWeight(FontWeight.Medium).maxLines(1).layoutWeight(1)
                            Text(`${item.change_pct > 0 ? '+' : ''}${item.change_pct.toFixed(2)}%`)
                              .fontSize(12)
                              .fontWeight(FontWeight.Bold)
                              .fontFamily('Monospace')
                              .fontColor(item.is_win ? '#3B82F6' : TaupeTheme.TEXT_SECONDARY)
                          }
                          Row() {
                            Text(`入场: $${item.entry.toFixed(1)} → 出场: $${item.exit.toFixed(1)}`)
                              .fontSize(9)
                              .fontFamily('Monospace')
                              .fontColor(TaupeTheme.TEXT_SECONDARY)
                            Blank()
                            Text(item.timestamp.substring(5, 16)).fontSize(9).fontColor(TaupeTheme.TEXT_SECONDARY)
                          }
                        }
                      }
                    })
                  }
                  .width('100%')
                  .padding({ left: 16, right: 16 })
                  .alignItems(HorizontalAlign.Start)
                }

                Blank().height(100)
              }
            }
          }
          .layoutWeight(1)
          .edgeEffect(EdgeEffect.Spring)
        }
        .width('100%')
        .height('100%')
        .backgroundColor(TaupeTheme.BACKGROUND)
        .onAppear(() => {
          this.backtestViewModel.fetchStats()
        })
      }
      .tabBar(this.TabBuilder(2, '回测', 'sys.symbol.clock_arrow_circlepath'))

      TabContent() { Text('深度发现') }
      .tabBar(this.TabBuilder(3, '发现', 'sys.symbol.magnifyingglass'))
    }
    .width('100%')
    .height('100%')
    .onChange((index: number) => {
      this.selectedIndex = index
    })
  }
}
