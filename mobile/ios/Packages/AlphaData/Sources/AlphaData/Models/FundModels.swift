// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/FundModels.swift
import Foundation

public struct FundComponent: Codable, Identifiable {
    public var id: String { code }
    public let code: String
    public let name: String
    public let weight: Double
    public let changePct: Double
    public let impact: Double
    
    public init(code: String, name: String, weight: Double, changePct: Double, impact: Double) {
        self.code = code
        self.name = name
        self.weight = weight
        self.changePct = changePct
        self.impact = impact
    }
    
    enum CodingKeys: String, CodingKey {
        case code, name, weight, impact
        case changePct = "change_pct"
    }
}

public struct FundStats: Codable {
    public let return1w: Double?
    public let return1m: Double?
    public let return3m: Double?
    public let return1y: Double?
    public let sharpeRatio: Double?
    public let sharpeGrade: String?
    public let maxDrawdown: Double?
    public let drawdownGrade: String?
    public let volatility: Double?
    public let sparklineData: [Double]?

    public init(return1w: Double?, return1m: Double?, return3m: Double?, return1y: Double?, sharpeRatio: Double?, sharpeGrade: String?, maxDrawdown: Double?, drawdownGrade: String?, volatility: Double?, sparklineData: [Double]?) {
        self.return1w = return1w
        self.return1m = return1m
        self.return3m = return3m
        self.return1y = return1y
        self.sharpeRatio = sharpeRatio
        self.sharpeGrade = sharpeGrade
        self.maxDrawdown = maxDrawdown
        self.drawdownGrade = drawdownGrade
        self.volatility = volatility
        self.sparklineData = sparklineData
    }

    enum CodingKeys: String, CodingKey {
        case return1w = "return_1w"
        case return1m = "return_1m"
        case return3m = "return_3m"
        case return1y = "return_1y"
        case sharpeRatio = "sharpe_ratio"
        case sharpeGrade = "sharpe_grade"
        case maxDrawdown = "max_drawdown"
        case drawdownGrade = "drawdown_grade"
        case volatility
        case sparklineData = "sparkline_data"
    }
}

public struct FundConfidence: Codable {
    public let level: String // "high", "medium", "low"
    public let score: Int
    public let isSuspectedRebalance: Bool?
    public let reasons: [String]?

    public init(level: String, score: Int, isSuspectedRebalance: Bool?, reasons: [String]?) {
        self.level = level
        self.score = score
        self.isSuspectedRebalance = isSuspectedRebalance
        self.reasons = reasons
    }

    enum CodingKeys: String, CodingKey {
        case level, score, reasons
        case isSuspectedRebalance = "is_suspected_rebalance"
    }
}

public struct SubSectorStat: Codable {
    public let impact: Double
    public let weight: Double
    
    public init(impact: Double, weight: Double) {
        self.impact = impact
        self.weight = weight
    }
}

public struct SectorStat: Codable {
    public let impact: Double
    public let weight: Double
    public let sub: [String: SubSectorStat]?
    
    public init(impact: Double, weight: Double, sub: [String: SubSectorStat]?) {
        self.impact = impact
        self.weight = weight
        self.sub = sub
    }
}

public struct FundValuation: Codable, Identifiable, Hashable, Equatable {
    public var id: String { fundCode }
    public let fundCode: String
    public let fundName: String
    public let estimatedGrowth: Double
    public let totalWeight: Double
    public let components: [FundComponent]
    public let timestamp: Date
    public let isQdii: Bool?
    public let confidence: FundConfidence?
    public let riskLevel: String?
    public let marketStatus: String?
    public let stats: FundStats?
    public let sectorAttribution: [String: SectorStat]?
    
    public init(fundCode: String, fundName: String, estimatedGrowth: Double, totalWeight: Double, components: [FundComponent], timestamp: Date, isQdii: Bool? = nil, confidence: FundConfidence? = nil, riskLevel: String? = nil, marketStatus: String? = nil, stats: FundStats? = nil, sectorAttribution: [String: SectorStat]? = nil) {
        self.fundCode = fundCode
        self.fundName = fundName
        self.estimatedGrowth = estimatedGrowth
        self.totalWeight = totalWeight
        self.components = components
        self.timestamp = timestamp
        self.isQdii = isQdii
        self.confidence = confidence
        self.riskLevel = riskLevel
        self.marketStatus = marketStatus
        self.stats = stats
        self.sectorAttribution = sectorAttribution
    }
    
    enum CodingKeys: String, CodingKey {
        case fundCode = "fund_code"
        case fundName = "fund_name"
        case estimatedGrowth = "estimated_growth"
        case totalWeight = "total_weight"
        case isQdii = "is_qdii"
        case riskLevel = "risk_level"
        case marketStatus = "market_status"
        case sectorAttribution = "sector_attribution"
        case components, timestamp, confidence, stats
    }
    
    // MARK: - Hashable & Equatable
    public static func == (lhs: FundValuation, rhs: FundValuation) -> Bool {
        return lhs.fundCode == rhs.fundCode
    }
    
    public func hash(into hasher: inout Hasher) {
        hasher.combine(fundCode)
    }
}

// MARK: - Fund AI Analysis (长按弹窗 AI 分析)

/// 基金 AI 市场分析响应
public struct FundAIAnalysisResponse: Codable {
    public let fundCode: String
    public let fundName: String
    public let hasIntelligence: Bool
    public let isFallback: Bool?
    public let fallbackSource: String?
    public let topAdvice: String?
    public let relatedIntelligence: [FundRelatedIntelligence]
    public let marketSnapshot: MarketSnapshot?
    public let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case fundCode = "fund_code"
        case fundName = "fund_name"
        case hasIntelligence = "has_intelligence"
        case isFallback = "is_fallback"
        case fallbackSource = "fallback_source"
        case topAdvice = "top_advice"
        case relatedIntelligence = "related_intelligence"
        case marketSnapshot = "market_snapshot"
        case generatedAt = "generated_at"
    }
}

/// 基金关联情报摘要
public struct FundRelatedIntelligence: Codable, Identifiable {
    public let id: Int
    public let timestamp: Date
    public let author: String?
    public let urgencyScore: Int
    public let summary: String
    public let advice: String?
    public let sentiment: String

    enum CodingKeys: String, CodingKey {
        case id, timestamp, author, summary, advice, sentiment
        case urgencyScore = "urgency_score"
    }
}
