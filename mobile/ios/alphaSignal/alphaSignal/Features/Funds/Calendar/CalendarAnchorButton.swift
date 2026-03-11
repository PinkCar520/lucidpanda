import SwiftUI
import AlphaDesign

struct CalendarAnchorButton: View {
    let viewModel: CalendarViewModel
    @Binding var isExpanded: Bool

    private var todayEvents: [CalendarEvent] {
        viewModel.events(for: Date())
    }

    var body: some View {
        Button {
            withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                isExpanded.toggle()
            }
        } label: {
            Image(systemName: "calendar")
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(todayEvents.isEmpty ? Color.secondary : Color.blue)
        }
    }
}
