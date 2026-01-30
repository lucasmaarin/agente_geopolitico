"""
Módulo de pipelines para processamento de notícias
"""
from .extractor import SemanticExtractor
from .analyzer import OpenAIAnalyzer
from .cross_reference import CrossReferenceEngine
from .report_generator import ReportGenerator

__all__ = [
    "SemanticExtractor",
    "OpenAIAnalyzer",
    "CrossReferenceEngine",
    "ReportGenerator"
]
