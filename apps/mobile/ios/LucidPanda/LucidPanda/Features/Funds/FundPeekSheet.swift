import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData
import OSLog

struct FundPeekSheet: View {
    @Environment(AppRootViewModel.self) private var rootViewModel
    let valuation: FundValuation
    @Environment(\.dismiss) private var dismiss
    private let logger = AppLog.watchlist
    
    @State private var analysis: FundAIAnalysisResponse? = nil
    @State private var narrative: String? = nil
    @State private var isLoading: Bool = true
    @State private var isAnalyzing: Bool = false
    @State private var analyzeError: String? = nil
    @State private var showPaywall = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // 1. Fund Header & Market Status
                    headerSection
                    
                    Divider().padding(.horizontal)
                    
                    // 2. Risk & Performance Matrix (Sharpe, Drawdown, Confidence)
                    performanceSection
                    
                    if let stats = valuation.stats, let sparkData = stats.sparklineData {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(LocalizedStringKey("funds.peek.trend_7d"))
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)
                                .padding(.horizontal)
                            
                            FundSparkline(data: sparkData, isPositive: (stats.return1m ?? 0) >= 0)
                                .frame(height: 40)
                                .padding(.horizontal)
                        }
                    }

                    if isLoading {
                        VStack(spacing: 20) {
                            ProgressView()
                            Text(LocalizedStringKey("funds.peek.analyzing_with_ai"))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                    } else if let data = analysis {
                        
                        // 3. AI Narrative & Deep Analysis
                        aiNarrativeSection
                        
                        // 4. Sector Attribution
                        if let sectors = data.sectorAttribution, !sectors.isEmpty {
                            sectorAttributionSection(sectors: sectors)
                        }

                        // 5. Associated Intelligence Section
                        associatedIntelligenceSection(data: data)

                        // 6. Market Snapshot Context
                        marketSnapshotSection(data: data)
                    }
                }
                .padding(.bottom, 40)
            }
            .navigationTitle("funds.peek.ai_analysis_title")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
            .task {
                await fetchAnalysis()
                await runAINarrative()
            }
        }
    }
    
    // MARK: - Subviews

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(valuation.fundName)
                    .font(.title3).fontWeight(.medium)
                    .foregroundStyle(.primary)
                
                Spacer()
                
                Text(Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: valuation.estimatedGrowth / 100.0)) ?? "\(valuation.estimatedGrowth.formatted(.number.precision(.fractionLength(2))))%")
                    .font(.system(size: 20, weight: .semibold, design: .monospaced))
                    .foregroundStyle(valuation.estimatedGrowth >= 0 ? Color.Alpha.up : Color.Alpha.down)
            }
            
            HStack(spacing: 8) {
                Text(valuation.fundCode)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundStyle(.secondary)
                
                TimelineView(.periodic(from: .now, by: 30)) { context in
                    let marketStatus = MarketSessionStatusResolver.status(for: valuation, now: context.date)
                    HStack(spacing: 4) {
                        Circle()
                            .fill(statusColor(marketStatus))
                            .frame(width: 6, height: 6)
                        Text(LocalizedStringKey(marketStatus.localizedKey))
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .padding(.horizontal)
        .padding(.top, 16)
    }

    private var performanceSection: some View {
        HStack(spacing: 12) {
            if let stats = valuation.stats {
                performanceMetricCard(label: "funds.compact.metric.sharpe.shorthand", value: String(format: "%.2f", stats.sharpeRatio ?? 0), grade: stats.sharpeRatio.map { _ in stats.sharpeGrade ?? "-" } ?? "-")
                performanceMetricCard(label: "funds.compact.metric.drawdown.shorthand", value: String(format: "%.1f%%", stats.maxDrawdown ?? 0), grade: stats.maxDrawdown.map { _ in stats.drawdownGrade ?? "-" } ?? "-")
            }
            
            if let confidence = valuation.confidence {
                VStack(alignment: .leading, spacing: 4) {
                    Text(LocalizedStringKey("common.label.confidence"))
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.secondary)
                    HStack(spacing: 4) {
                        Image(systemName: confidenceIcon(confidence.level))
                            .font(.system(size: 12))
                        Text("\(confidence.score)%")
                            .font(.system(size: 14, weight: .semibold, design: .monospaced))
                    }
                    .foregroundStyle(confidenceColor(confidence.level))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(Color.primary.opacity(0.03))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(.horizontal)
    }

    private func performanceMetricCard(label: String, value: String, grade: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(LocalizedStringKey(label))
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.secondary)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(value)
                    .font(.system(size: 14, weight: .semibold, design: .monospaced))
                Text(grade)
                    .font(.system(size: 10, weight: .black))
                    .padding(.horizontal, 4)
                    .background(Color.primary.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 2))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color.primary.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var aiNarrativeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(LocalizedStringKey("funds.peek.ai_narrative"), systemImage: "sparkles")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.purple)

                Spacer()

                if narrative == nil {
                    Button {
                        if rootViewModel.isPro {
                            Task { await runAINarrative() }
                        } else {
                            showPaywall = true
                        }
                    } label: {
                        if isAnalyzing {
                            HStack(spacing: 6) {
                                ProgressView().scaleEffect(0.75)
                                Text(LocalizedStringKey("intelligence.analysis.analyzing"))
                                    .font(.system(size: 13, weight: .medium))
                                    .foregroundStyle(.secondary)
                            }
                        } else {
                            HStack(spacing: 4) {
                                Image(systemName: "wand.and.stars")
                                Text(LocalizedStringKey("intelligence.analysis.start"))
                            }
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 7)
                            .background(Color.purple)
                            .clipShape(Capsule())
                        }
                    }
                    .disabled(isAnalyzing)
                }
            }
            .padding(.horizontal)

            if let err = analyzeError {
                Text(err)
                    .font(.caption)
                    .foregroundStyle(Color.Alpha.down)
                    .padding(.horizontal)
            }

            Button {
                if !rootViewModel.isPro {
                    showPaywall = true
                }
            } label: {
                LiquidGlassCard(backgroundColor: Color.purple.opacity(0.05)) {
                    VStack(alignment: .leading, spacing: 10) {
                        if let text = narrative {
                            Text(text)
                                .font(.subheadline)
                                .foregroundStyle(.primary.opacity(0.9))
                                .lineSpacing(4)
                                .transition(.move(edge: .top).combined(with: .opacity))
                        } else if let advice = analysis?.topAdvice {
                            Text(advice)
                                .font(.subheadline)
                                .foregroundStyle(.primary.opacity(0.8))
                                .lineSpacing(4)
                        } else {
                            Text(LocalizedStringKey(rootViewModel.isPro ? "funds.peek.no_ai_analysis" : "subscription.error.pro_required"))
                                .font(.subheadline)
                                .italic()
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .buttonStyle(.plain)
            .disabled(rootViewModel.isPro)
            .padding(.horizontal)
        }
    }
    private func sectorAttributionSection(sectors: [String: SectorStat]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(LocalizedStringKey("funds.peek.sector_attribution"), systemImage: "chart.bar.xaxis")
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.teal)
                .padding(.horizontal)
            
            LiquidGlassCard {
                VStack(spacing: 12) {
                    let sorted = sectors.sorted { $0.value.weight > $1.value.weight }.prefix(3)
                    ForEach(Array(sorted), id: \.key) { name, stat in
                        HStack(spacing: 12) {
                            Text(LocalizedStringKey(stat.id.map { "sector.name.\($0)" } ?? name))
                                .font(.system(size: 12, weight: .medium))
                                .frame(width: 60, alignment: .leading)
                                .lineLimit(1)
                            
                            GeometryReader { geo in
                                let width = geo.size.width * CGFloat(min(1.0, stat.weight / 100.0))
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(stat.impact >= 0 ? Color.Alpha.up : Color.Alpha.down)
                                    .frame(width: max(2, width))
                            }
                            .frame(height: 4)
                            .frame(maxWidth: .infinity)
                            
                            let formattedImpact = Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: stat.impact / 100.0)) ?? "\(stat.impact.formatted(.number.precision(.fractionLength(2))))%"
                            Text(formattedImpact)
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .foregroundStyle(stat.impact >= 0 ? Color.Alpha.up : Color.Alpha.down)
                                .frame(width: 60, alignment: .trailing)
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            .padding(.horizontal)
        }
    }

    private func associatedIntelligenceSection(data: FundAIAnalysisResponse) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Label(LocalizedStringKey("funds.peek.related_intelligence"), systemImage: "timeline.selection")
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.blue)
                .padding(.horizontal)
            
            if data.relatedIntelligence.isEmpty {
                VStack(spacing: 0) {
                    IntelligenceTimelinePlaceholderRow(
                        title: "近30天未检索到强关联事件",
                        subtitle: data.fallbackSource ?? "已扩大窗口检索基金相关行业与市场事件"
                    )
                }
                .padding(.horizontal)
            } else {
                let timelineItems = data.relatedIntelligence.sorted(by: { $0.timestamp < $1.timestamp })
                VStack(spacing: 0) {
                    ForEach(Array(timelineItems.enumerated()), id: \.element.id) { index, item in
                        IntelligenceTimelineRow(
                            item: item,
                            isFirst: index == 0,
                            isLast: index == timelineItems.count - 1
                        )
                    }
                }
                .padding(.horizontal)
            }
        }
    }

    private func marketSnapshotSection(data: FundAIAnalysisResponse) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            if let snapshot = data.marketSnapshot {
                Label(LocalizedStringKey("funds.peek.macro_context"), systemImage: "globe.asia.australia.fill")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)

                let isAShareFund = !(valuation.isQdii ?? false)
                VStack(spacing: 12) {
                    if isAShareFund {
                        if let shIndex = snapshot.shIndex, let szIndex = snapshot.szIndex {
                            HStack(spacing: 12) {
                                marketQuoteCard(shIndex, name: shIndex.name, unit: "SH")
                                marketQuoteCard(szIndex, name: szIndex.name, unit: "SZ")
                            }
                        } else if let shIndex = snapshot.shIndex {
                            marketQuoteCard(shIndex, name: shIndex.name, unit: "SH")
                        }
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            marketQuoteCard(snapshot.goldCny ?? snapshot.gold, name: snapshot.goldCny?.name ?? String(localized: "funds.peek.market.gold"), unit: snapshot.goldCny != nil ? "元/克" : nil)
                            marketQuoteCard(snapshot.oil, name: snapshot.oil.name)
                            marketQuoteCard(snapshot.us10y, name: String(localized: "funds.peek.market.us10y"))
                        }
                    } else {
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            marketQuoteCard(snapshot.gold, name: String(localized: "funds.peek.market.gold"))
                            marketQuoteCard(snapshot.dxy, name: String(localized: "funds.peek.market.usd"))
                            marketQuoteCard(snapshot.us10y, name: String(localized: "funds.peek.market.us10y"))
                        }
                    }
                }
                .padding(.horizontal)
            }
        }
    }

    // MARK: - Logic

    private func fetchAnalysis() async {
        isLoading = true
        do {
            let path = "/api/v1/web/watchlist/\(valuation.fundCode)/ai_analysis"
            self.analysis = try await APIClient.shared.fetch(path: path)
        } catch {
            logger.error("Failed to fetch AI analysis for fund \(valuation.fundCode): \(error.localizedDescription, privacy: .public)")
        }
        isLoading = false
    }

    private func runAINarrative() async {
        guard !isAnalyzing, narrative == nil else { return }
        isAnalyzing = true
        analyzeError = nil
        do {
            let path = "/api/v1/web/watchlist/\(valuation.fundCode)/ai_narrative"
            let response: FundAINarrativeResponse = try await APIClient.shared.fetch(path: path)
            withAnimation(.spring()) {
                self.narrative = response.narrative
            }
        } catch {
            logger.error("Failed to generate AI narrative for fund \(valuation.fundCode): \(error.localizedDescription, privacy: .public)")
            analyzeError = String(
                format: NSLocalizedString("intelligence.summary.error", comment: ""),
                error.localizedDescription
            )
        }
        isAnalyzing = false
    }

    private func marketQuoteCard(_ quote: MarketQuote, name: String, unit: String? = nil) -> some View {
        let hasLiveData = quote.timestamp != nil && quote.price != 0
        return LiquidGlassCard(backgroundColor: Color.primary.opacity(0.03)) {
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

                Text(hasLiveData ? String(format: "%.2f", quote.price) : "--")
                    .font(.system(size: 18, weight: .semibold, design: .monospaced))

                if hasLiveData {
                    let formattedChange = Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: quote.changePercent / 100.0)) ?? "\(quote.changePercent.formatted(.number.precision(.fractionLength(2))))%"
                    Text(verbatim: formattedChange)
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundStyle(quote.changePercent >= 0 ? Color.Alpha.up : Color.Alpha.down)
                } else {
                    Text("数据暂缺")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func statusColor(_ status: MarketSessionStatus) -> Color {
        switch status {
        case .open: return Color.Alpha.up
        case .lunchBreak: return .orange
        case .closed: return .gray
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
        case "low": return .red
        default: return .gray
        }
    }
}

struct IntelligenceBriefRow: View {
    let item: FundRelatedIntelligence
    
    var body: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(LocalizedStringKey(item.urgencyScore >= 8 ? "common.urgency.critical" : "common.urgency.important"))
                        .font(.system(size: 9, weight: .medium))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(item.urgencyScore >= 8 ? Color.Alpha.down.opacity(0.12) : Color.Alpha.primary.opacity(0.12))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.primary)
                        .clipShape(Capsule())
                    
                    if let author = item.author {
                        Text(author)
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.secondary)
                            .padding(.leading, 4)
                    }
                    
                    Spacer()
                    
                    Text(item.timestamp.formatted(date: .numeric, time: .shortened))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                
                Text(item.summary)
                    .font(.subheadline).fontWeight(.regular)
                    .foregroundStyle(.primary)
                    .lineLimit(2)

                if let advice = item.advice {
                    Text(advice)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .padding(.top, 4)
                }
            }
        }
    }
}

