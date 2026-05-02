import SwiftUI
import AlphaDesign
import AlphaData
import Charts

public struct GoldDeepAnalysisSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) var colorScheme
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var viewModel = GoldDeepAnalysisViewModel()
    @State private var isTickerAnimating = false
    @State private var selectedDate: Date?
    
    // 🎨 回归 App 语义化主题色
    private let actualLineColor = Color.Alpha.up
    private let predictionLineColor = Color(hex: "#007AFF")
    private let breakoutFillColor = Color.Alpha.up.opacity(0.12)
    private let confidenceFillColor = Color(hex: "#007AFF").opacity(0.08)
    private let pivotLineColor = Color.Alpha.taupe.opacity(0.4)

    private var beijingCalendar: Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Shanghai")!
        return cal
    }

    private static let beijingTimeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeZone = TimeZone(identifier: "Asia/Shanghai")
        formatter.dateFormat = "HH:mm"
        return formatter
    }()

    private static let beijingDayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeZone = TimeZone(identifier: "Asia/Shanghai")
        formatter.dateFormat = "MM-dd"
        return formatter
    }()

    private func formatBeijingTime(_ date: Date, useDay: Bool = false) -> String {
        if useDay {
            return Self.beijingDayFormatter.string(from: date)
        }
        return Self.beijingTimeFormatter.string(from: date)
    }

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
//                Color.Alpha.background.ignoresSafeArea()
                
                if viewModel.isLoading && viewModel.predictionData == nil {
                    ProgressView().tint(Color.Alpha.brand)
                } else {
                    ScrollView {
                        VStack(spacing: 24) {
                            // 1. Header Toolbar
                            topControlBar
                            
                            // 2. Legend
                            legendView
                            
                            // 3. Main Chart
                            mainChartSection
                            
                            // 5. Metric Cards
                            metricCardsGrid
                            }
                            .padding(.horizontal)
                            .padding(.top)
                            }
                            .refreshable {
                            await viewModel.fetchPrediction(forceRefresh: true)
                            }
                            }
                            }
            .navigationTitle("gold.prediction.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                }
            }
            .task {
                await viewModel.fetchInitialData()
            }
        }
    }
    
    // MARK: - Components

    private var topControlBar: some View {
        HStack(alignment: .bottom) {
            // Left Side: Live Price Data (Vertical Stack)
            let gold = rootViewModel.marketPulseViewModel.pulseData?.marketSnapshot.gold
            let isMarketClosed = viewModel.predictionData?.marketStatus == "CLOSED"
            
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(isMarketClosed ? Color.Alpha.neutral : Color.Alpha.brand)
                        .frame(width: 6, height: 6)
                        .opacity(isMarketClosed ? 0.6 : (isTickerAnimating ? 1 : 0.4))
                        .scaleEffect(isMarketClosed ? 1.0 : (isTickerAnimating ? 1.1 : 0.8))
                        .animation(isMarketClosed ? .default : .easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: isTickerAnimating)
                    
                    Text(gold != nil ? "$\(String(format: "%.2f", gold!.price))" : "—")
                        .font(.system(size: 20, weight: .bold, design: .monospaced))
                        .foregroundStyle(isMarketClosed ? Color.Alpha.textSecondary : Color.Alpha.textPrimary)
                        .contentTransition(.numericText())
                }
                
                Text(isMarketClosed ? String(localized: "market.status.closed_label") : (gold?.formattedChange ?? ""))
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundStyle(isMarketClosed ? Color.Alpha.neutral : ((gold?.change ?? 0) >= 0 ? Color.Alpha.up : Color.Alpha.down))
                    .padding(.leading, 12) // Align with price text start (Circle 6 + spacing 6)
            }
            .onAppear { isTickerAnimating = true }
            
            Spacer()
            
            // Right Side: Action Stack
            VStack(alignment: .trailing, spacing: 8) {
                Picker("", selection: $viewModel.selectedGranularity) {
                    Text("1H").tag("1h")
                    Text("4H").tag("4h")
                    Text("1D").tag("1d")
                }
                .pickerStyle(.segmented)
                .frame(width: 140)
                .onChange(of: viewModel.selectedGranularity) {
                    Task { await viewModel.fetchPrediction(forceRefresh: false) }
                }
            }
        }
        .padding(.bottom, 4)
    }
    
    private var legendView: some View {
        HStack(spacing: 12) {
            legendItem(name: "实际行情 (北京时间)", color: actualLineColor, isDashed: false)
            legendItem(name: "AI 预测中枢", color: predictionLineColor, isDashed: true)
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(predictionLineColor.opacity(0.12))
                    .frame(width: 16, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(predictionLineColor.opacity(0.3), lineWidth: 0.5))
                Text("置信区间").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.Alpha.up.opacity(0.12))
                    .frame(width: 16, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(Color.Alpha.up.opacity(0.3), lineWidth: 0.5))
                Text("突破区间").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    private func legendItem(name: String, color: Color, isDashed: Bool) -> some View {
        HStack(spacing: 4) {
            if isDashed {
                Path { path in
                    path.move(to: CGPoint(x: 0, y: 4))
                    path.addLine(to: CGPoint(x: 18, y: 4))
                }
                .stroke(color, style: StrokeStyle(lineWidth: 2, dash: [4, 2]))
                .frame(width: 18, height: 8)
            } else {
                Rectangle()
                    .fill(color)
                    .frame(width: 18, height: 2.5)
            }
            Text(name).font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
        }
    }

    private var mainChartSection: some View {
        Group {
            if let data = viewModel.predictionData {
                VStack(spacing: 12) {
                    if data.marketStatus == "CLOSED" {
                        HStack(spacing: 6) {
                            Image(systemName: "moon.stars.fill")
                            Text("market.prediction.mode.opening_anticipation")
                        }
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(predictionLineColor)
                        .padding(.vertical, 6)
                        .padding(.horizontal, 12)
                        .background(predictionLineColor.opacity(0.1))
                        .clipShape(Capsule())
                        .transition(.move(edge: .top).combined(with: .opacity))
                    }
                    
                    Chart {
                        confidenceArea(data)
                        breakoutArea(data)
                        actualLine(data)
                        predictionLine(data)
                        pivotMarkers(data)
                        crosshairMarkers(data)
                    }
                .environment(\.calendar, beijingCalendar)
                .chartXSelection(value: $selectedDate)
                .chartOverlay { proxy in
                    GeometryReader { geometry in
                        Rectangle().fill(.clear).contentShape(Rectangle())
                            .gesture(
                                DragGesture()
                                    .onChanged { value in
                                        if let date: Date = proxy.value(atX: value.location.x) {
                                            selectedDate = date
                                        }
                                    }
                                    .onEnded { _ in
                                        selectedDate = nil
                                    }
                            )
                    }
                }
                .overlay(alignment: Alignment.topLeading) {
                    if let date = selectedDate, let data = viewModel.predictionData {
                        tooltipView(for: date, in: data)
                    }
                }
                .chartXScale(domain: {
                    let granularity = data.granularity ?? "1h"
                    if granularity == "1h" {
                        let calendar = beijingCalendar
                        // 计算当前预测点所属的交易日起点 (06:00)
                        let issuedAt = data.prediction.issuedAt
                        var start = calendar.date(bySettingHour: 6, minute: 0, second: 0, of: issuedAt) ?? issuedAt
                        
                        // 核心修正：如果发布时间在 06:00 之前（如 05:00 收盘时），且我们处于“当前”或“未来”观察视角，
                        // 我们不应该强行跳回昨天的 06:00，否则图表会显示在最右侧并被切断。
                        // 我们让 start 保持在今天的 06:00，minDate 会自动包含 05:00 的起点，使预测从左侧开始。
                        if start > issuedAt && calendar.date(byAdding: .hour, value: -2, to: start)! > issuedAt {
                            start = calendar.date(byAdding: .day, value: -1, to: start)!
                        }
                        
                        // 交易日终点 (次日 05:00)
                        let end = calendar.date(byAdding: .hour, value: 23, to: start)!
                        
                        let historyDates = data.history.map { $0.timestamp }
                        let minDate = historyDates.min() ?? start
                        
                        // 锁定 Domain：从开始节点到 23 小时后的结束节点，确保图表比例一致且不溢出
                        return min(start, minDate)...end
                    }
                    return (data.history.first?.timestamp ?? .distantPast)...(data.prediction.mid.last?.timestamp ?? .distantFuture)
                }())
                .chartYScale(domain: {
                    let allPrices = data.history.map { $0.price } + data.prediction.mid.map { $0.price }
                    if let min = allPrices.min(), let max = allPrices.max(), min < max {
                        return min...max
                    }
                    return 2000...2600
                }())
                .chartXAxis {
                    xAxisContent(data)
                }
                .chartYAxis {
                    AxisMarks(position: .leading) { value in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(Color.gray.opacity(0.1))
                        AxisValueLabel {
                            if let price = value.as(Double.self) {
                                Text("$\(Int(price))")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .frame(height: 300)
                .clipped()
            }
        }
    }

    @AxisContentBuilder
    private func xAxisContent(_ data: GoldPredictionResponse) -> some AxisContent {
        let granularity = data.granularity ?? "1h"
        
        switch granularity {
        case "1h":
            let calendar = beijingCalendar
            let issuedAt = data.prediction.issuedAt
            
            // 核心逻辑同步：确定当前展示周期的起点
            let startNode: Date = {
                let base = calendar.date(bySettingHour: 6, minute: 0, second: 0, of: issuedAt)!
                if base > issuedAt && calendar.date(byAdding: .hour, value: -2, to: base)! > issuedAt {
                    return calendar.date(byAdding: .day, value: -1, to: base)!
                }
                return base
            }()
            
            let midNode = calendar.date(bySettingHour: 17, minute: 30, second: 0, of: startNode)!
            let endNode = calendar.date(byAdding: .hour, value: 23, to: startNode)!
            
            // 1. 核心分界点：预测发布
            AxisMarks(values: [issuedAt]) { _ in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    .foregroundStyle(pivotLineColor)
            }
            
            // 2. 固定交易节点：06:00, 17:30, 05:00
            AxisMarks(values: [startNode, midNode, endNode]) { value in
                if let date = value.as(Date.self) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [2, 2]))
                        .foregroundStyle(Color.gray.opacity(0.15))
                    
                    // 修复：使用 anchor 确保 05:00 贴在右侧，06:00 贴在左侧
                    let labelAnchor: UnitPoint = (date == endNode) ? .topTrailing : (date == startNode ? .topLeading : .top)
                    
                    AxisValueLabel(anchor: labelAnchor) {
                        Text(formatBeijingTime(date))
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                    }
                }
            }
            
        case "1d":
            // --- 1D 逻辑：仅显示首尾两个日期 ---
            let allDates = data.history.map { $0.timestamp } + data.prediction.mid.map { $0.timestamp }
            if let start = allDates.min(), let end = allDates.max() {
                AxisMarks(values: [start, end]) { value in
                    if let date = value.as(Date.self) {
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                            .foregroundStyle(Color.gray.opacity(0.1))
                        
                        let anchor: UnitPoint = (date == start) ? .topLeading : .topTrailing
                        AxisValueLabel(anchor: anchor) {
                            Text(formatBeijingTime(date, useDay: true))
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            
        default:
            // 默认逻辑
            AxisMarks(values: .automatic(desiredCount: 5)) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(Color.gray.opacity(0.1))
                AxisValueLabel {
                    if let date = value.as(Date.self) {
                        Text(formatBeijingTime(date))
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    @ChartContentBuilder
    private func confidenceArea(_ data: GoldPredictionResponse) -> some ChartContent {
        let mid = data.prediction.mid
        let upper = data.prediction.upper
        let lower = data.prediction.lower
        
        ForEach(mid.indices, id: \.self) { i in
            AreaMark(
                x: .value("Time", mid[i].timestamp),
                yStart: .value("Lower", lower[i].price),
                yEnd: .value("Upper", upper[i].price)
            )
            .foregroundStyle(confidenceFillColor)
        }
    }

    @ChartContentBuilder
    private func breakoutArea(_ data: GoldPredictionResponse) -> some ChartContent {
        let mid = data.prediction.mid
        let upper = data.prediction.upper
        let lower = data.prediction.lower
        let predictionStart = data.prediction.issuedAt
        let historyAfter = data.history.filter { $0.timestamp >= predictionStart }
        
        ForEach(historyAfter) { p in
            if let i = mid.firstIndex(where: { abs($0.timestamp.timeIntervalSince(p.timestamp)) < 1800 }) {
                let upVal = upper[i].price
                let loVal = lower[i].price
                
                if p.price > upVal {
                    AreaMark(
                        x: .value("Time", p.timestamp),
                        yStart: .value("Base", upVal),
                        yEnd: .value("Value", p.price)
                    )
                    .foregroundStyle(breakoutFillColor)
                } else if p.price < loVal {
                    AreaMark(
                        x: .value("Time", p.timestamp),
                        yStart: .value("Base", loVal),
                        yEnd: .value("Value", p.price)
                    )
                    .foregroundStyle(breakoutFillColor)
                }
            }
        }
    }

    @ChartContentBuilder
    private func actualLine(_ data: GoldPredictionResponse) -> some ChartContent {
        let sortedHistory = data.history.sorted { $0.timestamp < $1.timestamp }
        let isMarketClosed = data.marketStatus == "CLOSED"
        
        ForEach(sortedHistory) { p in
            LineMark(
                x: .value("Time", p.timestamp),
                y: .value("Price", p.price),
                series: .value("Series", "Actual")
            )
            .interpolationMethod(.monotone)
            .foregroundStyle(isMarketClosed ? actualLineColor.opacity(0.4) : actualLineColor)
            .lineStyle(StrokeStyle(lineWidth: isMarketClosed ? 1.5 : 2.5))
        }
    }

    @ChartContentBuilder
    private func predictionLine(_ data: GoldPredictionResponse) -> some ChartContent {
        let futureMid = data.prediction.mid
            .filter { $0.timestamp >= data.prediction.issuedAt }
            .sorted { $0.timestamp < $1.timestamp }
            
        let connectingPoint = data.history
            .filter { $0.timestamp <= data.prediction.issuedAt }
            .max(by: { $0.timestamp < $1.timestamp })
        
        if let startPoint = connectingPoint {
            LineMark(
                x: .value("Time", startPoint.timestamp),
                y: .value("Price", startPoint.price),
                series: .value("Series", "Prediction")
            )
            .interpolationMethod(.monotone)
            .foregroundStyle(predictionLineColor)
            .lineStyle(StrokeStyle(lineWidth: 2, dash: [6, 4]))
        }
        
        ForEach(futureMid) { p in
            LineMark(
                x: .value("Time", p.timestamp),
                y: .value("Price", p.price),
                series: .value("Series", "Prediction")
            )
            .interpolationMethod(.monotone)
            .foregroundStyle(predictionLineColor)
            .lineStyle(StrokeStyle(lineWidth: 2, dash: [6, 4]))
        }
    }

    @ChartContentBuilder
    private func pivotMarkers(_ data: GoldPredictionResponse) -> some ChartContent {
        let futureMid = data.prediction.mid.filter { $0.timestamp >= data.prediction.issuedAt }
        let connectingPoint = data.history.last(where: { $0.timestamp <= data.prediction.issuedAt })
        
        if let pivotPoint = futureMid.first ?? connectingPoint.map({ GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }) {
            PointMark(
                x: .value("Time", pivotPoint.timestamp),
                y: .value("Price", pivotPoint.price)
            )
            .symbolSize(80)
            .foregroundStyle(predictionLineColor)
        }
        
        RuleMark(x: .value("Pivot", data.prediction.issuedAt))
            .foregroundStyle(pivotLineColor)
            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
        
        if let lastTime = data.prediction.mid.last?.timestamp {
            RectangleMark(
                xStart: .value("Start", data.prediction.issuedAt),
                xEnd: .value("End", lastTime)
            )
            .foregroundStyle(Color(hex: "#888780").opacity(0.06))
        }
    }

    @ChartContentBuilder
    private func crosshairMarkers(_ data: GoldPredictionResponse) -> some ChartContent {
        if let selectedDate {
            let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
            let allPoints = historyPoints + data.prediction.mid
            
            if let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(selectedDate)) < abs($1.timestamp.timeIntervalSince(selectedDate)) }) {
                RuleMark(x: .value("Selected Time", closest.timestamp))
                    .foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                RuleMark(y: .value("Selected Price", closest.price))
                    .foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                PointMark(x: .value("Time", closest.timestamp), y: .value("Price", closest.price))
                    .foregroundStyle(closest.timestamp <= data.prediction.issuedAt ? actualLineColor : predictionLineColor)
                    .symbolSize(60)
            }
        }
    }

    private func tooltipView(for date: Date, in data: GoldPredictionResponse) -> some View {
        let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
        let allPoints = historyPoints + data.prediction.mid
        let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        let actual = data.history.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        let mid = data.prediction.mid.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        let snapDate = closest?.timestamp ?? date
        let diff = snapDate.timeIntervalSince(data.prediction.issuedAt)
        let hours = Int(round(diff / 3600))
        let relativeLabel = hours == 0 ? "发布时刻" : "\(hours > 0 ? "+" : "")\(hours)h"
        
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(formatBeijingTime(snapDate))
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                Text("(\(relativeLabel))")
                    .font(.system(size: 10))
            }
            .foregroundStyle(.secondary)
            
            if let a = actual, abs(a.timestamp.timeIntervalSince(date)) < 7200 {
                Text("实际: $\(a.price.formatted())")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(actualLineColor)
            }
            
            if let m = mid, abs(m.timestamp.timeIntervalSince(date)) < 7200 {
                Text("预测: $\(m.price.formatted())")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(predictionLineColor)
            }
        }
        .padding(8)
        .background(Color.Alpha.surface.opacity(0.95))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator, lineWidth: 1))
        .shadow(color: .black.opacity(0.15), radius: 4)
        .padding(10)
    }
    
    private var metricCardsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(label: "market.prediction.metric.issued_at", value: viewModel.predictedAtText, color: Color.Alpha.textPrimary)
            metricCard(label: "market.prediction.metric.target", value: String(format: "$%.1f", viewModel.targetPrice), color: predictionLineColor)
            metricCard(label: "market.prediction.metric.direction_accuracy", value: String(format: "%.0f%%", viewModel.directionAccuracy), color: Color.Alpha.brand)
            metricCard(label: "market.prediction.metric.historical_accuracy", value: String(format: "%.0f%%", viewModel.historicalAccuracy), color: Color.Alpha.up)
            metricCard(label: "market.prediction.metric.hit_rate", value: String(format: "%.0f%%", viewModel.hitRate), color: Color.Alpha.down)
            metricCard(label: "market.prediction.metric.deviation", value: String(format: "%@$%.1f", viewModel.currentDeviation >= 0 ? "+" : "-", abs(viewModel.currentDeviation)), color: viewModel.currentDeviation >= 0 ? Color.Alpha.down : Color.Alpha.up)
        }
    }
    
    private func metricCard(label: String, value: String, color: Color) -> some View {
        LiquidGlassCard(backgroundColor: Color.primary.opacity(0.03)) {
            VStack(alignment: .leading, spacing: 4) {
                Text(LocalizedStringKey(label))
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.secondary)
                
                Text(value)
                    .font(.system(size: 18, weight: .semibold, design: .monospaced))
                    .foregroundStyle(color)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
