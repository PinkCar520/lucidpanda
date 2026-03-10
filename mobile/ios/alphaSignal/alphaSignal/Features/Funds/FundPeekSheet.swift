import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData
import OSLog

struct FundPeekSheet: View {
    let valuation: FundValuation
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    private let logger = AppLog.watchlist
    
    @State private var linkedIntelligence: [IntelligenceItem] = []
    @State private var isLoading: Bool = true
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // 1. Fund Header
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(valuation.fundName)
                                .font(.title3.bold())
                                .foregroundStyle(.primary)
                            
                            Spacer()
                            
                            Text("\(valuation.estimatedGrowth >= 0 ? "+" : "")\(String(format: "%.2f", valuation.estimatedGrowth))%")
                                .font(.system(size: 20, weight: .black, design: .monospaced))
                                .foregroundStyle(valuation.estimatedGrowth >= 0 ? Color.Alpha.down : Color.Alpha.up)
                        }
                        
                        Text(valuation.fundCode)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal)
                    .padding(.top, 16)
                    
                    Divider()
                        .padding(.horizontal)
                    
                    // 2. Associated Intelligence Section
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Label("关联情报", systemImage: "link")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.blue)
                            
                            Spacer()
                            
                            if isLoading {
                                ProgressView().scaleEffect(0.8)
                            }
                        }
                        .padding(.horizontal)
                        
                        if linkedIntelligence.isEmpty && !isLoading {
                            LiquidGlassCard {
                                Text("intelligence.analysis.no_related", bundle: .main)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .center)
                                    .padding()
                            }
                            .padding(.horizontal)
                        } else {
                            ForEach(linkedIntelligence) { item in
                                IntelligenceBriefRow(item: item)
                                    .padding(.horizontal)
                            }
                        }
                    }
                    
                    // 3. AI Deep Analysis Shortcut
                    if let firstItem = linkedIntelligence.first {
                        VStack(alignment: .leading, spacing: 12) {
                            Label(LocalizedStringKey("intelligence.analysis.title"), systemImage: "sparkles")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.purple)
                                .padding(.horizontal)

                            LiquidGlassCard(backgroundColor: Color.purple.opacity(0.05)) {
                                VStack(alignment: .leading, spacing: 10) {
                                    HStack {
                                        Text(LocalizedStringKey("intelligence.analysis.core_signal"))
                                            .font(.caption.bold())
                                            .foregroundStyle(.purple)
                                        Spacer()
                                        if isAnalyzing {
                                            ProgressView().scaleEffect(0.6)
                                        }
                                    }

                                    if let advice = aiAdvice {
                                        Text(advice)
                                            .font(.subheadline)
                                            .foregroundStyle(.primary.opacity(0.8))
                                            .lineSpacing(4)
                                            .transition(.opacity)
                                    } else {
                                        Text(String(format: NSLocalizedString("intelligence.analysis.extracting", bundle: .main, comment: ""), firstItem.summary))
                                            .font(.subheadline)
                                            .italic()
                                            .foregroundStyle(.secondary)
                                    }

                                    HStack {
                                        Spacer()
                                        Text("intelligence.analysis.view_full_report", bundle: .main)
                                            .font(.caption.bold())
                                            .foregroundStyle(.blue)
                                    }
                                    .padding(.top, 4)
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.bottom, 40)
            }
            .navigationTitle(LocalizedStringKey("funds.peek.title"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
            .task {
                await fetchAllData()
            }
        }
    }
    
    @State private var aiAdvice: String? = nil
    @State private var isAnalyzing: Bool = false

    private func fetchAllData() async {
        let engine = IntelligenceLinkageEngine(modelContext: modelContext)
        linkedIntelligence = engine.fetchLinkedIntelligence(for: valuation)
        isLoading = false
        
        if let firstItem = linkedIntelligence.first {
            await fetchAIAnalysis(for: firstItem)
        }
    }
    
    private func fetchAIAnalysis(for item: IntelligenceItem) async {
        guard !isAnalyzing else { return }
        isAnalyzing = true
        defer { isAnalyzing = false }
        
        do {
            let response: AISummaryResponse = try await APIClient.shared.fetch(
                path: "/api/v1/mobile/intelligence/\(item.id)/ai_summary"
            )
            withAnimation {
                self.aiAdvice = response.ai_summary
            }
        } catch {
            logger.error("Failed to fetch AI analysis for fund peek: \(error.localizedDescription, privacy: .public)")
        }
    }
}

struct IntelligenceBriefRow: View {
    let item: IntelligenceItem
    
    var body: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(item.urgencyScore >= 8 ? "危急" : "重要")
                        .font(.system(size: 9, weight: .bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(item.urgencyScore >= 8 ? Color.Alpha.down.opacity(0.12) : Color.Alpha.primary.opacity(0.12))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.primary)
                        .clipShape(Capsule())
                    
                    Spacer()
                    
                    Text(item.timestamp.formatted(date: .numeric, time: .omitted))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                
                Text(item.summary)
                    .font(.subheadline.bold())
                    .foregroundStyle(.primary)
                    .lineLimit(2)
            }
        }
    }
}
