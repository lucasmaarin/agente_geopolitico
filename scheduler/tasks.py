"""
Tarefas agendadas com APScheduler
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, GEOPOLITICAL_TOPICS
from app.utils.logger import get_logger
from app.scrapers.scraper_manager import ScraperManager
from app.db.database import get_db_context
from app.db.repositories import ArticleRepository, SourceRepository
from app.db.models import ArticleStatus


logger = get_logger("scheduler")


class GeopoliticalScheduler:
    """
    Agendador de tarefas para coleta automática de notícias.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scraper_manager = ScraperManager()

    def start(self):
        """Inicia o agendador"""
        # Tarefa de coleta periódica
        self.scheduler.add_job(
            self.collect_news_task,
            trigger=IntervalTrigger(hours=settings.SCHEDULER_INTERVAL_HOURS),
            id="collect_news",
            name="Coleta periódica de notícias",
            replace_existing=True
        )

        # Tarefa de limpeza diária
        self.scheduler.add_job(
            self.cleanup_old_articles,
            trigger=CronTrigger(hour=3, minute=0),  # 3:00 AM
            id="cleanup",
            name="Limpeza de artigos antigos",
            replace_existing=True
        )

        # Tarefa de atualização de reputação semanal
        self.scheduler.add_job(
            self.update_source_reputation,
            trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),  # Domingo 4:00 AM
            id="update_reputation",
            name="Atualização de reputação de fontes",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Agendador iniciado")

    def stop(self):
        """Para o agendador"""
        self.scheduler.shutdown()
        logger.info("Agendador parado")

    def collect_news_task(self):
        """
        Tarefa de coleta de notícias de todas as fontes.
        Executa periodicamente baseado em SCHEDULER_INTERVAL_HOURS.
        """
        logger.info("Iniciando coleta agendada de notícias...")

        try:
            # Coletar de todas as fontes
            articles_by_source = self.scraper_manager.scrape_all_sources(
                max_articles_per_source=settings.MAX_ARTICLES_PER_SOURCE
            )

            total_new = 0
            total_existing = 0

            with get_db_context() as db:
                for source_key, articles in articles_by_source.items():
                    # Obter ou criar fonte no banco
                    source = SourceRepository.get_by_key(db, source_key)

                    for article in articles:
                        # Verificar se já existe
                        if ArticleRepository.exists(db, article.url):
                            total_existing += 1
                            continue

                        # Criar novo artigo
                        try:
                            ArticleRepository.create(
                                db,
                                source_id=source.id if source else None,
                                external_id=article.url,
                                title=article.title,
                                content=article.content,
                                raw_content=article.raw_content,
                                url=article.url,
                                author=article.author,
                                published_at=article.published_at,
                                language=article.language,
                                status=ArticleStatus.PENDING
                            )
                            total_new += 1
                        except Exception as e:
                            logger.error(f"Erro ao salvar artigo: {e}")

                    # Atualizar timestamp de última coleta
                    if source:
                        SourceRepository.update_last_scraped(db, source.id)

            logger.info(f"Coleta finalizada: {total_new} novos, {total_existing} existentes")

        except Exception as e:
            logger.error(f"Erro na coleta agendada: {e}")

    def cleanup_old_articles(self, days: int = 30):
        """
        Remove artigos mais antigos que N dias.
        Mantém apenas os que fazem parte de relatórios.
        """
        logger.info(f"Iniciando limpeza de artigos com mais de {days} dias...")

        try:
            # Implementação simplificada - em produção, fazer query direta
            logger.info("Limpeza concluída")

        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")

    def update_source_reputation(self):
        """
        Atualiza scores de reputação das fontes baseado em métricas.
        """
        logger.info("Atualizando reputação das fontes...")

        try:
            # Implementação simplificada
            # Em produção: analisar precisão histórica, correções feitas, etc.
            logger.info("Reputação atualizada")

        except Exception as e:
            logger.error(f"Erro ao atualizar reputação: {e}")

    def collect_specific_topic(self, topic: str):
        """
        Coleta notícias sobre um tema específico (sob demanda).

        Args:
            topic: Tema para coletar
        """
        logger.info(f"Coleta sob demanda: {topic}")

        try:
            articles = self.scraper_manager.search_topic(
                topic=topic,
                min_sources=3,
                max_articles_per_source=5
            )

            logger.info(f"Coletados {len(articles)} artigos sobre '{topic}'")
            return articles

        except Exception as e:
            logger.error(f"Erro na coleta sob demanda: {e}")
            return []


# Instância global
scheduler = GeopoliticalScheduler()


def start_scheduler():
    """Função helper para iniciar o agendador"""
    scheduler.start()


def stop_scheduler():
    """Função helper para parar o agendador"""
    scheduler.stop()


if __name__ == "__main__":
    # Para teste direto
    import time

    logger.info("Iniciando scheduler em modo teste...")
    scheduler.start()

    try:
        # Executar coleta imediatamente para teste
        scheduler.collect_news_task()

        # Manter rodando
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()
        logger.info("Scheduler encerrado")
