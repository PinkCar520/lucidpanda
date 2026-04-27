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
        # 优先从环境变量获取，或者根据 BASE_DIR 自动推断
        # 在 Docker 中，BASE_DIR 是 /app，uploads 应该在 /app/uploads
        # 在本地开发，BASE_DIR 是 apps/api，uploads 应该在 ../../uploads
        env_upload_dir = os.getenv("UPLOADS_DIR")
        if env_upload_dir:
            self.base_upload_dir = Path(env_upload_dir) / "news"
        else:
            # 智能推断：如果 BASE_DIR 下有 uploads，则使用之；否则使用 parent.parent (针对本地开发)
            local_uploads = Path(settings.BASE_DIR) / "uploads"
            if local_uploads.exists() or os.path.exists("/.dockerenv"):
                self.base_upload_dir = local_uploads / "news"
            else:
                self.base_upload_dir = Path(settings.BASE_DIR).parent.parent / "uploads" / "news"
        
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }

    async def _do_download(self, url: str, file_path: Path, trust_env: bool = True) -> bool:
        """执行实际的下载操作"""
        timeout = httpx.Timeout(20.0, connect=10.0)
        try:
            async with httpx.AsyncClient(
                headers=self.headers, 
                timeout=timeout, 
                follow_redirects=True,
                verify=False,
                trust_env=trust_env
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    logger.debug(f"下载尝试失败 (HTTP {response.status_code}, trust_env={trust_env}): {url}")
                    return False
        except Exception as e:
            logger.debug(f"下载尝试异常 ({type(e).__name__}, trust_env={trust_env}): {url}")
            return False

    async def download_image(self, url: str) -> str | None:
        """
        下载图片并返回本地相对路径。支持代理失败后直连重试。
        """
        if not url or not url.startswith("http"):
            return None
            
        try:
            # 自动识别后缀名
            ext = ".jpg"
            url_lower = url.lower()
            if ".png" in url_lower: ext = ".png"
            elif ".webp" in url_lower: ext = ".webp"
            elif ".gif" in url_lower: ext = ".gif"
            
            filename = f"{uuid.uuid4()}{ext}"
            file_path = self.base_upload_dir / filename
            
            # 第一步：尝试使用系统代理 (trust_env=True)
            success = await self._do_download(url, file_path, trust_env=True)
            
            # 第二步：如果失败，尝试直连 (trust_env=False)
            if not success:
                success = await self._do_download(url, file_path, trust_env=False)
            
            if success:
                return f"news/{filename}"
            else:
                logger.warning(f"图片下载彻底失败: {url}")
                
        except Exception as e:
            logger.error(f"图片下载过程发生崩溃: {type(e).__name__}({e}) | URL: {url}")
            
        return None

image_downloader = ImageDownloader()
