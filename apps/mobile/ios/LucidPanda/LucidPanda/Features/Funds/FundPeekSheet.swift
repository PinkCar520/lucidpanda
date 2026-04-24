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
                                .font(.title3).fontWeight(.medium)
                                .foregroundStyle(.primary)
                            
                            Spacer()
                            
                            Text(Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: valuation.estimatedGrowth / 100.0)) ?? "\(valuation.estimatedGrowth.formatted(.number.precision(.fractionLength(2))))%")
                                .font(.system(size: 20, weight: .semibold, design: .monospaced))
                                .foregroundStyle(valuation.estimatedGrowth >= 0 ? Color.Alpha.up : Color.Alpha.down)
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
                            Text("funds.peek.analyzing_with_ai")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                    } else if let data = analysis {
                        // 2. AI Market Analysis Insight
                        VStack(alignment: .leading, spacing: 12) {
                            Label("funds.peek.ai_interpretation", systemImage: "sparkles")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundStyle(.purple)
                                .padding(.horizontal)
                            
                            if let isFallback = data.isFallback, isFallback {
                                HStack(spacing: 6) {
                                    Image(systemName: "info.circle.fill")
                                    Text(data.fallbackSource ?? String(localized: "funds.peek.fallback_source.industry"))
                                        .font(.system(size: 10, weight: .semibold))
                                }
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.blue.opacity(0.1))
                                .foregroundStyle(.blue)
                                .clipShape(Capsule())
                                .padding(.horizontal)
                                .transition(.opacity)
                            }

                            LiquidGlassCard(backgroundColor: Color.purple.opacity(0.05)) {
                                VStack(alignment: .leading, spacing: 10) {
                                    if let advice = data.topAdvice {
                                        Text(advice)
                                            .font(.subheadline)
                                            .foregroundStyle(.primary.opacity(0.8))
                                            .lineSpacing(4)
                                    } else {
                                        Text("funds.peek.no_ai_analysis")
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
                            Label("funds.peek.related_intelligence", systemImage: "link")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundStyle(.blue)
                                .padding(.horizontal)
                            
                            if data.relatedIntelligence.isEmpty {
                                LiquidGlassCard {
                                    Text("funds.peek.no_related_intelligence_7d")
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
                                Label("funds.peek.macro_context", systemImage: "globe.asia.australia.fill")
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundStyle(.secondary)
                                    .padding(.horizontal)
                                
                                HStack(spacing: 12) {
                                    marketSmallQuote(snapshot.gold, name: String(localized: "funds.peek.market.gold"))
                                    marketSmallQuote(snapshot.dxy, name: String(localized: "funds.peek.market.usd"))
                                    marketSmallQuote(snapshot.us10y, name: String(localized: "funds.peek.market.us10y"))
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
                .padding(.bottom, 40)
            }
            .navigationTitle("funds.peek.ai_analysis_title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
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
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.secondary)
            Text(Formatters.signedPercentFormatter(fractionDigits: 2).string(from: NSNumber(value: quote.changePercent)) ?? "\(quote.changePercent.formatted(.number.precision(.fractionLength(2))))%")
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(quote.changePercent >= 0 ? Color.Alpha.up : Color.Alpha.down)
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
                    Text(item.urgencyScore >= 8 ? "common.urgency.critical" : "common.urgency.important")
                        .font(.system(size: 9, weight: .medium))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(item.urgencyScore >= 8 ? Color.Alpha.down.opacity(0.12) : Color.Alpha.primary.opacity(0.12))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.down : Color.Alpha.primary)
                        .clipShape(Capsule())
                    
                    if let author = item.author {
                        Text(author)
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.secondary)
                            .padding(.leading, 4)
                    }
                    
                    Spacer()
                    
                    Text(item.timestamp.formatted(date: .numeric, time: .shortened))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                
                Text(item.summary)
                    .font(.subheadline).fontWeight(.regular)
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
