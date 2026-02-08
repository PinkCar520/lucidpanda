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
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("策略仿真回测")
                                .font(.system(size: 24, weight: .black, design: .rounded))
                                .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                            
                            Text("基于全量历史数据的 AI 胜率分析")
                                .font(.caption2)
                                .foregroundStyle(.gray)
                        }
                        Spacer()
                        
                        Button {
                            showConfig.toggle()
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
                    
                    if showConfig {
                        configPanel.transition(.move(edge: .top).combined(with: .opacity))
                    }
                    
                    if let stats = viewModel.stats {
                        statsGrid(stats)
                        sessionChart(stats)
                        sensitivitySection(stats)
                    } else {
                        ProgressView().tint(.blue).padding(.top, 40)
                    }
                    
                    Spacer(minLength: 100)
                }
            }
        }
        .task {
            await viewModel.fetchStats()
        }
    }
    
    private var configPanel: some View {
        LiquidGlassCard {
            VStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("最低紧迫评分: \(viewModel.minScore)")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(.blue)
                    
                    Slider(value: Binding(get: { Double(viewModel.minScore) }, set: { viewModel.minScore = Int($0) }), in: 1...10, step: 1)
                        .tint(.blue)
                }
                
                Picker("时间窗口", selection: $viewModel.selectedWindow) {
                    Text("1小时").tag("1h")
                    Text("24小时").tag("24h")
                }
                .pickerStyle(.segmented)
                
                Button {
                    Task { 
                        withAnimation { showConfig = false }
                        await viewModel.fetchStats() 
                    }
                } label: {
                    Text("应用配置并重新重算")
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
            statItem(title: "修正胜率", value: "\(Int(stats.adjWinRate))%", sub: "Adjusted", color: .blue)
            statItem(title: "平均跌幅", value: String(format: "%.2f%%", abs(stats.avgDrop)), sub: "Avg Drop", color: .red)
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
                    .font(.system(size: 20, weight: .black, design: .monospaced))
                    .foregroundStyle(color == .primary ? .black : color)
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
                Text("市场时段表现")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                
                Chart(stats.sessionStats) { session in
                    BarMark(
                        x: .value("Session", session.session),
                        y: .value("WinRate", session.winRate)
                    )
                    .foregroundStyle(by: .value("Session", session.session))
                    .annotation(position: .top) {
                        Text("\(Int(session.winRate))%")
                            .font(.system(size: 8, weight: .bold, design: .monospaced))
                            .foregroundStyle(.gray)
                    }
                }
                .frame(height: 120)
                .chartLegend(.hidden)
                .chartYScale(domain: 0...100)
            }
        }
        .padding(.horizontal)
    }
    
    private func sensitivitySection(_ stats: BacktestStats) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("环境敏感度分析")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(.black)
                .padding(.horizontal)
            
            HStack(spacing: 12) {
                sensitivityCard(title: "美元走强", stats: stats.correlation["DXY_STRONG"])
                sensitivityCard(title: "美元走弱", stats: stats.correlation["DXY_WEAK"])
            }
            .padding(.horizontal)
        }
    }
    
    private func sensitivityCard(title: String, stats: BacktestStats.SessionWinRate?) -> some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.gray)
                
                if let stats = stats {
                    HStack(alignment: .bottom, spacing: 4) {
                        Text("\(Int(stats.winRate))%")
                            .font(.system(size: 18, weight: .black, design: .monospaced))
                            .foregroundStyle(.blue)
                        Text("胜率")
                            .font(.system(size: 8))
                            .foregroundStyle(.gray)
                            .padding(.bottom, 2)
                    }
                } else {
                    Text("无数据").font(.caption).foregroundStyle(.gray)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}