// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/BacktestModels.swift
import Foundation

public struct BacktestStats: Codable {
    public let count: Int
    public let winRate: Double
    public let adjWinRate: Double
    public let avgDrop: Double
    public let hygiene: HygieneStats
    public let correlation: [String: SessionWinRate]
    public let positioning: [String: SessionWinRate]?
    public let volatility: [String: SessionWinRate]?
    public let distribution: [DistributionBin]?
    public let sessionStats: [SessionPerformance]
    public let items: [BacktestItem]?
    
    public init(count: Int, winRate: Double, adjWinRate: Double, avgDrop: Double, hygiene: HygieneStats, correlation: [String: SessionWinRate], positioning: [String: SessionWinRate]? = nil, volatility: [String: SessionWinRate]? = nil, distribution: [DistributionBin]? = nil, sessionStats: [SessionPerformance], items: [BacktestItem]? = nil) {
        self.count = count
        self.winRate = winRate
        self.adjWinRate = adjWinRate
        self.avgDrop = avgDrop
        self.hygiene = hygiene
        self.correlation = correlation
        self.positioning = positioning
        self.volatility = volatility
        self.distribution = distribution
        self.sessionStats = sessionStats
        self.items = items
    }
    
    public struct HygieneStats: Codable {
        public let avgClustering: Double
        public let avgExhaustion: Double
        public let avgDxy: Double?
        public let avgUs10y: Double?
        public let avgGvz: Double?
        
        public init(avgClustering: Double, avgExhaustion: Double, avgDxy: Double? = nil, avgUs10y: Double? = nil, avgGvz: Double? = nil) {
            self.avgClustering = avgClustering
            self.avgExhaustion = avgExhaustion
            self.avgDxy = avgDxy
            self.avgUs10y = avgUs10y
            self.avgGvz = avgGvz
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
    
    public struct DistributionBin: Codable, Identifiable {
        public var id: Double { bin }
        public let bin: Double
        public let count: Int
        
        public init(bin: Double, count: Int) {
            self.bin = bin
            self.count = count
        }
    }
    
    public struct BacktestItem: Codable, Identifiable {
        public let id: Int
        public let title: String
        public let timestamp: Date
        public let score: Int
        public let entry: Double
        public let exit: Double
        public let isWin: Bool
        public let changePct: Double
        
        public init(id: Int, title: String, timestamp: Date, score: Int, entry: Double, exit: Double, isWin: Bool, changePct: Double) {
            self.id = id
            self.title = title
            self.timestamp = timestamp
            self.score = score
            self.entry = entry
            self.exit = exit
            self.isWin = isWin
            self.changePct = changePct
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            id = try container.decode(Int.self, forKey: .id)
            timestamp = try container.decode(Date.self, forKey: .timestamp)
            score = try container.decode(Int.self, forKey: .score)
            entry = try container.decode(Double.self, forKey: .entry)
            exit = try container.decode(Double.self, forKey: .exit)
            isWin = try container.decode(Bool.self, forKey: .isWin)
            changePct = try container.decode(Double.self, forKey: .changePct)

            if let plainTitle = try? container.decode(String.self, forKey: .title), !plainTitle.isEmpty {
                title = plainTitle
            } else if let localizedTitle = try? container.decode([String: String].self, forKey: .title) {
                title = localizedTitle["zh"] ?? localizedTitle["en"] ?? localizedTitle.values.first ?? ""
            } else {
                title = ""
            }
        }
        
        enum CodingKeys: String, CodingKey {
            case id, title, timestamp, score, entry, exit
            case isWin = "is_win"
            case changePct = "change_pct"
        }
    }
}
