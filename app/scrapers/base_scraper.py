"""
Classe base abstrata para scrapers de notícias
"""
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings
from app.utils.logger import LoggerMixin
from app.utils.text_cleaner import TextCleaner


@dataclass
class ScrapedArticle:
    """Estrutura de dados para artigo coletado"""
    url: str
    title: str
    content: str = ""
    raw_content: str = ""
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    language: str = "en"
    source_key: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC, LoggerMixin):
    """
    Classe base abstrata para todos os scrapers.
    Implementa funcionalidades comuns como:
    - Requests com retry e headers rotativos
    - Rate limiting
    - Normalização de conteúdo
    - Tratamento de erros
    """

    # Configurações padrão (podem ser sobrescritas)
    SOURCE_KEY: str = ""
    SOURCE_NAME: str = ""
    BASE_URL: str = ""
    LANGUAGE: str = "en"

    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self._setup_session()

    def _setup_session(self) -> None:
        """Configura a sessão com headers padrão"""
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def _get_random_headers(self) -> Dict[str, str]:
        """Retorna headers com User-Agent aleatório"""
        return {
            "User-Agent": self.ua.random
        }

    def _respect_rate_limit(self) -> None:
        """Aplica delay aleatório entre requests"""
        delay = random.uniform(
            settings.SCRAPER_DELAY_MIN,
            settings.SCRAPER_DELAY_MAX
        )
        time.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Faz request para uma URL com retry automático.

        Args:
            url: URL para buscar

        Returns:
            Conteúdo HTML ou None se falhar
        """
        try:
            self._respect_rate_limit()

            response = self.session.get(
                url,
                headers=self._get_random_headers(),
                timeout=settings.SCRAPER_TIMEOUT
            )
            response.raise_for_status()

            return response.text

        except requests.RequestException as e:
            self.logger.error(f"Erro ao buscar {url}: {e}")
            raise

    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Converte HTML em BeautifulSoup"""
        return BeautifulSoup(html_content, "lxml")

    def _resolve_url(self, url: str) -> str:
        """Resolve URLs relativas para absolutas"""
        if url.startswith("http"):
            return url
        return urljoin(self.BASE_URL, url)

    def _clean_content(self, html_content: str) -> str:
        """Limpa e extrai texto do conteúdo HTML"""
        return TextCleaner.extract_article_content(html_content)

    def _extract_title(self, html_content: str) -> Optional[str]:
        """Extrai título do artigo"""
        return TextCleaner.extract_title(html_content)

    def _extract_metadata(self, html_content: str) -> Dict[str, Any]:
        """Extrai metadados do artigo"""
        return TextCleaner.extract_metadata(html_content)

    @abstractmethod
    def get_article_urls(self, topic: Optional[str] = None) -> List[str]:
        """
        Obtém lista de URLs de artigos.

        Args:
            topic: Tema opcional para filtrar

        Returns:
            Lista de URLs de artigos
        """
        pass

    @abstractmethod
    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """
        Faz scraping de um artigo específico.

        Args:
            url: URL do artigo

        Returns:
            ScrapedArticle ou None se falhar
        """
        pass

    def scrape_all(
        self,
        topic: Optional[str] = None,
        max_articles: Optional[int] = None
    ) -> List[ScrapedArticle]:
        """
        Coleta todos os artigos disponíveis.

        Args:
            topic: Tema opcional para filtrar
            max_articles: Número máximo de artigos

        Returns:
            Lista de artigos coletados
        """
        max_articles = max_articles or settings.MAX_ARTICLES_PER_SOURCE
        articles = []

        try:
            urls = self.get_article_urls(topic)
            self.logger.info(f"[{self.SOURCE_NAME}] Encontrados {len(urls)} artigos")

            for url in urls[:max_articles]:
                try:
                    article = self.scrape_article(url)
                    if article:
                        article.source_key = self.SOURCE_KEY
                        articles.append(article)
                        self.logger.debug(f"Coletado: {article.title[:50]}...")
                except Exception as e:
                    self.logger.error(f"Erro ao coletar {url}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"[{self.SOURCE_NAME}] Erro geral: {e}")

        self.logger.info(f"[{self.SOURCE_NAME}] Total coletado: {len(articles)} artigos")
        return articles

    def search(self, query: str, max_results: int = 10) -> List[ScrapedArticle]:
        """
        Busca artigos por termo.

        Args:
            query: Termo de busca
            max_results: Número máximo de resultados

        Returns:
            Lista de artigos encontrados
        """
        return self.scrape_all(topic=query, max_articles=max_results)
