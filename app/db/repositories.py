"""
Repositórios para operações CRUD no Firestore
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud.firestore_v1 import FieldFilter, Query

from .database import (
    get_collection, get_firestore_client, server_timestamp,
    document_to_dict, query_to_list, COLLECTIONS
)
from .models import (
    Source, Article, Event, Report,
    AnalysisLog, ArticleStatus, ReportStatus
)


class SourceRepository:
    """Repositório para operações com fontes"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["sources"])

    @staticmethod
    def get_all(active_only: bool = True) -> List[Dict]:
        """Retorna todas as fontes"""
        query = SourceRepository._collection()
        if active_only:
            query = query.where(filter=FieldFilter("is_active", "==", True))
        docs = query.stream()
        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def get_by_key(key: str) -> Optional[Dict]:
        """Retorna fonte pelo key (document ID)"""
        doc = SourceRepository._collection().document(key).get()
        return document_to_dict(doc)

    @staticmethod
    def get_by_id(source_id: str) -> Optional[Dict]:
        """Alias para get_by_key"""
        return SourceRepository.get_by_key(source_id)

    @staticmethod
    def create(**kwargs) -> Dict:
        """Cria nova fonte"""
        key = kwargs.pop("key", None)
        if not key:
            raise ValueError("key é obrigatório para criar fonte")

        kwargs["created_at"] = server_timestamp()
        kwargs["updated_at"] = server_timestamp()

        doc_ref = SourceRepository._collection().document(key)
        doc_ref.set(kwargs)

        return {"id": key, **kwargs}

    @staticmethod
    def update(source_id: str, **kwargs) -> Optional[Dict]:
        """Atualiza fonte existente"""
        kwargs["updated_at"] = server_timestamp()
        doc_ref = SourceRepository._collection().document(source_id)
        doc_ref.update(kwargs)
        return SourceRepository.get_by_key(source_id)

    @staticmethod
    def update_last_scraped(source_id: str) -> None:
        """Atualiza timestamp de última coleta"""
        doc_ref = SourceRepository._collection().document(source_id)
        doc_ref.update({
            "last_scraped_at": server_timestamp(),
            "updated_at": server_timestamp()
        })

    @staticmethod
    def get_by_region(region: str) -> List[Dict]:
        """Retorna fontes por região"""
        docs = SourceRepository._collection().where(
            filter=FieldFilter("region", "==", region)
        ).where(
            filter=FieldFilter("is_active", "==", True)
        ).stream()
        return [document_to_dict(doc) for doc in docs]


class ArticleRepository:
    """Repositório para operações com artigos"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["articles"])

    @staticmethod
    def get_by_id(article_id: str) -> Optional[Dict]:
        """Retorna artigo pelo ID"""
        doc = ArticleRepository._collection().document(article_id).get()
        return document_to_dict(doc)

    @staticmethod
    def get_by_url(url: str) -> Optional[Dict]:
        """Retorna artigo pela URL"""
        docs = ArticleRepository._collection().where(
            filter=FieldFilter("url", "==", url)
        ).limit(1).stream()

        for doc in docs:
            return document_to_dict(doc)
        return None

    @staticmethod
    def exists(url: str) -> bool:
        """Verifica se artigo existe pela URL"""
        return ArticleRepository.get_by_url(url) is not None

    @staticmethod
    def create(**kwargs) -> Dict:
        """Cria novo artigo"""
        kwargs["created_at"] = server_timestamp()
        kwargs["updated_at"] = server_timestamp()
        kwargs["scraped_at"] = kwargs.get("scraped_at") or server_timestamp()

        # Gerar ID automático
        doc_ref = ArticleRepository._collection().document()
        doc_ref.set(kwargs)

        return {"id": doc_ref.id, **kwargs}

    @staticmethod
    def bulk_create(articles: List[Dict[str, Any]]) -> List[Dict]:
        """Cria múltiplos artigos em batch"""
        batch = get_firestore_client().batch()
        results = []

        for article_data in articles:
            article_data["created_at"] = server_timestamp()
            article_data["updated_at"] = server_timestamp()
            article_data["scraped_at"] = article_data.get("scraped_at") or server_timestamp()

            doc_ref = ArticleRepository._collection().document()
            batch.set(doc_ref, article_data)
            results.append({"id": doc_ref.id, **article_data})

        batch.commit()
        return results

    @staticmethod
    def update_status(
        article_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Atualiza status do artigo"""
        update_data = {
            "status": status,
            "updated_at": server_timestamp()
        }
        if status == ArticleStatus.COMPLETED.value:
            update_data["processed_at"] = server_timestamp()
        if error_message:
            update_data["error_message"] = error_message

        ArticleRepository._collection().document(article_id).update(update_data)

    @staticmethod
    def search(
        query_text: str,
        source_ids: Optional[List[str]] = None,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict]:
        """
        Busca artigos por texto.
        Nota: Firestore não suporta full-text search nativo.
        Para produção, considere usar Algolia ou Elasticsearch.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Query básica por data
        query = ArticleRepository._collection().where(
            filter=FieldFilter("created_at", ">=", cutoff)
        ).order_by("created_at", direction=Query.DESCENDING).limit(limit)

        docs = list(query.stream())
        results = []

        # Filtro manual por texto (não ideal, mas funcional)
        query_lower = query_text.lower()
        for doc in docs:
            data = document_to_dict(doc)
            title = (data.get("title") or "").lower()
            content = (data.get("content") or "").lower()

            if query_lower in title or query_lower in content:
                if source_ids is None or data.get("source_id") in source_ids:
                    results.append(data)

        return results[:limit]

    @staticmethod
    def get_recent(hours: int = 24, limit: int = 100) -> List[Dict]:
        """Retorna artigos recentes"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        docs = ArticleRepository._collection().where(
            filter=FieldFilter("created_at", ">=", cutoff)
        ).order_by("created_at", direction=Query.DESCENDING).limit(limit).stream()

        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def get_by_topic(topic: str, days: int = 7, limit: int = 50) -> List[Dict]:
        """Retorna artigos por tópico"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        docs = ArticleRepository._collection().where(
            filter=FieldFilter("created_at", ">=", cutoff)
        ).where(
            filter=FieldFilter("topics", "array_contains", topic)
        ).order_by("created_at", direction=Query.DESCENDING).limit(limit).stream()

        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def get_pending(limit: int = 100) -> List[Dict]:
        """Retorna artigos pendentes de processamento"""
        docs = ArticleRepository._collection().where(
            filter=FieldFilter("status", "==", ArticleStatus.PENDING.value)
        ).limit(limit).stream()

        return [document_to_dict(doc) for doc in docs]


class EventRepository:
    """Repositório para operações com eventos"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["events"])

    @staticmethod
    def get_by_id(event_id: str) -> Optional[Dict]:
        """Retorna evento pelo ID"""
        doc = EventRepository._collection().document(event_id).get()
        return document_to_dict(doc)

    @staticmethod
    def get_all(ongoing_only: bool = False, limit: int = 50) -> List[Dict]:
        """Retorna todos os eventos"""
        query = EventRepository._collection()
        if ongoing_only:
            query = query.where(filter=FieldFilter("is_ongoing", "==", True))

        docs = query.order_by("updated_at", direction=Query.DESCENDING).limit(limit).stream()
        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def create(**kwargs) -> Dict:
        """Cria novo evento"""
        kwargs["created_at"] = server_timestamp()
        kwargs["updated_at"] = server_timestamp()

        doc_ref = EventRepository._collection().document()
        doc_ref.set(kwargs)

        return {"id": doc_ref.id, **kwargs}

    @staticmethod
    def update(event_id: str, **kwargs) -> Optional[Dict]:
        """Atualiza evento existente"""
        kwargs["updated_at"] = server_timestamp()
        EventRepository._collection().document(event_id).update(kwargs)
        return EventRepository.get_by_id(event_id)

    @staticmethod
    def search_by_country(country: str) -> List[Dict]:
        """Busca eventos por país"""
        docs = EventRepository._collection().where(
            filter=FieldFilter("countries", "array_contains", country)
        ).order_by("start_date", direction=Query.DESCENDING).stream()

        return [document_to_dict(doc) for doc in docs]


class ReportRepository:
    """Repositório para operações com relatórios"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["reports"])

    @staticmethod
    def get_by_id(report_id: str) -> Optional[Dict]:
        """Retorna relatório pelo ID"""
        doc = ReportRepository._collection().document(report_id).get()
        return document_to_dict(doc)

    @staticmethod
    def get_all(status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Retorna todos os relatórios"""
        query = ReportRepository._collection()
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))

        docs = query.order_by("generated_at", direction=Query.DESCENDING).limit(limit).stream()
        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def create(**kwargs) -> Dict:
        """Cria novo relatório"""
        kwargs["created_at"] = server_timestamp()
        kwargs["updated_at"] = server_timestamp()
        kwargs["generated_at"] = kwargs.get("generated_at") or server_timestamp()

        doc_ref = ReportRepository._collection().document()
        doc_ref.set(kwargs)

        return {"id": doc_ref.id, **kwargs}

    @staticmethod
    def update(report_id: str, **kwargs) -> Optional[Dict]:
        """Atualiza relatório existente"""
        kwargs["updated_at"] = server_timestamp()
        ReportRepository._collection().document(report_id).update(kwargs)
        return ReportRepository.get_by_id(report_id)

    @staticmethod
    def search_by_topic(topic: str, limit: int = 20) -> List[Dict]:
        """
        Busca relatórios por tópico.
        Nota: Busca exata, não parcial (limitação do Firestore)
        """
        docs = ReportRepository._collection().where(
            filter=FieldFilter("topic", "==", topic)
        ).order_by("generated_at", direction=Query.DESCENDING).limit(limit).stream()

        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def add_article(report_id: str, article_id: str, relevance_score: float = 1.0) -> None:
        """Adiciona artigo ao relatório (atualiza lista de article_ids)"""
        from google.cloud.firestore_v1 import ArrayUnion

        ReportRepository._collection().document(report_id).update({
            "article_ids": ArrayUnion([article_id]),
            "updated_at": server_timestamp()
        })

    @staticmethod
    def get_articles(report_id: str) -> List[Dict]:
        """Retorna artigos associados ao relatório"""
        report = ReportRepository.get_by_id(report_id)
        if not report:
            return []

        article_ids = report.get("article_ids", [])
        articles = []

        for article_id in article_ids:
            article = ArticleRepository.get_by_id(article_id)
            if article:
                articles.append(article)

        return articles

    @staticmethod
    def publish(report_id: str) -> Optional[Dict]:
        """Publica um relatório"""
        return ReportRepository.update(
            report_id,
            status=ReportStatus.PUBLISHED.value,
            published_at=server_timestamp()
        )


class SourceConfigRepository:
    """Repositório para configuração dinâmica de fontes"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["sources"])

    @staticmethod
    def initialize_from_config(news_sources: Dict[str, Any]) -> int:
        """
        Inicializa fontes do config.py no Firestore se não existirem.
        Retorna número de fontes criadas.
        """
        created = 0
        for key, info in news_sources.items():
            doc_ref = SourceConfigRepository._collection().document(key)
            doc = doc_ref.get()

            if not doc.exists:
                doc_ref.set({
                    "key": key,
                    "name": info.get("name", key),
                    "url": info.get("url", ""),
                    "type": info.get("type", "news"),
                    "reputation_score": info.get("reputation_score", 50),
                    "language": info.get("language", "en"),
                    "region": info.get("region", "global"),
                    "is_active": True,
                    "is_builtin": True,  # Fonte do sistema
                    "created_at": server_timestamp(),
                    "updated_at": server_timestamp()
                })
                created += 1

        return created

    @staticmethod
    def get_all_sources(include_inactive: bool = False) -> List[Dict]:
        """Retorna todas as fontes configuradas"""
        query = SourceConfigRepository._collection()
        if not include_inactive:
            query = query.where(filter=FieldFilter("is_active", "==", True))
        docs = query.stream()
        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def get_active_source_keys() -> List[str]:
        """Retorna apenas as chaves das fontes ativas"""
        docs = SourceConfigRepository._collection().where(
            filter=FieldFilter("is_active", "==", True)
        ).stream()
        return [doc.id for doc in docs]

    @staticmethod
    def toggle_source(key: str, is_active: bool) -> Optional[Dict]:
        """Ativa ou desativa uma fonte"""
        doc_ref = SourceConfigRepository._collection().document(key)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        doc_ref.update({
            "is_active": is_active,
            "updated_at": server_timestamp()
        })

        return document_to_dict(doc_ref.get())

    @staticmethod
    def add_custom_source(
        key: str,
        name: str,
        url: str,
        source_type: str = "news",
        language: str = "en",
        region: str = "global",
        reputation_score: float = 70
    ) -> Dict:
        """Adiciona uma fonte customizada"""
        doc_ref = SourceConfigRepository._collection().document(key)

        if doc_ref.get().exists:
            raise ValueError(f"Fonte com key '{key}' já existe")

        data = {
            "key": key,
            "name": name,
            "url": url,
            "type": source_type,
            "reputation_score": reputation_score,
            "language": language,
            "region": region,
            "is_active": True,
            "is_builtin": False,  # Fonte customizada
            "created_at": server_timestamp(),
            "updated_at": server_timestamp()
        }

        doc_ref.set(data)
        return {"id": key, **data}

    @staticmethod
    def update_source(key: str, **kwargs) -> Optional[Dict]:
        """Atualiza dados de uma fonte"""
        doc_ref = SourceConfigRepository._collection().document(key)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        # Não permitir alterar certos campos
        kwargs.pop("key", None)
        kwargs.pop("is_builtin", None)
        kwargs.pop("created_at", None)

        kwargs["updated_at"] = server_timestamp()
        doc_ref.update(kwargs)

        return document_to_dict(doc_ref.get())

    @staticmethod
    def delete_source(key: str) -> bool:
        """Remove uma fonte customizada (não permite remover builtin)"""
        doc_ref = SourceConfigRepository._collection().document(key)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("is_builtin", True):
            raise ValueError("Não é possível remover fontes do sistema")

        doc_ref.delete()
        return True

    @staticmethod
    def get_source(key: str) -> Optional[Dict]:
        """Retorna uma fonte específica"""
        doc = SourceConfigRepository._collection().document(key).get()
        return document_to_dict(doc)


class AnalysisLogRepository:
    """Repositório para logs de análise"""

    @staticmethod
    def _collection():
        return get_collection(COLLECTIONS["analysis_logs"])

    @staticmethod
    def create(**kwargs) -> Dict:
        """Cria novo log de análise"""
        kwargs["created_at"] = server_timestamp()

        doc_ref = AnalysisLogRepository._collection().document()
        doc_ref.set(kwargs)

        return {"id": doc_ref.id, **kwargs}

    @staticmethod
    def get_by_report(report_id: str) -> List[Dict]:
        """Retorna logs de um relatório"""
        docs = AnalysisLogRepository._collection().where(
            filter=FieldFilter("report_id", "==", report_id)
        ).order_by("created_at").stream()

        return [document_to_dict(doc) for doc in docs]

    @staticmethod
    def get_total_cost(days: int = 30) -> float:
        """Calcula custo total em USD nos últimos N dias"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        docs = AnalysisLogRepository._collection().where(
            filter=FieldFilter("created_at", ">=", cutoff)
        ).where(
            filter=FieldFilter("success", "==", True)
        ).stream()

        total = sum(doc.to_dict().get("cost_usd", 0) or 0 for doc in docs)
        return total

    @staticmethod
    def get_stats(days: int = 30) -> Dict[str, Any]:
        """Retorna estatísticas de uso"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        docs = list(AnalysisLogRepository._collection().where(
            filter=FieldFilter("created_at", ">=", cutoff)
        ).stream())

        if not docs:
            return {
                "total_analyses": 0,
                "success_rate": 0,
                "total_cost": 0,
                "avg_latency_ms": 0
            }

        logs = [doc.to_dict() for doc in docs]
        successful = [l for l in logs if l.get("success")]

        return {
            "total_analyses": len(logs),
            "success_rate": len(successful) / len(logs) * 100 if logs else 0,
            "total_cost": sum(l.get("cost_usd", 0) or 0 for l in logs),
            "avg_latency_ms": (
                sum(l.get("latency_ms", 0) or 0 for l in successful) / len(successful)
                if successful else 0
            )
        }
