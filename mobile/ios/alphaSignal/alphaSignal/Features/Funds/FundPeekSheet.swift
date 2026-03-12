import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore
import SwiftData
import OSLog

struct FundPeekSheet: View {
    let valuation: FundValuation
    @Environment(\.dismiss) private var dismiss
    private let logger = AppLog.watchlist
    
    @State private var analysis: FundAIAnalysisResponse? = nil
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

                    if isLoading {
                        VStack(spacing: 20) {
                            ProgressView()
                            Text("正在通过 AI 引擎分析情报关联性...")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                    } else if let data = analysis {
                        // 2. AI Market Analysis Insight
                        VStack(alignment: .leading, spacing: 12) {
                            Label("AI 市场解读", systemImage: "sparkles")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.purple)
                                .padding(.horizontal)

                            LiquidGlassCard(backgroundColor: Color.purple.opacity(0.05)) {
                                VStack(alignment: .leading, spacing: 10) {
                                    if let advice = data.topAdvice {
                                        Text(advice)
                                            .font(.subheadline)
                                            .foregroundStyle(.primary.opacity(0.8))
                                            .lineSpacing(4)
                                    } else {
                                        Text("当前暂无针对该基金的专项 AI 解读。建议关注整体市场情绪。")
                                            .font(.subheadline)
                                            .italic()
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .padding(.horizontal)
                        }

                        // 3. Associated Intelligence Section
                        VStack(alignment: .leading, spacing: 16) {
                            Label("关联情报", systemImage: "link")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(.blue)
                                .padding(.horizontal)
                            
                            if data.relatedIntelligence.isEmpty {
                                LiquidGlassCard {
                                    Text("近 7 天暂无直接关联的重大情报。")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                        .frame(maxWidth: .infinity, alignment: .center)
                                        .padding()
                                }
                                .padding(.horizontal)
                            } else {
                                ForEach(data.relatedIntelligence) { item in
                                    IntelligenceBriefRow(item: item)
                                        .padding(.horizontal)
                                }
                            }
                        }

                        // 4. Market Snapshot Context
                        if let snapshot = data.marketSnapshot {
                            VStack(alignment: .leading, spacing: 16) {
                                Label("宏观背景", systemImage: "globe.asia.australia.fill")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundStyle(.secondary)
                                    .padding(.horizontal)
                                
                                HStack(spacing: 12) {
                                    marketSmallQuote(snapshot.gold, name: "黄金")
                                    marketSmallQuote(snapshot.dxy, name: "美元")
                                    marketSmallQuote(snapshot.us10y, name: "美债")
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
                .padding(.bottom, 40)
            }
            .navigationTitle("AI 专项分析")
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
                await fetchAnalysis()
            }
        }
    }
    
    private func fetchAnalysis() async {
        isLoading = true
        do {
            let path = "/api/v1/web/watchlist/\(valuation.fundCode)/ai_analysis"
            self.analysis = try await APIClient.shared.fetch(path: path)
        } catch {
            logger.error("Failed to fetch AI analysis for fund \(valuation.fundCode): \(error.localizedDescription, privacy: .public)")
        }
        isLoading = false
    }

    private func marketSmallQuote(_ quote: MarketQuote, name: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(name)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.secondary)
            Text("\(quote.changePercent >= 0 ? "+" : "")\(String(format: "%.2f%%", quote.changePercent))")
                .font(.system(size: 12, weight: .black, design: .monospaced))
                .foregroundStyle(quote.changePercent >= 0 ? Color.Alpha.down : Color.Alpha.up)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(Color.primary.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct IntelligenceBriefRow: View {
    let item: FundRelatedIntelligence
    
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

                if let advice = item.advice {
                    Text(advice)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .padding(.top, 4)
                }
            }
        }
    }
}
