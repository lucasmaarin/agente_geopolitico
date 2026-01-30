"""
Motor de cruzamento entre fontes - identifica convergências e divergências
"""
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.utils.logger import LoggerMixin
from app.pipelines.extractor import ExtractedData


@dataclass
class CrossReferenceResult:
    """Resultado do cruzamento entre fontes"""

    # Convergências
    confirmed_facts: List[Dict[str, Any]] = field(default_factory=list)
    common_countries: List[str] = field(default_factory=list)
    common_actors: List[str] = field(default_factory=list)
    common_topics: List[str] = field(default_factory=list)

    # Divergências
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    unique_claims: List[Dict[str, Any]] = field(default_factory=list)

    # Métricas
    convergence_score: float = 0.0
    sources_count: int = 0
    reliability_indicators: Dict[str, Any] = field(default_factory=dict)


class CrossReferenceEngine(LoggerMixin):
    """
    Motor de cruzamento que analisa múltiplas fontes para:
    - Identificar fatos confirmados por múltiplas fontes
    - Detectar contradições entre fontes
    - Calcular score de convergência
    """

    def __init__(self):
        self.min_sources_for_confirmation = 2

    def analyze(self, extracted_data: List[ExtractedData]) -> CrossReferenceResult:
        """
        Analisa dados extraídos de múltiplas fontes.

        Args:
            extracted_data: Lista de dados extraídos de cada artigo

        Returns:
            CrossReferenceResult com análise de convergência
        """
        if not extracted_data:
            return CrossReferenceResult()

        result = CrossReferenceResult(sources_count=len(extracted_data))

        # Analisar convergências de entidades
        result.common_countries = self._find_common_entities(
            [d.countries for d in extracted_data]
        )
        result.common_actors = self._find_common_entities(
            [d.actors for d in extracted_data]
        )
        result.common_topics = self._find_common_entities(
            [d.topics for d in extracted_data]
        )

        # Identificar fatos confirmados
        result.confirmed_facts = self._find_confirmed_facts(extracted_data)

        # Identificar contradições
        result.contradictions = self._find_contradictions(extracted_data)

        # Identificar claims únicos
        result.unique_claims = self._find_unique_claims(extracted_data)

        # Calcular score de convergência
        result.convergence_score = self._calculate_convergence_score(result)

        # Indicadores de confiabilidade
        result.reliability_indicators = self._calculate_reliability_indicators(
            extracted_data, result
        )

        return result

    def _find_common_entities(self, entity_lists: List[List[str]]) -> List[str]:
        """
        Encontra entidades mencionadas em múltiplas fontes.

        Args:
            entity_lists: Lista de listas de entidades (uma por fonte)

        Returns:
            Lista de entidades comuns
        """
        if not entity_lists:
            return []

        # Contar ocorrências
        entity_count = defaultdict(int)
        for entities in entity_lists:
            for entity in set(entities):  # set para não contar duplicatas na mesma fonte
                entity_count[entity] += 1

        # Retornar entidades mencionadas por pelo menos 2 fontes
        common = [
            entity for entity, count in entity_count.items()
            if count >= self.min_sources_for_confirmation
        ]

        # Ordenar por frequência
        common.sort(key=lambda x: entity_count[x], reverse=True)

        return common

    def _find_confirmed_facts(self, extracted_data: List[ExtractedData]) -> List[Dict]:
        """
        Identifica fatos mencionados por múltiplas fontes.

        Args:
            extracted_data: Dados extraídos

        Returns:
            Lista de fatos confirmados com fontes
        """
        confirmed = []

        # Agrupar fatos similares
        all_facts = []
        for data in extracted_data:
            for fact in data.key_facts:
                all_facts.append({
                    "fact": fact,
                    "source": data.source_key,
                    "url": data.article_url
                })

        # Encontrar fatos similares entre fontes
        fact_groups = self._group_similar_facts(all_facts)

        for group in fact_groups:
            if len(set(f["source"] for f in group)) >= self.min_sources_for_confirmation:
                sources = list(set(f["source"] for f in group))
                confirmed.append({
                    "fact": group[0]["fact"],  # Usar o primeiro como representativo
                    "confirmed_by": sources,
                    "confidence": "high" if len(sources) >= 3 else "medium",
                    "sources_count": len(sources)
                })

        return confirmed

    def _group_similar_facts(self, facts: List[Dict]) -> List[List[Dict]]:
        """
        Agrupa fatos similares baseado em sobreposição de palavras-chave.
        """
        if not facts:
            return []

        groups = []
        used = set()

        for i, fact1 in enumerate(facts):
            if i in used:
                continue

            group = [fact1]
            used.add(i)

            words1 = set(self._extract_keywords(fact1["fact"]))

            for j, fact2 in enumerate(facts[i+1:], i+1):
                if j in used:
                    continue

                words2 = set(self._extract_keywords(fact2["fact"]))

                # Calcular similaridade Jaccard
                if words1 and words2:
                    similarity = len(words1 & words2) / len(words1 | words2)
                    if similarity > 0.3:  # Threshold de similaridade
                        group.append(fact2)
                        used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave de um texto"""
        # Remover pontuação e converter para minúsculas
        text = re.sub(r'[^\w\s]', '', text.lower())
        words = text.split()

        # Remover stopwords comuns
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'that', 'this', 'these', 'those', 'and', 'but',
            'or', 'nor', 'so', 'yet', 'both', 'either', 'neither', 'not',
            'only', 'own', 'same', 'than', 'too', 'very', 'just'
        }

        return [w for w in words if w not in stopwords and len(w) > 2]

    def _find_contradictions(self, extracted_data: List[ExtractedData]) -> List[Dict]:
        """
        Identifica contradições entre fontes.

        Args:
            extracted_data: Dados extraídos

        Returns:
            Lista de contradições detectadas
        """
        contradictions = []

        # Padrões de contradição numérica
        numeric_claims = defaultdict(list)

        for data in extracted_data:
            for stat in data.statistics:
                key = stat.get("type", "unknown")
                numeric_claims[key].append({
                    "value": stat.get("value"),
                    "source": data.source_key
                })

        # Verificar se há números muito diferentes para o mesmo tipo de dado
        for claim_type, claims in numeric_claims.items():
            if len(claims) >= 2:
                values = []
                for claim in claims:
                    try:
                        val = float(claim["value"].replace(",", ""))
                        values.append((val, claim["source"]))
                    except (ValueError, AttributeError):
                        continue

                if len(values) >= 2:
                    # Verificar se há diferença significativa (>50%)
                    min_val = min(v[0] for v in values)
                    max_val = max(v[0] for v in values)

                    if min_val > 0 and (max_val - min_val) / min_val > 0.5:
                        contradictions.append({
                            "type": "numeric_discrepancy",
                            "claim_type": claim_type,
                            "values": values,
                            "severity": "high" if (max_val - min_val) / min_val > 1.0 else "medium"
                        })

        return contradictions

    def _find_unique_claims(self, extracted_data: List[ExtractedData]) -> List[Dict]:
        """
        Identifica claims únicos (não confirmados por outras fontes).

        Args:
            extracted_data: Dados extraídos

        Returns:
            Lista de claims únicos
        """
        unique_claims = []

        # Todos os fatos
        all_facts = []
        for data in extracted_data:
            for fact in data.key_facts:
                all_facts.append({
                    "fact": fact,
                    "source": data.source_key,
                    "keywords": set(self._extract_keywords(fact))
                })

        # Verificar quais não têm similar em outras fontes
        for i, fact1 in enumerate(all_facts):
            has_similar = False

            for j, fact2 in enumerate(all_facts):
                if i == j or fact1["source"] == fact2["source"]:
                    continue

                # Calcular similaridade
                if fact1["keywords"] and fact2["keywords"]:
                    similarity = len(fact1["keywords"] & fact2["keywords"]) / len(fact1["keywords"] | fact2["keywords"])
                    if similarity > 0.3:
                        has_similar = True
                        break

            if not has_similar:
                unique_claims.append({
                    "fact": fact1["fact"],
                    "source": fact1["source"],
                    "warning": "Informação não confirmada por outras fontes"
                })

        return unique_claims[:10]  # Limitar

    def _calculate_convergence_score(self, result: CrossReferenceResult) -> float:
        """
        Calcula score de convergência (0-100).

        Fatores:
        - Quantidade de fatos confirmados
        - Entidades comuns
        - Ausência de contradições
        """
        score = 0.0

        # Fatos confirmados (até 40 pontos)
        confirmed_count = len(result.confirmed_facts)
        score += min(40, confirmed_count * 10)

        # Entidades comuns (até 30 pontos)
        common_entities = (
            len(result.common_countries) +
            len(result.common_actors) +
            len(result.common_topics)
        )
        score += min(30, common_entities * 5)

        # Penalização por contradições (até -20 pontos)
        contradiction_penalty = len(result.contradictions) * 10
        score -= min(20, contradiction_penalty)

        # Bônus por múltiplas fontes
        if result.sources_count >= 3:
            score += 10
        if result.sources_count >= 5:
            score += 10

        return max(0, min(100, score))

    def _calculate_reliability_indicators(
        self,
        extracted_data: List[ExtractedData],
        result: CrossReferenceResult
    ) -> Dict[str, Any]:
        """Calcula indicadores detalhados de confiabilidade"""

        # Diversidade de fontes
        source_types = set()
        source_regions = set()
        for data in extracted_data:
            # Inferir tipo baseado no source_key
            if data.source_key in ["reuters", "apnews", "bbc"]:
                source_types.add("news_agency")
            elif data.source_key in ["foreignaffairs", "csis", "cfr", "rand"]:
                source_types.add("think_tank")
            else:
                source_types.add("regional_news")

        # Cobertura de perspectivas
        all_countries = set()
        for data in extracted_data:
            all_countries.update(data.countries)

        return {
            "source_diversity": len(source_types),
            "geographic_coverage": len(all_countries),
            "facts_per_source": len(result.confirmed_facts) / max(1, result.sources_count),
            "contradiction_ratio": len(result.contradictions) / max(1, len(result.confirmed_facts)),
            "unique_claims_ratio": len(result.unique_claims) / max(1, sum(len(d.key_facts) for d in extracted_data))
        }
