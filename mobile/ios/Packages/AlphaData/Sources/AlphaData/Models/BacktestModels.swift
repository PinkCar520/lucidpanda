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
    
    public init(count: Int, winRate: Double, adjWinRate: Double, avgDrop: Double, hygiene: HygieneStats, correlation: [String: SessionWinRate], sessionStats: [SessionPerformance]) {
        self.count = count
        self.winRate = winRate
        self.adjWinRate = adjWinRate
        self.avgDrop = avgDrop
        self.hygiene = hygiene
        self.correlation = correlation
        self.sessionStats = sessionStats
    }
    
    public struct HygieneStats: Codable {
        public let avgClustering: Double
        public let avgExhaustion: Double
        
        public init(avgClustering: Double, avgExhaustion: Double) {
            self.avgClustering = avgClustering
            self.avgExhaustion = avgExhaustion
        }
    }
    
    public struct SessionWinRate: Codable {
        public let count: Int
        public let winRate: Double
        
        public init(count: Int, winRate: Double) {
            self.count = count
            self.winRate = winRate
        }
    }
    
    public struct SessionPerformance: Codable, Identifiable {
        public var id: String { session }
        public let session: String
        public let count: Int
        public let winRate: Double
        public let avgDrop: Double
        
        public init(session: String, count: Int, winRate: Double, avgDrop: Double) {
            self.session = session
            self.count = count
            self.winRate = winRate
            self.avgDrop = avgDrop
        }
    }
}
