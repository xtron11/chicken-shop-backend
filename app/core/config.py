from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "Chicken Shop API"
    DEBUG: bool = False

    # --- Database ---
    # пример: postgresql+asyncpg://user:password@localhost:5432/chicken_shop
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chicken_shop"

    # --- Admin panel auth ---
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_me"
    ADMIN_SECRET_KEY: str = "change_me_too_please"

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- Payment provider (заглушка, подставить реальные ключи провайдера) ---
    PAYMENT_PROVIDER: str = "dummy"  # kaspi | cloudpayments | dummy
    PAYMENT_API_KEY: str = ""
    PAYMENT_API_SECRET: str = ""
    PAYMENT_WEBHOOK_SECRET: str = ""

    # --- Business rules ---
    MIN_HOURS_BEFORE_DELIVERY: int = 2   # нельзя заказать доставку раньше, чем через N часов
    WORK_HOUR_FROM: int = 9
    WORK_HOUR_TO: int = 21
    DELIVERY_SLOT_STEP_MINUTES: int = 60
    PENDING_ORDER_TTL_MINUTES: int = 20  # через сколько отменять неоплаченный заказ


settings = Settings()
