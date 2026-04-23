import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundCompactCard: View, Equatable {
    let valuation: FundValuation
    @Environment(\.colorScheme) var colorScheme
    
    // Performance: Equatable implementation to prevent body re-evals during scroll
    static func == (lhs: FundCompactCard, rhs: FundCompactCard) -> Bool {
        lhs.valuation.id == rhs.valuation.id && 
        lhs.valuation.estimatedGrowth == rhs.valuation.estimatedGrowth &&
        lhs.valuation.timestamp == rhs.valuation.timestamp
    }

    private var growthText: String {
        let prefix = valuation.estimatedGrowth >= 0 ? "+" : ""
        return "\(prefix)\(String(format: "%.2f", valuation.estimatedGrowth))%"
    }
    
    private var growthColor: Color {
        valuation.estimatedGrowth >= 0 ? Color.Alpha.up : Color.Alpha.down
    }
    
    var body: some View {
        VStack(spacing: 16) {
            HStack(alignment: .top, spacing: 12) {
                // 1. 基金名称与状态标签
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 6) {
                        Text(valuation.fundName)
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                            .lineLimit(1)

                        if valuation.isQdii == true {
                            Text("funds.compact.badge.qdii")
                                .font(.system(size: 8, weight: .black))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.blue.opacity(0.12))
                                .foregroundStyle(.blue)
                                .clipShape(RoundedRectangle(cornerRadius: 2))
                        }
                    }
                    
                    HStack(spacing: 8) {
                        Text(valuation.fundCode)
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundStyle(Color.Alpha.textSecondary.opacity(0.8))
                        
                        if let risk = valuation.riskLevel {
                            Text(risk)
                                .font(.system(size: 8, weight: .black))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(riskColor(risk).opacity(0.1))
                                .foregroundStyle(riskColor(risk))
                                .clipShape(Capsule())
                        }
                        
                        if let confidence = valuation.confidence {
                            Image(systemName: confidenceIcon(confidence.level))
                                .font(.system(size: 10))
                                .foregroundStyle(confidenceColor(confidence.level))
                        }
                    }
                }
                
                Spacer(minLength: 8)
                
                // 2. 实时估值显示
                VStack(alignment: .trailing, spacing: 4) {
                    Text(verbatim: growthText)
                        .font(.system(size: 20, weight: .black, design: .monospaced))
                        .foregroundStyle(growthColor)
                    
                    MarketStatusRow(valuation: valuation)
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
                            .opacity(0.8)
                    }
                } else {
                    Spacer()
                }
                
                Image(systemName: "chevron.right")
                    .font(.system(size: 10, weight: .black))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.3))
                    .padding(.leading, 4)
            }
        }
        .padding(16)
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(Color.Alpha.separator, lineWidth: 1)
        )
        .shadow(color: colorScheme == .light ? Color.black.opacity(0.02) : Color.clear, radius: 2, y: 1)
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
    
    // MARK: - Market Status Sub-View
    
    private struct MarketStatusRow: View {
        let valuation: FundValuation
        
        var body: some View {
            TimelineView(.periodic(from: .now, by: 30)) { context in
                let marketStatus = MarketSessionStatusResolver.status(for: valuation, now: context.date)
                HStack(spacing: 3) {
                    Circle()
                        .fill(statusColor(marketStatus))
                        .frame(width: 5, height: 5)
                    Text(LocalizedStringKey(marketStatus.localizedKey))
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.textSecondary.opacity(0.7))
                }
            }
        }
        
        private func statusColor(_ status: MarketSessionStatus) -> Color {
            switch status {
            case .open: return Color.Alpha.up
            case .lunchBreak: return .orange
            case .closed: return .gray
            }
        }
    }
    
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
