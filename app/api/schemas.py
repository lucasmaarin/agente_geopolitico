"""
Schemas Pydantic para a API
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# Enums
class ReportStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SourceTypeEnum(str, Enum):
    NEWS = "news"
    ANALYSIS = "analysis"


# Request Schemas
class SearchRequest(BaseModel):
    """Request para busca de notícias"""
    topic: str = Field(..., min_length=2, max_length=200, description="Tema para buscar")
    sources: Optional[List[str]] = Field(default=None, description="Lista de fontes específicas")
    max_articles_per_source: int = Field(default=5, ge=1, le=20)
    days: int = Field(default=7, ge=1, le=30, description="Buscar artigos dos últimos N dias")


class ReportRequest(BaseModel):
    """Request para geração de relatório"""
    topic: str = Field(..., min_length=2, max_length=200, description="Tema do relatório")
    sources: Optional[List[str]] = Field(default=None, description="Fontes específicas a usar")
    min_sources: int = Field(default=3, ge=1, le=10, description="Mínimo de fontes requeridas")
    include_scenarios: bool = Field(default=True, description="Incluir projeção de cenários")
    language: str = Field(default="pt-br", description="Idioma do relatório")


# Response Schemas
class SourceInfo(BaseModel):
    """Informações de uma fonte"""
    key: str
    name: str
    url: str
    type: str
    reputation_score: float
    language: str
    region: str


class ArticleResponse(BaseModel):
    """Artigo retornado pela API"""
    id: Optional[str] = None
    source: str
    source_name: str
    title: str
    url: str
    content_preview: str = Field(description="Primeiros 500 caracteres do conteúdo")
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    language: str
    countries: List[str] = []
    topics: List[str] = []


class SearchResponse(BaseModel):
    """Resposta de busca de notícias"""
    topic: str
    articles_found: int
    sources_used: int
    articles: List[ArticleResponse]
    search_timestamp: datetime


class ConfidenceBreakdown(BaseModel):
    """Detalhamento do score de confiabilidade"""
    numero_fontes: Dict[str, Any]
    convergencia_factual: Dict[str, Any]
    reputacao_fontes: Dict[str, Any]
    linguagem_emocional: Dict[str, Any]
    dados_verificaveis: Dict[str, Any]
    risco_clickbait: Dict[str, Any]


class ScenarioResponse(BaseModel):
    """Cenário projetado"""
    titulo: str
    probabilidade: str
    descricao: str
    impacto_brasil: Optional[str] = None


class ReportResponse(BaseModel):
    """Relatório geopolítico completo"""
    id: Optional[str] = None
    topic: str
    generated_at: datetime

    # Seções principais
    tldr: str
    what_happened: str
    why_it_matters: str
    winners_losers: str
    brazil_impact: str
    manipulation_risk: str
    simple_explanation: str

    # Cenários
    short_term_scenario: Optional[ScenarioResponse] = None
    medium_term_scenario: Optional[ScenarioResponse] = None
    extreme_risk_scenario: Optional[ScenarioResponse] = None

    # Confiabilidade
    confidence_score: int
    confidence_classification: str
    confidence_breakdown: Optional[ConfidenceBreakdown] = None

    # Metadados
    sources_count: int
    convergence_score: float
    sources_used: List[SourceInfo]
    alerts: List[str] = []

    # Formato legível
    formatted_report: str = Field(description="Relatório formatado para exibição")


class EventResponse(BaseModel):
    """Evento geopolítico"""
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    countries: List[str] = []
    start_date: Optional[datetime] = None
    is_ongoing: bool = True
    severity: Optional[str] = None
    reports_count: int = 0


class EventListResponse(BaseModel):
    """Lista de eventos"""
    total: int
    events: List[EventResponse]


class HealthResponse(BaseModel):
    """Response do health check"""
    status: str
    version: str
    timestamp: datetime
    database: str
    openai_configured: bool
    scrapers_available: int


class StatsResponse(BaseModel):
    """Estatísticas do sistema"""
    total_articles: int
    total_reports: int
    total_events: int
    sources_active: int
    cache_stats: Dict[str, Any]
    last_24h: Dict[str, int]


class ErrorResponse(BaseModel):
    """Resposta de erro"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Responses para listagens
class SourceListResponse(BaseModel):
    """Lista de fontes disponíveis"""
    total: int
    sources: List[SourceInfo]


class ReportListResponse(BaseModel):
    """Lista de relatórios"""
    total: int
    reports: List[Dict[str, Any]]
