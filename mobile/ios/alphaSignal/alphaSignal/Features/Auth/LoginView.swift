import SwiftUI
import AlphaDesign
import UIKit

struct LoginView: View {
    @State private var viewModel = LoginViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    @State private var showPassword = false
    @State private var activePrompt: AuthPrompt?
    @State private var panelState: PanelState = .collapsed
    @GestureState private var panelDragTranslation: CGFloat = 0

    var body: some View {
        GeometryReader { proxy in
            let metrics = panelMetrics(in: proxy)
            let baseTop = panelState == .expanded ? metrics.topExpanded : metrics.topCollapsed
            let proposedTop = baseTop + panelDragTranslation
            let panelTop = clamp(proposedTop, min: metrics.topExpanded, max: metrics.topCollapsed)
            let progress = panelProgress(metrics: metrics, panelTop: panelTop)
            let cornerRadius = panelCornerRadius(progress: progress)

            ZStack(alignment: .top) {
                LiquidBackground()

                loginInteriorLayer(progress: progress)

                loginPanel(metrics: metrics, progress: progress, cornerRadius: cornerRadius)
                    .offset(y: panelTop)
            }
            .ignoresSafeArea()
        }
        .onAppear {
            viewModel.onSuccess = {
                rootViewModel.updateState(to: .authenticated)
            }
        }
        .onChange(of: panelState) { newValue in
            if newValue == .expanded {
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
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

    private func loginInteriorLayer(progress: CGFloat) -> some View {
        VStack(spacing: 16) {
            HStack(spacing: 10) {
                marketPill(title: "上证", value: "+0.8%", trend: .up)
                marketPill(title: "深证", value: "+0.6%", trend: .up)
                marketPill(title: "创业板", value: "-0.3%", trend: .down)
                Spacer(minLength: 0)
            }

            LiquidGlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text("今日风向")
                        .font(.system(size: 14, weight: .bold))

                    previewRow(title: "新能源主题", subtitle: "领涨板块", value: "+3.2%", trend: .up)
                    previewRow(title: "红利低波", subtitle: "资金净流入", value: "+2.1 亿", trend: .up)
                }
                .padding(.vertical, 8)
            }

            LiquidGlassCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text("市场温度计")
                        .font(.system(size: 13, weight: .bold))

                    HStack(spacing: 10) {
                        heatTag(title: "低温", color: .green)
                        heatTag(title: "中性", color: .yellow)
                        heatTag(title: "高温", color: .red)
                        Spacer(minLength: 0)
                    }

                    Text("滑动面板，切换看盘视角")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 8)
            }

            Spacer(minLength: 0)
        }
        .padding(.top, 72)
        .padding(.horizontal, 20)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .opacity(1 - progress * 0.35)
        .blur(radius: 6 * progress)
        .overlay(Color.black.opacity(0.18 * progress))
        .allowsHitTesting(false)
    }

    private func loginPanel(metrics: PanelMetrics, progress: CGFloat, cornerRadius: CGFloat) -> some View {
        let collapsedOpacity = max(0, 1 - progress * 1.15)
        let expandedOpacity = max(0, min(1, (progress - 0.05) / 0.95))

        return VStack(spacing: 0) {
            panelHeader(progress: progress, metrics: metrics)

            ScrollView(showsIndicators: false) {
                ZStack(alignment: .top) {
                    collapsedPanelContent
                        .opacity(collapsedOpacity)
                        .offset(y: 12 * progress)
                        .allowsHitTesting(panelState == .collapsed)

                    expandedPanelContent
                        .opacity(expandedOpacity)
                        .offset(y: 16 * (1 - progress))
                        .allowsHitTesting(panelState == .expanded)
                }
                .frame(maxWidth: .infinity, alignment: .top)
                .padding(.horizontal, 20)
                .padding(.bottom, 24)
                .padding(.top, 8)
            }
            .scrollDisabled(panelState == .collapsed)
        }
        .frame(maxWidth: .infinity, maxHeight: metrics.panelHeight, alignment: .top)
        .background(
            .ultraThinMaterial,
            in: RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .stroke(Color.white.opacity(0.18), lineWidth: 1)
        )
    }

    private func panelHeader(progress: CGFloat, metrics: PanelMetrics) -> some View {
        VStack(spacing: 6) {
            Capsule()
                .fill(Color.secondary.opacity(0.4))
                .frame(width: 36, height: 4)

            HStack(spacing: 6) {
                Text(panelState == .expanded ? "向下拖拽收起" : "向上滑动进入")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                Image(systemName: panelState == .expanded ? "chevron.down" : "chevron.up")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .opacity(0.8 - progress * 0.2)
        }
        .padding(.top, 12)
        .padding(.bottom, 8)
        .frame(maxWidth: .infinity)
        .contentShape(Rectangle())
        .gesture(panelDragGesture(metrics: metrics))
        .onTapGesture {
            togglePanel()
        }
    }

    private var collapsedPanelContent: some View {
        VStack(spacing: 18) {
            VStack(spacing: 8) {
                Image(systemName: "chart.line.uptrend.xyaxis.circle.fill")
                    .font(.system(size: 46))
                    .foregroundStyle(.primary)

                Text("AlphaSignal")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)

                Text("auth.login.subtitle")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            Button {
                Task { await viewModel.performPasskeyLogin() }
            } label: {
                HStack(spacing: 8) {
                    if viewModel.isPasskeyLoading {
                        ProgressView()
                            .tint(Color(uiColor: .systemBackground))
                    } else {
                        Image(systemName: "person.badge.key.fill")
                            .font(.system(size: 14, weight: .semibold))
                    }
                    Text("auth.action.passkey_login")
                        .font(.system(size: 15, weight: .semibold))
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(FintechPrimaryButtonStyle())
            .disabled(viewModel.isLoading || viewModel.isPasskeyLoading)

            Button {
                updatePanelState(.expanded)
            } label: {
                Text("使用账号密码登录")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var expandedPanelContent: some View {
        VStack(spacing: 20) {
            loginFormCard

            VStack(spacing: 4) {
                Text("auth.status.secure_channel")
                Text("auth.status.module_ready")
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
    }

    private var loginFormCard: some View {
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
                            ProgressView().tint(Color(uiColor: .systemBackground))
                        } else {
                            Text("auth.action.login")
                                .fontWeight(.semibold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(FintechPrimaryButtonStyle())
                .disabled(viewModel.isLoading || viewModel.isPasskeyLoading || !viewModel.canSubmit)

                Button {
                    Task { await viewModel.performPasskeyLogin() }
                } label: {
                    HStack(spacing: 8) {
                        if viewModel.isPasskeyLoading {
                            ProgressView()
                                .tint(.primary)
                        } else {
                            Image(systemName: "person.badge.key.fill")
                                .font(.system(size: 14, weight: .semibold))
                        }
                        Text("auth.action.passkey_login")
                            .font(.system(size: 15, weight: .semibold))
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(FintechSecondaryButtonStyle())
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
    }

    private func togglePanel() {
        updatePanelState(panelState == .expanded ? .collapsed : .expanded)
    }

    private func updatePanelState(_ newState: PanelState) {
        withAnimation(.spring(response: 0.45, dampingFraction: 0.86)) {
            panelState = newState
        }
    }

    private func panelDragGesture(metrics: PanelMetrics) -> some Gesture {
        DragGesture(minimumDistance: 12)
            .updating($panelDragTranslation) { value, state, _ in
                state = value.translation.height
            }
            .onEnded { value in
                let baseTop = panelState == .expanded ? metrics.topExpanded : metrics.topCollapsed
                let predictedTop = baseTop + value.predictedEndTranslation.height
                let midpoint = (metrics.topExpanded + metrics.topCollapsed) / 2
                let shouldExpand = predictedTop < midpoint
                updatePanelState(shouldExpand ? .expanded : .collapsed)
            }
    }

    private func panelMetrics(in proxy: GeometryProxy) -> PanelMetrics {
        let height = proxy.size.height
        let topSafe = proxy.safeAreaInsets.top
        let bottomSafe = proxy.safeAreaInsets.bottom
        let collapsedPeek = min(height * 0.42, 320)
        let topCollapsed = height - collapsedPeek
        let topExpanded = max(topSafe + 18, 36)
        let panelHeight = height - topExpanded + bottomSafe
        return PanelMetrics(topExpanded: topExpanded, topCollapsed: topCollapsed, panelHeight: panelHeight)
    }

    private func panelProgress(metrics: PanelMetrics, panelTop: CGFloat) -> CGFloat {
        let range = metrics.topCollapsed - metrics.topExpanded
        guard range > 0 else { return 1 }
        return 1 - (panelTop - metrics.topExpanded) / range
    }

    private func panelCornerRadius(progress: CGFloat) -> CGFloat {
        let collapsed: CGFloat = 34
        let expanded: CGFloat = 22
        return collapsed - (collapsed - expanded) * progress
    }

    private func clamp(_ value: CGFloat, min minValue: CGFloat, max maxValue: CGFloat) -> CGFloat {
        Swift.min(Swift.max(value, minValue), maxValue)
    }

    private enum MarketTrend {
        case up
        case down
        case neutral
    }

    private func marketPill(title: String, value: String, trend: MarketTrend) -> some View {
        HStack(spacing: 6) {
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(trend == .up ? .red : trend == .down ? .green : .secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Color.white.opacity(0.14))
        .clipShape(Capsule())
    }

    private func previewRow(title: String, subtitle: String, value: String, trend: MarketTrend) -> some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 12, weight: .bold))
                Text(subtitle)
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(value)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(trend == .up ? .red : trend == .down ? .green : .secondary)
        }
        .padding(10)
        .background(Color.white.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func heatTag(title: String, color: Color) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(color.opacity(0.85))
                .frame(width: 8, height: 8)
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(Color.white.opacity(0.1))
        .clipShape(Capsule())
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

    private enum PanelState {
        case collapsed
        case expanded
    }

    private struct PanelMetrics {
        let topExpanded: CGFloat
        let topCollapsed: CGFloat
        let panelHeight: CGFloat
    }

    private enum AuthPrompt {
        case forgotPassword
        case createAccount
    }
}
