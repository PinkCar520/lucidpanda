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
    
    // Design Tokens from PRD
    private let actualLineColor = Color(hex: "#D85A30")
    private let predictionLineColor = Color(hex: "#378ADD")
    private let breakoutFillColor = Color(hex: "#E24B4A").opacity(0.13)
    private let confidenceFillColor = Color(hex: "#378ADD").opacity(0.09)
    private let pivotLineColor = Color(hex: "#888780").opacity(0.45)

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()
                
                if viewModel.isLoading && viewModel.predictionData == nil {
                    ProgressView().tint(actualLineColor)
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
            .navigationTitle("market.pulse.title")
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
                await viewModel.fetchPrediction()
            }
        }
    }
    
    // MARK: - Components

    private var topControlBar: some View {
        VStack(spacing: 12) {
            HStack {
                HStack(spacing: 8) {
                    Circle()
                        .fill(actualLineColor)
                        .frame(width: 7, height: 7)
                        .opacity(isTickerAnimating ? 1 : 0.4)
                        .scaleEffect(isTickerAnimating ? 1.0 : 0.7)
                        .animation(.easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: isTickerAnimating)
                        .onAppear { isTickerAnimating = true }
                    
                    Text(verbatim: "XAU/USD 实时")
                        .font(.system(size: 13))
                        .foregroundStyle(Color.Alpha.textSecondary)
                    
                    if let lastActual = viewModel.predictionData?.history.last {
                        Text("$\(lastActual.price.formatted())")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                    
                    Text("+12 (+0.37%)") // Mock delta for now as requested by PRD
                        .font(.system(size: 12))
                        .foregroundStyle(Color(hex: "#3B6D11"))
                }
                
                Spacer()
                
                Picker("", selection: $viewModel.selectedGranularity) {
                    Text("1H").tag("1h")
                    Text("4H").tag("4h")
                    Text("1D").tag("1d")
                }
                .pickerStyle(.segmented)
                .frame(width: 140)
                .onChange(of: viewModel.selectedGranularity) {
                    Task { await viewModel.fetchPrediction() }
                }
            }
        }
    }
    
    private var legendView: some View {
        HStack(spacing: 16) {
            legendItem(name: "实际行情（实时）", color: actualLineColor, isDashed: false)
            legendItem(name: "AI 预测中枢", color: predictionLineColor, isDashed: true)
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(predictionLineColor.opacity(0.15))
                    .frame(width: 20, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(predictionLineColor.opacity(0.35), lineWidth: 0.5))
                Text("置信区间").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
            
            HStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color(hex: "#E24B4A").opacity(0.13))
                    .frame(width: 20, height: 8)
                    .overlay(RoundedRectangle(cornerRadius: 2).stroke(Color(hex: "#E24B4A").opacity(0.3), lineWidth: 0.5))
                Text("突破区间").font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    private func legendItem(name: String, color: Color, isDashed: Bool) -> some View {
        HStack(spacing: 5) {
            if isDashed {
                Path { path in
                    path.move(to: CGPoint(x: 0, y: 4))
                    path.addLine(to: CGPoint(x: 22, y: 4))
                }
                .stroke(color, style: StrokeStyle(lineWidth: 2, dash: [4, 2]))
                .frame(width: 22, height: 8)
            } else {
                Rectangle()
                    .fill(color)
                    .frame(width: 22, height: 2.5)
            }
            Text(name).font(.system(size: 10)).foregroundStyle(Color.Alpha.textSecondary)
        }
    }

    private var mainChartSection: some View {
        Group {
            if let data = viewModel.predictionData {
                Chart {
                    // 1. Confidence Area
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
                    
                    // 2. Breakout Area
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
                    
                    // 3. AI Prediction Mid
                    ForEach(mid) { p in
                        LineMark(
                            x: .value("Time", p.timestamp),
                            y: .value("Price", p.price)
                        )
                        .interpolationMethod(.catmullRom)
                        .foregroundStyle(predictionLineColor)
                        .lineStyle(StrokeStyle(lineWidth: 1.8, dash: [6, 4]))
                    }
                    
                    if let first = mid.first {
                        PointMark(
                            x: .value("Time", first.timestamp),
                            y: .value("Price", first.price)
                        )
                        .symbolSize(40)
                        .foregroundStyle(predictionLineColor)
                    }
                    
                    // 4. Actual Price Line
                    ForEach(data.history) { p in
                        LineMark(
                            x: .value("Time", p.timestamp),
                            y: .value("Price", p.price)
                        )
                        .interpolationMethod(.catmullRom)
                        .foregroundStyle(actualLineColor)
                        .lineStyle(StrokeStyle(lineWidth: 2.5))
                    }
                    
                    // 5. Pivot Line
                    RuleMark(x: .value("Pivot", data.prediction.issuedAt))
                        .foregroundStyle(pivotLineColor)
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                        .annotation(position: .top, alignment: .center) {
                            Text(LocalizedStringKey("market.prediction.label.pivot"))
                                .font(.system(size: 11))
                                .foregroundStyle(pivotLineColor.opacity(1.5))
                        }
                    
                    // 6. Prediction Area Background
                    if let lastTime = mid.last?.timestamp {
                        RectangleMark(
                            xStart: .value("Start", data.prediction.issuedAt),
                            xEnd: .value("End", lastTime)
                        )
                        .foregroundStyle(Color(hex: "#888780").opacity(0.06))
                    }
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
                .chartYScale(domain: data.history.map { $0.price }.min()!...data.history.map { $0.price }.max()!)
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 6)) { value in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(Color.gray.opacity(0.1))
                        AxisValueLabel {
                            if let date = value.as(Date.self) {
                                Text(date, format: .dateTime.hour().minute())
                                    .font(.system(size: 10))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .chartYAxis {
                    AxisMarks { value in
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

    private func tooltipView(for date: Date, in data: GoldPredictionResponse) -> some View {
        let actual = data.history.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        let mid = data.prediction.mid.min(by: { abs($0.timestamp.timeIntervalSince(date)) < abs($1.timestamp.timeIntervalSince(date)) })
        
        return VStack(alignment: .leading, spacing: 4) {
            Text(date, format: .dateTime.hour().minute())
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.secondary)
            
            if let a = actual, abs(a.timestamp.timeIntervalSince(date)) < 3600 {
                Text("实际: $\(a.price.formatted())")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(actualLineColor)
            }
            
            if let m = mid, abs(m.timestamp.timeIntervalSince(date)) < 3600 {
                Text("预测: $\(m.price.formatted())")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(predictionLineColor)
            }
        }
        .padding(8)
        .background(Color.Alpha.surface.opacity(0.95))
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator, lineWidth: 0.5))
        .shadow(radius: 4)
        .padding(10)
    }
    
    private var timelineLabels: some View {
        HStack {
            Text(LocalizedStringKey("market.prediction.label.history"))
            Spacer()
            Text(LocalizedStringKey("market.prediction.label.tracking"))
        }
        .font(.system(size: 11))
        .foregroundStyle(Color.Alpha.textSecondary.opacity(0.6))
    }
    
    private var metricCardsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            metricCard(label: "market.prediction.metric.issued_at", value: viewModel.predictedAtText, color: Color.Alpha.textPrimary)
            metricCard(label: "market.prediction.metric.hit_rate", value: String(format: "%.0f%%", viewModel.hitRate), color: Color(hex: "#3B6D11"))
            metricCard(label: "market.prediction.metric.deviation", value: String(format: "%@$%.1f", viewModel.currentDeviation >= 0 ? "+" : "-", abs(viewModel.currentDeviation)), color: viewModel.currentDeviation >= 0 ? Color(hex: "#3B6D11") : Color(hex: "#A32D2D"))
            metricCard(label: "market.prediction.metric.target", value: String(format: "$%.1f", viewModel.targetPrice), color: predictionLineColor)
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
