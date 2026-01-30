"""
Configuração e conexão com Firebase/Firestore
"""
import os
from contextlib import contextmanager
from typing import Optional, Generator
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Client

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings, NEWS_SOURCES
from app.utils.logger import get_logger


logger = get_logger("database")

# Instância global do cliente Firestore
_firestore_client: Optional[Client] = None
_firebase_app: Optional[firebase_admin.App] = None


def init_firebase() -> None:
    """
    Inicializa a conexão com o Firebase/Firestore.
    Deve ser chamado uma vez na inicialização da aplicação.
    """
    global _firebase_app, _firestore_client

    if _firebase_app is not None:
        logger.info("Firebase já inicializado")
        return

    try:
        cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)

        if not cred_path.exists():
            logger.warning(
                f"Arquivo de credenciais não encontrado: {cred_path}. "
                "Tentando usar credenciais padrão do ambiente."
            )
            # Tenta usar Application Default Credentials
            _firebase_app = firebase_admin.initialize_app()
        else:
            cred = credentials.Certificate(str(cred_path))
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': settings.FIREBASE_PROJECT_ID
            })

        _firestore_client = firestore.client()
        logger.info("Firebase/Firestore inicializado com sucesso")

        # Inicializar coleções padrão
        _initialize_default_collections()

    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase: {e}")
        raise


def get_firestore_client() -> Client:
    """
    Retorna o cliente Firestore.
    Inicializa se ainda não foi inicializado.
    """
    global _firestore_client

    if _firestore_client is None:
        init_firebase()

    return _firestore_client


def get_collection(collection_name: str):
    """
    Retorna uma referência para uma coleção com prefixo configurado.

    Args:
        collection_name: Nome da coleção (sem prefixo)

    Returns:
        Referência da coleção no Firestore
    """
    client = get_firestore_client()
    full_name = f"{settings.FIRESTORE_COLLECTION_PREFIX}_{collection_name}"
    return client.collection(full_name)


# Nomes das coleções
COLLECTIONS = {
    "sources": "sources",
    "articles": "articles",
    "events": "events",
    "reports": "reports",
    "analysis_logs": "analysis_logs"
}


def _initialize_default_collections() -> None:
    """
    Inicializa as coleções padrão com as fontes de notícias.
    """
    try:
        sources_ref = get_collection(COLLECTIONS["sources"])

        # Verificar se já existem fontes
        existing = list(sources_ref.limit(1).stream())
        if existing:
            logger.debug("Fontes já inicializadas")
            return

        # Inserir fontes padrão
        batch = get_firestore_client().batch()

        for key, source_data in NEWS_SOURCES.items():
            doc_ref = sources_ref.document(key)
            batch.set(doc_ref, {
                "key": key,
                "name": source_data["name"],
                "url": source_data["url"],
                "type": source_data["type"],
                "reputation_score": source_data["reputation_score"],
                "language": source_data["language"],
                "region": source_data["region"],
                "is_active": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_scraped_at": None
            })

        batch.commit()
        logger.info(f"Inicializadas {len(NEWS_SOURCES)} fontes de notícias")

    except Exception as e:
        logger.error(f"Erro ao inicializar coleções: {e}")


@contextmanager
def get_db_context() -> Generator[Client, None, None]:
    """
    Context manager para operações no Firestore.
    Mantido para compatibilidade com código existente.

    Uso:
        with get_db_context() as db:
            # operações no db
    """
    try:
        client = get_firestore_client()
        yield client
    except Exception as e:
        logger.error(f"Erro no contexto do Firestore: {e}")
        raise


def get_db() -> Generator:
    """
    Dependency para injeção do cliente Firestore no FastAPI.

    Uso:
        @app.get("/items")
        def read_items(db = Depends(get_db)):
            ...
    """
    client = get_firestore_client()
    yield client


def init_db() -> None:
    """
    Função de inicialização do banco de dados.
    Alias para init_firebase() para compatibilidade.
    """
    init_firebase()


def close_db() -> None:
    """
    Fecha a conexão com o Firebase.
    """
    global _firebase_app, _firestore_client

    if _firebase_app is not None:
        firebase_admin.delete_app(_firebase_app)
        _firebase_app = None
        _firestore_client = None
        logger.info("Conexão Firebase fechada")


# Funções utilitárias para Firestore

def server_timestamp():
    """Retorna o timestamp do servidor Firestore"""
    return firestore.SERVER_TIMESTAMP


def document_to_dict(doc) -> dict:
    """
    Converte um documento Firestore para dicionário.

    Args:
        doc: Documento do Firestore

    Returns:
        Dicionário com os dados do documento + id
    """
    if not doc.exists:
        return None

    data = doc.to_dict()
    data["id"] = doc.id
    return data


def query_to_list(query_result) -> list:
    """
    Converte resultado de query para lista de dicionários.

    Args:
        query_result: Resultado de uma query Firestore

    Returns:
        Lista de dicionários
    """
    return [document_to_dict(doc) for doc in query_result]
