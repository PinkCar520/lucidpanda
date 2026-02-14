import Foundation
import AlphaData
import AlphaCore
import OSLog

/// 生产级估值计算 Actor
/// 负责处理高频价格流并维护基金的实时估值状态
public actor ValuationActor {
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "ValuationEngine")
    
    private var isRunning = false
    private var currentValuation: FundValuation
    private var priceMap: [String: Double] = [:] // SecurityID -> Price
    
    public init(initialValuation: FundValuation) {
        self.currentValuation = initialValuation
        // 初始化价格映射
        for component in initialValuation.components {
            priceMap[component.code] = component.changePct
        }
    }
    
    /// 启动实时估值流
    /// 逻辑：订阅后端价格推送，根据持仓权重实时累加
    public func start() -> AsyncStream<FundValuation> {
        self.isRunning = true
        
        return AsyncStream { continuation in
            let task = Task {
                // 1. 获取订阅列表 (底层持仓代码)
                let symbols = currentValuation.components.map { $0.code }
                logger.debug("🛰️ Subscribing to price stream for symbols: \(symbols.joined(separator: ","))")
                
                // 2. 这里的逻辑是对接 SSEResolver
                // 在成熟实现中，后端会有一个专门推送资产价格的 SSE 端点
                // 这里我们先实现基于 REST 轮询的高级封装，作为 SSE 的降级/备选方案
                while isRunning {
                    do {
                        // 模拟从后端获取最新分片价格或直接获取推算结果
                        // 生产环境应为：for try await priceUpdate in SSEResolver.shared.subscribe(...)
                        let updatedValuation: FundValuation = try await APIClient.shared.fetch(
                            path: "/api/v1/web/funds/\(currentValuation.fundCode)/valuation"
                        )
                        
                        if !isRunning { break }
                        
                        self.currentValuation = updatedValuation
                        continuation.yield(updatedValuation)
                        
                        // 模拟盘中 2 秒同步频率
                        try await Task.sleep(nanoseconds: 2_000_000_000)
                    } catch {
                        logger.error("❌ Valuation sync failed: \(error.localizedDescription)")
                        try? await Task.sleep(nanoseconds: 5_000_000_000) // 错误退避
                    }
                }
                continuation.finish()
            }
            
            continuation.onTermination = { @Sendable _ in
                Task { await self.stop() }
                task.cancel()
            }
        }
    }
    
    public func stop() {
        isRunning = false
    }
    
    /// 计算 2σ 统计边界
    /// 基于过去 30 天历史收益率的真实计算
    public func calculateThreshold2Sigma(history: [ValuationHistory]) -> Double {
        let returns = history.compactMap { $0.growth }
        guard returns.count > 5 else { return 1.5 } // 数据不足时返回经验值
        
        let mean = returns.reduce(0, +) / Double(returns.count)
        let sumOfSquaredDiff = returns.map { pow($0 - mean, 2) }.reduce(0, +)
        let standardDeviation = sqrt(sumOfSquaredDiff / Double(returns.count))
        
        return standardDeviation * 2.0
    }
}

/// 补充 ValuationHistory 模型定义
public struct ValuationHistory: Codable {
    public let date: Date
    public let growth: Double
}
