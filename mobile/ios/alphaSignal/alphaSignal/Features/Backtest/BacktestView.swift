import SwiftUI
import AlphaDesign
import AlphaData
import Charts

struct BacktestView: View {
    @State private var viewModel = BacktestViewModel()
    @State private var showConfig = false
    @State private var hasInitializedConfig = false
    @State private var selectedEvidence: BacktestStats.BacktestItem?
    @State private var selectedIntelligence: IntelligenceItem?
    @State private var loadingEvidenceDetailId: Int?
    @State private var evidenceDetailError: String?
    
    @AppStorage("backtest.window") private var savedWindow = "1h"
    @AppStorage("backtest.min_score") private var savedMinScore = 8
    @AppStorage("backtest.sentiment") private var savedSentiment = "bearish"
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 24) {
                        headerSection
                        
                        if showConfig {
                            configPanel.transition(.move(edge: .top).combined(with: .opacity))
                        }
                        
                        if let stats = viewModel.stats {
                            ZStack {
                                VStack(spacing: 20) {
                                    statsGrid(stats)
                                    hygieneSection(stats)
                                    sessionChart(stats)
                                    sessionBreakdownSection(stats)
                                    environmentSection(stats)
                                    
                                    if let dist = stats.distribution, !dist.isEmpty {
                                        distributionChart(dist)
                                    }
                                    
                                    if let items = stats.items, !items.isEmpty {
                                        evidenceListSection(items)
                                    }
                                }
                                
                                if stats.count == 0 {
                                    noDataOverlay
                                }
                            }
                            
                        } else if viewModel.isLoading {
                            ProgressView().tint(.blue).padding(.top, 40)
                        } else {
                            emptyStateView
                        }
                        
                        if let errorMessage = viewModel.errorMessage {
                            Text(errorMessage)
                                .font(.caption)
                                .foregroundStyle(.red)
                                .padding(.horizontal)
                        }
                        
                        Spacer(minLength: 100)
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .task {
                if !hasInitializedConfig {
                    viewModel.applySavedConfiguration(
                        window: normalizedWindow(savedWindow),
                        minScore: max(1, min(savedMinScore, 10)),
                        sentiment: normalizedSentiment(savedSentiment)
                    )
                    hasInitializedConfig = true
                }
                await viewModel.fetchStats()
            }
            .onChange(of: viewModel.selectedWindow) {
                guard hasInitializedConfig else { return }
                savedWindow = viewModel.selectedWindow
                viewModel.scheduleRefresh(.immediate)
            }
            .onChange(of: viewModel.sentiment) {
                guard hasInitializedConfig else { return }
                savedSentiment = viewModel.sentiment
                viewModel.scheduleRefresh(.immediate)
            }
            .onChange(of: viewModel.minScore) {
                guard hasInitializedConfig else { return }
                savedMinScore = viewModel.minScore
                viewModel.scheduleRefresh(.debounced)
            }
            .sheet(item: $selectedEvidence) { item in
                evidenceDetailSheet(item)
            }
            .navigationDestination(item: $selectedIntelligence) { item in
                IntelligenceDetailView(item: item)
            }
        }
    }
    
    // MARK: - Sub-View Sections
    
    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("backtest.title")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                
                Text("backtest.subtitle")
                    .font(.caption2)
                    .foregroundStyle(.gray)
            }
            Spacer()
            
            Button {
                withAnimation(.spring()) { showConfig.toggle() }
            } label: {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(.blue)
                    .padding(10)
                    .background(.blue.opacity(0.1))
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
    }
    
    private var configPanel: some View {
        LiquidGlassCard {
            VStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("\(t("backtest.metric.min_score")): \(viewModel.minScore)")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                        Spacer()
                        Text("\(t("backtest.metric.direction")): \(viewModel.sentiment == "bearish" ? t("backtest.direction.bearish") : t("backtest.direction.bullish"))")
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                    }
                    .foregroundStyle(.blue)
                    
                    Slider(value: Binding(get: { Double(viewModel.minScore) }, set: { viewModel.minScore = Int($0) }), in: 1...10, step: 1)
                        .tint(.blue)
                    
                    if let hint = scoreHint {
                        Text(hint)
                            .font(.system(size: 9, weight: .semibold))
                            .foregroundStyle(.orange)
                    }
                }
                
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("backtest.metric.window").font(.system(size: 9, weight: .bold)).foregroundStyle(.secondary)
                        Picker("backtest.metric.window", selection: $viewModel.selectedWindow) {
                            Text("backtest.window.15m").tag("15m")
                            Text("backtest.window.1h").tag("1h")
                            Text("backtest.window.4h").tag("4h")
                            Text("backtest.window.12h").tag("12h")
                            Text("backtest.window.24h").tag("24h")
                        }
                        .pickerStyle(.segmented)
                        .font(.system(size: 12, weight: .bold))
                        .glassEffect(.regular, in: .rect(cornerRadius: 12))
                        .padding(.vertical, 4)
                    }
                }
                
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("backtest.metric.direction").font(.system(size: 9, weight: .bold)).foregroundStyle(.secondary)
                        Picker("backtest.metric.direction", selection: $viewModel.sentiment) {
                            Text("backtest.direction.bearish").tag("bearish")
                            Text("backtest.direction.bullish").tag("bullish")
                        }
                        .pickerStyle(.segmented)
                        .font(.system(size: 12, weight: .bold))
                        .glassEffect(.regular, in: .rect(cornerRadius: 12))
                        .padding(.vertical, 4)
                    }
                }
                
                Button {
                    Task { 
                        withAnimation { showConfig = false }
                        await viewModel.fetchStats() 
                    }
                } label: {
                    Text("backtest.action.run")
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .padding(.horizontal)
    }
    
    private func statsGrid(_ stats: BacktestStats) -> some View {
        HStack(spacing: 12) {
            statItem(title: t("backtest.metric.sample_size"), value: "\(stats.count)", sub: "N")
            statItem(title: t("backtest.metric.risk_adjusted_win_rate"), value: String(format: "%.1f%%", stats.adjWinRate), sub: "RAR", color: .blue)
            statItem(title: t("backtest.metric.average_return"), value: String(format: "%.2f%%", abs(stats.avgDrop)), sub: "Return", color: .red)
        }
        .padding(.horizontal)
    }
    
    private func hygieneSection(_ stats: BacktestStats) -> some View {
        HStack(spacing: 12) {
            statItem(
                title: t("backtest.hygiene.clustering"),
                value: String(format: "%.1f", stats.hygiene.avgClustering),
                sub: "Clustering",
                color: stats.hygiene.avgClustering > 2 ? .orange : .blue
            )
            statItem(
                title: t("backtest.hygiene.exhaustion"),
                value: String(format: "%.1f", stats.hygiene.avgExhaustion),
                sub: "Exhaustion",
                color: stats.hygiene.avgExhaustion > 4 ? .red : .blue
            )
        }
        .padding(.horizontal)
    }
    
    private func statItem(title: String, value: String, sub: String, color: Color = .primary) -> some View {
        LiquidGlassCard {
            VStack(spacing: 4) {
                Text(title)
                    .font(.system(size: 8, weight: .bold))
                    .foregroundStyle(.gray)
                Text(value)
                    .font(.system(size: 18, weight: .black, design: .monospaced))
                    .foregroundStyle(color == .primary ? .primary : color)
                Text(sub)
                    .font(.system(size: 8, weight: .bold))
                    .foregroundStyle(.gray.opacity(0.5))
            }
            .frame(maxWidth: .infinity)
        }
    }
    
    private func sessionChart(_ stats: BacktestStats) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("backtest.section.session_distribution")
                    .font(.system(size: 12, weight: .bold))
                
                Chart(stats.sessionStats) { session in
                    BarMark(
                        x: .value("Session", session.session),
                        y: .value("WinRate", session.winRate)
                    )
                    .foregroundStyle(by: .value("Session", session.session))
                    .annotation(position: .top) {
                        Text("\(Int(session.winRate))%")
                            .font(.system(size: 8, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(height: 120)
                .chartLegend(.hidden)
                .chartYScale(domain: 0...100)
            }
        }
        .padding(.horizontal)
    }
    
    private func sessionBreakdownSection(_ stats: BacktestStats) -> some View {
        let focusedSessions = ["ASIA", "LONDON", "NEWYORK", "LATE_NY"]
        let bestSession = stats.sessionStats.max(by: { $0.winRate < $1.winRate })?.session
        
        return VStack(alignment: .leading, spacing: 12) {
            Text("backtest.section.session_breakdown")
                .font(.system(size: 12, weight: .bold))
                .padding(.horizontal)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                ForEach(focusedSessions, id: \.self) { name in
                    let item = stats.sessionStats.first(where: { $0.session == name })
                    let isBest = bestSession == name
                    
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(readableSessionName(name))
                                    .font(.system(size: 9, weight: .bold))
                                    .foregroundStyle(isBest ? .blue : .secondary)
                                Spacer()
                                if isBest {
                                    Text("backtest.label.best")
                                        .font(.system(size: 8, weight: .bold))
                                        .foregroundStyle(.blue)
                                }
                            }
                            
                            HStack(alignment: .lastTextBaseline, spacing: 4) {
                                Text(item.map { "\(Int($0.winRate))%" } ?? "-")
                                    .font(.system(size: 16, weight: .black, design: .monospaced))
                                Text("n=\(item?.count ?? 0)")
                                    .font(.system(size: 9, weight: .medium, design: .monospaced))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func environmentSection(_ stats: BacktestStats) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("backtest.section.environment")
                .font(.system(size: 12, weight: .bold))
                .padding(.horizontal)
            
            VStack(spacing: 12) {
                // 1. DXY Sensitivity
                HStack(spacing: 12) {
                    sensitivityCard(title: t("backtest.env.dxy_strong"), stats: stats.correlation["DXY_STRONG"])
                    sensitivityCard(title: t("backtest.env.dxy_weak"), stats: stats.correlation["DXY_WEAK"])
                }
                
                // 2. Volatility (GVZ)
                HStack(spacing: 12) {
                    sensitivityCard(title: t("backtest.env.high_vol"), stats: stats.volatility?["HIGH_VOL"])
                    sensitivityCard(title: t("backtest.env.low_vol"), stats: stats.volatility?["LOW_VOL"])
                }
                
                // 3. Positioning (COT)
                HStack(spacing: 12) {
                    sensitivityCard(title: t("backtest.env.overcrowded_long"), stats: stats.positioning?["OVERCROWDED_LONG"])
                    sensitivityCard(title: t("backtest.env.neutral_position"), stats: stats.positioning?["NEUTRAL_POSITION"])
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func distributionChart(_ dist: [BacktestStats.DistributionBin]) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("backtest.section.distribution")
                    .font(.system(size: 12, weight: .bold))
                
                Chart(dist) { bin in
                    BarMark(
                        x: .value("Returns", bin.bin),
                        y: .value("Count", bin.count)
                    )
                    .foregroundStyle(bin.bin >= 0 ? Color.red.opacity(0.7) : Color.green.opacity(0.7))
                }
                .frame(height: 100)
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        AxisValueLabel {
                            if let val = value.as(Double.self) {
                                Text("\(val, specifier: "%.1f")%")
                                    .font(.system(size: 8))
                            }
                        }
                    }
                }
            }
        }
        .padding(.horizontal)
    }
    
    private func evidenceListSection(_ items: [BacktestStats.BacktestItem]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("backtest.section.evidence")
                .font(.system(size: 12, weight: .bold))
                .padding(.horizontal)
            
            VStack(spacing: 10) {
                ForEach(items) { item in
                    Button {
                        evidenceDetailError = nil
                        selectedEvidence = item
                    } label: {
                        LiquidGlassCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(item.title)
                                        .font(.system(size: 12, weight: .bold))
                                        .lineLimit(1)
                                    Spacer()
                                    Text(String(format: "%+.2f%%", item.changePct))
                                        .font(.system(size: 12, weight: .black, design: .monospaced))
                                        .foregroundStyle(item.isWin ? .blue : .secondary)
                                }
                                
                                HStack {
                                    Text("\(t("backtest.evidence.entry")): $\(String(format: "%.1f", item.entry))")
                                    Text("→")
                                    Text("\(t("backtest.evidence.exit")): $\(String(format: "%.1f", item.exit))")
                                    Spacer()
                                    Text(formatDate(item.timestamp))
                                    Image(systemName: "chevron.right")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundStyle(.gray.opacity(0.5))
                                }
                                .font(.system(size: 9, design: .monospaced))
                                .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func sensitivityCard(title: String, stats: BacktestStats.SessionWinRate?) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(.secondary)
                
                if let stats = stats {
                    HStack(alignment: .bottom, spacing: 2) {
                        Text("\(Int(stats.winRate))%")
                            .font(.system(size: 16, weight: .black, design: .monospaced))
                            .foregroundStyle(.blue)
                        Text("backtest.metric.win_rate_short")
                            .font(.system(size: 7))
                            .foregroundStyle(.secondary)
                            .padding(.bottom, 2)
                    }
                } else {
                    Text("backtest.state.insufficient_sample").font(.system(size: 10)).foregroundStyle(.tertiary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM-dd HH:mm"
        return formatter.string(from: date)
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Spacer(minLength: 100)
            Image(systemName: "chart.bar.xaxis")
                .font(.largeTitle)
                .foregroundStyle(.gray.opacity(0.2))
            Text("backtest.state.empty")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
    }
    
    private var scoreHint: String? {
        guard let stats = viewModel.stats, !viewModel.isLoading else { return nil }
        if stats.count == 0 { return t("backtest.state.no_data") }
        if stats.count < 5 { return t("backtest.state.low_sample_hint") }
        return nil
    }
    
    private var noDataOverlay: some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle")
                .foregroundStyle(.orange)
            Text("backtest.state.no_data")
                .font(.system(size: 12, weight: .bold))
            Text("backtest.state.no_data_hint")
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
        }
        .padding(14)
        .background(Color.white.opacity(0.9))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private func evidenceDetailSheet(_ item: BacktestStats.BacktestItem) -> some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(item.title)
                                .font(.system(size: 16, weight: .black))
                            
                            HStack {
                                Text(formatDate(item.timestamp))
                                Spacer()
                                Text("\(t("backtest.evidence.score")) \(item.score)/10")
                            }
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.secondary)
                            
                            HStack {
                                Text("\(t("backtest.evidence.entry")): \(String(format: "%.2f", item.entry))")
                                Spacer()
                                Text("\(t("backtest.evidence.exit")): \(String(format: "%.2f", item.exit))")
                            }
                            .font(.system(size: 11, design: .monospaced))
                            
                            Text("\(t("backtest.evidence.net_change")) \(String(format: "%+.3f%%", item.changePct))")
                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                .foregroundStyle(item.isWin ? .blue : .red)
                        }
                    }
                    .padding(.horizontal)
                    
                    if let evidenceDetailError = evidenceDetailError {
                        Text(evidenceDetailError)
                            .font(.caption)
                            .foregroundStyle(.red)
                            .padding(.horizontal)
                    }
                    
                    Button {
                        Task { await openIntelligenceDetail(for: item) }
                    } label: {
                        HStack(spacing: 8) {
                            if loadingEvidenceDetailId == item.id {
                                ProgressView().tint(.white)
                            } else {
                                Image(systemName: "arrow.up.right.square")
                            }
                            Text(loadingEvidenceDetailId == item.id ? t("common.loading") : t("backtest.detail.view_full_intelligence"))
                        }
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .disabled(loadingEvidenceDetailId == item.id)
                    .padding(.horizontal)
                }
                .padding(.top, 16)
            }
            .navigationTitle("backtest.detail.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("common.close") { selectedEvidence = nil }
                }
            }
        }
    }
    
    private func openIntelligenceDetail(for item: BacktestStats.BacktestItem) async {
        loadingEvidenceDetailId = item.id
        evidenceDetailError = nil
        do {
            let detail = try await viewModel.fetchIntelligenceDetail(id: item.id)
            selectedEvidence = nil
            selectedIntelligence = detail
        } catch {
            evidenceDetailError = t("error.network.generic")
            print("Failed to fetch intelligence detail for backtest item \(item.id): \(error)")
        }
        loadingEvidenceDetailId = nil
    }
    
    private func normalizedWindow(_ value: String) -> String {
        switch value {
        case "15m", "1h", "4h", "12h", "24h":
            return value
        default:
            return "1h"
        }
    }
    
    private func normalizedSentiment(_ value: String) -> String {
        switch value {
        case "bearish", "bullish":
            return value
        default:
            return "bearish"
        }
    }
    
    private func windowLabel(_ value: String) -> String {
        switch value {
        case "15m": return "15M"
        case "1h": return "1H"
        case "4h": return "4H"
        case "12h": return "12H"
        case "24h": return "24H"
        default: return "1H"
        }
    }
    
    private func readableSessionName(_ name: String) -> String {
        switch name {
        case "ASIA": return t("backtest.session.asia")
        case "LONDON": return t("backtest.session.london")
        case "NEWYORK": return t("backtest.session.newyork")
        case "LATE_NY": return t("backtest.session.late_ny")
        default: return name
        }
    }

    private func t(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }
}
