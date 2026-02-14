import SwiftUI
import AlphaDesign
import AlphaData
import Charts
import SwiftData

struct FundDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel: FundDetailViewModel
    @Environment(\.colorScheme) var colorScheme
    
    init(valuation: FundValuation) {
        _viewModel = State(initialValue: FundDetailViewModel(valuation: valuation))
    }
    
    // 模拟行业数据 (实际应从后端 sector_attribution 解析)
    private var sectors: [SectorImpact] {
        [
            SectorImpact(name: "黄金资产", weight: 65.5, impact: 0.22),
            SectorImpact(name: "信息技术", weight: 20.2, impact: -0.05),
            SectorImpact(name: "金融", weight: 14.3, impact: 0.08)
        ]
    }
    
    var body: some View {
        @Bindable var viewModel = viewModel
        return ZStack {
            LiquidBackground()
            
            ScrollView(showsIndicators: false) {
                VStack(spacing: 24) {
                    // 1. 实时估值核心显示 (Intraday Estimation)
                    VStack(spacing: 8) {
                        HStack(alignment: .firstTextBaseline) {
                            LiquidTicker(value: viewModel.liveGrowth, precision: 2, prefix: viewModel.liveGrowth >= 0 ? "+" : "")
                                .foregroundStyle(viewModel.liveGrowth >= 0 ? .red : .green)
                            
                            Text("%")
                                .font(.system(size: 16, weight: .black, design: .monospaced))
                                .foregroundStyle(viewModel.liveGrowth >= 0 ? .red : .green)
                        }
                        
                        HStack(spacing: 6) {
                            Circle()
                                .fill(.green)
                                .frame(width: 6, height: 6)
                                .opacity(viewModel.isLive ? 1 : 0.3)
                            
                            Text(viewModel.isLive ? "LIVE 推算中 (Est.)" : "同步中...")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 32)
                    
                    // 2. 精算指标矩阵 (Actuarial Matrix)
                    if let stats = viewModel.valuation.stats {
                        LiquidGlassCard {
                            VStack(spacing: 16) {
                                HStack {
                                    actuarialStat(label: "夏普比率", value: String(format: "%.2f", stats.sharpeRatio ?? 0), grade: stats.sharpeGrade ?? "-", color: .orange)
                                    Spacer()
                                    Divider().frame(height: 30)
                                    Spacer()
                                    actuarialStat(label: "最大回撤", value: String(format: "%.2f", stats.maxDrawdown ?? 0) + "%", grade: stats.drawdownGrade ?? "-", color: .teal)
                                }
                                
                                Divider()
                                
                                HStack(spacing: 0) {
                                    periodReturn(label: "1周", value: stats.return1w)
                                    Spacer()
                                    periodReturn(label: "1月", value: stats.return1m)
                                    Spacer()
                                    periodReturn(label: "3月", value: stats.return3m)
                                    Spacer()
                                    periodReturn(label: "1年", value: stats.return1y)
                                }
                            }
                        }
                        .padding(.horizontal)
                    }
                    
                    // 3. 智能波动报警 (Smart Alarm)
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 16) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("智能 2σ 波动报警")
                                        .font(.system(size: 14, weight: .bold))
                                    Text("基于过去 30 日波动率建议")
                                        .font(.system(size: 10))
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Toggle("", isOn: $viewModel.isAlarmEnabled)
                                    .labelsHidden()
                                    .tint(.orange)
                            }
                            
                            HStack(spacing: 12) {
                                Image(systemName: "bell.badge.fill")
                                    .foregroundStyle(.orange)
                                
                                VStack(alignment: .leading) {
                                    Text("报警阈值: ±\(String(format: "%.2f", viewModel.threshold2Sigma))%")
                                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                                    Text("当前属于 95% 置信区间外的异常波动")
                                        .font(.system(size: 10))
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(.vertical, 8)
                            .padding(.horizontal, 12)
                            .background(.orange.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                    }
                    .padding(.horizontal)
                    
                    // 4. 估值置信度说明 (Confidence Insights)
                    if let confidence = viewModel.valuation.confidence {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("估值分析报告")
                                .font(.system(size: 14, weight: .bold))
                                .padding(.horizontal)
                            
                            LiquidGlassCard {
                                VStack(alignment: .leading, spacing: 12) {
                                    HStack {
                                        Text("置信得分: \(confidence.score)")
                                            .font(.system(size: 12, weight: .black, design: .monospaced))
                                        Spacer()
                                        Text(confidence.level.uppercased())
                                            .font(.system(size: 10, weight: .bold))
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .background(confidenceColor(confidence.level).opacity(0.1))
                                            .foregroundStyle(confidenceColor(confidence.level))
                                            .clipShape(Capsule())
                                    }
                                    
                                    if let reasons = confidence.reasons, !reasons.isEmpty {
                                        VStack(alignment: .leading, spacing: 6) {
                                            ForEach(reasons, id: \.self) { reason in
                                                HStack(spacing: 6) {
                                                    Circle().fill(.gray.opacity(0.3)).frame(width: 4, height: 4)
                                                    Text(reason)
                                                        .font(.system(size: 11))
                                                        .foregroundStyle(.secondary)
                                                }
                                            }
                                        }
                                    }
                                    
                                    if confidence.isSuspectedRebalance == true {
                                        HStack(spacing: 8) {
                                            Image(systemName: "exclamationmark.triangle.fill")
                                            Text("检测到疑似重大调仓，当前持仓数据可能过时")
                                        }
                                        .font(.system(size: 10, weight: .bold))
                                        .padding(10)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color.purple.opacity(0.1))
                                        .foregroundStyle(.purple)
                                        .clipShape(RoundedRectangle(cornerRadius: 8))
                                    }
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                    
                    // 5. 行业分布 (饼图)
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("行业分配")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(colorScheme == .dark ? .white : .black)
                            
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
                    .padding(.horizontal)
                    
                    // 6. 关联地缘政治情报 (Intelligence Linkage)
                    if !viewModel.linkedIntelligence.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Image(systemName: "antenna.radiowaves.left.and.right")
                                    .font(.system(size: 12))
                                Text("关联地缘政治情报")
                                    .font(.system(size: 14, weight: .bold))
                                Spacer()
                            }
                            .foregroundStyle(.blue)
                            .padding(.horizontal)
                            
                            ForEach(viewModel.linkedIntelligence) { item in
                                NavigationLink(destination: IntelligenceDetailView(item: item)) {
                                    LiquidGlassCard {
                                        VStack(alignment: .leading, spacing: 8) {
                                            HStack {
                                                Text(item.urgencyScore >= 8 ? "极高紧迫性" : "重要情报")
                                                    .font(.system(size: 10, weight: .bold))
                                                    .padding(.horizontal, 6)
                                                    .padding(.vertical, 2)
                                                    .background(item.urgencyScore >= 8 ? .red.opacity(0.1) : .orange.opacity(0.1))
                                                    .foregroundStyle(item.urgencyScore >= 8 ? .red : .orange)
                                                    .clipShape(Capsule())
                                                
                                                Spacer()
                                                Text("\(item.urgencyScore).0")
                                                    .font(.system(size: 12, weight: .black, design: .monospaced))
                                                    .foregroundStyle(item.urgencyScore >= 8 ? .red : .orange)
                                            }
                                            
                                            Text(item.summary)
                                                .font(.system(size: 13))
                                                .foregroundStyle(colorScheme == .dark ? .white : .black)
                                                .lineLimit(2)
                                        }
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                            .padding(.horizontal)
                        }
                    }
                    
                    // 7. 持仓归因列表 (Portfolio Penetration)
                    VStack(alignment: .leading, spacing: 12) {
                        Text("持仓穿透分析")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(colorScheme == .dark ? .white : .black)
                            .padding(.horizontal)
                        
                        ForEach(viewModel.valuation.components) { component in
                            LiquidGlassCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(component.name)
                                            .font(.system(size: 14, weight: .bold))
                                            .foregroundStyle(colorScheme == .dark ? .white : .black)
                                        Text(component.code)
                                            .font(.system(size: 10, design: .monospaced))
                                            .foregroundStyle(.secondary)
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
                                        .foregroundStyle(.secondary)
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
        .navigationTitle(viewModel.valuation.fundName)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            viewModel.setModelContext(modelContext)
            viewModel.startLiveUpdates()
        }
        .onDisappear {
            viewModel.stopLiveUpdates()
        }
    }
    
    // --- Subviews ---
    
    private func actuarialStat(label: String, value: String, grade: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.secondary)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 16, weight: .black, design: .monospaced))
                Text(grade)
                    .font(.system(size: 10, weight: .black))
                    .padding(.horizontal, 4)
                    .background(color.opacity(0.1))
                    .foregroundStyle(color)
                    .clipShape(RoundedRectangle(cornerRadius: 2))
            }
        }
    }
    
    private func periodReturn(label: String, value: Double?) -> some View {
        VStack(spacing: 4) {
            Text(label)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(.secondary)
            if let val = value {
                Text("\(val > 0 ? "+" : "")\(String(format: "%.1f", val))%")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(val >= 0 ? .red : .green)
            } else {
                Text("-")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
        }
    }
    
    private func confidenceColor(_ level: String) -> Color {
        switch level {
        case "high": return .green
        case "medium": return .blue
        case "low": return .red
        default: return .gray
        }
    }
}
