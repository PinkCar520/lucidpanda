import SwiftUI
import AlphaDesign
import AlphaData
import Charts

struct BacktestView: View {
    @State private var viewModel = BacktestViewModel()
    @State private var showConfig = false
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView(showsIndicators: false) {
                VStack(spacing: 24) {
                    headerSection
                    
                    if showConfig {
                        configPanel.transition(.move(edge: .top).combined(with: .opacity))
                    }
                    
                    if let stats = viewModel.stats {
                        // 1. Core KPIs
                        statsGrid(stats)
                        
                        // 2. Time-based Analysis
                        sessionChart(stats)
                        
                        // 3. Environment Analysis (Macro Regimes)
                        environmentSection(stats)
                        
                        // 4. Return Distribution
                        if let dist = stats.distribution {
                            distributionChart(dist)
                        }
                        
                        // 5. Evidence List (Trade Log)
                        if let items = stats.items, !items.isEmpty {
                            evidenceListSection(items)
                        }
                        
                    } else if viewModel.isLoading {
                        ProgressView().tint(.blue).padding(.top, 40)
                    } else {
                        emptyStateView
                    }
                    
                    Spacer(minLength: 100)
                }
            }
        }
        .task {
            await viewModel.fetchStats()
        }
    }
    
    // MARK: - Sub-View Sections
    
    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("策略仿真回测")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                
                Text("基于 \(viewModel.selectedWindow == "1h" ? "1H" : "24H") 窗口的历史胜率建模")
                    .font(.caption2)
                    .foregroundStyle(.gray)
            }
            Spacer()
            
            Button {
                withAnimation(.spring()) { showConfig.toggle() }
            } label: {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(.blue)
                    .padding(10)
                    .background(.blue.opacity(0.1))
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal)
        .padding(.top, 24)
    }
    
    private var configPanel: some View {
        LiquidGlassCard {
            VStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("最低紧迫评分: \(viewModel.minScore)")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                        Spacer()
                        Text("当前选择: \(viewModel.sentiment == "bearish" ? "看跌信号" : "看涨信号")")
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                    }
                    .foregroundStyle(.blue)
                    
                    Slider(value: Binding(get: { Double(viewModel.minScore) }, set: { viewModel.minScore = Int($0) }), in: 1...10, step: 1)
                        .tint(.blue)
                }
                
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("预测窗口").font(.system(size: 9, weight: .bold)).foregroundStyle(.secondary)
                        Picker("窗口", selection: $viewModel.selectedWindow) {
                            Text("15分钟").tag("15m")
                            Text("1小时").tag("1h")
                            Text("4小时").tag("4h")
                            Text("24小时").tag("24h")
                        }
                        .pickerStyle(.segmented)
                    }
                }
                
                HStack(spacing: 12) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("信号方向").font(.system(size: 9, weight: .bold)).foregroundStyle(.secondary)
                        Picker("方向", selection: $viewModel.sentiment) {
                            Text("看跌 (Bearish)").tag("bearish")
                            Text("看涨 (Bullish)").tag("bullish")
                        }
                        .pickerStyle(.segmented)
                    }
                }
                
                Button {
                    Task { 
                        withAnimation { showConfig = false }
                        await viewModel.fetchStats() 
                    }
                } label: {
                    Text("开始回测重算")
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
        .padding(.horizontal)
    }
    
    private func statsGrid(_ stats: BacktestStats) -> some View {
        HStack(spacing: 12) {
            statItem(title: "样本量", value: "\(stats.count)", sub: "Events")
            statItem(title: "修正胜率", value: String(format: "%.1f%%", stats.adjWinRate), sub: "Adjusted", color: .blue)
            statItem(title: "平均跌幅", value: String(format: "%.2f%%", abs(stats.avgDrop)), sub: "Avg Gain/Drop", color: .red)
        }
        .padding(.horizontal)
    }
    
    private func statItem(title: String, value: String, sub: String, color: Color = .primary) -> some View {
        LiquidGlassCard {
            VStack(spacing: 4) {
                Text(title)
                    .font(.system(size: 8, weight: .bold))
                    .foregroundStyle(.gray)
                Text(value)
                    .font(.system(size: 18, weight: .black, design: .monospaced))
                    .foregroundStyle(color == .primary ? .primary : color)
                Text(sub)
                    .font(.system(size: 8, weight: .bold))
                    .foregroundStyle(.gray.opacity(0.5))
            }
            .frame(maxWidth: .infinity)
        }
    }
    
    private func sessionChart(_ stats: BacktestStats) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("市场时段胜率分布")
                    .font(.system(size: 12, weight: .bold))
                
                Chart(stats.sessionStats) { session in
                    BarMark(
                        x: .value("Session", session.session),
                        y: .value("WinRate", session.winRate)
                    )
                    .foregroundStyle(by: .value("Session", session.session))
                    .annotation(position: .top) {
                        Text("\(Int(session.winRate))%")
                            .font(.system(size: 8, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(height: 120)
                .chartLegend(.hidden)
                .chartYScale(domain: 0...100)
            }
        }
        .padding(.horizontal)
    }
    
    private func environmentSection(_ stats: BacktestStats) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("多维宏观环境对比")
                .font(.system(size: 12, weight: .bold))
                .padding(.horizontal)
            
            VStack(spacing: 12) {
                // 1. DXY Sensitivity
                HStack(spacing: 12) {
                    sensitivityCard(title: "美元走强", stats: stats.correlation["DXY_STRONG"])
                    sensitivityCard(title: "美元走弱", stats: stats.correlation["DXY_WEAK"])
                }
                
                // 2. Volatility (GVZ)
                HStack(spacing: 12) {
                    sensitivityCard(title: "高波动环境", stats: stats.volatility?["HIGH_VOL"])
                    sensitivityCard(title: "低波动环境", stats: stats.volatility?["LOW_VOL"])
                }
                
                // 3. Positioning (COT)
                HStack(spacing: 12) {
                    sensitivityCard(title: "极度拥挤(多)", stats: stats.positioning?["OVERCROWDED_LONG"])
                    sensitivityCard(title: "正常/极度(空)", stats: stats.positioning?["NEUTRAL_POSITION"])
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func distributionChart(_ dist: [BacktestStats.DistributionBin]) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 16) {
                Text("盈亏概率分布 (Histogram)")
                    .font(.system(size: 12, weight: .bold))
                
                Chart(dist) { bin in
                    BarMark(
                        x: .value("Returns", bin.bin),
                        y: .value("Count", bin.count)
                    )
                    .foregroundStyle(bin.bin >= 0 ? Color.red.opacity(0.7) : Color.green.opacity(0.7))
                }
                .frame(height: 100)
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        AxisValueLabel {
                            if let val = value.as(Double.self) {
                                Text("\(val, specifier: "%.1f")%")
                                    .font(.system(size: 8))
                            }
                        }
                    }
                }
            }
        }
        .padding(.horizontal)
    }
    
    private func evidenceListSection(_ items: [BacktestStats.BacktestItem]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("最近 50 条回测证据")
                .font(.system(size: 12, weight: .bold))
                .padding(.horizontal)
            
            VStack(spacing: 10) {
                ForEach(items) { item in
                    LiquidGlassCard {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(item.title)
                                    .font(.system(size: 12, weight: .bold))
                                    .lineLimit(1)
                                Spacer()
                                Text(String(format: "%+.2f%%", item.changePct))
                                    .font(.system(size: 12, weight: .black, design: .monospaced))
                                    .foregroundStyle(item.isWin ? .blue : .secondary)
                            }
                            
                            HStack {
                                Text("入场: $\(String(format: "%.1f", item.entry))")
                                Text("→")
                                Text("出场: $\(String(format: "%.1f", item.exit))")
                                Spacer()
                                Text(formatDate(item.timestamp))
                            }
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .padding(.horizontal)
        }
    }
    
    private func sensitivityCard(title: String, stats: BacktestStats.SessionWinRate?) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(.secondary)
                
                if let stats = stats {
                    HStack(alignment: .bottom, spacing: 2) {
                        Text("\(Int(stats.winRate))%")
                            .font(.system(size: 16, weight: .black, design: .monospaced))
                            .foregroundStyle(.blue)
                        Text("胜率")
                            .font(.system(size: 7))
                            .foregroundStyle(.secondary)
                            .padding(.bottom, 2)
                    }
                } else {
                    Text("样本不足").font(.system(size: 10)).foregroundStyle(.tertiary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM-dd HH:mm"
        return formatter.string(from: date)
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Spacer(minLength: 100)
            Image(systemName: "chart.bar.xaxis")
                .font(.largeTitle)
                .foregroundStyle(.gray.opacity(0.2))
            Text("暂无回测数据")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
    }
}
