"""
Calculadora de score de confiabilidade
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.utils.logger import LoggerMixin
from app.scoring.source_reputation import SourceReputationManager
from app.pipelines.cross_reference import CrossReferenceResult
from app.pipelines.extractor import ExtractedData


@dataclass
class ConfidenceScoreResult:
    """Resultado do cálculo de confiabilidade"""
    total_score: int
    classification: str
    breakdown: Dict[str, Dict[str, Any]]
    alerts: List[str]
    recommendations: List[str]


class ConfidenceCalculator(LoggerMixin):
    """
    Calcula score de confiabilidade (0-100) baseado em múltiplos critérios:
    - Número de fontes (20 pontos)
    - Convergência factual (25 pontos)
    - Reputação das fontes (20 pontos)
    - Linguagem emocional (15 pontos)
    - Dados verificáveis (10 pontos)
    - Risco de clickbait (10 pontos)
    """

    def __init__(self):
        self.reputation_manager = SourceReputationManager()

    def calculate(
        self,
        extracted_data: List[ExtractedData],
        cross_reference: CrossReferenceResult,
        bias_analysis: Optional[Dict] = None
    ) -> ConfidenceScoreResult:
        """
        Calcula score de confiabilidade completo.

        Args:
            extracted_data: Dados extraídos dos artigos
            cross_reference: Resultado do cruzamento de fontes
            bias_analysis: Análise de viés (se disponível)

        Returns:
            ConfidenceScoreResult com score detalhado
        """
        breakdown = {}
        alerts = []
        recommendations = []

        # 1. Número de fontes (20 pontos)
        sources_score = self._score_source_count(extracted_data)
        breakdown["numero_fontes"] = sources_score
        if sources_score["pontos"] < 15:
            alerts.append("Poucas fontes independentes")
            recommendations.append("Buscar mais fontes para validação cruzada")

        # 2. Convergência factual (25 pontos)
        convergence_score = self._score_convergence(cross_reference)
        breakdown["convergencia_factual"] = convergence_score
        if convergence_score["pontos"] < 15:
            alerts.append("Baixa convergência entre fontes")

        # 3. Reputação das fontes (20 pontos)
        reputation_score = self._score_reputation(extracted_data)
        breakdown["reputacao_fontes"] = reputation_score
        if reputation_score["pontos"] < 12:
            alerts.append("Mix de fontes poderia ser melhorado")
            recommendations.extend(reputation_score.get("recommendations", []))

        # 4. Linguagem emocional (15 pontos)
        emotional_score = self._score_emotional_language(extracted_data, bias_analysis)
        breakdown["linguagem_emocional"] = emotional_score
        if emotional_score["pontos"] < 10:
            alerts.append("Linguagem emocional detectada nas fontes")

        # 5. Dados verificáveis (10 pontos)
        verifiable_score = self._score_verifiable_data(extracted_data)
        breakdown["dados_verificaveis"] = verifiable_score
        if verifiable_score["pontos"] < 5:
            alerts.append("Poucos dados verificáveis nos artigos")

        # 6. Risco de clickbait (10 pontos)
        clickbait_score = self._score_clickbait_risk(extracted_data)
        breakdown["risco_clickbait"] = clickbait_score
        if clickbait_score["pontos"] < 5:
            alerts.append("Alguns títulos parecem sensacionalistas")

        # Calcular total
        total = sum(item["pontos"] for item in breakdown.values())
        total = max(0, min(100, total))

        # Classificação
        classification = self._get_classification(total)

        return ConfidenceScoreResult(
            total_score=total,
            classification=classification,
            breakdown=breakdown,
            alerts=alerts,
            recommendations=recommendations[:3]  # Top 3 recomendações
        )

    def _score_source_count(self, extracted_data: List[ExtractedData]) -> Dict:
        """Pontua baseado no número de fontes (máx 20 pontos)"""
        num_sources = len(extracted_data)
        unique_sources = len(set(d.source_key for d in extracted_data))

        if unique_sources >= 5:
            pontos = 20
        elif unique_sources >= 3:
            pontos = 15
        elif unique_sources >= 2:
            pontos = 10
        else:
            pontos = 5

        return {
            "pontos": pontos,
            "maximo": 20,
            "fontes_totais": num_sources,
            "fontes_unicas": unique_sources,
            "justificativa": f"{unique_sources} fontes independentes"
        }

    def _score_convergence(self, cross_reference: CrossReferenceResult) -> Dict:
        """Pontua baseado na convergência (máx 25 pontos)"""
        # Usar o score de convergência do cross-reference
        convergence = cross_reference.convergence_score

        # Converter para escala de 25 pontos
        pontos = int((convergence / 100) * 25)

        # Penalizar por contradições
        num_contradictions = len(cross_reference.contradictions)
        pontos -= num_contradictions * 3
        pontos = max(0, pontos)

        return {
            "pontos": pontos,
            "maximo": 25,
            "convergencia_percentual": round(convergence, 1),
            "fatos_confirmados": len(cross_reference.confirmed_facts),
            "contradicoes": num_contradictions,
            "justificativa": f"Convergência de {convergence:.1f}% entre fontes"
        }

    def _score_reputation(self, extracted_data: List[ExtractedData]) -> Dict:
        """Pontua baseado na reputação das fontes (máx 20 pontos)"""
        source_keys = list(set(d.source_key for d in extracted_data))

        # Avaliar mix de fontes
        mix_eval = self.reputation_manager.evaluate_source_mix(source_keys)

        # Converter score do mix para escala de 20 pontos
        pontos = int((mix_eval["score"] / 100) * 20)

        return {
            "pontos": pontos,
            "maximo": 20,
            "qualidade_mix": mix_eval["quality"],
            "tier_distribution": mix_eval["tier_distribution"],
            "diversidade": mix_eval["diversity"],
            "recommendations": mix_eval.get("recommendations", []),
            "justificativa": f"Qualidade do mix: {mix_eval['quality']}"
        }

    def _score_emotional_language(
        self,
        extracted_data: List[ExtractedData],
        bias_analysis: Optional[Dict]
    ) -> Dict:
        """Pontua baseado na linguagem emocional (máx 15 pontos)"""
        # Usar análise de sentimento dos dados extraídos
        total_positive = 0
        total_negative = 0

        for data in extracted_data:
            sentiment = data.sentiment_keywords
            total_positive += sentiment.get("positive", 0)
            total_negative += sentiment.get("negative", 0)

        # Calcular ratio de linguagem emocional
        total_emotional = total_positive + total_negative
        total_words = sum(d.word_count for d in extracted_data)

        if total_words > 0:
            emotional_ratio = total_emotional / (total_words / 100)  # Por 100 palavras
        else:
            emotional_ratio = 0

        # Quanto menos emocional, mais pontos
        if emotional_ratio < 1:
            pontos = 15
        elif emotional_ratio < 2:
            pontos = 12
        elif emotional_ratio < 3:
            pontos = 8
        elif emotional_ratio < 5:
            pontos = 5
        else:
            pontos = 2

        # Ajustar baseado na análise de viés se disponível
        if bias_analysis and isinstance(bias_analysis, dict):
            risk_level = bias_analysis.get("risco_geral", "baixo")
            if risk_level == "alto":
                pontos -= 5
            elif risk_level == "médio":
                pontos -= 2

        pontos = max(0, min(15, pontos))

        return {
            "pontos": pontos,
            "maximo": 15,
            "keywords_positivos": total_positive,
            "keywords_negativos": total_negative,
            "ratio_emocional": round(emotional_ratio, 2),
            "justificativa": f"Ratio emocional: {emotional_ratio:.2f} por 100 palavras"
        }

    def _score_verifiable_data(self, extracted_data: List[ExtractedData]) -> Dict:
        """Pontua baseado em dados verificáveis (máx 10 pontos)"""
        total_stats = 0
        total_dates = 0
        total_quotes = 0

        for data in extracted_data:
            total_stats += len(data.statistics)
            total_dates += len(data.dates)
            total_quotes += len(data.quotes)

        total_verifiable = total_stats + total_dates + total_quotes

        # Quanto mais dados verificáveis, mais pontos
        if total_verifiable >= 15:
            pontos = 10
        elif total_verifiable >= 10:
            pontos = 8
        elif total_verifiable >= 5:
            pontos = 6
        elif total_verifiable >= 2:
            pontos = 4
        else:
            pontos = 2

        return {
            "pontos": pontos,
            "maximo": 10,
            "estatisticas": total_stats,
            "datas": total_dates,
            "citacoes": total_quotes,
            "total_verificaveis": total_verifiable,
            "justificativa": f"{total_verifiable} dados verificáveis encontrados"
        }

    def _score_clickbait_risk(self, extracted_data: List[ExtractedData]) -> Dict:
        """Pontua baseado no risco de clickbait (máx 10 pontos)"""
        clickbait_indicators = 0
        total_articles = len(extracted_data)

        clickbait_patterns = [
            "você não vai acreditar",
            "shocking", "chocante",
            "incredible", "incrível",
            "breaking", "urgente",
            "bombshell", "bomba",
            "revealed", "revelado",
            "secret", "segredo",
            "!!", "?!"
        ]

        for data in extracted_data:
            title_lower = data.title.lower()
            for pattern in clickbait_patterns:
                if pattern in title_lower:
                    clickbait_indicators += 1
                    break

        # Calcular proporção de clickbait
        if total_articles > 0:
            clickbait_ratio = clickbait_indicators / total_articles
        else:
            clickbait_ratio = 0

        # Quanto menos clickbait, mais pontos
        if clickbait_ratio == 0:
            pontos = 10
        elif clickbait_ratio < 0.2:
            pontos = 8
        elif clickbait_ratio < 0.4:
            pontos = 5
        elif clickbait_ratio < 0.6:
            pontos = 3
        else:
            pontos = 1

        return {
            "pontos": pontos,
            "maximo": 10,
            "titulos_suspeitos": clickbait_indicators,
            "total_artigos": total_articles,
            "ratio_clickbait": round(clickbait_ratio, 2),
            "justificativa": f"{clickbait_indicators} de {total_articles} títulos suspeitos"
        }

    def _get_classification(self, score: int) -> str:
        """Retorna classificação textual do score"""
        if score >= 85:
            return "MUITO ALTA - Informações altamente confiáveis"
        elif score >= 70:
            return "ALTA - Informações confiáveis com pequenas ressalvas"
        elif score >= 50:
            return "MÉDIA - Informações parcialmente verificáveis"
        elif score >= 30:
            return "BAIXA - Informações com problemas significativos"
        else:
            return "MUITO BAIXA - Informações não confiáveis"

    def quick_score(self, num_sources: int, has_tier1: bool = False) -> int:
        """
        Cálculo rápido de score sem análise completa.
        Útil para filtros e ordenação.

        Args:
            num_sources: Número de fontes
            has_tier1: Se tem fonte tier 1 (Reuters, AP)

        Returns:
            Score estimado (0-100)
        """
        base_score = min(50, num_sources * 15)

        if has_tier1:
            base_score += 20

        if num_sources >= 3:
            base_score += 10

        return min(100, base_score)
