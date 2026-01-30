"""
Gerenciador de scrapers - orquestra todos os scrapers
"""
from typing import List, Dict, Optional, Type
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings, NEWS_SOURCES
from app.utils.logger import get_logger
from app.utils.cache import global_cache

from .base_scraper import BaseScraper, ScrapedArticle
from .reuters_scraper import ReutersScraper
from .bbc_scraper import BBCScraper, BBCPortugueseScraper
from .apnews_scraper import APNewsScraper
from .dw_scraper import DWScraper
from .aljazeera_scraper import AlJazeeraScraper
from .analysis_scrapers import (
    ForeignAffairsScraper,
    CSISScraper,
    CFRScraper,
    CrisisGroupScraper,
    RANDScraper
)
from .brazil_scrapers import NexoScraper, Poder360Scraper


logger = get_logger("ScraperManager")


def get_active_sources() -> Dict[str, Dict]:
    """
    Retorna fontes ativas do Firestore.
    Fallback para NEWS_SOURCES se Firestore não estiver disponível.
    """
    try:
        from app.db.repositories import SourceConfigRepository
        sources_data = SourceConfigRepository.get_all_sources(include_inactive=False)

        if sources_data:
            return {
                s.get("key") or s.get("id"): s
                for s in sources_data
            }
    except Exception as e:
        logger.warning(f"Não foi possível carregar fontes do Firestore: {e}")

    # Fallback para config estático
    return NEWS_SOURCES


# Mapeamento de chaves para classes de scraper
SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "reuters": ReutersScraper,
    "apnews": APNewsScraper,
    "bbc": BBCScraper,
    "bbc_portuguese": BBCPortugueseScraper,
    "dw": DWScraper,
    "aljazeera": AlJazeeraScraper,
    "foreignaffairs": ForeignAffairsScraper,
    "csis": CSISScraper,
    "cfr": CFRScraper,
    "crisisgroup": CrisisGroupScraper,
    "rand": RANDScraper,
    "nexo": NexoScraper,
    "poder360": Poder360Scraper,
}


class ScraperManager:
    """
    Gerenciador central de scrapers.
    Orquestra a coleta de múltiplas fontes em paralelo.
    """

    def __init__(self, max_workers: int = 5):
        """
        Inicializa o gerenciador.

        Args:
            max_workers: Número máximo de threads para coleta paralela
        """
        self.max_workers = max_workers
        self._scrapers: Dict[str, BaseScraper] = {}
        self._active_sources: Dict[str, Dict] = {}
        self._initialize_scrapers()

    def _initialize_scrapers(self) -> None:
        """Inicializa instâncias de todos os scrapers registrados"""
        # Carregar fontes ativas do Firestore ou fallback
        self._active_sources = get_active_sources()

        for key, scraper_class in SCRAPER_REGISTRY.items():
            # Verificar se a fonte está ativa
            if key in self._active_sources:
                source_info = self._active_sources[key]
                # Para Firestore, is_active já está filtrado
                # Para fallback, verificar reputation_score > 0
                if source_info.get("reputation_score", 0) > 0:
                    try:
                        self._scrapers[key] = scraper_class()
                        logger.debug(f"Scraper inicializado: {key}")
                    except Exception as e:
                        logger.error(f"Erro ao inicializar scraper {key}: {e}")

    def refresh_sources(self) -> None:
        """Recarrega a lista de fontes ativas do Firestore"""
        self._active_sources = get_active_sources()
        self._scrapers.clear()
        self._initialize_scrapers()
        logger.info(f"Fontes recarregadas: {len(self._scrapers)} scrapers ativos")

    def get_available_sources(self) -> List[Dict]:
        """Retorna lista de fontes disponíveis"""
        sources = []
        for key in self._scrapers.keys():
            if key in self._active_sources:
                source_info = self._active_sources[key].copy()
                source_info["key"] = key
                sources.append(source_info)
        return sources

    def scrape_source(
        self,
        source_key: str,
        topic: Optional[str] = None,
        max_articles: int = 10
    ) -> List[ScrapedArticle]:
        """
        Coleta artigos de uma fonte específica.

        Args:
            source_key: Chave da fonte (ex: "reuters")
            topic: Tema opcional para filtrar
            max_articles: Número máximo de artigos

        Returns:
            Lista de artigos coletados
        """
        if source_key not in self._scrapers:
            logger.warning(f"Scraper não encontrado: {source_key}")
            return []

        # Verificar cache
        cache_key = f"scraper:{source_key}:{topic}:{max_articles}"
        cached = global_cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit para {source_key}")
            return cached

        scraper = self._scrapers[source_key]
        articles = scraper.scrape_all(topic=topic, max_articles=max_articles)

        # Armazenar no cache
        if articles:
            global_cache.set(cache_key, articles, ttl=settings.CACHE_TTL_SECONDS)

        return articles

    def scrape_all_sources(
        self,
        topic: Optional[str] = None,
        max_articles_per_source: int = 10,
        source_types: Optional[List[str]] = None,
        regions: Optional[List[str]] = None
    ) -> Dict[str, List[ScrapedArticle]]:
        """
        Coleta artigos de todas as fontes em paralelo.

        Args:
            topic: Tema opcional para filtrar
            max_articles_per_source: Máximo de artigos por fonte
            source_types: Tipos de fonte para filtrar (news, analysis)
            regions: Regiões para filtrar (global, brazil, europe, etc.)

        Returns:
            Dicionário com artigos por fonte
        """
        results: Dict[str, List[ScrapedArticle]] = {}

        # Filtrar fontes
        sources_to_scrape = []
        for key in self._scrapers.keys():
            if key not in self._active_sources:
                continue

            source_info = self._active_sources[key]

            # Filtrar por tipo
            if source_types and source_info.get("type") not in source_types:
                continue

            # Filtrar por região
            if regions and source_info.get("region") not in regions:
                continue

            sources_to_scrape.append(key)

        logger.info(f"Iniciando coleta de {len(sources_to_scrape)} fontes sobre '{topic or 'geral'}'")

        # Executar em paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(
                    self.scrape_source,
                    source_key,
                    topic,
                    max_articles_per_source
                ): source_key
                for source_key in sources_to_scrape
            }

            for future in as_completed(future_to_source):
                source_key = future_to_source[future]
                try:
                    articles = future.result()
                    results[source_key] = articles
                    logger.info(f"[{source_key}] Coletados {len(articles)} artigos")
                except Exception as e:
                    logger.error(f"[{source_key}] Erro na coleta: {e}")
                    results[source_key] = []

        total_articles = sum(len(arts) for arts in results.values())
        logger.info(f"Coleta finalizada: {total_articles} artigos de {len(results)} fontes")

        return results

    def search_topic(
        self,
        topic: str,
        min_sources: int = 3,
        max_articles_per_source: int = 5
    ) -> List[ScrapedArticle]:
        """
        Busca um tema em múltiplas fontes garantindo diversidade.

        Args:
            topic: Tema para buscar
            min_sources: Número mínimo de fontes
            max_articles_per_source: Máximo de artigos por fonte

        Returns:
            Lista de artigos de múltiplas fontes
        """
        all_articles: List[ScrapedArticle] = []
        sources_with_results = 0

        results = self.scrape_all_sources(
            topic=topic,
            max_articles_per_source=max_articles_per_source
        )

        for source_key, articles in results.items():
            if articles:
                sources_with_results += 1
                all_articles.extend(articles)

        if sources_with_results < min_sources:
            logger.warning(
                f"Apenas {sources_with_results} fontes encontradas para '{topic}'. "
                f"Mínimo requerido: {min_sources}"
            )

        # Ordenar por data de publicação (mais recentes primeiro)
        all_articles.sort(
            key=lambda x: x.published_at or datetime.min,
            reverse=True
        )

        return all_articles

    def get_statistics(self) -> Dict:
        """Retorna estatísticas dos scrapers"""
        return {
            "total_scrapers": len(self._scrapers),
            "scrapers_available": list(self._scrapers.keys()),
            "cache_stats": global_cache.stats()
        }
