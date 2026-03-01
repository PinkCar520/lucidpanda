import SwiftUI
import UIKit

public struct LiquidAddButton: View {
    let isAdded: Bool
    let action: () async -> Void
    
    @State private var isProcessing = false
    @State private var bounceTrigger = 0
    
    public init(isAdded: Bool, action: @escaping () async -> Void) {
        self.isAdded = isAdded
        self.action = action
    }
    
    public var body: some View {
        Button {
            let generator = UIImpactFeedbackGenerator(style: .light)
            generator.prepare()
            generator.impactOccurred()
            
            Task {
                if !isAdded {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        isProcessing = true
                    }
                }
                
                await action()
                
                if !isAdded {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        isProcessing = false
                    }
                }
                
                bounceTrigger += 1
                
                let successGen = UINotificationFeedbackGenerator()
                successGen.notificationOccurred(isAdded ? .warning : .success)
            }
        } label: {
            ZStack {
                if isProcessing {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .scaleEffect(0.8)
                        .tint(.blue)
                        .transition(.scale.combined(with: .opacity))
                } else if isAdded {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 22))
                        .foregroundStyle(
                            LinearGradient(colors: [.green, .mint], startPoint: .topLeading, endPoint: .bottomTrailing)
                        )
                        .symbolEffect(.bounce.byLayer, value: bounceTrigger)
                        .transition(.scale.combined(with: .opacity))
                } else {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 22))
                        .foregroundStyle(.blue.opacity(0.8))
                        .symbolRenderingMode(.hierarchical)
                        .transition(.scale.combined(with: .opacity))
                }
            }
            .frame(width: 30, height: 30)
        }
        .buttonStyle(.plain)
    }
}
