// mobile/ios/alphaSignal/alphaSignal/Features/Market/Components/MarketChartView.swift
import SwiftUI
import AlphaData
import Charts

/// 迷你 K 线图组件
struct MarketChartView: View {
    let chartData: MarketChartData
    let height: CGFloat
    let showVolume: Bool
    
    init(chartData: MarketChartData, height: CGFloat = 120, showVolume: Bool = true) {
        self.chartData = chartData
        self.height = height
        self.showVolume = showVolume
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // K 线图表
            Chart(chartData.quotes) { quote in
                // 蜡烛图 - 影线 (High-Low)
                RuleMark(
                    x: .value("Date", quote.date),
                    yStart: .value("Low", quote.low),
                    yEnd: .value("High", quote.high)
                )
                .foregroundStyle(quote.isBullish ? Color.red : Color.green)
                .lineStyle(StrokeStyle(lineWidth: 1))

                // 实体 (Open-Close)
                RectangleMark(
                    x: .value("Date", quote.date),
                    yStart: .value("Price", min(quote.open, quote.close)),
                    yEnd: .value("Price", max(quote.open, quote.close)),
                    width: .fixed(4)
                )
                .foregroundStyle(quote.isBullish ? Color.red : Color.green)

                // 成交量（可选）
                if showVolume, let volume = quote.volume {
                    RectangleMark(
                        x: .value("Date", quote.date),
                        y: .value("Volume", volume),
                        width: .fixed(4)
                    )
                    .foregroundStyle(quote.isBullish ? Color.red.opacity(0.3) : Color.green.opacity(0.3))
                    .opacity(0.5)
                }
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartPlotStyle { plotArea in
                plotArea
                    .background(Color(.systemBackground))
            }
            .frame(height: showVolume ? height * 0.7 : height)

            // 成交量图表（如果启用）
            if showVolume {
                Chart(chartData.quotes) { quote in
                    BarMark(
                        x: .value("Date", quote.date),
                        y: .value("Volume", quote.volume ?? 0)
                    )
                    .foregroundStyle(quote.isBullish ? Color.red.opacity(0.4) : Color.green.opacity(0.4))
                }
                .chartXAxis {
                    AxisMarks(values: .stride(by: .hour, count: 4)) { _ in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [2, 2]))
                            .foregroundStyle(Color.gray.opacity(0.2))
                        AxisValueLabel(format: .dateTime.hour())
                            .foregroundStyle(Color.secondary)
                    }
                }
                .chartYAxis(.hidden)
                .frame(height: height * 0.3)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.systemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }
}

/// 品种价格趋势火花图（简化版）
struct SparklineView: View {
    let prices: [Double]
    let color: Color
    
    var body: some View {
        GeometryReader { geometry in
            Path { path in
                guard !prices.isEmpty else { return }
                
                let stepX = geometry.size.width / CGFloat(max(prices.count - 1, 1))
                let minPrice = prices.min() ?? 0
                let maxPrice = prices.max() ?? 1
                let priceRange = maxPrice - minPrice
                
                for (index, price) in prices.enumerated() {
                    let x = CGFloat(index) * stepX
                    let y = geometry.size.height - CGFloat((price - minPrice) / priceRange) * geometry.size.height
                    
                    if index == 0 {
                        path.move(to: CGPoint(x: x, y: y))
                    } else {
                        path.addLine(to: CGPoint(x: x, y: y))
                    }
                }
            }
            .stroke(color, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
        }
        .frame(height: 40)
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 16) {
        // 模拟 K 线数据
        let mockQuotes = (0..<20).map { i -> MarketQuoteBar in
            let basePrice = 2680.0 + Double(i) * 2
            return MarketQuoteBar(
                date: Calendar.current.date(byAdding: .hour, value: -20 + i, to: Date())!,
                open: basePrice,
                high: basePrice + 3,
                low: basePrice - 2,
                close: basePrice + 1,
                volume: Double(1000 + i * 100)
            )
        }
        
        let mockData = MarketChartData(
            symbol: "GC=F",
            quotes: mockQuotes,
            indicators: nil
        )
        
        MarketChartView(chartData: mockData, height: 150)
            .padding()
        
        SparklineView(
            prices: [2670, 2675, 2673, 2680, 2685, 2682, 2690, 2688, 2695, 2692],
            color: .red
        )
        .frame(height: 40)
        .padding()
    }
    .background(Color(.systemGray6))
}
