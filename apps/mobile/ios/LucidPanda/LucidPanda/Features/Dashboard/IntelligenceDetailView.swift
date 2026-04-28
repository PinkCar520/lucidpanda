import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct IntelligenceDetailView: View {
    let item: IntelligenceItem
    @State private var fullItem: IntelligenceItem?
    @State private var isSummarizing = false
    @State private var summary: String?
    @State private var isLoadingFullContent = false
    @Environment(\.colorScheme) var colorScheme
    
    private var currentItem: IntelligenceItem {
        fullItem ?? item
    }
    
    var body: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            
            ScrollView {
                VStack(alignment: .leading, spacing: 32) {
                    // Header Area
                    VStack(alignment: .leading, spacing: 20) {
                        HStack(spacing: 12) {
                            Text(verbatim: "\(currentItem.urgencyScore).0")
                                .font(.system(size: 11, weight: .black, design: .monospaced))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(currentItem.urgencyScore >= 8 ? Color.Alpha.up.opacity(0.15) : Color.Alpha.brand.opacity(0.15))
                                .foregroundStyle(currentItem.urgencyScore >= 8 ? Color.Alpha.up : Color.Alpha.brand)
                                .clipShape(RoundedRectangle(cornerRadius: 2))
                            
                            Text(currentItem.author)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(Color.Alpha.taupe400)
                            
                            Spacer()
                            
                            Text(currentItem.timestamp.formatted(date: .numeric, time: .shortened))
                                .font(.system(size: 11, weight: .medium, design: .monospaced))
                                .foregroundStyle(Color.Alpha.taupe400.opacity(0.6))
                        }
                        
                        Text(currentItem.summary)
                            .font(.system(size: 24, weight: .bold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                            .lineSpacing(4)
                    }
                    .padding(.horizontal)
                    .padding(.top, 24)

                    // Analysis Section (AI Summary)
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Label("intelligence.analysis.title", systemImage: "sparkles")
                                .font(.system(size: 14, weight: .black))
                                .textCase(.uppercase)
                                .foregroundStyle(Color.Alpha.brand)
                            
                            Spacer()
                            
                            if summary == nil {
                                Button {
                                    runAISummary()
                                } label: {
                                    HStack(spacing: 6) {
                                        if isSummarizing {
                                            ProgressView().tint(.white).scaleEffect(0.8)
                                        }
                                        Text(isSummarizing ? "intelligence.summary.generating" : "intelligence.summary.generate")
                                    }
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundStyle(.white)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color.Alpha.brand)
                                    .clipShape(RoundedRectangle(cornerRadius: 4))
                                    .shadow(color: Color.Alpha.brand.opacity(0.3), radius: 4, y: 2)
                                }
                                .disabled(isSummarizing)
                            }
                        }
                        .padding(.horizontal)
                        
                        if let summary = summary {
                            Text(summary)
                                .font(.system(size: 15, weight: .medium))
                                .foregroundStyle(Color.Alpha.textPrimary.opacity(0.9))
                                .lineSpacing(6)
                                .padding(20)
                                .background(Color.Alpha.brand.opacity(0.06))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 4)
                                        .stroke(Color.Alpha.brand.opacity(0.1), lineWidth: 1)
                                )
                                .padding(.horizontal)
                                .transition(.move(edge: .top).combined(with: .opacity))
                        }
                    }

                    // Article Content
                    VStack(alignment: .leading, spacing: 24) {
                        if isLoadingFullContent {
                            HStack {
                                Spacer()
                                ProgressView()
                                    .padding()
                                Spacer()
                            }
                        } else {
                            Text(currentItem.content)
                                .font(.system(size: 17, weight: .regular))
                                .foregroundStyle(Color.Alpha.textPrimary.opacity(0.8))
                                .lineSpacing(10)
                                .textSelection(.enabled)
                        }
                        
                        if let price = currentItem.goldPriceSnapshot {
                            HStack {
                                Text("dashboard.asset.gold")
                                    .font(.system(size: 10, weight: .black))
                                    .foregroundStyle(Color.Alpha.brand)
                                Text(String(format: "$%.2f", price))
                                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                                    .foregroundStyle(Color.Alpha.textSecondary)
                                Spacer()
                                Text("dashboard.asset.gold.realtime")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundStyle(Color.Alpha.taupe.opacity(0.4))
                            }
                            .padding()
                            .background(Color.Alpha.surfaceContainerLow.opacity(0.5))
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .overlay(
                                RoundedRectangle(cornerRadius: 4)
                                    .stroke(Color.Alpha.separator.opacity(0.5), lineWidth: 1)
                            )
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 100)
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if item.content.isEmpty {
                await fetchFullContent()
            }
        }
    }
    
    private func fetchFullContent() async {
        isLoadingFullContent = true
        do {
            let full: IntelligenceItem = try await APIClient.shared.fetch(path: "/api/v1/web/intelligence/\(item.id)")
            await MainActor.run {
                withAnimation {
                    self.fullItem = full
                    self.isLoadingFullContent = false
                }
            }
        } catch {
            print("Failed to fetch full intelligence content: \(error)")
            isLoadingFullContent = false
        }
    }
    
    private func runAISummary() {
        guard !isSummarizing else { return }
        withAnimation { isSummarizing = true }
        
        let savedLanguage = UserDefaults.standard.string(forKey: "appLanguage") ?? "system"
        let languageCode = savedLanguage != "system" ? savedLanguage.lowercased() : (Bundle.main.preferredLocalizations.first?.lowercased() ?? "en")
        let language = languageCode.contains("zh") ? "zh" : "en"
        
        Task {
            do {
                let response: AISummaryResponse = try await APIClient.shared.fetch(path: "/api/v1/mobile/intelligence/\(item.id)/ai_summary?lang=\(language)")
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
