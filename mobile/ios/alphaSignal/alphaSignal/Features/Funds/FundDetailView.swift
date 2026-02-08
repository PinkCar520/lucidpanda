import SwiftUI
import AlphaDesign
import AlphaData
import Charts

struct FundDetailView: View {
    let valuation: FundValuation
    @Environment(\.colorScheme) var colorScheme
    
    // 模拟行业数据 (实际应从后端 sector_attribution 解析)
    private var sectors: [SectorImpact] {
        [
            SectorImpact(name: "信息技术", weight: 35.5, impact: 0.12),
            SectorImpact(name: "金融", weight: 20.2, impact: -0.05),
            SectorImpact(name: "消费", weight: 15.8, impact: 0.08),
            SectorImpact(name: "工业", weight: 12.0, impact: -0.02)
        ]
    }
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView(showsIndicators: false) {
                VStack(spacing: 24) {
                    // 1. 行业分布 (饼图)
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("行业分配")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(.white)
                            
                            Chart(sectors) { sector in
                                SectorMark(
                                    angle: .value("Weight", sector.weight),
                                    innerRadius: .ratio(0.6),
                                    angularInset: 2
                                )
                                .foregroundStyle(by: .value("Name", sector.name))
                                .cornerRadius(4)
                            }
                            .frame(height: 180)
                            .chartLegend(position: .bottom, spacing: 12)
                        }
                    }
                    
                    // 2. 核心持仓列表
                    VStack(alignment: .leading, spacing: 12) {
                        Text("持仓归因分析")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(colorScheme == .dark ? .white : .black)
                            .padding(.horizontal)
                        
                        ForEach(valuation.components) { component in
                            LiquidGlassCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(component.name)
                                            .font(.system(size: 14, weight: .bold))
                                            .foregroundStyle(.white)
                                        Text(component.code)
                                            .font(.system(size: 10, design: .monospaced))
                                            .foregroundStyle(.white.opacity(0.4))
                                    }
                                    Spacer()
                                    VStack(alignment: .trailing, spacing: 4) {
                                        Text("\(component.changePct > 0 ? "+" : "")\(String(format: "%.2f", component.changePct))%")
                                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                                            .foregroundStyle(component.changePct >= 0 ? .red : .green)
                                        
                                        HStack(spacing: 4) {
                                            Text("权重 \(String(format: "%.1f", component.weight))%")
                                            Text("•")
                                            Text("贡献 \(String(format: "%.3f", component.impact))%")
                                        }
                                        .font(.system(size: 8))
                                        .foregroundStyle(.white.opacity(0.5))
                                    }
                                }
                            }
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 40)
                }
            }
        }
        .navigationTitle(valuation.fundName)
        .navigationBarTitleDisplayMode(.inline)
    }
}
