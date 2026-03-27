import requests

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.providers.channels.base import BaseChannel


class BarkChannel(BaseChannel):
    def send(self, title, message, source_url=None, db_id=None):
        if not settings.BARK_URL or "YOUR_TOKEN" in settings.BARK_URL:
            logger.warning("Bark 推送未配置，跳过")
            return

        try:
            import urllib.parse

            # 如果有 URL，在消息末尾增加跳转链接（Bark 会识别自动变蓝/点击跳转）
            if source_url:
                message = f"{message}\n\n🔗 详情: {source_url}"

            encoded_title = urllib.parse.quote(str(title))
            encoded_msg = urllib.parse.quote(str(message))

            # Bark 格式: URL/title/body
            url = f"{settings.BARK_URL.rstrip('/')}/{encoded_title}/{encoded_msg}"

            # 记录发送状态以便追踪
            trace_id = (
                f"ID: {db_id}"
                if db_id
                else f"URL: {source_url}"
                if source_url
                else "N/A"
            )
            resp = requests.get(url, timeout=5)

            if resp.status_code == 200:
                logger.info(f"✅ Bark 推送成功 [{trace_id}]")
            else:
                logger.error(f"❌ Bark 推送失败 [{trace_id}]: HTTP {resp.status_code}")

        except Exception as e:
            trace_id = (
                f"ID: {db_id}"
                if db_id
                else f"URL: {source_url}"
                if source_url
                else "N/A"
            )
            logger.error(f"❌ Bark 发送异常 [{trace_id}]: {e}")
