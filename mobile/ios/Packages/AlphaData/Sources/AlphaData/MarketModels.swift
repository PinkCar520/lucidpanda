// mobile/ios/Packages/AlphaData/Sources/AlphaData/MarketModels.swift
import Foundation

public struct MarketDataPoint: Codable, Identifiable, Hashable {
    public var id: Double { timestamp }
    public let timestamp: Double
    public let price: Double
    
    public init(timestamp: Double, price: Double) {
        self.timestamp = timestamp
        self.price = price
    }
    
    public var date: Date {
        Date(timeIntervalSince1970: timestamp)
    }
}

public struct MarketResponse: Codable {
    public let symbol: String
    public let data: [MarketDataPoint]
    
    public init(symbol: String, data: [MarketDataPoint]) {
        self.symbol = symbol
        self.data = data
    }
}
