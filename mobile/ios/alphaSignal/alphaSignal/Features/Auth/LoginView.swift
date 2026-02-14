import SwiftUI
import AlphaDesign

struct LoginView: View {
    @State private var viewModel = LoginViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var showPassword = false
    @State private var activePrompt: AuthPrompt?
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    Image(systemName: "chart.line.uptrend.xyaxis.circle.fill")
                        .font(.system(size: 42))
                        .foregroundStyle(.tint)

                    Text("AlphaSignal")
                        .font(.largeTitle.bold())
                        .foregroundStyle(.primary)

                    Text("auth.login.subtitle")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 48)
                
                LiquidGlassCard {
                    VStack(spacing: 16) {
                        Text("auth.login.title")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        VStack(spacing: 16) {
                            HStack {
                                Image(systemName: "envelope.fill")
                                    .foregroundStyle(.secondary)
                                    .frame(width: 24)
                                TextField("auth.field.email", text: $viewModel.email)
                                    .textInputAutocapitalization(.never)
                                    .keyboardType(.emailAddress)
                                    .foregroundStyle(.primary)
                            }
                            .padding()
                            .background(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .fill(Color(uiColor: .secondarySystemBackground))
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color(uiColor: .separator).opacity(0.25), lineWidth: 0.5)
                            )
                            
                            HStack {
                                Image(systemName: "lock.fill")
                                    .foregroundStyle(.secondary)
                                    .frame(width: 24)
                                if showPassword {
                                    TextField("auth.field.password", text: $viewModel.password)
                                        .textInputAutocapitalization(.never)
                                        .foregroundStyle(.primary)
                                } else {
                                    SecureField("auth.field.password", text: $viewModel.password)
                                        .foregroundStyle(.primary)
                                }
                                Button {
                                    showPassword.toggle()
                                } label: {
                                    Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill")
                                        .foregroundStyle(.secondary)
                                }
                                .buttonStyle(.plain)
                            }
                            .padding()
                            .background(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .fill(Color(uiColor: .secondarySystemBackground))
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color(uiColor: .separator).opacity(0.25), lineWidth: 0.5)
                            )
                        }
                        
                        if let error = viewModel.errorMessage {
                            Text(error)
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(.red)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        
                        Button {
                            Task { await viewModel.performLogin() }
                        } label: {
                            HStack {
                                if viewModel.isLoading {
                                    ProgressView().tint(.white)
                                } else {
                                    Text("auth.action.login")
                                        .fontWeight(.semibold)
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(viewModel.isLoading || viewModel.isPasskeyLoading || !viewModel.canSubmit)
                        
                        Button {
                            Task { await viewModel.performPasskeyLogin() }
                        } label: {
                            HStack(spacing: 8) {
                                if viewModel.isPasskeyLoading {
                                    ProgressView()
                                        .tint(.blue)
                                } else {
                                    Image(systemName: "person.badge.key.fill")
                                        .font(.system(size: 14, weight: .semibold))
                                }
                                Text("auth.action.passkey_login")
                                    .font(.system(size: 15, weight: .semibold))
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 46)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .disabled(viewModel.isLoading || viewModel.isPasskeyLoading)
                        
                        Text("auth.passkey.hint")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        
                        HStack {
                            Button("auth.action.forgot_password") {
                                activePrompt = .forgotPassword
                            }
                            .font(.footnote.weight(.semibold))
                            
                            Spacer()
                            
                            Button("auth.action.create_account") {
                                activePrompt = .createAccount
                            }
                            .font(.footnote.weight(.semibold))
                        }
                        .tint(.accentColor)
                    }
                }
                .padding(.horizontal, 20)
                
                Spacer()
                
                VStack(spacing: 4) {
                    Text("auth.status.secure_channel")
                    Text("auth.status.module_ready")
                }
                .font(.footnote)
                .foregroundStyle(.secondary)
                .padding(.bottom, 16)
            }
        }
        .onAppear {
            viewModel.onSuccess = {
                rootViewModel.updateState(to: .authenticated)
            }
        }
        .alert(alertTitleKey, isPresented: Binding(
            get: { activePrompt != nil },
            set: { if !$0 { activePrompt = nil } }
        )) {
            Button("common.close", role: .cancel) {}
        } message: {
            Text(alertMessageKey)
        }
    }
    
    private var alertTitleKey: String {
        switch activePrompt {
        case .forgotPassword: return String(localized: "auth.alert.forgot_password.title")
        case .createAccount: return String(localized: "auth.alert.create_account.title")
        case .none: return ""
        }
    }
    
    private var alertMessageKey: LocalizedStringKey {
        switch activePrompt {
        case .forgotPassword: return "auth.alert.forgot_password.message"
        case .createAccount: return "auth.alert.create_account.message"
        case .none: return ""
        }
    }
    
    private enum AuthPrompt {
        case forgotPassword
        case createAccount
    }
}
