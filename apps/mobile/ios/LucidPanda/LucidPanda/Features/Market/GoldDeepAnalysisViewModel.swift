import Foundation
import Observation
import AlphaCore
import AlphaData
import SwiftUI

@Observable
@MainActor
public class GoldDeepAnalysisViewModel {
    private let apiClient = APIClient.shared
    
    public var predictionData: GoldPredictionResponse?
    public var marketSnapshot: MarketSnapshot?
    public var isLoading = false
    public var selectedGranularity: String = "1h"
    
    // Bottom Metrics
    public var hitRate: Double = 0
    public var currentDeviation: Double = 0
    public var targetPrice: Double = 0
    public var predictedAtText: String = "—"
    
    // Header Info
    public var currentPriceText: String = "—"
    public var priceChangeText: String = ""
    public var isPriceUp: Bool = true
    
    public init() {}
    
    public func fetchPrediction() async {
        isLoading = true
        do {
            async let predictionTask: GoldPredictionResponse = apiClient.fetch(path: "/api/v1/mobile/gold/prediction?granularity=\(selectedGranularity)")
            async let snapshotTask: MarketSnapshot = apiClient.fetch(path: "/api/v1/mobile/market/snapshot")
            
            let (prediction, snapshot) = try await (predictionTask, snapshotTask)
            
            self.predictionData = prediction
            self.marketSnapshot = snapshot
            
            updateHeader(with: snapshot)
            calculateMetrics(from: prediction)
        } catch {
            print("Failed to fetch gold prediction or snapshot: \(error)")
        }
        isLoading = false
    }
    
    private func updateHeader(with snapshot: MarketSnapshot) {
        let gold = snapshot.gold
        self.currentPriceText = "$\(gold.price.formatted())"
        self.priceChangeText = gold.formattedChange
        self.isPriceUp = gold.change >= 0
    }
    
    private func calculateMetrics(from data: GoldPredictionResponse) {
        let prediction = data.prediction
        let history = data.history
        
        // 1. Predicted At
        let now = Date()
        let diff = now.timeIntervalSince(prediction.issuedAt)
        let hours = Int(diff / 3600)
        self.predictedAtText = "\(hours) 小时前"
        
        // 2. Hit Rate (Points within range)
        // Find historical points after issuedAt
        let actualAfterIssued = history.filter { $0.timestamp > prediction.issuedAt }
        var inRangeCount = 0
        
        for actual in actualAfterIssued {
            // Find corresponding prediction range
            // (Simple nearest neighbor or interpolation, here we just find exact match for demo)
            if let upper = prediction.upper.first(where: { abs($0.timestamp.timeIntervalSince(actual.timestamp)) < 1800 }),
               let lower = prediction.lower.first(where: { abs($0.timestamp.timeIntervalSince(actual.timestamp)) < 1800 }) {
                if actual.price >= lower.price && actual.price <= upper.price {
                    inRangeCount += 1
                }
            }
        }
        
        if !actualAfterIssued.isEmpty {
            self.hitRate = Double(inRangeCount) / Double(actualAfterIssued.isEmpty ? 1 : actualAfterIssued.count) * 100.0
        } else {
            self.hitRate = 100.0 // Default for new predictions
        }
        
        // 3. Current Deviation
        if let lastActual = history.last,
           let lastMid = prediction.mid.first(where: { abs($0.timestamp.timeIntervalSince(lastActual.timestamp)) < 1800 }) {
            self.currentDeviation = lastActual.price - lastMid.price
        }
        
        // 4. Target Price
        self.targetPrice = prediction.mid.last?.price ?? 0
    }
}
