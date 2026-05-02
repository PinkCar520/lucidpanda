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
        formatter.dateFormat = "yyyy-MM-dd"
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
                        .foregroundStyle(Color.Alpha.textPrimary)
                        .contentTransition(.numericText())
                }
                
                if isMarketClosed {
                    Text("market.status.closed_label")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.neutral)
                        .padding(.leading, 12)
                } else {
                    Text(gold?.formattedChange ?? "")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundStyle((gold?.change ?? 0) >= 0 ? Color.Alpha.up : Color.Alpha.down)
                        .padding(.leading, 12)
                }
            }
            .onAppear { isTickerAnimating = true }
            
            Spacer()
            
            // Right Side: Action Stack
            VStack(alignment: .trailing, spacing: 8) {
                Picker("", selection: $viewModel.selectedGranularity) {
                    Text("1H").tag("1h")
                    Text("30M").tag("30m")
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
            legendItem(name: "actual_market_beijing_time", color: actualLineColor, isDashed: false)
            legendItem(name: "ai_prediction_mid", color: predictionLineColor, isDashed: true)
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(predictionLineColor.opacity(0.12))
                    .frame(width: 16, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(predictionLineColor.opacity(0.3), lineWidth: 0.5))
                Text("confidence_interval").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.Alpha.up.opacity(0.12))
                    .frame(width: 16, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(Color.Alpha.up.opacity(0.3), lineWidth: 0.5))
                Text("breakout_interval").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
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
            Text(LocalizedStringKey(name)).font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
        }
    }

    private var mainChartSection: some View {
        Group {
            if let data = viewModel.predictionData {
                VStack(spacing: 12) {
                    let granularity = data.granularity ?? "1h"
                    if data.marketStatus == "CLOSED" && granularity == "1d" {
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
                            let issuedAt = data.prediction.issuedAt
                            
                            // 交易日起点 (06:00)
                            let start = {
                                let base = calendar.date(bySettingHour: 6, minute: 0, second: 0, of: issuedAt)!
                                if base > issuedAt && calendar.date(byAdding: .hour, value: -1, to: base)! > issuedAt {
                                    return calendar.date(byAdding: .day, value: -1, to: base)!
                                }
                                return base
                            }()
                            
                            // 交易日终点 (次日 05:00)
                            let end = calendar.date(byAdding: .hour, value: 23, to: start)!
                            
                            // 锁定 Domain：严格从 06:00 到 05:00，确保 17:30 居中
                            return start...end
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
    }

    @AxisContentBuilder
    private func xAxisContent(_ data: GoldPredictionResponse) -> some AxisContent {
        let granularity = data.granularity ?? "1h"
        
        switch granularity {
        case "1h":
            let calendar = beijingCalendar
            let issuedAt = data.prediction.issuedAt
            
            // 严格同步起点确定逻辑
            let startNode: Date = {
                let base = calendar.date(bySettingHour: 6, minute: 0, second: 0, of: issuedAt)!
                if base > issuedAt && calendar.date(byAdding: .hour, value: -1, to: base)! > issuedAt {
                    return calendar.date(byAdding: .day, value: -1, to: base)!
                }
                return base
            }()
            
            let midNode = calendar.date(bySettingHour: 17, minute: 30, second: 0, of: startNode)!
            let endNode = calendar.date(byAdding: .hour, value: 23, to: startNode)!
            
            // 1. 固定交易节点：06:00, 17:30, 05:00
            AxisMarks(values: [startNode, midNode, endNode]) { value in
                if let date = value.as(Date.self) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [2, 2]))
                        .foregroundStyle(Color.gray.opacity(0.15))
                    
                    let labelAnchor: UnitPoint = {
                        if date == startNode { return .topLeading }
                        if date == endNode { return .topTrailing }
                        return .top
                    }()
                    
                    AxisValueLabel(anchor: labelAnchor) {
                        Text(formatBeijingTime(date))
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                    }
                }
            }
            
            // 2. 预测分界线（仅在非休市显示）
            if data.marketStatus != "CLOSED" {
                AxisMarks(values: [issuedAt]) { _ in
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                        .foregroundStyle(pivotLineColor)
                }
            }
            
        case "30m":
            // --- 30M 逻辑：跨度约 2 天，显示具体时间点 ---
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
            
        case "1d":
            // --- 1D 逻辑：仅显示首尾两个日期 ---
            let allDates = (data.history.map { $0.timestamp } + data.prediction.mid.map { $0.timestamp }).sorted()
            if let start = allDates.first, let end = allDates.last {
                AxisMarks(position: .bottom, values: [start, end]) { value in
                    if let date = value.as(Date.self) {
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                            .foregroundStyle(Color.gray.opacity(0.1))
                        
                        let isStart = abs(date.timeIntervalSince(start)) < 60
                        AxisValueLabel(anchor: isStart ? .topLeading : .topTrailing) {
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
        let granularity = data.granularity ?? "1h"
        let isMarketClosed = data.marketStatus == "CLOSED"
        
        // 1H/4H 模式下，休市期间不显示预测区域
        if (granularity == "1h" || granularity == "4h") && isMarketClosed {
            // Empty
        } else {
            ForEach(mid.indices, id: \.self) { i in
                AreaMark(
                    x: .value("Time", mid[i].timestamp),
                    yStart: .value("Lower", lower[i].price),
                    yEnd: .value("Upper", upper[i].price)
                )
                .foregroundStyle(confidenceFillColor)
            }
        }
    }

    @ChartContentBuilder
    private func breakoutArea(_ data: GoldPredictionResponse) -> some ChartContent {
        let mid = data.prediction.mid
        let upper = data.prediction.upper
        let lower = data.prediction.lower
        let predictionStart = data.prediction.issuedAt
        let historyAfter = data.history.filter { $0.timestamp >= predictionStart }
        let granularity = data.granularity ?? "1h"
        let isMarketClosed = data.marketStatus == "CLOSED"
        
        // 1H/4H 模式下，休市期间不显示
        if (granularity == "1h" || granularity == "4h") && isMarketClosed {
            // Empty
        } else {
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
    }

    @ChartContentBuilder
    private func actualLine(_ data: GoldPredictionResponse) -> some ChartContent {
        let sortedHistory = data.history.sorted { $0.timestamp < $1.timestamp }
        
        ForEach(sortedHistory) { p in
            LineMark(
                x: .value("Time", p.timestamp),
                y: .value("Price", p.price),
                series: .value("Series", "Actual")
            )
            .interpolationMethod(.monotone)
            .foregroundStyle(actualLineColor)
            .lineStyle(StrokeStyle(lineWidth: 2.5))
        }
    }

    @ChartContentBuilder
    private func predictionLine(_ data: GoldPredictionResponse) -> some ChartContent {
        let granularity = data.granularity ?? "1h"
        let isMarketClosed = data.marketStatus == "CLOSED"
        
        // 1H/4H 模式下，休市期间不显示预测线
        if (granularity == "1h" || granularity == "4h") && isMarketClosed {
            // Empty
        } else {
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
    }

    @ChartContentBuilder
    private func pivotMarkers(_ data: GoldPredictionResponse) -> some ChartContent {
        let granularity = data.granularity ?? "1h"
        let isMarketClosed = data.marketStatus == "CLOSED"
        
        if (granularity == "1h" || granularity == "4h") && isMarketClosed {
            // 休市期间不显示预测发布时刻的点和垂直线
        } else {
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
    }

    @ChartContentBuilder
    private func crosshairMarkers(_ data: GoldPredictionResponse) -> some ChartContent {
        if let selectedDate {
            let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
            let allPoints = historyPoints + data.prediction.mid
            let granularity = data.granularity ?? "1h"
            let isMarketClosed = data.marketStatus == "CLOSED"
            
            if let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(selectedDate)) < abs($1.timestamp.timeIntervalSince(selectedDate)) }) {
                let isPredictionPoint = closest.timestamp > data.prediction.issuedAt
                
                // 1H/4H 休市期间，如果长按的是预测点，不显示十字准星
                if (granularity == "1h" || granularity == "4h") && isMarketClosed && isPredictionPoint {
                    // Empty
                } else {
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
    }

    private func tooltipView(for date: Date, in data: GoldPredictionResponse) -> some View {
        let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
        let allPoints = historyPoints + data.prediction.mid
        let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        let actual = data.history.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        let mid = data.prediction.mid.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        let snapDate = closest?.timestamp ?? date
        let diff = snapDate.timeIntervalSince(data.prediction.issuedAt)
        let granularity = data.granularity ?? "1h"
        
        let timeUnit: Double = granularity == "1d" ? 86400 : 3600
        let offsets = Int(round(diff / timeUnit))
        let unitLabel = granularity == "1d" ? "d" : "h"
        let relativeLabel = offsets == 0 ? String(localized: "market.prediction.label.pivot") : "\(offsets > 0 ? "+" : "")\(offsets)\(unitLabel)"
        
        return VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(formatBeijingTime(snapDate, useDay: granularity == "1d"))
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                Text("(\(relativeLabel))")
                    .font(.system(size: 10))
            }
            .foregroundStyle(Color.Alpha.textSecondary)
            
            if let a = actual, abs(a.timestamp.timeIntervalSince(date)) < 7200 {
                HStack(spacing: 4) {
                    Text("market.prediction.label.history")
                    Text("$\(a.price.formatted())")
                }
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(actualLineColor)
            }
            
            if let m = mid, abs(m.timestamp.timeIntervalSince(date)) < 7200 {
                HStack(spacing: 4) {
                    Text("market.prediction.label.tracking")
                    Text("$\(m.price.formatted())")
                }
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(predictionLineColor)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .fill(Color.Alpha.surface)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .stroke(colorScheme == .dark ? Color(hex: "#2D2D2D") : Color.Alpha.separator, lineWidth: 1)
        )
        .padding(10)
    }
    
    private var metricCardsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(label: "market.prediction.metric.issued_at", value: viewModel.predictedAtText, color: Color.Alpha.textPrimary)
            metricCard(label: "market.prediction.metric.target", value: String(format: "$%.1f", viewModel.targetPrice), color: predictionLineColor)
            
            metricCard(label: "market.prediction.metric.direction_accuracy", 
                       value: viewModel.directionAccuracy.map { String(format: "%.0f%%", $0) } ?? "--", 
                       color: Color.Alpha.brand)
            
            metricCard(label: "market.prediction.metric.historical_accuracy", 
                       value: viewModel.historicalAccuracy.map { String(format: "%.0f%%", $0) } ?? "--", 
                       color: Color.Alpha.up)
            
            metricCard(label: "market.prediction.metric.hit_rate", 
                       value: viewModel.hitRate.map { String(format: "%.0f%%", $0) } ?? "--", 
                       color: Color.Alpha.down)
            
            let devValue: String = {
                if let dev = viewModel.currentDeviation {
                    return String(format: "%@$%.1f", dev >= 0 ? "+" : "-", abs(dev))
                }
                return "--"
            }()
            let devColor: Color = {
                if let dev = viewModel.currentDeviation {
                    return dev >= 0 ? Color.Alpha.down : Color.Alpha.up
                }
                return Color.Alpha.textSecondary
            }()
            metricCard(label: "market.prediction.metric.deviation", value: devValue, color: devColor)
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
