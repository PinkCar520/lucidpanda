import SwiftUI

public struct LiquidTicker: View {
    let value: Double
    let precision: Int
    let prefix: String
    
    @State private var flickerOpacity: Double = 0
    @State private var lastValue: Double = 0
    
    public init(value: Double, precision: Int = 4, prefix: String = "") {
        self.value = value
        self.precision = precision
        self.prefix = prefix
    }
    
    public var body: some View {
        ZStack {
            // Amber Flicker Effect
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color.orange.opacity(0.3))
                .blur(radius: 20)
                .opacity(flickerOpacity)
            
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                if !prefix.isEmpty {
                    Text(prefix)
                        .font(.system(size: 16, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                
                Text(String(format: "%.\(precision)f", value))
                    .font(.system(size: 36, weight: .black, design: .monospaced))
                    .contentTransition(.numericText())
                    .transaction { transaction in
                        transaction.animation = .spring(response: 0.3, dampingFraction: 0.7)
                    }
            }
        }
        .onChange(of: value) { oldValue, newValue in
            if newValue != oldValue {
                triggerFlicker()
            }
        }
    }
    
    private func triggerFlicker() {
        withAnimation(.easeIn(duration: 0.05)) {
            flickerOpacity = 1.0
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            withAnimation(.easeOut(duration: 0.2)) {
                flickerOpacity = 0
            }
        }
    }
}

#Preview {
    VStack {
        LiquidTicker(value: 1.2345)
        Button("Update") {
            // Simulate update
        }
    }
    .padding()
    .background(Color.black.opacity(0.1))
}
