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
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var sessions: [SessionRowDTO] = []
    @State private var isSessionsLoading = false
    @State private var isLoggingOut = false
    @State private var sessionErrorMessage: String?
    @State private var hasLoadedSessions = false

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
                Color.Alpha.background
                    .ignoresSafeArea()
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 28) {
                        profileHeader
                        profileEditCard
                        subscriptionCard // 🚀 New: Subscription Entry
                        accountSettingsCard
                        notificationsCard
                        securityCard

                        logoutCard
                    }
                    .padding(.top, 8)
                    .padding(.bottom, 32)
                }
                .refreshable {
                    await rootViewModel.fetchUserProfile()
                    if hasLoadedSessions {
                        await loadSessions()
                    }
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
            // Pre-warm the profile when opening settings
            await rootViewModel.fetchUserProfile()
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .paywall:
                PaywallView()
            default:
                EmptyView()
            }
        }
        .alert(String(localized: "settings.web.alert.title"), isPresented: $showWebPrompt) {
            Button("common.close", role: .cancel) {}
        } message: {
            Text("settings.web.alert.message")
        }
    }

    // MARK: - Sections

    private var subscriptionCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.section.subscription")
            premiumCard {
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

    // MARK: - Premium Card Container
    private func premiumCard<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(spacing: 0) {
            content()
        }
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .stroke(Color.Alpha.separator, lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.02), radius: 8, x: 0, y: 4)
        .padding(.horizontal, 20)
    }

    private func sectionHeader(title: LocalizedStringKey) -> some View {
        Text(title)
            .font(.system(size: 11, weight: .black))
            .foregroundStyle(Color.Alpha.taupe)
            .textCase(.uppercase)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 36)
            .padding(.bottom, 6)
    }

    // MARK: - Sections

    private var profileHeader: some View {
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
                                let response: AvatarUploadResponseDTO = try await APIClient.shared.upload(
                                    path: "/api/v1/auth/me/avatar",
                                    fileData: jpegData,
                                    fileName: "avatar.jpg",
                                    mimeType: "image/jpeg"
                                )
                                logger.info("Avatar uploaded: \(response.avatarUrl, privacy: .public)")
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

    private var accountSettingsCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.title")
            premiumCard {
                NavigationLink(destination: accountSettingsSubView) {
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

    private var profileEditCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.section.basic_info")
            premiumCard {
                NavigationLink(destination: profileEditSheet) {
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

    // MARK: - Profile Edit State
    @State private var profileName: String = ""
    @State private var profileNickname: String = ""
    @State private var profileGender: String = ""
    @State private var profileBirthday: Date = Date()
    @State private var profileHasBirthday: Bool = false
    @State private var profileLocation: String = ""
    @State private var isProfileSaving: Bool = false
    @State private var profileSaveSuccess: Bool = false
    @State private var profileSaveError: String? = nil

    private var accountSettingsSubView: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.section.account_actions")
                        premiumCard {
                            VStack(spacing: 0) {
                                NavigationLink(destination: passwordSheet) {
                                    settingsNavigationRow(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue, showDivider: true)
                                }
                                .buttonStyle(.plain)
                                
                                NavigationLink(destination: twoFactorSheet) {
                                    settingsNavigationRow(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange, showDivider: false)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.section.sessions")
                        premiumCard {
                            NavigationLink(destination: sessionsSheet) {
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
                                    
                                    Text(hasLoadedSessions ? "\(sessions.count)" : "—")
                                        .font(.system(size: 13, weight: .medium, design: .monospaced))
                                        .foregroundStyle(Color.Alpha.taupe)
                                    
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

    private var notificationsCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.section.notifications")
            premiumCard {
                settingsToggleRow(icon: "bell.badge.fill", titleKey: "settings.item.push_alert", color: .red, isOn: $pushAlertsEnabled, showDivider: true)
                settingsToggleRow(icon: "waveform.path.ecg", titleKey: "settings.item.signal_alert", color: .blue, isOn: $signalAlertsEnabled, showDivider: true)
                settingsToggleRow(icon: "chart.line.uptrend.xyaxis", titleKey: "settings.item.price_alert", color: .green, isOn: $priceAlertsEnabled, showDivider: false)
            }
        }
    }

    private var securityCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.section.security")
            premiumCard {
                settingsToggleRow(icon: "faceid", titleKey: "settings.item.biometric_unlock", color: .purple, isOn: $biometricUnlockEnabled, showDivider: false)
            }
        }
    }





    private var logoutCard: some View {
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

    private func actionTile(icon: String, titleKey: LocalizedStringKey, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(color.opacity(0.1))
                        .frame(width: 40, height: 40)
                    Image(systemName: icon)
                        .foregroundStyle(color)
                        .font(.system(size: 18, weight: .semibold))
                }

                Text(titleKey)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Color.Alpha.surface)
            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 4, style: .continuous)
                    .stroke(Color.Alpha.separator, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
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
    private func loadSessions() async {
        guard let refreshToken = AuthTokenStore.refreshToken() else {
            sessions = []
            hasLoadedSessions = true
            return
        }

        isSessionsLoading = true
        sessionErrorMessage = nil
        defer {
            isSessionsLoading = false
            hasLoadedSessions = true
        }

        do {
            let endpoint = SessionListEndpoint(refreshToken: refreshToken)
            sessions = try await APIClient.shared.request(endpoint)
        } catch {
            sessionErrorMessage = String(format: NSLocalizedString("settings.session.error.load_failed %@", comment: ""), error.localizedDescription)
        }
    }

    @MainActor
    private func revokeSession(_ sessionID: Int) async {
        sessionErrorMessage = nil
        do {
            let endpoint = SessionRevokeEndpoint(sessionID: sessionID)
            let _: MessageResponseDTO = try await APIClient.shared.request(endpoint)
            sessions.removeAll { $0.id == sessionID }
        } catch {
            sessionErrorMessage = String(format: NSLocalizedString("settings.session.error.revoke_failed %@", comment: ""), error.localizedDescription)
        }
    }

    @MainActor
    private func logoutCurrentSession() async {
        guard !isLoggingOut else { return }
        isLoggingOut = true
        defer { isLoggingOut = false }

        let refreshToken = AuthTokenStore.refreshToken()

        // 先本地退出，避免被网络请求阻塞导致界面卡顿。
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
                } catch {
                    // Backend logout best-effort only.
                }
            }
        }
    }

    private var profileEditSheet: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    // MARK: - Basic Info
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.section.basic_info")
                        premiumCard {
                            VStack(spacing: 0) {
                                // Email — read-only
                                settingsValueRow(label: "settings.field.email", value: rootViewModel.userProfile?.email ?? "—", showDivider: true)
                                
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.field.nickname"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                        .frame(width: 80, alignment: .leading)
                                    
                                    TextField(LocalizedStringKey("settings.field.nickname.placeholder"), text: $profileNickname)
                                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                                        .multilineTextAlignment(.trailing)
                                        .foregroundStyle(Color.Alpha.taupe)
                                }
                                .padding(.vertical, 14)
                                .padding(.horizontal, 16)
                            }
                        }
                    }

                    // MARK: - App Preferences
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.section.preferences")
                        premiumCard {
                            VStack(spacing: 0) {
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.item.language"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                    Spacer()
                                    Picker("", selection: $appLanguage) {
                                        Text("settings.language.system").tag("system")
                                        Text("settings.language.en").tag("en")
                                        Text("settings.language.zh").tag("zh-Hans")
                                    }
                                    .pickerStyle(.menu)
                                    .labelsHidden()
                                    .tint(Color.Alpha.brand)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 16)
                                
                                Divider()
                                    .background(Color.Alpha.separator)
                                    .padding(.leading, 16)
                                
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.item.appearance"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                    Spacer()
                                    Picker("", selection: $appAppearance) {
                                        Text("common.system").tag("system")
                                        Text("common.light").tag("light")
                                        Text("common.dark").tag("dark")
                                    }
                                    .pickerStyle(.menu)
                                    .labelsHidden()
                                    .tint(Color.Alpha.brand)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 16)
                            }
                        }
                    }

                    // MARK: - Gender
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.field.gender")
                        premiumCard {
                            HStack(spacing: 16) {
                                Text(LocalizedStringKey("settings.field.gender"))
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(Color.Alpha.textPrimary)
                                Spacer()
                                Picker("", selection: $profileGender) {
                                    Text(LocalizedStringKey("settings.field.gender.unset")).tag("")
                                    Text(LocalizedStringKey("settings.field.gender.male")).tag("male")
                                    Text(LocalizedStringKey("settings.field.gender.female")).tag("female")
                                }
                                .pickerStyle(.menu)
                                .labelsHidden()
                                .tint(Color.Alpha.brand)
                            }
                            .padding(.vertical, 8)
                            .padding(.horizontal, 16)
                        }
                    }
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle(LocalizedStringKey("settings.section.basic_info"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await saveProfile() }
                } label: {
                    if isProfileSaving {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.brand)
                    }
                }
                .disabled(isProfileSaving)
            }
        }
        .alert("common.success", isPresented: $profileSaveSuccess) {
            Button("common.ok", role: .cancel) {}
        } message: {
            Text("settings.profile.save_success")
        }
        .alert("common.error", isPresented: Binding(
            get: { profileSaveError != nil },
            set: { if !$0 { profileSaveError = nil } }
        )) {
            Button("common.ok", role: .cancel) {}
        } message: {
            Text(profileSaveError ?? "")
        }
        .onAppear {
            if let profile = rootViewModel.userProfile {
                profileNickname = profile.nickname ?? ""
                profileGender   = profile.gender ?? ""
            }
        }
    }

    private func settingsValueRow(label: LocalizedStringKey, value: String, showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                Text(label)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .frame(width: 80, alignment: .leading)
                
                Spacer()
                
                Text(value)
                    .font(.system(size: 14, weight: .medium, design: .monospaced))
                    .foregroundStyle(Color.Alpha.taupe)
                    .lineLimit(1)
            }
            .padding(.vertical, 14)
            .padding(.horizontal, 16)
            
            if showDivider {
                Divider()
                    .background(Color.Alpha.separator)
                    .padding(.leading, 16)
            }
        }
    }


    private func saveProfile() async {
        isProfileSaving = true
        defer { isProfileSaving = false }

        struct ProfileUpdatePayload: Encodable {
            var name: String?
            var nickname: String?
            var gender: String?
            var birthday: String?
            var languagePreference: String?

            enum CodingKeys: String, CodingKey {
                case name, nickname, gender, birthday
                case languagePreference = "language_preference"
            }
        }

        let birthdayStr: String?
        if profileHasBirthday {
            let fmt = DateFormatter()
            fmt.dateFormat = "yyyy-MM-dd"
            birthdayStr = fmt.string(from: profileBirthday)
        } else {
            birthdayStr = nil
        }

        let langToSave = appLanguage == "system" ? nil : appLanguage

        let payload = ProfileUpdatePayload(
            name: profileName.isEmpty ? nil : profileName,
            nickname: profileNickname.isEmpty ? nil : profileNickname,
            gender: profileGender.isEmpty ? nil : profileGender,
            birthday: birthdayStr,
            languagePreference: langToSave
        )

        do {
            let _: UserProfileDTO = try await APIClient.shared.send(
                path: "/api/v1/auth/me",
                method: "PATCH",
                body: payload
            )
            await rootViewModel.fetchUserProfile()
            profileSaveSuccess = true
        } catch {
            profileSaveError = error.localizedDescription
        }
    }

    private var passwordSheet: some View {
        ZStack {
            Color.Alpha.background
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.dialog.change_password.title")
                        premiumCard {
                            VStack(alignment: .leading, spacing: 16) {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("settings.field.current_password")
                                        .font(.system(size: 11, weight: .black))
                                        .foregroundStyle(Color.Alpha.taupe)
                                        .textCase(.uppercase)
                                    SecureField("settings.field.current_password", text: $currentPassword)
                                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                                        .padding(14)
                                        .background(Color.Alpha.surfaceDim)
                                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                                .stroke(Color.Alpha.separator, lineWidth: 1)
                                        )
                                }

                                VStack(alignment: .leading, spacing: 8) {
                                    Text("settings.field.new_password")
                                        .font(.system(size: 11, weight: .black))
                                        .foregroundStyle(Color.Alpha.taupe)
                                        .textCase(.uppercase)
                                    SecureField("settings.field.new_password", text: $newPassword)
                                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                                        .padding(14)
                                        .background(Color.Alpha.surfaceDim)
                                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                                .stroke(Color.Alpha.separator, lineWidth: 1)
                                        )
                                }
                            }
                            .padding(16)
                        }
                    }

                    if let errorMessage = passwordErrorMessage {
                        Text(errorMessage)
                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                            .foregroundStyle(errorMessage.contains("✅") ? Color.Alpha.up : Color.Alpha.down)
                            .padding(.horizontal, 32)
                    }
                }
                .padding(.top, 24)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle("settings.dialog.change_password.title")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await changePassword() }
                } label: {
                    if isPasswordChanging {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle((currentPassword.isEmpty || newPassword.count < 6) ? Color.Alpha.taupe.opacity(0.3) : Color.Alpha.brand)
                    }
                }
                .allowsHitTesting(!(currentPassword.isEmpty || newPassword.count < 6 || isPasswordChanging))
            }
        }
    }
    
    @State private var isPasswordChanging = false
    @State private var passwordErrorMessage: String?
    
    @MainActor
    private func changePassword() async {
        isPasswordChanging = true
        passwordErrorMessage = nil
        
        do {
            let payload = ChangePasswordPayload(
                currentPassword: currentPassword,
                newPassword: newPassword
            )
            
            let response: MessageResponseDTO = try await APIClient.shared.send(
                path: "/api/v1/user/change-password",
                method: "POST",
                body: payload
            )
            
            currentPassword = ""
            newPassword = ""
            
            // 显示成功提示
            passwordErrorMessage = NSLocalizedString("settings.password.success", comment: "")
            logger.info("Password changed: \(response.message, privacy: .public)")
        } catch {
            passwordErrorMessage = String(format: NSLocalizedString("settings.password.error_format %@", comment: ""), error.localizedDescription)
        }
        
        isPasswordChanging = false
    }

    @State private var is2FAEnabled: Bool = false
    @State private var showing2FASetupModal: Bool = false
    @State private var twoFAQRImageData: Data? = nil
    @State private var twoFASecret: String = ""
    @State private var twoFACode: String = ""
    @State private var is2FALoading: Bool = false
    @State private var twoFAErrorMessage: String? = nil
    @State private var is2FAVerifying: Bool = false

    private var twoFactorSheet: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 4) {
                    // Toggle row
                    premiumCard {
                        HStack {
                            Text(LocalizedStringKey("settings.two_factor.authenticator_app"))
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            Spacer()
                            Toggle("", isOn: $is2FAEnabled)
                                .labelsHidden()
                                .tint(Color.Alpha.brand)
                        }
                        .padding(16)
                    }
                    .onChange(of: is2FAEnabled) { oldValue, newValue in
                        if newValue && !oldValue {
                            twoFAQRImageData = nil
                            twoFASecret = ""
                            twoFACode = ""
                            twoFAErrorMessage = nil
                            showing2FASetupModal = true
                        }
                    }
                    
                    Text(LocalizedStringKey("settings.two_factor.hint_description"))
                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                        .foregroundStyle(Color.Alpha.taupe)
                        .padding(.horizontal, 36)
                        .padding(.top, 8)
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle(LocalizedStringKey("settings.dialog.two_factor.title"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(action: { dismiss() }) {
                    Image(systemName: "checkmark")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Color.Alpha.brand)
                }
            }
        }
        .sheet(isPresented: $showing2FASetupModal) {
            twoFactorSetupModal
        }
    }
    
    private var twoFactorSetupModal: some View {
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 24) {
                        // QR Code display
                        Group {
                            if is2FALoading {
                                ProgressView()
                                    .frame(width: 180, height: 180)
                            } else if let data = twoFAQRImageData,
                                      let uiImage = UIImage(data: data) {
                                Image(uiImage: uiImage)
                                    .resizable()
                                    .interpolation(.none)
                                    .scaledToFit()
                                    .frame(width: 180, height: 180)
                                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                                            .stroke(Color.Alpha.separator, lineWidth: 1)
                                    )
                            } else {
                                Image(systemName: "qrcode")
                                    .font(.system(size: 80, weight: .ultraLight))
                                    .foregroundStyle(Color.Alpha.taupe)
                                    .frame(width: 180, height: 180)
                                    .background(Color.Alpha.surfaceDim)
                                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                            }
                        }
                        .padding(.top, 24)

                        Text(LocalizedStringKey("settings.dialog.two_factor.hint"))
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(Color.Alpha.taupe)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 32)

                        // Code input
                        TextField("000000", text: $twoFACode)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.center)
                            .font(.system(size: 32, weight: .black, design: .monospaced))
                            .padding(16)
                            .background(Color.Alpha.surfaceDim)
                            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 4, style: .continuous)
                                    .stroke(Color.Alpha.separator, lineWidth: 1)
                            )
                            .padding(.horizontal, 48)

                        if let err = twoFAErrorMessage {
                            Text(err)
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(Color.Alpha.down)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 32)
                        }

                        Button(action: {
                            Task { await verify2FA() }
                        }) {
                            Group {
                                if is2FAVerifying {
                                    ProgressView()
                                        .tint(.white)
                                } else {
                                    Text("settings.security.verify_and_enable")
                                        .font(.system(size: 15, weight: .black))
                                        .textCase(.uppercase)
                                }
                            }
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(twoFACode.count == 6 ? Color.Alpha.brand : Color.Alpha.brand.opacity(0.3))
                            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                            .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
                        }
                        .disabled(twoFACode.count != 6 || is2FAVerifying)
                        .padding(.horizontal, 32)
                    }
                    .padding(.bottom, 32)
                }
            }
            .presentationDetents([.fraction(0.75), .large])
            .presentationDragIndicator(.visible)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        is2FAEnabled = false
                        showing2FASetupModal = false
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                }
            }
            .task {
                await fetchTwoFAQRCode()
            }
        }
    }

    private func fetchTwoFAQRCode() async {
        is2FALoading = true
        defer { is2FALoading = false }
        do {
            struct TwoFASetupResponse: Decodable {
                let secret: String
                let qrCodeUrl: String
                enum CodingKeys: String, CodingKey {
                    case secret
                    case qrCodeUrl = "qr_code_url"
                }
            }
            struct EmptyBody: Encodable {}
            let resp: TwoFASetupResponse = try await APIClient.shared.send(
                path: "/api/v1/auth/2fa/setup",
                body: EmptyBody()
            )
            twoFASecret = resp.secret
            // qr_code_url is "data:image/png;base64,<data>"
            let base64Part = resp.qrCodeUrl
                .replacingOccurrences(of: "data:image/png;base64,", with: "")
            if let data = Data(base64Encoded: base64Part, options: .ignoreUnknownCharacters) {
                twoFAQRImageData = data
            }
        } catch {
            twoFAErrorMessage = NSLocalizedString("settings.two_factor.error.load_qr_failed", comment: "")
        }
    }

    private func verify2FA() async {
        guard !twoFASecret.isEmpty else { return }
        is2FAVerifying = true
        twoFAErrorMessage = nil
        defer { is2FAVerifying = false }
        do {
            struct VerifyPayload: Encodable {
                let secret: String
                let code: String
            }
            let _: MessageResponseDTO = try await APIClient.shared.send(
                path: "/api/v1/auth/2fa/verify",
                body: VerifyPayload(secret: twoFASecret, code: twoFACode)
            )
            is2FAEnabled = true
            showing2FASetupModal = false
        } catch {
            twoFAErrorMessage = NSLocalizedString("settings.two_factor.error.invalid_code", comment: "")
        }
    }

    private var sessionsSheet: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        HStack {
                            sectionHeader(title: "settings.active_sessions")
                            Spacer()
                            Button {
                                Task { await loadSessions() }
                            } label: {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(Color.Alpha.brand)
                            }
                            .padding(.horizontal, 36)
                            .padding(.bottom, 6)
                            .disabled(isSessionsLoading)
                        }

                        premiumCard {
                            sessionListContent
                                .padding(16)
                        }
                    }

                    if let sessionErrorMessage {
                        VStack(spacing: 0) {
                            sectionHeader(title: "common.error")
                            premiumCard {
                                Text(sessionErrorMessage)
                                    .font(.system(size: 13, weight: .bold, design: .monospaced))
                                    .foregroundStyle(Color.Alpha.down)
                                    .padding(16)
                            }
                        }
                    }
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
            .refreshable {
                await loadSessions()
            }
        }
        .navigationTitle(LocalizedStringKey("settings.active_sessions"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(action: { dismiss() }) {
                    Image(systemName: "checkmark")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Color.Alpha.brand)
                }
            }
        }
        .task {
            if !hasLoadedSessions {
                await loadSessions()
            }
        }
    }

    @ViewBuilder
    private var sessionListContent: some View {
        if isSessionsLoading {
            HStack(spacing: 12) {
                ProgressView().scaleEffect(0.8)
                Text("settings.session.loading")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.taupe)
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical, 12)
        } else if sessions.isEmpty {
            Text("settings.session.empty")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(Color.Alpha.taupe)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 12)
        } else {
            VStack(spacing: 16) {
                ForEach(sessions) { session in
                    HStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .fill(session.isCurrent ? Color.Alpha.brand.opacity(0.1) : Color.Alpha.taupe.opacity(0.1))
                                .frame(width: 32, height: 32)
                            Image(systemName: session.isCurrent ? "iphone" : "desktopcomputer")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(session.isCurrent ? Color.Alpha.brand : Color.Alpha.taupe)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(session.deviceName)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            Text(session.metaLine)
                                .font(.system(size: 12, weight: .medium, design: .monospaced))
                                .foregroundStyle(Color.Alpha.taupe)
                        }
                        Spacer()

                        if session.isCurrent {
                            Text("settings.session.current")
                                .font(.system(size: 10, weight: .black))
                                .textCase(.uppercase)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.Alpha.brand.opacity(0.1))
                                .foregroundStyle(Color.Alpha.brand)
                                .clipShape(RoundedRectangle(cornerRadius: 2, style: .continuous))
                        } else {
                            Toggle("", isOn: Binding(
                                get: { true },
                                set: { newValue in
                                    if !newValue {
                                        Task { await revokeSession(session.id) }
                                    }
                                }
                            ))
                            .labelsHidden()
                            .tint(Color.Alpha.brand)
                            .scaleEffect(0.8)
                        }
                    }

                    if session.id != sessions.last?.id {
                        Divider()
                            .background(Color.Alpha.separator)
                    }
                }
            }
        }
    }
}

private enum ActiveSheet: Int, Identifiable {
    case password
    case twoFactor
    case sessions
    case paywall // 🚀 New

    var id: Int { rawValue }
}

private struct SessionListEndpoint: Endpoint {
    let refreshToken: String
    let path = "/api/v1/auth/sessions"
    let method: HTTPMethod = .get
    var headers: [String : String]? { ["X-Refresh-Token": refreshToken] }
}

private struct SessionRevokeEndpoint: Endpoint {
    let sessionID: Int
    var path: String { "/api/v1/auth/sessions/\(sessionID)" }
    let method: HTTPMethod = .delete
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

private struct SessionRowDTO: Decodable, Identifiable {
    let id: Int
    let deviceInfo: [String: String]?
    let ipAddress: String?
    let createdAt: Date
    let lastActiveAt: Date?
    let isCurrent: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case deviceInfo = "device_info"
        case ipAddress = "ip_address"
        case createdAt = "created_at"
        case lastActiveAt = "last_active_at"
        case isCurrent = "is_current"
    }

    var deviceName: String {
        if let name = deviceInfo?["name"], !name.isEmpty {
            return name
        }
        return "Unknown Device"
    }

    var metaLine: String {
        let active = (lastActiveAt ?? createdAt).formatted(date: .abbreviated, time: .shortened)
        return active
    }
}



private struct ChangePasswordPayload: Encodable {
    let currentPassword: String
    let newPassword: String
    
    enum CodingKeys: String, CodingKey {
        case currentPassword = "current_password"
        case newPassword = "new_password"
    }
}

private struct AvatarUploadResponseDTO: Decodable {
    let avatarUrl: String
    
    enum CodingKeys: String, CodingKey {
        case avatarUrl = "avatar_url"
    }
}
