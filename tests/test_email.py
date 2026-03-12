import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os
from dotenv import load_dotenv

# 1. 加载环境变量
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"[x] 找不到 .env 文件: {dotenv_path}")

# 2. 读取配置
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mail.me.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def test_icloud_smtp():
    print("=== iCloud SMTP 配置测试 ===")
    print(f"服务器: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"发件人: {EMAIL_SENDER}")
    print(f"收件人: {EMAIL_RECEIVER}")
    print(f"密码长度: {len(EMAIL_PASSWORD) if EMAIL_PASSWORD else 0} 位")
    print("----------------------------")

    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("[x] 错误: 请先在 .env 中配置 EMAIL_SENDER 和 EMAIL_PASSWORD")
        return

    # 构造简单邮件
    msg = MIMEText('这是一条来自 AlphaSignal 的 SMTP 测试邮件。如果你收到这封信，说明你的 iCloud 配置完全正确！', 'plain', 'utf-8')
    msg['Subject'] = Header('AlphaSignal 配置测试', 'utf-8')
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        print("[*] 正在连接 iCloud 服务器...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        
        print("[*] 开启 TLS 加密...")
        server.starttls()
        
        print("[*] 正在尝试登录...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        print("[*] 正在发送邮件...")
        server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
        
        server.quit()
        print("\n[✅] 恭喜！测试邮件发送成功！请检查你的收件箱。")
        
    except smtplib.SMTPAuthenticationError:
        print("\n[x] 认证失败！")
        print("原因: 用户名或密码错误。")
        print("提示: 必须使用 iCloud 的 'App 专用密码'，而不是 Apple ID 的主密码。")
    except Exception as e:
        print(f"\n[x] 发送失败，错误详情: {e}")

if __name__ == "__main__":
    test_icloud_smtp()
