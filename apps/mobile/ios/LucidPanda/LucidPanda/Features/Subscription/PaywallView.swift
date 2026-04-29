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
        case monthly, yearly
    }
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 32) {
                        // 1. Hero Section
                        heroSection
                        
                        // 2. Feature Matrix
                        featureMatrix
                        
                        // 3. Pricing Section
                        pricingSection
                        
                        // 4. Action Button
                        subscribeButton
                        
                        // 5. Footer
                        footerLinks
                    }
                    .padding(.vertical, 40)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
    }
    
    private var heroSection: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(Color.Alpha.brand.opacity(0.1))
                    .frame(width: 100, height: 100)
                    .blur(radius: 20)
                
                Image(systemName: "sparkles")
                    .font(.system(size: 50, weight: .light))
                    .foregroundStyle(Color.Alpha.brand)
                    .symbolEffect(.pulse)
            }
            
            Text("subscription.title")
                .font(.system(size: 32, weight: .black, design: .rounded))
                .foregroundStyle(Color.Alpha.textPrimary)
            
            Text("subscription.slogan")
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(Color.Alpha.taupe)
        }
        .padding(.top, 20)
    }
    
    private var featureMatrix: some View {
        VStack(spacing: 16) {
            featureRow(icon: "timeline.selection", title: "subscription.feature.timechain")
            featureRow(icon: "wand.and.stars", title: "subscription.feature.narrative")
            featureRow(icon: "chart.bar.xaxis", title: "subscription.feature.backtest")
            featureRow(icon: "folder.badge.plus", title: "subscription.feature.watchlist")
            featureRow(icon: "bell.badge.fill", title: "subscription.feature.alarm")
        }
        .padding(.horizontal, 24)
    }
    
    private func featureRow(icon: String, title: LocalizedStringKey) -> some View {
        LiquidGlassCard {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .foregroundStyle(Color.Alpha.brand)
                    .frame(width: 32)
                
                Text(title)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                
                Spacer()
                
                Image(systemName: "checkmark.seal.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(Color.Alpha.brand.opacity(0.5))
            }
        }
    }
    
    private var pricingSection: some View {
        HStack(spacing: 16) {
            planCard(type: .monthly, price: "$9.99", label: "subscription.plan.monthly")
            planCard(type: .yearly, price: "$79.99", label: "subscription.plan.yearly", badge: "subscription.plan.save")
        }
        .padding(.horizontal, 24)
    }
    
    private func planCard(type: PlanType, price: String, label: LocalizedStringKey, badge: LocalizedStringKey? = nil) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) { selectedPlan = type }
        } label: {
            VStack(spacing: 12) {
                if let badge = badge {
                    Text(badge)
                        .font(.system(size: 10, weight: .black))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.Alpha.brand)
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                } else {
                    Spacer().frame(height: 18)
                }
                
                Text(label)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(selectedPlan == type ? Color.Alpha.textPrimary : Color.Alpha.taupe)
                
                Text(price)
                    .font(.system(size: 24, weight: .black, design: .monospaced))
                    .foregroundStyle(selectedPlan == type ? Color.Alpha.brand : Color.Alpha.textPrimary)
                
                Text(type == .monthly ? "/ mo" : "/ year")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
            .background(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(selectedPlan == type ? Color.Alpha.brand.opacity(0.05) : Color.Alpha.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(selectedPlan == type ? Color.Alpha.brand : Color.Alpha.separator, lineWidth: selectedPlan == type ? 2 : 1)
            )
        }
        .buttonStyle(.plain)
    }
    
    private var subscribeButton: some View {
        Button {
            performPurchase()
        } label: {
            HStack {
                if isPurchasing {
                    ProgressView().tint(.white)
                } else {
                    Text("subscription.action.subscribe")
                        .font(.system(size: 18, weight: .black))
                }
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 60)
            .background(Color.Alpha.brand)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .shadow(color: Color.Alpha.brand.opacity(0.3), radius: 10, y: 5)
        }
        .buttonStyle(LiquidScaleButtonStyle())
        .padding(.horizontal, 24)
        .disabled(isPurchasing)
    }
    
    private var footerLinks: some View {
        VStack(spacing: 12) {
            Button("subscription.action.restore") {
                // Restore logic
            }
            .font(.system(size: 13, weight: .medium))
            .foregroundStyle(.secondary)
            
            HStack(spacing: 20) {
                Text("Terms of Service")
                Text("Privacy Policy")
            }
            .font(.system(size: 11))
            .foregroundStyle(.tertiary)
        }
    }
    
    private func performPurchase() {
        let generator = UIImpactFeedbackGenerator(style: .heavy)
        generator.impactOccurred()
        
        isPurchasing = true
        
        // Mock purchase delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            isPurchasing = false
            // In a real app, StoreKit 2 would handle this.
            // For now, we would trigger a state update if successful.
            dismiss()
        }
    }
}

#Preview {
    PaywallView()
        .environment(AppRootViewModel())
}
