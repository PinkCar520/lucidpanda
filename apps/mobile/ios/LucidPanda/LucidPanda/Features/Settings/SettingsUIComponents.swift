import SwiftUI
import AlphaDesign

public struct PremiumCard<Content: View>: View {
    let content: Content
    @Environment(\.colorScheme) var colorScheme
    
    public init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }
    
    public var body: some View {
        VStack(spacing: 0) {
            content
        }
        .background(Color.Alpha.surface)
        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 4, style: .continuous)
                .stroke(Color.Alpha.separator, lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.02), radius: 8, x: 0, y: 4)
        .padding(.horizontal, 20)
    }
}

public struct SettingsSectionHeader: View {
    let title: LocalizedStringKey
    
    public init(title: LocalizedStringKey) {
        self.title = title
    }
    
    public var body: some View {
        Text(title)
            .font(.system(size: 11, weight: .black))
            .foregroundStyle(Color.Alpha.taupe)
            .textCase(.uppercase)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 36)
            .padding(.bottom, 6)
    }
}
