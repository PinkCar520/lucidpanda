import SwiftUI
import AlphaDesign
import AlphaData
import Charts

public struct GoldDeepAnalysisSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) var colorScheme
    let pulseData: MarketPulseResponse?
    
    public init(pulseData: MarketPulseResponse?) {
        self.pulseData = pulseData
    }

    public var body: some View {
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 24) {
                        // 1. Gold Price Chart Section
                        priceChartSection
                        
                        // 2. Valuation Summary
                        valuationSummarySection
                        
                        // 3. Quantitative Metrics
                        quantMetricsSection
                        
                        Spacer(minLength: 40)
                    }
                    .padding()
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                }
            }
        }
    }
    
    // MARK: - Sections

    private var priceChartSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("market.asset.gold_spot")
                        .font(.system(size: 10, weight: .bold))
                        .textCase(.uppercase)
                        .kerning(1.0)
                        .foregroundStyle(Color.Alpha.taupe)
                    
                    Text(pulseData.map { String(format: "$%.2f", $0.marketSnapshot.gold.price) } ?? "$2,342.15")
                        .font(.system(size: 28, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.Alpha.textPrimary)
                        .contentTransition(.numericText())
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text(pulseData.map { String(format: "%+.2f%%", $0.marketSnapshot.gold.changePercent) } ?? "+1.24%")
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.up)
                    
                    Text("common.status.live")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(Color.Alpha.taupe.opacity(0.6))
                }
            }
            
            // Mock K-Line Chart
            ZStack(alignment: .bottom) {
                HStack(alignment: .bottom, spacing: 8) {
                    ForEach(0..<12) { i in
                        let height = CGFloat.random(in: 40...120)
                        let isUp = Bool.random()
                        VStack(spacing: 2) {
                            Rectangle()
                                .fill(isUp ? Color.Alpha.up : Color.Alpha.down)
                                .frame(width: 1, height: 10)
                            Rectangle()
                                .fill((isUp ? Color.Alpha.up : Color.Alpha.down).opacity(0.2))
                                .frame(height: height)
                                .overlay(
                                    Rectangle()
                                        .stroke((isUp ? Color.Alpha.up : Color.Alpha.down).opacity(0.4), lineWidth: 1)
                                )
                            Rectangle()
                                .fill(isUp ? Color.Alpha.up : Color.Alpha.down)
                                .frame(width: 1, height: 15)
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
                .frame(height: 180)
                
                HStack {
                    Text("09:00"); Spacer(); Text("15:00"); Spacer(); Text("21:00")
                }
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundStyle(Color.Alpha.taupe.opacity(0.5))
                .padding(.top, 8)
            }
        }
        .padding(20)
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator, lineWidth: 1))
        .shadow(color: colorScheme == .light ? Color.black.opacity(0.03) : Color.clear, radius: 4, y: 2)
    }

    private var valuationSummarySection: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("market.section.valuation_summary")
                .font(.system(size: 11, weight: .black))
                .textCase(.uppercase)
                .kerning(1.5)
                .foregroundStyle(Color.Alpha.taupe)
            
            VStack(spacing: 16) {
                valuationRow(label: "market.metric.total_aum", value: "$42.85M", valueColor: Color.Alpha.textPrimary)
                Divider().background(Color.Alpha.separator.opacity(0.5))
                valuationRow(label: "market.metric.nav", value: "$124.52", valueColor: Color.Alpha.brand)
                Divider().background(Color.Alpha.separator.opacity(0.5))
                valuationRow(label: "market.metric.daily_change", value: "+$1.42 (1.14%)", valueColor: Color.Alpha.up)
            }
        }
        .padding(24)
        .background(Color.Alpha.surfaceContainerLow.opacity(0.5))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.brand.opacity(0.1), lineWidth: 1))
    }

    private var quantMetricsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("market.section.quant_performance")
                .font(.system(size: 11, weight: .black))
                .textCase(.uppercase)
                .kerning(1.5)
                .foregroundStyle(Color.Alpha.taupe)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                metricCard(label: "funds.compact.metric.sharpe.shorthand", value: "1.84", subValue: "↑ 0.2", subColor: Color.Alpha.up)
                metricCard(label: "market.metric.alpha", value: "4.2%", subValue: "↑ 1.1", subColor: Color.Alpha.up)
                metricCard(label: "funds.detail.metric.volatility", value: "12.5%", subValue: "LOW", subColor: Color.Alpha.taupe)
                metricCard(label: "funds.detail.metric.max_drawdown", value: "-6.2%", subValue: "↓ 0.4", subColor: Color.Alpha.down)
            }
        }
    }

    private var actionButtonsSection: some View {
        HStack(spacing: 12) {
            Button { } label: {
                Text("market.action.invest_now")
                    .font(.system(size: 14, weight: .black))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Color.Alpha.brand)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .shadow(color: Color.Alpha.brand.opacity(0.3), radius: 8, y: 4)
            }
            
            Button { } label: {
                Text("market.action.reports")
                    .font(.system(size: 14, weight: .black))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Color.Alpha.surfaceContainerLow)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator, lineWidth: 1))
            }
        }
        .padding(.top, 8)
    }
    
    // MARK: - Components

    private func valuationRow(label: LocalizedStringKey, value: String, valueColor: Color) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(Color.Alpha.textSecondary)
            Spacer()
            Text(value)
                .font(.system(size: 16, weight: .bold, design: .monospaced))
                .foregroundStyle(valueColor)
        }
    }

    private func metricCard(label: LocalizedStringKey, value: String, subValue: String, subColor: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(.system(size: 9, weight: .black))
                .textCase(.uppercase)
                .foregroundStyle(Color.Alpha.taupe)
            
            HStack(alignment: .lastTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 20, weight: .bold, design: .monospaced))
                    .foregroundStyle(Color.Alpha.textPrimary)
                
                Text(subValue)
                    .font(.system(size: 9, weight: .black, design: .monospaced))
                    .foregroundStyle(subColor)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator, lineWidth: 1))
    }
}
