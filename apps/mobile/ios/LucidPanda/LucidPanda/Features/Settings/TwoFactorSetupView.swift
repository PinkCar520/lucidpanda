import SwiftUI
import AlphaCore
import AlphaData
import OSLog

@Observable
class TwoFactorViewModel {
    private let logger = AppLog.root
    var is2FAEnabled: Bool = false
    var showing2FASetupModal: Bool = false
    var twoFAQRImageData: Data? = nil
    var twoFASecret: String = ""
    var twoFACode: String = ""
    var is2FALoading: Bool = false
    var twoFAErrorMessage: String? = nil
    var is2FAVerifying: Bool = false

    init(isEnabled: Bool) {
        self.is2FAEnabled = isEnabled
    }

    @MainActor
    func fetchTwoFAQRCode() async {
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
            let base64Part = resp.qrCodeUrl
                .replacingOccurrences(of: "data:image/png;base64,", with: "")
            if let data = Data(base64Encoded: base64Part, options: .ignoreUnknownCharacters) {
                twoFAQRImageData = data
            }
        } catch {
            twoFAErrorMessage = NSLocalizedString("settings.two_factor.error.load_qr_failed", comment: "")
        }
    }

    @MainActor
    func verify2FA() async -> Bool {
        guard !twoFASecret.isEmpty else { return false }
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
            return true
        } catch {
            twoFAErrorMessage = NSLocalizedString("settings.two_factor.error.invalid_code", comment: "")
            return false
        }
    }
}

struct TwoFactorSetupView: View {
    @State private var viewModel: TwoFactorViewModel
    @Environment(\.dismiss) var dismiss

    init(is2FAEnabled: Bool) {
        _viewModel = State(initialValue: TwoFactorViewModel(isEnabled: is2FAEnabled))
    }

    var body: some View {
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 4) {
                    PremiumCard {
                        HStack {
                            Text(LocalizedStringKey("settings.two_factor.authenticator_app"))
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.Alpha.textPrimary)
                            Spacer()
                            Toggle("", isOn: $viewModel.is2FAEnabled)
                                .labelsHidden()
                                .tint(Color.Alpha.brand)
                        }
                        .padding(16)
                    }
                    .onChange(of: viewModel.is2FAEnabled) { oldValue, newValue in
                        if newValue && !oldValue {
                            viewModel.twoFAQRImageData = nil
                            viewModel.twoFASecret = ""
                            viewModel.twoFACode = ""
                            viewModel.twoFAErrorMessage = nil
                            viewModel.showing2FASetupModal = true
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
        .sheet(isPresented: $viewModel.showing2FASetupModal) {
            twoFactorSetupModal()
        }
    }

    @ViewBuilder
    private func twoFactorSetupModal() -> some View {
        @Bindable var bindable = viewModel
        NavigationStack {
            ZStack {
                Color.Alpha.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 24) {
                        Group {
                            if viewModel.is2FALoading {
                                ProgressView()
                                    .frame(width: 180, height: 180)
                            } else if let data = viewModel.twoFAQRImageData,
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

                        TextField("000000", text: $bindable.twoFACode)
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

                        if let err = viewModel.twoFAErrorMessage {
                            Text(err)
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(Color.Alpha.down)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 32)
                        }

                        Button(action: {
                            Task { _ = await viewModel.verify2FA() }
                        }) {
                            Group {
                                if viewModel.is2FAVerifying {
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
                            .background(viewModel.twoFACode.count == 6 ? Color.Alpha.brand : Color.Alpha.brand.opacity(0.3))
                            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                            .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
                        }
                        .disabled(viewModel.twoFACode.count != 6 || viewModel.is2FAVerifying)
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
                        viewModel.is2FAEnabled = false
                        viewModel.showing2FASetupModal = false
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                }
            }
            .task {
                await viewModel.fetchTwoFAQRCode()
            }
        }
    }
}

private struct MessageResponseDTO: Decodable {
    let message: String
}
