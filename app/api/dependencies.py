"""
Dependências para injeção na API
"""
from typing import Generator, Optional
from functools import lru_cache

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import settings
from app.db.database import get_db, get_firestore_client
from app.scrapers.scraper_manager import ScraperManager
from app.pipelines.extractor import SemanticExtractor
from app.pipelines.analyzer import OpenAIAnalyzer
from app.pipelines.cross_reference import CrossReferenceEngine
from app.pipelines.report_generator import ReportGenerator
from app.scoring.confidence_calculator import ConfidenceCalculator
from app.scoring.source_reputation import SourceReputationManager
from app.utils.logger import get_logger


logger = get_logger("dependencies")


@lru_cache()
def get_scraper_manager() -> ScraperManager:
    """
    Retorna instância singleton do ScraperManager.
    Cached para evitar reinicialização a cada request.
    """
    logger.info("Inicializando ScraperManager...")
    return ScraperManager()


@lru_cache()
def get_extractor() -> SemanticExtractor:
    """Retorna instância singleton do extrator semântico"""
    return SemanticExtractor()


@lru_cache()
def get_analyzer() -> Optional[OpenAIAnalyzer]:
    """
    Retorna instância do analisador OpenAI.
    Retorna None se API key não estiver configurada.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY não configurada")
        return None

    return OpenAIAnalyzer()


@lru_cache()
def get_cross_reference_engine() -> CrossReferenceEngine:
    """Retorna instância do motor de cruzamento"""
    return CrossReferenceEngine()


@lru_cache()
def get_report_generator() -> ReportGenerator:
    """Retorna instância do gerador de relatórios"""
    return ReportGenerator()


@lru_cache()
def get_confidence_calculator() -> ConfidenceCalculator:
    """Retorna instância da calculadora de confiabilidade"""
    return ConfidenceCalculator()


@lru_cache()
def get_reputation_manager() -> SourceReputationManager:
    """Retorna instância do gerenciador de reputação"""
    return SourceReputationManager()


class GeopoliticalService:
    """
    Serviço que orquestra todo o pipeline de análise geopolítica.
    Facilita a injeção de dependências na API.
    """

    def __init__(
        self,
        scraper_manager: ScraperManager,
        extractor: SemanticExtractor,
        analyzer: Optional[OpenAIAnalyzer],
        cross_reference: CrossReferenceEngine,
        report_generator: ReportGenerator,
        confidence_calculator: ConfidenceCalculator
    ):
        self.scraper_manager = scraper_manager
        self.extractor = extractor
        self.analyzer = analyzer
        self.cross_reference = cross_reference
        self.report_generator = report_generator
        self.confidence_calculator = confidence_calculator
        self.logger = get_logger("GeopoliticalService")

    def search_topic(self, topic: str, max_per_source: int = 5) -> dict:
        """
        Busca artigos sobre um tema em múltiplas fontes.

        Args:
            topic: Tema para buscar
            max_per_source: Máximo de artigos por fonte

        Returns:
            Dicionário com artigos por fonte
        """
        return self.scraper_manager.scrape_all_sources(
            topic=topic,
            max_articles_per_source=max_per_source
        )

    def generate_report(self, topic: str, min_sources: int = 3) -> dict:
        """
        Gera relatório geopolítico completo.

        Args:
            topic: Tema do relatório
            min_sources: Mínimo de fontes requeridas

        Returns:
            Relatório completo
        """
        from config import NEWS_SOURCES

        # 1. Coletar artigos
        self.logger.info(f"Coletando artigos sobre: {topic}")
        articles_by_source = self.search_topic(topic, max_per_source=5)

        # Converter para lista flat
        all_articles = []
        for source_key, articles in articles_by_source.items():
            for article in articles:
                all_articles.append({
                    "source": source_key,
                    "source_name": NEWS_SOURCES.get(source_key, {}).get("name", source_key),
                    "title": article.title,
                    "content": article.content,
                    "url": article.url,
                    "published_at": article.published_at,
                    "language": article.language
                })

        if len(all_articles) < min_sources:
            return {
                "error": f"Apenas {len(all_articles)} artigos encontrados. Mínimo: {min_sources}",
                "articles_found": len(all_articles)
            }

        # 2. Extrair informações semânticas
        self.logger.info("Extraindo informações semânticas...")
        scraped_articles = []
        from app.scrapers.base_scraper import ScrapedArticle
        for a in all_articles:
            scraped_articles.append(ScrapedArticle(
                url=a["url"],
                title=a["title"],
                content=a["content"],
                source_key=a["source"],
                language=a.get("language", "en")
            ))

        extracted_data = self.extractor.extract_batch(scraped_articles)

        # 3. Cruzar informações
        self.logger.info("Cruzando informações entre fontes...")
        cross_ref_result = self.cross_reference.analyze(extracted_data)

        # 4. Análise via OpenAI (se disponível)
        analysis_results = {}
        if self.analyzer:
            self.logger.info("Executando análise via OpenAI...")
            analysis_results = self.analyzer.full_analysis(all_articles)
        else:
            self.logger.warning("Análise OpenAI não disponível (API key não configurada)")

        # 5. Calcular score de confiabilidade
        self.logger.info("Calculando score de confiabilidade...")
        bias_analysis = None
        if "bias_detection" in analysis_results and analysis_results["bias_detection"].success:
            bias_analysis = analysis_results["bias_detection"].content

        confidence_result = self.confidence_calculator.calculate(
            extracted_data,
            cross_ref_result,
            bias_analysis
        )

        # 6. Gerar relatório
        self.logger.info("Gerando relatório final...")
        sources_info = [
            {
                "key": a["source"],
                "name": a["source_name"],
                "url": a["url"]
            }
            for a in all_articles
        ]

        report = self.report_generator.generate(
            topic=topic,
            analysis_results=analysis_results,
            cross_reference=cross_ref_result,
            sources=sources_info
        )

        # Adicionar score de confiabilidade ao relatório
        report.confidence_score = confidence_result.total_score
        report.confidence_breakdown = confidence_result.breakdown

        # Formatar relatório
        formatted = self.report_generator.format_report(report)

        return {
            "report": report,
            "formatted": formatted,
            "confidence": confidence_result,
            "cross_reference": cross_ref_result,
            "articles_used": len(all_articles)
        }


def get_geopolitical_service() -> GeopoliticalService:
    """Factory function para criar o serviço geopolítico"""
    return GeopoliticalService(
        scraper_manager=get_scraper_manager(),
        extractor=get_extractor(),
        analyzer=get_analyzer(),
        cross_reference=get_cross_reference_engine(),
        report_generator=get_report_generator(),
        confidence_calculator=get_confidence_calculator()
    )
