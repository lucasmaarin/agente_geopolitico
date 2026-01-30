"""
Rotas da API FastAPI
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import threading
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import settings, NEWS_SOURCES
from app.db.database import get_db
from app.db.repositories import ArticleRepository, ReportRepository, EventRepository, SourceRepository, SourceConfigRepository
from app.api.schemas import (
    SearchRequest, SearchResponse, ArticleResponse,
    ReportRequest, ReportResponse, ScenarioResponse,
    SourceListResponse, SourceInfo,
    EventListResponse, EventResponse,
    HealthResponse, StatsResponse, ErrorResponse,
    ReportListResponse
)
from app.api.dependencies import (
    get_geopolitical_service, GeopoliticalService,
    get_scraper_manager, ScraperManager
)
from app.utils.logger import get_logger
from app.utils.cache import global_cache


router = APIRouter()
logger = get_logger("api.routes")

# ============================================================================
# SISTEMA DE TAREFAS EM BACKGROUND
# ============================================================================
_tasks: Dict[str, Dict[str, Any]] = {}
_tasks_lock = threading.Lock()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retorna uma tarefa pelo ID"""
    with _tasks_lock:
        return _tasks.get(task_id)


def update_task(task_id: str, **kwargs):
    """Atualiza uma tarefa"""
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].update(kwargs)


def create_task(task_type: str, topic: str) -> str:
    """Cria uma nova tarefa e retorna o ID"""
    task_id = str(uuid.uuid4())[:8]
    with _tasks_lock:
        _tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "topic": topic,
            "status": "pending",
            "progress": 0,
            "message": "Iniciando...",
            "created_at": datetime.utcnow().isoformat(),
            "result": None,
            "error": None
        }
    return task_id


# Health & Info Endpoints
@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Verifica o status do sistema"""
    scraper_manager = get_scraper_manager()

    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION,
        timestamp=datetime.utcnow(),
        database="firestore",
        openai_configured=bool(settings.OPENAI_API_KEY),
        scrapers_available=len(scraper_manager.get_available_sources())
    )


@router.get("/sources", tags=["Fontes"])
async def list_sources(include_inactive: bool = Query(default=False)):
    """
    Lista todas as fontes de notícias disponíveis.

    - **include_inactive**: Se True, inclui fontes desativadas
    """
    # Primeiro, garantir que fontes do config existem no Firestore
    SourceConfigRepository.initialize_from_config(NEWS_SOURCES)

    # Buscar do Firestore
    sources_data = SourceConfigRepository.get_all_sources(include_inactive=include_inactive)

    sources = []
    for s in sources_data:
        sources.append({
            "key": s.get("key") or s.get("id"),
            "name": s.get("name", ""),
            "url": s.get("url", ""),
            "type": s.get("type", "news"),
            "reputation_score": s.get("reputation_score", 0),
            "language": s.get("language", "en"),
            "region": s.get("region", "global"),
            "is_active": s.get("is_active", True),
            "is_builtin": s.get("is_builtin", True)
        })

    return {
        "total": len(sources),
        "active": len([s for s in sources if s.get("is_active", True)]),
        "sources": sources
    }


@router.put("/sources/{source_key}/toggle", tags=["Fontes"])
async def toggle_source(source_key: str, is_active: bool = Query(...)):
    """
    Ativa ou desativa uma fonte.

    - **source_key**: Chave da fonte (ex: "reuters", "bbc")
    - **is_active**: True para ativar, False para desativar
    """
    result = SourceConfigRepository.toggle_source(source_key, is_active)

    if not result:
        raise HTTPException(status_code=404, detail=f"Fonte '{source_key}' não encontrada")

    return {
        "message": f"Fonte '{source_key}' {'ativada' if is_active else 'desativada'} com sucesso",
        "source": result
    }


@router.post("/sources", tags=["Fontes"])
async def add_custom_source(
    key: str = Query(..., description="Identificador único (ex: 'minha_fonte')"),
    name: str = Query(..., description="Nome da fonte"),
    url: str = Query(..., description="URL base da fonte"),
    source_type: str = Query(default="news", description="Tipo: news ou analysis"),
    language: str = Query(default="en", description="Idioma: en, pt-br, etc"),
    region: str = Query(default="global", description="Região: global, brazil, europe, etc"),
    reputation_score: float = Query(default=70, ge=0, le=100, description="Score de reputação (0-100)")
):
    """
    Adiciona uma nova fonte customizada.

    Fontes customizadas usam um scraper genérico (RSS/Atom).
    Para scrapers específicos, é necessário desenvolvimento adicional.
    """
    try:
        result = SourceConfigRepository.add_custom_source(
            key=key,
            name=name,
            url=url,
            source_type=source_type,
            language=language,
            region=region,
            reputation_score=reputation_score
        )

        return {
            "message": f"Fonte '{name}' adicionada com sucesso",
            "source": result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/sources/{source_key}", tags=["Fontes"])
async def update_source(
    source_key: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    reputation_score: Optional[float] = Query(default=None, ge=0, le=100)
):
    """
    Atualiza dados de uma fonte.

    Apenas fontes customizadas podem ter URL alterada.
    """
    updates = {}
    if name is not None:
        updates["name"] = name
    if url is not None:
        updates["url"] = url
    if reputation_score is not None:
        updates["reputation_score"] = reputation_score

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    result = SourceConfigRepository.update_source(source_key, **updates)

    if not result:
        raise HTTPException(status_code=404, detail=f"Fonte '{source_key}' não encontrada")

    return {
        "message": f"Fonte '{source_key}' atualizada com sucesso",
        "source": result
    }


@router.delete("/sources/{source_key}", tags=["Fontes"])
async def delete_source(source_key: str):
    """
    Remove uma fonte customizada.

    Fontes do sistema (builtin) não podem ser removidas.
    Use toggle para desativá-las.
    """
    try:
        result = SourceConfigRepository.delete_source(source_key)

        if not result:
            raise HTTPException(status_code=404, detail=f"Fonte '{source_key}' não encontrada")

        return {"message": f"Fonte '{source_key}' removida com sucesso"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=StatsResponse, tags=["Sistema"])
async def get_stats():
    """Retorna estatísticas do sistema"""
    return StatsResponse(
        total_articles=0,
        total_reports=0,
        total_events=0,
        sources_active=len(NEWS_SOURCES),
        cache_stats=global_cache.stats(),
        last_24h={
            "articles_collected": 0,
            "reports_generated": 0
        }
    )


# Search Endpoints
@router.post("/search", response_model=SearchResponse, tags=["Busca"])
async def search_news(
    request: SearchRequest,
    service: GeopoliticalService = Depends(get_geopolitical_service)
):
    """
    Busca notícias sobre um tema em múltiplas fontes.

    - **topic**: Tema para buscar (ex: "Ukraine war", "US elections")
    - **sources**: Lista opcional de fontes específicas
    - **max_articles_per_source**: Máximo de artigos por fonte (1-20)
    """
    try:
        logger.info(f"Buscando notícias sobre: {request.topic}")

        articles_by_source = service.search_topic(
            topic=request.topic,
            max_per_source=request.max_articles_per_source
        )

        # Converter para response
        articles = []
        for source_key, source_articles in articles_by_source.items():
            source_name = NEWS_SOURCES.get(source_key, {}).get("name", source_key)

            for article in source_articles:
                articles.append(ArticleResponse(
                    source=source_key,
                    source_name=source_name,
                    title=article.title,
                    url=article.url,
                    content_preview=article.content[:500] if article.content else "",
                    author=article.author,
                    published_at=article.published_at,
                    language=article.language,
                    countries=[],
                    topics=[]
                ))

        return SearchResponse(
            topic=request.topic,
            articles_found=len(articles),
            sources_used=len(articles_by_source),
            articles=articles,
            search_timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Report Endpoints
@router.post("/report", response_model=ReportResponse, tags=["Relatórios"])
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    service: GeopoliticalService = Depends(get_geopolitical_service)
):
    """
    Gera um relatório geopolítico completo sobre um tema.

    O relatório inclui:
    - Resumo factual neutro
    - Detecção de viés e propaganda
    - Score de confiabilidade
    - Explicação simples para leigos
    - Projeção de cenários futuros

    **Requer API key da OpenAI configurada para análises avançadas.**
    """
    try:
        logger.info(f"Gerando relatório sobre: {request.topic}")

        result = service.generate_report(
            topic=request.topic,
            min_sources=request.min_sources
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        report = result["report"]
        confidence = result["confidence"]

        # Converter cenários
        scenarios = report.future_scenarios or {}

        short_term = None
        if "cenario_curto_prazo" in scenarios:
            sc = scenarios["cenario_curto_prazo"]
            short_term = ScenarioResponse(
                titulo=sc.get("titulo", "N/A"),
                probabilidade=sc.get("probabilidade", "N/A"),
                descricao=sc.get("descricao", ""),
                impacto_brasil=sc.get("impacto_brasil")
            )

        medium_term = None
        if "cenario_medio_prazo" in scenarios:
            sc = scenarios["cenario_medio_prazo"]
            medium_term = ScenarioResponse(
                titulo=sc.get("titulo", "N/A"),
                probabilidade=sc.get("probabilidade", "N/A"),
                descricao=sc.get("descricao", ""),
                impacto_brasil=sc.get("impacto_brasil")
            )

        extreme_risk = None
        if "cenario_risco_extremo" in scenarios:
            sc = scenarios["cenario_risco_extremo"]
            extreme_risk = ScenarioResponse(
                titulo=sc.get("titulo", "N/A"),
                probabilidade=sc.get("probabilidade", "baixa"),
                descricao=sc.get("descricao", ""),
                impacto_brasil=sc.get("impacto_brasil")
            )

        # Converter fontes usadas
        sources_used = []
        for s in report.sources[:10]:
            sources_used.append(SourceInfo(
                key=s.get("key", ""),
                name=s.get("name", ""),
                url=s.get("url", ""),
                type="news",
                reputation_score=NEWS_SOURCES.get(s.get("key", ""), {}).get("reputation_score", 0),
                language="en",
                region="global"
            ))

        # Salvar relatório no Firestore
        try:
            saved_report = ReportRepository.create(
                topic=request.topic,
                tldr=report.tldr or "N/A",
                what_happened=report.what_happened or "N/A",
                why_it_matters=report.why_it_matters or "N/A",
                winners_losers=report.winners_losers or "N/A",
                brazil_impact=report.brazil_impact or "N/A",
                manipulation_risk=report.manipulation_risk or "N/A",
                simple_explanation=report.simple_explanation or "N/A",
                future_scenarios=report.future_scenarios or {},
                confidence_score=confidence.total_score,
                confidence_breakdown=confidence.to_dict() if hasattr(confidence, 'to_dict') else {},
                sources_count=report.sources_count,
                convergence_score=report.convergence_score,
                sources=[s.get("url", "") for s in report.sources[:10]],
                bias_detected=report.bias_detected if hasattr(report, 'bias_detected') else []
            )
            logger.info(f"Relatório salvo no Firestore com ID: {saved_report.get('id')}")
        except Exception as save_error:
            logger.error(f"Erro ao salvar relatório no Firestore: {save_error}")

        return ReportResponse(
            topic=request.topic,
            generated_at=report.generated_at,
            tldr=report.tldr or "N/A",
            what_happened=report.what_happened or "N/A",
            why_it_matters=report.why_it_matters or "N/A",
            winners_losers=report.winners_losers or "N/A",
            brazil_impact=report.brazil_impact or "N/A",
            manipulation_risk=report.manipulation_risk or "N/A",
            simple_explanation=report.simple_explanation or "N/A",
            short_term_scenario=short_term,
            medium_term_scenario=medium_term,
            extreme_risk_scenario=extreme_risk,
            confidence_score=confidence.total_score,
            confidence_classification=confidence.classification,
            confidence_breakdown=None,
            sources_count=report.sources_count,
            convergence_score=report.convergence_score,
            sources_used=sources_used,
            alerts=confidence.alerts,
            formatted_report=result["formatted"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DE TAREFAS ASSÍNCRONAS
# ============================================================================

def _run_report_generation(task_id: str, topic: str, min_sources: int):
    """Executa geração de relatório em background"""
    try:
        service = get_geopolitical_service()

        # Atualizar progresso
        update_task(task_id, status="running", progress=10, message="Coletando artigos de múltiplas fontes...")

        # Gerar relatório
        result = service.generate_report(topic=topic, min_sources=min_sources)

        if "error" in result:
            update_task(task_id, status="failed", progress=100, error=result["error"])
            return

        update_task(task_id, progress=80, message="Formatando relatório...")

        report = result["report"]
        confidence = result["confidence"]

        # Converter cenários
        scenarios = report.future_scenarios or {}

        def convert_scenario(key):
            if key in scenarios:
                sc = scenarios[key]
                return {
                    "titulo": sc.get("titulo", "N/A"),
                    "probabilidade": sc.get("probabilidade", "N/A"),
                    "descricao": sc.get("descricao", ""),
                    "impacto_brasil": sc.get("impacto_brasil")
                }
            return None

        # Converter fontes
        sources_used = []
        for s in report.sources[:10]:
            sources_used.append({
                "key": s.get("key", ""),
                "name": s.get("name", ""),
                "url": s.get("url", ""),
                "type": "news",
                "reputation_score": NEWS_SOURCES.get(s.get("key", ""), {}).get("reputation_score", 0),
                "language": "en",
                "region": "global"
            })

        # Resultado final
        report_data = {
            "topic": topic,
            "generated_at": report.generated_at.isoformat() if report.generated_at else datetime.utcnow().isoformat(),
            "tldr": report.tldr or "N/A",
            "what_happened": report.what_happened or "N/A",
            "why_it_matters": report.why_it_matters or "N/A",
            "winners_losers": report.winners_losers or "N/A",
            "brazil_impact": report.brazil_impact or "N/A",
            "manipulation_risk": report.manipulation_risk or "N/A",
            "simple_explanation": report.simple_explanation or "N/A",
            "short_term_scenario": convert_scenario("cenario_curto_prazo"),
            "medium_term_scenario": convert_scenario("cenario_medio_prazo"),
            "extreme_risk_scenario": convert_scenario("cenario_risco_extremo"),
            "confidence_score": confidence.total_score,
            "confidence_classification": confidence.classification,
            "confidence_breakdown": None,
            "sources_count": report.sources_count,
            "convergence_score": report.convergence_score,
            "sources_used": sources_used,
            "alerts": confidence.alerts,
            "formatted_report": result["formatted"]
        }

        # Salvar relatório no Firestore
        try:
            saved_report = ReportRepository.create(
                topic=topic,
                tldr=report.tldr or "N/A",
                what_happened=report.what_happened or "N/A",
                why_it_matters=report.why_it_matters or "N/A",
                winners_losers=report.winners_losers or "N/A",
                brazil_impact=report.brazil_impact or "N/A",
                manipulation_risk=report.manipulation_risk or "N/A",
                simple_explanation=report.simple_explanation or "N/A",
                future_scenarios=report.future_scenarios or {},
                confidence_score=confidence.total_score,
                confidence_breakdown=confidence.to_dict() if hasattr(confidence, 'to_dict') else {},
                sources_count=report.sources_count,
                convergence_score=report.convergence_score,
                sources=[s.get("url", "") for s in report.sources[:10]],
                bias_detected=report.bias_detected if hasattr(report, 'bias_detected') else []
            )
            report_data["id"] = saved_report.get("id")
            logger.info(f"Relatório salvo no Firestore com ID: {saved_report.get('id')}")
        except Exception as save_error:
            logger.error(f"Erro ao salvar relatório no Firestore: {save_error}")

        update_task(task_id, status="completed", progress=100, message="Relatório gerado com sucesso!", result=report_data)
        logger.info(f"Tarefa {task_id} concluída com sucesso")

    except Exception as e:
        logger.error(f"Erro na tarefa {task_id}: {e}\n{traceback.format_exc()}")
        update_task(task_id, status="failed", progress=100, error=str(e))


@router.post("/report/async", tags=["Relatórios"])
async def generate_report_async(
    request: ReportRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia geração de relatório em background.

    Retorna um task_id que pode ser usado para verificar o status.
    Use GET /tasks/{task_id} para verificar o progresso.
    """
    task_id = create_task("report", request.topic)

    # Executar em thread separada
    thread = threading.Thread(
        target=_run_report_generation,
        args=(task_id, request.topic, request.min_sources)
    )
    thread.daemon = True
    thread.start()

    logger.info(f"Tarefa {task_id} iniciada para tema: {request.topic}")

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Tarefa iniciada. Use GET /tasks/{task_id} para verificar o progresso."
    }


@router.get("/tasks/{task_id}", tags=["Tarefas"])
async def get_task_status(task_id: str):
    """
    Verifica o status de uma tarefa em background.

    Status possíveis:
    - pending: Aguardando início
    - running: Em execução
    - completed: Concluído com sucesso (result contém o relatório)
    - failed: Falhou (error contém a mensagem de erro)
    """
    task = get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    return task


@router.get("/reports", response_model=ReportListResponse, tags=["Relatórios"])
async def list_reports(
    limit: int = Query(default=20, ge=1, le=100)
):
    """Lista relatórios gerados anteriormente"""
    reports = ReportRepository.get_all(limit=limit)

    return ReportListResponse(
        total=len(reports),
        reports=[
            {
                "id": r.get("id"),
                "topic": r.get("topic"),
                "confidence_score": r.get("confidence_score"),
                "sources_count": r.get("sources_count"),
                "generated_at": r.get("generated_at").isoformat() if r.get("generated_at") else None,
                "status": r.get("status", "draft")
            }
            for r in reports
        ]
    )


@router.get("/reports/{report_id}", tags=["Relatórios"])
async def get_report(report_id: str):
    """Obtém um relatório específico pelo ID"""
    report = ReportRepository.get_by_id(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    return {
        "id": report.get("id"),
        "topic": report.get("topic"),
        "tldr": report.get("tldr"),
        "what_happened": report.get("what_happened"),
        "why_it_matters": report.get("why_it_matters"),
        "winners_losers": report.get("winners_losers"),
        "brazil_impact": report.get("brazil_impact"),
        "manipulation_risk": report.get("manipulation_risk"),
        "simple_explanation": report.get("simple_explanation"),
        "future_scenarios": report.get("future_scenarios"),
        "confidence_score": report.get("confidence_score"),
        "confidence_breakdown": report.get("confidence_breakdown"),
        "sources_count": report.get("sources_count"),
        "convergence_score": report.get("convergence_score"),
        "generated_at": report.get("generated_at").isoformat() if report.get("generated_at") else None
    }


# Events Endpoints
@router.get("/events", response_model=EventListResponse, tags=["Eventos"])
async def list_events(
    ongoing_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100)
):
    """Lista eventos geopolíticos identificados"""
    events = EventRepository.get_all(ongoing_only=ongoing_only, limit=limit)

    return EventListResponse(
        total=len(events),
        events=[
            EventResponse(
                id=e.get("id"),
                title=e.get("title"),
                description=e.get("description"),
                event_type=e.get("event_type"),
                countries=e.get("countries") or [],
                start_date=e.get("start_date"),
                is_ongoing=e.get("is_ongoing", True),
                severity=e.get("severity", "medium"),
                reports_count=0
            )
            for e in events
        ]
    )


@router.get("/events/{event_id}", response_model=EventResponse, tags=["Eventos"])
async def get_event(event_id: str):
    """Obtém detalhes de um evento específico"""
    event = EventRepository.get_by_id(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    return EventResponse(
        id=event.get("id"),
        title=event.get("title"),
        description=event.get("description"),
        event_type=event.get("event_type"),
        countries=event.get("countries") or [],
        start_date=event.get("start_date"),
        is_ongoing=event.get("is_ongoing", True),
        severity=event.get("severity", "medium"),
        reports_count=0
    )
