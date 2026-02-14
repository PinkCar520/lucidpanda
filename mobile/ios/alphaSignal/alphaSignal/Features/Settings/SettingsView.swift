import SwiftUI
import AlphaData
import AlphaCore

struct SettingsView: View {
    @Environment(AppRootViewModel.self) private var rootViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var showWebPrompt = false
    @State private var activeSheet: ActiveSheet?
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var sessions: [SessionRowDTO] = []
    @State private var isSessionsLoading = false
    @State private var isLoggingOut = false
    @State private var sessionErrorMessage: String?

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
            Form {
                Section {
                    HStack(spacing: 12) {
                        Circle()
                            .fill(Color.accentColor.opacity(0.2))
                            .frame(width: 42, height: 42)
                            .overlay(
                                Text("A")
                                    .font(.headline)
                                    .foregroundStyle(Color.accentColor)
                            )

                        VStack(alignment: .leading, spacing: 2) {
                            Text("settings.user.display_name")
                                .font(.subheadline.weight(.semibold))
                            Text("pincar@alphasignal.com")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("settings.section.notifications") {
                    Toggle(isOn: $pushAlertsEnabled) {
                        Label("settings.item.push_alert", systemImage: "bell.badge.fill")
                    }
                    Toggle(isOn: $signalAlertsEnabled) {
                        Label("settings.item.signal_alert", systemImage: "waveform.path.ecg")
                    }
                    Toggle(isOn: $priceAlertsEnabled) {
                        Label("settings.item.price_alert", systemImage: "chart.line.uptrend.xyaxis")
                    }
                }

                Section("settings.section.security") {
                    Toggle(isOn: $biometricUnlockEnabled) {
                        Label("settings.item.biometric_unlock", systemImage: "faceid")
                    }

                    Button {
                        activeSheet = .password
                    } label: {
                        settingsRow(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue)
                    }
                    .buttonStyle(.plain)

                    Button {
                        showWebPrompt = true
                    } label: {
                        settingsRow(icon: "person.text.rectangle.fill", titleKey: "settings.action.identity", color: .green)
                    }
                    .buttonStyle(.plain)

                    Button {
                        activeSheet = .twoFactor
                    } label: {
                        settingsRow(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange)
                    }
                    .buttonStyle(.plain)
                }

                Section("settings.section.advanced") {
                    Button {
                        showWebPrompt = true
                    } label: {
                        settingsRow(icon: "safari", titleKey: "settings.action.manage_on_web", color: .accentColor)
                    }
                    .buttonStyle(.plain)
                }

                Section("Session Security") {
                    if isSessionsLoading {
                        HStack(spacing: 10) {
                            ProgressView()
                            Text("Loading sessions...")
                                .foregroundStyle(.secondary)
                        }
                    } else if sessions.isEmpty {
                        Text("No active sessions")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(sessions) { session in
                            HStack(spacing: 10) {
                                Image(systemName: session.isCurrent ? "iphone" : "desktopcomputer")
                                    .foregroundStyle(session.isCurrent ? .blue : .secondary)
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
                                }
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                if !session.isCurrent {
                                    Button(role: .destructive) {
                                        Task { await revokeSession(session.id) }
                                    } label: {
                                        Text("Revoke")
                                    }
                                }
                            }
                        }
                    }

                    Button {
                        Task { await loadSessions() }
                    } label: {
                        Text("Refresh Session List")
                    }
                }

                if let sessionErrorMessage {
                    Section {
                        Text(sessionErrorMessage)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }

                Section {
                    Button("settings.action.logout", role: .destructive) {
                        Task { await logoutCurrentSession() }
                    }
                    .disabled(isLoggingOut)
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
            await loadSessions()
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .password:
                passwordSheet
            case .twoFactor:
                twoFactorSheet
            }
        }
        .alert(String(localized: "settings.web.alert.title"), isPresented: $showWebPrompt) {
            Button("common.close", role: .cancel) {}
        } message: {
            Text("settings.web.alert.message")
        }
    }

    @MainActor
    private func loadSessions() async {
        guard let refreshToken = AuthTokenStore.refreshToken() else {
            sessions = []
            return
        }

        isSessionsLoading = true
        sessionErrorMessage = nil
        defer { isSessionsLoading = false }

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

    private func settingsRow(icon: String, titleKey: LocalizedStringKey, color: Color) -> some View {
        HStack {
            Label {
                Text(titleKey)
                    .foregroundStyle(.primary)
            } icon: {
                Image(systemName: icon)
                    .foregroundStyle(color)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(.tertiary)
        }
    }

    private var passwordSheet: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("settings.field.current_password", text: $currentPassword)
                    SecureField("settings.field.new_password", text: $newPassword)
                }
                Section {
                    Button("settings.action.save_changes") {
                        currentPassword = ""
                        newPassword = ""
                        activeSheet = nil
                    }
                    .disabled(currentPassword.isEmpty || newPassword.isEmpty)
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

    private var twoFactorSheet: some View {
        NavigationStack {
            Form {
                Section {
                    HStack(alignment: .center, spacing: 12) {
                        Image(systemName: "qrcode")
                            .font(.system(size: 46))
                            .foregroundStyle(.secondary)
                        Text("settings.dialog.two_factor.hint")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
                Section {
                    Button("settings.action.done") {
                        activeSheet = nil
                    }
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
}

private enum ActiveSheet: Int, Identifiable {
    case password
    case twoFactor

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
