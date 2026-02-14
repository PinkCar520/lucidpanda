import SwiftUI

public struct LiquidBackground: View {
    public init() {}
    
    public var body: some View {
        // 锁定为 Web 端的纯净白/浅蓝背景
        ZStack {
            Color(red: 0.98, green: 0.99, blue: 1.0) 
        }
        .ignoresSafeArea()
    }
}

public struct LiquidGlassCard<Content: View>: View {
    let content: Content
    
    public init(@ViewBuilder content: () -> Content) { self.content = content() }
    
    public var body: some View {
        ZStack {
            // 对齐 Web 浅色卡片效果
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color.white)
                .shadow(color: Color.black.opacity(0.05), radius: 15, x: 0, y: 5)
            
            // 极简细边框
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.black.opacity(0.05), lineWidth: 1)
            
            content.padding(20)
        }
    }
}

public struct GlassTextFieldStyle: TextFieldStyle {
    public init() {}
    public func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding()
            .background(Color.black.opacity(0.05))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .font(.system(size: 14, weight: .medium, design: .monospaced))
    }
}
