import SwiftUI
import AlphaDesign
import AlphaData
import Charts
import SwiftData

struct FundDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel: FundDetailViewModel
    @Environment(\.colorScheme) var colorScheme
    
    // --- 交互状态分离 ---
    @State private var filteredSector: (name: String, stat: SectorStat)? = nil // 饼图联动：原地过滤
    @State private var selectedSectorForSheet: (name: String, stat: SectorStat)? = nil // 列表交互：弹窗
    @State private var showAllHoldings = false // 持仓全量弹窗触发
    @State private var analysisTab: AnalysisTab = .sector
    
    init(valuation: FundValuation) {
        _viewModel = State(initialValue: FundDetailViewModel(valuation: valuation))
    }
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            List {
                Group {
                    headerSection
                    
                    if let stats = viewModel.valuation.stats {
                        actuarialMatrixSection(stats: stats)
                    }
                    
                    smartAlarmSection
                    
                    if let confidence = viewModel.valuation.confidence {
                        confidenceReportSection(confidence: confidence)
                    }
                    
                    analysisSwitcherSection
                    
                    if !viewModel.linkedIntelligence.isEmpty {
                        linkedIntelligenceSection
                    }
                }
                .listRowSeparator(.hidden)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets(top: 12, leading: 0, bottom: 12, trailing: 0))
                Group {
                    historyLedgerSection
                    
                    Text(LocalizedStringKey("funds.disclaimer"))
                        .font(.system(size: 11, weight: .regular))
                        .foregroundStyle(.secondary.opacity(0.8))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                        .padding(.top, 20)
                        .padding(.bottom, 40)
                        .frame(maxWidth: .infinity)
                }
                .listRowSeparator(.hidden)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets(top: 12, leading: 0, bottom: 12, trailing: 0))
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
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
        .onChange(of: analysisTab) { _, newValue in
            if newValue != .sector {
                filteredSector = nil
            }
        }
        .sheet(item: Binding(
            get: { selectedSectorForSheet.map { IdentifiableSector(name: $0.name, stat: $0.stat) } },
            set: { _ in selectedSectorForSheet = nil }
        )) { identifiableSector in
            SectorDetailView(sectorName: identifiableSector.name, stat: identifiableSector.stat)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $showAllHoldings) {
            HoldingsPenetrationView(components: viewModel.valuation.components)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }
    
    // MARK: - Sub-View Sections
    
    private var headerSection: some View {
        VStack(spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                LiquidTicker(value: viewModel.liveGrowth, precision: 2, prefix: viewModel.liveGrowth >= 0 ? "+" : "")
                    .foregroundStyle(viewModel.liveGrowth >= 0 ? Color.Alpha.down : Color.Alpha.up)
                
                Text("%")
                    .font(.system(size: 16, weight: .black, design: .monospaced))
                    .foregroundStyle(viewModel.liveGrowth >= 0 ? Color.Alpha.down : Color.Alpha.up)
            }
            
            TimelineView(.periodic(from: .now, by: 30)) { context in
                let marketStatus = MarketSessionStatusResolver.status(for: viewModel.valuation, now: context.date)
                HStack(spacing: 6) {
                    Circle()
                        .fill(marketStatusColor(marketStatus))
                        .frame(width: 6, height: 6)
                        .opacity(viewModel.isLive ? 1 : 0.3)

                    if viewModel.isLive {
                        Text(LocalizedStringKey(marketStatus.localizedKey))
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    } else {
                        Text("funds.detail.status.syncing")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .padding(.vertical, 32)
    }
    
    private func actuarialMatrixSection(stats: FundStats) -> some View {
        LiquidGlassCard {
            VStack(spacing: 16) {
                HStack {
                    actuarialStat(label: String(localized: "funds.detail.metric.sharpe_ratio"), value: String(format: "%.2f", stats.sharpeRatio ?? 0), grade: stats.sharpeGrade ?? "-", color: .orange)
                    Spacer()
                    Divider().frame(height: 30)
                    Spacer()
                    actuarialStat(label: String(localized: "funds.detail.metric.max_drawdown"), value: String(format: "%.2f", stats.maxDrawdown ?? 0) + "%", grade: stats.drawdownGrade ?? "-", color: .teal)
                }
                
                Divider()
                
                HStack(spacing: 0) {
                    periodReturn(label: String(localized: "funds.detail.period.1w"), value: stats.return1w)
                    Spacer()
                    periodReturn(label: String(localized: "funds.detail.period.1m"), value: stats.return1m)
                    Spacer()
                    periodReturn(label: String(localized: "funds.detail.period.3m"), value: stats.return3m)
                    Spacer()
                    periodReturn(label: String(localized: "funds.detail.period.1y"), value: stats.return1y)
                }
            }
        }
        .padding(.horizontal)
    }
    
    private var smartAlarmSection: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("funds.detail.alarm.title")
                            .font(.system(size: 14, weight: .bold))
                        Text("funds.detail.alarm.subtitle")
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Toggle(
                        "",
                        isOn: Binding(
                            get: { viewModel.isAlarmEnabled },
                            set: { viewModel.isAlarmEnabled = $0 }
                        )
                    )
                    .labelsHidden()
                    .tint(.orange)
                }
                
                HStack(spacing: 12) {
                    Image(systemName: "bell.badge.fill")
                        .foregroundStyle(.orange)
                    
                    VStack(alignment: .leading) {
                        Text(
                            String(
                                format: NSLocalizedString("funds.detail.alarm.threshold_format", comment: ""),
                                String(format: "%.2f", viewModel.threshold2Sigma)
                            )
                        )
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                        Text("funds.detail.alarm.anomaly")
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
    }
    
    private func confidenceReportSection(confidence: FundConfidence) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("funds.detail.report.title")
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal)
            
            LiquidGlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text(
                            String(
                                format: NSLocalizedString("funds.detail.report.confidence_score_format", comment: ""),
                                confidence.score
                            )
                        )
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
                            Text("funds.detail.report.rebalance_warning")
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
    
    private var sectorAttributionSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("funds.detail.sector.title")
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal)
            
            if let attribution = viewModel.valuation.sectorAttribution, !attribution.isEmpty {
                let sortedSectors = attribution.sorted { $0.value.weight > $1.value.weight }
                
                // Visual Overview (Interactive - Precise Radial Trigger)
                LiquidGlassCard {
                    Chart(sortedSectors, id: \.key) { name, stat in
                        SectorMark(
                            angle: .value("Weight", stat.weight),
                            innerRadius: .ratio(0.6),
                            angularInset: filteredSector?.name == name ? 4 : 2
                        )
                        .foregroundStyle(by: .value("Name", name))
                        .opacity(filteredSector == nil || filteredSector?.name == name ? 1.0 : 0.3)
                        .cornerRadius(4)
                    }
                    .frame(height: 180)
                    .chartLegend(position: .bottom, spacing: 12)
                    .padding(.vertical, 8)
                    .chartOverlay { proxy in
                        GeometryReader { geometry in
                            ZStack {
                                Rectangle().fill(.clear).contentShape(Rectangle())
                                    .onTapGesture { location in
                                        let frame = geometry.frame(in: .local)
                                        let center = CGPoint(x: frame.midX, y: frame.midY)
                                        let dx = location.x - center.x
                                        let dy = location.y - center.y
                                        let distance = sqrt(dx*dx + dy*dy)
                                        let chartRadius = min(frame.width, frame.height) / 2.0
                                        let innerR = chartRadius * 0.5
                                        let outerR = chartRadius * 1.1
                                        
                                        guard distance >= innerR && distance <= outerR else { return }
                                        
                                        if let angleValue: Double = proxy.value(atAngle: .radians(atan2(dy, dx) + Double.pi / 2)) {
                                            let total = sortedSectors.reduce(0) { $0 + $1.value.weight }
                                            var current: Double = 0
                                            for (name, stat) in sortedSectors {
                                                current += stat.weight
                                                if angleValue <= (current / total) * total {
                                                    withAnimation(.spring()) {
                                                        if filteredSector?.name == name {
                                                            filteredSector = nil
                                                        } else {
                                                            filteredSector = (name, stat)
                                                        }
                                                    }
                                                    break
                                                }
                                            }
                                        }
                                    }
                            }
                        }
                    }
                }
                .padding(.horizontal)
                
                // Dynamic Linked List
                VStack(spacing: 10) {
                    if let selected = filteredSector {
                        // MODE A: Inline Drill-down (Stocks in selected sector)
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text(selected.name)
                                    .font(.system(size: 12, weight: .black))
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(
                                    String(
                                        format: NSLocalizedString("funds.detail.sector.components_count_format", comment: ""),
                                        selected.stat.sub?.count ?? 0
                                    )
                                )
                                    .font(.system(size: 10))
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.horizontal, 4)
                            
                            if let subItems = selected.stat.sub, !subItems.isEmpty {
                                let sortedSubs = subItems.sorted { $0.value.impact > $1.value.impact }
                                ForEach(sortedSubs, id: \.key) { name, subStat in
                                    Button {
                                        selectedSectorForSheet = selected
                                    } label: {
                                        LiquidGlassCard {
                                            HStack {
                                                VStack(alignment: .leading, spacing: 2) {
                                                    Text(name)
                                                        .font(.system(size: 13, weight: .bold))
                                                    Text(
                                                        String(
                                                            format: NSLocalizedString("funds.detail.sector.position_format", comment: ""),
                                                            subStat.weight
                                                        )
                                                    )
                                                        .font(.system(size: 9))
                                                        .foregroundStyle(.secondary)
                                                }
                                                Spacer()
                                                Text(String(format: "%+.3f%%", subStat.impact))
                                                    .font(.system(size: 13, weight: .black, design: .monospaced))
                                                    .foregroundStyle(subStat.impact >= 0 ? Color.Alpha.down : Color.Alpha.up)
                                                
                                                Image(systemName: "chevron.right")
                                                    .font(.system(size: 10, weight: .bold))
                                                    .foregroundStyle(.tertiary)
                                            }
                                        }
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                        .transition(.opacity)
                    } else {
                        // MODE B: Overview View (All sectors)
                        ForEach(sortedSectors, id: \.key) { name, stat in
                            Button {
                                selectedSectorForSheet = (name, stat)
                            } label: {
                                LiquidGlassCard {
                                    HStack(spacing: 12) {
                                        RoundedRectangle(cornerRadius: 4)
                                            .fill(stat.impact >= 0 ? Color.Alpha.down : Color.Alpha.up)
                                            .frame(width: 4, height: 24)
                                            .opacity(0.8)
                                        
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(name)
                                                .font(.system(size: 13, weight: .bold))
                                            Text(
                                                String(
                                                    format: NSLocalizedString("funds.detail.sector.weight_format", comment: ""),
                                                    stat.weight
                                                )
                                            )
                                                .font(.system(size: 9))
                                                .foregroundStyle(.secondary)
                                        }
                                        
                                        Spacer()
                                        
                                        Text(String(format: "%+.2f%%", stat.impact))
                                            .font(.system(size: 13, weight: .black, design: .monospaced))
                                            .foregroundStyle(stat.impact >= 0 ? Color.Alpha.down : Color.Alpha.up)
                                        
                                        Image(systemName: "chevron.right")
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundStyle(.tertiary)
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                        }
                        .transition(.opacity)
                    }
                }
                .padding(.horizontal)
            } else {
                LiquidGlassCard {
                    Text("funds.detail.sector.empty")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .padding(.horizontal)
            }
        }
    }
    
    private var linkedIntelligenceSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .font(.system(size: 12))
                Text("funds.detail.intelligence.title")
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
                                Text(item.urgencyScore >= 8 ? "funds.detail.intelligence.critical" : "funds.detail.intelligence.important")
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

    private var analysisSwitcherSection: some View {
        VStack(spacing: 12) {
            Picker("analysis", selection: $analysisTab) {
                ForEach(AnalysisTab.allCases) { tab in
                    Text(tab.title).tag(tab)
                }
            }
            .pickerStyle(.segmented)
            .controlSize(.extraLarge)
            .glassEffect(.regular, in: .capsule)
            .padding(.horizontal)
            Group {
                if analysisTab == .sector {
                    sectorAttributionSection
                } else {
                    portfolioPenetrationSection
                }
            }
        }
    }
    
    @ViewBuilder
    private var portfolioPenetrationSection: some View {
        HStack {
            Text("funds.detail.holdings.title")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(colorScheme == .dark ? .white : .black)
            
            Spacer()
            
            if viewModel.valuation.components.count > 3 {
                Button {
                    showAllHoldings = true
                } label: {
                    HStack(spacing: 4) {
                        Text("funds.detail.holdings.view_all")
                        Image(systemName: "chevron.right")
                    }
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.blue)
                }
            }
        }
        .padding(.horizontal)
        .padding(.top, 12)
        
        let topComponents = viewModel.valuation.components
            .sorted { abs($0.impact) > abs($1.impact) }
            .prefix(3)
        
        ForEach(topComponents) { component in
            HoldingRow(component: component)
                .padding(.horizontal)
        }
    }
    
    private var historyLedgerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("funds.detail.history.title")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(colorScheme == .dark ? .white : .black)
                .padding(.horizontal)
            
            if viewModel.isHistoryLoading {
                HStack {
                    Spacer()
                    ProgressView()
                        .padding()
                    Spacer()
                }
            } else if viewModel.history.isEmpty {
                LiquidGlassCard {
                    Text("funds.detail.history.empty")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding()
                }
                .padding(.horizontal)
            } else {
                let historyRecords = viewModel.history
                LiquidGlassCard {
                    VStack(spacing: 0) {
                        // Table Header
                        HStack {
                            Text("funds.detail.history.header.date").frame(width: 70, alignment: .leading)
                            Spacer()
                            Text("funds.detail.history.header.estimate").frame(width: 60, alignment: .trailing)
                            Text("funds.detail.history.header.official").frame(width: 60, alignment: .trailing)
                            Text("funds.detail.history.header.deviation").frame(width: 60, alignment: .trailing)
                            Text("funds.detail.history.header.accuracy").frame(width: 40, alignment: .trailing)
                        }
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.secondary)
                        .padding(.bottom, 12)
                        
                                    ForEach(historyRecords, id: \.tradeDate) { record in
                                        VStack(spacing: 0) {
                                            Divider().opacity(0.5)
                                            HStack {
                                                Text(formatDateString(record.tradeDate))
                                                    .font(.system(size: 10, design: .monospaced))
                                                    .frame(width: 70, alignment: .leading)
                                                
                                                Spacer()
                                                
                                                let est = record.frozenEstGrowth ?? 0.0
                                                Text(formatPct(est))
                                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                    .foregroundStyle(est >= 0 ? Color.Alpha.down : Color.Alpha.up)
                                                    .frame(width: 60, alignment: .trailing)
                                                
                                                let official = record.officialGrowth ?? 0.0
                                                Text(formatPct(official))
                                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                    .foregroundStyle(official >= 0 ? Color.Alpha.down : Color.Alpha.up)
                                                    .frame(width: 60, alignment: .trailing)
                                                
                                                Text(formatPct(record.deviation ?? 0.0))
                                                    .font(.system(size: 10, design: .monospaced))
                                                    .foregroundStyle(.secondary)
                                                    .frame(width: 60, alignment: .trailing)
                                                
                                                accuracyBadge(record.trackingStatus ?? "-")
                                                    .frame(width: 40, alignment: .trailing)
                                            }
                                            .padding(.vertical, 10)
                                        }
                                    }
                    }
                }
                .padding(.horizontal)
            }
        }
    }
    
    // MARK: - Helper Types

    private enum AnalysisTab: String, CaseIterable, Identifiable {
        case sector
        case holdings

        var id: String { rawValue }

        var title: LocalizedStringKey {
            switch self {
            case .sector:
                return "funds.detail.sector.title"
            case .holdings:
                return "funds.detail.holdings.title"
            }
        }
    }
    
    // Identifiable wrapper for SectorStat to use with .sheet
    private struct IdentifiableSector: Identifiable {
        var id: String { name }
        let name: String
        let stat: SectorStat
    }
    
    // MARK: - Subviews Helpers
    
    private func accuracyBadge(_ status: String) -> some View {
        Text(status)
            .font(.system(size: 9, weight: .black))
            .padding(.horizontal, 4)
            .padding(.vertical, 2)
            .background(statusColor(status).opacity(0.1))
            .foregroundStyle(statusColor(status))
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }
    
    private func statusColor(_ status: String) -> Color {
        switch status {
        case "S": return .green
        case "A": return .blue
        case "B": return .orange
        case "C": return .red
        default: return .gray
        }
    }
    
    private func formatPct(_ val: Double) -> String {
        let prefix = val > 0 ? "+" : ""
        return "\(prefix)\(String(format: "%.2f", val))%"
    }
    
    private func formatDateString(_ date: String) -> String {
        // Assume format is YYYY-MM-DD
        return String(date.suffix(5)) // Return MM-DD
    }
    
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
                    .foregroundStyle(val >= 0 ? Color.Alpha.down : Color.Alpha.up)
            } else {
                Text("-")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
        }
    }
    
    private func confidenceColor(_ level: String) -> Color {
        switch level {
        case "high": return Color.Alpha.up
        case "medium": return .blue
        case "low": return Color.Alpha.down
        default: return .gray
        }
    }

    private func marketStatusColor(_ status: MarketSessionStatus) -> Color {
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

// MARK: - Sub-Component: Holding Row

struct HoldingRow: View {
    let component: FundComponent
    @Environment(\.colorScheme) var colorScheme
    
    var body: some View {
        let bgColor: Color? = component.changePct > 0 ? Color.Alpha.down.opacity(0.05) : (component.changePct < 0 ? Color.Alpha.up.opacity(0.05) : nil)
        LiquidGlassCard(backgroundColor: bgColor) {
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
                        .foregroundStyle(component.changePct >= 0 ? Color.Alpha.down : Color.Alpha.up)
                    
                    HStack(spacing: 4) {
                        Text(
                            String(
                                format: NSLocalizedString("funds.detail.holdings.weight_format", comment: ""),
                                String(format: "%.1f", component.weight)
                            )
                        )
                        Text("•")
                        Text(
                            String(
                                format: NSLocalizedString("funds.detail.holdings.contribution_format", comment: ""),
                                String(format: "%.3f", component.impact)
                            )
                        )
                    }
                    .font(.system(size: 8))
                    .foregroundStyle(.secondary)
                }
            }
        }
    }
}

// MARK: - Sub-View: Full Holdings Penetration

struct HoldingsPenetrationView: View {
    let components: [FundComponent]
    @State private var searchText = ""
    @State private var sortMode: SortMode = .impact
    @Environment(\.dismiss) var dismiss
    
    enum SortMode {
        case impact
        case weight
        case performance
        
        var label: String {
            switch self {
            case .impact: return String(localized: "funds.detail.holdings.sort.impact")
            case .weight: return String(localized: "funds.detail.holdings.sort.weight")
            case .performance: return String(localized: "funds.detail.holdings.sort.performance")
            }
        }
        
        var icon: String {
            switch self {
            case .impact: return "bolt.fill"
            case .weight: return "chart.bar.fill"
            case .performance: return "arrow.up.forward"
            }
        }
    }
    
    var filteredResults: [FundComponent] {
        let list = searchText.isEmpty 
            ? components 
            : components.filter { $0.name.contains(searchText) || $0.code.contains(searchText.uppercased()) }
        
        return list.sorted { a, b in
            switch sortMode {
            case .impact: return abs(a.impact) > abs(b.impact)
            case .weight: return a.weight > b.weight
            case .performance: return abs(a.changePct) > abs(b.changePct)
            }
        }
    }
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                VStack(spacing: 0) {
                    // Search & Filter Header
                    VStack(spacing: 12) {
                        HStack {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(.secondary)
                            TextField(String(localized: "funds.detail.holdings.search_prompt"), text: $searchText)
                                .textFieldStyle(.plain)
                        }
                        .padding(10)
                        .background(Color.secondary.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        
                        HStack(spacing: 8) {
                            ForEach([SortMode.impact, .weight, .performance], id: \.self) { mode in
                                Button {
                                    withAnimation(.spring()) { sortMode = mode }
                                } label: {
                                    HStack(spacing: 4) {
                                        Image(systemName: mode.icon)
                                        Text(mode.label)
                                    }
                                    .font(.system(size: 11, weight: .bold))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(sortMode == mode ? Color.blue : Color.secondary.opacity(0.1))
                                    .foregroundStyle(sortMode == mode ? .white : .primary)
                                    .clipShape(Capsule())
                                }
                            }
                            Spacer()
                        }
                    }
                    .padding()
                    .background(.ultraThinMaterial)
                    
                    ScrollView {
                        LazyVStack(spacing: 10) {
                            ForEach(filteredResults) { component in
                                HoldingRow(component: component)
                            }
                        }
                        .padding()
                        .padding(.bottom, 20)
                    }
                }
            }
            .navigationTitle(String(localized: "funds.detail.holdings.full_title"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }
}
