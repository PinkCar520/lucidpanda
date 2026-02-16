import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct IntelligenceDetailView: View {
    let item: IntelligenceItem
    @State private var marketData: [MarketDataPoint] = []
    @State private var isSummarizing = false
    @State private var summary: String?
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView {
                VStack(spacing: 24) {
                    if !marketData.isEmpty {
                        MarketChartView(data: marketData)
                            .padding(.top)
                    } else {
                        RoundedRectangle(cornerRadius: 20)
                            .fill(Color.black.opacity(0.03))
                            .frame(height: 200)
                            .overlay(ProgressView().tint(.blue))
                    }
                    
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            DetailBadge(text: "URGENCY \(item.urgencyScore)", color: item.urgencyScore >= 8 ? .red : .blue)
                            Spacer()
                            Text(item.timestamp.formatted())
                                .font(.caption2)
                                .foregroundStyle(.gray.opacity(0.6))
                        }
                        
                        Text(item.summary)
                            .font(.title2)
                            .fontWeight(.black)
                            .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                        
                        Button {
                            runAISummary()
                        } label: {
                            HStack {
                                Image(systemName: "sparkles")
                                Text(isSummarizing ? "intelligence.summary.generating" : "intelligence.summary.generate")
                            }
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(.blue)
                            .padding(.vertical, 10)
                            .padding(.horizontal, 16)
                            .glassEffect(.regular, in: .capsule)
                            .clipShape(Capsule())
                        }
                        
                        if let summary = summary {
                            Text(summary)
                                .font(.subheadline)
                                .padding()
                                .background(Color.black.opacity(0.03))
                                .cornerRadius(12)
                                .transition(.scale.combined(with: .opacity))
                        }
                        
                        Text(item.content)
                            .font(.body)
                            .foregroundStyle(.black.opacity(0.8))
                            .lineSpacing(6)
                    }
                    .padding()
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 24))
                    .shadow(color: .black.opacity(0.05), radius: 10)
                }
                .padding()
            }
        }
        .navigationTitle("intelligence.detail.title")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await fetchMarketContext()
        }
    }
    
    private func runAISummary() {
        withAnimation { isSummarizing = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation {
                summary = NSLocalizedString("intelligence.summary.mock", comment: "")
                isSummarizing = false
            }
        }
    }
    
    private func fetchMarketContext() async {
        do {
            let response: MarketResponse = try await APIClient.shared.fetch(path: "/api/market?symbol=GC=F&range=1d&interval=5m")
            withAnimation {
                self.marketData = response.data
            }
        } catch {
            print("Failed to load market context: \(error)")
        }
    }
}

struct DetailBadge: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .black, design: .monospaced))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.1))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}
