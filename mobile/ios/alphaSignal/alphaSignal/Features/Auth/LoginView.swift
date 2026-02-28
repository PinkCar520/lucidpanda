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
        case password
        case confirmPassword
    }

    var body: some View {
        ZStack {
            // 1. Clean Premium Background
            Color(uiColor: .systemBackground)
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
                withAnimation(.spring()) {
                    rootViewModel.updateState(to: .authenticated)
                }
            }
        }
        .onTapGesture {
            focusedField = nil
        }
    }

    // MARK: - Central Authentication Card
    private var authCard: some View {
        VStack(spacing: 24) {
            // Logo Branding
            VStack(spacing: 12) {
                Image(systemName: "chart.line.uptrend.xyaxis.circle.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(Color.blue)
                
                Text("AlphaSignal")
                    .font(.system(size: 26, weight: .heavy, design: .rounded))
                    .foregroundStyle(.primary)
            }
            .padding(.bottom, 12)
            
            // Header
            if viewModel.mode != .login {
                VStack(spacing: 8) {
                    Text(viewModel.mode == .register ? "注册账号" : "重置密码")
                        .font(.system(size: 20, weight: .bold)) // 适度缩小字号
                        .foregroundStyle(.primary)
                    
                    Text(viewModel.mode == .register ? "创建您的新账号" : "向您的邮箱发送验证码")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
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
                .foregroundStyle(.red)
                .frame(maxWidth: .infinity, alignment: .leading)
                .transition(.opacity)
            }
            if let suc = viewModel.successMessage {
                HStack {
                    Image(systemName: "checkmark.shield.fill")
                    Text(suc)
                }
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.green)
                .frame(maxWidth: .infinity, alignment: .leading)
                .transition(.opacity)
            }
            
            // Action Button
            let actionText = viewModel.mode == .login ? "登录" :
                            (viewModel.mode == .register ? "注册" : "重置密码")
                            
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
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(.white)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(
                    Capsule()
                        .fill(viewModel.canSubmit ? Color.blue : Color.secondary.opacity(0.4))
                        .shadow(color: viewModel.canSubmit ? Color.blue.opacity(0.3) : .clear, radius: 8, x: 0, y: 4)
                )
            }
            .buttonStyle(.plain)
            .allowsHitTesting(!(viewModel.isLoading || !viewModel.canSubmit))
            
            // Mode Switchers
            HStack {
                if viewModel.mode == .login {
                    Button("忘记密码？") { switchMode(to: .forgotPassword) }
                    Spacer()
                    Button("注册账号") { switchMode(to: .register) }
                } else {
                    Spacer()
                    Button("返回登录") { switchMode(to: .login) }
                    Spacer()
                }
            }
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(.secondary)
            .padding(.top, 4)
            
            // WebAuthn Passkey Section
            if viewModel.mode == .login {
                Divider().background(Color.white.opacity(0.1))
                    .padding(.vertical, 8)
                
                Button {
                    Task { await viewModel.performPasskeyLogin() }
                } label: {
                    HStack(spacing: 8) {
                        if viewModel.isPasskeyLoading {
                            ProgressView().tint(.primary)
                                .frame(width: 20, height: 20)
                        } else {
                            Image(systemName: "faceid")
                                .font(.system(size: 18))
                                .frame(width: 20, height: 20)
                        }
                        Text("使用通行密钥登录")
                            .font(.system(size: 14, weight: .semibold))
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                    .background(Color(uiColor: .systemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .stroke(Color.primary.opacity(0.15), lineWidth: 1)
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
                .foregroundStyle(focusedField == field ? Color.accentColor : .secondary)
                .frame(width: 24)
            
            if isSecure {
                SecureField(placeholder, text: text)
                    .focused($focusedField, equals: field)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled(true)
            } else {
                TextField(placeholder, text: text)
                    .focused($focusedField, equals: field)
                    .textInputAutocapitalization(.never)
                    .keyboardType(field == .email ? .emailAddress : .default)
                    .autocorrectionDisabled(true)
            }
            
            if field == .password {
                Button { showPassword.toggle() } label: {
                    Image(systemName: showPassword ? "eye.slash.fill" : "eye.fill")
                        .foregroundStyle(.secondary)
                        .frame(width: 24, height: 24)
                }
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 52)
        .background(Color(uiColor: .systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(focusedField == field ? Color.accentColor.opacity(0.8) : Color.primary.opacity(0.15), lineWidth: focusedField == field ? 1.5 : 1)
        )
        .animation(.easeInOut(duration: 0.2), value: focusedField)
    }
    
    // MARK: - Handlers
    private func switchMode(to newMode: AuthMode) {
        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
            viewModel.mode = newMode
            viewModel.errorMessage = nil
            viewModel.successMessage = nil
            focusedField = nil
        }
    }
    
    // MARK: - Footer
    private var footerView: some View {
        VStack(spacing: 4) {
            Text("AlphaSignal Core Engine v2.0")
            Text("Powered by AI & Institutional Data Nodes")
        }
        .font(.system(size: 10, weight: .bold, design: .monospaced))
        .foregroundStyle(.secondary.opacity(0.6))
        .padding(.bottom, 30)
    }
}
