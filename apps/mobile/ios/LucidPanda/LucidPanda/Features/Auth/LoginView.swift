import SwiftUI
import AlphaDesign
import UIKit

struct LoginView: View {
    @State private var viewModel = LoginViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var showPassword = false
    
    // UI Animation States
    @State private var appearAnimation = false
    @FocusState private var focusedField: AuthField?
    
    enum AuthField {
        case email
        case username
        case password
        case confirmPassword
    }

    var body: some View {
        ZStack {
            // 1. Clean Premium Background
            Color.Alpha.background
                .ignoresSafeArea()
                
            GeometryReader { proxy in
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 0) {
                        Spacer(minLength: 80)
                        
                        // 3. Central Login Form (Now Borderless & Immersive)
                        authCard
                            .padding(.horizontal, 16)
                            .opacity(appearAnimation ? 1 : 0)
                            .scaleEffect(appearAnimation ? 1 : 0.95)
                        
                        Spacer(minLength: 60)
                        
                        // 4. Branding Footer
                        footerView
                            .opacity(appearAnimation ? 1 : 0)
                            .offset(y: appearAnimation ? 0 : 20)
                    }
                    .frame(minHeight: proxy.size.height)
                }
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.8)) {
                appearAnimation = true
            }
            viewModel.onSuccess = {
                rootViewModel.updateState(to: .authenticated)
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("auth.action.complete") {
                    focusedField = nil
                }
            }
        }
    }

    // MARK: - Central Authentication Card
    private var authCard: some View {
        VStack(spacing: 24) {
            // Logo Branding
            VStack(spacing: 12) {
                Image(systemName: "chart.line.uptrend.xyaxis.circle.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(Color.Alpha.brand)
                
                Text(verbatim: "LucidPanda")
                    .font(.system(size: 26, weight: .heavy, design: .rounded))
                    .foregroundStyle(Color.Alpha.textPrimary)
            }
            .padding(.bottom, 12)
            
            // Header
            if viewModel.mode != .login {
                VStack(spacing: 8) {
                    Text(viewModel.mode == .register ? "auth.action.register_title" : "auth.action.reset_password_title")
                        .font(.system(size: 20, weight: .medium)) // 适度缩小字号
                        .foregroundStyle(Color.Alpha.textPrimary)
                    
                    Text(viewModel.mode == .register ? "auth.action.create_account_desc" : "auth.action.send_verification_code")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(Color.Alpha.textSecondary)
                }
                .padding(.bottom, 8)
            }
            
            // Input Fields
            VStack(spacing: 16) {
                customTextField(
                    icon: "envelope.fill",
                    placeholder: "电子邮箱",
                    text: $viewModel.email,
                    isSecure: false,
                    field: .email
                )
                
                if viewModel.mode != .forgotPassword {
                    customTextField(
                        icon: "lock.fill",
                        placeholder: "密码",
                        text: $viewModel.password,
                        isSecure: !showPassword,
                        field: .password
                    )
                }
                
                if viewModel.mode == .register {
                    customTextField(
                        icon: "person.fill",
                        placeholder: "用户名（3-50位，仅字母数字下划线）",
                        text: $viewModel.username,
                        isSecure: false,
                        field: .username
                    )

                    customTextField(
                        icon: "lock.shield.fill",
                        placeholder: "确认密码",
                        text: $viewModel.confirmPassword,
                        isSecure: true,
                        field: .confirmPassword
                    )
                }
            }
            
            // Alerts
            if let err = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                    Text(err)
                }
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color.Alpha.up)
                .frame(maxWidth: .infinity, alignment: .leading)
                .transition(.opacity)
            }
            if let suc = viewModel.successMessage {
                HStack {
                    Image(systemName: "checkmark.shield.fill")
                    Text(suc)
                }
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Color.Alpha.down)
                .frame(maxWidth: .infinity, alignment: .leading)
                .transition(.opacity)
            }
            
            // Action Button
            let actionText = viewModel.mode == .login ? "登录" :
                            (viewModel.mode == .register ? "注册" : "auth.action.reset_password_title")
                            
            Button {
                focusedField = nil
                Task {
                    switch viewModel.mode {
                    case .login: await viewModel.performLogin()
                    case .register: await viewModel.performRegister()
                    case .forgotPassword: await viewModel.performPasswordReset()
                    }
                }
            } label: {
                HStack {
                    if viewModel.isLoading {
                        ProgressView().tint(.white)
                            .frame(width: 20, height: 20)
                    } else {
                        Text(actionText)
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(.white)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(
                    Capsule()
                        .fill(viewModel.canSubmit ? Color.Alpha.brand : Color.Alpha.textSecondary.opacity(0.4))
                )
            }
            .buttonStyle(.plain)
            .allowsHitTesting(!(viewModel.isLoading || !viewModel.canSubmit))
            
            // Mode Switchers
            HStack {
                if viewModel.mode == .login {
                    Button("auth.action.forgot_password_question") { switchMode(to: .forgotPassword) }
                    Spacer()
                    Button("auth.action.register_title") { switchMode(to: .register) }
                } else {
                    Spacer()
                    Button("auth.action.back_to_login") { switchMode(to: .login) }
                    Spacer()
                }
            }
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(Color.Alpha.textSecondary)
            .padding(.top, 4)
            
            // WebAuthn Passkey Section
            if viewModel.mode == .login {
                Divider().background(Color.Alpha.separator)
                    .padding(.vertical, 8)
                
                Button {
                    Task { await viewModel.performPasskeyLogin() }
                } label: {
                    HStack(spacing: 8) {
                        if viewModel.isPasskeyLoading {
                            ProgressView().tint(Color.Alpha.textPrimary)
                                .frame(width: 20, height: 20)
                        } else {
                            Image(systemName: "faceid")
                                .font(.system(size: 18))
                                .frame(width: 20, height: 20)
                        }
                        Text(LocalizedStringKey("auth.action.passkey_login"))
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(Color.Alpha.textPrimary)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                    .background(Color.Alpha.surface)
                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 4, style: .continuous)
                            .stroke(Color.Alpha.separator, lineWidth: 1)
                    )
                }
                .buttonStyle(.plain)
                .disabled(viewModel.isLoading || viewModel.isPasskeyLoading)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 32)
    }
    
    // MARK: - Reusable Custom Text Field
    private func customTextField(icon: String, placeholder: String, text: Binding<String>, isSecure: Bool, field: AuthField) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundStyle(focusedField == field ? Color.Alpha.brand : Color.Alpha.textSecondary)
                .frame(width: 24)
            
            if isSecure {
                SecureField(placeholder, text: text)
                    .focused($focusedField, equals: field)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled(true)
                    .foregroundStyle(Color.Alpha.textPrimary)
            } else {
                TextField(placeholder, text: text)
                    .focused($focusedField, equals: field)
                    .textInputAutocapitalization(.never)
                    .keyboardType(field == .email ? .emailAddress : .default)
                    .autocorrectionDisabled(true)
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .submitLabel((field == .email && viewModel.mode == .forgotPassword) || field == .confirmPassword ? .go : .next)
                    .onSubmit {
                        if field == .email {
                            if viewModel.mode == .forgotPassword {
                                Task { await viewModel.performPasswordReset() }
                            } else {
                                focusedField = viewModel.mode == .register ? .username : .password
                            }
                        } else if field == .username {
                            focusedField = .password
                        } else if field == .password {
                            if viewModel.mode == .register {
                                focusedField = .confirmPassword
                            } else if viewModel.mode == .login {
                                Task { await viewModel.performLogin() }
                            }
                        } else if field == .confirmPassword, viewModel.mode == .register {
                            Task { await viewModel.performRegister() }
                        }
                    }
            }
            
            if field == .password {
                Button { showPassword.toggle() } label: {
                    Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill")
                        .foregroundStyle(Color.Alpha.textSecondary)
                        .frame(width: 24, height: 24)
                }
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 52)
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .stroke(focusedField == field ? Color.Alpha.brand.opacity(0.8) : Color.Alpha.separator, lineWidth: focusedField == field ? 1.5 : 1)
        )
    }
    
    // MARK: - Handlers
    private func switchMode(to newMode: AuthMode) {
        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
            viewModel.mode = newMode
            viewModel.errorMessage = nil
            viewModel.successMessage = nil
            if newMode != .register {
                viewModel.username = ""
                viewModel.confirmPassword = ""
            }
            focusedField = nil
        }
    }
    
    // MARK: - Footer
    private var footerView: some View {
        VStack(spacing: 4) {
            Text("dashboard.header.subtitle")
            Text("auth.footer.powered_by")
        }
        .font(.system(size: 10, weight: .medium, design: .monospaced))
        .foregroundStyle(.secondary.opacity(0.6))
        .padding(.bottom, 30)
    }
}
