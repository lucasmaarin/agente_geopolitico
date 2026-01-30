"""
Módulo de scrapers para coleta de notícias geopolíticas
"""
from .base_scraper import BaseScraper
from .scraper_manager import ScraperManager

__all__ = ["BaseScraper", "ScraperManager"]
