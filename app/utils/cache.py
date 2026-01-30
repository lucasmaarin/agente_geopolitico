"""
Sistema de cache em memória com TTL
"""
import time
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheEntry:
    """Entrada do cache com valor e timestamp"""
    value: Any
    timestamp: float
    ttl: int


class Cache:
    """
    Cache em memória thread-safe com TTL e limite de tamanho.
    """

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        """
        Inicializa o cache.

        Args:
            default_ttl: Tempo de vida padrão em segundos (1 hora)
            max_size: Número máximo de entradas no cache
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()

    def _generate_key(self, *args, **kwargs) -> str:
        """Gera uma chave única baseada nos argumentos"""
        key_data = f"{args}{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Verifica se uma entrada expirou"""
        return time.time() - entry.timestamp > entry.ttl

    def _cleanup(self) -> None:
        """Remove entradas expiradas"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry.timestamp > entry.ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    def _evict_oldest(self) -> None:
        """Remove a entrada mais antiga se o cache estiver cheio"""
        if len(self._cache) >= self._max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].timestamp
            )
            del self._cache[oldest_key]

    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.

        Args:
            key: Chave do cache

        Returns:
            Valor armazenado ou None se não existir/expirado
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return None

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no cache.

        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: Tempo de vida em segundos (usa default se não especificado)
        """
        with self._lock:
            self._cleanup()
            self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl or self._default_ttl
            )

    def delete(self, key: str) -> bool:
        """
        Remove uma entrada do cache.

        Args:
            key: Chave do cache

        Returns:
            True se removido, False se não existia
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Limpa todo o cache"""
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self._lock:
            self._cleanup()
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "default_ttl": self._default_ttl
            }


def cached(ttl: Optional[int] = None, cache_instance: Optional[Cache] = None):
    """
    Decorator para cache de funções.

    Args:
        ttl: Tempo de vida em segundos
        cache_instance: Instância de Cache a usar (cria nova se não fornecida)

    Usage:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            ...
    """
    _cache = cache_instance or Cache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{_cache._generate_key(*args, **kwargs)}"

            result = _cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            _cache.set(key, result, ttl)
            return result

        wrapper.cache = _cache
        wrapper.cache_clear = _cache.clear
        return wrapper

    return decorator


# Instância global do cache
global_cache = Cache()
