import SwiftUI
import AlphaDesign
import AlphaData
import Charts
import OSLog

struct BacktestView: View {
    @State private var viewModel = BacktestViewModel()
    @State private var hasInitializedConfig = false
    @State private var selectedEvidence: BacktestStats.BacktestItem?
    @State private var selectedIntelligence: IntelligenceItem?
    @State private var loadingEvidenceDetailId: Int?
    @State private var evidenceDetailError: String?
    @State private var showSettingsPopover = false
    @Environment(\.colorScheme) var colorScheme
    private let logger = AppLog.dashboard

    @AppStorage("backtest.window") private var savedWindow = "1h"
    @AppStorage("backtest.min_score") private var savedMinScore = 8
    @AppStorage("backtest.sentiment") private var savedSentiment = "bearish"
    
    var body: some View {
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 32) {
                        headerSection

                        // 1. Configuration Section (Stitch Style)
                        configurationCard()

                        // 2. Results Section (Existing Performance Metrics)
                        VStack(spacing: 24) {
                            resultsHeader

                            if let stats = viewModel.stats {
                                resultsContent(stats)
                            } else if viewModel.isLoading {
                                ProgressView().tint(Color.Alpha.brand).padding(.top, 40)
                            } else {
                                emptyStateView
                            }
                        }

                        if let errorMessage = viewModel.errorMessage {
                            Text(errorMessage)
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.red)
                                .padding(.horizontal)
                        }

                        Spacer(minLength: 120)
                    }
                    .padding(.bottom, 40)
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
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .navigationDestination(item: $selectedIntelligence) { item in
                IntelligenceDetailView(item: item)
            }
            .sheet(isPresented: $showSettingsPopover) {
                settingsSheet
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        withAnimation(.spring()) { showSettingsPopover.toggle() }
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                }
            }
        }
    }
    
    // MARK: - Configuration View
    
    private func configurationCard() -> some View {
        @Bindable var bindable = viewModel
        return LiquidGlassCard {
            VStack(alignment: .leading, spacing: 20) {
                Text("backtest.section.configuration")
                    .font(.system(size: 11, weight: .black))
                    .textCase(.uppercase)
                    .kerning(1.5)
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.7))
                
                VStack(spacing: 16) {
                    // Strategy Type
                    VStack(alignment: .leading, spacing: 8) {
                        Text("backtest.field.strategy_type")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                        
                        Picker("", selection: $bindable.strategyType) {
                            ForEach(BacktestViewModel.StrategyType.allCases) { type in
                                Text(type.localizedName).tag(type)
                            }
                        }
                        .pickerStyle(.menu)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(colorScheme == .dark ? Color.Alpha.surfaceContainerLow : Color.Alpha.surfaceContainerLow)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    
                    // Date Range
                    HStack(spacing: 16) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("backtest.field.start_date")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            DatePicker("", selection: $bindable.startDate, displayedComponents: .date)
                                .labelsHidden()
                                .padding(4)
                                .background(Color.Alpha.surfaceContainerLow)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        
                        VStack(alignment: .leading, spacing: 8) {
                            Text("backtest.field.end_date")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            DatePicker("", selection: $bindable.endDate, displayedComponents: .date)
                                .labelsHidden()
                                .padding(4)
                                .background(Color.Alpha.surfaceContainerLow)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    
                    // Initial Capital
                    VStack(alignment: .leading, spacing: 8) {
                        Text("backtest.field.capital")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                        
                        HStack {
                            Text(verbatim: "$")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textSecondary)
                            TextField("10,000", value: $bindable.initialCapital, format: .number)
                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                .keyboardType(.numberPad)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 12)
                        .background(Color.Alpha.surfaceContainerLow)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
                
                Button {
                    let generator = UIImpactFeedbackGenerator(style: .heavy)
                    generator.impactOccurred()
                    Task { await viewModel.fetchStats() }
                } label: {
                    Text("backtest.action.run_btn")
                        .font(.system(size: 14, weight: .black))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(colorScheme == .dark ? Color.Alpha.brand : Color(hex: "#8D7D77"))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .shadow(color: Color.black.opacity(0.15), radius: 10, y: 5)
                }
                .padding(.top, 12)
            }
        }
        .padding(.horizontal)
    }

    private var resultsHeader: some View {
        HStack {
            Text("backtest.section.results")
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(Color.Alpha.textPrimary)
            
            Spacer()
            
            if viewModel.isLoading {
                Text("backtest.status.simulating")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.Alpha.brand)
            } else {
                Text("backtest.status.complete")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.5))
            }
        }
        .padding(.horizontal, 24)
    }

    @ViewBuilder
    private func resultsContent(_ stats: BacktestStats) -> some View {
        VStack(spacing: 24) {
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
    }
    
    // MARK: - Existing UI Components (Refined)

    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Text("backtest.title_prefix")
                        .font(.system(size: 26, weight: .black))
                        .foregroundStyle(Color.Alpha.textPrimary)
                    Text("backtest.title_suffix")
                        .font(.system(size: 26, weight: .black))
                        .foregroundStyle(Color.Alpha.brand)
                }

                Text("backtest.subtitle")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))
                    .textCase(.uppercase)
                    .kerning(0.5)
            }
            Spacer()
        }
        .padding(.horizontal)
        .padding(.top, 24)
    }
    
    private var settingsSheet: some View {
        NavigationStack {
            ZStack {
                ScrollView {
                    VStack(spacing: 20) {
                        // 最小分数设置
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Label("backtest.setting.min_score", systemImage: "star.fill")
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundStyle(.blue)
                                Spacer()
                                Text(verbatim: "\(viewModel.minScore) / 10")
                                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                                    .foregroundStyle(.primary)
                            }

                            Slider(value: Binding(get: { Double(viewModel.minScore) }, set: { viewModel.minScore = Int($0) }), in: 1...10, step: 1)
                                .tint(.blue)

                            HStack {
                                Text(verbatim: "1")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(verbatim: "10")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.secondary)
                            }

                            if let hint = scoreHint {
                                Label(hint, systemImage: "exclamationmark.triangle.fill")
                                    .font(.system(size: 11, weight: .medium))
                                    .foregroundStyle(.orange)
                                    .padding(.vertical, 4)
                                    .padding(.horizontal, 8)
                                    .background(Color.orange.opacity(0.1))
                                    .cornerRadius(6)
                            }
                        }

                        Divider()
                            .background(Color.gray.opacity(0.2))

                        // 时间窗口设置
                        VStack(alignment: .leading, spacing: 12) {
                            Label("backtest.setting.window", systemImage: "clock.fill")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(.blue)

                            Picker("backtest.metric.window", selection: $viewModel.selectedWindow) {
                                Text("backtest.window.15m").tag("15m")
                                Text("backtest.window.1h").tag("1h")
                                Text("backtest.window.4h").tag("4h")
                                Text("backtest.window.12h").tag("12h")
                                Text("backtest.window.24h").tag("24h")
                            }
                            .pickerStyle(.segmented)
                            .font(.system(size: 12, weight: .medium))
                        }

                        Divider()
                            .background(Color.gray.opacity(0.2))

                        // 交易方向设置
                        VStack(alignment: .leading, spacing: 12) {
                            Label("backtest.setting.direction", systemImage: "arrow.up.arrow.down")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(.blue)

                            Picker("backtest.metric.direction", selection: $viewModel.sentiment) {
                                Text("backtest.direction.bearish_label").tag("bearish")
                                Text("backtest.direction.bullish_label").tag("bullish")
                            }
                            .pickerStyle(.segmented)
                            .font(.system(size: 12, weight: .medium))
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 16)
                    .padding(.bottom, 32)
                }
            }
            .navigationTitle("backtest.setting.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showSettingsPopover = false
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
                
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showSettingsPopover = false
                        Task {
                            await viewModel.fetchStats()
                        }
                    } label: {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.blue)
                    }
                }
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
        }
    }
    
    private func statsGrid(_ stats: BacktestStats) -> some View {
        HStack(spacing: 12) {
            statItem(title: "backtest.metric.sample_size", value: "\(stats.count)", sub: "common.label.n")
            statItem(title: "backtest.metric.risk_adjusted_win_rate", value: String(format: "%.1f%%", stats.adjWinRate ?? stats.winRate), sub: "backtest.metric.rar", color: .blue)
            statItem(title: "backtest.metric.average_return", value: String(format: "%.2f%%", abs(stats.avgDrop)), sub: "common.label.return", color: .red)
        }
        .padding(.horizontal)
    }
    
    private func hygieneSection(_ stats: BacktestStats) -> some View {
        HStack(spacing: 12) {
            statItem(
                title: "backtest.hygiene.clustering",
                value: String(format: "%.1f", stats.hygiene.avgClustering),
                sub: "backtest.hygiene.clustering",
                color: stats.hygiene.avgClustering > 2 ? .orange : .blue
            )
            statItem(
                title: "backtest.hygiene.exhaustion",
                value: String(format: "%.1f", stats.hygiene.avgExhaustion),
                sub: "backtest.hygiene.exhaustion",
                color: stats.hygiene.avgExhaustion > 4 ? .red : .blue
            )
        }
        .padding(.horizontal)
    }
    
    private func statItem(title: LocalizedStringKey, value: String, sub: LocalizedStringKey, color: Color = .primary) -> some View {
        LiquidGlassCard {
            VStack(spacing: 6) {
                Text(title)
                    .font(.system(size: 9, weight: .black))
                    .textCase(.uppercase)
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.5))
                
                Text(value)
                    .font(.system(size: 20, weight: .black, design: .monospaced))
                    .foregroundStyle(color == .primary ? Color.Alpha.textPrimary : color)
                
                Text(sub)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.3))
            }
            .frame(maxWidth: .infinity)
        }
    }
    
    private func sessionChart(_ stats: BacktestStats) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("backtest.section.session_distribution")
                    .font(.system(size: 12, weight: .medium))
                
                Chart(stats.sessionStats) { session in
                    BarMark(
                        x: .value("common.label.session", session.session),
                        y: .value("dashboard.metric.win_rate", session.winRate)
                    )
                    .foregroundStyle(by: .value("common.label.session", session.session))
                    .annotation(position: .top) {
                        Text(verbatim: "\(Int(session.winRate))%")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
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
                .font(.system(size: 12, weight: .medium))
                .padding(.horizontal)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                ForEach(focusedSessions, id: \.self) { name in
                    let item = stats.sessionStats.first(where: { $0.session == name })
                    let isBest = bestSession == name
                    
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(readableSessionName(name))
                                    .font(.system(size: 9, weight: .medium))
                                    .foregroundStyle(isBest ? .blue : .secondary)
                                Spacer()
                                if isBest {
                                    Text("backtest.label.best")
                                        .font(.system(size: 8, weight: .medium))
                                        .foregroundStyle(.blue)
                                }
                            }
                            
                            HStack(alignment: .lastTextBaseline, spacing: 4) {
                                Text(item.map { "\(Int($0.winRate))%" } ?? "-")
                                    .font(.system(size: 16, weight: .semibold, design: .monospaced))
                                Text(verbatim: "n=\(item?.count ?? 0)")
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
                .font(.system(size: 12, weight: .medium))
                .padding(.horizontal)
            
            VStack(spacing: 12) {
                // 1. DXY Sensitivity
                HStack(spacing: 12) {
                    sensitivityCard(title: "backtest.env.dxy_strong", stats: stats.correlation["DXY_STRONG"])
                    sensitivityCard(title: "backtest.env.dxy_weak", stats: stats.correlation["DXY_WEAK"])
                }

                // 2. Volatility (GVZ)
                HStack(spacing: 12) {
                    sensitivityCard(title: "backtest.env.high_vol", stats: stats.volatility?["HIGH_VOL"])
                    sensitivityCard(title: "backtest.env.low_vol", stats: stats.volatility?["LOW_VOL"])
                }

                // 3. Positioning (COT)
                HStack(spacing: 12) {
                    sensitivityCard(title: "backtest.env.overcrowded_long", stats: stats.positioning?["OVERCROWDED_LONG"])
                    sensitivityCard(title: "backtest.env.neutral_position", stats: stats.positioning?["NEUTRAL_POSITION"])
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func distributionChart(_ dist: [BacktestStats.DistributionBin]) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("backtest.section.distribution")
                    .font(.system(size: 12, weight: .medium))
                
                Chart(dist) { bin in
                    BarMark(
                        x: .value("dashboard.metric.returns", bin.bin),
                        y: .value("common.label.count", bin.count)
                    )
                    .foregroundStyle(bin.bin >= 0 ? Color.red.opacity(0.7) : Color.green.opacity(0.7))
                }
                .frame(height: 100)
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        AxisValueLabel {
                            if let val = value.as(Double.self) {
                                Text(verbatim: "\(String(format: "%.1f%%", val))")
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
                .font(.system(size: 12, weight: .medium))
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
                                        .font(.system(size: 12, weight: .medium))
                                        .lineLimit(1)
                                    Spacer()
                                    Text(String(format: "%+.2f%%", item.changePct))
                                        .font(.system(size: 12, weight: .semibold, design: .monospaced))
                                        .foregroundStyle(item.isWin ? .blue : .secondary)
                                }
                                
                                HStack {
                                    Text("backtest.evidence.entry: $\(String(format: "%.1f", item.entry))")
                                    Text(verbatim: "→")
                                    Text("backtest.evidence.exit: $\(String(format: "%.1f", item.exit))")
                                    Spacer()
                                    Text(formatDate(item.timestamp))
                                    Image(systemName: "chevron.right")
                                        .font(.system(size: 9, weight: .medium))
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
    
    private func sensitivityCard(title: LocalizedStringKey, stats: BacktestStats.SessionWinRate?) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.system(size: 10, weight: .black))
                    .textCase(.uppercase)
                    .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))

                if let stats = stats {
                    HStack(alignment: .bottom, spacing: 2) {
                        Text(verbatim: "\(Int(stats.winRate))%")
                            .font(.system(size: 18, weight: .black, design: .monospaced))
                            .foregroundStyle(Color.Alpha.brand)
                        Text("backtest.metric.win_rate_short")
                            .font(.system(size: 8, weight: .bold))
                            .foregroundStyle(Color.Alpha.textSecondary.opacity(0.4))
                            .padding(.bottom, 2)
                    }
                } else {
                    Text("backtest.state.insufficient_sample")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Color.Alpha.textSecondary.opacity(0.3))
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
    
    private var scoreHint: LocalizedStringKey? {
        guard let stats = viewModel.stats, !viewModel.isLoading else { return nil }
        if stats.count == 0 { return "backtest.state.no_data" }
        if stats.count < 5 { return "backtest.state.low_sample_hint" }
        return nil
    }
    
    private var noDataOverlay: some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle")
                .foregroundStyle(.orange)
            Text("backtest.state.no_data")
                .font(.system(size: 12, weight: .medium))
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
                                .font(.system(size: 16, weight: .semibold))

                            HStack {
                                Text(formatDate(item.timestamp))
                                Spacer()
                                Text(String(format: NSLocalizedString("backtest.evidence.score %lld/10", comment: ""), item.score))
                            }
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.secondary)

                            HStack {
                                Text(String(format: NSLocalizedString("backtest.evidence.entry: $%@", comment: ""), String(format: "%.2f", item.entry)))
                                Spacer()
                                Text(String(format: NSLocalizedString("backtest.evidence.exit: $%@", comment: ""), String(format: "%.2f", item.exit)))
                            }
                            .font(.system(size: 11, design: .monospaced))

                            Text(String(format: NSLocalizedString("backtest.evidence.net_change %@", comment: ""), String(format: "%+.3f%%", item.changePct)))
                                .font(.system(size: 14, weight: .medium, design: .monospaced))
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
                            Text(loadingEvidenceDetailId == item.id ? NSLocalizedString("common.loading", comment: "") : NSLocalizedString("backtest.detail.view_full_intelligence", comment: ""))
                        }
                        .font(.subheadline).fontWeight(.regular)
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
                ToolbarItem(placement: .topBarLeading) {
                    Button(action: { selectedEvidence = nil }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
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
            evidenceDetailError = "error.network.generic"
            logger.error("Failed to fetch intelligence detail for item \(item.id, privacy: .public): \(error.localizedDescription, privacy: .public)")
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

    private func readableSessionName(_ name: String) -> LocalizedStringKey {
        switch name {
        case "ASIA": return "backtest.session.asia"
        case "LONDON": return "backtest.session.london"
        case "NEWYORK": return "backtest.session.newyork"
        case "LATE_NY": return "backtest.session.late_ny"
        default: return LocalizedStringKey(name)
        }
    }
}
