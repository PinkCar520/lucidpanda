// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/BacktestModels.swift
import Foundation

public struct BacktestStats: Codable {
    public let count: Int
    public let winRate: Double
    public let adjWinRate: Double
    public let avgDrop: Double
    public let hygiene: HygieneStats
    public let correlation: [String: SessionWinRate]
    public let sessionStats: [SessionPerformance]
    
    public struct HygieneStats: Codable {
        public let avgClustering: Double
        public let avgExhaustion: Double
    }
    
    public struct SessionWinRate: Codable {
        public let count: Int
        public let winRate: Double
    }
    
    public struct SessionPerformance: Codable, Identifiable {
        public var id: String { session }
        public let session: String
        public let count: Int
        public let winRate: Double
        public let avgDrop: Double
    }
}
