import SwiftUI
import AlphaDesign
import AlphaData
import StoreKit

struct PaywallView: View {
    @Environment(AppRootViewModel.self) private var rootViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var selectedPlan: PlanType = .yearly
    @State private var isPurchasing = false
    
    enum PlanType {
        case monthly, quarterly, yearly
    }
    
    var body: some View {
        NavigationStack {
            ZStack(alignment: .top) {
                // 1. Background Base
                Color.Alpha.background.ignoresSafeArea()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 0) {
                        // 2. Hero Section (Editorial Impact)
                        heroSection
                            .padding(.top, 24)
                            .padding(.bottom, 48)
                        
                        // 3. Feature Matrix (Tonal Separation)
                        featureMatrix
                            .padding(.bottom, 48)
                        
                        // 4. Pricing Tiers
                        pricingSection
                            .padding(.bottom, 32)
                        
                        // 5. Footer Legal
                        footerLinks
                            .padding(.bottom, 60)
                    }
                }
            }
            .navigationTitle(LocalizedStringKey("subscription.label.premium")) // 🚀 Matches standard navigation style
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold)) // 🚀 Exactly as in MarketPulseSheet
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
    }
    
    // MARK: - Components
    
    private var heroSection: some View {
        VStack(spacing: 24) {
            // 🚀 Hero Icon (workspace_premium) - Enlarged
            ZStack {
                Circle()
                    .fill(Color.Alpha.surfaceContainerLow)
                    .frame(width: 110, height: 110)
                
                Image(systemName: "seal.fill") 
                    .font(.system(size: 56))
                    .foregroundStyle(Color.Alpha.brand)
                    .overlay {
                        Image(systemName: "checkmark")
                            .font(.system(size: 26, weight: .black))
                            .foregroundStyle(.white)
                    }
            }
            .shadow(color: Color.Alpha.brand.opacity(0.12), radius: 24, y: 12)
            
            VStack(spacing: 12) {
                Text(LocalizedStringKey("subscription.title"))
                    .font(.system(size: 28, weight: .black, design: .serif)) // 🚀 Reduced for better balance
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .tracking(-0.2)
                
                Text(LocalizedStringKey("subscription.slogan"))
                    .font(.system(size: 15, weight: .regular))
                    .foregroundStyle(Color.Alpha.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                    .lineSpacing(4)
            }
        }
    }
    
    private var featureMatrix: some View {
        VStack(spacing: 28) {
            // 🚀 Feature List with design icons
            featureRow(icon: "bell.badge.fill", title: LocalizedStringKey("subscription.feature.alerts.title"), sub: LocalizedStringKey("subscription.feature.alerts.sub"))
            featureRow(icon: "doc.text.fill", title: LocalizedStringKey("subscription.feature.backtest.title"), sub: LocalizedStringKey("subscription.feature.backtest.sub"))
            featureRow(icon: "brain.head.profile", title: LocalizedStringKey("subscription.feature.sentiment.title"), sub: LocalizedStringKey("subscription.feature.sentiment.sub"))
        }
        .padding(.horizontal, 24)
    }
    
    private func featureRow(icon: String, title: LocalizedStringKey, sub: LocalizedStringKey) -> some View {
        HStack(alignment: .top, spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundStyle(Color.Alpha.brand)
                .frame(width: 40, height: 40)
                .background(Circle().fill(Color.Alpha.primaryContainer.opacity(0.15)))
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                Text(sub)
                    .font(.system(size: 14))
                    .foregroundStyle(Color.Alpha.textSecondary)
                    .lineLimit(2)
            }
            Spacer()
        }
    }
    
    private var pricingSection: some View {
        VStack(spacing: 12) {
            // Annual (Best Value)
            planRow(type: .yearly, title: LocalizedStringKey("subscription.plan.yearly"), price: "$199.99", sub: LocalizedStringKey("subscription.plan.yearly.sub"), isBest: true)
            
            // Quarterly
            planRow(type: .quarterly, title: LocalizedStringKey("subscription.plan.quarterly"), price: "$59.99", sub: LocalizedStringKey("subscription.plan.quarterly.sub"))
            
            // Monthly
            planRow(type: .monthly, title: LocalizedStringKey("subscription.plan.monthly"), price: "$24.99", sub: LocalizedStringKey("subscription.plan.monthly.sub"))
            
            subscribeButton
                .padding(.top, 12)
        }
        .padding(.horizontal, 24)
    }
    
    private func planRow(type: PlanType, title: LocalizedStringKey, price: String, sub: LocalizedStringKey, isBest: Bool = false) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) { selectedPlan = type }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(Color.Alpha.textPrimary)
                    Text(sub)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Color.Alpha.taupe)
                        .textCase(.uppercase)
                        .tracking(1.0)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 2) {
                    Text(price)
                        .font(.system(size: 20, weight: .black, design: .monospaced))
                        .foregroundStyle(selectedPlan == type ? Color.Alpha.brand : Color.Alpha.textPrimary)
                    
                    if isBest {
                        Text(LocalizedStringKey("subscription.plan.best_value"))
                            .font(.system(size: 10, weight: .black))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Color.Alpha.brand)
                            .foregroundStyle(.white)
                            .clipShape(Capsule())
                    }
                }
            }
            .padding(.all, 20)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(selectedPlan == type ? Color.Alpha.surfaceContainerLowest : Color.Alpha.surfaceContainerLow)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(selectedPlan == type ? Color.Alpha.brand : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
    }
    
    private var subscribeButton: some View {
        Button {
            performPurchase()
        } label: {
            ZStack {
                if isPurchasing {
                    ProgressView().tint(.white)
                } else {
                    Text(LocalizedStringKey("subscription.action.subscribe"))
                        .font(.system(size: 18, weight: .bold))
                }
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 64)
            .background(
                LinearGradient(colors: [Color(hex: "#7d562d"), Color(hex: "#d4a373")], startPoint: .topLeading, endPoint: .bottomTrailing)
            )
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .shadow(color: Color(hex: "#7d562d").opacity(0.3), radius: 20, x: 0, y: 10)
        }
        .buttonStyle(LiquidScaleButtonStyle())
        .disabled(isPurchasing)
    }
    
    private var footerLinks: some View {
        VStack(spacing: 16) {
            Button(LocalizedStringKey("subscription.action.restore")) {
                // Restore logic
            }
            .font(.system(size: 12, weight: .bold))
            .foregroundStyle(Color.Alpha.taupe)
            .tracking(1.5)
            .textCase(.uppercase)
            
            HStack(spacing: 24) {
                Text(LocalizedStringKey("subscription.label.tos"))
                Circle().fill(Color.Alpha.separator).frame(width: 4, height: 4)
                Text(LocalizedStringKey("subscription.label.privacy"))
            }
            .font(.system(size: 11, weight: .medium))
            .foregroundStyle(Color.Alpha.taupe)
        }
    }
    
    private func performPurchase() {
        let generator = UIImpactFeedbackGenerator(style: .heavy)
        generator.impactOccurred()
        
        isPurchasing = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            isPurchasing = false
            dismiss()
        }
    }
}

// MARK: - Helpers

extension View {
    func glassEffect() -> some View {
        self.background(.ultraThinMaterial)
            .overlay(
                Circle()
                    .stroke(Color.white.opacity(0.2), lineWidth: 1)
            )
    }
}

#Preview {
    PaywallView()
        .environment(AppRootViewModel())
}

