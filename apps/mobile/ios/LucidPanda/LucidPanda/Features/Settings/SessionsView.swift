import SwiftUI
import AlphaCore
import AlphaData
import OSLog

@Observable
class SessionsViewModel {
    private let logger = AppLog.root
    var sessions: [SessionRowDTO] = []
    var isSessionsLoading = false
    var sessionErrorMessage: String?
    var hasLoadedSessions = false

    @MainActor
    func loadSessions() async {
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
    func revokeSession(_ sessionID: Int) async {
        sessionErrorMessage = nil
        do {
            let endpoint = SessionRevokeEndpoint(sessionID: sessionID)
            let _: MessageResponseDTO = try await APIClient.shared.request(endpoint)
            sessions.removeAll { $0.id == sessionID }
        } catch {
            sessionErrorMessage = String(format: NSLocalizedString("settings.session.error.revoke_failed %@", comment: ""), error.localizedDescription)
        }
    }
}

struct SessionsView: View {
    @State private var viewModel = SessionsViewModel()
    @Environment(\.dismiss) var dismiss

    var body: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        HStack {
                            SettingsSectionHeader(title: "settings.active_sessions")
                            Spacer()
                            Button {
                                Task { await viewModel.loadSessions() }
                            } label: {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(Color.Alpha.brand)
                            }
                            .padding(.horizontal, 36)
                            .padding(.bottom, 6)
                            .disabled(viewModel.isSessionsLoading)
                        }

                        PremiumCard {
                            sessionListContent()
                                .padding(16)
                        }
                    }

                    if let errorMessage = viewModel.sessionErrorMessage {
                        VStack(spacing: 0) {
                            SettingsSectionHeader(title: "common.error")
                            PremiumCard {
                                Text(errorMessage)
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
                await viewModel.loadSessions()
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
            if !viewModel.hasLoadedSessions {
                await viewModel.loadSessions()
            }
        }
    }

    @ViewBuilder
    private func sessionListContent() -> some View {
        if viewModel.isSessionsLoading {
            HStack(spacing: 12) {
                ProgressView().scaleEffect(0.8)
                Text("settings.session.loading")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.taupe)
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical, 12)
        } else if viewModel.sessions.isEmpty {
            Text("settings.session.empty")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(Color.Alpha.taupe)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 12)
        } else {
            VStack(spacing: 16) {
                ForEach(viewModel.sessions) { session in
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
                                        Task { await viewModel.revokeSession(session.id) }
                                    }
                                }
                            ))
                            .labelsHidden()
                            .tint(Color.Alpha.brand)
                            .scaleEffect(0.8)
                        }
                    }

                    if session.id != viewModel.sessions.last?.id {
                        Divider()
                            .background(Color.Alpha.separator)
                    }
                }
            }
        }
    }
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

struct SessionRowDTO: Decodable, Identifiable {
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

private struct MessageResponseDTO: Decodable {
    let message: String
}
