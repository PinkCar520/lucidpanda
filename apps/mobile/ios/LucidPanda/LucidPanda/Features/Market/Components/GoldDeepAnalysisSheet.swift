import SwiftUI
import AlphaDesign
import AlphaData
import Charts

public struct GoldDeepAnalysisSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) var colorScheme
    @State private var viewModel = GoldDeepAnalysisViewModel()
    @State private var isTickerAnimating = false
    @State private var selectedDate: Date?
    
    // 🎨 回归 App 语义化主题色
    private let actualLineColor = Color.Alpha.up
    private let predictionLineColor = Color(hex: "#007AFF")
    private let breakoutFillColor = Color.Alpha.up.opacity(0.12)
    private let confidenceFillColor = Color(hex: "#007AFF").opacity(0.08)
    private let pivotLineColor = Color.Alpha.taupe.opacity(0.4)

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()
                
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
                            
                            // 4. Timeline Markers
                            timelineLabels
                            
                            // 5. Metric Cards
                            metricCardsGrid
                            
                            Spacer(minLength: 40)
                        }
                        .padding()
                    }
                    .refreshable {
                        await viewModel.fetchPrediction()
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
        VStack(spacing: 12) {
            HStack {
                HStack(spacing: 8) {
                    Circle()
                        .fill(Color.Alpha.brand)
                        .frame(width: 7, height: 7)
                        .opacity(isTickerAnimating ? 1 : 0.4)
                        .scaleEffect(isTickerAnimating ? 1.0 : 0.7)
                        .animation(.easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: isTickerAnimating)
                        .onAppear { isTickerAnimating = true }
                    
                    Text(viewModel.currentPriceText)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(Color.Alpha.textPrimary)
                    
                    Text(viewModel.priceChangeText)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(viewModel.isPriceUp ? Color.Alpha.up : Color.Alpha.down)
                }
                
                Spacer()
                
                Button {
                    Task { await viewModel.fetchPrediction(forceRefresh: true) }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "sparkles")
                        Text("AI 预测")
                    }
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color.Alpha.brand)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.Alpha.brand.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                .disabled(viewModel.isLoading)
                
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
    }
    
    private var legendView: some View {
        HStack(spacing: 12) {
            legendItem(name: "实际行情 (实时)", color: actualLineColor, isDashed: false)
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
                Chart {
                    confidenceArea(data)
                    breakoutArea(data)
                    actualLine(data)
                    predictionLine(data)
                    pivotMarkers(data)
                    crosshairMarkers(data)
                }
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
                .chartYScale(domain: {
                    let allPrices = data.history.map { $0.price } + data.prediction.mid.map { $0.price }
                    if let min = allPrices.min(), let max = allPrices.max(), min < max {
                        return min...max
                    }
                    return 2000...2600 // 兜底黄金价格区间
                }())
                .chartXAxis {
                    // 1. 核心分界点：预测发布 (0)
                    AxisMarks(values: [data.prediction.issuedAt]) { _ in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                            .foregroundStyle(pivotLineColor)
                        AxisValueLabel(anchor: .top) {
                            Text("0")
                                .font(.system(size: 10))
                                .foregroundStyle(.secondary)
                        }
                    }
                    
                    // 2. 显式相对刻度：-12, -10, -8, -6, -4, -2, +2, +4, +6, +8
                    let relativeOffsets = [-12, -10, -8, -6, -4, -2, 2, 4, 6, 8]
                    let markDates = relativeOffsets.map { data.prediction.issuedAt.addingTimeInterval(Double($0 * 3600)) }
                    
                    AxisMarks(values: markDates) { value in
                        if let date = value.as(Date.self) {
                            let diff = date.timeIntervalSince(data.prediction.issuedAt)
                            let hours = Int(round(diff / 3600))
                            
                            AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                                .foregroundStyle(Color.gray.opacity(0.1))
                            
                            AxisValueLabel {
                                Text("\(hours > 0 ? "+" : "")\(hours)")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
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
            // 1. 统一类型后寻找磁吸点
            let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
            let allPoints = historyPoints + data.prediction.mid
            
            if let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(selectedDate)) < abs($1.timestamp.timeIntervalSince(selectedDate)) }) {
                // 垂直引导虚线
                RuleMark(x: .value("Selected Time", closest.timestamp))
                    .foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                
                // 水平引导虚线
                RuleMark(y: .value("Selected Price", closest.price))
                    .foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                
                // 交汇处的亮点
                PointMark(x: .value("Time", closest.timestamp), y: .value("Price", closest.price))
                    .foregroundStyle(closest.timestamp <= data.prediction.issuedAt ? actualLineColor : predictionLineColor)
                    .symbolSize(60)
            }
        }
    }

    private func tooltipView(for date: Date, in data: GoldPredictionResponse) -> some View {
        // 核心修正：找到物理上最接近的真实数据点
        let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
        let allPoints = historyPoints + data.prediction.mid
        let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        let actual = data.history.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        let mid = data.prediction.mid.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        // 使用吸附后的点的时间，确保用户看到的时间和价格是完全匹配的
        let snapDate = closest?.timestamp ?? date
        let diff = snapDate.timeIntervalSince(data.prediction.issuedAt)
        let hours = Int(round(diff / 3600))
        let relativeLabel = hours == 0 ? "发布时刻" : "\(hours > 0 ? "+" : "")\(hours)h"
        
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(snapDate, format: .dateTime.hour().minute())
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
    
    private var timelineLabels: some View {
        HStack {
            Text(LocalizedStringKey("market.prediction.label.history"))
            Spacer()
            Text("← 预测发布时间点")
            Spacer()
            Text(LocalizedStringKey("market.prediction.label.tracking"))
        }
        .font(.system(size: 11))
        .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))
    }
    
    private var metricCardsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            // Row 1
            metricCard(label: "market.prediction.metric.issued_at", value: viewModel.predictedAtText, color: Color.Alpha.textPrimary)
            metricCard(label: "market.prediction.metric.target", value: String(format: "$%.1f", viewModel.targetPrice), color: predictionLineColor)
            
            // Row 2
            metricCard(label: "market.prediction.metric.direction_accuracy", value: String(format: "%.0f%%", viewModel.directionAccuracy), color: Color.Alpha.brand)
            metricCard(label: "market.prediction.metric.historical_accuracy", value: String(format: "%.0f%%", viewModel.historicalAccuracy), color: Color.Alpha.up)
            
            // Row 3
            metricCard(label: "market.prediction.metric.hit_rate", value: String(format: "%.0f%%", viewModel.hitRate), color: Color.Alpha.down)
            metricCard(label: "market.prediction.metric.deviation", value: String(format: "%@$%.1f", viewModel.currentDeviation >= 0 ? "+" : "-", abs(viewModel.currentDeviation)), color: viewModel.currentDeviation >= 0 ? Color.Alpha.down : Color.Alpha.up)
        }
    }
    
    private func metricCard(label: String, value: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(LocalizedStringKey(label))
                .font(.system(size: 11))
                .foregroundStyle(Color.Alpha.textSecondary)
            
            Text(value)
                .font(.system(size: 20, weight: .bold, design: .monospaced))
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color.Alpha.surfaceContainerLow)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
