"""
Módulo de banco de dados (Firestore)
"""
from .database import (
    get_db,
    init_db,
    get_firestore_client,
    get_collection,
    get_db_context,
    COLLECTIONS
)
from .models import Article, Report, Source, Event, AnalysisLog, ArticleStatus, ReportStatus
from .repositories import (
    SourceRepository,
    SourceConfigRepository,
    ArticleRepository,
    EventRepository,
    ReportRepository,
    AnalysisLogRepository
)

__all__ = [
    "get_db",
    "init_db",
    "get_firestore_client",
    "get_collection",
    "get_db_context",
    "COLLECTIONS",
    "Article",
    "Report",
    "Source",
    "Event",
    "AnalysisLog",
    "ArticleStatus",
    "ReportStatus",
    "SourceRepository",
    "SourceConfigRepository",
    "ArticleRepository",
    "EventRepository",
    "ReportRepository",
    "AnalysisLogRepository"
]
