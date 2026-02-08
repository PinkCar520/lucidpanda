// mobile/ios/Packages/AlphaData/Sources/AlphaData/IntelligenceModels.swift
import Foundation

public struct IntelligenceItem: Codable, Identifiable, Hashable {
    public let id: Int
    public let timestamp: Date
    public let author: String
    public let summary: String
    public let content: String
    public let sentiment: String
    public let urgencyScore: Int
    public let goldPriceSnapshot: Double?
    
    // 手动定义的 public memberwise initializer
    public init(id: Int, timestamp: Date, author: String, summary: String, content: String, sentiment: String, urgencyScore: Int, goldPriceSnapshot: Double?) {
        self.id = id
        self.timestamp = timestamp
        self.author = author
        self.summary = summary
        self.content = content
        self.sentiment = sentiment
        self.urgencyScore = urgencyScore
        self.goldPriceSnapshot = goldPriceSnapshot
    }
    
    // 2026 生产级：支持多语言内容解析 (FastAPI 返回的可能是 JSON 对象)
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        author = try container.decode(String.self, forKey: .author)
        urgencyScore = try container.decode(Int.self, forKey: .urgencyScore)
        goldPriceSnapshot = try container.decodeIfPresent(Double.self, forKey: .goldPriceSnapshot)
        
        // 处理潜在的本地化 JSON 结构 (对齐 web/page.tsx 的 getLocalizedText)
        if let summaryDict = try? container.decode([String: String].self, forKey: .summary) {
            summary = summaryDict["zh"] ?? summaryDict["en"] ?? ""
        } else {
            summary = try container.decode(String.self, forKey: .summary)
        }
        
        if let contentDict = try? container.decode([String: String].self, forKey: .content) {
            content = contentDict["zh"] ?? contentDict["en"] ?? ""
        } else {
            content = try container.decode(String.self, forKey: .content)
        }
        
        if let sentimentDict = try? container.decode([String: String].self, forKey: .sentiment) {
            sentiment = sentimentDict["zh"] ?? sentimentDict["en"] ?? ""
        } else {
            sentiment = try container.decode(String.self, forKey: .sentiment)
        }
    }
    
    enum CodingKeys: String, CodingKey {
        case id, timestamp, author, summary, content, sentiment
        case urgencyScore = "urgency_score"
        case goldPriceSnapshot = "gold_price_snapshot"
    }
}

// SSE 事件包裹容器
public struct IntelligenceEvent: Codable {
    public let type: String
    public let data: [IntelligenceItem]?
}
