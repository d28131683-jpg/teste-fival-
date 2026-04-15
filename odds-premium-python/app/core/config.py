from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='Odds Premium Engine', alias='APP_NAME')
    app_env: Literal['development', 'staging', 'production'] = Field(default='development', alias='APP_ENV')
    app_host: str = Field(default='0.0.0.0', alias='APP_HOST')
    app_port: int = Field(default=8000, alias='APP_PORT')
    app_log_level: str = Field(default='INFO', alias='APP_LOG_LEVEL')
    internal_cron_token: str = Field(default='change-me', alias='INTERNAL_CRON_TOKEN')

    openrouter_api_key: str = Field(default='', alias='OPENROUTER_API_KEY')
    openrouter_model: str = Field(default='openai/gpt-4.1-mini', alias='OPENROUTER_MODEL')
    openrouter_base_url: str = Field(default='https://openrouter.ai/api/v1', alias='OPENROUTER_BASE_URL')

    supabase_url: str = Field(default='', alias='SUPABASE_URL')
    supabase_anon_key: str = Field(default='', alias='SUPABASE_ANON_KEY')
    supabase_service_role_key: str = Field(default='', alias='SUPABASE_SERVICE_ROLE_KEY')
    supabase_storage_schema: str = Field(default='public', alias='SUPABASE_STORAGE_SCHEMA')

    odds_api_key: str = Field(default='', alias='ODDS_API_KEY')
    odds_api_base_url: str = Field(default='https://api.the-odds-api.com', alias='ODDS_API_BASE_URL')
    odds_api_regions: str = Field(default='eu', alias='ODDS_API_REGIONS')
    odds_api_markets: str = Field(default='h2h,totals,player_points', alias='ODDS_API_MARKETS')
    odds_api_bookmakers: str = Field(default='', alias='ODDS_API_BOOKMAKERS')

    sports_data_api_key: str = Field(default='', alias='SPORTS_DATA_API_KEY')
    sports_data_api_base_url: str = Field(default='https://example-sports-data-provider.com/api', alias='SPORTS_DATA_API_BASE_URL')
    sports_data_timeout_seconds: int = Field(default=20, alias='SPORTS_DATA_TIMEOUT_SECONDS')

    pipeline_interval_seconds: int = Field(default=30, alias='PIPELINE_INTERVAL_SECONDS')
    pipeline_batch_size: int = Field(default=50, alias='PIPELINE_BATCH_SIZE')
    enable_local_scheduler: bool = Field(default=True, alias='ENABLE_LOCAL_SCHEDULER')
    request_timeout_seconds: int = Field(default=20, alias='REQUEST_TIMEOUT_SECONDS')
    http_max_retries: int = Field(default=3, alias='HTTP_MAX_RETRIES')
    lock_ttl_seconds: int = Field(default=25, alias='LOCK_TTL_SECONDS')

    @property
    def odds_regions_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_regions.split(',') if item.strip()]

    @property
    def odds_markets_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_markets.split(',') if item.strip()]

    @property
    def odds_bookmakers_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_bookmakers.split(',') if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
