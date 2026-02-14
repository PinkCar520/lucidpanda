import Foundation
import UserNotifications
import AlphaCore
import OSLog

public class AlarmNotificationManager {
    public static let shared = AlarmNotificationManager()
    private let logger = Logger(subsystem: "com.pincar.alphasignal", category: "Alarm")
    
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
        content.title = "⚠️ [异常波动预警] \(fundName)"
        content.body = "盘中估值当前波动为 \(String(format: "%.2f", changePct))%，已突破 \(String(format: "%.2f", threshold))% 的 2σ 统计边界。"
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
