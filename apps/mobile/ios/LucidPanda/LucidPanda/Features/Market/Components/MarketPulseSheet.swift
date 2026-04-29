// mobile/ios/LucidPanda/LucidPanda/Features/Market/Components/MarketPulseSheet.swift
import SwiftUI
import AlphaDesign
import AlphaData
import Charts

struct MarketPulseSheet: View {
    let viewModel: MarketPulseViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var selectedPulseSection: PulseSection = .alerts

    private enum PulseSection: Int, CaseIterable, Identifiable {
        case alerts
        case events

        var id: Int { rawValue }

        var title: LocalizedStringKey {
            switch self {
            case .alerts: return LocalizedStringKey("market.pulse.section.alerts.short")
            case .events: return LocalizedStringKey("market.pulse.section.events.short")
            }
        }
    }
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // 1. Overall Sentiment
                    if let data = viewModel.pulseData {
                        sentimentSection(data)
                        
                        Divider().padding(.horizontal)
                        
                        // 2. Market Snapshot (四大品种)
                        marketSnapshotSection(data.marketSnapshot)
                        
                        Divider().padding(.horizontal)
                        
                        Picker(LocalizedStringKey("market.pulse.section_label"), selection: $selectedPulseSection) {
                            ForEach(PulseSection.allCases) { section in
                                Text(section.title).tag(section)
                            }
                        }
                        .pickerStyle(.segmented)
                        .controlSize(.extraLarge)
                        .glassEffect(.regular, in: .capsule)
                        .padding(.horizontal)
                        .padding(.top, 4)
                        .padding(.bottom, 6)
                        
                        if selectedPulseSection == .alerts {
                            topAlertsSection(data.topAlerts)
                        } else {
                            upcomingEventsSection(data.upcomingEvents)
                        }
                    } else {
                        ProgressView()
                            .frame(maxWidth: .infinity, minHeight: 300)
                    }
                }
                .padding(.vertical, 20)
            }
            .navigationTitle("market.pulse.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
    }
    
    // --- UI Sections ---
    
    private func sentimentSection(_ data: MarketPulseResponse) -> some View {
        VStack(spacing: 12) {
            HStack {
                Text("market.pulse.today_sentiment")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                if let last = viewModel.lastUpdated {
                    let timeStr = last.formatted(date: .omitted, time: .shortened)
                    Text("market.pulse.updated_format \(timeStr)")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary.opacity(0.8))
                }
            }
            .padding(.horizontal, 24)
            
            HStack(spacing: 16) {
                Text(sentimentLocalizationKey(data.overallSentiment))
                    .font(.system(size: 32, weight: .semibold))
                    .foregroundStyle(sentimentColor(data.overallSentiment))

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 4) {
                        Image(systemName: sentimentIcon(data.overallSentiment))
                        Text(String(format: "%.2f", data.sentimentScore))
                    }
                    .font(.system(size: 16, weight: .medium, design: .monospaced))
                    .foregroundStyle(sentimentColor(data.overallSentiment))

                    Text("market.pulse.based_on_24h_alerts \(data.alertCount24h)")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
            }
            
            // 情绪刻度尺
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(
                            LinearGradient(
                                colors: [Color.Alpha.down, Color.Alpha.neutral, Color.Alpha.up],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(height: 8)
                    
                    // 指针
                    Capsule()
                        .fill(.white)
                        .frame(width: 4, height: 14)
                        .offset(x: sentimentOffset(data.sentimentScore, width: geo.size.width))
                }
            }
            .frame(height: 20)
            .padding(.horizontal, 40)
            
            // 4. 情绪走势图 (Sparkline)
            if let trend = data.sentimentTrend, !trend.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("market.pulse.24h_trend")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.secondary)
                    
                    Chart {
                        ForEach(trend) { point in
                            LineMark(
                                x: .value("chart.label.time", point.hour),
                                y: .value("chart.label.sentiment", point.score)
                            )
                            .interpolationMethod(.catmullRom)
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [sentimentColor(data.overallSentiment), sentimentColor(data.overallSentiment).opacity(0.3)],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                            
                            AreaMark(
                                x: .value("chart.label.time", point.hour),
                                y: .value("chart.label.sentiment", point.score)
                            )
                            .interpolationMethod(.catmullRom)
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [sentimentColor(data.overallSentiment).opacity(0.15), .clear],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                        }
                    }
                    .chartYScale(domain: -1.0...1.0)
                    .chartXAxis(Visibility.hidden)
                    .chartYAxis(Visibility.hidden)
                    .frame(height: 40)
                }
                .padding(.horizontal, 30)
                .padding(.top, 8)
            }
        }
    }
    
    private func marketSnapshotSection(_ snapshot: MarketSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("market.pulse.core_market_data", systemImage: "chart.line.uptrend.xyaxis")
                .font(.system(size: 16, weight: .medium))
                .padding(.horizontal)
            
            VStack(spacing: 12) {
                // 0. A股核心指数（可用时）
                if let shIndex = snapshot.shIndex, let szIndex = snapshot.szIndex {
                    HStack(spacing: 12) {
                        marketQuoteItem(shIndex, name: "上证指数", unit: "SH")
                        marketQuoteItem(szIndex, name: "深证成指", unit: "SZ")
                    }
                } else if let shIndex = snapshot.shIndex {
                    marketQuoteItem(shIndex, name: "上证指数", unit: "SH")
                }

                // 1. 黄金双品种 (国际/国内)
                HStack(spacing: 12) {
                    marketQuoteItem(snapshot.gold, name: LocalizedStringKey("market.asset.gold"))
                    if let cny = snapshot.goldCny {
                        marketQuoteItem(cny, name: "上海金", unit: "元/克")
                    }
                }
                
                // 2. 宏观三剑客
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    marketQuoteItem(snapshot.dxy, name: LocalizedStringKey("market.asset.dxy"))
                    marketQuoteItem(snapshot.oil, name: LocalizedStringKey("market.asset.oil"))
                    marketQuoteItem(snapshot.us10y, name: LocalizedStringKey("market.asset.us10y"))
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func marketQuoteItem(_ quote: MarketQuote, name: LocalizedStringKey, unit: String? = nil) -> some View {
        LiquidGlassCard(backgroundColor: Color.primary.opacity(0.03)) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(alignment: .lastTextBaseline, spacing: 4) {
                    Text(name)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                    
                    if let unit = unit {
                        Text(unit)
                            .font(.system(size: 8))
                            .foregroundStyle(.secondary.opacity(0.6))
                    }
                }

                Text(String(format: "%.2f", quote.price))
                    .font(.system(size: 18, weight: .semibold, design: .monospaced))
                    .contentTransition(.numericText())

                HStack(spacing: 4) {
                    Text(verbatim: "\(quote.changePercent >= 0 ? "+" : "")\(String(format: "%.2f%%", quote.changePercent))")
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundStyle(quote.changePercent >= 0 ? Color.Alpha.up : Color.Alpha.down)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    
    private func topAlertsSection(_ alerts: [MarketPulseAlert]) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            if alerts.isEmpty {
                Text("market.pulse.no_high_urgency")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
            } else {
                ForEach(alerts) { alert in
                    LiquidGlassCard(backgroundColor: Color.Alpha.up.opacity(0.05)) {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                Text("market.pulse.urgency_score \(alert.urgencyScore)")
                                    .font(.system(size: 9, weight: .semibold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.Alpha.up.opacity(0.1))
                                    .foregroundStyle(Color.Alpha.up)
                                    .clipShape(Capsule())

                                Spacer()

                                Text(alertDateFormatter.string(from: alert.timestamp))
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }

                            Text(alert.summary)
                                .font(.system(size: 14, weight: .medium))
                                .lineLimit(3)
                        }
                    }
                    .padding(.horizontal)
                }
            }
        }
    }

    private func upcomingEventsSection(_ events: [MarketPulseEvent]?) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            if events == nil || events!.isEmpty {
                Text("market.pulse.no_macro_events_48h")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
            } else {
                ForEach(events!) { event in
                    LiquidGlassCard(backgroundColor: Color.Alpha.primary.opacity(0.08)) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(event.country)
                                    .font(.system(size: 10, weight: .medium))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.Alpha.primary.opacity(0.1))
                                    .foregroundStyle(Color.Alpha.primary)
                                    .clipShape(RoundedRectangle(cornerRadius: 4))

                                Spacer()

                                Text(verbatim: "\(event.date) \(event.time ?? "")")
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }

                            Text(event.title)
                                .font(.system(size: 14, weight: .medium))

                            HStack(spacing: 12) {
                                if let prev = event.previous {
                                    Text("market.pulse.previous_value \(prev)")
                                }
                                if let fore = event.forecast {
                                    Text("market.pulse.forecast_value \(fore)")
                                }
                            }
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.horizontal)
                }
            }
        }
    }
    
    
    // --- Helpers ---
    
    private let alertDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter
    }()

    private func sentimentLocalizationKey(_ sentiment: String) -> LocalizedStringKey {
        switch sentiment {
        case "bullish": return LocalizedStringKey("sentiment.bullish")
        case "bearish": return LocalizedStringKey("sentiment.bearish")
        default: return LocalizedStringKey("sentiment.neutral")
        }
    }

    private func sentimentColor(_ sentiment: String) -> Color {
        switch sentiment {
        case "bullish": return Color.Alpha.up
        case "bearish": return Color.Alpha.down
        default: return Color.Alpha.neutral
        }
    }
    
    private func sentimentIcon(_ sentiment: String) -> String {
        switch sentiment {
        case "bullish": return "arrow.up.right.circle.fill"
        case "bearish": return "arrow.down.right.circle.fill"
        default: return "minus.circle.fill"
        }
    }
    
    private func sentimentOffset(_ score: Double, width: CGFloat) -> CGFloat {
        // score is from -1.0 to 1.0
        // mapping to 0 to width
        // Wait, Green (up) is on the left in the gradient?
        // [Color.Alpha.up, Color.Alpha.neutral, Color.Alpha.down]
        // Alpha.up is Green, Alpha.down is Red.
        // So -1.0 (bearish/green) -> 0
        // 0.0 (neutral) -> width / 2
        // 1.0 (bullish/red) -> width
        
        let normalized = (score + 1.0) / 2.0 // 0.0 to 1.0
        return normalized * width - 2 // -2 for half of capsule width
    }
}
