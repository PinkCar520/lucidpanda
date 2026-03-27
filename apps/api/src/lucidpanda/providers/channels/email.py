import smtplib
from email.header import Header
from email.mime.text import MIMEText

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.providers.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    def send(self, title, message, source_url=None, db_id=None):
        if not settings.EMAIL_SENDER or not settings.EMAIL_PASSWORD:
            logger.warning("邮件配置缺失，跳过发送")
            return

        try:
            # 同样在邮件末尾增加源链接以便追踪
            if source_url:
                message = f"{message}\n\n----------------------------\n🔗 详情追溯: {source_url}"

            msg = MIMEText(message, "plain", "utf-8")
            msg["Subject"] = Header(title, "utf-8")
            msg["From"] = settings.EMAIL_SENDER
            msg["To"] = settings.EMAIL_RECEIVER

            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
            server.sendmail(
                settings.EMAIL_SENDER, [settings.EMAIL_RECEIVER], msg.as_string()
            )
            server.quit()

            trace_id = (
                f"ID: {db_id}"
                if db_id
                else f"URL: {source_url}"
                if source_url
                else "N/A"
            )
            logger.info(f"✅ 邮件已成功投递至 {settings.EMAIL_RECEIVER} [{trace_id}]")
        except Exception as e:
            trace_id = (
                f"ID: {db_id}"
                if db_id
                else f"URL: {source_url}"
                if source_url
                else "N/A"
            )
            logger.error(f"❌ 邮件投递失败 [{trace_id}]: {e}")
