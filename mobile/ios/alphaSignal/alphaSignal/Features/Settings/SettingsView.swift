import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct SettingsView: View {
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var isPasswordDialogOpen = false
    @State private var is2FADialogOpen = false
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            ScrollView {
                VStack(spacing: 24) {
                    Text("settings.title")
                        .font(.system(size: 24, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                        .padding(.top, 24)
                    
                    // 用户基本资料卡片
                    LiquidGlassCard {
                        HStack(spacing: 20) {
                            Circle()
                                .fill(Color.blue)
                                .frame(width: 64, height: 64)
                                .overlay(Text("A").font(.title.bold()).foregroundStyle(.white))
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text("settings.user.display_name")
                                    .font(.headline)
                                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                                Text("pincar@alphasignal.com")
                                    .font(.caption)
                                    .foregroundStyle(.gray)
                            }
                            Spacer()
                        }
                    }
                    .padding(.horizontal)
                    
                    // 安全操作模块 (对齐 Web 端弹窗设计)
                    VStack(alignment: .leading, spacing: 12) {
                        Text("settings.section.security")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(.gray)
                            .padding(.horizontal)
                        
                        VStack(spacing: 1) {
                            settingsButton(icon: "lock.shield.fill", titleKey: "settings.action.change_password", color: .blue) {
                                isPasswordDialogOpen = true
                            }
                            settingsButton(icon: "phone.badge.checkmark", titleKey: "settings.action.identity", color: .green) {
                                // 逻辑类似
                            }
                            settingsButton(icon: "key.viewfinder", titleKey: "settings.action.two_factor", color: .orange) {
                                is2FADialogOpen = true
                            }
                        }
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 20))
                        .shadow(color: .black.opacity(0.05), radius: 10)
                        .padding(.horizontal)
                    }
                    
                    // 登出按钮
                    Button {
                        try? KeychainManager.shared.delete(key: "access_token")
                        rootViewModel.updateState(to: .unauthenticated)
                    } label: {
                        Text("settings.action.logout")
                            .font(.subheadline.bold())
                            .foregroundStyle(.red)
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(Color.red.opacity(0.05))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }
                    .padding(.horizontal)
                    .padding(.top, 20)
                }
            }
            
            // --- 弹窗逻辑 ---
            if isPasswordDialogOpen {
                passwordChangeDialog
            }
            
            if is2FADialogOpen {
                twoFASetupDialog
            }
        }
    }
    
    private func settingsButton(icon: String, titleKey: LocalizedStringKey, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                    .frame(width: 32)
                Text(titleKey)
                    .font(.subheadline)
                    .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption2.bold())
                    .foregroundStyle(.gray.opacity(0.3))
            }
            .padding()
            .background(Color.white)
        }
    }
    
    // 修改密码弹窗组件
    private var passwordChangeDialog: some View {
        Dialog(isOpen: $isPasswordDialogOpen) {
            VStack(spacing: 20) {
                Text("settings.dialog.change_password.title").font(.headline)
                VStack(spacing: 12) {
                    SecureField("settings.field.current_password", text: .constant(""))
                        .textFieldStyle(GlassTextFieldStyle())
                    SecureField("settings.field.new_password", text: .constant(""))
                        .textFieldStyle(GlassTextFieldStyle())
                }
                Button("settings.action.save_changes") { isPasswordDialogOpen = false }
                    .buttonStyle(.borderedProminent)
            }
            .padding()
        }
    }
    
    private var twoFASetupDialog: some View {
        Dialog(isOpen: $is2FADialogOpen) {
            VStack(spacing: 20) {
                Text("settings.dialog.two_factor.title").font(.headline)
                Image(systemName: "qrcode").font(.system(size: 80))
                Text("settings.dialog.two_factor.hint").font(.caption).foregroundStyle(.gray)
                Button("settings.action.done") { is2FADialogOpen = false }
                    .buttonStyle(.borderedProminent)
            }
            .padding()
        }
    }
}

// 补充一个极简的 Dialog 包装器，如果没有使用 Radix 的话
struct Dialog<Content: View>: View {
    @Binding var isOpen: Bool
    let content: Content
    
    init(isOpen: Binding<Bool>, @ViewBuilder content: () -> Content) {
        self._isOpen = isOpen
        self.content = content()
    }
    
    var body: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()
                .onTapGesture { isOpen = false }
            
            VStack {
                content
            }
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 24))
            .shadow(radius: 20)
            .padding(40)
        }
    }
}
