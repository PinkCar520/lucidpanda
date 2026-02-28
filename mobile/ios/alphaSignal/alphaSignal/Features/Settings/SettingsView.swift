import SwiftUI
import PhotosUI
import AlphaDesign
import AlphaData
import AlphaCore

struct SettingsView: View {
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
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("common.close") { dismiss() }
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
            case .password:
                passwordSheet
            case .twoFactor:
                twoFactorSheet
            case .sessions:
                sessionsSheet
            }
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
            .font(.system(size: 13, weight: .bold))
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 36)
            .padding(.bottom, 6)
    }

    // MARK: - Sections

    private var profileHeader: some View {
        VStack(spacing: 16) {
            let displayEmail = rootViewModel.userProfile?.email ?? "root@alphasignal.com"
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
                .shadow(color: Color.blue.opacity(0.3), radius: 16, y: 8)
                
                PhotosPicker(selection: $avatarItem, matching: .images) {
                    ZStack {
                        Circle()
                            .fill(Color(uiColor: .systemBackground))
                            .frame(width: 28, height: 28)
                            .shadow(color: .black.opacity(0.1), radius: 4, y: 2)
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
                                print("✅ Avatar successfully uploaded to Backend: \(response.avatarUrl)")
                                await rootViewModel.fetchUserProfile()
                            } catch {
                                print("❌ Avatar upload failed: \(error)")
                            }
                        }
                    }
                }
            }

            VStack(spacing: 6) {
                Text(displayName)
                    .font(.system(size: 24, weight: .bold))
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
            sectionHeader(title: "Settings")
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
                        
                        Text("账户与安全")
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

    private var accountSettingsSubView: some View {
        ZStack {
            Color(uiColor: .systemGroupedBackground).ignoresSafeArea()
            ScrollView(showsIndicators: false) {
                VStack(spacing: 28) {
                    quickActionsCard
                    sessionsCard
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle("账户与安全")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var quickActionsCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "Account Actions")
            premiumCard {
                VStack(spacing: 0) {
                    HStack(spacing: 16) {
                        actionTile(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue) {
                            activeSheet = .password
                        }
                        actionTile(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange) {
                            activeSheet = .twoFactor
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 16)
                    
                    HStack(spacing: 16) {
                        actionTile(icon: "person.text.rectangle.fill", titleKey: "settings.action.identity", color: .green) {
                            showWebPrompt = true
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 16)
                }
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

    private var sessionsCard: some View {
        VStack(spacing: 0) {
            sectionHeader(title: "Session Security")
            premiumCard {
                Button {
                    activeSheet = .sessions
                } label: {
                    HStack(spacing: 16) {
                        ZStack {
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .fill(Color.blue)
                                .frame(width: 32, height: 32)
                            Image(systemName: "desktopcomputer.and.iphone")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundStyle(.white)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Active Sessions")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundStyle(.primary)
                        }
                        Spacer()
                        Text(hasLoadedSessions ? "\(sessions.count)" : "—")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(Color(uiColor: .tertiarySystemFill))
                            .clipShape(Capsule())
                        
                        Image(systemName: "chevron.right")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(Color(uiColor: .tertiaryLabel))
                    }
                    .padding(.vertical, 12)
                    .padding(.horizontal, 16)
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var logoutCard: some View {
        Button(action: { Task { await logoutCurrentSession() } }) {
            Text("settings.action.logout")
                .font(.system(size: 16, weight: .bold))
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

        if let refreshToken = AuthTokenStore.refreshToken() {
            do {
                let _: MessageResponseDTO = try await APIClient.shared.send(
                    path: "/api/v1/auth/logout",
                    method: "POST",
                    body: LogoutPayload(refreshToken: refreshToken)
                )
            } catch {
                // Network failure should not block local sign-out.
            }
        }

        AuthTokenStore.clear()
        rootViewModel.updateState(to: .unauthenticated)
    }

    private var passwordSheet: some View {
        NavigationStack {
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
                                .foregroundStyle(Color.red)
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
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        activeSheet = nil
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(.primary)
                    }
                }
                
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
        .presentationDetents([.fraction(0.55), .large])
        .presentationDragIndicator(.visible)
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
            activeSheet = nil
            
            // 显示成功提示
            print("✅ Password changed: \(response.message)")
        } catch {
            passwordErrorMessage = "修改密码失败：\(error.localizedDescription)"
        }
        
        isPasswordChanging = false
    }

    private var twoFactorSheet: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                ScrollView {
                    VStack(spacing: 16) {
                        LiquidGlassCard {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(spacing: 12) {
                                    ZStack {
                                        Circle()
                                            .fill(Color.orange.opacity(0.15))
                                            .frame(width: 44, height: 44)
                                        Image(systemName: "qrcode")
                                            .font(.system(size: 20, weight: .bold))
                                            .foregroundStyle(.orange)
                                    }
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("settings.dialog.two_factor.title")
                                            .font(.headline)
                                        Text("settings.section.security")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                }

                                Text("settings.dialog.two_factor.hint")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(16)
                        }
                        .padding(.horizontal)

                        VStack(spacing: 10) {
                            Button("settings.action.done") {
                                activeSheet = nil
                            }
                            .buttonStyle(FintechSecondaryButtonStyle())
                        }
                        .padding(.horizontal)
                    }
                    .padding(.top, 12)
                    .padding(.bottom, 32)
                }
            }
            .navigationTitle("settings.dialog.two_factor.title")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("common.close") {
                        activeSheet = nil
                    }
                }
            }
        }
    }

    private var sessionsSheet: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                ScrollView {
                    VStack(spacing: 16) {
                        LiquidGlassCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Session Security")
                                        .font(.headline)
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    Button {
                                        Task { await loadSessions() }
                                    } label: {
                                        Image(systemName: "arrow.clockwise")
                                            .font(.system(size: 14, weight: .bold))
                                    }
                                    .foregroundStyle(.secondary)
                                    .disabled(isSessionsLoading)
                                }

                                Text("Active Sessions")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(16)
                        }
                        .padding(.horizontal)

                        LiquidGlassCard {
                            sessionListContent
                                .padding(16)
                        }
                        .padding(.horizontal)

                        if let sessionErrorMessage {
                            LiquidGlassCard {
                                Text(sessionErrorMessage)
                                    .font(.caption)
                                    .foregroundStyle(.red)
                                    .padding(12)
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding(.top, 12)
                    .padding(.bottom, 32)
                }
                .refreshable {
                    await loadSessions()
                }
            }
            .navigationTitle("Active Sessions")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("common.close") {
                        activeSheet = nil
                    }
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
                Text("Loading sessions...")
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical, 12)
        } else if sessions.isEmpty {
            Text("No active sessions")
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
                                .font(.subheadline.weight(.semibold))
                            Text(session.metaLine)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()

                        if session.isCurrent {
                            Text("Current")
                                .font(.caption2.weight(.bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Color.blue.opacity(0.12))
                                .clipShape(Capsule())
                        } else {
                            Button("Revoke", role: .destructive) {
                                Task { await revokeSession(session.id) }
                            }
                            .font(.caption.weight(.semibold))
                            .buttonStyle(.bordered)
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
        let ip = ipAddress ?? "Unknown IP"
        let active = (lastActiveAt ?? createdAt).formatted(date: .abbreviated, time: .shortened)
        return "\(ip) · \(active)"
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
