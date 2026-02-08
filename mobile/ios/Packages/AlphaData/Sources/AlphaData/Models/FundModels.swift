// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/FundModels.swift
import Foundation

public struct FundComponent: Codable, Identifiable {
    public var id: String { code }
    public let code: String
    public let name: String
    public let weight: Double
    public let changePct: Double
    public let impact: Double
    
    enum CodingKeys: String, CodingKey {
        case code, name, weight, impact
        case changePct = "change_pct"
    }
}

public struct FundValuation: Codable, Identifiable {
    public var id: String { fundCode }
    public let fundCode: String
    public let fundName: String
    public let estimatedGrowth: Double
    public let totalWeight: Double
    public let components: [FundComponent]
    public let timestamp: Date
    
    enum CodingKeys: String, CodingKey {
        case fundCode = "fund_code"
        case fundName = "fund_name"
        case estimatedGrowth = "estimated_growth"
        case totalWeight = "total_weight"
        case components, timestamp
    }
}
