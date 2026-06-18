from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    max_pending_per_user: int = 3
    question_max_length: int = 280
    config_db_url: str = ""


settings = Settings()
