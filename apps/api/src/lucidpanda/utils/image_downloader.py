import os
import uuid
import httpx
import asyncio
from pathlib import Path
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger

class ImageDownloader:
    """新闻图片本地缓存下载器"""
    
    def __init__(self):
        # 统一使用根目录下的 uploads/news，确保与 Docker volumes (./uploads:/app/uploads) 匹配
        # settings.BASE_DIR 是 apps/api，所以 parent.parent 指向项目根目录
        self.base_upload_dir = Path(settings.BASE_DIR).parent.parent / "uploads" / "news"
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }

    async def download_image(self, url: str) -> str | None:
        """
        下载图片并返回本地相对路径。
        
        Args:
            url: 图片原始 URL
            
        Returns:
            str: 本地相对路径（用于前端访问），下载失败则返回 None
        """
        if not url or not url.startswith("http"):
            return None
            
        try:
            # 自动识别后缀名
            ext = ".jpg"
            if ".png" in url.lower(): ext = ".png"
            elif ".webp" in url.lower(): ext = ".webp"
            elif ".gif" in url.lower(): ext = ".gif"
            
            filename = f"{uuid.uuid4()}{ext}"
            file_path = self.base_upload_dir / filename
            
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    
                    # 返回相对路径，前端拼接 base_url 后访问，例如: /static/news/filename.jpg
                    return f"news/{filename}"
                else:
                    logger.warning(f"图片下载失败 (HTTP {response.status_code}): {url}")
        except Exception as e:
            logger.error(f"图片下载异常: {e} | URL: {url}")
            
        return None

image_downloader = ImageDownloader()
