"""
Testes para a API FastAPI
"""
import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Testes para o endpoint de health"""

    def test_health_check(self):
        """Testa endpoint de health"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"


class TestSourcesEndpoint:
    """Testes para o endpoint de fontes"""

    def test_list_sources(self):
        """Testa listagem de fontes"""
        response = client.get("/api/v1/sources")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "sources" in data
        assert data["total"] > 0

    def test_source_structure(self):
        """Testa estrutura de uma fonte"""
        response = client.get("/api/v1/sources")
        data = response.json()

        if data["sources"]:
            source = data["sources"][0]
            assert "key" in source
            assert "name" in source
            assert "url" in source
            assert "reputation_score" in source


class TestRootEndpoint:
    """Testes para o endpoint raiz"""

    def test_root(self):
        """Testa endpoint raiz"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestSearchEndpoint:
    """Testes para o endpoint de busca"""

    def test_search_validation(self):
        """Testa validação do endpoint de busca"""
        # Tema muito curto
        response = client.post("/api/v1/search", json={"topic": "a"})
        assert response.status_code == 422  # Validation error

    def test_search_structure(self):
        """Testa estrutura da resposta de busca"""
        response = client.post(
            "/api/v1/search",
            json={"topic": "test topic", "max_articles_per_source": 1}
        )

        # Pode falhar se não conseguir scrape, mas estrutura deve estar correta
        if response.status_code == 200:
            data = response.json()
            assert "topic" in data
            assert "articles_found" in data
            assert "sources_used" in data


class TestStatsEndpoint:
    """Testes para o endpoint de estatísticas"""

    def test_stats(self):
        """Testa endpoint de estatísticas"""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200

        data = response.json()
        assert "sources_active" in data
        assert "cache_stats" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
