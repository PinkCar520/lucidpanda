// mobile/ios/alphaSignal/alphaSignal/Features/Market/MarketTerminalView.swift
import SwiftUI
import AlphaData
import AlphaDesign

/// 市场情报终端主视图
public struct MarketTerminalView: View {
    @State private var viewModel = MarketTerminalViewModel()
    @State private var selectedSymbol: MarketQuoteCard.SymbolType?
    @State private var showingDetail = false
    
    public init() {}
    
    public var body: some View {
        NavigationStack {
            ZStack {
                // 背景
                Color(.systemBackground)
                    .ignoresSafeArea()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 16) {
                        // 1. 状态栏
                        statusSection
                        
                        // 2. 四宫格报价卡
                        quoteGridSection
                        
                        // 3. 选中品种的 K 线图
                        if let selected = selectedSymbol,
                           let chartData = viewModel.chartData[selected.rawValue] {
                            chartSection(symbol: selected, data: chartData)
                        }
                        
                        // 4. 关联市场情报
                        intelligenceSection
                    }
                    .padding()
                }
                
                // 加载状态
                if viewModel.isLoading {
                    loadingView
                }
            }
            .navigationTitle("市场情报")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: {
                        Task { await viewModel.refresh() }
                    }) {
                        Image(systemName: "arrow.clockwise")
                            .foregroundStyle(.primary)
                    }
                    .disabled(viewModel.isLoading)
                }
            }
            .task {
                await viewModel.start()
            }
            .onDisappear {
                Task { await viewModel.stopIntelligenceStream() }
            }
        }
    }
    
    // MARK: - Subviews
    
    /// 状态栏
    private var statusSection: some View {
        HStack {
            // 连接状态
            HStack(spacing: 6) {
                Circle()
                    .fill(viewModel.statusColor)
                    .frame(width: 8, height: 8)
                
                Text(viewModel.statusText)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(viewModel.statusColor)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                Capsule()
                    .fill(viewModel.statusColor.opacity(0.1))
            )
            
            Spacer()
            
            // 最后更新时间
            if let lastUpdated = viewModel.lastUpdated {
                Text("更新于 \(formatTime(lastUpdated))")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.bottom, 8)
    }
    
    /// 四宫格报价卡
    private var quoteGridSection: some View {
        LazyVGrid(
            columns: [GridItem(.flexible()), GridItem(.flexible())],
            spacing: 12
        ) {
            ForEach(MarketQuoteCard.SymbolType.allCases, id: \.self) { symbol in
                if let quote = viewModel.quote(for: symbol.rawValue) {
                    MarketQuoteCard(
                        quote: quote,
                        symbol: symbol,
                        onTap: {
                            withAnimation(.spring(response: 0.3)) {
                                selectedSymbol = symbol
                            }
                            Task {
                                await viewModel.loadChartData(for: symbol.rawValue)
                            }
                        }
                    )
                    .frame(height: 150)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(
                                selectedSymbol == symbol ? Color.blue : Color.clear,
                                lineWidth: 2
                            )
                    )
                } else {
                    // 数据加载中占位
                    QuoteCardPlaceholder(symbol: symbol)
                        .frame(height: 150)
                }
            }
        }
    }
    
    /// K 线图区域
    private func chartSection(symbol: MarketQuoteCard.SymbolType, data: MarketChartData) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(symbol.displayName)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.primary)
                
                Spacer()

                // 时间范围选择器（简化版）
                Picker("范围", selection: .constant("1d")) {
                    Text("1 天").tag("1d")
                    Text("1 周").tag("1w")
                    Text("1 月").tag("1m")
                }
                .pickerStyle(.segmented)
                .frame(width: 150)
            }
            
            MarketChartView(chartData: data, height: 180, showVolume: true)
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(.secondarySystemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .strokeBorder(Color.gray.opacity(0.1), lineWidth: 1)
        )
    }
    
    /// 关联情报区域
    private var intelligenceSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "waveform.path.ecg")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.blue)
                
                Text("市场情报")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.primary)
                
                Spacer()
                
                Text("\(viewModel.intelligenceItems.count) 条")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            
            if viewModel.intelligenceItems.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "tray.and.arrow.down")
                        .font(.system(size: 32))
                        .foregroundStyle(.gray.opacity(0.3))
                    Text("暂无市场情报")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 32)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color(.secondarySystemBackground))
                )
            } else {
                VStack(spacing: 10) {
                    ForEach(viewModel.intelligenceItems.prefix(5)) { item in
                        IntelligenceItemCard(item: item)
                    }
                }
            }
        }
    }
    
    /// 加载视图
    private var loadingView: some View {
        ZStack {
            Color(.systemBackground).opacity(0.9)
            
            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                
                Text("正在加载市场数据...")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
        }
        .ignoresSafeArea()
    }
    
    // MARK: - Helpers
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: date)
    }
}

// MARK: - Placeholder Component

/// 报价卡占位符（加载中使用）
struct QuoteCardPlaceholder: View {
    let symbol: MarketQuoteCard.SymbolType
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: symbol.icon)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(symbol.primaryColor.opacity(0.5))
                
                Text(symbol.displayName)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.secondary.opacity(0.5))
                
                Spacer()
            }
            
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.gray.opacity(0.1))
                .frame(width: 80, height: 28)
            
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.gray.opacity(0.1))
                .frame(width: 60, height: 18)
            
            Spacer()
        }
        .padding(14)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(0.1), lineWidth: 1)
        )
    }
}

// MARK: - Intelligence Item Card (简化版)

extension MarketTerminalView {
    struct IntelligenceItemCard: View {
        let item: MarketIntelligenceItem
        
        var body: some View {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(item.summary)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                    
                    Spacer()
                }
                
                HStack {
                    // 紧急度标签
                    if item.urgencyScore >= 8 {
                        Text("警报")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule().fill(Color.red)
                            )
                    }
                    
                    Text(formatDate(item.timestamp))
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                    
                    Spacer()
                    
                    // 情绪标签
                    Text(item.sentiment)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(item.sentiment.contains("鹰") || item.sentiment.contains("利空") ? .green : .red)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(
                            Capsule().fill((item.sentiment.contains("鹰") || item.sentiment.contains("利空") ? Color.green : Color.red).opacity(0.1))
                        )
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color(.secondarySystemBackground))
            )
        }
        
        private func formatDate(_ date: Date) -> String {
            let formatter = DateFormatter()
            formatter.dateFormat = "MM-dd HH:mm"
            return formatter.string(from: date)
        }
    }
}

// MARK: - Preview

#Preview {
    MarketTerminalView()
}
