import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct IntelligenceItemCard: View {
    enum Style {
        case featured
        case standard
    }
    
    let item: IntelligenceItem
    let style: Style
    
    @State private var isPressed: Bool = false
    @State private var showPeek: Bool = false
    @Environment(\.colorScheme) var colorScheme
    @Environment(AppRootViewModel.self) private var rootViewModel

    private var formattedTime: String {
        Self.timeFormatter.string(from: item.timestamp)
    }
    
    private var formattedGoldPrice: String? {
        guard let price = item.goldPriceSnapshot else { return nil }
        return String(format: "$%.2f", price)
    }

    var body: some View {
        Group {
            switch style {
            case .featured:
                featuredLayout
            case .standard:
                standardLayout
            }
        }
        .compositingGroup() // 🚀 Optimization: Reduce rendering passes during scroll
        .scaleEffect(isPressed ? 0.98 : 1.0)
        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isPressed)
        .onLongPressGesture(minimumDuration: 0.4, pressing: { pressing in
            withAnimation { isPressed = pressing }
        }, perform: {
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()
            showPeek = true
        })
        .sheet(isPresented: $showPeek) {
            IntelligencePeekSheet(item: item)
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
    }
    
    private func resolvedImageURL() -> URL? {
        if let localPath = item.local_image_path {
            // Priority: Local cached image served via /static/
            return APIClient.shared.baseURL.appendingPathComponent("static").appendingPathComponent(localPath)
        } else if let originalUrlString = item.imageUrl {
            // Fallback: Original URL (no proxy)
            return URL(string: originalUrlString)
        }
        return nil
    }

    // MARK: - Layouts

    private var featuredLayout: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Image with real project assets or remote URL
            ZStack(alignment: .bottomLeading) {
                if let url = resolvedImageURL() {
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    } placeholder: {
                        Color.Alpha.surfaceDim
                    }
                    .frame(maxWidth: .infinity)
                    .aspectRatio(16/9, contentMode: .fit)
                    .clipped()
                } else {
                    let imageName = item.id % 2 == 0 ? "featured_1" : "featured_2"
                    // Base 16:9 container to prevent distortion
                    Color.clear
                        .aspectRatio(16/9, contentMode: .fit)
                        .overlay(
                            Image(imageName)
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        )
                        .clipped()
                }
                
                Color.black.opacity(0.1) // Subtle darkening for text readability
                
                HStack(spacing: 8) {
                    Text("dashboard.badge.featured")
                        .font(.system(size: 9, weight: .black))
                        .textCase(.uppercase)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.Alpha.brand.opacity(0.8)) // More solid on real images
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                    
                    Text("dashboard.read_time.format \(5)")
                        .font(.system(size: 9, weight: .bold))
                        .textCase(.uppercase)
                        .foregroundStyle(.white)
                        .shadow(color: .black.opacity(0.3), radius: 2)
                }
                .padding(16)
            }
            
            VStack(alignment: .leading, spacing: 12) {
                Text(item.summary)
                    .font(.system(size: 19, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)
                
                Text("dashboard.action.read_full")
                    .font(.system(size: 13, weight: .black))
                    .textCase(.uppercase)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(Color.Alpha.brand)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .shadow(color: Color.Alpha.brand.opacity(0.25), radius: 5, y: 3)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(Color.Alpha.surface)
        }
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(Color.Alpha.separator, lineWidth: 1)
        )
        .shadow(color: colorScheme == .light ? Color.black.opacity(0.04) : Color.clear, radius: 4, y: 2)
    }

    private var standardLayout: some View {
        HStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 10) {
                // Meta info
                HStack(spacing: 8) {
                    Text(verbatim: "\(item.urgencyScore).0")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(item.urgencyScore >= 8 ? Color.Alpha.up.opacity(0.15) : Color.Alpha.brand.opacity(0.15))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.up : Color.Alpha.brand)
                        .clipShape(RoundedRectangle(cornerRadius: 2))

                    Text(item.author)
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(Color.Alpha.taupe)
                    
                    Spacer()
                    
                    Text(formattedTime)
                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                        .foregroundStyle(Color.Alpha.taupe.opacity(0.6))
                }

                // Summary
                Text(item.summary)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .lineLimit(2)
                    .lineSpacing(2)
                    .multilineTextAlignment(.leading)

                // Asset Snapshot
                if let priceString = formattedGoldPrice {
                    HStack(spacing: 4) {
                        Text("dashboard.asset.gold")
                            .font(.system(size: 8, weight: .black))
                            .foregroundStyle(Color.Alpha.brand)
                        Text(priceString)
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(Color.Alpha.textSecondary)
                    }
                }
            }
            
            Spacer()
            
            // Thumbnail with real image support
            if let url = resolvedImageURL() {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    Rectangle()
                        .fill(Color.Alpha.surfaceContainerLow)
                        .overlay(ProgressView().scaleEffect(0.5))
                }
                .frame(width: 80, height: 80)
                .clipShape(RoundedRectangle(cornerRadius: 4))
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.Alpha.separator.opacity(0.3), lineWidth: 0.5))
            } else {
                Rectangle()
                    .fill(Color.Alpha.surfaceContainerLow)
                    .frame(width: 80, height: 80)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .overlay(
                        Image(systemName: "newspaper.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(Color.Alpha.brand.opacity(0.15))
                    )
            }
        }
        .padding(14)
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(Color.Alpha.separator.opacity(0.5), lineWidth: 1)
        )
        .shadow(color: colorScheme == .light ? Color.black.opacity(0.02) : Color.clear, radius: 2, y: 1)
    }

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter
    }()
}

// MARK: - Quick Peek Sheet

struct IntelligencePeekSheet: View {
    let item: IntelligenceItem

    @State private var aiSummary: String? = nil
    @State private var isAnalyzing: Bool = false
    @State private var analyzeError: String? = nil
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {

                        // Meta row
                        HStack(spacing: 8) {
                            HStack(spacing: 4) {
                                Image(systemName: "bolt.fill")
                                Text(verbatim: "\(item.urgencyScore)")
                            }
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(item.urgencyScore >= 8 ? Color.Alpha.up.opacity(0.15) : Color.Alpha.brand.opacity(0.15))
                            .foregroundStyle(item.urgencyScore >= 8 ? Color.Alpha.up : Color.Alpha.brand)
                            .clipShape(Capsule())

                            Spacer()

                            Text(item.timestamp.formatted(date: .abbreviated, time: .shortened))
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundStyle(Color.Alpha.taupe)
                        }

                        // Summary Title
                        Text(item.summary)
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundStyle(Color.Alpha.textPrimary)
                            .lineSpacing(4)

                        // Source & Asset row
                        HStack {
                            Label(item.author, systemImage: "newspaper.fill")
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundStyle(Color.Alpha.textSecondary)
                            
                            Spacer()
                            
                            if let price = item.goldPriceSnapshot {
                                HStack(spacing: 4) {
                                    Text("dashboard.asset.gold")
                                        .font(.system(size: 8, weight: .medium))
                                        .padding(.horizontal, 4)
                                        .padding(.vertical, 2)
                                        .background(Color.Alpha.separator.opacity(0.8))
                                        .cornerRadius(4)
                                    
                                    Text("$\(String(format: "%.2f", price))")
                                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                                }
                                .foregroundStyle(Color.Alpha.textSecondary)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)

                        Divider().background(Color.Alpha.separator)

                        // AI Analysis Section
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Label(LocalizedStringKey("intelligence.analysis.title"), systemImage: "sparkles")
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundStyle(Color.Alpha.brand)

                                Spacer()

                                if aiSummary == nil {
                                    Button {
                                        Task { await runAIAnalysis() }
                                    } label: {
                                        if isAnalyzing {
                                            HStack(spacing: 6) {
                                                ProgressView().scaleEffect(0.75)
                                                Text(LocalizedStringKey("intelligence.analysis.analyzing"))
                                                    .font(.system(size: 13, weight: .medium))
                                                    .foregroundStyle(Color.Alpha.textSecondary)
                                            }
                                        } else {
                                            Text(LocalizedStringKey("intelligence.analysis.start"))
                                                .font(.system(size: 13, weight: .medium))
                                                .foregroundStyle(.white)
                                                .padding(.horizontal, 14)
                                                .padding(.vertical, 7)
                                                .background(Color.Alpha.brand)
                                                .clipShape(Capsule())
                                        }
                                    }
                                    .disabled(isAnalyzing)
                                }
                            }

                            if let result = aiSummary {
                                Text(result)
                                    .font(.subheadline)
                                    .foregroundStyle(Color.Alpha.textPrimary.opacity(0.85))
                                    .lineSpacing(4)
                                    .padding(14)
                                    .background(Color.Alpha.brand.opacity(0.06))
                                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                                    .transition(.move(edge: .bottom).combined(with: .opacity))
                            }

                            if let err = analyzeError {
                                Text(err)
                                    .font(.caption)
                                    .foregroundStyle(Color.Alpha.down)
                            }
                        }
                    }
                    .padding(20)
                }
            }
            .navigationTitle(LocalizedStringKey("intelligence.analysis.quick_view"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(.primary)
                    }
                }
            }
            .task {
                // Auto-trigger AI analysis on open
                await runAIAnalysis()
            }
        }
    }

    private func runAIAnalysis() async {
        guard !isAnalyzing, aiSummary == nil else { return }
        withAnimation { isAnalyzing = true }
        defer { withAnimation { isAnalyzing = false } }

        let savedLanguage = UserDefaults.standard.string(forKey: "appLanguage") ?? "system"
        let languageCode = savedLanguage != "system" ? savedLanguage.lowercased() : (Bundle.main.preferredLocalizations.first?.lowercased() ?? "en")
        let language = languageCode.contains("zh") ? "zh" : "en"

        do {
            let response: AISummaryResponse = try await APIClient.shared.fetch(
                path: "/api/v1/mobile/intelligence/\(item.id)/ai_summary?lang=\(language)"
            )
            withAnimation(.easeInOut(duration: 0.4)) {
                aiSummary = response.ai_summary
            }
        } catch {
            analyzeError = String(
                format: NSLocalizedString("intelligence.summary.error", comment: ""),
                error.localizedDescription
            )
        }
    }
}
