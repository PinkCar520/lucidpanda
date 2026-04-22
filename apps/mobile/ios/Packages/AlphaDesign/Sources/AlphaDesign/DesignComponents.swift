import SwiftUI

public struct LiquidBackground: View {
    public init() {}

    public var body: some View {
        Color.Alpha.background
        .ignoresSafeArea()
    }
}

public struct LiquidGlassCard<Content: View>: View {
    let content: Content
    var backgroundColor: Color?
    var showBorder: Bool
    @Environment(\.colorScheme) var colorScheme

    public init(backgroundColor: Color? = nil, showBorder: Bool = false, @ViewBuilder content: () -> Content) {
        self.backgroundColor = backgroundColor
        self.showBorder = showBorder
        self.content = content()
    }

    public var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 4, style: .continuous)
                    .fill(backgroundColor ?? Color.Alpha.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 4, style: .continuous)
                    .stroke(colorScheme == .dark ? Color(hex: "#2D2D2D") : Color.Alpha.separator, lineWidth: 1)
            )
            .shadow(color: colorScheme == .light ? Color.black.opacity(0.05) : Color.clear, radius: 2, y: 1)
    }
}

public struct GlassTextFieldStyle: TextFieldStyle {
    public init() {}
    public func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .font(.body)
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color(uiColor: .separator).opacity(0.25), lineWidth: 0.5)
            )
    }
}

public struct FintechPrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.medium))
            .foregroundStyle(Color(uiColor: .systemBackground))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .label))
            )
            .opacity(isEnabled ? (configuration.isPressed ? 0.88 : 1.0) : 0.45)
            .scaleEffect(configuration.isPressed ? 0.99 : 1.0)
            .animation(.easeOut(duration: 0.16), value: configuration.isPressed)
    }
}

public struct FintechSecondaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.regular))
            .foregroundStyle(Color(uiColor: .label))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 13)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Color(uiColor: .separator).opacity(0.28), lineWidth: 0.7)
            )
            .opacity(isEnabled ? (configuration.isPressed ? 0.88 : 1.0) : 0.5)
            .scaleEffect(configuration.isPressed ? 0.99 : 1.0)
            .animation(.easeOut(duration: 0.16), value: configuration.isPressed)
    }
}
