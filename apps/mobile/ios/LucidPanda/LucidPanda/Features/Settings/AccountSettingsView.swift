import SwiftUI
import AlphaDesign
import AlphaData

struct AccountSettingsView: View {
    @Environment(AppRootViewModel.self) private var rootViewModel

    var body: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.section.account_actions")
                        PremiumCard {
                            VStack(spacing: 0) {
                                NavigationLink(destination: PasswordChangeView()) {
                                    settingsNavigationRow(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue, showDivider: true)
                                }
                                .buttonStyle(.plain)
                                
                                NavigationLink(destination: TwoFactorSetupView(is2FAEnabled: rootViewModel.userProfile?.isTwoFaEnabled ?? false)) {
                                    settingsNavigationRow(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange, showDivider: false)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    
                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.section.sessions")
                        PremiumCard {
                            NavigationLink(destination: SessionsView()) {
                                HStack(spacing: 16) {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                                            .fill(Color.blue.opacity(0.1))
                                            .frame(width: 32, height: 32)
                                        Image(systemName: "desktopcomputer.and.iphone")
                                            .font(.system(size: 14, weight: .semibold))
                                            .foregroundStyle(Color.blue)
                                    }
                                    
                                    Text("settings.active_sessions")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                    
                                    Spacer()
                                    
                                    Image(systemName: "chevron.right")
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundStyle(Color.Alpha.taupe)
                                }
                                .padding(.vertical, 12)
                                .padding(.horizontal, 16)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle(LocalizedStringKey("settings.account_security"))
        .navigationBarTitleDisplayMode(.inline)
    }

    private func settingsNavigationRow(icon: String, titleKey: LocalizedStringKey, color: Color, showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                ZStack {
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(color.opacity(0.1))
                        .frame(width: 32, height: 32)
                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(color)
                }
                
                Text(titleKey)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.Alpha.taupe)
            }
            .padding(.vertical, 12)
            .padding(.horizontal, 16)
            
            if showDivider {
                Divider()
                    .background(Color.Alpha.separator)
                    .padding(.leading, 64)
            }
        }
    }
}
