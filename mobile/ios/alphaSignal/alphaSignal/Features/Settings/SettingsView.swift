import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct SettingsView: View {
    @Environment(AppRootViewModel.self) private var rootViewModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var showWebPrompt = false
    @State private var activeSheet: ActiveSheet?
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var sessions: [SessionRowDTO] = []
    @State private var isSessionsLoading = false
    @State private var isLoggingOut = false
    @State private var sessionErrorMessage: String?
    @State private var userProfile: UserProfileDTO?
    @State private var isProfileLoading = false
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
                LiquidBackground()
                ScrollView {
                    LazyVStack(spacing: 18) {
                        profileCard
                        quickActionsCard
                        notificationsCard
                        securityCard
                        sessionsCard

                        logoutCard
                    }
                    .padding(.top, 8)
                    .padding(.bottom, 32)
                }
                .refreshable {
                    await loadUserProfile()
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
            await loadUserProfile()
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

    private var profileCard: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 14) {
                    if isProfileLoading {
                        ProgressView()
                            .frame(width: 56, height: 56)
                    } else if let user = userProfile {
                        Circle()
                            .fill(Color.accentColor.opacity(0.15))
                            .frame(width: 56, height: 56)
                            .overlay(
                                Text(String(user.email.prefix(1)).uppercased())
                                    .font(.title2.weight(.bold))
                                    .foregroundStyle(Color.accentColor)
                            )

                        VStack(alignment: .leading, spacing: 4) {
                            Text(user.displayName ?? user.email)
                                .font(.headline)
                                .foregroundStyle(.primary)
                            Text(user.email)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        Circle()
                            .fill(Color.accentColor.opacity(0.15))
                            .frame(width: 56, height: 56)
                            .overlay(
                                Text("A")
                                    .font(.title2.weight(.bold))
                                    .foregroundStyle(Color.accentColor)
                            )

                        VStack(alignment: .leading, spacing: 4) {
                            Text("settings.user.display_name")
                                .font(.headline)
                                .foregroundStyle(.primary)
                            Text("pincar@alphasignal.com")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Spacer()
                }

                if isProfileLoading {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color(uiColor: .secondarySystemFill))
                        .frame(height: 8)
                        .opacity(0.6)
                        .redacted(reason: .placeholder)
                }
            }
            .padding(16)
        }
        .padding(.horizontal)
    }

    private var quickActionsCard: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                Text("Account Actions")
                    .font(.headline)
                    .foregroundStyle(.primary)

                LazyVGrid(
                    columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ],
                    spacing: 12
                ) {
                    actionTile(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue) {
                        activeSheet = .password
                    }
                    actionTile(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange) {
                        activeSheet = .twoFactor
                    }
                    actionTile(icon: "person.text.rectangle.fill", titleKey: "settings.action.identity", color: .green) {
                        showWebPrompt = true
                    }
                    actionTile(icon: "safari", titleKey: "settings.action.manage_on_web", color: .accentColor) {
                        showWebPrompt = true
                    }
                }
            }
            .padding(16)
        }
        .padding(.horizontal)
    }

    private var notificationsCard: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                Text("settings.section.notifications")
                    .font(.headline)
                    .foregroundStyle(.primary)

                VStack(spacing: 12) {
                    settingsToggleRow(icon: "bell.badge.fill", titleKey: "settings.item.push_alert", color: .orange, isOn: $pushAlertsEnabled)
                    settingsToggleRow(icon: "waveform.path.ecg", titleKey: "settings.item.signal_alert", color: .blue, isOn: $signalAlertsEnabled)
                    settingsToggleRow(icon: "chart.line.uptrend.xyaxis", titleKey: "settings.item.price_alert", color: .green, isOn: $priceAlertsEnabled)
                }
            }
            .padding(16)
        }
        .padding(.horizontal)
    }

    private var securityCard: some View {
        LiquidGlassCard {
            VStack(alignment: .leading, spacing: 14) {
                Text("settings.section.security")
                    .font(.headline)
                    .foregroundStyle(.primary)

                settingsToggleRow(icon: "faceid", titleKey: "settings.item.biometric_unlock", color: .purple, isOn: $biometricUnlockEnabled)
            }
            .padding(16)
        }
        .padding(.horizontal)
    }

    private var sessionsCard: some View {
        LiquidGlassCard {
            Button {
                activeSheet = .sessions
            } label: {
                HStack(spacing: 12) {
                    ZStack {
                        Circle()
                            .fill(Color.blue.opacity(0.12))
                            .frame(width: 40, height: 40)
                        Image(systemName: "lock.shield")
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundStyle(.blue)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Session Security")
                            .font(.headline)
                            .foregroundStyle(.primary)
                        Text("Active Sessions")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(hasLoadedSessions ? "\(sessions.count)" : "—")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color(uiColor: .secondarySystemFill))
                        .clipShape(Capsule())
                    Image(systemName: "chevron.right")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.tertiary)
                }
            }
            .buttonStyle(.plain)
            .padding(16)
        }
        .padding(.horizontal)
    }

    private var logoutCard: some View {
        LiquidGlassCard {
            Button("settings.action.logout", role: .destructive) {
                Task { await logoutCurrentSession() }
            }
            .disabled(isLoggingOut)
            .frame(maxWidth: .infinity)
            .padding(16)
            .font(.headline)
        }
        .padding(.horizontal)
    }

    private func actionTile(icon: String, titleKey: LocalizedStringKey, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 10) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.15))
                        .frame(width: 36, height: 36)
                    Image(systemName: icon)
                        .foregroundStyle(color)
                        .font(.system(size: 16, weight: .semibold))
                }

                Text(titleKey)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground).opacity(0.8))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Color(uiColor: .separator).opacity(0.25), lineWidth: 0.6)
            )
        }
        .buttonStyle(.plain)
    }

    private func settingsToggleRow(icon: String, titleKey: LocalizedStringKey, color: Color, isOn: Binding<Bool>) -> some View {
        HStack {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Text(titleKey)
                    .foregroundStyle(.primary)
            }
            Spacer()
            Toggle("", isOn: isOn)
                .labelsHidden()
                .tint(.blue)
        }
        .padding(.vertical, 4)
    }

    @MainActor
    private func loadUserProfile() async {
        isProfileLoading = true
        defer { isProfileLoading = false }
        
        do {
            let response: UserProfileDTO = try await APIClient.shared.fetch(path: "/api/v1/user/profile")
            self.userProfile = response
        } catch {
            print("❌ Failed to load user profile: \(error)")
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
                LiquidBackground()
                ScrollView {
                    VStack(spacing: 16) {
                        LiquidGlassCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack(spacing: 12) {
                                    ZStack {
                                        Circle()
                                            .fill(Color.blue.opacity(0.15))
                                            .frame(width: 44, height: 44)
                                        Image(systemName: "lock.shield.fill")
                                            .font(.system(size: 20, weight: .bold))
                                            .foregroundStyle(.blue)
                                    }
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("settings.dialog.change_password.title")
                                            .font(.headline)
                                        Text("settings.section.security")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                }
                            }
                            .padding(16)
                        }
                        .padding(.horizontal)

                        LiquidGlassCard {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("settings.field.current_password")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                SecureField("settings.field.current_password", text: $currentPassword)
                                    .textFieldStyle(GlassTextFieldStyle())

                                Text("settings.field.new_password")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                SecureField("settings.field.new_password", text: $newPassword)
                                    .textFieldStyle(GlassTextFieldStyle())
                            }
                            .padding(16)
                        }
                        .padding(.horizontal)

                        if let errorMessage = passwordErrorMessage {
                            LiquidGlassCard {
                                Text(errorMessage)
                                    .font(.caption)
                                    .foregroundStyle(.red)
                                    .padding(12)
                            }
                            .padding(.horizontal)
                        }

                        VStack(spacing: 10) {
                            Button {
                                Task { await changePassword() }
                            } label: {
                                HStack(spacing: 8) {
                                    if isPasswordChanging {
                                        ProgressView()
                                            .controlSize(.small)
                                    }
                                    Text("settings.action.save_changes")
                                }
                            }
                            .buttonStyle(FintechPrimaryButtonStyle())
                            .disabled(currentPassword.isEmpty || newPassword.count < 6 || isPasswordChanging)

                            Button("common.close") {
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
            .navigationTitle("settings.dialog.change_password.title")
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
                            Button("settings.action.manage_on_web") {
                                showWebPrompt = true
                            }
                            .buttonStyle(FintechPrimaryButtonStyle())

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

private struct UserProfileDTO: Decodable {
    let id: Int
    let email: String
    let displayName: String?
    let createdAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, email
        case displayName = "display_name"
        case createdAt = "created_at"
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
