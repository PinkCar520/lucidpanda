import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct IntelligenceItemCard: View {
    let item: IntelligenceItem

    @State private var isPressed: Bool = false
    @State private var showPeek: Bool = false

    var body: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                // Header row
                HStack {
                    HStack(spacing: 4) {
                        Image(systemName: "bolt.fill")
                        Text("\(item.urgencyScore)")
                    }
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(item.urgencyScore >= 8 ? Color.red.opacity(0.12) : Color(uiColor: .secondarySystemFill))
                    .foregroundStyle(item.urgencyScore >= 8 ? Color.red : Color.primary)
                    .clipShape(Capsule())

                    Spacer()

                    Text(dateFormatter.string(from: item.timestamp))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary)
                }

                // Body
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.summary)
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    Text(item.content)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                }

                // Footer
                HStack {
                    Label(item.author, systemImage: "newspaper.fill")
                        .foregroundStyle(.secondary)

                    Spacer()

                    if let price = item.goldPriceSnapshot {
                        HStack(spacing: 4) {
                            Text("dashboard.asset.gold")
                                .font(.system(size: 8, weight: .bold))
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .background(Color(uiColor: .tertiarySystemFill))
                                .cornerRadius(4)

                            Text("$\(String(format: "%.1f", price))")
                                .fontWeight(.black)
                        }
                        .foregroundStyle(.primary)
                    }

                    // Long-press hint icon
                    Image(systemName: "hand.tap.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                        .padding(.leading, 6)
                }
                .font(.system(size: 10, design: .monospaced))
                .padding(.top, 4)
            }
        }
        .scaleEffect(isPressed ? 0.97 : 1.0)
        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isPressed)
        .onLongPressGesture(minimumDuration: 0.4, pressing: { pressing in
            withAnimation { isPressed = pressing }
        }, perform: {
            showPeek = true
        })
        .sheet(isPresented: $showPeek) {
            IntelligencePeekSheet(item: item)
                .presentationDetents([.medium])
                .presentationDragIndicator(.visible)
        }
        .transition(.asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity).combined(with: .scale(scale: 0.9)),
            removal: .opacity
        ))
    }

    private var dateFormatter: DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter
    }
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
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {

                    // Meta row
                    HStack(spacing: 8) {
                        HStack(spacing: 4) {
                            Image(systemName: "bolt.fill")
                            Text("\(item.urgencyScore)")
                        }
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(item.urgencyScore >= 8 ? Color.red.opacity(0.12) : Color(uiColor: .secondarySystemFill))
                        .foregroundStyle(item.urgencyScore >= 8 ? Color.red : Color.primary)
                        .clipShape(Capsule())

                        Spacer()

                        Text(item.timestamp.formatted(date: .abbreviated, time: .shortened))
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }

                    // Title
                    Text(item.summary)
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundStyle(.primary)

                    // Full content
                    Text(item.content)
                        .font(.body)
                        .foregroundStyle(.primary.opacity(0.85))
                        .lineSpacing(5)

                    // Source & Asset row — matching card footer
                    HStack {
                        Label(item.author, systemImage: "newspaper.fill")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.secondary)
                        
                        Spacer()
                        
                        if let price = item.goldPriceSnapshot {
                            HStack(spacing: 4) {
                                Text("dashboard.asset.gold")
                                    .font(.system(size: 8, weight: .bold))
                                    .padding(.horizontal, 4)
                                    .padding(.vertical, 2)
                                    .background(Color(uiColor: .tertiarySystemFill))
                                    .cornerRadius(4)
                                
                                Text("$\(String(format: "%.1f", price))")
                                    .font(.system(size: 11, weight: .black, design: .monospaced))
                            }
                            .foregroundStyle(.primary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Divider()

                    // AI Analysis Section
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Label(LocalizedStringKey("intelligence.analysis.title"), systemImage: "sparkles")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(.blue)

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
                                        }
                                    } else {
                                        Text(LocalizedStringKey("intelligence.analysis.start"))
                                            .font(.system(size: 13, weight: .semibold))
                                            .foregroundStyle(.white)
                                            .padding(.horizontal, 14)
                                            .padding(.vertical, 7)
                                            .background(Color.blue)
                                            .clipShape(Capsule())
                                    }
                                }
                                .disabled(isAnalyzing)
                            }
                        }

                        if let result = aiSummary {
                            Text(result)
                                .font(.subheadline)
                                .foregroundStyle(.primary.opacity(0.85))
                                .lineSpacing(4)
                                .padding(14)
                                .background(Color.blue.opacity(0.06))
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                .transition(.move(edge: .bottom).combined(with: .opacity))
                        }

                        if let err = analyzeError {
                            Text(err)
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                }
                .padding(20)
            }
            .navigationTitle(LocalizedStringKey("intelligence.analysis.quick_view"))
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
                // Auto-trigger AI analysis on open
                await runAIAnalysis()
            }
        }
    }

    private func runAIAnalysis() async {
        guard !isAnalyzing, aiSummary == nil else { return }
        withAnimation { isAnalyzing = true }
        defer { withAnimation { isAnalyzing = false } }

        do {
            let response: AISummaryResponse = try await APIClient.shared.fetch(
                path: "/api/v1/mobile/intelligence/\(item.id)/ai_summary"
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
