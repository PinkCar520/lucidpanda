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
                    Text("4H").tag("4h")
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
        HStack(spacing: 12) {
            HStack(spacing: 4) {
                // 恢复实际行情标签：改为上下两个横条
                VStack(spacing: 1.5) {
                    Rectangle().fill(actualUpColor).frame(width: 12, height: 1.5)
                    Rectangle().fill(actualDownColor).frame(width: 12, height: 1.5)
                }
                Text("actual_market_beijing_time").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            HStack(spacing: 4) {
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
                .foregroundStyle(a.price >= (a.open ?? a.price) ? upColor : downColor)
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
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.Alpha.surface).shadow(radius: 2))
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

    var body: some View {
        Chart {
            // 1. Prediction Zone Background (Light Grey Stripe)
            if let lastTime = data.prediction.mid.last?.timestamp {
                RectangleMark(
                    xStart: .value("Start", data.prediction.issuedAt),
                    xEnd: .value("End", lastTime)
                )
                .foregroundStyle(Color(hex: "#888780").opacity(0.06))
            }
            
            // 2. Prediction Confidence Area (Blue - Future ONLY)
            // ⚠️ 修复重叠：强制仅在历史数据点之后显示蓝色背景
            let lastHistoryTs = data.history.last?.timestamp ?? data.prediction.issuedAt
            let futureMid = data.prediction.mid.filter { $0.timestamp > lastHistoryTs }
            let futureUpper = data.prediction.upper.filter { $0.timestamp > lastHistoryTs }
            let futureLower = data.prediction.lower.filter { $0.timestamp > lastHistoryTs }
            
            ForEach(futureMid.indices, id: \.self) { i in
                AreaMark(
                    x: .value("T", futureMid[i].timestamp),
                    yStart: .value("L", futureLower[i].price),
                    yEnd: .value("U", futureUpper[i].price)
                )
                .foregroundStyle(confidenceFillColor)
            }
            
            // 3. Breakout Area (Gold - Overlap with History ONLY)
            let historyAfter = data.history.filter { $0.timestamp >= data.prediction.issuedAt }
            ForEach(historyAfter) { p in
                if let i = data.prediction.mid.firstIndex(where: { abs($0.timestamp.timeIntervalSince(p.timestamp)) < 1800 }) {
                    let up = data.prediction.upper[i].price
                    let lo = data.prediction.lower[i].price
                    if p.price > up { 
                        AreaMark(x: .value("T", p.timestamp), yStart: .value("B", up), yEnd: .value("V", p.price)).foregroundStyle(breakoutFillColor) 
                    } else if p.price < lo { 
                        AreaMark(x: .value("T", p.timestamp), yStart: .value("B", lo), yEnd: .value("V", p.price)).foregroundStyle(breakoutFillColor) 
                    }
                }
            }
            
            // 4. Main History (Intraday Line vs Candlesticks)
            if data.granularity == "1m" {
                let preClose = data.previousClose ?? (data.history.first?.price ?? 0)
                
                // History Area Fill (Dynamic Red/Green based on baseline)
                ForEach(data.history) { p in
                    let isUp = p.price >= preClose
                    AreaMark(
                        x: .value("T", p.timestamp),
                        yStart: .value("B", preClose),
                        yEnd: .value("P", p.price)
                    )
                    .foregroundStyle(
                        LinearGradient(
                            colors: [(isUp ? upColor : downColor).opacity(0.12), .clear], 
                            startPoint: .top, 
                            endPoint: .bottom
                        )
                    )
                }
                
                // Line Series (Split into UP and DOWN to force color segments)
                ForEach(data.history) { p in
                    LineMark(
                        x: .value("T", p.timestamp),
                        y: .value("P", p.price),
                        series: .value("Series", "Actual")
                    )
                    .foregroundStyle(p.price >= preClose ? upColor : downColor)
                    .lineStyle(StrokeStyle(lineWidth: 2))
                }
                
                // PreClose Baseline
                RuleMark(y: .value("Baseline", preClose))
                    .foregroundStyle(.gray.opacity(0.3))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
            } else {
                ForEach(data.history) { p in
                    if let open = p.open, let high = p.high, let low = p.low {
                        let candleColor = p.price >= open ? upColor : downColor
                        RectangleMark(x: .value("T", p.timestamp), yStart: .value("L", low), yEnd: .value("H", high), width: 1).foregroundStyle(candleColor)
                        RectangleMark(x: .value("T", p.timestamp), yStart: .value("O", min(open, p.price)), yEnd: .value("C", max(open, p.price)), width: .fixed(8)).foregroundStyle(candleColor)
                    }
                }
            }
            
            // 5. AI Prediction Curve (Dashed Line Series)
            ForEach(data.prediction.mid) { p in
                LineMark(
                    x: .value("T", p.timestamp),
                    y: .value("P", p.price),
                    series: .value("Series", "Prediction")
                )
                .foregroundStyle(predictionLineColor)
                .lineStyle(StrokeStyle(lineWidth: 2, dash: [5, 5]))
            }

            // 6. Pivot Marker (IssuedAt Dot & Vertical Line)
            RuleMark(x: .value("Pivot", data.prediction.issuedAt))
                .foregroundStyle(pivotLineColor)
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))

            if let pivotPoint = data.history.last(where: { $0.timestamp <= data.prediction.issuedAt }) ?? 
                data.prediction.mid.first.map({ GoldTrendPoint(timestamp: $0.timestamp, price: $0.price, isForecast: true) }) {
                PointMark(
                    x: .value("T", pivotPoint.timestamp),
                    y: .value("P", pivotPoint.price)
                )
                .symbolSize(60)
                .foregroundStyle(predictionLineColor)
            }

            
            // 7. Crosshair
            if let date = selectedDate {
                let all = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) } + data.prediction.mid
                if let c = all.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) }) {
                    RuleMark(x: .value("T", c.timestamp)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    RuleMark(y: .value("P", c.price)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                    PointMark(x: .value("T", c.timestamp), y: .value("P", c.price))
                        .foregroundStyle({
                            if c.timestamp > data.history.last?.timestamp ?? data.prediction.issuedAt {
                                return predictionLineColor
                            } else {
                                let histPoint = data.history.first(where: { abs($0.timestamp.timeIntervalSince(c.timestamp)) < 1 })
                                return (histPoint?.price ?? 0) >= (histPoint?.open ?? histPoint?.price ?? 0) ? upColor : downColor
                            }
                        }())
                        .symbolSize(60)
                }
            }
        }
        .chartXScale(domain: xDomain)
        .chartYScale(domain: yDomain)
        .chartXAxis { xAxisContent }
        .chartYAxis {
            AxisMarks(position: .leading) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                if let price = value.as(Double.self) {
                    AxisValueLabel { Text("$\(Int(price))").font(.system(size: 10, design: .monospaced)).foregroundStyle(.secondary) }
                }
            }
        }
        .chartOverlay { proxy in
            GeometryReader { geometry in
                Rectangle().fill(.clear).contentShape(Rectangle())
                    .gesture(DragGesture().onChanged { value in
                        if let date: Date = proxy.value(atX: value.location.x) { selectedDate = date }
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

    private var xDomain: ClosedRange<Date> {
        let granularity = data.granularity ?? "1m"
        if granularity == "1m" {
            let start = {
                let base = beijingCalendar.date(bySettingHour: 6, minute: 0, second: 0, of: data.prediction.issuedAt)!
                return base > data.prediction.issuedAt ? beijingCalendar.date(byAdding: .day, value: -1, to: base)! : base
            }()
            return start...beijingCalendar.date(byAdding: .hour, value: 23, to: start)!
        }
        return (data.history.first?.timestamp ?? .distantPast)...(data.prediction.mid.last?.timestamp ?? .distantFuture)
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

    @AxisContentBuilder
    private var xAxisContent: some AxisContent {
        let granularity = data.granularity ?? "1m"
        if granularity == "1m" {
            let start = xDomain.lowerBound
            let mid = beijingCalendar.date(bySettingHour: 17, minute: 30, second: 0, of: start)!
            let end = xDomain.upperBound
            AxisMarks(values: [start, mid, end]) { value in
                if let date = value.as(Date.self) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                    AxisValueLabel(anchor: date == start ? .topLeading : (date == end ? .topTrailing : .top)) {
                        Text(Self.timeFormatter.string(from: date))
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        } else {
            AxisMarks(values: .automatic(desiredCount: 5)) { value in
                if let date = value.as(Date.self) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                    AxisValueLabel {
                        VStack(spacing: 0) {
                            if granularity == "4h" || granularity == "1d" { Text(Self.dayFormatter.string(from: date)).font(.system(size: 8)) }
                            Text(Self.timeFormatter.string(from: date)).font(.system(size: 10, design: .monospaced))
                        }.foregroundStyle(.secondary)
                    }
                }
            }
        }
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
                Color.Alpha.background.ignoresSafeArea()
                if let data = viewModel.predictionData {
                    VStack(spacing: 0) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("gold.prediction.title").font(.headline).foregroundStyle(Color.Alpha.textPrimary)
                                Text(data.granularity?.uppercased() ?? "").font(.system(size: 10, weight: .bold)).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button { isPresented = false } label: { Image(systemName: "xmark.circle.fill").font(.title).foregroundStyle(Color.Alpha.textSecondary.opacity(0.5)) }
                        }.padding(.horizontal, 24).padding(.top, 16)
                        
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
                        .padding(.horizontal, 20).padding(.bottom, 20)
                    }
                }
            }
            .rotationEffect(.degrees(90))
            .frame(width: geo.size.height, height: geo.size.width)
            .position(x: geo.size.width/2, y: geo.size.height/2)
        }
        .ignoresSafeArea()
    }
}
