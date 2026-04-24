import Foundation

public struct DiscoverResponse: Codable {
    public let trendingTags: [TrendingTagDTO]
    public let suggestedReading: [SuggestedReadingDTO]
    
    enum CodingKeys: String, CodingKey {
        case trendingTags = "trending_tags"
        case suggestedReading = "suggested_reading"
    }
}

public struct TrendingTagDTO: Codable, Identifiable {
    public var id: String { code }
    public let title: String
    public let code: String
}

public struct SuggestedReadingDTO: Codable, Identifiable {
    public let id: Int
    public let categoryKey: String
    public let title: String
    public let timestamp: Date
    public let imageUrl: String
    
    enum CodingKeys: String, CodingKey {
        case id
        case categoryKey = "category_key"
        case title
        case timestamp
        case imageUrl
    }
}
