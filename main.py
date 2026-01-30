"""
Entry point da aplicação FastAPI
Agente de Inteligência Geopolítica Anti-Fake News
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from contextlib import asynccontextmanager

from config import settings
from app.api.routes import router
from app.db.database import init_db
from app.utils.logger import setup_logger

from frontend.app import app as flask_app


# Configurar logger
logger = setup_logger(
    name="geopolitica",
    log_file=settings.LOGS_DIR / "app.log"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("Inicializando aplicação...")
    logger.info(f"Versão: {settings.API_VERSION}")
    logger.info(f"Debug: {settings.DEBUG}")

    # Inicializar banco de dados
    init_db()
    logger.info("Banco de dados inicializado")

    # Verificar configuração OpenAI
    if settings.OPENAI_API_KEY:
        logger.info("OpenAI API configurada")
    else:
        logger.warning("OPENAI_API_KEY não configurada - análises avançadas desabilitadas")

    yield

    # Shutdown
    logger.info("Encerrando aplicação...")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description="""
    ## Agente de Inteligência Geopolítica Anti-Fake News

    API para coleta, análise e síntese de informações geopolíticas de múltiplas fontes confiáveis.

    ### Funcionalidades principais:

    * 📰 **Busca de notícias** - Coleta artigos de 13+ fontes internacionais
    * 📊 **Relatórios inteligentes** - Análise cruzada com detecção de viés
    * 🔍 **Score de confiabilidade** - Avaliação de 0-100 baseada em múltiplos critérios
    * 🇧🇷 **Contexto brasileiro** - Impactos analisados para o Brasil
    * 👩‍🏫 **Explicação para leigos** - Versão didática de cada análise

    ### Fontes de dados:

    **Notícias:** Reuters, AP News, BBC, DW, Al Jazeera

    **Análise:** Foreign Affairs, CSIS, CFR, Crisis Group, RAND

    **Brasil:** Nexo, BBC Brasil, Poder360
    """,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir para domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(router, prefix=settings.API_PREFIX)


# Rota raiz
@app.get("/api", tags=["Root"])
async def root():
    """Informações básicas da API"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "ui": "/",
        "health": f"{settings.API_PREFIX}/health"
    }


# Montar frontend Flask no mesmo servidor
app.mount("/", WSGIMiddleware(flask_app))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
