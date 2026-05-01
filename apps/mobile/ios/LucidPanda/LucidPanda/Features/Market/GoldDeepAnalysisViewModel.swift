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
    public var directionAccuracy: Double = 0
    public var historicalAccuracy: Double = 0
    public var currentDeviation: Double = 0
    public var targetPrice: Double = 0
    public var predictedAtText: String = "—"
    
    // Header Info
    public var currentPriceText: String = "—"
    public var priceChangeText: String = ""
    public var isPriceUp: Bool = true
    
    public init() {}
    
    public func fetchInitialData() async {
        // Run them in parallel but they are independent
        async let marketTask = fetchMarketData()
        async let predictionTask = fetchPrediction(forceRefresh: false)
        _ = await (marketTask, predictionTask)
    }
    
    public func fetchMarketData() async {
        do {
            let snapshot: MarketSnapshot = try await apiClient.fetch(path: "/api/v1/mobile/market/snapshot")
            self.marketSnapshot = snapshot
            updateHeader(with: snapshot)
        } catch {
            print("Failed to fetch gold market snapshot: \(error)")
        }
    }
    
    public func fetchPrediction(forceRefresh: Bool = false) async {
        isLoading = true
        do {
            let path = "/api/v1/mobile/gold/prediction?granularity=\(selectedGranularity)\(forceRefresh ? "&force_refresh=true" : "")"
            let prediction: GoldPredictionResponse = try await apiClient.fetch(path: path)
            self.predictionData = prediction
            calculateMetrics(from: prediction)
        } catch {
            print("Failed to fetch gold prediction (force=\(forceRefresh)): \(error)")
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
        
        // 1. Predicted At (Now using generatedAt, the real execution time)
        let now = Date()
        let refDate = data.generatedAt ?? prediction.issuedAt
        let diff = now.timeIntervalSince(refDate)
        let minutes = Int(diff / 60)
        
        if minutes < 1 {
            self.predictedAtText = "刚刚"
        } else if minutes < 60 {
            self.predictedAtText = "\(minutes) 分钟前"
        } else {
            let hours = Int(minutes / 60)
            self.predictedAtText = "\(hours) 小时前"
        }
        
        // 2. Hit Rate (Points within range)
        // Find historical points after issuedAt (The chart pivot)
        let actualAfterIssued = history.filter { $0.timestamp > prediction.issuedAt }
        var inRangeCount = 0
        
        for actual in actualAfterIssued {
            if let upper = prediction.upper.first(where: { abs($0.timestamp.timeIntervalSince(actual.timestamp)) < 1800 }),
               let lower = prediction.lower.first(where: { abs($0.timestamp.timeIntervalSince(actual.timestamp)) < 1800 }) {
                if actual.price >= lower.price && actual.price <= upper.price {
                    inRangeCount += 1
                }
            }
        }
        
        if !actualAfterIssued.isEmpty {
            self.hitRate = Double(inRangeCount) / Double(actualAfterIssued.count) * 100.0
        } else {
            self.hitRate = 100.0 // Default for new predictions
        }

        // 3. Direction Accuracy & Historical Accuracy (Correct direction & Precise hit)
        if let pivotPoint = history.last(where: { $0.timestamp <= prediction.issuedAt }) {
            let actualAfter = history.filter { $0.timestamp > prediction.issuedAt }
            var correctDirectionCount = 0
            var perfectHitCount = 0
            
            for actual in actualAfter {
                if let mid = prediction.mid.first(where: { abs($0.timestamp.timeIntervalSince(actual.timestamp)) < 1800 }) {
                    let actualChange = actual.price - pivotPoint.price
                    let predictedChange = mid.price - pivotPoint.price
                    
                    // 方向判定：涨跌方向一致
                    let isDirectionMatch = (actualChange > 0 && predictedChange > 0) ||
                                           (actualChange < 0 && predictedChange < 0) ||
                                           (abs(actualChange) < 0.01 && abs(predictedChange) < 0.01)
                    
                    if isDirectionMatch {
                        correctDirectionCount += 1
                        
                        // 历史准确率：方向正确且点位偏差 <= $3.0 (高标准)
                        if abs(actual.price - mid.price) <= 3.0 {
                            perfectHitCount += 1
                        }
                    }
                }
            }
            
            if !actualAfter.isEmpty {
                self.directionAccuracy = Double(correctDirectionCount) / Double(actualAfter.count) * 100.0
                self.historicalAccuracy = Double(perfectHitCount) / Double(actualAfter.count) * 100.0
            } else {
                self.directionAccuracy = 100.0
                self.historicalAccuracy = 100.0
            }
        }
        
        // 4. Current Deviation
        if let lastActual = history.last,
           let lastMid = prediction.mid.first(where: { abs($0.timestamp.timeIntervalSince(lastActual.timestamp)) < 1800 }) {
            self.currentDeviation = lastActual.price - lastMid.price
        }
        
        // 5. Target Price
        self.targetPrice = prediction.mid.last?.price ?? 0
    }
}
