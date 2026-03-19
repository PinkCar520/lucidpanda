import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct IntelligenceDetailView: View {
    let item: IntelligenceItem
    @State private var isSummarizing = false
    @State private var summary: String?
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView {
                VStack(spacing: 24) {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            DetailBadge(text: "\(String(localized: "dashboard.urgency_label")) \(item.urgencyScore)", color: item.urgencyScore >= 8 ? .red : .blue)
                            Spacer()
                            Text(item.timestamp.formatted())
                                .font(.caption2)
                                .foregroundStyle(.gray.opacity(0.6))
                        }
                        
                        Text(item.summary)
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                        
                        Button {
                            runAISummary()
                        } label: {
                            HStack {
                                Image(systemName: "sparkles")
                                Text(isSummarizing ? "intelligence.summary.generating" : "intelligence.summary.generate")
                            }
                            .font(.system(size: 12, weight: .medium))
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
                    .background(Color(uiColor: .systemBackground))
                    .overlay(
                        RoundedRectangle(cornerRadius: 24, style: .continuous)
                            .stroke(Color(uiColor: .separator).opacity(0.22), lineWidth: 0.6)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 24))
                }
                .padding()
            }
        }
        .navigationTitle("intelligence.detail.title")
        .navigationBarTitleDisplayMode(.inline)
    }
    
    private func runAISummary() {
        guard !isSummarizing else { return }
        withAnimation { isSummarizing = true }
        
        Task {
            do {
                let response: AISummaryResponse = try await APIClient.shared.fetch(path: "/api/v1/mobile/intelligence/\(item.id)/ai_summary")
                await MainActor.run {
                    withAnimation {
                        self.summary = response.ai_summary
                        self.isSummarizing = false
                    }
                }
            } catch {
                await MainActor.run {
                    withAnimation {
                        self.summary = String(format: NSLocalizedString("intelligence.summary.error", comment: ""), error.localizedDescription)
                        self.isSummarizing = false
                    }
                }
            }
        }
    }
    
}

struct DetailBadge: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .medium, design: .monospaced))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.1))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}

struct AISummaryResponse: Codable {
    let ai_summary: String
}
