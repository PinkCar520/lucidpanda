import SwiftUI

public struct FundSparkline: View {
    let data: [Double]
    let isPositive: Bool
    
    public init(data: [Double], isPositive: Bool = true) {
        self.data = data
        self.isPositive = isPositive
    }
    
    public var body: some View {
        Canvas { context, size in
            guard data.count >= 2 else { return }
            
            let color = isPositive ? Color.red : Color.green
            var path = Path()
            
            for (index, value) in data.enumerated() {
                let x = size.width * CGFloat(index) / CGFloat(data.count - 1)
                let y = size.height * (1 - CGFloat(value))
                
                if index == 0 {
                    path.move(to: CGPoint(x: x, y: y))
                } else {
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
            
            // Draw stroke
            context.stroke(path, with: .color(color), lineWidth: 1.5)
            
            // Draw area fill
            var fillPath = path
            fillPath.addLine(to: CGPoint(x: size.width, y: size.height))
            fillPath.addLine(to: CGPoint(x: 0, y: size.height))
            fillPath.closeSubpath()
            
            context.fill(fillPath, with: .color(color.opacity(0.1)))
        }
    }
}

#Preview {
    FundSparkline(data: [0.1, 0.4, 0.3, 0.8, 0.5, 0.9], isPositive: true)
        .frame(width: 100, height: 40)
        .padding()
}
