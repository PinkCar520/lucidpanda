import SwiftUI
import AlphaCore
import AlphaData
import OSLog

@Observable
class PasswordChangeViewModel {
    private let logger = AppLog.root
    var currentPassword = ""
    var newPassword = ""
    var isPasswordChanging = false
    var passwordErrorMessage: String?

    @MainActor
    func changePassword() async {
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
            
            passwordErrorMessage = "✅ " + NSLocalizedString("settings.password.success", comment: "")
            logger.info("Password changed: \(response.message, privacy: .public)")
        } catch {
            passwordErrorMessage = String(format: NSLocalizedString("settings.password.error_format %@", comment: ""), error.localizedDescription)
        }
        
        isPasswordChanging = false
    }
}

struct PasswordChangeView: View {
    @State private var viewModel = PasswordChangeViewModel()
    @Environment(\.dismiss) var dismiss

    var body: some View {
        @Bindable var bindable = viewModel
        ZStack {
            Color.Alpha.background
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.dialog.change_password.title")
                        PremiumCard {
                            VStack(alignment: .leading, spacing: 16) {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("settings.field.current_password")
                                        .font(.system(size: 11, weight: .black))
                                        .foregroundStyle(Color.Alpha.taupe)
                                        .textCase(.uppercase)
                                    SecureField("settings.field.current_password", text: $bindable.currentPassword)
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
                                    SecureField("settings.field.new_password", text: $bindable.newPassword)
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

                    if let errorMessage = viewModel.passwordErrorMessage {
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
                    Task { await viewModel.changePassword() }
                } label: {
                    if viewModel.isPasswordChanging {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle((viewModel.currentPassword.isEmpty || viewModel.newPassword.count < 6) ? Color.Alpha.taupe.opacity(0.3) : Color.Alpha.brand)
                    }
                }
                .allowsHitTesting(!(viewModel.currentPassword.isEmpty || viewModel.newPassword.count < 6 || viewModel.isPasswordChanging))
            }
        }
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

private struct MessageResponseDTO: Decodable {
    let message: String
}
