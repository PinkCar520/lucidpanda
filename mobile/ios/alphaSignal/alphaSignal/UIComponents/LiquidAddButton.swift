import SwiftUI
import UIKit

/// 富途/微牛风格的「添加/取消自选」按钮
/// - 核心法则：不阻断、瞬时响应、弱化等待、明确回馈
/// - 永远显示当前状态，绝不显示 Loading 转圈
/// - 点击时触发弹簧动画 + 触觉反馈
public struct LiquidAddButton: View {
    let isAdded: Bool
    let action: () async -> Void

    @State private var bounceTrigger = 0

    public init(isAdded: Bool, action: @escaping () async -> Void) {
        self.isAdded = isAdded
        self.action = action
    }

    public var body: some View {
        Button {
            // 触觉反馈：轻微的「Da」一声
            let generator = UIImpactFeedbackGenerator(style: .light)
            generator.prepare()
            generator.impactOccurred()

            Task {
                // 异步执行添加/删除操作（不阻塞 UI）
                await action()

                // 触发弹跳效果
                bounceTrigger += 1

                // 成功触觉反馈
                let successGen = UINotificationFeedbackGenerator()
                successGen.notificationOccurred(isAdded ? .warning : .success)
            }
        } label: {
            if isAdded {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 22))
                    .foregroundStyle(
                        LinearGradient(colors: [.green, .mint], startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
                    .symbolEffect(.bounce.byLayer, value: bounceTrigger)
            } else {
                Image(systemName: "plus.circle.fill")
                    .font(.system(size: 22))
                    .foregroundStyle(.blue.opacity(0.8))
                    .symbolRenderingMode(.hierarchical)
            }
        }
        .buttonStyle(.plain)
    }
}
