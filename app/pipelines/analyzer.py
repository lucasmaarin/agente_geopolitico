"""
Analisador via OpenAI - processa artigos usando GPT para análises avançadas
"""
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings
from app.utils.logger import LoggerMixin
from app.utils.cache import global_cache
from app.prompts.factual_summary import FACTUAL_SUMMARY_PROMPT, FACTUAL_SUMMARY_SYSTEM
from app.prompts.bias_detection import BIAS_DETECTION_PROMPT, BIAS_DETECTION_SYSTEM
from app.prompts.simple_explanation import SIMPLE_EXPLANATION_PROMPT, SIMPLE_EXPLANATION_SYSTEM
from app.prompts.confidence_score import CONFIDENCE_SCORE_PROMPT, CONFIDENCE_SCORE_SYSTEM
from app.prompts.scenario_projection import SCENARIO_PROJECTION_PROMPT, SCENARIO_PROJECTION_SYSTEM


@dataclass
class AnalysisResult:
    """Resultado de uma análise via OpenAI"""
    analysis_type: str
    content: Any
    model_used: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class OpenAIAnalyzer(LoggerMixin):
    """
    Analisador que usa OpenAI API para:
    - Resumo factual
    - Detecção de viés
    - Explicação simples
    - Score de confiabilidade
    - Projeção de cenários
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        json_response: bool = False
    ) -> AnalysisResult:
        """
        Faz uma chamada à API OpenAI.

        Args:
            system_prompt: Prompt de sistema
            user_prompt: Prompt do usuário
            json_response: Se deve forçar resposta em JSON

        Returns:
            AnalysisResult com o resultado
        """
        start_time = time.time()

        try:
            response_format = {"type": "json_object"} if json_response else {"type": "text"}

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format=response_format
            )

            latency_ms = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content

            if json_response:
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    self.logger.warning("Resposta não é JSON válido, retornando como texto")

            return AnalysisResult(
                analysis_type="openai_call",
                content=content,
                model_used=self.model,
                tokens_input=response.usage.prompt_tokens,
                tokens_output=response.usage.completion_tokens,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Erro na chamada OpenAI: {e}")

            return AnalysisResult(
                analysis_type="openai_call",
                content=None,
                model_used=self.model,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e)
            )

    def _format_articles_for_prompt(self, articles: List[Dict]) -> str:
        """Formata artigos para inclusão em prompts"""
        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(f"""
--- FONTE {i}: {article.get('source', 'Unknown')} ---
Título: {article.get('title', 'Sem título')}
URL: {article.get('url', '')}
Conteúdo:
{article.get('content', '')[:3000]}
---
""")
        return "\n".join(formatted)

    def generate_factual_summary(self, articles: List[Dict]) -> AnalysisResult:
        """
        Gera resumo factual neutro dos artigos.

        Args:
            articles: Lista de artigos com título, conteúdo e fonte

        Returns:
            AnalysisResult com o resumo
        """
        # Verificar cache
        cache_key = f"summary:{hash(str([a.get('url') for a in articles]))}"
        cached = global_cache.get(cache_key)
        if cached:
            return cached

        articles_content = self._format_articles_for_prompt(articles)
        prompt = FACTUAL_SUMMARY_PROMPT.format(articles_content=articles_content)

        result = self._call_openai(FACTUAL_SUMMARY_SYSTEM, prompt)
        result.analysis_type = "factual_summary"

        if result.success:
            global_cache.set(cache_key, result, ttl=settings.CACHE_TTL_SECONDS)

        return result

    def detect_bias(self, articles: List[Dict]) -> AnalysisResult:
        """
        Detecta viés e propaganda nos artigos.

        Args:
            articles: Lista de artigos

        Returns:
            AnalysisResult com análise de viés (JSON)
        """
        articles_content = self._format_articles_for_prompt(articles)
        prompt = BIAS_DETECTION_PROMPT.format(articles_content=articles_content)

        result = self._call_openai(BIAS_DETECTION_SYSTEM, prompt, json_response=True)
        result.analysis_type = "bias_detection"

        return result

    def generate_simple_explanation(
        self,
        technical_analysis: str,
        context: str = ""
    ) -> AnalysisResult:
        """
        Gera explicação simples para leigos.

        Args:
            technical_analysis: Análise técnica para simplificar
            context: Contexto adicional

        Returns:
            AnalysisResult com explicação simples
        """
        prompt = SIMPLE_EXPLANATION_PROMPT.format(
            technical_analysis=technical_analysis,
            context=context
        )

        result = self._call_openai(SIMPLE_EXPLANATION_SYSTEM, prompt)
        result.analysis_type = "simple_explanation"

        return result

    def calculate_confidence_score(
        self,
        sources: List[str],
        num_sources: int,
        factual_summary: str,
        bias_analysis: Dict
    ) -> AnalysisResult:
        """
        Calcula score de confiabilidade.

        Args:
            sources: Lista de nomes das fontes
            num_sources: Número de fontes
            factual_summary: Resumo factual gerado
            bias_analysis: Análise de viés

        Returns:
            AnalysisResult com score (JSON)
        """
        prompt = CONFIDENCE_SCORE_PROMPT.format(
            sources=", ".join(sources),
            num_sources=num_sources,
            factual_summary=factual_summary,
            bias_analysis=json.dumps(bias_analysis, ensure_ascii=False)
        )

        result = self._call_openai(CONFIDENCE_SCORE_SYSTEM, prompt, json_response=True)
        result.analysis_type = "confidence_score"

        return result

    def project_scenarios(
        self,
        base_analysis: str,
        main_actors: List[str],
        interests: str
    ) -> AnalysisResult:
        """
        Projeta cenários futuros.

        Args:
            base_analysis: Análise base do evento
            main_actors: Atores principais envolvidos
            interests: Interesses em jogo

        Returns:
            AnalysisResult com cenários (JSON)
        """
        prompt = SCENARIO_PROJECTION_PROMPT.format(
            base_analysis=base_analysis,
            main_actors=", ".join(main_actors),
            interests=interests
        )

        result = self._call_openai(SCENARIO_PROJECTION_SYSTEM, prompt, json_response=True)
        result.analysis_type = "scenario_projection"

        return result

    def full_analysis(self, articles: List[Dict]) -> Dict[str, AnalysisResult]:
        """
        Executa análise completa: resumo, viés, explicação, score e cenários.

        Args:
            articles: Lista de artigos para analisar

        Returns:
            Dicionário com todos os resultados de análise
        """
        results = {}

        # 1. Resumo factual
        self.logger.info("Gerando resumo factual...")
        results["factual_summary"] = self.generate_factual_summary(articles)

        if not results["factual_summary"].success:
            self.logger.error("Falha no resumo factual, abortando análise")
            return results

        # 2. Detecção de viés
        self.logger.info("Detectando viés...")
        results["bias_detection"] = self.detect_bias(articles)

        # 3. Explicação simples
        self.logger.info("Gerando explicação simples...")
        results["simple_explanation"] = self.generate_simple_explanation(
            technical_analysis=results["factual_summary"].content,
            context=f"Fontes: {', '.join([a.get('source', 'Unknown') for a in articles])}"
        )

        # 4. Score de confiabilidade
        self.logger.info("Calculando score de confiabilidade...")
        sources = [a.get("source", "Unknown") for a in articles]
        bias_data = results["bias_detection"].content if results["bias_detection"].success else {}

        results["confidence_score"] = self.calculate_confidence_score(
            sources=sources,
            num_sources=len(articles),
            factual_summary=results["factual_summary"].content,
            bias_analysis=bias_data
        )

        # 5. Projeção de cenários
        self.logger.info("Projetando cenários...")
        # Extrair atores do resumo (simplificado)
        actors = []
        for article in articles:
            if "countries" in article:
                actors.extend(article["countries"])
        actors = list(set(actors))[:5]  # Top 5 países

        results["scenarios"] = self.project_scenarios(
            base_analysis=results["factual_summary"].content,
            main_actors=actors if actors else ["Unknown"],
            interests="Análise baseada no conteúdo dos artigos"
        )

        self.logger.info("Análise completa finalizada")
        return results

    def get_usage_stats(self, results: Dict[str, AnalysisResult]) -> Dict:
        """Calcula estatísticas de uso da API"""
        total_input = sum(r.tokens_input for r in results.values() if r.success)
        total_output = sum(r.tokens_output for r in results.values() if r.success)
        total_latency = sum(r.latency_ms for r in results.values())

        # Estimativa de custo (GPT-4o prices: $5/1M input, $15/1M output)
        cost_input = (total_input / 1_000_000) * 5
        cost_output = (total_output / 1_000_000) * 15
        total_cost = cost_input + cost_output

        return {
            "total_tokens_input": total_input,
            "total_tokens_output": total_output,
            "total_latency_ms": total_latency,
            "estimated_cost_usd": round(total_cost, 4),
            "analyses_completed": sum(1 for r in results.values() if r.success),
            "analyses_failed": sum(1 for r in results.values() if not r.success)
        }
