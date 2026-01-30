"""
Testes para os scrapers
"""
import pytest
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle
from app.scrapers.scraper_manager import ScraperManager


class TestScrapedArticle:
    """Testes para a classe ScrapedArticle"""

    def test_create_article(self):
        """Testa criação de artigo"""
        article = ScrapedArticle(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            source_key="test"
        )
        assert article.url == "https://example.com/article"
        assert article.title == "Test Article"
        assert article.content == "Test content"
        assert article.source_key == "test"

    def test_article_defaults(self):
        """Testa valores padrão do artigo"""
        article = ScrapedArticle(
            url="https://example.com",
            title="Test"
        )
        assert article.content == ""
        assert article.author is None
        assert article.language == "en"


class TestScraperManager:
    """Testes para o ScraperManager"""

    def test_get_available_sources(self):
        """Testa listagem de fontes disponíveis"""
        manager = ScraperManager()
        sources = manager.get_available_sources()

        assert isinstance(sources, list)
        assert len(sources) > 0

        # Verificar estrutura
        for source in sources:
            assert "key" in source
            assert "name" in source
            assert "url" in source

    def test_statistics(self):
        """Testa estatísticas do manager"""
        manager = ScraperManager()
        stats = manager.get_statistics()

        assert "total_scrapers" in stats
        assert "scrapers_available" in stats
        assert stats["total_scrapers"] > 0


class TestBaseScraper:
    """Testes para funcionalidades do BaseScraper"""

    def test_resolve_url_absolute(self):
        """Testa resolução de URL absoluta"""
        class TestScraper(BaseScraper):
            SOURCE_KEY = "test"
            SOURCE_NAME = "Test"
            BASE_URL = "https://example.com"

            def get_article_urls(self, topic=None):
                return []

            def scrape_article(self, url):
                return None

        scraper = TestScraper()
        resolved = scraper._resolve_url("https://other.com/article")
        assert resolved == "https://other.com/article"

    def test_resolve_url_relative(self):
        """Testa resolução de URL relativa"""
        class TestScraper(BaseScraper):
            SOURCE_KEY = "test"
            SOURCE_NAME = "Test"
            BASE_URL = "https://example.com"

            def get_article_urls(self, topic=None):
                return []

            def scrape_article(self, url):
                return None

        scraper = TestScraper()
        resolved = scraper._resolve_url("/article/123")
        assert resolved == "https://example.com/article/123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
