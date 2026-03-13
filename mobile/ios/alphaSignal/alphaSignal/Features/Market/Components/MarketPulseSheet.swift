// mobile/ios/alphaSignal/alphaSignal/Features/Market/Components/MarketPulseSheet.swift
import SwiftUI
import AlphaDesign
import AlphaData
import Charts

struct MarketPulseSheet: View {
    let viewModel: MarketPulseViewModel
    @Environment(\.dismiss) private var dismiss
    
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
                        
                        // 3. Top Alerts
                        topAlertsSection(data.topAlerts)
                        
                        Divider().padding(.horizontal)
                        
                        // 4. Upcoming Events
                        upcomingEventsSection(data.upcomingEvents ?? [])
                    } else {
                        ProgressView()
                            .frame(maxWidth: .infinity, minHeight: 300)
                    }
                }
                .padding(.vertical, 20)
            }
            .navigationTitle("市场脉搏")
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
                Text("今日整体情绪")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                if let last = viewModel.lastUpdated {
                    Text("\(last.formatted(date: .omitted, time: .shortened)) 更新")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary.opacity(0.8))
                }
            }
            .padding(.horizontal, 24)
            
            HStack(spacing: 16) {
                Text(data.overallSentimentZh)
                    .font(.system(size: 32, weight: .black))
                    .foregroundStyle(sentimentColor(data.overallSentiment))
                
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 4) {
                        Image(systemName: sentimentIcon(data.overallSentiment))
                        Text(String(format: "%.2f", data.sentimentScore))
                    }
                    .font(.system(size: 16, weight: .bold, design: .monospaced))
                    .foregroundStyle(sentimentColor(data.overallSentiment))
                    
                    Text("基于近 24h \(data.alertCount24h) 条情报聚合")
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
                                colors: [Color.Alpha.up, Color.Alpha.neutral, Color.Alpha.down],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(height: 8)
                    
                    // 指针
                    Capsule()
                        .fill(.white)
                        .frame(width: 4, height: 14)
                        .shadow(radius: 2)
                        .offset(x: sentimentOffset(data.sentimentScore, width: geo.size.width))
                }
            }
            .frame(height: 20)
            .padding(.horizontal, 40)
            
            // 4. 情绪走势图 (Sparkline)
            if let trend = data.sentimentTrend, !trend.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("24h 情绪走势")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.secondary)
                    
                    Chart {
                        ForEach(trend) { point in
                            LineMark(
                                x: .value("时间", point.hour),
                                y: .value("情绪", point.score)
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
                                x: .value("时间", point.hour),
                                y: .value("情绪", point.score)
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
            Label("核心市场行情", systemImage: "chart.line.uptrend.xyaxis")
                .font(.system(size: 16, weight: .bold))
                .padding(.horizontal)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                marketQuoteItem(snapshot.gold, name: "伦敦金")
                marketQuoteItem(snapshot.dxy, name: "美元指数")
                marketQuoteItem(snapshot.oil, name: "美原油")
                marketQuoteItem(snapshot.us10y, name: "美债 10Y")
            }
            .padding(.horizontal)
        }
    }
    
    private func marketQuoteItem(_ quote: MarketQuote, name: String) -> some View {
        LiquidGlassCard(backgroundColor: Color.primary.opacity(0.03)) {
            VStack(alignment: .leading, spacing: 4) {
                Text(name)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.secondary)
                
                Text(String(format: "%.2f", quote.price))
                    .font(.system(size: 18, weight: .black, design: .monospaced))
                
                HStack(spacing: 4) {
                    Text("\(quote.changePercent >= 0 ? "+" : "")\(String(format: "%.2f%%", quote.changePercent))")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundStyle(quote.changePercent >= 0 ? Color.Alpha.down : Color.Alpha.up)
                }
            }
        }
    }
    
    private func topAlertsSection(_ alerts: [MarketPulseAlert]) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("高紧急情报摘要", systemImage: "exclamationmark.shield.fill")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(Color.Alpha.down)
                .padding(.horizontal)
            
            if alerts.isEmpty {
                Text("暂无高紧急度情报")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
            } else {
                ForEach(alerts) { alert in
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                Text("紧急度 \(alert.urgencyScore)")
                                    .font(.system(size: 9, weight: .black))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.Alpha.down.opacity(0.1))
                                    .foregroundStyle(Color.Alpha.down)
                                    .clipShape(Capsule())
                                
                                Spacer()
                                
                                Text(alert.timestamp.formatted(date: .omitted, time: .shortened))
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }
                            
                            Text(alert.summary)
                                .font(.system(size: 14, weight: .bold))
                                .lineLimit(3)
                        }
                    }
                    .padding(.horizontal)
                }
            }
        }
    }

    private func upcomingEventsSection(_ events: [MarketPulseEvent]) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("即将发生的重要事件", systemImage: "calendar.badge.clock")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(.blue)
                .padding(.horizontal)
            
            if events.isEmpty {
                Text("未来 48h 暂无重大宏观日程")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
            } else {
                ForEach(events) { event in
                    LiquidGlassCard(backgroundColor: Color.blue.opacity(0.03)) {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(event.country)
                                    .font(.system(size: 10, weight: .black))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.blue.opacity(0.1))
                                    .foregroundStyle(.blue)
                                    .clipShape(RoundedRectangle(cornerRadius: 4))
                                
                                Spacer()
                                
                                Text("\(event.date) \(event.time ?? "")")
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }
                            
                            Text(event.title)
                                .font(.system(size: 14, weight: .bold))
                            
                            HStack(spacing: 12) {
                                if let prev = event.previous {
                                    Text("前值: \(prev)")
                                }
                                if let fore = event.forecast {
                                    Text("预测: \(fore)")
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
    
    private func sentimentColor(_ sentiment: String) -> Color {
        switch sentiment {
        case "bullish": return Color.Alpha.down
        case "bearish": return Color.Alpha.up
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
