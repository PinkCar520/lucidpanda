import SwiftUI

public struct LiquidBackground: View {
    public init() {}
    
    public var body: some View {
        Color(uiColor: .systemGroupedBackground)
            .ignoresSafeArea()
    }
}

public struct LiquidGlassCard<Content: View>: View {
    let content: Content
    
    public init(@ViewBuilder content: () -> Content) { self.content = content() }
    
    public var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemGroupedBackground))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Color(uiColor: .separator).opacity(0.25), lineWidth: 0.5)
            )
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
