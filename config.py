"""
Configurações centralizadas do Agente de Inteligência Geopolítica
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Diretórios
    BASE_DIR: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # API
    API_TITLE: str = "Agente de Inteligência Geopolítica"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(default=4000, env="OPENAI_MAX_TOKENS")
    OPENAI_TEMPERATURE: float = Field(default=0.3, env="OPENAI_TEMPERATURE")

    # Firebase/Firestore
    FIREBASE_CREDENTIALS_PATH: str = Field(
        default="./firebase-credentials.json",
        env="FIREBASE_CREDENTIALS_PATH"
    )
    FIREBASE_PROJECT_ID: str = Field(
        default="",
        env="FIREBASE_PROJECT_ID"
    )
    FIRESTORE_COLLECTION_PREFIX: str = Field(
        default="geopolitica",
        env="FIRESTORE_COLLECTION_PREFIX"
    )

    # Scraping
    SCRAPER_TIMEOUT: int = Field(default=30, env="SCRAPER_TIMEOUT")
    SCRAPER_RETRY_ATTEMPTS: int = Field(default=3, env="SCRAPER_RETRY_ATTEMPTS")
    SCRAPER_DELAY_MIN: float = Field(default=1.0, env="SCRAPER_DELAY_MIN")
    SCRAPER_DELAY_MAX: float = Field(default=3.0, env="SCRAPER_DELAY_MAX")

    # Cache
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hora
    CACHE_MAX_SIZE: int = Field(default=1000, env="CACHE_MAX_SIZE")

    # Análise
    MIN_SOURCES_FOR_REPORT: int = Field(default=3, env="MIN_SOURCES_FOR_REPORT")
    MAX_ARTICLES_PER_SOURCE: int = Field(default=10, env="MAX_ARTICLES_PER_SOURCE")

    # Scheduler
    SCHEDULER_INTERVAL_HOURS: int = Field(default=6, env="SCHEDULER_INTERVAL_HOURS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Fontes de notícias confiáveis
NEWS_SOURCES = {
    # Notícias internacionais (fatos brutos)
    "reuters": {
        "name": "Reuters",
        "url": "https://www.reuters.com",
        "type": "news",
        "reputation_score": 95,
        "language": "en",
        "region": "global"
    },
    "apnews": {
        "name": "AP News",
        "url": "https://www.apnews.com",
        "type": "news",
        "reputation_score": 95,
        "language": "en",
        "region": "global"
    },
    "bbc": {
        "name": "BBC World",
        "url": "https://www.bbc.com/news/world",
        "type": "news",
        "reputation_score": 90,
        "language": "en",
        "region": "global"
    },
    "dw": {
        "name": "Deutsche Welle",
        "url": "https://www.dw.com",
        "type": "news",
        "reputation_score": 88,
        "language": "en",
        "region": "europe"
    },
    "aljazeera": {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com",
        "type": "news",
        "reputation_score": 80,
        "language": "en",
        "region": "middle_east"
    },

    # Análise geopolítica profunda
    "foreignaffairs": {
        "name": "Foreign Affairs",
        "url": "https://www.foreignaffairs.com",
        "type": "analysis",
        "reputation_score": 92,
        "language": "en",
        "region": "global"
    },
    "csis": {
        "name": "CSIS",
        "url": "https://www.csis.org",
        "type": "analysis",
        "reputation_score": 90,
        "language": "en",
        "region": "global"
    },
    "cfr": {
        "name": "Council on Foreign Relations",
        "url": "https://www.cfr.org",
        "type": "analysis",
        "reputation_score": 90,
        "language": "en",
        "region": "global"
    },
    "crisisgroup": {
        "name": "Crisis Group",
        "url": "https://www.crisisgroup.org",
        "type": "analysis",
        "reputation_score": 88,
        "language": "en",
        "region": "global"
    },
    "rand": {
        "name": "RAND Corporation",
        "url": "https://www.rand.org",
        "type": "analysis",
        "reputation_score": 88,
        "language": "en",
        "region": "global"
    },

    # Fontes brasileiras
    "nexo": {
        "name": "Nexo Jornal",
        "url": "https://www.nexojornal.com.br",
        "type": "news",
        "reputation_score": 85,
        "language": "pt-br",
        "region": "brazil"
    },
    "bbc_portuguese": {
        "name": "BBC Brasil",
        "url": "https://www.bbc.com/portuguese",
        "type": "news",
        "reputation_score": 88,
        "language": "pt-br",
        "region": "brazil"
    },
    "poder360": {
        "name": "Poder360",
        "url": "https://www.poder360.com.br",
        "type": "news",
        "reputation_score": 82,
        "language": "pt-br",
        "region": "brazil"
    }
}

# Temas geopolíticos para monitoramento
GEOPOLITICAL_TOPICS = [
    "war",
    "conflict",
    "sanctions",
    "diplomacy",
    "trade",
    "military",
    "nuclear",
    "climate",
    "elections",
    "economy",
    "energy",
    "migration",
    "terrorism",
    "cybersecurity",
    "alliance",
    "treaty"
]

# Países prioritários para análise
PRIORITY_COUNTRIES = [
    "United States", "China", "Russia", "Brazil",
    "Ukraine", "Israel", "Iran", "North Korea",
    "India", "European Union", "United Kingdom",
    "Germany", "France", "Japan", "Saudi Arabia"
]

# Instância global de configurações
settings = Settings()

# Criar diretórios necessários
settings.DATA_DIR.mkdir(exist_ok=True)
settings.LOGS_DIR.mkdir(exist_ok=True)
