import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundCompactCard: View {
    let valuation: FundValuation
    @Environment(\.colorScheme) var colorScheme
    
    var body: some View {
        VStack(spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                // 1. 基金名称与状态标签
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 6) {
                        Text(valuation.fundName)
                            .font(.system(size: 15, weight: .medium))
                            .foregroundStyle(colorScheme == .dark ? .white : Color(red: 0.06, green: 0.09, blue: 0.16))
                            .lineLimit(1)

                        if valuation.isQdii == true {
                            Text("funds.compact.badge.qdii")
                                .font(.system(size: 8, weight: .semibold))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.blue.opacity(0.1))
                                .foregroundStyle(.blue)
                                .clipShape(RoundedRectangle(cornerRadius: 2))
                        }
                    }
                    
                    HStack(spacing: 8) {
                        Text(valuation.fundCode)
                            .font(.system(size: 10, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        
                        if let risk = valuation.riskLevel {
                            Text(risk)
                                .font(.system(size: 8, weight: .medium))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(riskColor(risk).opacity(0.1))
                                .foregroundStyle(riskColor(risk))
                                .clipShape(Capsule())
                        }
                        
                        if let confidence = valuation.confidence {
                            Image(systemName: confidenceIcon(confidence.level))
                                .font(.system(size: 10))
                                .foregroundStyle(confidenceColor(confidence.level))
                            
                            if confidence.isSuspectedRebalance == true {
                                Image(systemName: "exclamationmark.arrow.triangle.2.circlepath")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.purple)
                            }
                        }
                    }
                }
                
                Spacer()
                
                // 2. 实时估值显示
                VStack(alignment: .trailing, spacing: 2) {
                    Text(verbatim: "\(valuation.estimatedGrowth >= 0 ? "+" : "")\(String(format: "%.2f", valuation.estimatedGrowth))%")
                        .font(.system(size: 18, weight: .semibold, design: .monospaced))
                        .foregroundStyle(valuation.estimatedGrowth >= 0 ? Color.Alpha.down : Color.Alpha.up)
                    
                    TimelineView(.periodic(from: .now, by: 30)) { context in
                        let marketStatus = MarketSessionStatusResolver.status(for: valuation, now: context.date)
                        HStack(spacing: 3) {
                            Circle()
                                .fill(statusColor(marketStatus))
                                .frame(width: 4, height: 4)
                            Text(LocalizedStringKey(marketStatus.localizedKey))
                                .font(.system(size: 8, weight: .semibold, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            
            // 3. 底部性能矩阵与走势图
            HStack(alignment: .center) {
                if let stats = valuation.stats {
                    HStack(spacing: 8) {
                        gradeBadge(labelKey: "funds.compact.metric.sharpe.shorthand", grade: stats.sharpeGrade ?? "-", color: .orange)
                        gradeBadge(labelKey: "funds.compact.metric.drawdown.shorthand", grade: stats.drawdownGrade ?? "-", color: .teal)
                    }
                    
                    Spacer()
                    
                    if let sparkData = stats.sparklineData {
                        FundSparkline(data: sparkData, isPositive: (stats.return1m ?? 0) >= 0)
                            .frame(width: 60, height: 20)
                            .opacity(0.6)
                    }
                } else {
                    Spacer()
                    Text("funds.compact.no_data")
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary.opacity(0.5))
                }
                
                Image(systemName: "hand.tap.fill")
                    .font(.system(size: 8))
                    .foregroundStyle(.tertiary)
                    .padding(.leading, 8)

                Image(systemName: "chevron.right")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(.gray.opacity(0.3))
                    .padding(.leading, 4)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(uiColor: .systemBackground))
        )
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isPressed)
        .onLongPressGesture(minimumDuration: 0.4, pressing: { pressing in
            withAnimation { isPressed = pressing }
        }, perform: {
            showPeek = true
        })
        .sheet(isPresented: $showPeek) {
            FundPeekSheet(valuation: valuation)
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }

    @State private var isPressed: Bool = false
    @State private var showPeek: Bool = false
    
    // --- UI Helpers ---
    
    private func gradeBadge(labelKey: String, grade: String, color: Color) -> some View {
        HStack(spacing: 2) {
            Text(LocalizedStringKey(labelKey))
                .font(.system(size: 8, weight: .medium))
                .foregroundStyle(.secondary)
            Text(verbatim: ":")
                .font(.system(size: 8, weight: .medium))
                .foregroundStyle(.secondary)
            Text(grade)
                .font(.system(size: 8, weight: .semibold))
                .foregroundStyle(grade == "S" ? color : (grade == "A" ? .blue : .gray))
        }
        .padding(.horizontal, 5)
        .padding(.vertical, 2)
        .background(Color.black.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }
    
    private func riskColor(_ risk: String) -> Color {
        switch risk {
        case "R1", "R2": return .blue
        case "R3": return .orange
        case "R4": return Color.Alpha.down
        case "R5": return .purple
        default: return .gray
        }
    }
    
    private func confidenceIcon(_ level: String) -> String {
        switch level {
        case "high": return "target"
        case "medium": return "scale.3d"
        case "low": return "exclamationmark.triangle"
        default: return "questionmark.circle"
        }
    }
    
    private func confidenceColor(_ level: String) -> Color {
        switch level {
        case "high": return .green
        case "medium": return .blue
        case "low": return Color.Alpha.down
        default: return .gray
        }
    }

    private func statusColor(_ status: MarketSessionStatus) -> Color {
        switch status {
        case .open:
            return Color.Alpha.up
        case .lunchBreak:
            return .orange
        case .closed:
            return .gray
        }
    }
}

#Preview {
    VStack(spacing: 16) {
        FundCompactCard(valuation: FundValuation(
            fundCode: "001234",
            fundName: "黄金主题成长精选",
            estimatedGrowth: 1.25,
            totalWeight: 95.0,
            components: [],
            timestamp: Date(),
            isQdii: true,
            confidence: FundConfidence(level: "high", score: 95, isSuspectedRebalance: true, reasons: []),
            riskLevel: "R4",
            stats: FundStats(return1w: 0.5, return1m: 2.3, return3m: 5.1, return1y: 12.0, sharpeRatio: 1.8, sharpeGrade: "S", maxDrawdown: -5.2, drawdownGrade: "A", volatility: 15.0, sparklineData: [0.1, 0.4, 0.2, 0.8, 0.6, 0.9])
        ))
        
        FundCompactCard(valuation: FundValuation(
            fundCode: "519001",
            fundName: "科技创新动力混合",
            estimatedGrowth: -0.85,
            totalWeight: 88.0,
            components: [],
            timestamp: Date(),
            stats: nil
        ))
    }
    .padding()
    .background(Color.gray.opacity(0.1))
}
