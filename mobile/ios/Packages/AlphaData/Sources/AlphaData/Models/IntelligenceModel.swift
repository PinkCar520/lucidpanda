// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/IntelligenceModel.swift
import Foundation
import SwiftData

@Model
public final class IntelligenceModel {
    @Attribute(.unique) public var id: Int
    public var timestamp: Date
    public var author: String
    public var summary: String
    public var content: String
    public var sentiment: String
    public var urgencyScore: Int
    public var goldPriceSnapshot: Double?
    
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
    
    // 从 DTO 转换的便捷方法
    public convenience init(from dto: IntelligenceItem) {
        self.init(
            id: dto.id,
            timestamp: dto.timestamp,
            author: dto.author,
            summary: dto.summary,
            content: dto.content,
            sentiment: dto.sentiment,
            urgencyScore: dto.urgencyScore,
            goldPriceSnapshot: dto.goldPriceSnapshot
        )
    }
}
