import Foundation
import UserNotifications
import AlphaCore
import OSLog

public class AlarmNotificationManager {
    public static let shared = AlarmNotificationManager()
    private let logger = Logger(subsystem: "com.pincar.lucidpanda", category: "Alarm")
    
    private init() {}
    
    public func requestPermissions() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge, .criticalAlert]) { granted, error in
            if granted {
                self.logger.debug("✅ Notification permissions granted (including Critical Alerts)")
            } else if let error = error {
                self.logger.error("❌ Notification permissions failed: \(error.localizedDescription)")
            }
        }
    }
    
    public func sendValuationAlarm(fundName: String, changePct: Double, threshold: Double) {
        let content = UNMutableNotificationContent()
        content.title = String(format: NSLocalizedString("alarm.notification.title %@", comment: ""), fundName)
        content.body = String(format: NSLocalizedString("alarm.notification.body %@ %@", comment: ""), String(format: "%.2f", changePct), String(format: "%.2f", threshold))
        content.sound = .defaultCritical
        
        let request = UNNotificationRequest(
            identifier: "alarm-\(fundName)-\(Date().timeIntervalSince1970)",
            content: content,
            trigger: nil // 立即发送
        )
        
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                self.logger.error("❌ Failed to send alarm: \(error.localizedDescription)")
            }
        }
    }
}
