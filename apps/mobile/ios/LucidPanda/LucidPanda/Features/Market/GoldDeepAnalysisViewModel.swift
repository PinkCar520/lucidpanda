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
    public var isLoading = false
    public var selectedGranularity: String = "1m"
    
    // Bottom Metrics
    public var hitRate: Double?
    public var directionAccuracy: Double?
    public var historicalAccuracy: Double?
    public var currentDeviation: Double?
    public var targetPrice: Double = 0
    public var predictedAtText: String = "—"
    
    // Task Management
    private var predictionFetchTask: Task<Void, Never>?
    
    public init() {}
    
    public func fetchInitialData() async {
        await fetchPrediction(forceRefresh: false)
    }
    
    public func fetchPrediction(forceRefresh: Bool = false) async {
        predictionFetchTask?.cancel()
        
        predictionFetchTask = Task {
            isLoading = true
            defer { isLoading = false }
            
            do {
                // 1. Fetch internal prediction
                let path = "/api/v1/mobile/gold/prediction?granularity=\(selectedGranularity)\(forceRefresh ? "&force_refresh=true" : "")"
                var prediction: GoldPredictionResponse = try await apiClient.fetch(path: path)
                
                // 2. Fetch external high-fidelity history from Sina (if granularity is intraday style)
                if selectedGranularity != "1d" {
                    let sinaHistory = await fetchSinaHistory()
                    if !sinaHistory.isEmpty {
                        // Use Sina's points as the authoritative history
                        // But keep prediction issuedAt and future points
                        prediction = GoldPredictionResponse(
                            history: sinaHistory,
                            prediction: prediction.prediction,
                            generatedAt: prediction.generatedAt,
                            granularity: prediction.granularity,
                            marketStatus: prediction.marketStatus
                        )
                    }
                }
                
                if !Task.isCancelled {
                    let isInitialLoad = self.predictionData == nil
                    self.predictionData = prediction
                    
                    // 休市感知：如果是初次加载且检测到休市，自动切换到 1D 视图
                    if isInitialLoad && prediction.marketStatus == "CLOSED" {
                        self.selectedGranularity = "1d"
                        // 重新发起一次 1D 的非强制刷新请求
                        Task { await self.fetchPrediction(forceRefresh: false) }
                    }
                    
                    calculateMetrics(from: prediction)
                }
            } catch {
                if isCancelledError(error) {
                    // Silent on cancellation: User pulled to refresh or closed the sheet
                } else {
                    print("Failed to fetch gold prediction (force=\(forceRefresh)): \(error)")
                }
            }
        }
        
        await predictionFetchTask?.value
    }

    /// 从新浪财经拉取高精度分时历史数据
    public func fetchSinaHistory() async -> [GoldTrendPoint] {
        let urlString = "https://stock.finance.sina.com.cn/futures/api/json_v2.php/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"
        guard let url = URL(string: urlString) else { return [] }
        
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let response = try JSONDecoder().decode(SinaGoldMinLineResponse.self, from: data)
            return response.toTrendPoints()
        } catch {
            print("❌ Failed to fetch Sina history: \(error)")
            return []
        }
    }

    private func isCancelledError(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        let nsError = error as NSError
        if nsError.domain == NSURLErrorDomain && nsError.code == -999 { return true }
        if nsError.domain == NSURLErrorDomain && nsError.code == URLError.cancelled.rawValue { return true }
        return false
    }
    
    private func calculateMetrics(from data: GoldPredictionResponse) {
        let prediction = data.prediction
        let history = data.history
        
        // 1. Predicted At (Now using RelativeDateTimeFormatter for localization)
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        self.predictedAtText = formatter.localizedString(for: data.generatedAt ?? prediction.issuedAt, relativeTo: Date())
        
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
            self.hitRate = nil
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
                self.directionAccuracy = nil
                self.historicalAccuracy = nil
            }
        } else {
            self.directionAccuracy = nil
            self.historicalAccuracy = nil
        }
        
        // 4. Current Deviation
        if let lastActual = history.last,
           let lastMid = prediction.mid.first(where: { abs($0.timestamp.timeIntervalSince(lastActual.timestamp)) < 1800 }) {
            self.currentDeviation = lastActual.price - lastMid.price
        } else {
            self.currentDeviation = nil
        }
        
        // 5. Target Price
        self.targetPrice = prediction.mid.last?.price ?? 0
    }
}
