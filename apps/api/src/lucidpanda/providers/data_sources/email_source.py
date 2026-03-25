import os
import imaplib
import email
from email.header import decode_header
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from src.lucidpanda.core.logger import logger
from src.lucidpanda.config import settings
from src.lucidpanda.providers.data_sources.base import BaseDataSource

class EmailDataSource(BaseDataSource):
    """
    基于 IMAP 的情报摄入源。
    专门监听来自白宫、美联储等官方域名的邮件通知。
    """
    
    OFFICIAL_DOMAINS = {
        "who.eop.gov": "White House",
        "frb.gov": "Federal Reserve",
        "federalreserve.gov": "Federal Reserve",
        "cftc.gov": "CFTC",
        "govdelivery.com": "Official News Service",  # 关键：美联储和白宫邮件系统的实际外发域名
        "usa.gov": "Official Gov",
    }

    def __init__(self, db=None):
        super().__init__(db)
        self.server = settings.IMAP_SERVER
        self.port = settings.IMAP_PORT
        self.user = settings.IMAP_USER
        self.password = settings.IMAP_PASSWORD

    def _decode_str(self, s: Any) -> str:
        if s is None:
            return ""
        if isinstance(s, bytes):
            value, charset = decode_header(s)[0]
            if charset:
                return value.decode(charset)
            return value.decode("utf-8", errors="ignore")
        return str(s)

    def _fetch_emails_sync(self) -> List[Dict[str, Any]]:
        """深度重构的同步抓取逻辑，完全适配网易 163 邮箱开发者规范。"""
        items = []
        if not all([self.server, self.user, self.password]):
            logger.warning("⚠️ IMAP 配置不完整，跳过采集。")
            return items

        try:
            # 1. 建立 SSL 连接
            mail = imaplib.IMAP4_SSL(self.server, self.port)
            
            # 2. 【关键】网易 163 要求 ID 指令声明身份
            # 尝试在登录前和登录后都发送一次，使用最简约的 ios 声明
            try:
                mail.xatom('ID', '("name" "ios")')
            except:
                pass

            # 3. 登录
            mail.login(self.user, self.password)
            
            # 登录后再发一次 ID 指令（部分 163 账户要求在登录后确认）
            try:
                mail.xatom('ID', '("name" "ios")')
            except:
                pass

            # --- 诊断：列出该账户所有可用的文件夹 ---
            try:
                _, folders = mail.list()
                # 提取带双引号的真实名称
                logger.info(f"📁 您的 163 邮箱可用文件夹: {[f.decode() for f in folders]}")
            except:
                pass

            # 4. 扫描文件夹
            # 网易会将通稿分发至：INBOX (收件箱)、&dcVr0mWHTvZZOQ- (订阅邮件)、&V4NXPpCuTvY- (垃圾箱)
            target_folders = ["INBOX", "&dcVr0mWHTvZZOQ-", "&V4NXPpCuTvY-"]
            
            for folder in target_folders:
                try:
                    # 尝试进入文件夹
                    status, _ = mail.select(folder)
                    if status != 'OK':
                        # 如果失败，尝试带引号进入
                        status, _ = mail.select(f'"{folder}"')
                    
                    if status != 'OK':
                        logger.info(f"ℹ️ 无法选择文件夹 {folder}: {status}")
                        continue
                    
                    # 搜索总数与未读
                    _, all_msg = mail.search(None, 'ALL')
                    _, unseen_msg = mail.search(None, 'UNSEEN')
                    
                    total = len(all_msg[0].split()) if all_msg[0] else 0
                    unseen = len(unseen_msg[0].split()) if unseen_msg[0] else 0
                    
                    logger.info(f"📂 正在检查文件夹 [{folder}]: 总数={total}, 未读={unseen}")

                    if unseen == 0:
                        continue

                    for num in unseen_msg[0].split():
                        # 抓取邮件
                        res, msg_data = mail.fetch(num, '(RFC822)')
                        if res != 'OK':
                            continue

                        raw_content = msg_data[0][1]
                        msg = email.message_from_bytes(raw_content)
                        
                        # 解析元数据
                        sender_raw = self._decode_str(msg.get("From", ""))
                        subject = self._decode_str(msg.get("Subject", ""))
                        
                        # 规范化发件人地址
                        sender_addr = ""
                        if "<" in sender_raw:
                            sender_addr = sender_raw.split("<")[-1].split(">")[0].lower()
                        else:
                            sender_addr = sender_raw.strip().lower()

                        logger.info(f"🔎 正在检查邮件: 发件人={sender_addr}, 标题={subject}")

                        # 来源匹配逻辑 (后缀匹配以支持子域名)
                        source_label = None
                        is_verified = False
                        
                        for domain, label in self.OFFICIAL_DOMAINS.items():
                            if sender_addr.endswith(f"@{domain}") or sender_addr.endswith(f".{domain}"):
                                source_label = label
                                is_verified = True
                                break
                        
                        # 测试绕过
                        test_sender = os.getenv("IMAP_TEST_SENDER", "").lower()
                        if not is_verified and test_sender and test_sender in sender_addr:
                            source_label = "Test Source (Bypass)"
                            is_verified = True

                        if not is_verified:
                            continue

                        # 提取正文
                        content_body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset() or 'utf-8'
                                    content_body = payload.decode(charset, errors='ignore')
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            charset = msg.get_content_charset() or 'utf-8'
                            content_body = payload.decode(charset, errors='ignore')

                        # 构建条目
                        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        msg_id = msg.get("Message-ID", f"manual_{num.decode()}")
                        
                        items.append({
                            "source": source_label,
                            "author": sender_raw,
                            "category": "macro_gold",
                            "timestamp": ts,
                            "content": f"[{subject}] {content_body[:5000]}",
                            "url": f"email://{folder}/{num.decode()}",
                            "id": f"email_{msg_id.strip('<>')}"
                        })

                        # 标记已读
                        mail.store(num, '+FLAGS', '\\Seen')
                        logger.info(f"✅ 成功摄入官方情报: {subject}")

                except Exception as folder_err:
                    logger.debug(f"ℹ️ 文件夹 {folder} 扫描故障: {folder_err}")

            mail.logout()
            logger.info(f"✅ 邮件巡检完毕: 发现并录入 {len(items)} 条新通稿。")
            
        except Exception as e:
            logger.error(f"❌ IMAP 深度摄入失败: {e}")
            
        return items

    async def fetch_async(self) -> List[Dict[str, Any]] | None:
        """异步包装，在线程池中运行同步 IMAP 逻辑。"""
        items = await asyncio.to_thread(self._fetch_emails_sync)
        return items if items else None

    def fetch(self) -> List[Dict[str, Any]] | None:
        """同步调用入口。"""
        return asyncio.run(self.fetch_async())
