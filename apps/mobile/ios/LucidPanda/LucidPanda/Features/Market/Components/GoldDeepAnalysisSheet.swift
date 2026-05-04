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
    @State private var isLandscape = false
    
    // 🎨 回归 App 语义化主题色
    private let actualUpColor = Color.Alpha.up
    private let actualDownColor = Color.Alpha.down
    private let predictionLineColor = Color(hex: "#007AFF")
    private let confidenceFillColor = Color(hex: "#007AFF").opacity(0.08)
    private let breakoutFillColor = Color.Alpha.up.opacity(0.12)
    private let pivotLineColor = Color.Alpha.taupe.opacity(0.4)

    private var beijingCalendar: Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Asia/Shanghai")!
        return cal
    }

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.isLoading && viewModel.predictionData == nil {
                    ProgressView().tint(Color.Alpha.brand)
                } else {
                    ScrollView {
                        VStack(spacing: 24) {
                            topControlBar
                            legendView
                            
                            if let data = viewModel.predictionData {
                                ProfessionalGoldChart(
                                    data: data,
                                    selectedDate: $selectedDate,
                                    beijingCalendar: beijingCalendar,
                                    upColor: actualUpColor,
                                    downColor: actualDownColor,
                                    predictionLineColor: predictionLineColor,
                                    confidenceFillColor: confidenceFillColor,
                                    breakoutFillColor: breakoutFillColor,
                                    pivotLineColor: pivotLineColor
                                )
                                .frame(height: 300)
                            }
                            
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
            .task { await viewModel.fetchInitialData() }
            .fullScreenCover(isPresented: $isLandscape) {
                LandscapeChartView(
                    viewModel: viewModel,
                    isPresented: $isLandscape,
                    beijingCalendar: beijingCalendar,
                    upColor: actualUpColor,
                    downColor: actualDownColor,
                    predictionLineColor: predictionLineColor,
                    confidenceFillColor: confidenceFillColor,
                    breakoutFillColor: breakoutFillColor,
                    pivotLineColor: pivotLineColor
                )
            }
        }
    }
    
    // MARK: - UI Components

    private var topControlBar: some View {
        HStack(alignment: .bottom) {
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
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.textPrimary)
                }
                
                Text(isMarketClosed ? String(localized: "market.status.closed_label") : (gold?.formattedChange ?? ""))
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundStyle(isMarketClosed ? Color.Alpha.neutral : ((gold?.change ?? 0) >= 0 ? actualUpColor : actualDownColor))
                    .padding(.leading, 12)
            }
            .onAppear { isTickerAnimating = true }
            
            Spacer()
            
            HStack(spacing: 10) {
                Button { isLandscape = true } label: {
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(Color.Alpha.textSecondary)
                        .padding(8)
                        .background(Color.Alpha.separator.opacity(0.3))
                        .clipShape(Circle())
                }
                
                Picker("", selection: $viewModel.selectedGranularity) {
                    Text("分时").tag("1m")
                    Text("15M").tag("15m")
                    Text("1D").tag("1d")
                }
                .pickerStyle(.segmented)
                .frame(width: 190)
                .onChange(of: viewModel.selectedGranularity) {
                    Task { await viewModel.fetchPrediction(forceRefresh: false) }
                }
            }
        }
        .padding(.bottom, 4)
    }
    
    private var legendView: some View {
        HStack(spacing: 16) {
            HStack(spacing: 4) {
                // 预测中枢虚线图例
                Path { path in
                    path.move(to: CGPoint(x: 0, y: 4))
                    path.addLine(to: CGPoint(x: 14, y: 4))
                }
                .stroke(predictionLineColor, style: StrokeStyle(lineWidth: 1.5, dash: [3, 2]))
                .frame(width: 14, height: 8)
                
                Text("ai_prediction_mid").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 1).fill(predictionLineColor.opacity(0.15)).frame(width: 12, height: 8)
                Text("confidence_interval").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 1).fill(breakoutFillColor).frame(width: 12, height: 8)
                Text("breakout_interval").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var metricCardsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(label: "market.prediction.metric.issued_at", value: viewModel.predictedAtText, color: Color.Alpha.textPrimary)
            metricCard(label: "market.prediction.metric.target", value: String(format: "$%.1f", viewModel.targetPrice), color: predictionLineColor)
            metricCard(label: "market.prediction.metric.direction_accuracy", value: viewModel.directionAccuracy.map { String(format: "%.0f%%", $0) } ?? "--", color: Color.Alpha.brand)
            metricCard(label: "market.prediction.metric.historical_accuracy", value: viewModel.historicalAccuracy.map { String(format: "%.0f%%", $0) } ?? "--", color: actualUpColor)
            metricCard(label: "market.prediction.metric.hit_rate", value: viewModel.hitRate.map { String(format: "%.0f%%", $0) } ?? "--", color: actualDownColor)
            metricCard(label: "market.prediction.metric.deviation", value: String(format: "%@$%.1f", (viewModel.currentDeviation ?? 0) >= 0 ? "+" : "-", abs(viewModel.currentDeviation ?? 0)), color: (viewModel.currentDeviation ?? 0) >= 0 ? actualDownColor : actualUpColor)
        }
    }
    
    private func metricCard(label: String, value: String, color: Color) -> some View {
        LiquidGlassCard(backgroundColor: Color.primary.opacity(0.03)) {
            VStack(alignment: .leading, spacing: 4) {
                Text(LocalizedStringKey(label)).font(.system(size: 12, weight: .medium)).foregroundStyle(.secondary)
                Text(value).font(.system(size: 18, weight: .semibold, design: .monospaced)).foregroundStyle(color)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

// MARK: - Shared Tooltip Component

struct ProfessionalChartTooltip: View {
    let date: Date
    let data: GoldPredictionResponse
    let upColor: Color
    let downColor: Color
    let predictionLineColor: Color
    
    private static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.timeZone = TimeZone(identifier: "Asia/Shanghai")
        f.dateFormat = "HH:mm"
        return f
    }()

    var body: some View {
        let history = data.history
        let predictions = data.prediction.mid
        let allPoints = history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) } + predictions
        
        let closest = allPoints.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        let snapDate = closest?.timestamp ?? date
        let actual = history.first(where: { abs($0.timestamp.timeIntervalSince(snapDate)) < 1 })
        let isPrediction = snapDate >= data.prediction.issuedAt
        
        VStack(alignment: .leading, spacing: 6) {
            Text(Self.timeFormatter.string(from: snapDate))
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(Color.Alpha.textSecondary)
            
            if let a = actual {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 4) {
                        Text("market.prediction.label.history")
                        Text("$\(a.price.formatted())")
                    }
                    if let o = a.open {
                        Text("O:$\(o.formatted()) H:$\(a.high?.formatted() ?? "") L:$\(a.low?.formatted() ?? "")")
                            .font(.system(size: 8))
                            .foregroundStyle(Color.Alpha.textSecondary)
                    }
                }
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundStyle({
                    let open = a.open ?? a.price
                    if a.price > open { return upColor }
                    if a.price < open { return downColor }
                    return Color.Alpha.neutral
                }())
            }
            
            if isPrediction, let p = predictions.first(where: { abs($0.timestamp.timeIntervalSince(snapDate)) < 1 }) {
                HStack(spacing: 4) {
                    Text("market.prediction.label.tracking")
                    Text("$\(p.price.formatted())")
                }
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundStyle(predictionLineColor)
            }
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.Alpha.surface))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.Alpha.separator, lineWidth: 0.5))
    }
}

// MARK: - Professional Chart Rendering Engine

struct ProfessionalGoldChart: View {
    let data: GoldPredictionResponse
    @Binding var selectedDate: Date?
    let beijingCalendar: Calendar
    let upColor: Color
    let downColor: Color
    let predictionLineColor: Color
    let confidenceFillColor: Color
    let breakoutFillColor: Color
    let pivotLineColor: Color

    // 计算索引映射，消除停盘空洞
    private var allPoints: [Date] {
        let historyTs = data.history.map { $0.timestamp }
        let predictionTs = data.prediction.mid.map { $0.timestamp }
        // 确保时间连续且去重
        return (historyTs + predictionTs).sorted()
    }

    private func index(for date: Date) -> Int? {
        allPoints.firstIndex { abs($0.timeIntervalSince(date)) < 1 }
    }

    private static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.timeZone = TimeZone(identifier: "Asia/Shanghai")
        f.dateFormat = "HH:mm"
        return f
    }()

    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.timeZone = TimeZone(identifier: "Asia/Shanghai")
        f.dateFormat = "MM-dd"
        return f
    }()
    
    private static let priceFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.minimumFractionDigits = 2
        f.maximumFractionDigits = 2
        return f
    }()

    var body: some View {
        let points = allPoints
        let historyCount = data.history.count
        
        Chart {
            // 2. Prediction Confidence Area (Blue - Future ONLY)
            let lastHistoryTs = data.history.last?.timestamp ?? data.prediction.issuedAt
            ForEach(data.prediction.mid.indices, id: \.self) { i in
                let p = data.prediction.mid[i]
                if p.timestamp > lastHistoryTs, let idx = index(for: p.timestamp) {
                    AreaMark(
                        x: .value("T", idx),
                        yStart: .value("L", data.prediction.lower[i].price),
                        yEnd: .value("U", data.prediction.upper[i].price)
                    )
                    .foregroundStyle(confidenceFillColor)
                }
            }
            
            // 3. Breakout Area (Gold - Overlap with History ONLY)
            ForEach(data.history) { p in
                if p.timestamp >= data.prediction.issuedAt, let idx = index(for: p.timestamp) {
                    if let i = data.prediction.mid.firstIndex(where: { abs($0.timestamp.timeIntervalSince(p.timestamp)) < 1800 }) {
                        let up = data.prediction.upper[i].price
                        let lo = data.prediction.lower[i].price
                        if p.price > up { 
                            AreaMark(x: .value("T", idx), yStart: .value("B", up), yEnd: .value("V", p.price)).foregroundStyle(breakoutFillColor) 
                        } else if p.price < lo { 
                            AreaMark(x: .value("T", idx), yStart: .value("B", lo), yEnd: .value("V", p.price)).foregroundStyle(breakoutFillColor) 
                        }
                    }
                }
            }
            
            // 4. Main History
            if data.granularity == "1m" {
                let preClose = data.previousClose ?? (data.history.first?.price ?? 0)
                ForEach(data.history.indices, id: \.self) { i in
                    let p = data.history[i]
                    if let idx = index(for: p.timestamp) {
                        let compare = i > 0 ? data.history[i - 1].price : preClose
                        let isUp = p.price >= compare
                        LineMark(
                            x: .value("T", idx),
                            y: .value("P", p.price),
                            series: .value("Series", isUp ? "ActualUp" : "ActualDown")
                        )
                        .foregroundStyle(isUp ? upColor : downColor)
                        .lineStyle(StrokeStyle(lineWidth: 2))
                    }
                }
            } else {
                ForEach(data.history) { p in
                    if let open = p.open, let high = p.high, let low = p.low, let idx = index(for: p.timestamp) {
                        let candleColor: Color = {
                            if p.price > open { return upColor }
                            if p.price < open { return downColor }
                            return Color.Alpha.neutral
                        }()
                        RectangleMark(x: .value("T", idx), yStart: .value("L", low), yEnd: .value("H", high), width: 1).foregroundStyle(candleColor)
                        RectangleMark(x: .value("T", idx), yStart: .value("O", min(open, p.price)), yEnd: .value("C", max(open, p.price)), width: .fixed(8)).foregroundStyle(candleColor)
                    }
                }
            }
            
            // 5. AI Prediction Curve
            ForEach(data.prediction.mid) { p in
                if let idx = index(for: p.timestamp) {
                    LineMark(
                        x: .value("T", idx),
                        y: .value("P", p.price),
                        series: .value("Series", "Prediction")
                    )
                    .foregroundStyle(predictionLineColor)
                    .lineStyle(StrokeStyle(lineWidth: 2, dash: [5, 5]))
                }
            }

            // 6. Pivot Marker
            if let pivotIdx = index(for: data.prediction.issuedAt) {
                RuleMark(x: .value("Pivot", pivotIdx))
                    .foregroundStyle(pivotLineColor)
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
            }

            // 7. Crosshair (Index based)
            if let date = selectedDate {
                let all = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) } + data.prediction.mid
                if let c = all.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) }),
                   let idx = index(for: c.timestamp) {
                    RuleMark(x: .value("T", idx)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    RuleMark(y: .value("P", c.price)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    PointMark(x: .value("T", idx), y: .value("P", c.price))
                        .foregroundStyle({
                            if c.timestamp > data.history.last?.timestamp ?? data.prediction.issuedAt {
                                return predictionLineColor
                            } else {
                                guard let hIdx = data.history.firstIndex(where: { abs($0.timestamp.timeIntervalSince(c.timestamp)) < 1 }) else {
                                    return upColor
                                }
                                let current = data.history[hIdx].price
                                let compare = hIdx > 0 ? data.history[hIdx - 1].price : (data.previousClose ?? current)
                                return current >= compare ? upColor : downColor
                            }
                        }())
                        .symbolSize(60)
                }
            }
        }
        .chartXScale(domain: 0...(points.count - 1))
        .chartYScale(domain: yDomain)
        .chartXAxis {
            let granularity = data.granularity ?? "1m"
            if granularity == "1m" {
                // 分时依然使用简单的三点标注，直接映射索引
                let indices = [0, points.count / 2, points.count - 1]
                AxisMarks(values: indices) { value in
                    if let idx = value.as(Int.self), idx < points.count {
                        let date = points[idx]
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                        AxisValueLabel(anchor: idx == 0 ? .topLeading : (idx == points.count - 1 ? .topTrailing : .top)) {
                            Text(Self.timeFormatter.string(from: date))
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                        }
                    }
                }
            } else {
                // 15m/4h/1d: 根据时间逻辑动态生成刻度索引
                let labelIndices = calculateLabelIndices(for: points, granularity: granularity)
                AxisMarks(values: labelIndices) { value in
                    if let idx = value.as(Int.self), idx < points.count {
                        let date = points[idx]
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                        AxisValueLabel {
                            let hour = beijingCalendar.component(.hour, from: date)
                            if granularity == "15m" {
                                if hour == 0 {
                                    Text(Self.dayFormatter.string(from: date)).font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Color.Alpha.textPrimary)
                                } else {
                                    Text(Self.timeFormatter.string(from: date)).font(.system(size: 10, design: .monospaced)).foregroundStyle(.secondary)
                                }
                            } else {
                                // 1D 只显示日期
                                Text(Self.dayFormatter.string(from: date))
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .stride(by: 10.0)) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
            }
            if let preClose = data.previousClose ?? data.history.first?.price {
                AxisMarks(position: .leading, values: [preClose]) { _ in
                    AxisValueLabel {
                        Text(Self.formattedPrice(preClose)).font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Color.Alpha.brand)
                    }
                }
            }
        }
        .chartOverlay { proxy in
            GeometryReader { geometry in
                Rectangle().fill(.clear).contentShape(Rectangle())
                    .gesture(DragGesture().onChanged { value in
                        if let idx: Int = proxy.value(atX: value.location.x), idx >= 0 && idx < points.count {
                            selectedDate = points[idx]
                        }
                    }.onEnded { _ in selectedDate = nil })
            }
        }
        .overlay(alignment: .topLeading) {
            if let date = selectedDate {
                ProfessionalChartTooltip(date: date, data: data, upColor: upColor, downColor: downColor, predictionLineColor: predictionLineColor)
                    .padding(10)
            }
        }
        .clipped()
    }

    private func calculateLabelIndices(for points: [Date], granularity: String) -> [Int] {
        var indices: [Int] = []
        var lastLabelDate: Date?
        
        for (i, date) in points.enumerated() {
            let hour = beijingCalendar.component(.hour, from: date)
            let minute = beijingCalendar.component(.minute, from: date)
            
            var shouldLabel = false
            if granularity == "15m" {
                // 每 12 小时 (00:00, 12:00) 且分钟为 0
                if minute == 0 && (hour == 0 || hour == 12) {
                    shouldLabel = true
                }
            } else if granularity == "1d" {
                // 每周一
                if beijingCalendar.component(.weekday, from: date) == 2 { shouldLabel = true }
            }
            
            if shouldLabel {
                if let last = lastLabelDate {
                    // 避免刻度过密 (至少间隔 4 小时以上的数据点)
                    if date.timeIntervalSince(last) > 3600 * 4 {
                        indices.append(i)
                        lastLabelDate = date
                    }
                } else {
                    indices.append(i)
                    lastLabelDate = date
                }
            }
        }
        
        // 确保至少有首尾标注（如果没匹配到逻辑）
        if indices.isEmpty && !points.isEmpty {
            indices = [0, points.count - 1]
        }
        
        return indices
    }

    private var yDomain: ClosedRange<Double> {
        let historyPrices = data.history.flatMap { [$0.price, $0.open ?? $0.price, $0.high ?? $0.price, $0.low ?? $0.price] }
        let predictionPrices = data.prediction.mid.map { $0.price }
        let allPrices = (historyPrices + predictionPrices).filter { $0 > 0 }
        
        guard let min = allPrices.min(), let max = allPrices.max(), min < max else { return 4500...4700 }
        
        let range = max - min
        let padding = range * 0.05
        return (min - padding)...(max + padding)
    }
    
    private static func formattedPrice(_ value: Double) -> String {
        priceFormatter.string(from: NSNumber(value: value)) ?? String(format: "%.2f", value)
    }
}

// MARK: - Professional Landscape Viewer

struct LandscapeChartView: View {
    let viewModel: GoldDeepAnalysisViewModel
    @Binding var isPresented: Bool
    @State private var selectedDate: Date?
    let beijingCalendar: Calendar
    let upColor: Color
    let downColor: Color
    let predictionLineColor: Color
    let confidenceFillColor: Color
    let breakoutFillColor: Color
    let pivotLineColor: Color

    var body: some View {
        GeometryReader { geo in
            ZStack {
                if let data = viewModel.predictionData {
                    VStack(spacing: 0) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("gold.prediction.title").font(.headline).foregroundStyle(Color.Alpha.textPrimary)
                                Text(data.granularity?.uppercased() ?? "").font(.system(size: 10, weight: .bold)).foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .padding(.horizontal, 24)
                        .padding(.top, 16)
                        
                        ProfessionalGoldChart(
                            data: data,
                            selectedDate: $selectedDate,
                            beijingCalendar: beijingCalendar,
                            upColor: upColor,
                            downColor: downColor,
                            predictionLineColor: predictionLineColor,
                            confidenceFillColor: confidenceFillColor,
                            breakoutFillColor: breakoutFillColor,
                            pivotLineColor: pivotLineColor
                        )
                        .padding(.horizontal, 20)
                        .padding(.bottom, 20)
                    }
                }
            }
            .rotationEffect(.degrees(90))
            .frame(width: geo.size.height, height: geo.size.width)
            .position(x: geo.size.width/2, y: geo.size.height/2)
            .safeAreaInset(edge: .trailing) {
                VStack {
                    Spacer()
                    Button { isPresented = false } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                            .padding(8)
                            .background(Color.Alpha.separator.opacity(0.3))
                            .clipShape(Circle())
                    }
                }
                .padding(.trailing, 10)
                .padding(.bottom, 12)
            }
        }
    }
}
