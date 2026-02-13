import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Settings:
    """
    全局配置类，从环境变量加载配置
    """
    # 基础配置
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 2))
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # DeepSeek
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 推送配置
    BARK_URL = os.getenv("BARK_URL")
    
    # RSSHub 配置
    RSSHUB_BASE_URL = os.getenv("RSSHUB_BASE_URL", "https://rsshub.app")
    
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend") # 'resend' or 'smtp'
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    # Database
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "alphasignal")
    
    # News Deduplication Settings
    NEWS_SIMILARITY_THRESHOLD = float(os.getenv("NEWS_SIMILARITY_THRESHOLD", 0.7)) # Cosine similarity for news content
    NEWS_DEDUPE_WINDOW_HOURS = int(os.getenv("NEWS_DEDUPE_WINDOW_HOURS", 24)) # How many hours back to check for duplicates
    
    # 路径配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    STATE_FILE = os.path.join(BASE_DIR, "monitor_state.json")
    DB_PATH = os.path.join(BASE_DIR, "alphasignal.db")

    # Security (JWT)
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-it-in-prod")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 60))
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

    # WebAuthn (Passkeys)
    RP_ID = os.getenv("RP_ID", "localhost")
    RP_NAME = os.getenv("RP_NAME", "AlphaSignal")
    ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

# 实例化单例
settings = Settings()
