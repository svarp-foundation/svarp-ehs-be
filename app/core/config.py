from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_DIR: str = ""

    @property
    def MASTER_DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DATABASE_DIR}/master.db"

    def get_company_db_path(self, company_id: int) -> str:
        return f"{self.DATABASE_DIR}/company_{company_id}.db"

    class Config:
        env_file = ".env"

settings = Settings()
