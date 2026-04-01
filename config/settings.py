"""
Configuration Settings
Environment-based configuration using pydantic
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Main application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )

    # Application
    APP_NAME: str = "Crypto Trading Signal Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENV: str = os.getenv("ENV", "development")

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    WORKERS: int = 4

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/crypto_bot"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Cache (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes

    # API Keys & Credentials
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_TESTNET: bool = True

    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, local
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-opus-20240229"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    TRANSFORMER_MODEL_PATH: str = "models/crypto-transformer"

    # JWT Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Trading Configuration
    TIMEFRAMES: List[str] = ["5m", "15m", "1h", "4h", "1d"]
    DEFAULT_TIMEFRAME: str = "15m"
    SUPPORTED_CRYPTOS: List[str] = [
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "POL", "DOGE", "LINK"
    ]

    # Risk Management
    MAX_POSITION_SIZE: float = 0.05  # 5% of portfolio
    MIN_POSITION_SIZE: float = 0.01  # 1% of portfolio
    MAX_OPEN_POSITIONS: int = 5
    RISK_PER_TRADE_PERCENT: float = 1.0  # 1% portfolio risk per trade

    # Fallback static TP/SL (only used when ATR is unavailable)
    DEFAULT_STOP_LOSS_PERCENT: float = 2.0
    DEFAULT_TP_PERCENT: float = 5.0

    # === ADAPTIVE ATR-BASED TP/SL MULTIPLIERS ===
    # Trending markets: wider targets, room to run
    ATR_TP_MULTIPLIER_TRENDING: float = 3.0
    ATR_SL_MULTIPLIER_TRENDING: float = 1.5
    # Ranging markets: tighter targets, mean-reversion style
    ATR_TP_MULTIPLIER_RANGING: float = 1.8
    ATR_SL_MULTIPLIER_RANGING: float = 1.0
    # Volatile/choppy markets: very tight SL, moderate TP
    ATR_TP_MULTIPLIER_VOLATILE: float = 2.0
    ATR_SL_MULTIPLIER_VOLATILE: float = 0.8

    # === SIGNAL QUALITY CONTROLS ===
    MIN_RISK_REWARD_RATIO: float = 1.5       # Reject signals with R:R < 1.5
    MIN_CONFLUENCE_STRATEGIES: int = 2        # Minimum strategies that must agree
    ADX_TREND_THRESHOLD: float = 25.0        # ADX >= this = trending
    ADX_RANGING_THRESHOLD: float = 20.0      # ADX < this = ranging

    # === MULTI-TIMEFRAME ===
    MTF_PRIMARY_TIMEFRAME: str = "4h"        # Trend direction
    MTF_SECONDARY_TIMEFRAME: str = "1h"      # Trend confirmation
    MTF_ENTRY_TIMEFRAME: str = "15m"         # Entry timing

    # Signal Configuration
    MIN_SIGNAL_CONFIDENCE: float = 0.60
    ENABLE_LLM_ANALYSIS: bool = True
    LLM_ANALYSIS_THRESHOLD: float = 0.50
    SCAN_INTERVAL: int = 60  # seconds

    # Postgres is used by legacy parts of this repo (SQLAlchemy migrations, trade execution history).
    # Planitt mode can run without it.
    ENABLE_POSTGRES_DB_INIT: bool = os.getenv("ENABLE_POSTGRES_DB_INIT", "true").lower() == "true"

    # --------------------------------------------------------------------
    # Planitt (recommended signals) - FastAPI processor -> NestJS backend
    # --------------------------------------------------------------------
    # NestJS backend public base URL (used by clients, if needed) or internal
    # base URL for service-to-service communication.
    PLANITT_BACKEND_BASE_URL: str = os.getenv("PLANITT_BACKEND_BASE_URL", "http://localhost:3000")
    # API key used by FastAPI processor to authenticate with NestJS internal endpoints.
    PLANITT_BACKEND_INTERNAL_API_KEY: str = os.getenv("PLANITT_BACKEND_INTERNAL_API_KEY", "change-me")
    # API key used to protect Planitt processor endpoints on FastAPI (internal only).
    PLANITT_PROCESSOR_INTERNAL_API_KEY: str = os.getenv("PLANITT_PROCESSOR_INTERNAL_API_KEY", "change-me")
    # Only accept LLM decisions above this threshold.
    PLANITT_MIN_CONFIDENCE: int = int(os.getenv("PLANITT_MIN_CONFIDENCE", "70"))
    # Comma separated list of scan timeframes, ex: "5m,15m,1h"
    PLANITT_SCAN_TIMEFRAMES_RAW: str = os.getenv("PLANITT_SCAN_TIMEFRAMES", "")
    # Tunables for confluence pre-gates (helps reduce over-filtering in live markets)
    PLANITT_MIN_CONFLUENCE_HITS: int = int(os.getenv("PLANITT_MIN_CONFLUENCE_HITS", "2"))
    PLANITT_VOLUME_MULTIPLIER: float = float(os.getenv("PLANITT_VOLUME_MULTIPLIER", "1.2"))
    PLANITT_TOUCH_TOLERANCE_PCT: float = float(os.getenv("PLANITT_TOUCH_TOLERANCE_PCT", "0.01"))

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"

    # Monitoring
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 9090
    ENABLE_SENTRY: bool = False
    SENTRY_DSN: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export singleton
settings = get_settings()
