// mobile/ios/Packages/AlphaData/Sources/AlphaData/IntelligenceModels.swift
import Foundation

public struct IntelligenceItem: Codable, Identifiable, Hashable {
    public let id: Int
    public let timestamp: Date
    public let author: String
    public let summary: String
    public let content: String
    public let image_url: String?
    public let sentiment: String
    public let urgencyScore: Int
    public let goldPriceSnapshot: Double?
    
    // 新增：多品种市场快照
    public let dxySnapshot: Double?
    public let us10ySnapshot: Double?
    public let oilSnapshot: Double?
    
    // 新增：回测结果
    public let price15m: Double?
    public let price1h: Double?
    public let price4h: Double?
    public let price12h: Double?
    public let price24h: Double?

    // 快捷访问
    public var imageUrl: String? { image_url }

    // 手动定义的 public memberwise initializer
    public init(
        id: Int,
        timestamp: Date,
        author: String,
        summary: String,
        content: String,
        image_url: String? = nil,
        sentiment: String,
        urgencyScore: Int,
        goldPriceSnapshot: Double?,
        dxySnapshot: Double? = nil,
        us10ySnapshot: Double? = nil,
        oilSnapshot: Double? = nil,
        price15m: Double? = nil,
        price1h: Double? = nil,
        price4h: Double? = nil,
        price12h: Double? = nil,
        price24h: Double? = nil
    ) {
        self.id = id
        self.timestamp = timestamp
        self.author = author
        self.summary = summary
        self.content = content
        self.image_url = image_url
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

    // 2026 生产级：支持多语言内容解析 (FastAPI 返回的可能是 JSON 对象或扁平字符串)
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        timestamp = try container.decode(Date.self, forKey: .timestamp)
        author = try container.decode(String.self, forKey: .author)
        urgencyScore = try container.decode(Int.self, forKey: .urgencyScore)
        goldPriceSnapshot = try container.decodeIfPresent(Double.self, forKey: .goldPriceSnapshot)
        image_url = try container.decodeIfPresent(String.self, forKey: .image_url)
        
        dxySnapshot = try container.decodeIfPresent(Double.self, forKey: .dxySnapshot)
        us10ySnapshot = try container.decodeIfPresent(Double.self, forKey: .us10ySnapshot)
        oilSnapshot = try container.decodeIfPresent(Double.self, forKey: .oilSnapshot)
        price15m = try container.decodeIfPresent(Double.self, forKey: .price15m)
        price1h = try container.decodeIfPresent(Double.self, forKey: .price1h)
        price4h = try container.decodeIfPresent(Double.self, forKey: .price4h)
        price12h = try container.decodeIfPresent(Double.self, forKey: .price12h)
        price24h = try container.decodeIfPresent(Double.self, forKey: .price24h)

        // --- 核心修复：健壮性解码逻辑 ---
        
        let rawContainer = try decoder.container(keyedBy: DynamicCodingKeys.self)

        // 1. 解码 Summary (兼容 summary 字典或字符串)
        if let summaryDict = try? container.decode([String: String].self, forKey: .summary) {
            summary = summaryDict["zh"] ?? summaryDict["en"] ?? ""
        } else {
            summary = (try? container.decode(String.self, forKey: .summary)) ?? ""
        }

        // 2. 解码 Content (兼容 content 字典或字符串)
        if let contentDict = try? container.decode([String: String].self, forKey: .content) {
            content = contentDict["zh"] ?? contentDict["en"] ?? ""
        } else {
            content = (try? container.decode(String.self, forKey: .content)) ?? ""
        }

        // 3. 解码 Sentiment (尝试 sentiment_label -> sentiment 字典 -> sentiment 字符串)
        if let label = try? rawContainer.decode(String.self, forKey: DynamicCodingKeys(stringValue: "sentiment_label")!) {
            sentiment = label
        } else if let sentimentDict = try? rawContainer.decode([String: String].self, forKey: DynamicCodingKeys(stringValue: "sentiment")!) {
            sentiment = sentimentDict["zh"] ?? sentimentDict["en"] ?? "Neutral"
        } else {
            sentiment = (try? rawContainer.decode(String.self, forKey: DynamicCodingKeys(stringValue: "sentiment")!)) ?? "Neutral"
        }
    }

    enum CodingKeys: String, CodingKey {
        case id, timestamp, author, summary, content, image_url
        case sentiment = "sentiment_label" // 保持默认映射用于向后兼容
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
    
    // 用于动态键查找的辅助结构
    private struct DynamicCodingKeys: CodingKey {
        var stringValue: String
        init?(stringValue: String) { self.stringValue = stringValue }
        var intValue: Int?
        init?(intValue: Int) { return nil }
    }
}

// SSE 事件包裹容器
public struct IntelligenceEvent: Codable {
    public let type: String
    public let data: [IntelligenceItem]?
}
