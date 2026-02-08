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
                    Text("个人中心")
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
                                Text("Alpha 交易员")
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
                        Text("安全管理")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(.gray)
                            .padding(.horizontal)
                        
                        VStack(spacing: 1) {
                            settingsButton(icon: "lock.shield.fill", title: "修改账户密码", color: .blue) {
                                isPasswordDialogOpen = true
                            }
                            settingsButton(icon: "phone.badge.checkmark", title: "身份验证信息", color: .green) {
                                // 逻辑类似
                            }
                            settingsButton(icon: "key.viewfinder", title: "双重身份认证 (2FA)", color: .orange) {
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
                        Text("断开同步连接")
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
    
    private func settingsButton(icon: String, title: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                    .frame(width: 32)
                Text(title)
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
                Text("修改账户密码").font(.headline)
                VStack(spacing: 12) {
                    SecureField("当前密码", text: .constant(""))
                        .textFieldStyle(GlassTextFieldStyle())
                    SecureField("新密码", text: .constant(""))
                        .textFieldStyle(GlassTextFieldStyle())
                }
                Button("保存更改") { isPasswordDialogOpen = false }
                    .buttonStyle(.borderedProminent)
            }
            .padding()
        }
    }
    
    private var twoFASetupDialog: some View {
        Dialog(isOpen: $is2FADialogOpen) {
            VStack(spacing: 20) {
                Text("2FA 双重验证").font(.headline)
                Image(systemName: "qrcode").font(.system(size: 80))
                Text("请扫描二维码以绑定身份验证器").font(.caption).foregroundStyle(.gray)
                Button("完成") { is2FADialogOpen = false }
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
    
    init(isOpen: @Binding var Bool, @ViewBuilder content: () -> Content) {
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
