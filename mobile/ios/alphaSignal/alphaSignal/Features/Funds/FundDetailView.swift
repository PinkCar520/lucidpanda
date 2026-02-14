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
    
    init(valuation: FundValuation) {
        _viewModel = State(initialValue: FundDetailViewModel(valuation: valuation))
    }
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView(showsIndicators: false) {
                VStack(spacing: 24) {
                    headerSection
                    
                    if let stats = viewModel.valuation.stats {
                        actuarialMatrixSection(stats: stats)
                    }
                    
                    smartAlarmSection
                    
                    if let confidence = viewModel.valuation.confidence {
                        confidenceReportSection(confidence: confidence)
                    }
                    
                    sectorAttributionSection
                    
                    if !viewModel.linkedIntelligence.isEmpty {
                        linkedIntelligenceSection
                    }
                    
                    portfolioPenetrationSection
                    
                    historyLedgerSection
                    
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
        .sheet(item: Binding(
            get: { selectedSectorForSheet.map { IdentifiableSector(name: $0.name, stat: $0.stat) } },
            set: { _ in selectedSectorForSheet = nil }
        )) { identifiableSector in
            SectorDetailView(sectorName: identifiableSector.name, stat: identifiableSector.stat)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }
    
    // MARK: - Sub-View Sections
    
    private var headerSection: some View {
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
    }
    
    private func actuarialMatrixSection(stats: FundStats) -> some View {
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
    
    private var smartAlarmSection: some View {
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
    }
    
    private func confidenceReportSection(confidence: FundConfidence) -> some View {
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
    
    private var sectorAttributionSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("行业权重分配")
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
                                Text("\(selected.stat.sub?.count ?? 0) 只成分股")
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
                                                    Text(String(format: "仓位 %.2f%%", subStat.weight))
                                                        .font(.system(size: 9))
                                                        .foregroundStyle(.secondary)
                                                }
                                                Spacer()
                                                Text(String(format: "%+.3f%%", subStat.impact))
                                                    .font(.system(size: 13, weight: .black, design: .monospaced))
                                                    .foregroundStyle(subStat.impact >= 0 ? .red : .green)
                                                
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
                                            .fill(stat.impact >= 0 ? Color.red : Color.green)
                                            .frame(width: 4, height: 24)
                                            .opacity(0.8)
                                        
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(name)
                                                .font(.system(size: 13, weight: .bold))
                                            Text(String(format: "权重 %.1f%%", stat.weight))
                                                .font(.system(size: 9))
                                                .foregroundStyle(.secondary)
                                        }
                                        
                                        Spacer()
                                        
                                        Text(String(format: "%+.2f%%", stat.impact))
                                            .font(.system(size: 13, weight: .black, design: .monospaced))
                                            .foregroundStyle(stat.impact >= 0 ? .red : .green)
                                        
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
                    Text("暂无行业归因数据")
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
    
    private var portfolioPenetrationSection: some View {
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
    }
    
    private var historyLedgerSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("历史对账明细")
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
                    Text("暂无历史对账记录")
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
                            Text("日期").frame(width: 70, alignment: .leading)
                            Spacer()
                            Text("估值").frame(width: 60, alignment: .trailing)
                            Text("实盘").frame(width: 60, alignment: .trailing)
                            Text("偏差").frame(width: 60, alignment: .trailing)
                            Text("精度").frame(width: 40, alignment: .trailing)
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
                                                    .foregroundStyle(est >= 0 ? .red : .green)
                                                    .frame(width: 60, alignment: .trailing)
                                                
                                                let official = record.officialGrowth ?? 0.0
                                                Text(formatPct(official))
                                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                    .foregroundStyle(official >= 0 ? .red : .green)
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
