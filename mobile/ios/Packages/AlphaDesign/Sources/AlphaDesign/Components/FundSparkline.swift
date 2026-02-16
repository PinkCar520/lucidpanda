import SwiftUI

public struct FundSparkline: View {
    let data: [Double]
    let isPositive: Bool
    
    public init(data: [Double], isPositive: Bool = true) {
        self.data = data
        self.isPositive = isPositive
    }
    
    public var body: some View {
        GeometryReader { geometry in
            if data.count < 2 {
                EmptyView()
            } else {
                let color = isPositive ? Color.red : Color.green
                
                Path { path in
                    for (index, value) in data.enumerated() {
                        let x = geometry.size.width * CGFloat(index) / CGFloat(data.count - 1)
                        let y = geometry.size.height * (1 - CGFloat(value))
                        
                        if index == 0 {
                            path.move(to: CGPoint(x: x, y: y))
                        } else {
                            path.addLine(to: CGPoint(x: x, y: y))
                        }
                    }
                }
                .stroke(color, style: StrokeStyle(lineWidth: 1.5, lineCap: .round, lineJoin: .round))
                
                // Area fill
                Path { path in
                    path.move(to: CGPoint(x: 0, y: geometry.size.height))
                    for (index, value) in data.enumerated() {
                        let x = geometry.size.width * CGFloat(index) / CGFloat(data.count - 1)
                        let y = geometry.size.height * (1 - CGFloat(value))
                        path.addLine(to: CGPoint(x: x, y: y))
                    }
                    path.addLine(to: CGPoint(x: geometry.size.width, y: geometry.size.height))
                    path.closeSubpath()
                }
                .fill(color.opacity(0.1))
            }
        }
    }
}

#Preview {
    FundSparkline(data: [0.1, 0.4, 0.3, 0.8, 0.5, 0.9], isPositive: true)
        .frame(width: 100, height: 40)
        .padding()
}
