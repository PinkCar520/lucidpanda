// mobile/ios/alphaSignal/alphaSignal/Features/Market/MarketTerminalViewModel.swift
import Foundation
import Observation
import AlphaCore
import AlphaData
import OSLog
import SwiftUI

@Observable
public class MarketTerminalViewModel {
    private let logger = AppLog.market
    private let apiClient = APIClient.shared
    
    // MARK: - Published State
    
    /// 四大品种实时报价
    public private(set) var marketSnapshot: MarketSnapshot?
    
    /// K 线图数据（按品种）
    public private(set) var chartData: [String: MarketChartData] = [:]
    
    /// 关联市场情报
    public private(set) var intelligenceItems: [MarketIntelligenceItem] = []
    
    /// 加载状态
    public var isLoading = true
    
    /// 连接状态（SSE 实时流）
    public var connectionStatus: String = "market.connection.disconnected"
    public var isStreaming = false
    
    /// 错误信息
    public var errorMessage: String?
    
    /// 最后更新时间
    public var lastUpdated: Date?
    
    // MARK: - Configuration
    
    /// 自动刷新间隔（秒）
    private let refreshInterval: TimeInterval = 30
    
    /// 定时刷新任务
    private var refreshTimer: Timer?
    
    // MARK: - Initialization
    
    public init() {}
    
    deinit {
        Task { @MainActor [weak self] in
            self?.stopAutoRefresh()
            await self?.stopIntelligenceStream()
        }
    }
    
    // MARK: - Public Methods
    
    /// 启动市场数据加载
    @MainActor
    public func start() async {
        isLoading = true
        errorMessage = nil
        
        await loadMarketSnapshot()
        await loadIntelligenceHistory()
        await startIntelligenceStream()
        startAutoRefresh()
        
        isLoading = false
    }
    
    /// 手动刷新
    @MainActor
    public func refresh() async {
        await loadMarketSnapshot()
    }
    
    /// 加载指定品种的 K 线图
    @MainActor
    public func loadChartData(for symbol: String, range: String = "1d", interval: String = "5m") async {
        guard !symbol.isEmpty else { return }
        
        do {
            let path = "/api/v1/web/market?symbol=\(symbol)&range=\(range)&interval=\(interval)"
            let data: MarketChartData = try await apiClient.fetch(path: path)
            
            withAnimation(.easeInOut(duration: 0.3)) {
                self.chartData[symbol] = data
            }
        } catch {
            logger.error("Failed to load chart data for \(symbol): \(error.localizedDescription)")
        }
    }
    
    // MARK: - Private Methods
    
    /// 加载市场快照
    @MainActor
    private func loadMarketSnapshot() async {
        do {
            let path = "/api/v1/mobile/market/snapshot"
            let snapshot: MarketSnapshot = try await apiClient.fetch(path: path)
            
            withAnimation(.easeInOut(duration: 0.3)) {
                self.marketSnapshot = snapshot
                self.lastUpdated = Date()
                self.connectionStatus = "market.connection.live"
            }
        } catch {
            logger.error("Failed to load market snapshot: \(error.localizedDescription)")
            
            if marketSnapshot == nil {
                errorMessage = "无法加载市场数据，请稍后重试"
            }
        }
    }
    
    /// 加载历史情报
    @MainActor
    private func loadIntelligenceHistory() async {
        do {
            let path = "/api/v1/mobile/intelligence?limit=20"
            let items: [MarketIntelligenceItem] = try await apiClient.fetch(path: path)
            
            withAnimation(.easeInOut(duration: 0.3)) {
                self.intelligenceItems = items.sorted { $0.timestamp > $1.timestamp }
            }
        } catch {
            logger.error("Failed to load intelligence history: \(error.localizedDescription)")
        }
    }
    
    /// 启动 SSE 实时情报流
    @MainActor
    public func startIntelligenceStream() async {
        guard !isStreaming else { return }
        isStreaming = true
        connectionStatus = "market.connection.connecting"
        
        var reconnectAttempts = 0
        let maxReconnectDelay: UInt64 = 30_000_000_000
        
        while !Task.isCancelled {
            do {
                let token = AuthTokenStore.accessToken()
                let streamURL = URL(string: "http://43.139.108.187:8001/api/v1/intelligence/stream")!
                let stream = await SSEResolver.shared.subscribe(url: streamURL, token: token)
                
                connectionStatus = "market.connection.live"
                reconnectAttempts = 0
                
                for try await jsonString in stream {
                    if Task.isCancelled { break }
                    guard let data = jsonString.data(using: .utf8) else { continue }
                    
                    let decoder = JSONDecoder()
                    decoder.dateDecodingStrategy = .iso8601
                    
                    // 使用 IntelligenceEvent (来自 AlphaData)
                    if let event = try? decoder.decode(IntelligenceEvent.self, from: data),
                       let newItems = event.data {
                        // 转换为 MarketIntelligenceItem（使用所有后端返回的字段）
                        let marketItems = newItems.map { item in
                            MarketIntelligenceItem(
                                id: item.id,
                                timestamp: item.timestamp,
                                author: item.author,
                                summary: item.summary,
                                content: item.content,
                                sentiment: item.sentiment,
                                urgencyScore: item.urgencyScore,
                                goldPriceSnapshot: item.goldPriceSnapshot,
                                dxySnapshot: item.dxySnapshot,
                                us10ySnapshot: item.us10ySnapshot,
                                oilSnapshot: item.oilSnapshot,
                                price15m: item.price15m,
                                price1h: item.price1h,
                                price4h: item.price4h,
                                price12h: item.price12h,
                                price24h: item.price24h
                            )
                        }
                        await processNewIntelligenceItems(marketItems)
                    }
                }
                
                if Task.isCancelled { break }
                
            } catch {
                if Task.isCancelled { break }
                
                reconnectAttempts += 1
                let delay = min(UInt64(pow(2, Double(reconnectAttempts))) * 1_000_000_000, maxReconnectDelay)
                
                logger.error("SSE stream failed (attempt \(reconnectAttempts)): \(error.localizedDescription)")
                connectionStatus = "market.connection.connecting"
                
                try? await Task.sleep(nanoseconds: delay)
            }
        }
        
        connectionStatus = "market.connection.disconnected"
        isStreaming = false
    }
    
    /// 停止 SSE 流
    @MainActor
    public func stopIntelligenceStream() async {
        isStreaming = false
        connectionStatus = "market.connection.disconnected"
        await SSEResolver.shared.stop()
    }
    
    /// 处理新情报
    @MainActor
    private func processNewIntelligenceItems(_ newItems: [MarketIntelligenceItem]) async {
        withAnimation(.interpolatingSpring(stiffness: 120, damping: 14)) {
            for item in newItems {
                if !self.intelligenceItems.contains(where: { $0.id == item.id }) {
                    self.intelligenceItems.insert(item, at: 0)
                }
            }
            
            if self.intelligenceItems.count > 50 {
                self.intelligenceItems = Array(self.intelligenceItems.prefix(50))
            }
        }
    }
    
    /// 启动自动刷新
    @MainActor
    private func startAutoRefresh() {
        stopAutoRefresh()
        
        refreshTimer = Timer.scheduledTimer(withTimeInterval: refreshInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.loadMarketSnapshot()
            }
        }
        RunLoop.current.add(refreshTimer!, forMode: .common)
    }
    
    /// 停止自动刷新
    @MainActor
    private func stopAutoRefresh() {
        refreshTimer?.invalidate()
        refreshTimer = nil
    }
}

// MARK: - Computed Properties

extension MarketTerminalViewModel {
    /// 获取指定品种的报价
    public func quote(for symbol: String) -> MarketQuote? {
        switch symbol.uppercased() {
        case "GC=F", "XAUUSD": return marketSnapshot?.gold
        case "DXY": return marketSnapshot?.dxy
        case "CL=F", "USOIL": return marketSnapshot?.oil
        case "US10Y": return marketSnapshot?.us10y
        default: return nil
        }
    }
    
    /// 获取品种名称
    public func name(for symbol: String) -> String {
        switch symbol.uppercased() {
        case "GC=F", "XAUUSD": return "黄金"
        case "DXY": return "美元指数"
        case "CL=F", "USOIL": return "原油"
        case "US10Y": return "美债 10Y"
        default: return symbol
        }
    }
    
    /// 连接状态颜色
    public var statusColor: Color {
        switch connectionStatus {
        case "market.connection.live": return .green
        case "market.connection.connecting": return .orange
        default: return .red
        }
    }
    
    /// 连接状态文本
    public var statusText: String {
        switch connectionStatus {
        case "market.connection.live": return "实时"
        case "market.connection.connecting": return "连接中"
        default: return "已断开"
        }
    }
}

// MARK: - Logger Extension

extension AppLog {
    static let market = Logger(subsystem: "com.pincar.alphasignal", category: "MarketTerminal")
}
