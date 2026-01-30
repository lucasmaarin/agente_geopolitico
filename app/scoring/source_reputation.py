"""
Gerenciador de reputação de fontes
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import NEWS_SOURCES
from app.utils.logger import LoggerMixin


@dataclass
class SourceReputation:
    """Dados de reputação de uma fonte"""
    key: str
    name: str
    base_score: float
    adjustments: Dict[str, float]
    final_score: float
    tier: str  # tier1, tier2, tier3
    notes: List[str]


class SourceReputationManager(LoggerMixin):
    """
    Gerencia scores de reputação das fontes de notícias.
    Considera:
    - Histórico de precisão
    - Viés conhecido
    - Tipo de fonte (agência, jornal, think tank)
    - Região de origem
    """

    # Classificação de fontes por tier
    TIER_1_SOURCES = [
        "reuters", "apnews"  # Agências de notícias, alta factualidade
    ]

    TIER_2_SOURCES = [
        "bbc", "dw", "foreignaffairs", "csis", "cfr"  # Jornais/think tanks de alto padrão
    ]

    TIER_3_SOURCES = [
        "aljazeera", "crisisgroup", "rand", "nexo",
        "bbc_portuguese", "poder360"  # Boas fontes com viés conhecido
    ]

    # Ajustes por características
    BIAS_ADJUSTMENTS = {
        "aljazeera": {"middle_east": -5, "general": 0},  # Viés regional
        "foreignaffairs": {"us_policy": -3, "general": 0},  # Viés institucional EUA
        "csis": {"us_policy": -3, "general": 0},
        "cfr": {"us_policy": -3, "general": 0},
        "rand": {"us_military": -5, "general": 0},
    }

    # Bônus por diversidade
    DIVERSITY_BONUS = {
        "different_region": 5,
        "different_language": 3,
        "different_type": 3
    }

    def __init__(self):
        self._reputation_cache: Dict[str, SourceReputation] = {}
        self._initialize_reputations()

    def _initialize_reputations(self) -> None:
        """Inicializa scores de reputação baseado em configuração"""
        for key, info in NEWS_SOURCES.items():
            base_score = info.get("reputation_score", 70)

            # Determinar tier
            if key in self.TIER_1_SOURCES:
                tier = "tier1"
            elif key in self.TIER_2_SOURCES:
                tier = "tier2"
            else:
                tier = "tier3"

            self._reputation_cache[key] = SourceReputation(
                key=key,
                name=info.get("name", key),
                base_score=base_score,
                adjustments={},
                final_score=base_score,
                tier=tier,
                notes=[]
            )

    def get_reputation(self, source_key: str) -> Optional[SourceReputation]:
        """
        Obtém reputação de uma fonte.

        Args:
            source_key: Chave da fonte

        Returns:
            SourceReputation ou None se não encontrada
        """
        return self._reputation_cache.get(source_key)

    def calculate_source_score(
        self,
        source_key: str,
        topic: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> float:
        """
        Calcula score ajustado para um contexto específico.

        Args:
            source_key: Chave da fonte
            topic: Tema sendo analisado
            context: Contexto adicional

        Returns:
            Score ajustado (0-100)
        """
        reputation = self.get_reputation(source_key)
        if not reputation:
            return 50.0  # Score default para fonte desconhecida

        score = reputation.base_score
        adjustments = []

        # Aplicar ajustes de viés se relevante
        if source_key in self.BIAS_ADJUSTMENTS:
            bias_info = self.BIAS_ADJUSTMENTS[source_key]

            if topic:
                topic_lower = topic.lower()
                for bias_key, adjustment in bias_info.items():
                    if bias_key in topic_lower:
                        score += adjustment
                        adjustments.append(f"Viés {bias_key}: {adjustment:+.0f}")

        # Ajuste por tier
        tier_bonus = {
            "tier1": 5,
            "tier2": 0,
            "tier3": -5
        }.get(reputation.tier, 0)
        score += tier_bonus

        # Garantir range 0-100
        score = max(0, min(100, score))

        return score

    def evaluate_source_mix(
        self,
        source_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Avalia a qualidade do mix de fontes.

        Args:
            source_keys: Lista de chaves de fontes

        Returns:
            Avaliação do mix de fontes
        """
        if not source_keys:
            return {
                "quality": "insufficient",
                "score": 0,
                "issues": ["Nenhuma fonte fornecida"]
            }

        # Coletar informações das fontes
        regions = set()
        languages = set()
        types = set()
        tiers = []
        scores = []

        for key in source_keys:
            if key not in NEWS_SOURCES:
                continue

            info = NEWS_SOURCES[key]
            regions.add(info.get("region", "unknown"))
            languages.add(info.get("language", "unknown"))
            types.add(info.get("type", "unknown"))

            reputation = self.get_reputation(key)
            if reputation:
                tiers.append(reputation.tier)
                scores.append(reputation.base_score)

        # Calcular métricas
        diversity_score = 0

        # Bônus por diversidade regional
        if len(regions) >= 2:
            diversity_score += self.DIVERSITY_BONUS["different_region"]
        if len(languages) >= 2:
            diversity_score += self.DIVERSITY_BONUS["different_language"]
        if len(types) >= 2:
            diversity_score += self.DIVERSITY_BONUS["different_type"]

        # Score médio das fontes
        avg_score = sum(scores) / len(scores) if scores else 0

        # Verificar presença de tier 1
        has_tier1 = "tier1" in tiers

        # Determinar qualidade geral
        issues = []
        if len(source_keys) < 3:
            issues.append("Menos de 3 fontes independentes")
        if not has_tier1:
            issues.append("Nenhuma fonte tier 1 (agências de notícias)")
        if len(regions) < 2:
            issues.append("Baixa diversidade regional")

        # Calcular score final do mix
        mix_score = avg_score + diversity_score
        if has_tier1:
            mix_score += 10

        # Classificar qualidade
        if mix_score >= 85 and len(source_keys) >= 3:
            quality = "excellent"
        elif mix_score >= 70 and len(source_keys) >= 3:
            quality = "good"
        elif mix_score >= 50:
            quality = "acceptable"
        else:
            quality = "poor"

        return {
            "quality": quality,
            "score": min(100, mix_score),
            "sources_count": len(source_keys),
            "diversity": {
                "regions": list(regions),
                "languages": list(languages),
                "types": list(types)
            },
            "tier_distribution": {
                "tier1": tiers.count("tier1"),
                "tier2": tiers.count("tier2"),
                "tier3": tiers.count("tier3")
            },
            "average_source_score": round(avg_score, 1),
            "diversity_bonus": diversity_score,
            "issues": issues,
            "recommendations": self._generate_recommendations(
                source_keys, regions, types, has_tier1
            )
        }

    def _generate_recommendations(
        self,
        current_sources: List[str],
        regions: set,
        types: set,
        has_tier1: bool
    ) -> List[str]:
        """Gera recomendações para melhorar o mix de fontes"""
        recommendations = []

        # Recomendar adicionar tier 1 se não tiver
        if not has_tier1:
            recommendations.append(
                "Adicione Reuters ou AP News para maior factualidade"
            )

        # Recomendar diversidade regional
        if "brazil" not in regions and "global" not in regions:
            recommendations.append(
                "Considere adicionar fontes brasileiras (Nexo, BBC Brasil)"
            )

        if "middle_east" not in regions:
            if any(t in str(current_sources).lower() for t in ["war", "conflict", "israel", "iran"]):
                recommendations.append(
                    "Para cobertura de Oriente Médio, considere Al Jazeera"
                )

        # Recomendar think tanks para análise
        if "analysis" not in types:
            recommendations.append(
                "Adicione think tanks (CFR, CSIS) para análise mais profunda"
            )

        return recommendations[:3]  # Limitar a 3 recomendações

    def get_source_warnings(self, source_key: str, topic: str) -> List[str]:
        """
        Retorna avisos específicos sobre uma fonte para um tema.

        Args:
            source_key: Chave da fonte
            topic: Tema sendo analisado

        Returns:
            Lista de avisos
        """
        warnings = []
        topic_lower = topic.lower()

        # Avisos específicos por fonte
        source_warnings = {
            "aljazeera": {
                "triggers": ["israel", "palestine", "gaza", "qatar"],
                "warning": "Al Jazeera pode ter viés em temas relacionados a Israel/Palestina e Qatar"
            },
            "rand": {
                "triggers": ["military", "defense", "pentagon", "us army"],
                "warning": "RAND tem contratos com Departamento de Defesa dos EUA"
            },
            "foreignaffairs": {
                "triggers": ["us policy", "american", "washington"],
                "warning": "Foreign Affairs representa perspectiva do establishment de política externa dos EUA"
            },
            "poder360": {
                "triggers": ["brasil", "brazil", "lula", "bolsonaro"],
                "warning": "Poder360 pode ter viés em cobertura política brasileira"
            }
        }

        if source_key in source_warnings:
            sw = source_warnings[source_key]
            if any(trigger in topic_lower for trigger in sw["triggers"]):
                warnings.append(sw["warning"])

        return warnings
