import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import Charts

struct ReconciliationView: View {
    @State private var history: [ValuationHistory] = []
    @State private var isLoading = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                ScrollView {
                    VStack(spacing: 24) {
                        headerSection
                        
                        if isLoading {
                            ProgressView().padding(.top, 40)
                        } else if history.isEmpty {
                            emptyStateView
                        } else {
                            // 1. 误差走势图 (Accuracy Trend)
                            LiquidGlassCard {
                                VStack(alignment: .leading, spacing: 16) {
                                    Text("reconciliation.chart.mae")
                                        .font(.system(size: 14, weight: .bold))
                                    
                                    Chart(history) { point in
                                        LineMark(
                                            x: .value("Date", point.date),
                                            y: .value("Error", point.growth)
                                        )
                                        .foregroundStyle(.blue)
                                        .interpolationMethod(.catmullRom)
                                        
                                        AreaMark(
                                            x: .value("Date", point.date),
                                            y: .value("Error", point.growth)
                                        )
                                        .foregroundStyle(.blue.opacity(0.1))
                                    }
                                    .frame(height: 200)
                                }
                            }
                            .padding(.horizontal)
                            
                            // 2. 统计摘要
                            HStack(spacing: 16) {
                                statsCard(title: String(localized: "reconciliation.stats.mae"), value: "0.12%", color: .green)
                                statsCard(title: String(localized: "reconciliation.stats.success_rate"), value: "99.2%", color: .blue)
                            }
                            .padding(.horizontal)
                            
                            // 3. 对账明细列表
                            VStack(alignment: .leading, spacing: 12) {
                                Text("reconciliation.history.title")
                                    .font(.system(size: 14, weight: .bold))
                                    .padding(.horizontal)
                                
                                ForEach(history.prefix(10)) { point in
                                    LiquidGlassCard {
                                        HStack {
                                            Text(point.date.formatted(date: .abbreviated, time: .omitted))
                                                .font(.system(size: 12, weight: .medium))
                                            Spacer()
                                            Text(
                                                String(
                                                    format: NSLocalizedString("reconciliation.history.error_format", comment: ""),
                                                    String(format: "%.3f", point.growth)
                                                )
                                            )
                                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                                .foregroundStyle(abs(point.growth) < 0.5 ? .green : .red)
                                        }
                                    }
                                }
                                .padding(.horizontal)
                            }
                        }
                        
                        Spacer(minLength: 40)
                    }
                }
            }
            .navigationTitle("reconciliation.nav.title")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await fetchReconciliationData()
            }
        }
    }
    
    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("reconciliation.header.title")
                .font(.system(size: 24, weight: .black, design: .rounded))
                .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
            Text("reconciliation.header.subtitle")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal)
        .padding(.top, 24)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    private func statsCard(title: String, value: String, color: Color) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(title).font(.caption2).foregroundStyle(.secondary)
                Text(value).font(.title3.bold()).foregroundStyle(color)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Spacer(minLength: 100)
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 48))
                .foregroundStyle(.gray.opacity(0.2))
            Text("reconciliation.empty")
                .font(.headline)
                .foregroundStyle(.gray)
        }
    }
    
    private func fetchReconciliationData() async {
        isLoading = true
        do {
            // 生产级：从后端拉取整体健康指标
            // 这里暂用模拟数据演示 Chart，实际应通过 APIClient 拉取
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.history = generateMockHistory()
        }
        isLoading = false
    }
    
    private func generateMockHistory() -> [ValuationHistory] {
        let calendar = Calendar.current
        return (0..<20).map { i in
            ValuationHistory(
                date: calendar.date(byAdding: .day, value: -i, to: Date())!,
                growth: Double.random(in: -0.8...0.8)
            )
        }.reversed()
    }
}

extension ValuationHistory: Identifiable {
    public var id: Date { date }
}
