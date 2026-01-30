"""
Gerador de relatórios - compila todas as análises no formato final
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.utils.logger import LoggerMixin
from app.pipelines.analyzer import AnalysisResult
from app.pipelines.cross_reference import CrossReferenceResult


@dataclass
class GeopoliticalReport:
    """Estrutura do relatório geopolítico final"""

    # Identificação
    topic: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    # Seções obrigatórias
    tldr: str = ""
    what_happened: str = ""
    why_it_matters: str = ""
    winners_losers: str = ""
    brazil_impact: str = ""
    manipulation_risk: str = ""
    simple_explanation: str = ""
    future_scenarios: Dict[str, Any] = field(default_factory=dict)

    # Score de confiabilidade
    confidence_score: int = 0
    confidence_breakdown: Dict[str, Any] = field(default_factory=dict)

    # Metadados
    sources: List[Dict[str, str]] = field(default_factory=list)
    sources_count: int = 0
    convergence_score: float = 0.0
    bias_detected: List[Dict] = field(default_factory=list)

    # Análises brutas (para debug/auditoria)
    raw_analyses: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator(LoggerMixin):
    """
    Gera relatórios geopolíticos no formato padronizado.
    Compila resultados do analyzer e cross-reference engine.
    """

    REPORT_TEMPLATE = """
🧾 RESUMO CURTO (TL;DR)
{tldr}

🌍 O QUE ACONTECEU
{what_happened}

❓ POR QUE ISSO IMPORTA
{why_it_matters}

⚔️ QUEM GANHA E QUEM PERDE
{winners_losers}

🇧🇷 IMPACTO PARA O BRASIL
{brazil_impact}

⚠️ RISCO DE MANIPULAÇÃO (VIÉS E PROPAGANDA)
{manipulation_risk}

📊 SCORE DE CONFIABILIDADE ({confidence_score}/100)
{confidence_explanation}

👩‍❤️‍👨 EXPLICAÇÃO SIMPLES PARA LEIGOS
{simple_explanation}

🔮 CENÁRIOS FUTUROS

📍 Curto Prazo (1-3 meses):
{short_term}

📍 Médio Prazo (6-12 meses):
{medium_term}

⚠️ Risco Extremo:
{extreme_risk}

---
📰 Fontes utilizadas: {sources_count}
📊 Score de convergência entre fontes: {convergence_score}%
⏰ Relatório gerado em: {generated_at}
"""

    def generate(
        self,
        topic: str,
        analysis_results: Dict[str, AnalysisResult],
        cross_reference: CrossReferenceResult,
        sources: List[Dict[str, str]]
    ) -> GeopoliticalReport:
        """
        Gera relatório completo.

        Args:
            topic: Tema do relatório
            analysis_results: Resultados das análises OpenAI
            cross_reference: Resultado do cruzamento de fontes
            sources: Lista de fontes utilizadas

        Returns:
            GeopoliticalReport completo
        """
        report = GeopoliticalReport(
            topic=topic,
            sources=sources,
            sources_count=len(sources),
            convergence_score=cross_reference.convergence_score
        )

        # Extrair resumo factual
        if "factual_summary" in analysis_results and analysis_results["factual_summary"].success:
            summary = analysis_results["factual_summary"].content
            report.what_happened = summary
            report.tldr = self._generate_tldr(summary)

        # Extrair detecção de viés
        if "bias_detection" in analysis_results and analysis_results["bias_detection"].success:
            bias_data = analysis_results["bias_detection"].content
            if isinstance(bias_data, dict):
                report.bias_detected = bias_data.get("vieses_detectados", [])
                report.manipulation_risk = self._format_bias_analysis(bias_data)

        # Extrair explicação simples
        if "simple_explanation" in analysis_results and analysis_results["simple_explanation"].success:
            report.simple_explanation = analysis_results["simple_explanation"].content

        # Extrair score de confiabilidade
        if "confidence_score" in analysis_results and analysis_results["confidence_score"].success:
            score_data = analysis_results["confidence_score"].content
            if isinstance(score_data, dict):
                report.confidence_score = score_data.get("score_total", 0)
                report.confidence_breakdown = score_data.get("breakdown", {})

        # Extrair cenários
        if "scenarios" in analysis_results and analysis_results["scenarios"].success:
            scenarios = analysis_results["scenarios"].content
            if isinstance(scenarios, dict):
                report.future_scenarios = scenarios

        # Gerar seções adicionais
        report.why_it_matters = self._generate_why_it_matters(
            report.what_happened,
            cross_reference
        )
        report.winners_losers = self._generate_winners_losers(
            cross_reference,
            report.future_scenarios
        )
        report.brazil_impact = self._generate_brazil_impact(
            cross_reference,
            report.future_scenarios
        )

        # Armazenar análises brutas
        report.raw_analyses = {
            k: v.content for k, v in analysis_results.items() if v.success
        }

        return report

    def _generate_tldr(self, full_summary: str) -> str:
        """Gera TL;DR a partir do resumo completo"""
        if not full_summary:
            return "Resumo não disponível."

        # Pegar as primeiras 2-3 sentenças
        sentences = full_summary.split(". ")
        tldr_sentences = sentences[:3]
        tldr = ". ".join(tldr_sentences)

        if not tldr.endswith("."):
            tldr += "."

        return tldr[:500]  # Limitar tamanho

    def _format_bias_analysis(self, bias_data: Dict) -> str:
        """Formata análise de viés para exibição"""
        parts = []

        risk_level = bias_data.get("risco_geral", "não avaliado")
        parts.append(f"Nível de risco: {risk_level.upper()}")

        vieses = bias_data.get("vieses_detectados", [])
        if vieses:
            parts.append("\nVieses identificados:")
            for v in vieses[:3]:  # Top 3
                parts.append(f"  • {v.get('tipo', 'N/A')}: {v.get('explicacao', 'N/A')}")

        propaganda = bias_data.get("propaganda_detectada", [])
        if propaganda:
            parts.append("\nTécnicas de propaganda:")
            for p in propaganda[:2]:  # Top 2
                parts.append(f"  • {p.get('tecnica', 'N/A')}")

        recomendacao = bias_data.get("recomendacao", "")
        if recomendacao:
            parts.append(f"\n💡 Recomendação: {recomendacao}")

        return "\n".join(parts)

    def _generate_why_it_matters(
        self,
        what_happened: str,
        cross_reference: CrossReferenceResult
    ) -> str:
        """Gera seção 'Por que isso importa'"""
        parts = []

        # Baseado nas entidades comuns
        if cross_reference.common_countries:
            countries = ", ".join(cross_reference.common_countries[:5])
            parts.append(f"Países diretamente envolvidos: {countries}")

        if cross_reference.common_topics:
            topics = ", ".join(cross_reference.common_topics)
            parts.append(f"Temas geopolíticos relevantes: {topics}")

        # Indicador de confiabilidade
        if cross_reference.convergence_score >= 70:
            parts.append("✅ Alta convergência entre fontes indica evento bem documentado.")
        elif cross_reference.convergence_score >= 40:
            parts.append("⚠️ Convergência moderada - algumas informações ainda em disputa.")
        else:
            parts.append("❌ Baixa convergência - informações contraditórias, cautela recomendada.")

        return "\n".join(parts) if parts else "Análise de relevância não disponível."

    def _generate_winners_losers(
        self,
        cross_reference: CrossReferenceResult,
        scenarios: Dict
    ) -> str:
        """Gera seção 'Quem ganha e quem perde'"""
        parts = []

        # Usar atores comuns
        if cross_reference.common_actors:
            parts.append("Atores principais identificados:")
            for actor in cross_reference.common_actors[:5]:
                parts.append(f"  • {actor}")

        # Se temos cenários, extrair de lá
        if scenarios and isinstance(scenarios, dict):
            if "variaveis_chave" in scenarios:
                parts.append("\nDinâmica de interesses:")
                for var in scenarios.get("variaveis_chave", [])[:2]:
                    parts.append(f"  • {var.get('variavel', 'N/A')}")

        return "\n".join(parts) if parts else "Análise de interesses não disponível."

    def _generate_brazil_impact(
        self,
        cross_reference: CrossReferenceResult,
        scenarios: Dict
    ) -> str:
        """Gera seção 'Impacto para o Brasil'"""
        parts = []

        # Verificar se Brasil está entre os países
        if "Brazil" in cross_reference.common_countries:
            parts.append("🇧🇷 Brasil diretamente mencionado nas fontes.")
        else:
            parts.append("Brasil não mencionado diretamente, mas pode haver impactos indiretos.")

        # Extrair impactos dos cenários
        if scenarios and isinstance(scenarios, dict):
            for key in ["cenario_curto_prazo", "cenario_medio_prazo", "cenario_risco_extremo"]:
                if key in scenarios and "impacto_brasil" in scenarios[key]:
                    impact = scenarios[key]["impacto_brasil"]
                    if impact:
                        label = {
                            "cenario_curto_prazo": "Curto prazo",
                            "cenario_medio_prazo": "Médio prazo",
                            "cenario_risco_extremo": "Risco extremo"
                        }.get(key, key)
                        parts.append(f"\n{label}: {impact}")

        return "\n".join(parts) if parts else "Impacto para o Brasil não avaliado."

    def format_report(self, report: GeopoliticalReport) -> str:
        """
        Formata relatório para exibição/exportação.

        Args:
            report: Relatório gerado

        Returns:
            String formatada do relatório
        """
        # Formatar cenários
        scenarios = report.future_scenarios
        short_term = ""
        medium_term = ""
        extreme_risk = ""

        if scenarios:
            if "cenario_curto_prazo" in scenarios:
                sc = scenarios["cenario_curto_prazo"]
                short_term = f"{sc.get('titulo', 'N/A')}\n{sc.get('descricao', '')}"

            if "cenario_medio_prazo" in scenarios:
                sc = scenarios["cenario_medio_prazo"]
                medium_term = f"{sc.get('titulo', 'N/A')}\n{sc.get('descricao', '')}"

            if "cenario_risco_extremo" in scenarios:
                sc = scenarios["cenario_risco_extremo"]
                extreme_risk = f"{sc.get('titulo', 'N/A')}\n{sc.get('descricao', '')}"

        # Explicação do score
        confidence_explanation = self._format_confidence_explanation(
            report.confidence_score,
            report.confidence_breakdown
        )

        return self.REPORT_TEMPLATE.format(
            tldr=report.tldr or "N/A",
            what_happened=report.what_happened or "N/A",
            why_it_matters=report.why_it_matters or "N/A",
            winners_losers=report.winners_losers or "N/A",
            brazil_impact=report.brazil_impact or "N/A",
            manipulation_risk=report.manipulation_risk or "Risco não avaliado",
            confidence_score=report.confidence_score,
            confidence_explanation=confidence_explanation,
            simple_explanation=report.simple_explanation or "N/A",
            short_term=short_term or "N/A",
            medium_term=medium_term or "N/A",
            extreme_risk=extreme_risk or "N/A",
            sources_count=report.sources_count,
            convergence_score=round(report.convergence_score, 1),
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M UTC")
        )

    def _format_confidence_explanation(
        self,
        score: int,
        breakdown: Dict
    ) -> str:
        """Formata explicação do score de confiabilidade"""
        # Classificação
        if score >= 85:
            classification = "MUITO ALTA ✅"
        elif score >= 70:
            classification = "ALTA ✅"
        elif score >= 50:
            classification = "MÉDIA ⚠️"
        elif score >= 30:
            classification = "BAIXA ⚠️"
        else:
            classification = "MUITO BAIXA ❌"

        parts = [f"Classificação: {classification}"]

        if breakdown:
            parts.append("\nDetalhamento:")
            for key, value in breakdown.items():
                if isinstance(value, dict) and "pontos" in value:
                    parts.append(f"  • {key}: {value['pontos']} pontos")

        return "\n".join(parts)

    def export_json(self, report: GeopoliticalReport) -> str:
        """Exporta relatório em JSON"""
        data = {
            "topic": report.topic,
            "generated_at": report.generated_at.isoformat(),
            "tldr": report.tldr,
            "what_happened": report.what_happened,
            "why_it_matters": report.why_it_matters,
            "winners_losers": report.winners_losers,
            "brazil_impact": report.brazil_impact,
            "manipulation_risk": report.manipulation_risk,
            "simple_explanation": report.simple_explanation,
            "future_scenarios": report.future_scenarios,
            "confidence_score": report.confidence_score,
            "confidence_breakdown": report.confidence_breakdown,
            "sources": report.sources,
            "sources_count": report.sources_count,
            "convergence_score": report.convergence_score,
            "bias_detected": report.bias_detected
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
