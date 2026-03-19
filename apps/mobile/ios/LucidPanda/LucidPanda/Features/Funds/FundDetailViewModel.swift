import Foundation
import Observation
import AlphaData
import AlphaCore
import SwiftUI
import SwiftData

@Observable
class FundDetailViewModel {
    var valuation: FundValuation
    var liveGrowth: Double
    var isLive: Bool = false
    
    // 2σ 智能报警设置
    var isAlarmEnabled: Bool = true
    var threshold2Sigma: Double = 1.5 
    private var hasFiredAlarmToday: Bool = false
    
    // 关联情报列表
    var linkedIntelligence: [IntelligenceItem] = []
    
    // 历史对账记录
    var history: [ValuationHistory] = []
    var isHistoryLoading: Bool = false
    
    private let actor: ValuationActor
    private var subscriptionTask: Task<Void, Never>?
    
    @ObservationIgnored
    private var persistenceContext: ModelContext?
    
    public func setModelContext(_ context: ModelContext) {
        self.persistenceContext = context
    }
    
    init(valuation: FundValuation, modelContext: ModelContext? = nil) {
        self.valuation = valuation
        self.liveGrowth = valuation.estimatedGrowth
        self.actor = ValuationActor(initialValuation: valuation)
        self.persistenceContext = modelContext
    }
    
    @MainActor
    func startLiveUpdates() {
        guard !isLive else { return }
        isLive = true
        
        // 1. 初始化 2σ 阈值与关联情报
        Task {
            await self.calculateDynamicThreshold()
            self.refreshLinkedIntelligence()
        }
        
        // 2. 启动实时流
        subscriptionTask = Task {
            let stream = await actor.start()
            for await updatedValuation in stream {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    self.valuation = updatedValuation
                    self.liveGrowth = updatedValuation.estimatedGrowth
                }
                checkAlarm(growth: updatedValuation.estimatedGrowth)
            }
        }
    }
    
    @MainActor
    private func calculateDynamicThreshold() async {
        isHistoryLoading = true
        do {
            let response: FundHistoryResponse = try await APIClient.shared.fetch(
                path: "/api/v1/web/funds/\(valuation.fundCode)/history?limit=20"
            )
            self.history = response.data
            let calculated = await actor.calculateThreshold2Sigma(history: response.data)
            self.threshold2Sigma = calculated
        } catch {
            self.threshold2Sigma = 1.5
        }
        isHistoryLoading = false
    }
    
    @MainActor
    private func refreshLinkedIntelligence() {
        guard let context = persistenceContext else { return }
        let engine = IntelligenceLinkageEngine(modelContext: context)
        self.linkedIntelligence = engine.fetchLinkedIntelligence(for: valuation)
    }
    
    private func checkAlarm(growth: Double) {
        guard isAlarmEnabled && !hasFiredAlarmToday else { return }
        
        if abs(growth) >= threshold2Sigma {
            hasFiredAlarmToday = true
            AlarmNotificationManager.shared.sendValuationAlarm(
                fundName: valuation.fundName,
                changePct: growth,
                threshold: threshold2Sigma
            )
        }
    }
    
    func stopLiveUpdates() {
        isLive = false
        subscriptionTask?.cancel()
        Task { await actor.stop() }
    }
}

// 补充 DTO 定义以匹配 sse_server.py
struct FundHistoryResponse: Codable {
    let data: [ValuationHistory]
}
