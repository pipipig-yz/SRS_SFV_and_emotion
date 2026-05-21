from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 3000
    data_backend: str = "mock"
    database_url: str = ""

    deepseek_api_key: str = ""
    deepseek_url: str = "https://api.deepseek.com/v1/chat/completions"

    volc_asr_api_key: str = ""
    volc_asr_uid: str = "srs-chatbot"
    volc_asr_flash_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
    volc_asr_submit_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
    volc_asr_query_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
    volc_asr_flash_resource_id: str = "volc.bigasr.auc_turbo"
    volc_asr_resource_id: str = "volc.seedasr.auc"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
