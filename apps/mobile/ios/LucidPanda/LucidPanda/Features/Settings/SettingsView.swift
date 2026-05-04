import SwiftUI
import PhotosUI
import AlphaDesign
import AlphaData
import AlphaCore
import OSLog

struct SettingsView: View {
    private let logger = AppLog.root
    @Environment(AppRootViewModel.self) private var rootViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var showWebPrompt = false
    @State private var activeSheet: ActiveSheet?
    @State private var avatarItem: PhotosPickerItem?
    @State private var avatarImage: Image?
    @State private var isLoggingOut = false

    @AppStorage("settings.notifications.push") private var pushAlertsEnabled = true
    @AppStorage("settings.notifications.signal") private var signalAlertsEnabled = true
    @AppStorage("settings.notifications.price") private var priceAlertsEnabled = true
    @AppStorage("settings.security.biometric_unlock") private var biometricUnlockEnabled = false
    @AppStorage("appLanguage") private var appLanguage: String = "system"
    @AppStorage("appAppearance") private var appAppearance: String = "system"

    let showCloseButton: Bool

    init(showCloseButton: Bool = false) {
        self.showCloseButton = showCloseButton
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 28) {
                        profileHeader()
                        profileEditCard()
                        subscriptionCard()
                        accountSettingsCard()
                        notificationsCard()
                        securityCard()

                        logoutCard()
                    }
                    .padding(.top, 8)
                    .padding(.bottom, 32)
                }
                .refreshable {
                    await rootViewModel.fetchUserProfile()
                }
            }
            .navigationTitle("settings.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if showCloseButton {
                    ToolbarItem(placement: .topBarLeading) {
                        Button(action: { dismiss() }) {
                            Image(systemName: "xmark")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(.primary)
                        }
                    }
                }
            }
        }
        .task {
            await rootViewModel.fetchUserProfile()
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .paywall:
                PaywallView()
            }
        }
        .alert(String(localized: "settings.web.alert.title"), isPresented: $showWebPrompt) {
            Button("common.close", role: .cancel) {}
        } message: {
            Text("settings.web.alert.message")
        }
    }

    // MARK: - Sections

    @ViewBuilder
    private func subscriptionCard() -> some View {
        VStack(spacing: 0) {
            SettingsSectionHeader(title: "settings.section.subscription")
            PremiumCard {
                Button {
                    activeSheet = .paywall
                } label: {
                    HStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(rootViewModel.isPro ? Color.Alpha.brand.opacity(0.1) : Color.Alpha.brand.opacity(0.1))
                                .frame(width: 32, height: 32)
                            Image(systemName: rootViewModel.isPro ? "seal.fill" : "sparkles")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color.Alpha.brand)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(LocalizedStringKey("settings.section.subscription"))
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            
                            Text(LocalizedStringKey(rootViewModel.isPro ? "settings.subscription.status.pro" : "settings.subscription.upgrade"))
                                .font(.system(size: 12, weight: .medium, design: .monospaced))
                                .foregroundStyle(rootViewModel.isPro ? Color.Alpha.brand : Color.Alpha.taupe)
                        }

                        Spacer()

                        if rootViewModel.isPro {
                            Text("PRO")
                                .font(.system(size: 10, weight: .black))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.Alpha.brand)
                                .foregroundStyle(.white)
                                .clipShape(Capsule())
                        }

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

    @ViewBuilder
    private func profileHeader() -> some View {
        VStack(spacing: 16) {
            let displayEmail = rootViewModel.userProfile?.email ?? "root@lucidpanda.com"
            let initial = String(displayEmail.prefix(1)).uppercased()
            let displayName = rootViewModel.userProfile?.displayName ?? String(localized: "settings.user.display_name")
            
            ZStack(alignment: .bottomTrailing) {
                Group {
                    if let avatarImage {
                        avatarImage
                            .resizable()
                            .scaledToFill()
                    } else if let avatarUrl = rootViewModel.userProfile?.avatarUrl {
                        let absoluteUrl = URL(string: avatarUrl, relativeTo: APIClient.shared.baseURL)
                        AsyncImage(url: absoluteUrl) { image in
                            image
                                .resizable()
                                .scaledToFill()
                        } placeholder: {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(Color.Alpha.surfaceDim)
                        }
                    } else {
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill(Color.Alpha.primaryContainer)
                            .overlay(
                                Text(initial)
                                    .font(.system(size: 36, weight: .heavy, design: .rounded))
                                    .foregroundStyle(.white)
                            )
                    }
                }
                .frame(width: 88, height: 88)
                .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .stroke(Color.Alpha.brand, lineWidth: 2)
                )

                PhotosPicker(selection: $avatarItem, matching: .images) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .fill(Color.Alpha.surface)
                            .frame(width: 28, height: 28)
                            .shadow(color: .black.opacity(0.1), radius: 2)
                        Image(systemName: "camera.fill")
                            .font(.system(size: 14))
                            .foregroundStyle(Color.Alpha.brand)
                    }
                }
                .onChange(of: avatarItem) { _, newItem in
                    Task {
                        if let data = try? await newItem?.loadTransferable(type: Data.self),
                           let uiImage = UIImage(data: data),
                           let jpegData = uiImage.jpegData(compressionQuality: 0.8) {
                            avatarImage = Image(uiImage: uiImage)
                            
                            do {
                                let _: AvatarUploadResponseDTO = try await APIClient.shared.upload(
                                    path: "/api/v1/auth/me/avatar",
                                    fileData: jpegData,
                                    fileName: "avatar.jpg",
                                    mimeType: "image/jpeg"
                                )
                                await rootViewModel.fetchUserProfile()
                            } catch {
                                logger.error("Avatar upload failed: \(error.localizedDescription, privacy: .public)")
                            }
                        }
                    }
                }
            }

            VStack(spacing: 6) {
                Text(displayName)
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                Text(displayEmail)
                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                    .foregroundStyle(Color.Alpha.taupe)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 16)
    }

    @ViewBuilder
    private func accountSettingsCard() -> some View {
        VStack(spacing: 0) {
            SettingsSectionHeader(title: "settings.title")
            PremiumCard {
                NavigationLink(destination: AccountSettingsView()) {
                    HStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(Color.blue.opacity(0.1))
                                .frame(width: 32, height: 32)
                            Image(systemName: "person.badge.shield.checkmark.fill")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color.blue)
                        }
                        
                        Text("settings.account_security")
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

    @ViewBuilder
    private func profileEditCard() -> some View {
        VStack(spacing: 0) {
            SettingsSectionHeader(title: "settings.section.basic_info")
            PremiumCard {
                NavigationLink(destination: ProfileEditView(userProfile: rootViewModel.userProfile)) {
                    HStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(Color.indigo.opacity(0.1))
                                .frame(width: 32, height: 32)
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(Color.indigo)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(LocalizedStringKey("settings.section.basic_info"))
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            if let nickname = rootViewModel.userProfile?.nickname, !nickname.isEmpty {
                                Text(nickname)
                                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                                    .foregroundStyle(Color.Alpha.taupe)
                            } else if let email = rootViewModel.userProfile?.email {
                                Text(email)
                                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                                    .foregroundStyle(Color.Alpha.taupe)
                            }
                        }

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

    @ViewBuilder
    private func notificationsCard() -> some View {
        VStack(spacing: 0) {
            SettingsSectionHeader(title: "settings.section.notifications")
            PremiumCard {
                settingsToggleRow(icon: "bell.badge.fill", titleKey: "settings.item.push_alert", color: .red, isOn: $pushAlertsEnabled, showDivider: true)
                settingsToggleRow(icon: "waveform.path.ecg", titleKey: "settings.item.signal_alert", color: .blue, isOn: $signalAlertsEnabled, showDivider: true)
                settingsToggleRow(icon: "chart.line.uptrend.xyaxis", titleKey: "settings.item.price_alert", color: .green, isOn: $priceAlertsEnabled, showDivider: false)
            }
        }
    }

    @ViewBuilder
    private func securityCard() -> some View {
        VStack(spacing: 0) {
            SettingsSectionHeader(title: "settings.section.security")
            PremiumCard {
                settingsToggleRow(icon: "faceid", titleKey: "settings.item.biometric_unlock", color: .purple, isOn: $biometricUnlockEnabled, showDivider: false)
            }
        }
    }

    @ViewBuilder
    private func logoutCard() -> some View {
        Button(action: { Task { await logoutCurrentSession() } }) {
            Text("settings.action.logout")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
        }
        .background(Color.Alpha.down)
        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
        .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
        .padding(.horizontal, 20)
        .padding(.top, 10)
        .disabled(isLoggingOut)
        .opacity(isLoggingOut ? 0.5 : 1)
    }

    private func settingsToggleRow(icon: String, titleKey: LocalizedStringKey, color: Color, isOn: Binding<Bool>, showDivider: Bool) -> some View {
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
                
                Toggle("", isOn: isOn)
                    .labelsHidden()
                    .tint(Color.Alpha.brand)
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

    @MainActor
    private func logoutCurrentSession() async {
        guard !isLoggingOut else { return }
        isLoggingOut = true
        defer { isLoggingOut = false }

        let refreshToken = AuthTokenStore.refreshToken()
        rootViewModel.updateState(to: .unauthenticated)
        dismiss()

        if let refreshToken {
            Task.detached(priority: .utility) {
                do {
                    let _: MessageResponseDTO = try await APIClient.shared.send(
                        path: "/api/v1/auth/logout",
                        method: "POST",
                        body: LogoutPayload(refreshToken: refreshToken)
                    )
                } catch {}
            }
        }
    }
}

private enum ActiveSheet: Int, Identifiable {
    case paywall
    var id: Int { rawValue }
}

private struct LogoutPayload: Encodable {
    let refreshToken: String
    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct MessageResponseDTO: Decodable {
    let message: String
}

private struct AvatarUploadResponseDTO: Decodable {
    let avatarUrl: String
    enum CodingKeys: String, CodingKey {
        case avatarUrl = "avatar_url"
    }
}
