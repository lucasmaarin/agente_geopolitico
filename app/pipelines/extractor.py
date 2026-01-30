"""
Extrator semântico - extrai entidades e informações estruturadas dos artigos
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import PRIORITY_COUNTRIES, GEOPOLITICAL_TOPICS
from app.utils.logger import LoggerMixin
from app.scrapers.base_scraper import ScrapedArticle


@dataclass
class ExtractedData:
    """Dados extraídos de um artigo"""
    article_url: str
    source_key: str
    title: str

    # Entidades extraídas
    countries: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    # Fatos e afirmações
    key_facts: List[str] = field(default_factory=list)
    quotes: List[Dict[str, str]] = field(default_factory=list)
    statistics: List[Dict[str, Any]] = field(default_factory=list)

    # Metadados
    language: str = "en"
    word_count: int = 0
    sentiment_keywords: Dict[str, int] = field(default_factory=dict)


class SemanticExtractor(LoggerMixin):
    """
    Extrai informações semânticas estruturadas dos artigos coletados.
    Identifica países, atores, organizações, datas e tópicos.
    """

    # Padrões de países (expandido)
    COUNTRY_PATTERNS = {
        # Grandes potências
        "United States": ["United States", "USA", "U.S.", "US", "America", "American", "Washington"],
        "China": ["China", "Chinese", "Beijing", "PRC"],
        "Russia": ["Russia", "Russian", "Moscow", "Kremlin", "Putin"],
        "European Union": ["European Union", "EU", "Brussels", "European"],

        # Europa
        "United Kingdom": ["United Kingdom", "UK", "Britain", "British", "London", "England"],
        "Germany": ["Germany", "German", "Berlin", "Scholz"],
        "France": ["France", "French", "Paris", "Macron"],
        "Italy": ["Italy", "Italian", "Rome"],
        "Spain": ["Spain", "Spanish", "Madrid"],
        "Poland": ["Poland", "Polish", "Warsaw"],
        "Ukraine": ["Ukraine", "Ukrainian", "Kyiv", "Kiev", "Zelensky"],

        # Oriente Médio
        "Israel": ["Israel", "Israeli", "Tel Aviv", "Jerusalem", "Netanyahu"],
        "Iran": ["Iran", "Iranian", "Tehran"],
        "Saudi Arabia": ["Saudi Arabia", "Saudi", "Riyadh"],
        "Turkey": ["Turkey", "Turkish", "Ankara", "Erdogan"],
        "Syria": ["Syria", "Syrian", "Damascus"],
        "Iraq": ["Iraq", "Iraqi", "Baghdad"],

        # Ásia
        "Japan": ["Japan", "Japanese", "Tokyo"],
        "South Korea": ["South Korea", "Korean", "Seoul"],
        "North Korea": ["North Korea", "DPRK", "Pyongyang", "Kim Jong"],
        "India": ["India", "Indian", "New Delhi", "Modi"],
        "Pakistan": ["Pakistan", "Pakistani", "Islamabad"],
        "Taiwan": ["Taiwan", "Taiwanese", "Taipei"],

        # América Latina
        "Brazil": ["Brazil", "Brazilian", "Brasília", "Brasilia", "Brasil", "Lula"],
        "Argentina": ["Argentina", "Argentine", "Buenos Aires"],
        "Mexico": ["Mexico", "Mexican", "Mexico City"],
        "Venezuela": ["Venezuela", "Venezuelan", "Caracas", "Maduro"],
        "Colombia": ["Colombia", "Colombian", "Bogotá"],
        "Chile": ["Chile", "Chilean", "Santiago"],

        # África
        "South Africa": ["South Africa", "South African", "Pretoria"],
        "Egypt": ["Egypt", "Egyptian", "Cairo"],
        "Nigeria": ["Nigeria", "Nigerian", "Abuja"],

        # Outros
        "Australia": ["Australia", "Australian", "Canberra"],
        "Canada": ["Canada", "Canadian", "Ottawa"],
    }

    # Organizações internacionais
    ORGANIZATIONS = [
        "United Nations", "UN", "NATO", "WHO", "WTO", "IMF",
        "World Bank", "G7", "G20", "BRICS", "OPEC", "ASEAN",
        "African Union", "OAS", "Arab League", "MERCOSUR",
        "European Commission", "Security Council", "General Assembly"
    ]

    # Palavras-chave de sentimento
    POSITIVE_KEYWORDS = [
        "agreement", "peace", "cooperation", "deal", "success",
        "progress", "growth", "alliance", "partnership", "acordo",
        "paz", "cooperação", "sucesso", "progresso"
    ]

    NEGATIVE_KEYWORDS = [
        "war", "conflict", "crisis", "attack", "sanction", "threat",
        "tension", "collapse", "failure", "violence", "guerra",
        "conflito", "crise", "ataque", "sanção", "ameaça"
    ]

    def extract(self, article: ScrapedArticle) -> ExtractedData:
        """
        Extrai informações semânticas de um artigo.

        Args:
            article: Artigo coletado

        Returns:
            ExtractedData com informações estruturadas
        """
        content = f"{article.title} {article.content}"
        content_lower = content.lower()

        extracted = ExtractedData(
            article_url=article.url,
            source_key=article.source_key,
            title=article.title,
            language=article.language,
            word_count=len(content.split())
        )

        # Extrair países
        extracted.countries = self._extract_countries(content)

        # Extrair atores (pessoas)
        extracted.actors = self._extract_actors(content)

        # Extrair organizações
        extracted.organizations = self._extract_organizations(content)

        # Extrair datas
        extracted.dates = self._extract_dates(content)

        # Identificar tópicos
        extracted.topics = self._identify_topics(content_lower)

        # Extrair fatos principais
        extracted.key_facts = self._extract_key_facts(article.content)

        # Extrair citações
        extracted.quotes = self._extract_quotes(article.content)

        # Extrair estatísticas
        extracted.statistics = self._extract_statistics(article.content)

        # Análise de sentimento básica
        extracted.sentiment_keywords = self._analyze_sentiment(content_lower)

        return extracted

    def _extract_countries(self, text: str) -> List[str]:
        """Extrai países mencionados no texto"""
        found_countries = set()

        for country, patterns in self.COUNTRY_PATTERNS.items():
            for pattern in patterns:
                if re.search(rf'\b{re.escape(pattern)}\b', text, re.IGNORECASE):
                    found_countries.add(country)
                    break

        return list(found_countries)

    def _extract_actors(self, text: str) -> List[str]:
        """Extrai nomes de pessoas (atores políticos)"""
        actors = set()

        # Padrão para nomes próprios (2-3 palavras capitalizadas)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
        matches = re.findall(name_pattern, text)

        # Filtrar nomes comuns que não são pessoas
        exclude_words = {
            "United States", "United Nations", "United Kingdom",
            "North Korea", "South Korea", "South Africa",
            "New York", "New Delhi", "Los Angeles"
        }

        for match in matches:
            if match not in exclude_words and len(match) > 5:
                actors.add(match)

        return list(actors)[:10]  # Limitar a 10 atores principais

    def _extract_organizations(self, text: str) -> List[str]:
        """Extrai organizações internacionais mencionadas"""
        found_orgs = []

        for org in self.ORGANIZATIONS:
            if re.search(rf'\b{re.escape(org)}\b', text, re.IGNORECASE):
                if org not in found_orgs:
                    found_orgs.append(org)

        return found_orgs

    def _extract_dates(self, text: str) -> List[str]:
        """Extrai datas mencionadas no texto"""
        dates = []

        # Padrões de data
        patterns = [
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # DD/MM/YYYY ou MM/DD/YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return list(set(dates))[:5]  # Limitar a 5 datas

    def _identify_topics(self, text_lower: str) -> List[str]:
        """Identifica tópicos geopolíticos no texto"""
        found_topics = []

        topic_keywords = {
            "war": ["war", "warfare", "military operation", "invasion", "guerra"],
            "conflict": ["conflict", "clash", "confrontation", "conflito"],
            "sanctions": ["sanction", "embargo", "restriction", "sanção"],
            "diplomacy": ["diplomacy", "diplomatic", "negotiation", "talks", "diplomacia"],
            "trade": ["trade", "tariff", "commerce", "export", "import", "comércio"],
            "military": ["military", "army", "troops", "defense", "weapon", "militar"],
            "nuclear": ["nuclear", "atomic", "uranium", "enrichment"],
            "climate": ["climate", "environment", "carbon", "emissions", "clima"],
            "elections": ["election", "vote", "ballot", "democracy", "eleição"],
            "economy": ["economy", "economic", "GDP", "inflation", "recession", "economia"],
            "energy": ["energy", "oil", "gas", "petroleum", "energia", "petróleo"],
            "migration": ["migration", "refugee", "asylum", "border", "migração"],
            "terrorism": ["terrorism", "terrorist", "extremism", "terrorismo"],
            "cybersecurity": ["cyber", "hacking", "data breach", "cibersegurança"],
            "alliance": ["alliance", "coalition", "partnership", "aliança"],
            "treaty": ["treaty", "agreement", "pact", "accord", "tratado"],
        }

        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if topic not in found_topics:
                        found_topics.append(topic)
                    break

        return found_topics

    def _extract_key_facts(self, content: str) -> List[str]:
        """Extrai frases que parecem ser fatos importantes"""
        sentences = re.split(r'[.!?]+', content)
        key_facts = []

        fact_indicators = [
            "announced", "confirmed", "reported", "according to",
            "stated", "declared", "revealed", "said",
            "anunciou", "confirmou", "relatou", "segundo"
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue

            # Verificar se contém indicadores de fato
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in fact_indicators):
                key_facts.append(sentence)

        return key_facts[:10]  # Limitar a 10 fatos principais

    def _extract_quotes(self, content: str) -> List[Dict[str, str]]:
        """Extrai citações diretas do texto"""
        quotes = []

        # Padrão para citações entre aspas
        quote_patterns = [
            r'"([^"]{20,200})"',
            r"'([^']{20,200})'",
            r'"([^"]{20,200})"',
        ]

        for pattern in quote_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                quotes.append({
                    "text": match.strip(),
                    "source": "unknown"  # Seria necessário NER mais sofisticado
                })

        return quotes[:5]  # Limitar a 5 citações

    def _extract_statistics(self, content: str) -> List[Dict[str, Any]]:
        """Extrai números e estatísticas do texto"""
        statistics = []

        # Padrões de números com contexto
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:percent|%)', "percentage"),
            (r'\$\s*(\d+(?:\.\d+)?)\s*(?:billion|million|trillion)', "money"),
            (r'(\d+(?:,\d+)*)\s*(?:people|troops|soldiers|casualties)', "count"),
            (r'(\d+(?:\.\d+)?)\s*(?:km|miles|kilometers)', "distance"),
        ]

        for pattern, stat_type in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                statistics.append({
                    "value": match,
                    "type": stat_type
                })

        return statistics[:10]

    def _analyze_sentiment(self, text_lower: str) -> Dict[str, int]:
        """Análise básica de sentimento por contagem de palavras-chave"""
        positive_count = sum(
            1 for word in self.POSITIVE_KEYWORDS
            if word in text_lower
        )
        negative_count = sum(
            1 for word in self.NEGATIVE_KEYWORDS
            if word in text_lower
        )

        return {
            "positive": positive_count,
            "negative": negative_count,
            "ratio": positive_count / (negative_count + 1)  # Evitar divisão por zero
        }

    def extract_batch(self, articles: List[ScrapedArticle]) -> List[ExtractedData]:
        """
        Extrai informações de múltiplos artigos.

        Args:
            articles: Lista de artigos coletados

        Returns:
            Lista de dados extraídos
        """
        results = []
        for article in articles:
            try:
                extracted = self.extract(article)
                results.append(extracted)
            except Exception as e:
                self.logger.error(f"Erro ao extrair de {article.url}: {e}")

        return results
