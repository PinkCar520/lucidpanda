"""
LucidPanda 配置模块
统一管理所有配置项
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# =============================================================================
# 环境变量加载
# =============================================================================


def find_project_root() -> Path:
    """
    查找项目根目录
    通过向上查找包含 .env 文件的目录来确定项目根目录
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    # 如果找不到 .env，使用当前工作目录
    return Path.cwd()


_project_root = find_project_root()

# 加载根目录 .env
load_dotenv(_project_root / ".env")

# 加载可选的专项配置文件
for config_file in [".env.ai"]:
    config_path = _project_root / config_file
    if config_path.exists():
        load_dotenv(config_path, override=True)


# =============================================================================
# 配置类定义
# =============================================================================


class Settings:
    """
    全局配置类，从环境变量加载配置
    按功能模块分组组织配置项
    """

    # -------------------------------------------------------------------------
    # 1. 基础运行时配置
    # -------------------------------------------------------------------------
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 2))

    # -------------------------------------------------------------------------
    # 2. AI Provider 选择
    # -------------------------------------------------------------------------
    AI_PROVIDER = os.getenv("AI_PROVIDER", "qwen")
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "dashscope")

    # -------------------------------------------------------------------------
    # 3. LLM 提供商配置
    # -------------------------------------------------------------------------

    # 3.1 Google Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_BATCH_MODEL = os.getenv("GEMINI_BATCH_MODEL", "gemini-2.0-flash-lite")
    GEMINI_EMBEDDING_MODEL = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"
    )
    GEMINI_USE_VERTEXAI = os.getenv("GEMINI_USE_VERTEXAI", "False").lower() == "true"
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # 3.2 DeepSeek
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    # 3.3 阿里云 Qwen (百炼)
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.5-flash")
    QWEN_BASE_URL = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 3.4 OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # -------------------------------------------------------------------------
    # 4. Embedding 提供商配置
    # -------------------------------------------------------------------------

    # 阿里云 DashScope
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    DASHSCOPE_EMBEDDING_MODEL = os.getenv(
        "DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3"
    )
    DASHSCOPE_EMBEDDING_DIMENSIONS = int(
        os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", 768)
    )

    # -------------------------------------------------------------------------
    # 5. 去重与语义分析配置
    # -------------------------------------------------------------------------
    NEWS_SIMILARITY_THRESHOLD = float(os.getenv("NEWS_SIMILARITY_THRESHOLD", 0.7))
    NEWS_DEDUPE_WINDOW_HOURS = int(os.getenv("NEWS_DEDUPE_WINDOW_HOURS", 24))
    ENABLE_SEMANTIC_DEDUPE = (
        os.getenv("ENABLE_SEMANTIC_DEDUPE", "true").lower() == "true"
    )

    # -------------------------------------------------------------------------
    # 6. 运行时配置
    # -------------------------------------------------------------------------
    # LLM 并发限制
    LLM_CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", "5"))

    # LLM 降级顺序
    LLM_FALLBACK_ORDER = [
        p.strip()
        for p in os.getenv("LLM_FALLBACK_ORDER", "qwen,deepseek,gemini").split(",")
    ]

    # Agent 工具配置
    ENABLE_AGENT_TOOLS = os.getenv("ENABLE_AGENT_TOOLS", "true").lower() == "true"
    AGENT_TOOL_MAX_CALLS = int(os.getenv("AGENT_TOOL_MAX_CALLS", "3"))
    AGENT_TOOL_TIMEOUT_SECONDS = int(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "8"))

    # -------------------------------------------------------------------------
    # 7. 通知推送配置
    # -------------------------------------------------------------------------
    BARK_URL = os.getenv("BARK_URL")

    # RSSHub
    RSSHUB_BASE_URL = os.getenv("RSSHUB_BASE_URL", "https://rsshub.app")

    # FRED (Federal Reserve Economic Data)
    FRED_API_KEY = os.getenv("FRED_API_KEY")

    # Email / Notifications
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    # IMAP (Intelligence Ingestion)
    IMAP_SERVER = os.getenv("IMAP_SERVER")
    IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
    IMAP_USER = os.getenv("IMAP_USER")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

    # -------------------------------------------------------------------------
    # 8. 数据库配置
    # -------------------------------------------------------------------------
    DB_TYPE = os.getenv("DB_TYPE", "postgres")

    # PostgreSQL
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "lucidpanda")

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # -------------------------------------------------------------------------
    # 9. 路径配置
    # -------------------------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    LOG_DIR = BASE_DIR / "logs"
    DB_PATH = BASE_DIR.parent.parent / "lucidpanda.db"

    # -------------------------------------------------------------------------
    # 10. 安全认证配置 (JWT)
    # -------------------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-it-in-prod")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # 风险风控
    RISK_DEVICE_MISMATCH_FORCE_REAUTH = (
        os.getenv("RISK_DEVICE_MISMATCH_FORCE_REAUTH", "true").lower() == "true"
    )
    RISK_IP_CHANGE_FORCE_REAUTH = (
        os.getenv("RISK_IP_CHANGE_FORCE_REAUTH", "true").lower() == "true"
    )
    RISK_IP_CHANGE_WINDOW_MINUTES = int(os.getenv("RISK_IP_CHANGE_WINDOW_MINUTES", 10))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 60)
    )

    # WebAuthn (Passkeys)
    RP_ID = os.getenv("RP_ID", "localhost")
    RP_NAME = os.getenv("RP_NAME", "LucidPanda")
    ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

    # -------------------------------------------------------------------------
    # 11. 前端配置
    # -------------------------------------------------------------------------
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")


# =============================================================================
# 单例实例
# =============================================================================
settings = Settings()
