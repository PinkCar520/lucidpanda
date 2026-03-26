import imaplib
import os
import socket
import ssl
import sys

# 路径修复
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root_dir, "apps/api"))
from src.lucidpanda.config import settings  # noqa: E402


def test_imap_connection():
    server = settings.IMAP_SERVER or "outlook.office365.com"
    port = settings.IMAP_PORT or 993
    user = settings.IMAP_USER

    print(f"📡 Diagnostic: Attempting to connect to {server}:{port}...")

    # 1. TCP 握手测试
    try:
        sock = socket.create_connection((server, port), timeout=10)
        print("✅ Step 1: TCP Connection Successful.")
        sock.close()
    except Exception as e:
        print(f"❌ Step 1: TCP Connection Failed: {e}")
        return

    # 2. SSL/TLS 层测试
    try:
        context = ssl.create_default_context()
        with socket.create_connection((server, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=server) as ssock:
                print(f"✅ Step 2: SSL/TLS Handshake Successful. Protocol: {ssock.version()}")
    except Exception as e:
        print(f"❌ Step 2: SSL/TLS Handshake Failed: {e}")
        return

    # 3. IMAP 登录测试
    try:
        print(f"🔐 Step 3: Attempting IMAP Login for {user}...")
        mail = imaplib.IMAP4_SSL(server, port)
        # 开启调试模式输出原始报文
        mail.debug = 4
        res, detail = mail.login(user, settings.IMAP_PASSWORD)
        print(f"✅ Step 3: IMAP Login Successful! Status: {res}")
        mail.logout()
    except imaplib.IMAP4.error as e:
        print(f"❌ Step 3: IMAP Login Failed (Protocol Error): {e}")
    except Exception as e:
        print(f"❌ Step 3: IMAP Login Failed (Network/Other): {e}")

if __name__ == "__main__":
    test_imap_connection()
