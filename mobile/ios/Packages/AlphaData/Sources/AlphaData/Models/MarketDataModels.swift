// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/MarketDataModels.swift
import Foundation

// MARK: - Market Snapshot (后端 API 响应模型)

/// 市场快照数据（四大品种）
public struct MarketSnapshot: Codable {
    public let gold: MarketQuote
    public let dxy: MarketQuote
    public let oil: MarketQuote
    public let us10y: MarketQuote
    public let lastUpdated: Date
    
    enum CodingKeys: String, CodingKey {
        case gold, dxy, oil
        case us10y = "us10y"
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
public struct MarketPulseResponse: Codable {
    public let marketSnapshot: MarketSnapshot
    public let topAlerts: [MarketPulseAlert]
    public let overallSentiment: String
    public let overallSentimentZh: String
    public let sentimentScore: Double
    public let alertCount24h: Int
    public let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case marketSnapshot = "market_snapshot"
        case topAlerts = "top_alerts"
        case overallSentiment = "overall_sentiment"
        case overallSentimentZh = "overall_sentiment_zh"
        case sentimentScore = "sentiment_score"
        case alertCount24h = "alert_count_24h"
        case generatedAt = "generated_at"
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
}

// MARK: - Helper Extensions

extension MarketQuote {
    /// 获取涨跌颜色（iOS 红涨绿跌）
    public var changeColor: String {
        change >= 0 ? "rise" : "fall"
    }
    
    /// 格式化价格变化
    public var formattedChange: String {
        let sign = change >= 0 ? "+" : ""
        return String(format: "%@%.2f (%.2f%%)", sign, change, changePercent)
    }
}

extension MarketQuoteBar {
    /// 判断 K 线阴阳
    public var isBullish: Bool {
        close >= open
    }
}
