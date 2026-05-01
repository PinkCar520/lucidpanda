// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/MarketDataModels.swift
import Foundation

// MARK: - Market Snapshot (后端 API 响应模型)

/// 市场快照数据（四大品种）
public struct MarketSnapshot: Codable {
    public let gold: MarketQuote
    public let goldCny: MarketQuote?
    public let dxy: MarketQuote
    public let oil: MarketQuote
    public let us10y: MarketQuote
    public let shIndex: MarketQuote?
    public let szIndex: MarketQuote?
    public let lastUpdated: Date
    
    enum CodingKeys: String, CodingKey {
        case gold, dxy, oil
        case goldCny = "gold_cny"
        case us10y = "us10y"
        case shIndex = "sh_index"
        case szIndex = "sz_index"
        case lastUpdated = "last_updated"
    }
}

/// 单个品种报价
public struct MarketQuote: Codable {
    public let symbol: String
    public let name: String
    public let price: Double
    public let change: Double
    public let changePercent: Double
    public let high24h: Double?
    public let low24h: Double?
    public let open: Double?
    public let previousClose: Double?
    public let timestamp: Date?
    
    public init(symbol: String, name: String, price: Double, change: Double, changePercent: Double, high24h: Double?, low24h: Double?, open: Double?, previousClose: Double?, timestamp: Date?) {
        self.symbol = symbol
        self.name = name
        self.price = price
        self.change = change
        self.changePercent = changePercent
        self.high24h = high24h
        self.low24h = low24h
        self.open = open
        self.previousClose = previousClose
        self.timestamp = timestamp
    }

    enum CodingKeys: String, CodingKey {
        case symbol, name, price, change
        case changePercent = "changePercent"
        case high24h = "high_24h"
        case low24h = "low_24h"
        case open, previousClose = "previous_close"
        case timestamp
    }
}

// MARK: - Market Chart Data (K 线图数据)

/// K 线图响应
public struct MarketChartData: Codable {
    public let symbol: String
    public let quotes: [MarketQuoteBar]
    public let indicators: MarketIndicators?

    public init(symbol: String, quotes: [MarketQuoteBar], indicators: MarketIndicators? = nil) {
        self.symbol = symbol
        self.quotes = quotes
        self.indicators = indicators
    }

    enum CodingKeys: String, CodingKey {
        case symbol, quotes, indicators
    }
}

/// 单根 K 线
public struct MarketQuoteBar: Codable, Identifiable {
    public let id = UUID()
    public let date: Date
    public let open: Double
    public let high: Double
    public let low: Double
    public let close: Double
    public let volume: Double?

    public init(date: Date, open: Double, high: Double, low: Double, close: Double, volume: Double? = nil) {
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
    }

    enum CodingKeys: String, CodingKey {
        case date, open, high, low, close, volume
    }
}

/// 市场指标（黄金价差等）
public struct MarketIndicators: Codable {
    public let domesticSpot: Double?
    public let intlSpotCny: Double?
    public let spread: Double?
    public let spreadPct: Double?
    public let fxRate: Double?
    public let lastUpdated: Date?
    
    enum CodingKeys: String, CodingKey {
        case domesticSpot = "domestic_spot"
        case intlSpotCny = "intl_spot_cny"
        case spread, spreadPct = "spread_pct"
        case fxRate = "fx_rate"
        case lastUpdated = "last_updated"
    }
}

// MARK: - Intelligence with Market Context (情报关联市场数据)

/// 市场情报项（扩展版，包含多品种快照）
public struct MarketIntelligenceItem: Codable, Identifiable {
    public let id: Int
    public let timestamp: Date
    public let author: String
    public let summary: String
    public let content: String
    public let sentiment: String
    public let urgencyScore: Int
    
    // 市场快照（多品种）
    public let goldPriceSnapshot: Double?
    public let dxySnapshot: Double?
    public let us10ySnapshot: Double?
    public let oilSnapshot: Double?
    
    // 回测结果
    public let price15m: Double?
    public let price1h: Double?
    public let price4h: Double?
    public let price12h: Double?
    public let price24h: Double?
    
    public init(
        id: Int,
        timestamp: Date,
        author: String,
        summary: String,
        content: String,
        sentiment: String,
        urgencyScore: Int,
        goldPriceSnapshot: Double?,
        dxySnapshot: Double?,
        us10ySnapshot: Double?,
        oilSnapshot: Double?,
        price15m: Double?,
        price1h: Double?,
        price4h: Double?,
        price12h: Double?,
        price24h: Double?
    ) {
        self.id = id
        self.timestamp = timestamp
        self.author = author
        self.summary = summary
        self.content = content
        self.sentiment = sentiment
        self.urgencyScore = urgencyScore
        self.goldPriceSnapshot = goldPriceSnapshot
        self.dxySnapshot = dxySnapshot
        self.us10ySnapshot = us10ySnapshot
        self.oilSnapshot = oilSnapshot
        self.price15m = price15m
        self.price1h = price1h
        self.price4h = price4h
        self.price12h = price12h
        self.price24h = price24h
    }
    
    enum CodingKeys: String, CodingKey {
        case id, timestamp, author, summary, content
        case sentiment = "sentiment_label"
        case urgencyScore = "urgency_score"
        case goldPriceSnapshot = "gold_price_snapshot"
        case dxySnapshot = "dxy_snapshot"
        case us10ySnapshot = "us10y_snapshot"
        case oilSnapshot = "oil_snapshot"
        case price15m = "price_15m"
        case price1h = "price_1h"
        case price4h = "price_4h"
        case price12h = "price_12h"
        case price24h = "price_24h"
    }
}

// MARK: - Dashboard Summary (仪表盘摘要)

/// 移动端仪表盘摘要响应
public struct MobileDashboardSummary: Codable {
    public let marketStatus: String
    public let watchlist: [String]  // 简化为数组，避免依赖 FundMobileSummary
    public let criticalAlerts: [MarketIntelligenceItem]
    public let marketSnapshot: MarketSnapshot?
    
    enum CodingKeys: String, CodingKey {
        case marketStatus = "market_status"
        case watchlist, criticalAlerts = "critical_alerts"
        case marketSnapshot = "market_snapshot"
    }
}

// MARK: - Market Pulse (悬浮胶囊数据)

/// 宏观市场脉搏响应
/// 宏观日历事件 (用于 Market Pulse)
public struct MarketPulseEvent: Codable, Identifiable {
    public let id: String
    public let title: String
    public let country: String
    public let date: String
    public let time: String?
    public let impact: String
    public let forecast: String?
    public let previous: String?
}

public struct MarketPulseResponse: Codable {
    public let marketSnapshot: MarketSnapshot
    public let topAlerts: [MarketPulseAlert]
    public let upcomingEvents: [MarketPulseEvent]?
    public let overallSentiment: String
    public let overallSentimentZh: String
    public let sentimentScore: Double
    public let sentimentTrend: [SentimentTrendPoint]?
    public let goldTrend: [GoldTrendPoint]?
    public let alertCount24h: Int
    public let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case marketSnapshot = "market_snapshot"
        case topAlerts = "top_alerts"
        case upcomingEvents = "upcoming_events"
        case overallSentiment = "overall_sentiment"
        case overallSentimentZh = "overall_sentiment_zh"
        case sentimentScore = "sentiment_score"
        case sentimentTrend = "sentiment_trend"
        case goldTrend = "gold_trend"
        case alertCount24h = "alert_count_24h"
        case generatedAt = "generated_at"
    }
}

/// 黄金走势数据点（包含 AI 预测）
public struct GoldTrendPoint: Codable, Identifiable {
    public var id: Date { timestamp }
    public let timestamp: Date
    public let price: Double
    public let isForecast: Bool

    public init(timestamp: Date, price: Double, isForecast: Bool) {
        self.timestamp = timestamp
        self.price = price
        self.isForecast = isForecast
    }

    enum CodingKeys: String, CodingKey {
        case timestamp, price
        case isForecast = "is_forecast"
    }
}

/// 脉搏中的高紧急度情报摘要
public struct MarketPulseAlert: Codable, Identifiable {
    public let id: Int
    public let timestamp: Date
    public let urgencyScore: Int
    public let summary: String
    public let sentiment: String

    enum CodingKeys: String, CodingKey {
        case id, timestamp, summary, sentiment
        case urgencyScore = "urgency_score"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        urgencyScore = try container.decode(Int.self, forKey: .urgencyScore)
        sentiment = try container.decode(String.self, forKey: .sentiment)

        if let summaryText = try? container.decode(String.self, forKey: .summary) {
            summary = summaryText
        } else if let summaryDict = try? container.decode([String: String].self, forKey: .summary) {
            summary = summaryDict["zh"] ?? summaryDict["en"] ?? summaryDict.values.first ?? ""
        } else {
            summary = ""
        }
    }
}

/// 情绪趋势数据点
public struct SentimentTrendPoint: Codable, Identifiable {
    public var id: Date { hour }
    public let hour: Date
    public let score: Double

    public init(hour: Date, score: Double) {
        self.hour = hour
        self.score = score
    }
}

// MARK: - Market Timechain (事件脉络)

public struct MarketTimechainResponse: Codable {
    public let theme_title: String
    public let ai_summary: String
    public let timeline: [TimechainEvent]
    public let generated_at: String?
}

public struct TimechainEvent: Codable, Identifiable {
    public var id: String { "\(date)-\(event)" }
    public let date: String
    public let event: String
    public let impact: String
    public let reasoning: String? // 因果逻辑说明
    public let sentiment: String // bullish, bearish, neutral
}

// MARK: - Gold Prediction (PRD v1.0)

public struct GoldPricePoint: Codable, Identifiable, Hashable {
    public var id: Date { timestamp }
    public let timestamp: Date
    public let price: Double
    
    public init(timestamp: Date, price: Double) {
        self.timestamp = timestamp
        self.price = price
    }
}

public struct GoldPredictionResponse: Codable {
    public let history: [GoldTrendPoint]
    public let prediction: GoldPredictionDetail
    public let generatedAt: Date?
    public let granularity: String?
    
    public init(history: [GoldTrendPoint], prediction: GoldPredictionDetail, generatedAt: Date?, granularity: String?) {
        self.history = history
        self.prediction = prediction
        self.generatedAt = generatedAt
        self.granularity = granularity
    }
}

public struct GoldPredictionDetail: Codable {
    public let issuedAt: Date
    public let mid: [GoldPricePoint]
    public let upper: [GoldPricePoint]
    public let lower: [GoldPricePoint]
    
    public init(issuedAt: Date, mid: [GoldPricePoint], upper: [GoldPricePoint], lower: [GoldPricePoint]) {
        self.issuedAt = issuedAt
        self.mid = mid
        self.upper = upper
        self.lower = lower
    }
}

// MARK: - Sina Finance External Data (Minute Line)

/// 新浪财经伦敦金分时线原始响应
public struct SinaGoldMinLineResponse: Codable {
    public let minLine1d: [[String]]

    enum CodingKeys: String, CodingKey {
        case minLine1d = "minLine_1d"
    }
    
    /// 将新浪非对称数组转换为标准的 GoldTrendPoint
    public func toTrendPoints() -> [GoldTrendPoint] {
        var points: [GoldTrendPoint] = []
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.timeZone = TimeZone(identifier: "Asia/Shanghai") // 新浪数据通常为北京时间

        for (index, rawArray) in minLine1d.enumerated() {
            // 第一个元素有 10 个字段，后续有 6 个字段
            // 最后一个字段都是完整的时间戳 "yyyy-MM-dd HH:mm:ss"
            guard let lastString = rawArray.last,
                  let date = formatter.date(from: lastString) else {
                continue
            }
            
            // 价格字段：第一个元素在 index 5，后续在 index 1
            // ⚠️ 核心修正：新浪 XAU 原始数据是标准金价的 2 倍 (双倍合约价格)，此处需归一化
            let priceIndex = (index == 0) ? 5 : 1
            guard rawArray.count > priceIndex,
                  let rawPrice = Double(rawArray[priceIndex]) else {
                continue
            }
            
            let normalizedPrice = rawPrice
            points.append(GoldTrendPoint(timestamp: date, price: normalizedPrice, isForecast: false))
        }
        return points
    }
}

// MARK: - Helper Extensions

extension MarketQuote {
    /// 获取涨跌颜色（iOS 红涨绿跌）
    public var changeColor: String {
        change >= 0 ? "rise" : "fall"
    }
    
    /// 格式化价格变化
    public var formattedChange: String {
        let formattedPrice = String(format: "%.2f", change)
        let formattedPct = String(format: "%.2f", changePercent)
        
        let priceSign = (change > 0 || (change == 0 && !formattedPrice.contains("-"))) ? "+" : ""
        let pctSign = (changePercent > 0 || (changePercent == 0 && !formattedPct.contains("-"))) ? "+" : ""
        
        return String(format: "%@%@ (%@%@%%)", priceSign, formattedPrice, pctSign, formattedPct)
    }
}

extension MarketQuoteBar {
    /// 判断 K 线阴阳
    public var isBullish: Bool {
        close >= open
    }
}
