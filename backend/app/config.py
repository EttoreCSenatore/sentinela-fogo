from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTINELA_", extra="ignore")

    database_url: str = "sqlite:///./sentinela.db"
    timezone: str = "America/Sao_Paulo"

    # MQTT
    mqtt_enabled: bool = True
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic: str = "sentinela/v1/nodes/+/telemetry"

    # INPE BDQueimadas hotspots
    inpe_enabled: bool = True
    inpe_base_url: str = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/"
    inpe_poll_seconds: int = 600
    # Rough Brazil bounding box (lat_min, lat_max, lon_min, lon_max); the feed covers South America.
    bbox: tuple[float, float, float, float] = (-34.0, 5.5, -74.0, -34.0)

    # Pilot sites (virtual stations) and weather
    sites_file: str = "config/sites.json"
    recipients_file: str = "config/recipients.json"
    weather_enabled: bool = True
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_poll_seconds: int = 3600
    weather_backfill_days: int = 30

    # Detection
    hotspot_radius_km: float = 5.0
    hotspot_window_hours: int = 3
    detection_threshold: float = 0.6
    alert_cooldown_minutes: int = 30
    hotspot_alert_cooldown_minutes: int = 180

    # Alerts
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None  # fallback recipient when recipients_file is absent
    telegram_bot_enabled: bool = True  # answer /start, /status, /ajuda (needs telegram_bot_token)
    # WhatsApp Cloud API (Meta). Business-initiated messages need an approved template in production.
    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    # SMS via Twilio
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None


settings = Settings()
