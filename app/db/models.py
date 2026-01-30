"""
Modelos de dados para Firestore (documentos)
Usa dataclasses para representar a estrutura dos documentos.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ArticleStatus(str, Enum):
    """Status de processamento do artigo"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ReportStatus(str, Enum):
    """Status do relatório"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass
class Source:
    """
    Modelo para fontes de notícias.
    Coleção: {prefix}_sources
    Documento ID: key (ex: "reuters", "bbc")
    """
    key: str
    name: str
    url: str
    type: str = "news"  # news, analysis
    reputation_score: float = 80.0
    language: str = "en"
    region: str = "global"
    is_active: bool = True
    last_scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ID do documento (preenchido ao ler do Firestore)
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário compatível com Firestore"""
        data = asdict(self)
        data.pop("id", None)  # Remove id pois é o document ID
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str = None) -> "Source":
        """Cria instância a partir de dicionário do Firestore"""
        if doc_id:
            data["id"] = doc_id
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Article:
    """
    Modelo para artigos coletados.
    Coleção: {prefix}_articles
    """
    title: str
    url: str
    source_id: str  # Referência para a fonte (document ID)
    content: str = ""
    raw_content: str = ""
    external_id: str = ""  # URL ou ID único da fonte
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    language: str = "en"

    # Metadados extraídos
    countries: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0

    # Status
    status: str = ArticleStatus.PENDING.value
    error_message: Optional[str] = None

    # Timestamps
    scraped_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ID do documento
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário compatível com Firestore"""
        data = asdict(self)
        data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str = None) -> "Article":
        """Cria instância a partir de dicionário do Firestore"""
        if doc_id:
            data["id"] = doc_id
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Event:
    """
    Modelo para eventos geopolíticos identificados.
    Coleção: {prefix}_events
    """
    title: str
    description: str = ""
    event_type: str = ""  # conflict, diplomacy, trade, etc.
    countries: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_ongoing: bool = True
    severity: str = "medium"  # low, medium, high, critical
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ID do documento
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário compatível com Firestore"""
        data = asdict(self)
        data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str = None) -> "Event":
        """Cria instância a partir de dicionário do Firestore"""
        if doc_id:
            data["id"] = doc_id
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Report:
    """
    Modelo para relatórios geopolíticos gerados.
    Coleção: {prefix}_reports
    """
    topic: str

    # Seções do relatório
    tldr: str = ""
    what_happened: str = ""
    why_it_matters: str = ""
    winners_losers: str = ""
    brazil_impact: str = ""
    manipulation_risk: str = ""
    simple_explanation: str = ""
    future_scenarios: Dict[str, Any] = field(default_factory=dict)

    # Score de confiabilidade
    confidence_score: float = 0.0
    confidence_breakdown: Dict[str, Any] = field(default_factory=dict)

    # Metadados
    event_id: Optional[str] = None  # Referência para evento
    sources_count: int = 0
    convergence_score: float = 0.0
    bias_detected: List[Dict] = field(default_factory=list)
    article_ids: List[str] = field(default_factory=list)  # Lista de IDs de artigos

    # Status
    status: str = ReportStatus.DRAFT.value
    version: int = 1

    # Timestamps
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ID do documento
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário compatível com Firestore"""
        data = asdict(self)
        data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str = None) -> "Report":
        """Cria instância a partir de dicionário do Firestore"""
        if doc_id:
            data["id"] = doc_id
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AnalysisLog:
    """
    Log de análises realizadas pela OpenAI.
    Coleção: {prefix}_analysis_logs
    """
    analysis_type: str  # summary, bias, explanation, etc.
    report_id: Optional[str] = None
    prompt_used: str = ""
    response: str = ""
    model_used: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    # ID do documento
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário compatível com Firestore"""
        data = asdict(self)
        data.pop("id", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], doc_id: str = None) -> "AnalysisLog":
        """Cria instância a partir de dicionário do Firestore"""
        if doc_id:
            data["id"] = doc_id
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Mapeamento de modelos para nomes de coleções
MODEL_COLLECTIONS = {
    Source: "sources",
    Article: "articles",
    Event: "events",
    Report: "reports",
    AnalysisLog: "analysis_logs"
}
