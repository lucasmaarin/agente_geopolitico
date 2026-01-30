"""
Testes para os pipelines
"""
import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipelines.extractor import SemanticExtractor, ExtractedData
from app.pipelines.cross_reference import CrossReferenceEngine, CrossReferenceResult
from app.scrapers.base_scraper import ScrapedArticle


class TestSemanticExtractor:
    """Testes para o extrator semântico"""

    def setup_method(self):
        """Setup para cada teste"""
        self.extractor = SemanticExtractor()

    def test_extract_countries(self):
        """Testa extração de países"""
        article = ScrapedArticle(
            url="https://example.com",
            title="US and China discuss trade",
            content="The United States and China met in Beijing to discuss trade relations. Russia also commented on the meeting.",
            source_key="test"
        )

        extracted = self.extractor.extract(article)

        assert "United States" in extracted.countries
        assert "China" in extracted.countries
        assert "Russia" in extracted.countries

    def test_extract_topics(self):
        """Testa identificação de tópicos"""
        article = ScrapedArticle(
            url="https://example.com",
            title="Military conflict escalates",
            content="The military conflict has escalated with new sanctions being imposed. Diplomacy efforts continue.",
            source_key="test"
        )

        extracted = self.extractor.extract(article)

        assert "military" in extracted.topics or "conflict" in extracted.topics
        assert "sanctions" in extracted.topics

    def test_extract_dates(self):
        """Testa extração de datas"""
        article = ScrapedArticle(
            url="https://example.com",
            title="Test",
            content="The meeting on January 15, 2024 was followed by another on 20/02/2024.",
            source_key="test"
        )

        extracted = self.extractor.extract(article)

        assert len(extracted.dates) >= 1

    def test_sentiment_analysis(self):
        """Testa análise de sentimento básica"""
        article = ScrapedArticle(
            url="https://example.com",
            title="Peace agreement reached",
            content="A peace agreement was reached after successful cooperation and progress in negotiations.",
            source_key="test"
        )

        extracted = self.extractor.extract(article)

        assert extracted.sentiment_keywords["positive"] > 0


class TestCrossReferenceEngine:
    """Testes para o motor de cruzamento"""

    def setup_method(self):
        """Setup para cada teste"""
        self.engine = CrossReferenceEngine()
        self.extractor = SemanticExtractor()

    def test_find_common_entities(self):
        """Testa identificação de entidades comuns"""
        entities1 = ["USA", "China", "Russia"]
        entities2 = ["China", "Russia", "Germany"]
        entities3 = ["China", "Japan"]

        common = self.engine._find_common_entities([entities1, entities2, entities3])

        assert "China" in common

    def test_convergence_score(self):
        """Testa cálculo de score de convergência"""
        # Criar dados extraídos simulados
        articles = [
            ScrapedArticle(
                url="https://source1.com",
                title="US China trade talks",
                content="The United States and China discussed trade.",
                source_key="reuters"
            ),
            ScrapedArticle(
                url="https://source2.com",
                title="Trade discussions between US and China",
                content="China and the US met for trade negotiations.",
                source_key="apnews"
            ),
            ScrapedArticle(
                url="https://source3.com",
                title="US-China relations",
                content="Trade talks between United States and China continue.",
                source_key="bbc"
            )
        ]

        extracted_data = [self.extractor.extract(a) for a in articles]
        result = self.engine.analyze(extracted_data)

        assert result.sources_count == 3
        assert "United States" in result.common_countries or "China" in result.common_countries


class TestConfidenceScoring:
    """Testes para o sistema de scoring"""

    def test_quick_score(self):
        """Testa cálculo rápido de score"""
        from app.scoring.confidence_calculator import ConfidenceCalculator

        calculator = ConfidenceCalculator()

        # Com tier 1
        score_with_tier1 = calculator.quick_score(3, has_tier1=True)
        assert score_with_tier1 > 50

        # Sem tier 1
        score_without_tier1 = calculator.quick_score(3, has_tier1=False)
        assert score_with_tier1 > score_without_tier1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
