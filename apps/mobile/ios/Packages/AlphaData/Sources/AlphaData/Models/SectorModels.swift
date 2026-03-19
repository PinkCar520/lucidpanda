// mobile/ios/Packages/AlphaData/Sources/AlphaData/Models/SectorModels.swift
import Foundation

public struct SectorImpact: Codable, Identifiable {
    public var id: String { name }
    public let name: String
    public let weight: Double
    public let impact: Double
    
    public init(name: String, weight: Double, impact: Double) {
        self.name = name
        self.weight = weight
        self.impact = impact
    }
}
