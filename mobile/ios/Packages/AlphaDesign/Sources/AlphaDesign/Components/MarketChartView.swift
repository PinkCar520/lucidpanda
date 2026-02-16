// mobile/ios/Packages/AlphaDesign/Sources/AlphaDesign/Components/MarketChartView.swift
import SwiftUI
import Charts
import AlphaData

public struct MarketChartView: View {
    let data: [MarketDataPoint]
    @State private var selectedDate: Date?
    
    public init(data: [MarketDataPoint]) {
        self.data = data
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // 当前选中价格显示
            if let selectedPoint = currentSelectedPoint {
                VStack(alignment: .leading) {
                    Text("$\(String(format: "%.2f", selectedPoint.price))")
                        .font(.system(size: 24, weight: .black, design: .monospaced))
                        .foregroundStyle(.white)
                    Text(selectedPoint.date.formatted(date: .abbreviated, time: .shortened))
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.4))
                }
                .transition(.opacity)
            } else if let last = data.last {
                VStack(alignment: .leading) {
                    Text("$\(String(format: "%.2f", last.price))")
                        .font(.system(size: 24, weight: .black, design: .monospaced))
                        .foregroundStyle(.blue)
                    Text("实时报价 (GC=F)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white.opacity(0.3))
                }
            }

            Chart {
                ForEach(data) { point in
                    // 区域填充
                    AreaMark(
                        x: .value("Time", point.date),
                        y: .value("Price", point.price)
                    )
                    .foregroundStyle(.blue.opacity(0.1))
                    .interpolationMethod(.catmullRom)

                    // 主趋势线
                    LineMark(
                        x: .value("Time", point.date),
                        y: .value("Price", point.price)
                    )
                    .foregroundStyle(.blue)
                    .lineStyle(StrokeStyle(lineWidth: 2, lineCap: .round))
                    .interpolationMethod(.catmullRom)
                }
                
                // 交互辅助线
                if let selectedDate {
                    RuleMark(x: .value("Selected", selectedDate))
                        .foregroundStyle(.white.opacity(0.2))
                        .offset(y: -10)
                        .annotation(position: .top, spacing: 0) {
                            Circle()
                                .fill(.blue)
                                .frame(width: 8, height: 8)
                                .shadow(radius: 4)
                        }
                }
            }
            .chartXSelection(value: $selectedDate)
            .chartYScale(domain: minPrice...maxPrice) // 智能缩放
            .frame(height: 200)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 4)) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.white.opacity(0.05))
                    AxisValueLabel().foregroundStyle(.white.opacity(0.3)).font(.system(size: 8))
                }
            }
            .chartYAxis {
                AxisMarks(position: .trailing, values: .automatic(desiredCount: 3)) {
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5)).foregroundStyle(.white.opacity(0.05))
                    AxisValueLabel().foregroundStyle(.white.opacity(0.3)).font(.system(size: 8))
                }
            }
        }
        .padding()
        .background(.white.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }
    
    private var minPrice: Double { (data.map { $0.price }.min() ?? 0) * 0.998 }
    private var maxPrice: Double { (data.map { $0.price }.max() ?? 0) * 1.002 }
    
    private var currentSelectedPoint: MarketDataPoint? {
        guard let selectedDate else { return nil }
        return data.min(by: { abs($0.date.timeIntervalSince(selectedDate)) < abs($1.date.timeIntervalSince(selectedDate)) })
    }
}
