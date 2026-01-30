"""
Sistema de logging configurado para a aplicação
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "geopolitica",
    level: int = logging.INFO,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Configura e retorna um logger formatado.

    Args:
        name: Nome do logger
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Caminho opcional para arquivo de log

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "geopolitica") -> logging.Logger:
    """
    Obtém um logger existente ou cria um novo.

    Args:
        name: Nome do logger

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        return setup_logger(name)

    return logger


class LoggerMixin:
    """Mixin para adicionar logging a classes"""

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
