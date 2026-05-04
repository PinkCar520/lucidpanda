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
                        await viewModel.fetchPrediction(forceRefresh: false)
                    }
                }
            }
            .navigationTitle("gold.prediction.short_title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { isLandscape = true } label: {
                        Image(systemName: "arrow.up.left.and.arrow.down.right")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textSecondary)
                    }
                }

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
                HStack(alignment: .center, spacing: 6) {
                    Circle()
                        .fill(isMarketClosed ? Color.Alpha.neutral : Color.Alpha.brand)
                        .frame(width: 6, height: 6)
                        .opacity(isMarketClosed ? 0.6 : (isTickerAnimating ? 1 : 0.4))
                        .scaleEffect(isMarketClosed ? 1.0 : (isTickerAnimating ? 1.1 : 0.8))
                        .animation(isMarketClosed ? .default : .easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: isTickerAnimating)
                    
                    Text(gold != nil ? "$\(String(format: "%.2f", gold!.price))" : "—")
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.Alpha.textPrimary)
                    
                    Button {
                        Task { await viewModel.fetchPrediction(forceRefresh: true) }
                    } label: {
                        Group {
                            if viewModel.isLoading {
                                ProgressView().tint(Color.Alpha.brand).scaleEffect(0.9)
                            } else {
                                Image(systemName: "sparkles")
                                    .font(.system(size: 22, weight: .semibold))
                                    .foregroundStyle(Color.Alpha.brand)
                            }
                        }
                        .frame(width: 32, height: 32)
                        .background(Color.Alpha.separator.opacity(0.3))
                        .clipShape(Circle())
                    }
                    .disabled(viewModel.isLoading)
                    .padding(.leading, 2)
                }
                
                Text(isMarketClosed ? String(localized: "market.status.closed_label") : (gold?.formattedChange ?? ""))
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundStyle(isMarketClosed ? Color.Alpha.neutral : ((gold?.change ?? 0) >= 0 ? actualUpColor : actualDownColor))
                    .padding(.leading, 12)
            }
            .onAppear { isTickerAnimating = true }
            
            Spacer()
            
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
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.Alpha.separator.opacity(0.5)))
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

    // MARK: - Pre-computed Logic for X-Axis Bounds

    private var sessionBounds: (start: Date, end: Date) {
        let cal = beijingCalendar
        let firstDate = data.history.first?.timestamp ?? Date()
        
        // 伦敦金北京时间 06:00 开盘，05:00 次日收盘
        var comps = cal.dateComponents([.year, .month, .day], from: firstDate)
        if cal.component(.hour, from: firstDate) < 6 {
            let yesterday = cal.date(byAdding: .day, value: -1, to: firstDate)!
            comps = cal.dateComponents([.year, .month, .day], from: yesterday)
        }
        
        comps.hour = 6
        comps.minute = 0
        let start = cal.date(from: comps)!
        let end = cal.date(byAdding: .hour, value: 23, to: start)! // 即次日 05:00
        return (start, end)
    }

    private var xDomain: ClosedRange<Date> {
        if (data.granularity ?? "1m") == "1m" {
            let b = sessionBounds
            return b.start...b.end
        } else {
            let allPoints = (data.history.map { $0.timestamp } + data.prediction.mid.map { $0.timestamp }).sorted()
            let start = allPoints.first ?? Date()
            let end = allPoints.last ?? Date()
            return (min(start, end))...(max(start, end))
        }
    }

    private var labelDates: [Date] {
        let granularity = data.granularity ?? "1m"
        if granularity == "1m" {
            let bounds = sessionBounds
            let mid = beijingCalendar.date(byAdding: .minute, value: 11 * 60 + 30, to: bounds.start)! // 17:30
            return [bounds.start, mid, bounds.end]
        } else {
            let allPoints = (data.history.map { $0.timestamp } + data.prediction.mid.map { $0.timestamp }).sorted()
            return calculateLabelDates(for: allPoints, granularity: granularity)
        }
    }

    private var yDomain: ClosedRange<Double> {
        var all: [Double] = []
        for p in data.history {
            all.append(p.price)
            if let o = p.open { all.append(o) }
            if let h = p.high { all.append(h) }
            if let l = p.low { all.append(l) }
        }
        for p in data.prediction.mid { all.append(p.price) }
        let filtered = all.filter { $0 > 0 }
        guard let minP = filtered.min(), let maxP = filtered.max(), minP < maxP else { return 4500...4700 }
        let padding = (maxP - minP) * 0.05
        return (minP - padding)...(maxP + padding)
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

    // MARK: - Body

    var body: some View {
        let currentDomain = xDomain
        let is1m = (data.granularity ?? "1m") == "1m"
        
        Chart {
            previousCloseMark
            confidenceAreaMark
            breakoutAreaMark
            historyPriceMark
            predictionLineMark
            pivotMark
            crosshairMark
        }
        .chartXScale(domain: currentDomain)
        .chartYScale(domain: yDomain)
        .chartXAxis {
            AxisMarks(values: labelDates) { value in
                if let date = value.as(Date.self) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
                    AxisValueLabel(anchor: date == currentDomain.lowerBound ? .topLeading : (date == currentDomain.upperBound ? .topTrailing : .top)) {
                        if is1m {
                            Text(Self.timeFormatter.string(from: date)).font(.system(size: 10, weight: .bold, design: .monospaced))
                        } else {
                            renderGranularLabel(for: date)
                        }
                    }
                }
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .stride(by: 10.0)) { _ in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.gray.opacity(0.1))
            }
            if let preClose = data.previousClose {
                AxisMarks(position: .leading, values: [preClose]) { _ in
                    AxisValueLabel {
                        Text(Self.formattedPrice(preClose))
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(Color.Alpha.brand)
                    }
                }
            }
        }
        .chartOverlay { proxy in
            GeometryReader { geometry in
                Rectangle().fill(.clear).contentShape(Rectangle())
                    .gesture(DragGesture().onChanged { value in
                        if let date: Date = proxy.value(atX: value.location.x) {
                            selectedDate = date
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

    @ViewBuilder
    private func renderGranularLabel(for date: Date) -> some View {
        let granularity = data.granularity ?? "1m"
        let hour = beijingCalendar.component(.hour, from: date)
        if granularity == "15m" {
            if hour == 0 {
                Text(Self.dayFormatter.string(from: date)).font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundStyle(Color.Alpha.textPrimary)
            } else {
                Text(Self.timeFormatter.string(from: date)).font(.system(size: 10, design: .monospaced)).foregroundStyle(.secondary)
            }
        } else {
            Text(Self.dayFormatter.string(from: date)).font(.system(size: 8, weight: .bold)).foregroundStyle(.secondary)
        }
    }

    private func calculateLabelDates(for points: [Date], granularity: String) -> [Date] {
        var dates: [Date] = []
        var lastLabelDate: Date?
        for date in points {
            let hour = beijingCalendar.component(.hour, from: date)
            let minute = beijingCalendar.component(.minute, from: date)
            var shouldLabel = false
            if granularity == "15m" {
                if minute == 0 && (hour == 0 || hour == 12) { shouldLabel = true }
            } else if granularity == "1d" {
                if beijingCalendar.component(.weekday, from: date) == 2 { shouldLabel = true }
            }
            if shouldLabel {
                if let last = lastLabelDate {
                    if date.timeIntervalSince(last) > 3600 * 4 {
                        dates.append(date)
                        lastLabelDate = date
                    }
                } else {
                    dates.append(date)
                    lastLabelDate = date
                }
            }
        }
        if dates.isEmpty && !points.isEmpty { dates = [points[0], points.last!] }
        return dates
    }

    private static func formattedPrice(_ value: Double) -> String {
        priceFormatter.string(from: NSNumber(value: value)) ?? String(format: "%.2f", value)
    }

    // MARK: - Sub-Chart Components

    @ChartContentBuilder
    private var previousCloseMark: some ChartContent {
        if let preClose = data.previousClose {
            RuleMark(y: .value("Ref", preClose))
                .foregroundStyle(Color.Alpha.brand.opacity(0.6))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
        }
    }

    @ChartContentBuilder
    private var confidenceAreaMark: some ChartContent {
        ForEach(data.prediction.mid) { p in
            if p.timestamp >= data.prediction.issuedAt,
               let lowPoint = data.prediction.lower.first(where: { abs($0.timestamp.timeIntervalSince(p.timestamp)) < 60 }),
               let upPoint = data.prediction.upper.first(where: { abs($0.timestamp.timeIntervalSince(p.timestamp)) < 60 }) {
                AreaMark(x: .value("T", p.timestamp), yStart: .value("L", lowPoint.price), yEnd: .value("U", upPoint.price))
                    .foregroundStyle(confidenceFillColor)
            }
        }
    }

    @ChartContentBuilder
    private var breakoutAreaMark: some ChartContent {
        ForEach(data.history) { p in
            if p.timestamp >= data.prediction.issuedAt {
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
        }
    }

    @ChartContentBuilder
    private var historyPriceMark: some ChartContent {
        if (data.granularity ?? "1m") == "1m" {
            let preClose = data.previousClose ?? (data.history.first?.price ?? 0)
            let trendColor = (data.history.last?.price ?? preClose) >= preClose ? upColor : downColor
            ForEach(data.history) { p in
                LineMark(x: .value("T", p.timestamp), y: .value("P", p.price))
                    .foregroundStyle(trendColor)
                    .lineStyle(StrokeStyle(lineWidth: 2))
            }
        } else {
            ForEach(data.history) { p in
                if let open = p.open, let high = p.high, let low = p.low {
                    let candleColor = p.price >= open ? upColor : downColor
                    RectangleMark(x: .value("T", p.timestamp), yStart: .value("L", low), yEnd: .value("H", high), width: 1).foregroundStyle(candleColor)
                    RectangleMark(x: .value("T", p.timestamp), yStart: .value("O", min(open, p.price)), yEnd: .value("C", max(open, p.price)), width: .fixed(8)).foregroundStyle(candleColor)
                }
            }
        }
    }
    
    @ChartContentBuilder
    private var predictionLineMark: some ChartContent {
        ForEach(data.prediction.mid) { p in
            if p.timestamp >= data.prediction.issuedAt {
                LineMark(x: .value("T", p.timestamp), y: .value("P", p.price), series: .value("S", "P"))
                    .foregroundStyle(predictionLineColor)
                    .lineStyle(StrokeStyle(lineWidth: 2, dash: [5, 5]))
            }
        }
    }

    @ChartContentBuilder
    private var pivotMark: some ChartContent {
        RuleMark(x: .value("X", data.prediction.issuedAt))
            .foregroundStyle(pivotLineColor)
            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
    }

    @ChartContentBuilder
    private var crosshairMark: some ChartContent {
        if let date = selectedDate {
            let historyPoints = data.history.map { GoldPricePoint(timestamp: $0.timestamp, price: $0.price) }
            let all = historyPoints + data.prediction.mid
            if let c = all.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) }) {
                RuleMark(x: .value("T", c.timestamp)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                RuleMark(y: .value("P", c.price)).foregroundStyle(Color.Alpha.textPrimary.opacity(0.15))
                PointMark(x: .value("T", c.timestamp), y: .value("P", c.price))
                    .foregroundStyle(c.timestamp > (data.history.last?.timestamp ?? Date()) ? predictionLineColor : upColor)
                    .symbolSize(60)
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
                if let data = viewModel.predictionData {
                    VStack(spacing: 0) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("gold.prediction.short_title").font(.headline).foregroundStyle(Color.Alpha.textPrimary)
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
