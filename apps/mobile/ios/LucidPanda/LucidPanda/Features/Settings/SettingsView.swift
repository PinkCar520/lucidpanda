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

    let showCloseButton: Bool

    init(showCloseButton: Bool = false) {
        self.showCloseButton = showCloseButton
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color(uiColor: .systemGroupedBackground)
                    .ignoresSafeArea()
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 28) {
                        profileHeader
                        profileEditCard
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
        .alert(String(localized: "settings.web.alert.title"), isPresented: $showWebPrompt) {
            Button("common.close", role: .cancel) {}
        } message: {
            Text("settings.web.alert.message")
        }
    }

    // MARK: - Sections

    // MARK: - Premium Card Container
    private func premiumCard<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(spacing: 0) {
            content()
        }
        .background(Color(uiColor: .secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .padding(.horizontal, 20)
    }

    private func sectionHeader(title: LocalizedStringKey) -> some View {
        Text(title)
            .font(.system(size: 13, weight: .medium))
            .foregroundStyle(.secondary)
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
                            Circle().fill(Color(uiColor: .systemFill))
                        }
                    } else {
                        Circle()
                            .fill(Color.blue)
                            .overlay(
                                Text(initial)
                                    .font(.system(size: 36, weight: .heavy, design: .rounded))
                                    .foregroundStyle(.white)
                            )
                    }
                }
                .frame(width: 88, height: 88)
                .clipShape(Circle())

                PhotosPicker(selection: $avatarItem, matching: .images) {
                    ZStack {
                        Circle()
                            .fill(Color(uiColor: .systemBackground))
                            .frame(width: 28, height: 28)
                        Image(systemName: "camera.fill")
                            .font(.system(size: 14))
                            .foregroundStyle(Color.blue)
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
                    .font(.system(size: 24, weight: .medium))
                    .foregroundStyle(.primary)
                Text(displayEmail)
                    .font(.system(size: 15, weight: .medium))
                    .foregroundStyle(.secondary)
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
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .fill(Color.blue)
                                .frame(width: 32, height: 32)
                            Image(systemName: "person.badge.shield.checkmark.fill")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(.white)
                        }
                        
                        Text("settings.account_security")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(.primary)
                        
                        Spacer()
                        
                        Image(systemName: "chevron.right")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(Color(uiColor: .tertiaryLabel))
                    }
                    .padding(.vertical, 10)
                    .padding(.horizontal, 16)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var profileEditCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "settings.section.basic_info")
            NavigationLink(destination: profileEditSheet) {
                HStack(spacing: 16) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(Color.indigo)
                            .frame(width: 32, height: 32)
                        Image(systemName: "person.crop.circle.fill")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(.white)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(LocalizedStringKey("settings.section.basic_info"))
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(.primary)
                        if let nickname = rootViewModel.userProfile?.nickname, !nickname.isEmpty {
                            Text(nickname)
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                        } else if let email = rootViewModel.userProfile?.email {
                            Text(email)
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                        }
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Color(uiColor: .tertiaryLabel))
                }
                .padding(.vertical, 12)
                .padding(.horizontal, 16)
            }
            .buttonStyle(.plain)
            .background(Color(uiColor: .secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .padding(.horizontal, 16)
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
        List {
            Section(header: Text(LocalizedStringKey("settings.section.account_actions"))) {
                NavigationLink(destination: passwordSheet) {
                    HStack(spacing: 12) {
                        Image(systemName: "lock.shield.fill")
                            .foregroundStyle(.blue)
                            .frame(width: 24)
                        Text(LocalizedStringKey("settings.action.change_password"))
                            .foregroundStyle(.primary)
                    }
                }
                
                NavigationLink(destination: twoFactorSheet) {
                    HStack(spacing: 12) {
                        Image(systemName: "key.viewfinder")
                            .foregroundStyle(.orange)
                            .frame(width: 24)
                        Text(LocalizedStringKey("settings.action.two_factor"))
                            .foregroundStyle(.primary)
                    }
                }
                
            }
            
            Section(header: Text(LocalizedStringKey("settings.section.sessions"))) {
                NavigationLink(destination: sessionsSheet) {
                    HStack(spacing: 12) {
                        Image(systemName: "desktopcomputer.and.iphone")
                            .foregroundStyle(.blue)
                            .frame(width: 24)
                        Text(LocalizedStringKey("settings.active_sessions"))
                            .foregroundStyle(.primary)
                        Spacer()
                        Text(hasLoadedSessions ? "\(sessions.count)" : "—")
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle(LocalizedStringKey("settings.account_security"))
        .navigationBarTitleDisplayMode(.inline)
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
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
        }
        .background(Color.red.opacity(0.9))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .padding(.horizontal, 20)
        .padding(.top, 10)
        .disabled(isLoggingOut)
        .opacity(isLoggingOut ? 0.5 : 1)
    }

    private func actionTile(icon: String, titleKey: LocalizedStringKey, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 12) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.12))
                        .frame(width: 40, height: 40)
                    Image(systemName: icon)
                        .foregroundStyle(color)
                        .font(.system(size: 18, weight: .semibold))
                }

                Text(titleKey)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(.primary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Color(uiColor: .tertiarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func settingsToggleRow(icon: String, titleKey: LocalizedStringKey, color: Color, isOn: Binding<Bool>, showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                ZStack {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(color)
                        .frame(width: 32, height: 32)
                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                }
                
                Text(titleKey)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.primary)
                
                Spacer()
                
                Toggle("", isOn: isOn)
                    .labelsHidden()
            }
            .padding(.vertical, 10)
            .padding(.horizontal, 16)
            
            if showDivider {
                Divider()
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
            sessionErrorMessage = "Failed to load sessions: \(error.localizedDescription)"
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
            sessionErrorMessage = "Failed to revoke session: \(error.localizedDescription)"
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
        List {
            // MARK: - Basic Info
            Section(header: Text(LocalizedStringKey("settings.section.basic_info"))) {
                // Email — read-only
                HStack {
                    Text(LocalizedStringKey("settings.field.email"))
                        .frame(width: 80, alignment: .leading)
                    Spacer()
                    Text(rootViewModel.userProfile?.email ?? "—")
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                HStack {
                    Text(LocalizedStringKey("settings.field.nickname"))
                        .frame(width: 80, alignment: .leading)
                    TextField(LocalizedStringKey("settings.field.nickname.placeholder"), text: $profileNickname)
                        .multilineTextAlignment(.trailing)
                        .foregroundStyle(.secondary)
                }
            }

            // MARK: - Language Preference
            Section(header: Text(LocalizedStringKey("settings.item.language"))) {
                HStack {
                    Text(LocalizedStringKey("settings.item.language"))
                    Spacer()
                    Picker("", selection: $appLanguage) {
                        Text("settings.language.system").tag("system")
                        Text("settings.language.en").tag("en")
                        Text("settings.language.zh").tag("zh-Hans")
                    }
                    .pickerStyle(.menu)
                    .labelsHidden()
                }
            }

            // MARK: - Gender
            Section(header: Text(LocalizedStringKey("settings.field.gender"))) {
                HStack {
                    Text(LocalizedStringKey("settings.field.gender"))
                    Spacer()
                    Picker("", selection: $profileGender) {
                        Text(LocalizedStringKey("settings.field.gender.unset")).tag("")
                        Text(LocalizedStringKey("settings.field.gender.male")).tag("male")
                        Text(LocalizedStringKey("settings.field.gender.female")).tag("female")
                    }
                    .pickerStyle(.menu)
                    .labelsHidden()
                }
            }
        }
        .listStyle(.insetGrouped)
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
                            .foregroundStyle(.blue)
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
            Color(uiColor: .systemGroupedBackground)
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        sectionHeader(title: "settings.dialog.change_password.title")
                        premiumCard {
                            VStack(alignment: .leading, spacing: 16) {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("settings.field.current_password")
                                        .font(.system(size: 13, weight: .semibold))
                                        .foregroundStyle(.secondary)
                                    SecureField("settings.field.current_password", text: $currentPassword)
                                        .font(.system(size: 16, weight: .medium))
                                        .padding(14)
                                        .background(Color(uiColor: .tertiarySystemGroupedBackground))
                                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                        .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color.primary.opacity(0.1), lineWidth: 1))
                                }

                                VStack(alignment: .leading, spacing: 8) {
                                    Text("settings.field.new_password")
                                        .font(.system(size: 13, weight: .semibold))
                                        .foregroundStyle(.secondary)
                                    SecureField("settings.field.new_password", text: $newPassword)
                                        .font(.system(size: 16, weight: .medium))
                                        .padding(14)
                                        .background(Color(uiColor: .tertiarySystemGroupedBackground))
                                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                        .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color.primary.opacity(0.1), lineWidth: 1))
                                }
                            }
                            .padding(16)
                        }
                    }

                    if let errorMessage = passwordErrorMessage {
                        Text(errorMessage)
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(errorMessage.contains("✅") ? .green : .red)
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
                        ProgressView()
                    } else {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle((currentPassword.isEmpty || newPassword.count < 6) ? Color.secondary.opacity(0.3) : Color.blue)
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
            passwordErrorMessage = "✅ Password successfully changed"
            logger.info("Password changed: \(response.message, privacy: .public)")
        } catch {
            passwordErrorMessage = "修改密码失败：\(error.localizedDescription)"
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
            Color(uiColor: .systemGroupedBackground).ignoresSafeArea()
            ScrollView {
                VStack(spacing: 4) {
                    // Toggle row
                    VStack(spacing: 0) {
                        HStack {
                            Text(LocalizedStringKey("settings.two_factor.authenticator_app"))
                                .font(.system(size: 16, weight: .medium))
                                .foregroundStyle(.primary)
                            Spacer()
                            Toggle("", isOn: $is2FAEnabled)
                                .labelsHidden()
                                .tint(.green)
                        }
                        .padding(14)
                    }
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .padding(.horizontal, 16)
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
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 16)
                        .padding(.top, 4)
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
                        .foregroundStyle(.blue)
                }
            }
        }
        .sheet(isPresented: $showing2FASetupModal) {
            twoFactorSetupModal
        }
    }
    
    private var twoFactorSetupModal: some View {
        NavigationStack {
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
                                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                        } else {
                            Image(systemName: "qrcode")
                                .font(.system(size: 80, weight: .ultraLight))
                                .foregroundStyle(.secondary)
                                .frame(width: 180, height: 180)
                        }
                    }
                    .padding(.top, 24)

                    Text(LocalizedStringKey("settings.dialog.two_factor.hint"))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)

                    // Code input
                    TextField("000000", text: $twoFACode)
                        .keyboardType(.numberPad)
                        .multilineTextAlignment(.center)
                        .font(.system(size: 28, weight: .semibold, design: .monospaced))
                        .padding(12)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .padding(.horizontal, 48)

                    if let err = twoFAErrorMessage {
                        Text(err)
                            .font(.caption)
                            .foregroundStyle(.red)
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
                                    .font(.headline)
                            }
                        }
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(twoFACode.count == 6 ? Color.blue : Color.blue.opacity(0.35))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                    .disabled(twoFACode.count != 6 || is2FAVerifying)
                    .padding(.horizontal, 32)
                }
                .padding(.bottom, 32)
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
                            .foregroundStyle(.primary)
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
            twoFAErrorMessage = "Failed to load QR code"
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
            twoFAErrorMessage = "Invalid code. Please try again."
        }
    }

    private var sessionsSheet: some View {
        ZStack {
            Color(uiColor: .systemGroupedBackground).ignoresSafeArea()
            ScrollView {
                VStack(spacing: 12) {
                    HStack {
                        Text("settings.active_sessions")
                            .font(.system(size: 13))
                            .foregroundStyle(.secondary)
                            .textCase(.uppercase)
                        Spacer()
                        Button {
                            Task { await loadSessions() }
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundStyle(.secondary)
                        .disabled(isSessionsLoading)
                    }
                    .padding(.horizontal, 32)
                    .padding(.top, 4)
                    .padding(.bottom, -4)

                    VStack(spacing: 0) {
                        sessionListContent
                            .padding(12)
                    }
                    .background(Color(uiColor: .secondarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .padding(.horizontal, 16)

                    if let sessionErrorMessage {
                        VStack(spacing: 0) {
                            Text(sessionErrorMessage)
                                .font(.system(size: 13))
                                .foregroundStyle(.red)
                                .padding(12)
                        }
                        .frame(maxWidth: .infinity)
                        .background(Color(uiColor: .secondarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .padding(.horizontal, 16)
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
                        .foregroundStyle(.blue)
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
            HStack(spacing: 10) {
                ProgressView()
                Text("settings.session.loading")
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical, 12)
        } else if sessions.isEmpty {
            Text("settings.session.empty")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 12)
        } else {
            VStack(spacing: 12) {
                ForEach(sessions) { session in
                    HStack(spacing: 12) {
                        Image(systemName: session.isCurrent ? "iphone" : "desktopcomputer")
                            .foregroundStyle(session.isCurrent ? .blue : .secondary)
                            .frame(width: 24)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(session.deviceName)
                                .font(.subheadline.weight(.medium))
                            Text(session.metaLine)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()

                        if session.isCurrent {
                            Text("settings.session.current")
                                .font(.caption2.weight(.medium))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Color.blue.opacity(0.12))
                                .clipShape(Capsule())
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
                            .tint(.green)
                            .scaleEffect(0.9)
                        }
                    }

                    if session.id != sessions.last?.id {
                        Divider()
                            .opacity(0.35)
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
