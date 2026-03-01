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
    private var sseNextRetryAt: Date = .distantPast
    private let sseRetryDelay: TimeInterval = 15
    
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
                
                while isRunning {
                    do {
                        let marketStatus = MarketSessionStatusResolver.status(for: currentValuation)
                        if marketStatus == .closed {
                            // 休市时暂停高频请求，避免无效轮询
                            try await Task.sleep(nanoseconds: 60_000_000_000)
                            continue
                        }

                        if Date() >= self.sseNextRetryAt {
                            let didStream = try await self.consumeSSE(continuation: continuation)
                            if didStream {
                                self.sseNextRetryAt = .distantPast
                                continue
                            }
                        }

                        let updatedValuation = try await pollLatestValuation()
                        if !isRunning { break }
                        self.currentValuation = updatedValuation
                        continuation.yield(updatedValuation)
                        try await Task.sleep(nanoseconds: 5_000_000_000)
                    } catch {
                        logger.error("❌ Valuation sync failed: \(error.localizedDescription)")
                        self.sseNextRetryAt = Date().addingTimeInterval(self.sseRetryDelay)
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

    private func pollLatestValuation() async throws -> FundValuation {
        try await APIClient.shared.fetch(
            path: "/api/v1/web/funds/\(currentValuation.fundCode)/valuation"
        )
    }

    private func consumeSSE(continuation: AsyncStream<FundValuation>.Continuation) async throws -> Bool {
        let baseURL = await APIClient.shared.baseURL
        let streamURL = baseURL.appendingPathComponent("api/v1/web/funds/\(currentValuation.fundCode)/stream")
        let token = AuthTokenStore.accessToken()
        let stream = await SSEResolver.shared.subscribe(url: streamURL, token: token)
        var receivedUpdate = false

        for try await payload in stream {
            if !isRunning { break }
            if let updated = decodeValuation(from: payload) {
                receivedUpdate = true
                currentValuation = updated
                continuation.yield(updated)
            }
        }

        if !receivedUpdate {
            self.sseNextRetryAt = Date().addingTimeInterval(self.sseRetryDelay)
        }
        return receivedUpdate
    }

    private func decodeValuation(from payload: String) -> FundValuation? {
        guard let data = payload.data(using: .utf8) else { return nil }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        if let direct = try? decoder.decode(FundValuation.self, from: data) {
            return direct
        }

        if let wrapped = try? decoder.decode(SSEFundValuationEnvelope.self, from: data) {
            return wrapped.data
        }
        return nil
    }
    
    /// 计算 2σ 统计边界
    /// 基于过去 30 天历史收益率的真实计算
    public func calculateThreshold2Sigma(history: [ValuationHistory]) -> Double {
        let returns = history.compactMap { $0.officialGrowth }
        guard returns.count > 5 else { return 1.5 } // 数据不足时返回经验值
        
        let mean = returns.reduce(0.0, +)
        let average = mean / Double(returns.count)
        let sumOfSquaredDiff = returns.map { pow($0 - average, 2.0) }.reduce(0.0, +)
        let standardDeviation = sqrt(sumOfSquaredDiff / Double(returns.count))
        
        return standardDeviation * 2.0
    }
}

private struct SSEFundValuationEnvelope: Decodable {
    let type: String?
    let data: FundValuation?
}

/// 补充 ValuationHistory 模型定义
public struct ValuationHistory: Codable {
    public let tradeDate: String
    public let frozenEstGrowth: Double?
    public let officialGrowth: Double?
    public let deviation: Double?
    public let trackingStatus: String?

    // Compatibility initializer for existing mock/test callers that still build history from date/growth.
    public init(date: Date, growth: Double) {
        let formatter = ISO8601DateFormatter()
        self.tradeDate = formatter.string(from: date)
        self.frozenEstGrowth = growth
        self.officialGrowth = growth
        self.deviation = 0
        self.trackingStatus = "A"
    }

    // Compatibility accessors for older call sites using the previous model shape.
    public var date: Date {
        let isoFormatter = ISO8601DateFormatter()
        if let parsed = isoFormatter.date(from: tradeDate) {
            return parsed
        }

        let dateOnlyFormatter = DateFormatter()
        dateOnlyFormatter.calendar = Calendar(identifier: .gregorian)
        dateOnlyFormatter.locale = Locale(identifier: "en_US_POSIX")
        dateOnlyFormatter.dateFormat = "yyyy-MM-dd"
        if let parsed = dateOnlyFormatter.date(from: tradeDate) {
            return parsed
        }

        return .distantPast
    }

    public var growth: Double { officialGrowth ?? 0 }
    
    enum CodingKeys: String, CodingKey {
        case tradeDate = "trade_date"
        case frozenEstGrowth = "frozen_est_growth"
        case officialGrowth = "official_growth"
        case deviation
        case trackingStatus = "tracking_status"
    }
}
