"""
Módulo de prompts para OpenAI API
"""
from .factual_summary import FACTUAL_SUMMARY_PROMPT
from .bias_detection import BIAS_DETECTION_PROMPT
from .simple_explanation import SIMPLE_EXPLANATION_PROMPT
from .confidence_score import CONFIDENCE_SCORE_PROMPT
from .scenario_projection import SCENARIO_PROJECTION_PROMPT

__all__ = [
    "FACTUAL_SUMMARY_PROMPT",
    "BIAS_DETECTION_PROMPT",
    "SIMPLE_EXPLANATION_PROMPT",
    "CONFIDENCE_SCORE_PROMPT",
    "SCENARIO_PROJECTION_PROMPT"
]
